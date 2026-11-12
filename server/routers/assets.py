"""Global assets-library routes.

The library operations themselves live in :mod:`server.services.asset_library.global_library`, shared with the Agent
tools; these routes add multipart uploads, entry editing/deletion and the HTTP rendering of refusals."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from lib.asset_library.links import delete_holder_links
from lib.db import async_session_factory
from lib.db.repositories.asset_repo import AssetRepository
from lib.infra.async_thread import run_sync_transaction
from lib.material.global_library import (
    NO_IMAGE_COLUMNS,
    GlobalImage,
    global_image_commit,
    library_entry_lock,
    library_holder,
    release_library_entry,
)
from lib.project.asset_types import GLOBAL_LIBRARY_ASSET_TYPES, ProjectAssetNameConflictError, validate_asset_name
from lib.project.project_change_hints import project_change_source
from lib.project.project_manager import get_project_manager
from server.i18n import Translator
from server.routers._asset_router_factory import localize_project_asset_name_conflict
from server.services.asset_library.global_library import (
    ApplyToProjectRequest,
    FromProjectRequest,
    GlobalLibraryError,
    LibraryContext,
    apply_library_assets,
    content_ids,
    delete_global_asset_files,
    discard_writer,
    forget_after_commit,
    get_library_asset,
    global_library_error_text,
    list_library_assets,
    save_project_asset,
    serialize_asset,
    serialize_entry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["Global asset library"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

__all__ = ["ApplyToProjectRequest", "FromProjectRequest", "router"]


def _context() -> LibraryContext:
    """Resolve collaborators per request so tests can replace this module's bindings."""
    return LibraryContext(pm=get_project_manager(), session_factory=async_session_factory)


def _http_error(exc: GlobalLibraryError, _t: Translator) -> HTTPException:
    message = global_library_error_text(exc, _t)
    if exc.existing is not None:
        return HTTPException(status_code=exc.status, detail={"message": message, "existing": exc.existing})
    return HTTPException(status_code=exc.status, detail=message)


def _validate_asset_name(name: str, _t: Translator) -> str:
    """HTTP boundary wrapper: return 400 for unsafe names (separators / null bytes / ..)."""
    try:
        return validate_asset_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_t("asset_invalid_name", name=name)) from exc


async def _read_upload(file: UploadFile, _t: Translator) -> tuple[bytes, str]:
    """Validate uploaded images and return bytes/extension (415/413 before any writes)."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=415, detail=_t("asset_unsupported_format"))

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=_t("asset_upload_too_large"))
    return data, ext


async def _release_after_delete(holder: str) -> None:
    """The entry is deleted: release all its object references. Deletion is committed; log release failures only, since extra references merely retain objects longer."""
    try:
        await release_library_entry(holder)
    except Exception:
        logger.warning("撤下已删除库条目的对象引用失败 holder=%s", holder, exc_info=True)


async def _delete_global_asset_files(rel_paths: Iterable[str]) -> None:
    await delete_global_asset_files(get_project_manager().data_root, rel_paths)


@router.get("")
async def list_assets(
    _t: Translator,
    type: str | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """List assets with offset pagination.

    ``total`` counts matches for current type/search to determine next-page availability. ``counts`` follows
    search only, not type filtering, so every type tab shows search matches, including unopened tabs."""
    return await list_library_assets(_context(), type=type, q=q, limit=limit, offset=offset)


@router.get("/{asset_id}")
async def get_asset(asset_id: str, _t: Translator):
    try:
        return await get_library_asset(_context(), asset_id)
    except GlobalLibraryError as exc:
        raise _http_error(exc, _t) from exc


@router.post("")
async def create_asset(
    _t: Translator,
    type: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    voice_style: str = Form(""),
    image: UploadFile | None = File(None),
):
    if type not in GLOBAL_LIBRARY_ASSET_TYPES:
        raise HTTPException(status_code=400, detail=_t("asset_invalid_type"))
    name = _validate_asset_name(name, _t)

    upload = await _read_upload(image, _t) if image is not None and image.filename else None

    # Save images before create; failures before entry commit release references/files, while postcommit response failures preserve images.
    # Allocate entry ID first, registering image object references under it.
    asset_id = str(uuid.uuid4())
    holder = library_holder(asset_id)
    data_root = get_project_manager().data_root
    async with global_image_commit(data_root, holder, saves_images=upload is not None) as writer:
        try:
            saved = await run_sync_transaction(writer.save_bytes, upload[0], type, upload[1]) if upload else None
            await writer.hold()
            async with async_session_factory() as s:
                repo = AssetRepository(s)
                try:
                    a = await repo.create(
                        asset_id=asset_id,
                        type=type,
                        name=name,
                        description=description,
                        voice_style=voice_style,
                        source_project=None,
                        **(saved.columns() if saved else NO_IMAGE_COLUMNS),
                    )
                    await writer.commit(s)
                    await s.refresh(a)
                except IntegrityError as exc:
                    await s.rollback()
                    raise HTTPException(status_code=409, detail=_t("asset_already_exists", name=name)) from exc
        except BaseException:
            await discard_writer(writer)
            raise

    return {"asset": serialize_asset(a)}


class UpdateAssetRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    voice_style: str | None = None


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: str,
    req: UpdateAssetRequest,
    _t: Translator,
):
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    if "name" in patch:
        patch["name"] = _validate_asset_name(patch["name"], _t)
    async with async_session_factory() as s:
        repo = AssetRepository(s)
        a = await repo.get_by_id(asset_id)
        if not a:
            raise HTTPException(status_code=404, detail=_t("asset_not_found", name=asset_id))
        if "name" in patch and patch["name"] != a.name and await repo.exists(a.type, patch["name"]):
            raise HTTPException(status_code=409, detail=_t("asset_already_exists", name=patch["name"]))
        try:
            a = await repo.update(asset_id, **patch)
            await s.commit()
            await s.refresh(a)
        except IntegrityError as exc:
            await s.rollback()
            raise HTTPException(status_code=409, detail=_t("asset_already_exists", name=patch.get("name", ""))) from exc
        payload = await serialize_entry(repo, a)
    return {"asset": payload}


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: str, _t: Translator):
    # Serialize with image replacement: deletion reads the final image, avoiding orphaned concurrent replacements in library storage.
    async with library_entry_lock(asset_id), async_session_factory() as s:
        repo = AssetRepository(s)
        a = await repo.get_by_id(asset_id)
        if a:
            # repo.delete removes derivative rows too, but only this code knows their image paths;
            # read them before deleting the base asset, or files become unreachable and permanently remain in library storage.
            derivatives = await repo.list_derivatives(asset_id)
            stored_files = [d.image_path for d in derivatives if d.image_path]
            stored_files.extend(path for path in (a.image_path, a.audio_path) if path)
            # Delete library association copies with entries; project copies and provider assets are unaffected.
            holder = library_holder(asset_id)
            await delete_holder_links(s, project_name=holder)
            await repo.delete(asset_id)
            await s.commit()
            # Delete files/release object references after commit: these are irreversible, and doing them first leaves missing-content rows on transaction failure.
            # Release only this entry's references: projects applying the image retain their own; collect objects only after every reference is gone.
            await _release_after_delete(holder)
            await _delete_global_asset_files(stored_files)
    return


@router.post("/{asset_id}/image")
async def replace_image(
    asset_id: str,
    _t: Translator,
    image: UploadFile = File(...),
):
    # Serialize image replacement per entry: read old images under lock, then release exactly those after commit.
    async with library_entry_lock(asset_id):
        # 1) Load asset and validate existence.
        async with async_session_factory() as s:
            repo = AssetRepository(s)
            a = await repo.get_by_id(asset_id)
            if not a:
                raise HTTPException(status_code=404, detail=_t("asset_not_found", name=asset_id))
            old_image = GlobalImage.of(a)
            asset_type = a.type

        # 2) Validate/save the new image first (415/413 checks), leaving old files intact.
        data, ext = await _read_upload(image, _t)

        # 3) Update DB; failure releases new references/files and preserves the old image.
        holder = library_holder(asset_id)
        async with global_image_commit(get_project_manager().data_root, holder) as writer:
            try:
                new_image = await run_sync_transaction(writer.save_bytes, data, asset_type, ext)
                await writer.hold()
                async with async_session_factory() as s:
                    repo = AssetRepository(s)
                    # Replacing images replaces content: old-image association copies do not belong to new images.
                    await delete_holder_links(s, project_name=holder, content_version_ids=content_ids([old_image]))
                    a = await repo.update(asset_id, **new_image.columns())
                    await writer.commit(s)
                    await s.refresh(a)
                    payload = await serialize_entry(repo, a)
            except BaseException:
                await discard_writer(writer)
                raise

        # 4) Release old references/delete old files only after DB update succeeds.
        await forget_after_commit(holder, [old_image])
        if old_image is not None and old_image.path != new_image.path:
            await _delete_global_asset_files([old_image.path])

    return {"asset": payload}


@router.post("/from-project")
async def from_project(
    req: FromProjectRequest,
    _t: Translator,
):
    try:
        return await save_project_asset(_context(), req)
    except GlobalLibraryError as exc:
        raise _http_error(exc, _t) from exc


@router.post("/apply-to-project")
async def apply_to_project(
    req: ApplyToProjectRequest,
    _t: Translator,
):
    try:
        with project_change_source("webui"):
            return await apply_library_assets(_context(), req)
    except GlobalLibraryError as exc:
        raise _http_error(exc, _t) from exc
    except ProjectAssetNameConflictError as exc:
        raise HTTPException(status_code=409, detail=localize_project_asset_name_conflict(exc, _t)) from exc
