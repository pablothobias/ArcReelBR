"""Install creator-supplied finished media as selected manual-upload versions.

Shared by the Web upload routes (shot storyboard/video, reference-video unit video, character
derivative sheet) and the Agent ``install_finished_media`` tool. Each entry point resolves its target,
stages bytes beside the canonical file and commits through the formal transactions in
:mod:`server.services.currency.upload_finalize`: version history with ``source=manual_upload``,
metadata writeback, manifest claim and the generation-success change event. Nothing here submits
generation work.

Domain failures raise :class:`UploadValidationError` (``key``/``status_code``/``params``) or
``ApiError`` subclasses; callers translate them for their transport.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Literal

from lib.artifacts.version_manager import VersionManager
from lib.infra.api_errors import NotFoundError
from lib.infra.async_thread import run_noninterruptible_sync, run_sync_transaction
from lib.infra.image_utils import normalize_storyboard_upload
from lib.infra.path_safety import PathTraversalError, safe_join
from lib.project.project_change_hints import project_change_source
from lib.project.project_manager import ProjectManager, is_reference_video_project
from lib.project.resource_paths import resource_relative_path
from lib.script.storyboard_sequence import find_storyboard_item, get_storyboard_items
from server.services.currency.upload_finalize import (
    UploadTooLargeError,
    UploadValidationError,
    commit_manual_storyboard_upload,
    commit_manual_video_upload,
    finalize_shot_video_upload,
    install_manual_derivative_upload,
    resolve_derivative_upload_target,
    stage_uploaded_bytes,
    stage_uploaded_video_stream,
    validate_upload,
)
from server.services.tasks.generation_tasks import emit_generation_success_batch
from server.services.tasks.reference_video_tasks import apply_unit_video_assets

ChangeSource = Literal["webui", "worker"]


@dataclass(frozen=True, slots=True)
class InstalledMedia:
    """A committed manual-upload version: canonical project-relative path, selected version and change fingerprints."""

    path: str
    version: int
    asset_fingerprints: dict[str, int] = field(default_factory=dict)
    script_file: str | None = None


def _normalize_png(content: bytes, max_bytes: int) -> bytes:
    if len(content) > max_bytes:
        raise UploadTooLargeError(max_bytes)
    try:
        return normalize_storyboard_upload(content)
    except ValueError as exc:
        raise UploadValidationError("invalid_image_file") from exc


# ---------------------------------------------------------------------------
# Storyboard (image-to-video route) shot storyboard image / video
# ---------------------------------------------------------------------------


def _resolve_shot(
    manager: ProjectManager, project_name: str, script_file: str, shot_id: str, relative_path: str
) -> tuple[Path, VersionManager]:
    # Map missing projects separately; FileNotFoundError from load_script means a missing script.
    try:
        project_path = manager.get_project_path(project_name)
    except FileNotFoundError as exc:
        raise NotFoundError("project_not_found", name=project_name) from exc
    script = manager.load_script(project_name, script_file)
    # reference_video scripts return an empty list → 404; uploads for that mode use reference-video unit uploads.
    items, id_field, _, _, _ = get_storyboard_items(script)
    if find_storyboard_item(items, id_field, shot_id) is None:
        raise UploadValidationError("segment_not_found", status_code=404, id=shot_id)
    # Path traversal guard: absolute paths built from shot_id must stay within the project, matching versions.py.
    try:
        safe_join(project_path, relative_path)
    except PathTraversalError as exc:
        raise UploadValidationError("invalid_resource_id", resource_id=shot_id) from exc
    return project_path, VersionManager(project_path)


async def install_shot_storyboard_image(
    *,
    manager: ProjectManager,
    project_name: str,
    script_file: str,
    shot_id: str,
    filename: str | None,
    content: bytes,
    change_source: ChangeSource,
) -> InstalledMedia:
    """Normalize to PNG and select an uploaded storyboard image for one storyboard-route shot.

    Raises:
        UploadValidationError: Bad extension/size/image, missing shot, unsafe id.
        NotFoundError: Missing project.
        FileNotFoundError: Missing script.
    """
    max_bytes = validate_upload(filename, len(content), kind="image")
    relative_path = resource_relative_path("storyboards", shot_id)
    project_path, versions = await run_sync_transaction(
        _resolve_shot, manager, project_name, script_file, shot_id, relative_path
    )
    target = project_path / relative_path
    png_bytes = await asyncio.to_thread(_normalize_png, content, max_bytes)

    with project_change_source(change_source):
        # Register staged files immediately on persistence; cancellation loses the return value, so reclaim through registration;
        # after successful staging, commit_manual_storyboard_upload finally handles cleanup.
        staged_images: list[Path] = []

        def _stage() -> None:
            staged_images.append(stage_uploaded_bytes(png_bytes, target))

        try:
            await run_sync_transaction(_stage)
        except BaseException:
            for path in staged_images:
                # hard-delete: temp -- staged upload file
                await run_noninterruptible_sync(path.unlink, missing_ok=True)
            raise
        version = await commit_manual_storyboard_upload(
            project_name=project_name,
            script_file=script_file,
            shot_id=shot_id,
            asset_path=relative_path,
            staged_image=staged_images[0],
            current_image=target,
            versions=versions,
            original_filename=filename,
        )
        # emit reads scripts to resolve episodes and computes fingerprints in a worker thread.
        fingerprints = await run_sync_transaction(
            emit_generation_success_batch,
            task_type="storyboard",
            project_name=project_name,
            resource_id=shot_id,
            payload={"script_file": script_file},
        )
    return InstalledMedia(path=relative_path, version=version, asset_fingerprints=fingerprints, script_file=script_file)


async def install_shot_video(
    *,
    manager: ProjectManager,
    project_name: str,
    script_file: str,
    shot_id: str,
    filename: str | None,
    stream: BinaryIO,
    declared_size: int | None,
    change_source: ChangeSource,
) -> InstalledMedia:
    """Stream an uploaded video (mp4/mov/m4v, ≤200 MiB) and select it for one storyboard-route shot.

    Thumbnail, ``video_uri`` reset, version history and manifest claim commit together."""
    max_bytes = validate_upload(filename, declared_size, kind="video")
    relative_path = resource_relative_path("videos", shot_id)
    project_path, versions = await run_sync_transaction(
        _resolve_shot, manager, project_name, script_file, shot_id, relative_path
    )
    target = project_path / relative_path

    with project_change_source(change_source):
        staged_video = await stage_uploaded_video_stream(stream, target, max_bytes=max_bytes)
        version = await finalize_shot_video_upload(
            project_name=project_name,
            script_file=script_file,
            shot_id=shot_id,
            project_path=project_path,
            video_rel=relative_path,
            staged_video=staged_video,
            versions=versions,
            original_filename=filename,
        )
        fingerprints = await run_sync_transaction(
            emit_generation_success_batch,
            task_type="video",
            project_name=project_name,
            resource_id=shot_id,
            payload={"script_file": script_file},
        )
    return InstalledMedia(path=relative_path, version=version, asset_fingerprints=fingerprints, script_file=script_file)


# ---------------------------------------------------------------------------
# Reference-video unit video
# ---------------------------------------------------------------------------


def resolve_reference_episode_script(
    manager: ProjectManager, project_name: str, episode: int, *, readonly: bool = False
) -> tuple[dict, dict, str]:
    """Load project.json and the episode's reference-video script; return (project, script, script_file).

    Raises:
        NotFoundError: Missing project or script.
        UploadValidationError: Episode absent (404) or project not on the reference-video route (409).
    """
    try:
        project = manager.load_project(project_name)
    except FileNotFoundError as exc:
        raise NotFoundError("project_not_found", name=project_name) from exc
    episodes = project.get("episodes") or []
    meta = next((e for e in episodes if e.get("episode") == episode), None)
    if meta is None or not meta.get("script_file"):
        raise UploadValidationError("ref_episode_not_found", status_code=404, episode=episode)
    script_file = meta["script_file"]
    try:
        load = manager.load_script_readonly if readonly else manager.load_script
        script = load(project_name, script_file)
    except FileNotFoundError as exc:
        raise NotFoundError("script_not_found", name=script_file) from exc
    if not is_reference_video_project(project):
        raise UploadValidationError("ref_not_reference_video_mode", status_code=409)
    return project, script, script_file


def _require_unit(script: dict, unit_id: str) -> dict:
    for unit in script.get("video_units") or []:
        if unit.get("unit_id") == unit_id:
            return unit
    raise UploadValidationError("ref_unit_not_found", status_code=404, unit_id=unit_id)


async def install_reference_unit_video(
    *,
    manager: ProjectManager,
    project_name: str,
    episode: int,
    unit_id: str,
    filename: str | None,
    stream: BinaryIO,
    declared_size: int | None,
    change_source: ChangeSource,
) -> InstalledMedia:
    """Stream an uploaded unit clip and select it for one reference-video unit.

    The episode→script binding is re-resolved after staging (uploads can take seconds while the binding
    changes), so metadata lands in the active script. A unit deleted in the narrow window before locked
    writeback raises ``ref_unit_not_found``."""
    max_bytes = validate_upload(filename, declared_size, kind="video")
    relative_path = resource_relative_path("reference_videos", unit_id)

    def _validate_unit() -> tuple[Path, VersionManager]:
        _project, script, _script_file = resolve_reference_episode_script(manager, project_name, episode)
        _require_unit(script, unit_id)
        project_path = manager.get_project_path(project_name)
        try:
            safe_join(project_path, relative_path)
        except PathTraversalError as exc:
            raise UploadValidationError("invalid_resource_id", resource_id=unit_id) from exc
        return project_path, VersionManager(project_path)

    project_path, versions = await run_sync_transaction(_validate_unit)
    target = project_path / relative_path

    with project_change_source(change_source):
        staged_video = await stage_uploaded_video_stream(stream, target, max_bytes=max_bytes)

        def _recheck_binding() -> str:
            _project, script, script_file = resolve_reference_episode_script(manager, project_name, episode)
            _require_unit(script, unit_id)
            return script_file

        try:
            script_file = await run_sync_transaction(_recheck_binding)

            def _commit_metadata(thumb_rel: str | None, on_commit: Callable[[Path], None]) -> None:
                with manager.locked_script(project_name, script_file, validate=False, on_commit=on_commit) as script:
                    apply_unit_video_assets(script, unit_id, video_uri=None, thumb_rel=thumb_rel)

            try:
                version = await commit_manual_video_upload(
                    project_path=project_path,
                    versions=versions,
                    resource_type="reference_videos",
                    resource_id=unit_id,
                    script_file=script_file,
                    staged_video=staged_video,
                    current_video=target,
                    thumbnail_file=project_path / "reference_videos" / "thumbnails" / f"{unit_id}.jpg",
                    thumbnail_rel=f"reference_videos/thumbnails/{unit_id}.jpg",
                    original_filename=filename,
                    commit_metadata=_commit_metadata,
                )
            except KeyError as exc:
                # Unit deleted concurrently between the post-staging binding check and locked writeback.
                raise UploadValidationError("ref_unit_not_found", status_code=404, unit_id=unit_id) from exc
        finally:
            await asyncio.to_thread(staged_video.unlink, missing_ok=True)  # hard-delete: temp -- staged upload file
        fingerprints = await run_sync_transaction(
            emit_generation_success_batch,
            task_type="reference_video",
            project_name=project_name,
            resource_id=unit_id,
            payload={"script_file": script_file},
        )
    return InstalledMedia(path=relative_path, version=version, asset_fingerprints=fingerprints, script_file=script_file)


# ---------------------------------------------------------------------------
# Character derivative sheet
# ---------------------------------------------------------------------------


async def install_derivative_sheet(
    *,
    manager: ProjectManager,
    project_name: str,
    owner_name: str,
    derivative_name: str,
    filename: str | None,
    content: bytes,
    change_source: ChangeSource,
) -> InstalledMedia:
    """Normalize to PNG and select an uploaded finished derivative sheet; the change description is preserved.

    Raises:
        UploadValidationError: Bad extension/size/image.
        NotFoundError: Missing project, base or derivative.
        BadRequestError: Canonical path escapes the project.
    """
    max_bytes = validate_upload(filename, len(content), kind="image")
    upload = await run_sync_transaction(
        resolve_derivative_upload_target, manager, project_name, owner_name, derivative_name
    )
    png_bytes = await asyncio.to_thread(_normalize_png, content, max_bytes)
    with project_change_source(change_source):
        installed = await install_manual_derivative_upload(
            project_name=project_name,
            upload=upload,
            png_bytes=png_bytes,
            original_filename=filename,
            project_manager=manager,
        )
    return InstalledMedia(
        path=upload.target.sheet_path, version=installed.version, asset_fingerprints=installed.asset_fingerprints
    )


__all__ = [
    "InstalledMedia",
    "install_derivative_sheet",
    "install_reference_unit_video",
    "install_shot_storyboard_image",
    "install_shot_video",
    "resolve_reference_episode_script",
]
