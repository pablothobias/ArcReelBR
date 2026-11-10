"""Grid composite record access and manual composite replacement, shared by the Web grid routes and Agent tools.

Replacing a composite installs client bytes as a new ``grids`` version and resets the record to
"composite ready, awaiting split" (``mark_composite_replaced``). It never splits and never touches
storyboard cells: splitting stays a separate action that the user explicitly agrees to.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lib.artifacts.artifact_activation import (
    register_current_resource_artifact,
    resolve_current_resource_artifact_basis,
)
from lib.artifacts.artifact_version_provenance import IMAGE_ARTIFACT_BASIS_FIELD
from lib.artifacts.version_manager import VersionManager
from lib.generation.generation_queue import GenerationQueue
from lib.infra.api_errors import BadRequestError, ConflictError, NotFoundError
from lib.infra.async_thread import run_noninterruptible_sync, run_sync_transaction
from lib.infra.image_utils import MAX_UPLOAD_PIXELS, ImagePixelLimitError, normalize_storyboard_upload
from lib.infra.json_io import domain_error_on_value_error
from lib.material.formal_objects import formal_commit
from lib.project.project_change_hints import ProjectChangeSource, project_change_source
from lib.project.project_manager import ProjectManager
from lib.script.grid.grid_access import ensure_grid_writable
from lib.script.grid.grid_manager import GridManager
from lib.script.grid.layout import video_aspect_ratio_of
from lib.script.grid.models import GridGeneration
from server.services.currency.artifact_version_restore import expected_current_selection
from server.services.currency.upload_finalize import UPLOAD_VERSION_SOURCE, stage_uploaded_bytes
from server.services.grid.grid_submission import grid_is_in_flight, grid_submission_section


def grid_project_path(project_manager: ProjectManager, project_name: str) -> Path:
    try:
        return project_manager.get_project_path(project_name)
    except ValueError as exc:
        raise BadRequestError("invalid_project_name", name=project_name) from exc


def load_grid_or_404(project_path: Path, grid_id: str) -> GridGeneration:
    """Read a grid record by ID; invalid ID formats and missing records both raise ``grid_not_found`` without format details."""
    try:
        grid = GridManager(project_path).get(grid_id)
    except ValueError as exc:
        raise NotFoundError("grid_not_found", grid_id=grid_id) from exc
    if grid is None:
        raise NotFoundError("grid_not_found", grid_id=grid_id)
    return grid


def load_project_for_grid_write(project_manager: ProjectManager, project_name: str) -> dict[str, Any]:
    """Load the project and enforce grid-write gates, sharing ``ensure_grid_writable`` with version restoration."""
    # Corrupt project.json (JSONDecodeError) is not an invalid project name; let callers surface a generic failure.
    with domain_error_on_value_error(lambda _exc: BadRequestError("invalid_project_name", name=project_name)):
        project = project_manager.load_project(project_name)
    ensure_grid_writable(project)
    return project


def grid_write_target(project_manager: ProjectManager, project_name: str) -> tuple[dict[str, Any], Path]:
    """Project and directory for grid writes."""
    project = load_project_for_grid_write(project_manager, project_name)
    return project, project_manager.get_project_path(project_name)


async def ensure_grid_idle(queue: GenerationQueue, project_name: str, grid: GridGeneration, user_id: str) -> None:
    """Reject splitting/uploads for in-flight pending/generating grids: worker completion overwrites composites and
    would race uploads or splits of old content. Only active queued tasks establish in-flight state. User actions
    may take over orphan intermediate records after cancellation, restart loss or enqueue failure."""
    if await grid_is_in_flight(grid, queue=queue, project_name=project_name, user_id=user_id):
        raise ConflictError("grid_generation_in_progress", grid_id=grid.id)


async def install_grid_composite(
    *,
    queue: GenerationQueue,
    project_name: str,
    project: dict[str, Any],
    project_path: Path,
    grid: GridGeneration,
    content: bytes,
    filename: str | None,
    user_id: str,
    change_source: ProjectChangeSource,
    expected_current_version: int | None = None,
) -> dict[str, Any]:
    """Normalize ``content`` and install it as the grid's new current composite version.

    Only normalize format: PNG conversion/EXIF orientation, without resizing or validating rows×cols layout, which
    remains the user's responsibility. Register a new grids version without splitting or touching storyboard cells.
    ``expected_current_version`` (0 = none yet) is compared under the versions lock inside the record transaction and
    raises ``CurrentVersionChangedError`` without writing. Callers validate the byte limit and the grid gates first; this rereads the record and re-probes in-flight state
    inside the grid submission section before committing."""
    grid_id = grid.id
    aspect_ratio = video_aspect_ratio_of(project)
    try:
        png_bytes = await asyncio.to_thread(normalize_storyboard_upload, content, max_long_edge=None)
    except ImagePixelLimitError as exc:
        raise BadRequestError("image_pixels_too_large", max_megapixels=MAX_UPLOAD_PIXELS // 1_000_000) from exc
    except ValueError as exc:
        raise BadRequestError("invalid_image_file") from exc

    # Register staging immediately; cancellation loses staging returns, so finally cleans via registration.
    staged_files: list[Path] = []

    def _stage() -> Path:
        target = GridManager(project_path).image_path(grid_id)
        staged_files.append(stage_uploaded_bytes(png_bytes, target))
        return target

    try:
        with project_change_source(change_source):
            target = await run_sync_transaction(_stage)
        staged_file = staged_files[0]
        async with grid_submission_section(project_name):
            # Enqueueing/record writes share one critical section; reread and probe again after acquiring it
            # to prevent regeneration between an earlier orphan decision and submission.
            current_grid = await asyncio.to_thread(load_grid_or_404, project_path, grid_id)
            await ensure_grid_idle(queue, project_name, current_grid, user_id)

            def _commit() -> int:
                grid_manager = GridManager(project_path)
                versions = VersionManager(project_path)
                version_box: list[int] = []

                def _replace_record(current_grid: GridGeneration) -> None:
                    # Manual replacement equals successful composite output, returning failed records to ready;
                    # changed content clears split_at, marking it awaiting explicit splitting.
                    current_grid.status = "completed"
                    current_grid.error_message = None
                    current_grid.mark_composite_replaced()
                    # Upload layout uses the current project ratio and updates frozen values; retaining old values after
                    # a ratio change would center-crop new images with the old ratio.
                    current_grid.video_aspect_ratio = aspect_ratio

                def _activate() -> None:
                    basis = resolve_current_resource_artifact_basis(
                        project_path,
                        resource_type="grids",
                        resource_id=grid_id,
                    )
                    metadata: dict[str, object] = {"source": UPLOAD_VERSION_SOURCE}
                    if filename:
                        metadata["original_filename"] = filename
                    if basis is not None:
                        metadata[IMAGE_ARTIFACT_BASIS_FIELD] = basis.to_evidence_dict()

                    def _register() -> None:
                        register_current_resource_artifact(
                            project_path,
                            resource_type="grids",
                            resource_id=grid_id,
                            basis=basis,
                        )

                    # Compared under the versions lock inside the grid record transaction: a raise here rolls back the record.
                    with expected_current_selection(versions, "grids", grid_id, expected_current_version):
                        version_box.append(
                            versions.commit_staged_version(
                                resource_type="grids",
                                resource_id=grid_id,
                                prompt="",
                                staged_file=staged_file,
                                current_file=target,
                                on_commit=_register,
                                **metadata,
                            )
                        )

                with project_change_source(change_source):
                    committed = grid_manager.update_formal(grid_id, _replace_record, on_commit=_activate)
                    if committed is None or len(version_box) != 1:
                        raise RuntimeError("grid upload metadata commit skipped staged activation")
                    return version_box[0]

            # Save new versions according to global storage; unconfirmed remote persistence publishes nothing, preserving records/selection.
            async with formal_commit(project_name):
                version = await run_noninterruptible_sync(_commit)

        with project_change_source(change_source):
            from server.services.tasks.generation_tasks import emit_generation_success_batch

            # Reading scripts may persist migrations.
            fingerprints = await run_sync_transaction(
                emit_generation_success_batch,
                task_type="grid",
                project_name=project_name,
                resource_id=grid_id,
                payload={"script_file": grid.script_file},
            )
    finally:
        for path in staged_files:
            await asyncio.to_thread(path.unlink, missing_ok=True)  # hard-delete: temp -- staged upload file

    return {
        "success": True,
        "path": f"grids/{grid_id}.png",
        "version": version,
        "asset_fingerprints": fingerprints,
    }


__all__ = [
    "ensure_grid_idle",
    "grid_project_path",
    "grid_write_target",
    "install_grid_composite",
    "load_grid_or_404",
    "load_project_for_grid_write",
]
