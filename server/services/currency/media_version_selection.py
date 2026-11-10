"""Media version listing and current-version selection shared by the Web version routes and Agent tools.

Selection installs a recorded version snapshot as the current media file inside the same metadata
transaction that rewrites its owner (asset sheet pointer, storyboard pointer, derivative pointer,
grid record, or typed script/Manifest descriptor). It never regenerates media and never simulates a
restore by re-uploading bytes, so provenance, manual-record policy and Manifest claims stay intact.

Typed media (narration audio, videos) delegate to :mod:`server.services.currency.typed_media_restore`.
Grid composites reset their record's split state and never split: splitting stays an explicit action.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from lib.artifacts.artifact_activation import (
    forget_current_resource_artifact,
    forget_unbound_grid_artifacts,
    forget_unbound_storyboard_artifacts,
    register_current_resource_artifact,
)
from lib.artifacts.artifact_version_provenance import parse_image_version_basis
from lib.artifacts.formal_write import project_metadata_lock
from lib.artifacts.version_manager import MANUAL_UPLOAD_VERSION_SOURCE, VersionManager
from lib.generation.generation_queue import GenerationQueue
from lib.infra.api_errors import BadRequestError
from lib.infra.async_thread import run_sync_transaction
from lib.material.work_files import local_work_files
from lib.project.asset_derivatives import DERIVATIVE_TASK_TYPE, DerivativeSheetTarget, split_derivative_artifact_id
from lib.project.project_change_hints import ProjectChangeSource, project_change_source
from lib.project.project_manager import ProjectManager
from lib.project.resource_paths import CHARACTER_DERIVATIVE_RESOURCE_TYPE
from lib.script.grid.grid_access import ensure_grid_writable
from server.services.currency.artifact_version_restore import (
    CurrentVersionChangedError,
    expected_current_selection,
    is_typed_media_restore_resource,
    is_typed_media_version_restorable,
)
from server.services.currency.typed_media_restore import resolve_media_file, restore_typed_media_resource
from server.services.presentation.presentation_read_model import is_presentation_version_available
from server.services.tasks.derivative_sheet_tasks import point_derivative_at_sheet

logger = logging.getLogger(__name__)

# Restorable resource types are API policy; lib.project.resource_paths defines paths. Allow only types
# with post-restoration metadata synchronization. Grid restoration replaces composites and resets split
# state only, without splitting/touching storyboards; explicit grid splitting assigns cells.
RESTORABLE_RESOURCE_TYPES = frozenset(
    {
        "storyboards",
        "videos",
        "audio",
        "characters",
        "scenes",
        "props",
        "products",
        "reference_videos",
        "grids",
        CHARACTER_DERIVATIVE_RESOURCE_TYPE,
    }
)

# resource_type (plural URL segment) → asset_type (singular ASSET_SPECS key).
RESOURCE_TO_ASSET_TYPE: dict[str, str] = {
    "characters": "character",
    "scenes": "scene",
    "props": "prop",
    "products": "product",
}
# Asset/derivative/storyboard images restored to manual-upload records register basis from uploaded bytes.
_UPLOAD_CLAIMED_RESOURCE_TYPES = frozenset({*RESOURCE_TO_ASSET_TYPE, CHARACTER_DERIVATIVE_RESOURCE_TYPE, "storyboards"})


def resolve_restorable_resource_path(
    resource_type: str,
    resource_id: str,
    project_path: Path,
) -> tuple[Path, str]:
    """Return (current_file_absolute, relative_file_path); raise domain exceptions for unrestorable types or out-of-bounds IDs."""
    if resource_type not in RESTORABLE_RESOURCE_TYPES:
        raise BadRequestError("unsupported_resource_type", resource_type=resource_type)
    return resolve_media_file(resource_type, resource_id, project_path)


def sync_grid_record(
    project_path: Path,
    resource_id: str,
    *,
    on_commit: Callable[[], None] | None = None,
    on_miss: Callable[[], None] | None = None,
) -> None:
    """Reset grid records after restoring composites: historical content replaces current, so old split results no longer match.

    Change only grid split_at/failure state, without synchronizing scripts/storyboards; splitting requires explicit endpoint execution.
    Retain frame_chain unchanged. Skip missing/corrupt records as best effort because composite restoration already succeeded.

    Restoration has no in-flight gate, like storyboard restoration. ``GridGeneration.mark_composite_replaced`` retains
    in-flight state during generation rather than falsely marking the record idle."""
    from lib.script.grid.grid_manager import GridManager

    manager = GridManager(project_path)
    manager.update_formal(
        resource_id,
        lambda grid: grid.mark_composite_replaced(),
        on_commit=on_commit,
        on_miss=on_miss,
        ignore_invalid=True,
    )


def commit_non_typed_restore_claim(
    *,
    resource_type: str,
    resource_id: str,
    file_path: str,
    project_path: Path,
    record: Mapping[str, Any] | None,
    owner_present: bool,
) -> None:
    """Apply the claim half of a non-typed restore inside its metadata locks."""

    if not owner_present:
        if resource_type == "storyboards":
            forget_unbound_storyboard_artifacts(project_path, resource_id)
        elif resource_type == "grids":
            forget_unbound_grid_artifacts(project_path, resource_id)
        else:
            forget_current_resource_artifact(
                project_path,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        return

    if resource_type in _UPLOAD_CLAIMED_RESOURCE_TYPES and (record or {}).get("source") == MANUAL_UPLOAD_VERSION_SOURCE:
        # For restored finished asset/derivative images, uploaded/library-applied, or uploaded storyboards,
        # the upload record is selected; project basis from its bytes, forgetting basis if projection fails.
        register_current_resource_artifact(
            project_path,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return

    try:
        basis = parse_image_version_basis(resource_type, resource_id, record or {})
    except (TypeError, ValueError):
        basis = None
    if basis is None:
        forget_current_resource_artifact(
            project_path,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return
    register_current_resource_artifact(
        project_path,
        resource_type=resource_type,
        resource_id=resource_id,
        artifact_path=file_path,
        basis=basis,
    )


def restore_non_typed_version(
    *,
    project_manager: ProjectManager,
    versions: VersionManager,
    resource_type: str,
    project_name: str,
    resource_id: str,
    version: int,
    current_file: Path,
    file_path: str,
    project_path: Path,
    change_source: ProjectChangeSource = "webui",
    expected_current_version: int | None = None,
) -> dict[str, Any]:
    """Restore metadata → version bytes/pointer → claim in canonical lock order.

    ``expected_current_version`` is compared under the versions lock inside the metadata transaction and raises
    :class:`CurrentVersionChangedError` (nothing written) when another commit changed current meanwhile.

    Asset rename, grid split, formal generation, and typed restore all acquire
    script/file/project locks before the versions lock. Non-typed restore enters
    the same metadata transaction first so none of those paths can form an ABBA
    cycle while their nested rollback scopes remain intact.
    """

    restored: list[dict[str, Any]] = []

    def _restore(*, owner_present: bool) -> None:
        def _commit_claim(record: dict[str, Any]) -> None:
            commit_non_typed_restore_claim(
                resource_type=resource_type,
                resource_id=resource_id,
                file_path=file_path,
                project_path=project_path,
                record=record,
                owner_present=owner_present,
            )

        with expected_current_selection(versions, resource_type, resource_id, expected_current_version):
            restored.append(
                versions.restore_version(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    version=version,
                    current_file=current_file,
                    on_restore=_commit_claim,
                )
            )

    if resource_type == "storyboards":
        scripts_dir = project_path / "scripts"
        script_names = [path.name for path in sorted(scripts_dir.glob("*.json"))] if scripts_dir.exists() else []
        with project_change_source(change_source):
            project_manager.update_scene_asset_across_scripts(
                project_name,
                script_names,
                resource_id,
                "storyboard_image",
                file_path,
                on_commit=lambda: _restore(owner_present=True),
                on_miss=lambda: _restore(owner_present=False),
            )
    elif resource_type == CHARACTER_DERIVATIVE_RESOURCE_TYPE:
        owner_key, derivative_key = split_derivative_artifact_id(resource_id)
        try:
            with project_change_source(change_source):
                point_derivative_at_sheet(
                    project_name=project_name,
                    target=DerivativeSheetTarget(owner_key=owner_key, derivative_key=derivative_key),
                    on_commit=lambda _project_file: _restore(owner_present=True),
                    project_manager=project_manager,
                )
        except KeyError:
            with project_metadata_lock(project_path):
                _restore(owner_present=False)
    elif (asset_type := RESOURCE_TO_ASSET_TYPE.get(resource_type)) is not None:
        try:
            with project_change_source(change_source):
                project_manager._update_asset_sheet(
                    asset_type,
                    project_name,
                    resource_id,
                    file_path,
                    on_commit=lambda _project_file: _restore(owner_present=True),
                )
        except KeyError:
            with project_metadata_lock(project_path):
                _restore(owner_present=False)
    elif resource_type == "grids":
        with project_change_source(change_source):
            sync_grid_record(
                project_path,
                resource_id,
                on_commit=lambda: _restore(owner_present=True),
                on_miss=lambda: _restore(owner_present=False),
            )
    else:
        with project_metadata_lock(project_path):
            _restore(owner_present=True)

    if len(restored) != 1:
        raise RuntimeError("non-typed restore metadata transaction skipped version selection")
    return restored[0]


# Queue task types whose completion writes a new current file for each resource type. ``image_edit``
# shares one task type across images and is additionally keyed by its singular resource_type.
_WRITER_TASK_TYPES: dict[str, tuple[str, ...]] = {
    "characters": ("character",),
    "scenes": ("scene",),
    "props": ("prop",),
    "products": ("product",),
    CHARACTER_DERIVATIVE_RESOURCE_TYPE: (DERIVATIVE_TASK_TYPE,),
    "storyboards": ("storyboard",),
    "grids": ("grid",),
    "audio": ("tts",),
}
_IMAGE_EDIT_RESOURCE_TYPES: dict[str, str] = {
    "characters": "character",
    "scenes": "scene",
    "props": "prop",
    "products": "product",
    CHARACTER_DERIVATIVE_RESOURCE_TYPE: DERIVATIVE_TASK_TYPE,
    "storyboards": "storyboard",
}
_ACTIVE_STATUSES = ("queued", "running")
_TASK_PAGE_SIZE = 200


async def active_media_writer_tasks(
    queue: GenerationQueue,
    *,
    project_name: str,
    resource_type: str,
    resource_id: str,
) -> list[str]:
    """Task IDs of queued/running tasks whose completion would replace this resource's current media.

    Selecting a version while such a task is active would be overwritten (or contradicted) by its commit,
    so Agent selection refuses instead. This is a point-in-time probe: image tasks do not take the
    per-unit admission lock, so a task enqueued right after the probe is not excluded.
    """

    task_types = list(_WRITER_TASK_TYPES.get(resource_type, ()))
    edit_type = _IMAGE_EDIT_RESOURCE_TYPES.get(resource_type)
    if edit_type is not None:
        task_types.append("image_edit")
    found: list[str] = []
    for task_type in task_types:
        for status in _ACTIVE_STATUSES:
            page = 1
            while True:
                listing = await queue.list_tasks(
                    project_name=project_name,
                    status=status,
                    task_type=task_type,
                    page=page,
                    page_size=_TASK_PAGE_SIZE,
                )
                items = listing.get("items") or []
                for task in items:
                    if str(task.get("resource_id") or "") != resource_id:
                        continue
                    if task_type == "image_edit" and (task.get("resource_type") or "") != edit_type:
                        continue
                    found.append(str(task.get("task_id")))
                if len(items) < _TASK_PAGE_SIZE:
                    break
                page += 1
    return list(dict.fromkeys(found))


def describe_resource_versions(versions: VersionManager, resource_type: str, resource_id: str) -> dict[str, Any]:
    """Version list with per-record restorability and presentation availability (synchronous; call in a worker thread)."""
    versions_info = versions.get_versions(resource_type, resource_id)
    for record in versions_info.get("versions", []):
        if isinstance(record, dict):
            record["restorable"] = is_typed_media_version_restorable(resource_type, record)
            record["presentation_available"] = is_presentation_version_available(resource_type, record)
    return {"resource_type": resource_type, "resource_id": resource_id, **versions_info}


async def read_media_versions(versions: VersionManager, resource_type: str, resource_id: str) -> dict[str, Any]:
    """List versions; invalid requests (such as corrupt versions.json) map to ``request_invalid`` without leaking paths."""
    try:
        return await asyncio.to_thread(describe_resource_versions, versions, resource_type, resource_id)
    except ValueError as e:
        # Invalid project names, corrupt versions.json and other bad requests may put paths in str(e); log only.
        logger.warning("版本查询请求非法: %s", e)
        raise BadRequestError("request_invalid") from e


async def restore_media_version(
    *,
    project_manager: ProjectManager,
    versions: VersionManager,
    project_name: str,
    resource_type: str,
    resource_id: str,
    version: int,
    change_source: ProjectChangeSource = "webui",
    expected_current_version: int | None = None,
) -> dict[str, Any]:
    """Select ``version`` as current for one media resource, through the same transaction for every entry point.

    Typed media (audio / videos / reference_videos) use the typed descriptor restore with its admission guard
    and active-TTS conflict check. Image resources rewrite their owner metadata and Manifest claim; grids also
    require grid write admission and reset split state without splitting."""
    try:
        if is_typed_media_restore_resource(resource_type):
            with project_change_source(change_source):
                return await restore_typed_media_resource(
                    project_manager=project_manager,
                    versions=versions,
                    project_name=project_name,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    version=version,
                    expected_current_version=expected_current_version,
                )

        def _locate() -> tuple[Path, str | None]:
            project_path = project_manager.get_project_path(project_name)
            records = versions.get_versions(resource_type, resource_id)["versions"]
            record = next((item for item in records if item.get("version") == version), None)
            file = record.get("file") if isinstance(record, dict) else None
            return project_path, file if isinstance(file, str) else None

        # Locate the snapshot to restore; register use throughout retrieval and restoration.
        project_path, file = await asyncio.to_thread(_locate)

        def _sync() -> dict[str, Any]:
            # Restoration also writes composites, restoring historical content and resetting grid records,
            # so share regeneration/split/upload admission; omission would let blocked projects bypass via restoration.
            if resource_type == "grids":
                ensure_grid_writable(project_manager.load_project(project_name))

            current_file, file_path = resolve_restorable_resource_path(resource_type, resource_id, project_path)

            result = restore_non_typed_version(
                project_manager=project_manager,
                versions=versions,
                resource_type=resource_type,
                project_name=project_name,
                resource_id=resource_id,
                version=version,
                current_file=current_file,
                file_path=file_path,
                project_path=project_path,
                change_source=change_source,
                expected_current_version=expected_current_version,
            )

            # Compute the restored file fingerprint.
            asset_fingerprints: dict[str, int] = {}
            if current_file.exists():
                asset_fingerprints[file_path] = current_file.stat().st_mtime_ns

            return {
                "success": True,
                **result,
                "file_path": file_path,
                "asset_fingerprints": asset_fingerprints,
            }

        async with local_work_files(project_path, [file] if file is not None else []):
            return await run_sync_transaction(_sync)

    except ValueError as e:
        # Invalid project names/out-of-bounds resource_id may put paths in str(e); log only.
        logger.warning("版本还原请求非法: %s", e)
        raise BadRequestError("request_invalid") from e


__all__ = [
    "RESOURCE_TO_ASSET_TYPE",
    "RESTORABLE_RESOURCE_TYPES",
    "CurrentVersionChangedError",
    "active_media_writer_tasks",
    "commit_non_typed_restore_claim",
    "describe_resource_versions",
    "read_media_versions",
    "resolve_restorable_resource_path",
    "restore_media_version",
    "restore_non_typed_version",
    "sync_grid_record",
]
