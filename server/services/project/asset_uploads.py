"""Project-level asset uploads shared by the Web upload route and Agent media-ingest tools.

``UPLOAD_SPECS`` is the single registration table for per-``upload_type`` persistence rules
(destination, extension allowlist, size cap, content handling and metadata writeback). The Web
route ``POST /projects/{name}/upload/{upload_type}`` and the Agent tools both call
:func:`check_upload_target` and :func:`persist_asset_upload`, so validation, naming, formal sheet
installation and orphan cleanup stay in one implementation.

Domain failures raise :class:`UploadValidationError` (``key``/``status_code``/``params``); callers
translate them for their transport. Uploading never submits generation work.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from lib.bgm.library import BGM_DIR, BGM_EXTENSIONS, BGM_MAX_BYTES, BgmTrack
from lib.bgm.service import BgmError, BgmLibraryService
from lib.infra.async_thread import run_noninterruptible_sync, run_sync_transaction
from lib.infra.image_utils import IMAGE_FILE_EXTENSIONS, normalize_uploaded_image, validate_image_bytes
from lib.material.formal_objects import formal_commit
from lib.material.storage import ContentVersion
from lib.project.asset_types import ASSET_SPECS, resolve_asset_key, validate_asset_name
from lib.project.project_change_hints import project_change_source
from lib.project.project_manager import ProjectManager
from lib.project.project_migration_guard import assert_project_migration_ok
from lib.speech.audio_utils import (
    AUDIO_REFERENCE_MAX_BYTES,
    AUDIO_REFERENCE_MAX_SECONDS,
    AUDIO_REFERENCE_MIN_SECONDS,
    probe_audio_duration_seconds,
)
from server.services.currency.upload_finalize import (
    UPLOAD_IMAGE_MAX_BYTES,
    UploadValidationError,
    install_manual_asset_sheet_upload,
)

ChangeSource = Literal["webui", "worker"]

_IMAGE_EXTS: tuple[str, ...] = IMAGE_FILE_EXTENSIONS

# Persisted filename policies.
#   stable_png: stable single-image `{name}.png` (actual extension follows image normalization).
#   keep_ext: stable single-file name retaining uploaded extension (audio is not transcoded).
#   sequenced: accumulate images using numbered unique names.
#   delegated: dedicated type branches own naming.
Naming = Literal["stable_png", "keep_ext", "sequenced", "delegated"]

# Pre-persistence content handling.
#   normalize_image: validate/compress by threshold, possibly changing extension.
#   validate_image: check decodability only, preserving original bytes.
#   audio: validate duration without transcoding (max_bytes independently checks size).
#   delegated: dedicated type branches own content handling.
ContentCheck = Literal["normalize_image", "validate_image", "audio", "delegated"]

MetadataSetter = Callable[[ProjectManager, str, str, str], object]


@dataclass(frozen=True)
class UploadSpec:
    """Persistence rules for one upload_type: destination, extension allowlist, size cap, processing, and metadata writeback.

    Register new types only in ``UPLOAD_SPECS``, without copying branches. ``source`` is the sole exception:
    the source-upload route owns its flow; registration supplies only type checks/extension allowlists.

    Uploads addressed by script_file + shot_id that update script metadata use their own storyboard-level
    routes, sharing validation/persistence helpers in ``server.services.currency.upload_finalize`` rather than this table."""

    allowed_exts: tuple[str, ...]
    subdir: tuple[str, ...]
    naming: Naming
    content_check: ContentCheck
    unsupported_ext_key: str = "unsupported_image_type"
    # Request-body limit, None for unlimited; applies to all types independently of content_check.
    max_bytes: int | None = None
    metadata_setter: MetadataSetter | None = None
    # Nonempty means a host-asset field is the file's sole pointer; reject absent hosts
    # (including concurrent-deletion windows), avoiding UI-invisible orphan files. Stable single-image paths
    # tolerate later asset creation, so have no such constraint.
    host_bucket: str | None = None
    host_not_found_key: str = ""
    # Reference-audio byte replacement/field writeback use ProjectManager project-lock transactions; remove old-extension files after commit.
    tracks_stale_audio: bool = False

    def __post_init__(self) -> None:
        # Register host constraints together with 404 wording, or rejection would look up an empty translation key.
        if (self.host_bucket is None) != (not self.host_not_found_key):
            raise ValueError("host_bucket and host_not_found_key must be registered together")
        if self.tracks_stale_audio and self.host_bucket is None:
            raise ValueError("tracks_stale_audio requires a registered host constraint")


UPLOAD_SPECS: dict[str, UploadSpec] = {
    "source": UploadSpec(
        allowed_exts=(".txt", ".md", ".docx", ".epub", ".pdf"),
        subdir=("source",),
        naming="delegated",
        content_check="delegated",
    ),
    "character": UploadSpec(
        allowed_exts=_IMAGE_EXTS,
        subdir=(ASSET_SPECS["character"].subdir,),
        naming="stable_png",
        content_check="normalize_image",
        metadata_setter=ProjectManager.update_project_character_sheet,
    ),
    "character_ref": UploadSpec(
        allowed_exts=_IMAGE_EXTS,
        subdir=(ASSET_SPECS["character"].subdir, "refs"),
        naming="stable_png",
        content_check="normalize_image",
        metadata_setter=ProjectManager.update_character_reference_image,
    ),
    "character_audio_ref": UploadSpec(
        allowed_exts=(".wav", ".mp3"),
        subdir=(ASSET_SPECS["character"].subdir, "refs_audio"),
        naming="keep_ext",
        content_check="audio",
        unsupported_ext_key="unsupported_audio_type",
        max_bytes=AUDIO_REFERENCE_MAX_BYTES,
        metadata_setter=ProjectManager.update_character_reference_audio,
        host_bucket=ASSET_SPECS["character"].bucket_key,
        host_not_found_key="character_not_found",
        tracks_stale_audio=True,
    ),
    "scene": UploadSpec(
        allowed_exts=_IMAGE_EXTS,
        subdir=(ASSET_SPECS["scene"].subdir,),
        naming="stable_png",
        content_check="normalize_image",
        metadata_setter=ProjectManager.update_scene_sheet,
    ),
    "prop": UploadSpec(
        allowed_exts=_IMAGE_EXTS,
        subdir=(ASSET_SPECS["prop"].subdir,),
        naming="stable_png",
        content_check="normalize_image",
        metadata_setter=ProjectManager.update_prop_sheet,
    ),
    "product": UploadSpec(
        allowed_exts=_IMAGE_EXTS,
        subdir=(ASSET_SPECS["product"].subdir,),
        naming="stable_png",
        content_check="normalize_image",
        metadata_setter=ProjectManager.update_product_sheet,
    ),
    # Project BGM is owned by BgmLibraryService (measured loudness, atomic persistence, byte registration); table supplies only type/extension checks.
    "bgm": UploadSpec(
        allowed_exts=BGM_EXTENSIONS,
        subdir=(BGM_DIR,),
        naming="delegated",
        content_check="delegated",
        unsupported_ext_key="unsupported_audio_type",
        max_bytes=BGM_MAX_BYTES,
    ),
    "product_ref": UploadSpec(
        allowed_exts=_IMAGE_EXTS,
        subdir=(ASSET_SPECS["product"].subdir, "refs"),
        naming="sequenced",
        # Product originals anchor fidelity acceptance (ADR 0034): check decodability only, preserving original bytes/extensions,
        # without threshold compression/reencoding. Presubmission reference compression separately guarantees request-body limits.
        content_check="validate_image",
        metadata_setter=ProjectManager.add_product_reference_image,
        host_bucket=ASSET_SPECS["product"].bucket_key,
        host_not_found_key="product_not_found",
    ),
}

FORMAL_SHEET_UPLOAD_TYPES = frozenset(ASSET_SPECS)

# Allowed file types (frontend/src/utils/source-files.ts mirrors source).
ALLOWED_EXTENSIONS = {upload_type: list(spec.allowed_exts) for upload_type, spec in UPLOAD_SPECS.items()}


@dataclass(frozen=True, slots=True)
class UploadTarget:
    """A validated upload request: its registered spec, lowercase extension and normalized asset name."""

    upload_type: str
    spec: UploadSpec
    ext: str
    name: str | None


def check_upload_target(upload_type: str, filename: str, name: str | None) -> UploadTarget:
    """Validate upload type, extension and asset name before any bytes are read.

    Names enter persisted paths, so unsafe separators / ``..`` / controls are rejected here.
    Omitted names fall back to original stems without validation."""
    spec = UPLOAD_SPECS.get(upload_type)
    if spec is None:
        raise UploadValidationError("invalid_upload_type", upload_type=upload_type)
    ext = Path(filename).suffix.lower()
    if ext not in spec.allowed_exts:
        raise UploadValidationError(spec.unsupported_ext_key, ext=ext, allowed=", ".join(spec.allowed_exts))
    if name:
        try:
            name = validate_asset_name(name)
        except ValueError as exc:
            raise UploadValidationError("asset_invalid_name", name=name) from exc
    return UploadTarget(upload_type=upload_type, spec=spec, ext=ext, name=name)


def _check_size(spec: UploadSpec, content: bytes) -> None:
    if spec.max_bytes is not None and len(content) > spec.max_bytes:
        raise UploadValidationError("upload_too_large", max_mb=spec.max_bytes // (1024 * 1024))


async def _check_audio(spec: UploadSpec, content: bytes, ext: str) -> None:
    if spec.content_check != "audio":
        return
    try:
        duration = await probe_audio_duration_seconds(content, ext)
    except ValueError as exc:
        raise UploadValidationError("invalid_audio_file") from exc
    if duration is not None and not (AUDIO_REFERENCE_MIN_SECONDS <= duration <= AUDIO_REFERENCE_MAX_SECONDS):
        raise UploadValidationError(
            "audio_duration_out_of_range",
            min_seconds=int(AUDIO_REFERENCE_MIN_SECONDS),
            max_seconds=int(AUDIO_REFERENCE_MAX_SECONDS),
        )


def _install_sync(
    *,
    manager: ProjectManager,
    project_name: str,
    target: UploadTarget,
    original_filename: str,
    content: bytes,
    change_source: ChangeSource,
    require_reference_host: bool,
    require_asset: bool,
) -> AssetUploadResult:
    installed_version: ContentVersion | None = None
    spec, ext, name, upload_type = target.spec, target.ext, target.name, target.upload_type
    project_dir = manager.get_project_path(project_name)

    if require_reference_host and upload_type == "character_ref":
        hosts = manager.load_project(project_name).get("characters") or {}
        if not name or resolve_asset_key(hosts, name) is None:
            raise UploadValidationError("character_not_found", status_code=404, name=name or "")

    if spec.host_bucket is not None:
        hosts = manager.load_project(project_name).get(spec.host_bucket) or {}
        # validate_asset_name normalized name to NFC; existing host keys may be NFD, so resolve existence in the coordinate system.
        if not name or resolve_asset_key(hosts, name) is None:
            raise UploadValidationError(spec.host_not_found_key, status_code=404, name=name or "")

    if require_asset and upload_type in FORMAL_SHEET_UPLOAD_TYPES:
        hosts = manager.load_project(project_name).get(ASSET_SPECS[upload_type].bucket_key) or {}
        if not name or resolve_asset_key(hosts, name) is None:
            raise UploadValidationError(f"{upload_type}_not_found", status_code=404, name=name or "", id=name or "")

    target_dir = project_dir.joinpath(*spec.subdir)
    # Stable filenames avoid jpg/png version-restoration/reference mismatches; omitted names use original stems.
    stem = name or Path(original_filename).stem
    filename = f"{stem}.png" if spec.naming == "stable_png" else f"{stem}{ext}"

    target_dir.mkdir(parents=True, exist_ok=True)

    if spec.content_check == "normalize_image":
        try:
            content, normalized_ext = normalize_uploaded_image(content, ext)
        except ValueError as exc:
            raise UploadValidationError("invalid_image_file") from exc
        filename = Path(filename).with_suffix(normalized_ext).name
    elif spec.content_check == "validate_image":
        try:
            validate_image_bytes(content)
        except ValueError as exc:
            raise UploadValidationError("invalid_image_file") from exc

    created_placeholder = False
    if spec.naming == "sequenced":
        # Allocate numbered unique names using atomic exclusive placeholders: concurrent uploads for one host
        # receive distinct numbers without silently overwriting each other.
        seq = 1
        while True:
            candidate = target_dir / f"{stem}_{seq}{ext or '.png'}"
            try:
                candidate.touch(exist_ok=False)
                created_placeholder = True
                break
            except FileExistsError:
                seq += 1
        filename = candidate.name

    target_path = target_dir / filename
    relative_path = "/".join((*spec.subdir, filename))

    if require_reference_host and upload_type == "character_ref" and name:
        try:
            with project_change_source(change_source):
                manager.install_character_reference_image(project_name, name, relative_path, content)
        except KeyError as exc:
            raise UploadValidationError("character_not_found", status_code=404, name=name) from exc
    elif spec.tracks_stale_audio and name:
        try:
            with project_change_source(change_source):
                manager.install_character_reference_audio(project_name, name, relative_path, content)
        except KeyError as exc:
            raise UploadValidationError(spec.host_not_found_key, status_code=404, name=name) from exc
    elif upload_type in FORMAL_SHEET_UPLOAD_TYPES and name:
        with project_change_source(change_source):
            installed_version = install_manual_asset_sheet_upload(
                project_manager=manager,
                project_name=project_name,
                asset_type=upload_type,
                name=name,
                sheet_path=relative_path,
                content=content,
                original_filename=original_filename,
                require_asset=require_asset,
            )
        if require_asset and installed_version is None:
            # The asset was deleted between the precheck and the locked install; nothing was written.
            raise UploadValidationError(f"{upload_type}_not_found", status_code=404, name=name, id=name)
    else:
        try:
            with open(target_path, "wb") as f:
                f.write(content)

            if spec.metadata_setter is not None and name:
                try:
                    with project_change_source(change_source):
                        spec.metadata_setter(manager, project_name, name, relative_path)
                except KeyError as exc:
                    if spec.host_bucket is not None:
                        # Entry validation established host existence; concurrent-deletion races return 404,
                        # cleaning persisted files to avoid orphans.
                        raise UploadValidationError(spec.host_not_found_key, status_code=404, name=name) from exc
                    # Single-image types ignore absent assets: deterministic paths remain referencable when assets are created later.
        except BaseException:
            if created_placeholder or spec.host_bucket is not None:
                # hard-delete: rollback -- Remove this request's new uniquely named upload when metadata writeback fails.
                target_path.unlink(missing_ok=True)
            raise

    payload = {
        "success": True,
        "filename": filename,
        "path": relative_path,
        "url": f"/api/v1/files/{project_name}/{relative_path}",
    }
    return AssetUploadResult(
        payload=payload, path=relative_path, version=installed_version.version if installed_version else None
    )


@dataclass(frozen=True, slots=True)
class AssetUploadResult:
    """Outcome of one project upload: the Web response payload, the persisted path, and — for finished sheets —
    the version the install transaction itself selected (never re-read afterwards)."""

    payload: dict[str, Any]
    path: str
    version: int | None


async def install_asset_upload(
    *,
    manager: ProjectManager,
    project_name: str,
    target: UploadTarget,
    original_filename: str,
    content: bytes,
    change_source: ChangeSource,
    require_reference_host: bool = False,
    require_asset: bool = False,
) -> AssetUploadResult:
    """Persist one non-source, non-BGM project upload through the registered spec.

    Finished asset sheets (character/scene/prop/product with a name) become a selected
    ``manual_upload`` version through ``install_manual_asset_sheet_upload`` inside ``formal_commit``.
    ``require_asset`` refuses sheet bytes for an asset that does not exist (Agent installs), instead of
    writing unclaimed bytes for a later asset.

    Raises:
        UploadValidationError: Size/content/host validation failed.
        FileNotFoundError: Missing project.
    """
    if target.upload_type in {"source", "bgm"}:
        raise ValueError(f"{target.upload_type} uploads have dedicated flows")
    _check_size(target.spec, content)
    await _check_audio(target.spec, content, target.ext)

    def _sync() -> AssetUploadResult:
        return _install_sync(
            manager=manager,
            project_name=project_name,
            target=target,
            original_filename=original_filename,
            content=content,
            change_source=change_source,
            require_reference_host=require_reference_host,
            require_asset=require_asset,
        )

    if target.upload_type in FORMAL_SHEET_UPLOAD_TYPES and target.name:
        # Finished sheets follow global new-content-version storage settings (local by default).
        async with formal_commit(project_name):
            return await run_sync_transaction(_sync)
    return await run_sync_transaction(_sync)


async def persist_asset_upload(
    *,
    manager: ProjectManager,
    project_name: str,
    target: UploadTarget,
    original_filename: str,
    content: bytes,
    change_source: ChangeSource,
    require_reference_host: bool = False,
    require_asset: bool = False,
) -> dict[str, Any]:
    """Web-route shape of :func:`install_asset_upload`: the unchanged response payload."""
    result = await install_asset_upload(
        manager=manager,
        project_name=project_name,
        target=target,
        original_filename=original_filename,
        content=content,
        change_source=change_source,
        require_reference_host=require_reference_host,
        require_asset=require_asset,
    )
    return result.payload


# ---------------------------------------------------------------------------
# Product original photographs (ordered, byte-preserving)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProductReferenceUpload:
    filename: str
    content: bytes


@dataclass(frozen=True, slots=True)
class InstalledProductReference:
    path: str
    original_filename: str
    sha256: str
    size_bytes: int


def _remove_product_references(manager: ProjectManager, project_name: str, product_name: str, paths: list[str]) -> None:
    """Compensate a partially installed batch: detach this batch's paths, then delete their unique files."""
    project_dir = manager.get_project_path(project_name)

    def _mutate(project: dict) -> None:
        bucket = project.get("products")
        key = resolve_asset_key(bucket, product_name)
        if not isinstance(bucket, dict) or key is None:
            return
        refs = bucket[key].get("reference_images")
        if isinstance(refs, list):
            bucket[key]["reference_images"] = [ref for ref in refs if ref not in paths]

    try:
        manager.update_project(project_name, _mutate)
    finally:
        for path in paths:
            # hard-delete: rollback -- Remove files this failed batch created under unique sequenced names.
            (project_dir / path).unlink(missing_ok=True)


async def install_product_reference_images(
    *,
    manager: ProjectManager,
    project_name: str,
    product_name: str,
    uploads: Sequence[ProductReferenceUpload],
    change_source: ChangeSource,
) -> list[InstalledProductReference]:
    """Append original product photographs in the given order, preserving their exact bytes.

    Every upload is validated (extension, image limit, decodability) before anything is written; the
    batch then installs sequentially through the ``product_ref`` spec, so ``reference_images`` order
    matches ``uploads``. If a later item fails (for example the product is deleted concurrently), this
    batch's earlier paths are detached and their files removed, leaving no orphans. No generation runs.
    """
    if not uploads:
        raise UploadValidationError("missing_filename")
    targets: list[UploadTarget] = []
    for upload in uploads:
        target = check_upload_target("product_ref", upload.filename, product_name)
        if len(upload.content) > UPLOAD_IMAGE_MAX_BYTES:
            raise UploadValidationError("upload_too_large", max_mb=UPLOAD_IMAGE_MAX_BYTES // (1024 * 1024))
        try:
            await asyncio.to_thread(validate_image_bytes, upload.content)
        except ValueError as exc:
            raise UploadValidationError("invalid_image_file", filename=upload.filename) from exc
        targets.append(target)

    installed: list[InstalledProductReference] = []
    try:
        for upload, target in zip(uploads, targets, strict=True):
            result = await install_asset_upload(
                manager=manager,
                project_name=project_name,
                target=target,
                original_filename=upload.filename,
                content=upload.content,
                change_source=change_source,
            )
            digest = await asyncio.to_thread(lambda data=upload.content: hashlib.sha256(data).hexdigest())
            installed.append(
                InstalledProductReference(
                    path=result.path,
                    original_filename=upload.filename,
                    sha256=digest,
                    size_bytes=len(upload.content),
                )
            )
    except BaseException:
        if installed:
            paths = [item.path for item in installed]
            await run_noninterruptible_sync(_remove_product_references, manager, project_name, product_name, paths)
        raise
    return installed


def product_reference_ref_id(path: str) -> str:
    """Stable per-product identity of an original photograph: its unique sequenced file name."""
    return path.rsplit("/", 1)[-1]


class ReferenceImagesChangedError(Exception):
    """``reference_images`` no longer matches the order the caller based its arrangement on."""

    def __init__(self, current: list[str]):
        super().__init__("reference_images_changed")
        self.current = current


def arrange_product_reference_images(
    manager: ProjectManager,
    project_name: str,
    product_name: str,
    *,
    expected: Sequence[str],
    order: Sequence[str],
    change_source: ChangeSource,
) -> list[str]:
    """Reorder and/or detach original photographs, as the Web asset PATCH of ``reference_images`` does.

    ``expected`` and ``order`` hold ref ids (:func:`product_reference_ref_id`). The comparison and the
    write run in one project-lock transaction (``update_asset_entry``), so a concurrent upload or
    arrangement raises :class:`ReferenceImagesChangedError` instead of being overwritten. Detached
    images keep their files (no deletion), matching native PATCH semantics; nothing is generated.

    Raises:
        KeyError: Product missing.
        ValueError: ``order`` contains unknown or duplicate ids.
        ReferenceImagesChangedError: Current list differs from ``expected``.
    """
    if len(set(order)) != len(order):
        raise ValueError("order contains duplicate ref ids")
    unknown = [ref for ref in order if ref not in set(expected)]
    if unknown:
        raise ValueError(f"order contains ref ids not in expected_order: {', '.join(unknown)}")
    arranged: list[str] = []

    def _mutate(entry: dict) -> None:
        refs = entry.get("reference_images") or []
        if not isinstance(refs, list):
            raise ValueError("reference_images must be a list")
        current_ids = [product_reference_ref_id(str(ref)) for ref in refs]
        if current_ids != list(expected):
            raise ReferenceImagesChangedError(current_ids)
        by_id = {product_reference_ref_id(str(ref)): ref for ref in refs}
        entry["reference_images"] = [by_id[ref] for ref in order]
        arranged.extend(entry["reference_images"])

    with project_change_source(change_source):
        manager.update_asset_entry("product", project_name, product_name, _mutate)
    return arranged


# ---------------------------------------------------------------------------
# Project BGM
# ---------------------------------------------------------------------------


#: Native BGM error code → (HTTP status, i18n message key); the single mapping for Web routes and Agent tools.
BGM_ERROR_STATUS: dict[str, tuple[int, str]] = {
    "bgm_unsupported_type": (400, "unsupported_audio_type"),
    "bgm_too_large": (400, "upload_too_large"),
    "bgm_invalid_audio": (400, "invalid_audio_file"),
    "bgm_silent": (400, "bgm_silent"),
    "bgm_ffmpeg_unavailable": (503, "bgm_ffmpeg_unavailable"),
}


def bgm_error_message(exc: BgmError) -> tuple[int, str, dict[str, Any]]:
    """Translate a ``BgmError`` into (status, i18n key, key params) without its free-text message.

    The native message can embed the server's random staging file name, so callers render only the key."""
    if exc.code == "project_not_found":
        return 404, "project_not_found", {"name": exc.params.get("project", "")}
    status, key = BGM_ERROR_STATUS[exc.code]
    return status, key, dict(exc.params)


def bgm_view(project_name: str, track: BgmTrack) -> dict[str, object]:
    """BGM-list shape shared by the Web BGM routes."""
    return {
        "id": track.id,
        "name": track.name,
        "duration": track.duration,
        "gain": round(track.gain, 6),
        "path": track.file,
        "url": f"/api/v1/files/{project_name}/{track.file}",
    }


async def install_project_bgm(
    manager: ProjectManager,
    project_name: str,
    *,
    filename: str,
    content: bytes,
    change_source: ChangeSource = "webui",
) -> BgmTrack:
    """Register project BGM through ``BgmLibraryService`` (format/size, duration, loudness gain, byte digest).

    Refused while the project migration is blocked. Does not insert the track into any timeline.

    Raises:
        BgmError: Native BGM validation failed (stable codes such as ``bgm_invalid_audio``).
    """
    await asyncio.to_thread(assert_project_migration_ok, project_name)
    return await BgmLibraryService(manager).upload(
        project_name, filename=filename, content=content, change_source=change_source
    )


__all__ = [
    "ALLOWED_EXTENSIONS",
    "BGM_ERROR_STATUS",
    "FORMAL_SHEET_UPLOAD_TYPES",
    "UPLOAD_SPECS",
    "AssetUploadResult",
    "BgmError",
    "ChangeSource",
    "ContentCheck",
    "InstalledProductReference",
    "MetadataSetter",
    "Naming",
    "ProductReferenceUpload",
    "ReferenceImagesChangedError",
    "UploadSpec",
    "UploadTarget",
    "arrange_product_reference_images",
    "bgm_error_message",
    "bgm_view",
    "check_upload_target",
    "install_asset_upload",
    "install_product_reference_images",
    "install_project_bgm",
    "persist_asset_upload",
    "product_reference_ref_id",
]
