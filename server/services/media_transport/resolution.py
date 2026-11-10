"""Resolve a typed media selector to one project-relative media file through native services.

Version-managed kinds (asset sheets, character derivatives, storyboard images, end frames, grid composites, narration
audio, unit videos) read the immutable version snapshot from ``VersionManager`` history, so a pinned version keeps
pointing at the same bytes after the current version moves. When no history exists but a current file is registered
in metadata (asset sheets, derivatives, storyboards, end frames), the registered current file is used with
``version=None`` and the content digest alone pins it. Other kinds resolve through their native owners: product
``reference_images`` and character ``reference_audio`` in project metadata, the ``voice_sample`` task result,
``FinalCutService.status``, the BGM library and the retained Jianying package store.

Resolution is read-only: no task, provider call or metadata write. Results never leave the server with their path."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from lib.artifacts.artifact_manifest import ArtifactStatus
from lib.artifacts.version_manager import UnmanagedSnapshotPathError, VersionManager
from lib.bgm.library import BGM_DIR, read_bgm_library
from lib.edit_timeline import EditTimelineError
from lib.final_cut.basis import video_resource_type_for
from lib.infra.api_errors import ApiError
from lib.project.asset_types import ASSET_SPECS
from lib.project.project_manager import ProjectManager
from lib.project.resource_paths import END_FRAME_RESOURCE_TYPE, resource_relative_path
from lib.script.script_editor import ScriptEditError, resolve_items
from lib.script.storyboard_sequence import find_storyboard_item, get_storyboard_items
from server.services.media_transport import private_store
from server.services.media_transport.errors import (
    MEDIA_MISSING,
    MEDIA_NOT_FOUND,
    MEDIA_PATH_REFUSED,
    MEDIA_VERSION_NOT_FOUND,
    MediaTransportError,
)
from server.services.media_transport.jianying_packages import PACKAGE_AREA, jianying_package_relative_path
from server.services.media_transport.selectors import selector_payload

logger = logging.getLogger(__name__)

_MIME_OVERRIDES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".zip": "application/zip",
}


def media_mime_type(relative_path: str) -> str:
    suffix = PurePosixPath(relative_path).suffix.lower()
    return _MIME_OVERRIDES.get(suffix) or mimetypes.guess_type(relative_path)[0] or "application/octet-stream"


@dataclass(frozen=True, slots=True)
class ResolvedMedia:
    """A resolved media file. ``relative_path`` is project-relative and server-only; ``selector`` has any resolved version pinned."""

    kind: str
    selector: dict[str, Any]
    version: int | None
    relative_path: str
    mime_type: str
    #: Artifact currency for rendered outputs (final_cut: ``current`` or ``stale``); ``None`` for other kinds.
    status: str | None = None


def _not_found(detail: str, **params: Any) -> MediaTransportError:
    return MediaTransportError(MEDIA_NOT_FOUND, detail, **params)


def _missing(detail: str, **params: Any) -> MediaTransportError:
    return MediaTransportError(MEDIA_MISSING, detail, **params)


def _available_versions(versions: VersionManager, resource_type: str, resource_id: str) -> list[int]:
    records = versions.get_versions(resource_type, resource_id).get("versions")
    return [
        record["version"]
        for record in (records if isinstance(records, list) else [])
        if isinstance(record, Mapping) and type(record.get("version")) is int
    ]


def _snapshot_relative(
    versions: VersionManager, project_dir: Path, resource_type: str, resource_id: str, version: int
) -> str | None:
    records = versions.get_versions(resource_type, resource_id).get("versions")
    for record in records if isinstance(records, list) else []:
        if isinstance(record, Mapping) and record.get("version") == version:
            try:
                VersionManager.resolve_snapshot_path(project_dir, resource_type, record.get("file"))
            except UnmanagedSnapshotPathError:
                # The recorded snapshot escapes the project (traversal or a symbolic link pointing outside it).
                raise MediaTransportError(
                    MEDIA_PATH_REFUSED,
                    "media file is outside the project, behind a symbolic link, or not a regular file",
                ) from None
            file = record.get("file")
            return file if isinstance(file, str) else None
    return None


def _versioned(
    project_dir: Path,
    *,
    kind: str,
    selector: dict[str, Any],
    resource_type: str,
    resource_id: str,
    requested: int | None,
    current_pointer: str | None,
) -> ResolvedMedia:
    """Pinned or current version snapshot; otherwise the registered current file without history."""
    versions = VersionManager(project_dir)
    available = _available_versions(versions, resource_type, resource_id)
    version = requested
    if version is None:
        current = versions.get_current_version(resource_type, resource_id)
        version = current if current > 0 else None
    elif version not in available:
        raise MediaTransportError(
            MEDIA_VERSION_NOT_FOUND,
            f"version {version} does not exist",
            available_versions=available,
        )
    if version is not None:
        relative = _snapshot_relative(versions, project_dir, resource_type, resource_id, version)
        if relative is None:
            raise _missing("the version has no readable snapshot", version=version)
        return ResolvedMedia(kind, {**selector, "version": version}, version, relative, media_mime_type(relative))
    if current_pointer:
        return ResolvedMedia(kind, selector, None, current_pointer, media_mime_type(current_pointer))
    raise _missing("no media has been generated or uploaded for this object")


def _load_script(projects: ProjectManager, project_name: str, script: str) -> dict[str, Any]:
    try:
        return projects.load_script_readonly(project_name, script)
    except (FileNotFoundError, ValueError, OSError):
        raise _not_found("script not found", script=script) from None


def _storyboard_item(
    projects: ProjectManager, project_name: str, script: str, item_id: str
) -> tuple[str, dict[str, Any]]:
    try:
        items, id_field, *_ = get_storyboard_items(_load_script(projects, project_name, script))
    except ScriptEditError:
        raise _not_found("script items are unreadable", script=script) from None
    found = find_storyboard_item(items, id_field, item_id)
    if found is None or not isinstance(found[0], dict):
        raise _not_found("storyboard item not found", script=script, item_id=item_id)
    item = found[0]
    return str(item.get(id_field) or item_id), item


def _resolve_sync(projects: ProjectManager, project_name: str, selector: Any) -> ResolvedMedia:
    # Local imports keep this module importable where image-edit task dependencies are heavy.
    from server.services.tasks.image_edit_tasks import edit_version_resource_type, resolve_current_image_pointer

    project_dir = projects.get_project_path(project_name)
    payload = selector_payload(selector)
    kind = selector.kind
    if kind in {"asset_sheet", "character_derivative"}:
        resource_type = selector.asset_type if kind == "asset_sheet" else "character_derivative"
        project = projects.load_project(project_name)
        try:
            resource_id, pointer = resolve_current_image_pointer(project, resource_type, selector.name, None)
        except KeyError:
            raise _not_found("asset not found", name=selector.name) from None
        return _versioned(
            project_dir,
            kind=kind,
            selector=payload,
            resource_type=edit_version_resource_type(resource_type),
            resource_id=resource_id,
            requested=selector.version,
            current_pointer=pointer,
        )
    if kind == "product_reference_image":
        project = projects.load_project(project_name)
        from lib.project.asset_types import resolve_asset_key

        key = resolve_asset_key(project.get("products"), selector.product)
        if key is None:
            raise _not_found("product not found", product=selector.product)
        images = project["products"][key].get("reference_images")
        images = images if isinstance(images, list) else []
        if selector.index >= len(images) or not isinstance(images[selector.index], str) or not images[selector.index]:
            raise _not_found("product reference image index out of range", count=len(images))
        relative = images[selector.index]
        return ResolvedMedia(kind, payload, None, relative, media_mime_type(relative))
    if kind == "character_reference_image":
        project = projects.load_project(project_name)
        from lib.project.asset_types import resolve_asset_key

        key = resolve_asset_key(project.get("characters"), selector.character)
        if key is None:
            raise _not_found("character not found", character=selector.character)
        relative = project["characters"][key].get("reference_image")
        if not isinstance(relative, str) or not relative:
            raise _missing("character has no uploaded reference image", character=selector.character)
        return ResolvedMedia(kind, payload, None, relative, media_mime_type(relative))
    if kind == "style_image":
        relative = projects.load_project(project_name).get("style_image")
        if not isinstance(relative, str) or not relative:
            raise _missing("project has no uploaded style reference image")
        return ResolvedMedia(kind, payload, None, relative, media_mime_type(relative))
    if kind == "storyboard_image":
        project = projects.load_project(project_name)
        script = _load_script(projects, project_name, selector.script)
        try:
            resource_id, pointer = resolve_current_image_pointer(project, "storyboard", selector.item_id, script)
        except (KeyError, ScriptEditError):
            raise _not_found("storyboard item not found", item_id=selector.item_id) from None
        return _versioned(
            project_dir,
            kind=kind,
            selector=payload,
            resource_type="storyboards",
            resource_id=resource_id,
            requested=selector.version,
            current_pointer=pointer,
        )
    if kind == "end_frame":
        resource_id, item = _storyboard_item(projects, project_name, selector.script, selector.item_id)
        pointer = item.get("end_frame_image")
        return _versioned(
            project_dir,
            kind=kind,
            selector=payload,
            resource_type=END_FRAME_RESOURCE_TYPE,
            resource_id=resource_id,
            requested=selector.version,
            current_pointer=pointer if isinstance(pointer, str) and pointer else None,
        )
    if kind == "grid_composite":
        if not (project_dir / "grids" / f"{selector.grid_id}.json").is_file():
            raise _not_found("grid not found", grid_id=selector.grid_id)
        return _versioned(
            project_dir,
            kind=kind,
            selector=payload,
            resource_type="grids",
            resource_id=selector.grid_id,
            requested=selector.version,
            # Same canonical composite as GridManager.image_path when no version history is recorded.
            current_pointer=f"grids/{selector.grid_id}.png",
        )
    if kind == "narration_audio":
        if selector.unit_id.startswith("voice_sample__"):
            raise _not_found("not a narration unit; use kind=voice_sample", unit_id=selector.unit_id)
        versions = VersionManager(project_dir)
        if not _available_versions(versions, "audio", selector.unit_id):
            raise _missing("this unit has no narration audio versions", unit_id=selector.unit_id)
        return _versioned(
            project_dir,
            kind=kind,
            selector=payload,
            resource_type="audio",
            resource_id=selector.unit_id,
            requested=selector.version,
            current_pointer=None,
        )
    if kind == "unit_video":
        script = _load_script(projects, project_name, selector.script)
        try:
            items, id_field, script_kind = resolve_items(script)
        except ScriptEditError:
            raise _not_found("script items are unreadable", script=selector.script) from None
        if not any(isinstance(item, dict) and str(item.get(id_field)) == selector.unit_id for item in items):
            raise _not_found("video unit not found", unit_id=selector.unit_id)
        return _versioned(
            project_dir,
            kind=kind,
            selector=payload,
            resource_type=video_resource_type_for(script_kind),
            resource_id=selector.unit_id,
            requested=selector.version,
            current_pointer=None,
        )
    if kind == "bgm":
        track = read_bgm_library(projects.load_project(project_name)).get(selector.bgm_id)
        if track is None:
            raise _not_found("BGM not found", bgm_id=selector.bgm_id)
        return ResolvedMedia(kind, payload, None, track.file, media_mime_type(track.file))
    if kind == "jianying_package":
        relative, _meta = jianying_package_relative_path(project_dir, selector.package_id)
        return ResolvedMedia(kind, payload, None, relative, "application/zip")
    raise _not_found(f"unsupported media kind {kind}")


async def _resolve_final_cut(projects: ProjectManager, project_name: str, selector: Any) -> ResolvedMedia:
    from lib.final_cut.service import FinalCutService

    try:
        status = await FinalCutService(projects).status(
            project_name, selector.timeline, narration=selector.narration, subtitles=selector.subtitles
        )
    except EditTimelineError:
        raise _not_found("edit timeline not found", timeline=selector.timeline) from None
    if status.status not in {ArtifactStatus.CURRENT, ArtifactStatus.STALE}:
        raise _missing("no final cut has been rendered for this timeline variant", timeline=selector.timeline)
    pinned = {**selector_payload(selector), "narration": status.narration, "subtitles": status.subtitles}
    return ResolvedMedia(
        "final_cut",
        pinned,
        status.version,
        status.artifact_path,
        media_mime_type(status.artifact_path),
        status=str(status.status.value if hasattr(status.status, "value") else status.status),
    )


async def _resolve_voice(projects: ProjectManager, project_name: str, selector: Any, queue: Any) -> ResolvedMedia:
    # Worker C's voice-reference service owns these identities; transport reads only the resolved project-relative file.
    from server.services.voice_references import (
        resolve_character_voice_reference_media,
        resolve_voice_sample_media,
    )

    payload = selector_payload(selector)
    try:
        if selector.kind == "character_voice_reference":
            media = await resolve_character_voice_reference_media(project_name, selector.character, projects=projects)
            if media is None:
                raise _missing("character has no bound reference audio", character=selector.character)
        else:
            media = await resolve_voice_sample_media(project_name, selector.task_id, projects=projects, queue=queue)
    except ApiError as exc:
        # The voice-reference service's stable keys (task_not_found, voice_sample_not_ready, voice_sample_file_missing,
        # voice_sample_content_changed, character_not_found, asset_invalid_name) are relayed as problem codes.
        raise MediaTransportError(exc.key, f"voice media unavailable ({exc.key})") from None
    return ResolvedMedia(selector.kind, payload, None, media.relative_path, media.mime_type)


_VERSIONS_PREFIX = "versions/"
STYLE_IMAGE_STEM = "style_reference"
_STYLE_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
CHARACTER_DERIVATIVE_SUBDIR = resource_relative_path("character_derivatives", "x/y").rsplit("/", 2)[0]

#: Directories each kind may serve from. Metadata pointers (project.json strings, task results) are only trusted inside
#: the canonical directory their native writer uses, so a pointer edited to name ``project.json``, a script, a staged
#: upload or another private record is refused even though it stays inside the project.
_KIND_PREFIXES: dict[str, tuple[str, ...]] = {
    "character_derivative": (f"{CHARACTER_DERIVATIVE_SUBDIR}/", _VERSIONS_PREFIX),
    "product_reference_image": (f"{ASSET_SPECS['product'].subdir}/refs/",),
    # Same directory as the native character_ref upload (server/services/project/asset_uploads.py).
    "character_reference_image": (f"{ASSET_SPECS['character'].subdir}/refs/",),
    # upload_project_style_image writes style_reference<ext> at the project root; nothing else at the root is served.
    "style_image": (f"{STYLE_IMAGE_STEM}.",),
    "character_voice_reference": (f"{ASSET_SPECS['character'].subdir}/refs_audio/",),
    "voice_sample": ("audio/",),
    "storyboard_image": ("storyboards/", _VERSIONS_PREFIX),
    "end_frame": (f"{END_FRAME_RESOURCE_TYPE}/", _VERSIONS_PREFIX),
    "grid_composite": ("grids/", _VERSIONS_PREFIX),
    "narration_audio": (_VERSIONS_PREFIX,),
    "unit_video": (_VERSIONS_PREFIX,),
    "final_cut": ("renders/",),
    "bgm": (f"{BGM_DIR}/",),
    "jianying_package": (f"{private_store.ARCREEL_DIR}/{PACKAGE_AREA}/",),
}


def _allowed_prefixes(selector: Any) -> tuple[str, ...]:
    if selector.kind == "asset_sheet":
        return (f"{ASSET_SPECS[selector.asset_type].subdir}/", _VERSIONS_PREFIX)
    return _KIND_PREFIXES[selector.kind]


def _require_canonical_location(selector: Any, resolved: ResolvedMedia) -> ResolvedMedia:
    """Refuse a resolved path outside the kind's canonical directories, or with any hidden/dot segment.

    The private-store path of a retained Jianying package is the only hidden location served; it is computed by the
    server from a validated package ID, never read from metadata."""
    refused = MediaTransportError(
        MEDIA_PATH_REFUSED, "media file is outside the canonical location for this media kind"
    )
    relative = resolved.relative_path
    if not isinstance(relative, str) or "\\" in relative:
        raise refused
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise refused
    if not any(relative.startswith(prefix) for prefix in _allowed_prefixes(selector)):
        raise refused
    hidden = [part for part in parts[:-1] if part.startswith(".")]
    if selector.kind != "jianying_package" and (hidden or parts[-1].startswith(".")):
        raise refused
    if selector.kind == "style_image" and (
        len(parts) != 1 or PurePosixPath(relative).suffix.lower() not in _STYLE_IMAGE_SUFFIXES
    ):
        raise refused
    if selector.kind == "character_reference_image" and len(parts) != 3:
        # Reference images sit directly in characters/refs/.
        raise refused
    if selector.kind == "asset_sheet" and not relative.startswith(_VERSIONS_PREFIX) and len(parts) != 2:
        # Sheets sit directly in their asset directory, not in refs/, refs_audio/ or derivatives/.
        raise refused
    return resolved


async def resolve_media(projects: ProjectManager, project_name: str, selector: Any, *, queue: Any) -> ResolvedMedia:
    """Resolve ``selector`` in ``project_name``; raises :class:`MediaTransportError` with a stable code."""
    if selector.kind == "final_cut":
        resolved = await _resolve_final_cut(projects, project_name, selector)
    elif selector.kind in {"character_voice_reference", "voice_sample"}:
        resolved = await _resolve_voice(projects, project_name, selector, queue)
    else:
        resolved = await asyncio.to_thread(_resolve_sync, projects, project_name, selector)
    return _require_canonical_location(selector, resolved)


__all__ = ["ResolvedMedia", "media_mime_type", "resolve_media"]
