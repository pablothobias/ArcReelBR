"""Client media ingest tools: original product photographs, finished media, storyboard end frames and project BGM.

Handlers are thin adapters over the shared native services used by the Web upload routes
(``server.services.project.asset_uploads``, ``server.services.currency.manual_media_install``,
``server.services.project.end_frame``). Client bytes arrive as inline ``content_base64`` or as a
``staged_upload_id`` from the remote media-transport staging service; server filesystem paths are
never accepted. None of these tools submits generation tasks or provider calls.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, BinaryIO, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from lib.artifacts.version_manager import VersionManager
from lib.bgm.service import BgmError
from lib.i18n import DEFAULT_LOCALE, translate_or
from lib.infra.api_errors import ApiError
from lib.infra.async_thread import run_sync_transaction
from lib.infra.content_digest import sha256_file
from lib.project.asset_types import ASSET_SPECS, resolve_asset_key
from lib.project.project_change_hints import project_change_source
from lib.project.project_manager import is_reference_video_project
from lib.script.script_editor import ScriptEditError
from server.media_tools.context import tool_error, tool_problem
from server.services.currency.manual_media_install import (
    install_derivative_sheet,
    install_reference_unit_video,
    install_shot_storyboard_image,
    install_shot_video,
)
from server.services.currency.upload_finalize import (
    UPLOAD_IMAGE_MAX_BYTES,
    UPLOAD_VIDEO_MAX_BYTES,
    UploadValidationError,
    validate_upload,
)
from server.services.media_transport import MediaTransportError, discard_staged_upload, resolve_staged_upload
from server.services.project.asset_uploads import (
    ProductReferenceUpload,
    ReferenceImagesChangedError,
    arrange_product_reference_images,
    bgm_error_message,
    check_upload_target,
    install_asset_upload,
    install_product_reference_images,
    install_project_bgm,
    product_reference_ref_id,
)
from server.services.project.end_frame import (
    EndFrameError,
    clear_end_frame,
    require_last_frame_capability,
    resolve_end_frame_source_identity,
    set_end_frame_from_bytes,
    set_end_frame_from_project_image,
)
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolRequest, migration_gate

INLINE_BASE64_MAX_CHARS = 20 * 1024 * 1024

MAX_PRODUCT_PHOTOS_PER_CALL = 10

_FALLBACK_DETAILS: dict[str, str] = {
    "reference_images_changed": "reference_images changed since expected_order was read; list again and retry.",
    "invalid_base64": "content_base64 is not valid base64.",
}


# ---------------------------------------------------------------------------
# Byte input
# ---------------------------------------------------------------------------


class MediaBytes(BaseModel):
    """Client-supplied file bytes: inline base64 or a completed staged upload, never a server path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str = Field(
        min_length=1,
        max_length=255,
        description="Original plain filename (no directories); its extension selects validation",
    )
    content_base64: str | None = Field(
        default=None,
        min_length=1,
        max_length=INLINE_BASE64_MAX_CHARS,
        description="Base64 file bytes (at most 20 MiB of base64); exclusive with staged_upload_id",
    )
    staged_upload_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description=(
            "upload_id of a completed begin_media_upload/append_media_upload_chunk staging for this project "
            "(remote MCP only), for files larger than the inline limit; exclusive with content_base64. Staging "
            "purpose must match: product photos product_reference_image, asset sheets asset_image, derivatives "
            "derivative_image, storyboard images storyboard_image, storyboard/unit videos unit_video, end frames "
            "end_frame, BGM bgm"
        ),
    )

    @model_validator(mode="after")
    def _one_source(self) -> MediaBytes:
        if (self.content_base64 is None) == (self.staged_upload_id is None):
            raise ValueError("provide exactly one of content_base64 or staged_upload_id")
        name = self.filename
        if "/" in name or "\\" in name or name in {".", ".."} or "\x00" in name:
            raise ValueError("filename must be a plain filename without directories")
        return self


@dataclass(slots=True)
class _OpenedInput:
    filename: str
    stream: BinaryIO
    size_bytes: int
    sha256: str


class _InputProblem(Exception):
    def __init__(self, code: str, **params: Any):
        super().__init__(code)
        self.code = code
        self.params = params


def _decode_inline(data: str) -> tuple[bytes, str]:
    try:
        content = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise _InputProblem("invalid_base64") from exc
    return content, hashlib.sha256(content).hexdigest()


@asynccontextmanager
async def _opened(
    scope: ProjectScope, services: Services, item: MediaBytes, *, purposes: tuple[str, ...]
) -> AsyncGenerator[_OpenedInput]:
    """Open one byte input: decode inline base64, or open a complete digest-verified staged upload.

    Staged uploads are resolved by ``resolve_staged_upload`` (project + remote-caller scoped); its
    refusal codes (``upload_not_found`` / ``upload_expired`` / ``upload_incomplete`` /
    ``upload_digest_mismatch`` / ``upload_purpose_mismatch``) are returned unchanged. ``purposes`` names the
    staging purposes this install accepts, so a staging checked against another media kind's limit is refused."""
    if item.content_base64 is not None:
        content, digest = await asyncio.to_thread(_decode_inline, item.content_base64)
        yield _OpenedInput(filename=item.filename, stream=BytesIO(content), size_bytes=len(content), sha256=digest)
        return
    assert item.staged_upload_id is not None
    try:
        staged = await resolve_staged_upload(
            services.projects, scope.project_name, item.staged_upload_id, purposes=purposes
        )
    except MediaTransportError as exc:
        raise _InputProblem(exc.code, **exc.params) from exc
    try:
        yield _OpenedInput(
            filename=item.filename, stream=staged.stream, size_bytes=staged.size_bytes, sha256=staged.sha256
        )
    finally:
        await asyncio.to_thread(staged.close)


async def _discard_staged(scope: ProjectScope, services: Services, *items: MediaBytes | None) -> None:
    """Release staged uploads after their bytes were installed; failures only leave them to the TTL sweep."""
    for item in items:
        if item is None or item.staged_upload_id is None:
            continue
        with suppress(Exception):
            await discard_staged_upload(services.projects, scope.project_name, item.staged_upload_id)


async def _read_bounded(opened: _OpenedInput, max_bytes: int) -> bytes:
    """Read an image-sized input fully (bounded by the native limit + 1 so oversize is detectable)."""
    return await asyncio.to_thread(opened.stream.read, max_bytes + 1)


# ---------------------------------------------------------------------------
# Problem mapping
# ---------------------------------------------------------------------------


def _detail(key: str, params: dict[str, Any]) -> str:
    fallback = _FALLBACK_DETAILS.get(key, key)
    with suppress(KeyError, IndexError, ValueError):
        fallback = fallback.format(**params)
    try:
        return translate_or(key, fallback, DEFAULT_LOCALE, **params)
    except (KeyError, IndexError, ValueError):
        return fallback


def _keyed(key: str, params: dict[str, Any] | None = None) -> ToolOutcome[Any]:
    params = dict(params or {})
    return tool_problem(_detail(key, params), code=key, params=params or None)


def _mapped_problem(operation: str, exc: BaseException, *, filename: str | None = None) -> ToolOutcome[Any]:
    if isinstance(exc, _InputProblem):
        return _keyed(exc.code, exc.params)
    if isinstance(exc, (UploadValidationError, EndFrameError)):
        return _keyed(exc.key, dict(exc.params))
    if isinstance(exc, ApiError):
        return _keyed(exc.key, dict(exc.params))
    if isinstance(exc, BgmError):
        # Same code→message mapping as the Web BGM routes; the native free text can embed a random staging name.
        _status, key, params = bgm_error_message(exc)
        detail = _detail(key, params)
        if filename:
            detail = f"{filename}: {detail}"
        public = {name: value for name, value in params.items() if name in {"ext", "allowed", "max_mb"}}
        return tool_problem(detail, code=exc.code, params=public or None)
    if isinstance(exc, ReferenceImagesChangedError):
        return _keyed("reference_images_changed", {"current_order": exc.current})
    if isinstance(exc, ScriptEditError):
        return tool_problem(str(exc), code="script_edit_failed")
    if isinstance(exc, FileNotFoundError):
        # Never echo the exception text: it can contain absolute server paths.
        return tool_problem("Project or script not found", code="not_found")
    return tool_error(operation, exc)


# ---------------------------------------------------------------------------
# MCP-011: original product photographs
# ---------------------------------------------------------------------------


class UploadProductReferenceImagesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    product: str = Field(min_length=1, description="Existing product name")
    images: list[MediaBytes] = Field(
        min_length=1,
        max_length=MAX_PRODUCT_PHOTOS_PER_CALL,
        description="Original product photographs in the order they should be appended to reference_images",
    )


class ProductReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    product: str = Field(min_length=1, description="Existing product name")


class ArrangeProductReferenceImagesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    product: str = Field(min_length=1, description="Existing product name")
    expected_order: list[str] = Field(
        description="Current ref_id order as returned by list_product_reference_images; mismatch is refused"
    )
    order: list[str] = Field(
        description="New ref_id order; ids omitted from expected_order are detached (their files are kept)"
    )
    confirm_detach: StrictBool = Field(
        default=False,
        description=(
            "Required true when order omits any expected_order id (detaching photos the user approved removing); "
            "reorder-only calls need no confirmation"
        ),
    )


def _product_entry(project: dict, product: str) -> tuple[str, dict] | None:
    bucket = project.get("products") or {}
    key = resolve_asset_key(bucket, product)
    if key is None or not isinstance(bucket.get(key), dict):
        return None
    return key, bucket[key]


def _describe_file(project_dir: Path, rel: str) -> dict[str, Any]:
    target = project_dir / rel
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(project_dir.resolve())
        if not resolved.is_file():
            raise FileNotFoundError(rel)
        digest = sha256_file(resolved)
        size = resolved.stat().st_size
    except (OSError, ValueError):
        return {"present": False, "sha256": None, "size_bytes": None}
    return {"present": True, "sha256": digest, "size_bytes": size}


def _consumption(project: dict, entry: dict, originals: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe which images reach requests, mirroring the native consumers.

    Storyboard images (``lib.artifacts.generation_input`` ``add_product``): the declared sheet, then every
    declared original. Reference video (``resolve_reference_assets``): the sheet replaces the originals;
    originals are sent only when no sheet is declared. Per-request clamping by ``max_reference_images``
    applies to the whole unit/shot reference list in mention order."""
    sheet_declared = bool(entry.get(ASSET_SPECS["product"].sheet_field))
    present_originals = [item["ref_id"] for item in originals if item["present"]]
    if is_reference_video_project(project):
        route = "reference_video"
        used = [] if sheet_declared else present_originals
        rule = "sheet_replaces_originals" if sheet_declared else "originals_without_sheet"
    else:
        route = "storyboard"
        used = present_originals
        rule = "sheet_then_originals"
    return {
        "route": route,
        "rule": rule,
        "sends_product_sheet": sheet_declared,
        "originals_sent": used,
        "image_count_before_clamp": len(used) + (1 if sheet_declared else 0),
    }


async def _product_listing(services: Services, project_name: str, product: str) -> dict[str, Any]:
    def _sync() -> dict[str, Any]:
        project = services.projects.load_project(project_name)
        found = _product_entry(project, product)
        if found is None:
            raise UploadValidationError("product_not_found", status_code=404, name=product)
        key, entry = found
        project_dir = services.projects.get_project_path(project_name)
        refs = entry.get("reference_images") or []
        originals = [
            {"index": index, "ref_id": product_reference_ref_id(str(ref)), **_describe_file(project_dir, str(ref))}
            for index, ref in enumerate(refs)
        ]
        sheet = entry.get(ASSET_SPECS["product"].sheet_field) or ""
        versions = VersionManager(project_dir)
        sheet_view = {
            "declared": bool(sheet),
            "current_version": versions.get_current_version("products", key) if sheet else None,
            **(_describe_file(project_dir, sheet) if sheet else {"present": False, "sha256": None, "size_bytes": None}),
        }
        return {
            "product": key,
            "reference_images": originals,
            "product_sheet": sheet_view,
            "effective_consumption": _consumption(project, entry, originals),
            "project": project,
        }

    listing = await asyncio.to_thread(_sync)
    project = listing.pop("project")
    max_refs: int | None = None
    try:
        caps = await services.capabilities.video_capabilities_for_project(project)
        max_refs = caps.get("max_reference_images")
    except Exception:
        max_refs = None
    listing["effective_consumption"]["max_reference_images"] = max_refs
    listing["effective_consumption"]["note"] = (
        "Provider-library selections install a product_sheet version; they are not original photographs. "
        "Use get_prompt_preview for the exact per-shot/unit reference list after clamping."
    )
    return listing


async def upload_product_reference_images(
    request: ToolRequest[UploadProductReferenceImagesRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    value = request.value
    uploads: list[ProductReferenceUpload] = []
    digests: list[str] = []
    try:
        for item in value.images:
            async with _opened(scope, services, item, purposes=("product_reference_image",)) as opened:
                content = await _read_bounded(opened, UPLOAD_IMAGE_MAX_BYTES)
            uploads.append(ProductReferenceUpload(filename=item.filename, content=content))
            digests.append(opened.sha256)
        installed = await install_product_reference_images(
            manager=services.projects,
            project_name=scope.project_name,
            product_name=value.product,
            uploads=uploads,
            change_source="worker",
        )
        listing = await _product_listing(services, scope.project_name, value.product)
    except Exception as exc:
        return _mapped_problem("upload_product_reference_images", exc)
    await _discard_staged(scope, services, *value.images)
    return ToolOutcome(
        value={
            "product": listing["product"],
            "installed": [
                {
                    "ref_id": product_reference_ref_id(item.path),
                    "original_filename": item.original_filename,
                    "sha256": item.sha256,
                    "input_sha256": digest,
                    "size_bytes": item.size_bytes,
                    "bytes_preserved": item.sha256 == digest,
                }
                for item, digest in zip(installed, digests, strict=True)
            ],
            "reference_images": listing["reference_images"],
            "effective_consumption": listing["effective_consumption"],
            "generation_submitted": False,
        }
    )


async def list_product_reference_images(
    request: ToolRequest[ProductReferenceRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    if (problem := await migration_gate(scope, services)) is not None:
        return ToolOutcome(problem=problem)
    try:
        return ToolOutcome(value=await _product_listing(services, scope.project_name, request.value.product))
    except Exception as exc:
        return _mapped_problem("list_product_reference_images", exc)


async def arrange_product_reference_images_tool(
    request: ToolRequest[ArrangeProductReferenceImagesRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    value = request.value
    would_detach = [ref for ref in value.expected_order if ref not in set(value.order)]
    if would_detach and not value.confirm_detach:
        return tool_problem(
            "Detaching original product photos requires confirm_detach=true after the user approves: "
            + ", ".join(would_detach),
            code="confirmation_required",
            params={"would_detach": would_detach},
        )
    try:
        await run_sync_transaction(
            lambda: arrange_product_reference_images(
                services.projects,
                scope.project_name,
                value.product,
                expected=value.expected_order,
                order=value.order,
                change_source="worker",
            )
        )
        listing = await _product_listing(services, scope.project_name, value.product)
    except KeyError:
        return _keyed("product_not_found", {"name": value.product})
    except ValueError as exc:
        if isinstance(exc, UploadValidationError):
            return _mapped_problem("arrange_product_reference_images", exc)
        return tool_problem(str(exc), code="invalid_request")
    except Exception as exc:
        return _mapped_problem("arrange_product_reference_images", exc)
    detached = [ref for ref in value.expected_order if ref not in set(value.order)]
    return ToolOutcome(value={**listing, "detached": detached, "files_deleted": False})


# ---------------------------------------------------------------------------
# MCP-012: finished media installation
# ---------------------------------------------------------------------------


class AssetSheetTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["asset_sheet"]
    asset_type: Literal["character", "scene", "prop", "product"] = Field(description="Asset type")
    name: str = Field(min_length=1, description="Existing asset name")


class CharacterDerivativeTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["character_derivative"]
    character: str = Field(min_length=1, description="Base character name")
    derivative: str = Field(min_length=1, description="Existing derivative name of that character")


class StoryboardImageTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["storyboard_image"]
    script: str = Field(min_length=1, description="Episode script file, e.g. episode_1.json")
    item_id: str = Field(min_length=1, description="Storyboard segment/scene id (storyboard route only)")


class StoryboardVideoTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["storyboard_video"]
    script: str = Field(min_length=1, description="Episode script file, e.g. episode_1.json")
    item_id: str = Field(min_length=1, description="Storyboard segment/scene id (storyboard route only)")


class ReferenceUnitVideoTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["reference_unit_video"]
    episode: int = Field(ge=1, description="Episode number on the reference-video route")
    unit_id: str = Field(min_length=1, description="Reference-video unit id")


FinishedMediaTarget = Annotated[
    AssetSheetTarget
    | CharacterDerivativeTarget
    | StoryboardImageTarget
    | StoryboardVideoTarget
    | ReferenceUnitVideoTarget,
    Field(discriminator="kind"),
]


#: Staging purposes accepted per install target (``begin_media_upload`` purpose must match).
_TARGET_PURPOSES: dict[str, tuple[str, ...]] = {
    "asset_sheet": ("asset_image",),
    "character_derivative": ("derivative_image",),
    "storyboard_image": ("storyboard_image",),
    "storyboard_video": ("unit_video",),
    "reference_unit_video": ("unit_video",),
}


class InstallFinishedMediaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: FinishedMediaTarget = Field(description="Where the approved finished media becomes the current version")
    file: MediaBytes = Field(description="The finished image or video supplied by the client")


async def _installed_digest(project_dir: Path, rel: str) -> str | None:
    def _sync() -> str | None:
        target = project_dir / rel
        return sha256_file(target) if target.is_file() else None

    return await asyncio.to_thread(_sync)


async def install_finished_media(
    request: ToolRequest[InstallFinishedMediaRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    target = request.value.target
    item = request.value.file
    manager = services.projects
    try:
        async with _opened(scope, services, item, purposes=_TARGET_PURPOSES[target.kind]) as opened:
            input_sha = opened.sha256
            size = opened.size_bytes
            if isinstance(target, AssetSheetTarget):
                upload_target = check_upload_target(target.asset_type, item.filename, target.name)
                content = await _read_bounded(opened, UPLOAD_IMAGE_MAX_BYTES)
                if len(content) > UPLOAD_IMAGE_MAX_BYTES:
                    raise UploadValidationError("upload_too_large", max_mb=UPLOAD_IMAGE_MAX_BYTES // (1024 * 1024))
                result = await install_asset_upload(
                    manager=manager,
                    project_name=scope.project_name,
                    target=upload_target,
                    original_filename=item.filename,
                    content=content,
                    change_source="worker",
                    require_asset=True,
                )
                # The version selected by the install transaction itself (require_asset guarantees one).
                path, version = result.path, result.version
                fingerprints: dict[str, int] = {}
            elif isinstance(target, CharacterDerivativeTarget):
                content = await _read_bounded(opened, UPLOAD_IMAGE_MAX_BYTES)
                installed = await install_derivative_sheet(
                    manager=manager,
                    project_name=scope.project_name,
                    owner_name=target.character,
                    derivative_name=target.derivative,
                    filename=item.filename,
                    content=content,
                    change_source="worker",
                )
                path, version, fingerprints = installed.path, installed.version, installed.asset_fingerprints
            elif isinstance(target, StoryboardImageTarget):
                content = await _read_bounded(opened, UPLOAD_IMAGE_MAX_BYTES)
                installed = await install_shot_storyboard_image(
                    manager=manager,
                    project_name=scope.project_name,
                    script_file=target.script,
                    shot_id=target.item_id,
                    filename=item.filename,
                    content=content,
                    change_source="worker",
                )
                path, version, fingerprints = installed.path, installed.version, installed.asset_fingerprints
            elif isinstance(target, StoryboardVideoTarget):
                installed = await install_shot_video(
                    manager=manager,
                    project_name=scope.project_name,
                    script_file=target.script,
                    shot_id=target.item_id,
                    filename=item.filename,
                    stream=opened.stream,
                    declared_size=min(size, UPLOAD_VIDEO_MAX_BYTES + 1) if size else None,
                    change_source="worker",
                )
                path, version, fingerprints = installed.path, installed.version, installed.asset_fingerprints
            else:
                installed = await install_reference_unit_video(
                    manager=manager,
                    project_name=scope.project_name,
                    episode=target.episode,
                    unit_id=target.unit_id,
                    filename=item.filename,
                    stream=opened.stream,
                    declared_size=min(size, UPLOAD_VIDEO_MAX_BYTES + 1) if size else None,
                    change_source="worker",
                )
                path, version, fingerprints = installed.path, installed.version, installed.asset_fingerprints
        project_dir = await asyncio.to_thread(manager.get_project_path, scope.project_name)
        installed_sha = await _installed_digest(project_dir, path)
    except Exception as exc:
        return _mapped_problem("install_finished_media", exc)
    await _discard_staged(scope, services, item)
    return ToolOutcome(
        value={
            "target": target.model_dump(),
            "path": path,
            "version": version,
            "version_source": "manual_upload",
            "input_sha256": input_sha,
            "installed_sha256": installed_sha,
            "bytes_preserved": installed_sha == input_sha,
            # Read after the install transaction committed; a concurrent install to the same target can replace
            # the file in between, so treat installed_sha256/bytes_preserved as advisory, not proof.
            "installed_sha256_advisory": True,
            "asset_fingerprints": fingerprints,
            "generation_submitted": False,
        }
    )


# ---------------------------------------------------------------------------
# MCP-013: storyboard end frames
# ---------------------------------------------------------------------------


class EndFrameSourceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["storyboard_image", "asset_sheet", "character_derivative", "product_reference_image"] = Field(
        description="Which project image to copy as the end frame"
    )
    script: str | None = Field(default=None, description="storyboard_image: script file of the source storyboard")
    item_id: str | None = Field(default=None, description="storyboard_image: source storyboard segment/scene id")
    asset_type: Literal["character", "scene", "prop", "product"] | None = Field(
        default=None, description="asset_sheet: asset type"
    )
    name: str | None = Field(
        default=None, description="asset_sheet / product_reference_image: asset name; character_derivative: character"
    )
    derivative: str | None = Field(default=None, description="character_derivative: derivative name")
    index: int | None = Field(default=None, ge=0, description="product_reference_image: zero-based index")


class SetEndFrameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    script: str = Field(min_length=1, description="Episode script file of the storyboard shot")
    item_id: str = Field(min_length=1, description="Storyboard segment/scene id receiving the end frame")
    file: MediaBytes | None = Field(default=None, description="Client-supplied end-frame image; exclusive with source")
    source: EndFrameSourceIdentity | None = Field(
        default=None, description="Existing project image identity to snapshot; exclusive with file"
    )

    @model_validator(mode="after")
    def _one_input(self) -> SetEndFrameRequest:
        if (self.file is None) == (self.source is None):
            raise ValueError("provide exactly one of file or source")
        return self


class ClearEndFrameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    script: str = Field(min_length=1, description="Episode script file of the storyboard shot")
    item_id: str = Field(min_length=1, description="Storyboard segment/scene id whose end frame is cleared")


async def set_end_frame(
    request: ToolRequest[SetEndFrameRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    value = request.value
    try:
        project = await asyncio.to_thread(services.projects.load_project, scope.project_name)
        # Agent-only refusal, stricter than the Web route: the storyboard worker silently drops an end frame the
        # model cannot send, so an Agent must not be told it was set.
        caps = await require_last_frame_capability(project, services.capabilities)
        with project_change_source("worker"):
            if value.file is not None:
                async with _opened(scope, services, value.file, purposes=("end_frame",)) as opened:
                    content = await _read_bounded(opened, UPLOAD_IMAGE_MAX_BYTES)
                # Same extension/size policy as the Web end-frame upload route.
                validate_upload(value.file.filename, len(content), kind="image")
                relative = await set_end_frame_from_bytes(
                    project_name=scope.project_name, script_file=value.script, shot_id=value.item_id, content=content
                )
            else:
                source = value.source
                assert source is not None
                source_path = await asyncio.to_thread(
                    lambda: resolve_end_frame_source_identity(
                        services.projects,
                        scope.project_name,
                        kind=source.kind,
                        script_file=source.script,
                        item_id=source.item_id,
                        asset_type=source.asset_type,
                        name=source.name,
                        derivative=source.derivative,
                        index=source.index,
                    )
                )
                relative = await set_end_frame_from_project_image(
                    project_name=scope.project_name,
                    script_file=value.script,
                    shot_id=value.item_id,
                    source_path=source_path,
                )
        project_dir = await asyncio.to_thread(services.projects.get_project_path, scope.project_name)
        digest = await _installed_digest(project_dir, relative)
    except Exception as exc:
        return _mapped_problem("set_end_frame", exc)
    await _discard_staged(scope, services, value.file)
    return ToolOutcome(
        value={
            "script": value.script,
            "item_id": value.item_id,
            "end_frame_image": relative,
            "snapshot_sha256": digest,
            "video_model": {"provider": caps.get("provider_id"), "model": caps.get("model"), "last_frame": True},
            "generation_submitted": False,
        }
    )


async def clear_end_frame_tool(
    request: ToolRequest[ClearEndFrameRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    _services: Services,
) -> ToolOutcome[dict[str, Any]]:
    value = request.value
    try:
        with project_change_source("worker"):
            await clear_end_frame(project_name=scope.project_name, script_file=value.script, shot_id=value.item_id)
    except Exception as exc:
        return _mapped_problem("clear_end_frame", exc)
    return ToolOutcome(value={"script": value.script, "item_id": value.item_id, "end_frame_image": None})


# ---------------------------------------------------------------------------
# MCP-016: project BGM
# ---------------------------------------------------------------------------


class UploadBgmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    file: MediaBytes = Field(description="BGM audio (.mp3/.wav/.m4a) supplied by the client")


async def upload_bgm(
    request: ToolRequest[UploadBgmRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    item = request.value.file
    from lib.bgm.library import BGM_MAX_BYTES

    try:
        async with _opened(scope, services, item, purposes=("bgm",)) as opened:
            content = await asyncio.to_thread(opened.stream.read, BGM_MAX_BYTES + 1)
            input_sha = opened.sha256
        track = await install_project_bgm(
            services.projects, scope.project_name, filename=item.filename, content=content, change_source="worker"
        )
    except Exception as exc:
        return _mapped_problem("upload_bgm", exc, filename=item.filename)
    await _discard_staged(scope, services, item)
    return ToolOutcome(
        value={
            "id": track.id,
            "name": track.name,
            "duration_seconds": track.duration,
            "integrated_lufs": track.integrated_lufs,
            "gain_db": track.gain_db,
            "gain": round(track.gain, 6),
            "content_digest": track.content_digest,
            "input_sha256": input_sha,
            "inserted_into_timeline": False,
        }
    )


def product_reference_summary(value: dict[str, Any]) -> str:
    refs = value.get("reference_images") or []
    consumption = value.get("effective_consumption") or {}
    lines = [f"Product {value.get('product')}: {len(refs)} original photo(s); route {consumption.get('route')}"]
    lines.extend(f"- #{item['index']} {item['ref_id']} sha256={item['sha256']}" for item in refs)
    return "\n".join(lines)


__all__ = [
    "ArrangeProductReferenceImagesRequest",
    "ClearEndFrameRequest",
    "InstallFinishedMediaRequest",
    "MediaBytes",
    "ProductReferenceRequest",
    "SetEndFrameRequest",
    "UploadBgmRequest",
    "UploadProductReferenceImagesRequest",
    "arrange_product_reference_images_tool",
    "clear_end_frame_tool",
    "install_finished_media",
    "list_product_reference_images",
    "product_reference_summary",
    "set_end_frame",
    "upload_bgm",
    "upload_product_reference_images",
]
