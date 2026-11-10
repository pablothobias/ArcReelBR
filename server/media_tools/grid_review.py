"""Host-neutral grid composite review tools: list grid records, inspect a composite before splitting, replace it.

These tools never generate, never split and never touch storyboard cells. ``inspect_grid`` returns the
composite as an image content block together with its version and sha256, which ``split_grids`` accepts
as ``reviewed_composites`` so a split only ever applies to the composite the user actually saw.
``replace_grid_composite`` installs a client-supplied composite through the same service as the Web
upload: a new ``grids`` version, split state reset to "awaiting split", cells untouched.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import logging
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from pydantic.json_schema import SkipJsonSchema

from lib.artifacts.version_manager import VersionManager
from lib.final_cut.basis import version_snapshot
from lib.i18n import DEFAULT_LOCALE
from lib.i18n import _ as translate
from lib.infra.api_errors import ApiError
from lib.infra.image_utils import compress_image_bytes
from lib.material.work_files import local_work_files
from lib.script.grid.grid_access import ensure_grid_writable
from lib.script.grid.grid_manager import GridManager
from lib.script.grid.grid_resolution import resolve_image_resolution
from lib.script.grid.layout import large_grid_allowed, max_cell_count
from lib.script.grid.models import GridGeneration
from server.agent_toolset.declaration import ToolImage
from server.media_tools.context import tool_error, tool_problem
from server.services.currency.artifact_version_restore import CurrentVersionChangedError
from server.services.currency.upload_finalize import (
    UploadValidationError,
    validate_upload,
)
from server.services.grid.grid_composite import (
    ensure_grid_idle,
    install_grid_composite,
    load_grid_or_404,
    load_project_for_grid_write,
)
from server.services.grid.grid_submission import GRID_IN_FLIGHT_STATUSES, grid_is_in_flight
from server.services.media_transport import MediaTransportError, discard_staged_upload, resolve_staged_upload
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolRequest, migration_gate

logger = logging.getLogger(__name__)

MAX_COMPOSITE_EDGE = 2000
_JPEG_QUALITY = 85
#: Inline base64 ceiling shared with other byte-accepting tools (~15 MiB of raw image bytes).
MAX_CONTENT_BASE64_CHARS = 20 * 1024 * 1024

type GridState = Literal["generating", "failed", "no_composite", "awaiting_split", "split"]


def _api_problem(exc: ApiError) -> ToolOutcome[Any]:
    """Relay native domain errors in the default language, keeping their i18n keys as problem codes."""
    return tool_problem(translate(exc.key, DEFAULT_LOCALE, **exc.params), code=exc.key, params=exc.params or None)


def _write_block(project: Mapping[str, Any]) -> str | None:
    try:
        ensure_grid_writable(dict(project))
    except ApiError as exc:
        return exc.key
    return None


def grid_state(grid: GridGeneration) -> GridState:
    """Composite lifecycle as the user sees it; ``split`` means cells were saved from the current composite."""
    if grid.status in GRID_IN_FLIGHT_STATUSES:
        return "generating"
    if grid.status == "failed":
        return "failed"
    if not grid.grid_image_path:
        return "no_composite"
    return "split" if grid.split_at else "awaiting_split"


def _grid_summary(grid: GridGeneration, current_version: int) -> dict[str, Any]:
    return {
        "grid_id": grid.id,
        "episode": grid.episode,
        "script_file": grid.script_file,
        "state": grid_state(grid),
        "status": grid.status,
        "scene_ids": list(grid.scene_ids),
        "rows": grid.rows,
        "cols": grid.cols,
        "grid_size": grid.grid_size,
        "split_at": grid.split_at,
        "current_version": current_version or None,
        "created_at": grid.created_at,
    }


# ==================== list_grids ====================


class ListGridsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    episode: StrictInt | SkipJsonSchema[None] = Field(
        default=None, ge=1, description="Only list grids of this episode; omit to list every grid in the project"
    )


async def list_grids(
    request: ToolRequest[ListGridsRequest],
    scope: ProjectScope,
    caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    if (problem := await migration_gate(scope, services)) is not None:
        return ToolOutcome(problem=problem)
    try:

        def read() -> tuple[dict[str, Any], list[tuple[GridGeneration, int]]]:
            project = services.projects.load_project(scope.project_name)
            project_path = services.projects.get_project_path(scope.project_name)
            versions = VersionManager(project_path)
            grids = [
                (grid, versions.get_current_version("grids", grid.id))
                for grid in GridManager(project_path).list_all()
                if request.value.episode is None or grid.episode == request.value.episode
            ]
            return project, grids

        project, grids = await asyncio.to_thread(read)
        allowed = large_grid_allowed(await resolve_image_resolution(services.capabilities, project))
        entries: list[dict[str, Any]] = []
        for grid, current_version in grids:
            entry = _grid_summary(grid, current_version)
            entry["in_flight"] = await grid_is_in_flight(
                grid, queue=services.queue, project_name=scope.project_name, user_id=caller.user_id
            )
            entries.append(entry)
        return ToolOutcome(
            value={
                "capability": {
                    "large_grid_allowed": allowed,
                    "max_cell_count": max_cell_count(allow_large_grid=allowed),
                },
                "writable": _write_block(project) is None,
                "write_block": _write_block(project),
                "grids": entries,
            }
        )
    except Exception as exc:
        return tool_error("list_grids", exc)


def list_grids_summary(value: dict[str, Any]) -> str:
    awaiting = [g["grid_id"] for g in value["grids"] if g["state"] == "awaiting_split"]
    text = f"{len(value['grids'])} grid record(s); max {value['capability']['max_cell_count']} cells per grid"
    return f"{text}; awaiting split after user review: {', '.join(awaiting)}" if awaiting else text


# ==================== inspect_grid ====================


class InspectGridRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    grid_id: str = Field(min_length=1, description="Grid ID, for example grid_a1b2c3d4e5f6")
    version: StrictInt | SkipJsonSchema[None] = Field(
        default=None,
        ge=1,
        description="Composite version to inspect; omit for the current composite. Historical versions are shown for comparison only",
    )


@dataclass(frozen=True, slots=True)
class InspectedGrid:
    record: dict[str, Any]
    jpeg: bytes | None = None


def _composite_bytes(
    project_path: Path, versions: VersionManager, grid: GridGeneration, version: int | None
) -> tuple[bytes | None, Mapping[str, Any]]:
    if version is not None:
        found = version_snapshot(project_path, versions, "grids", grid.id, version)
        if found is None:
            return None, {}
        path, record = found
        return path.read_bytes(), record
    path = GridManager(project_path).image_path(grid.id)
    if not grid.grid_image_path or not path.is_file():
        return None, {}
    return path.read_bytes(), {}


def _image_size(content: bytes) -> tuple[int, int] | None:
    from PIL import Image

    try:
        with Image.open(BytesIO(content)) as image:
            return image.size
    except (OSError, ValueError):
        return None


async def inspect_grid(
    request: ToolRequest[InspectGridRequest],
    scope: ProjectScope,
    caller: CallerContext,
    services: Services,
) -> ToolOutcome[InspectedGrid]:
    grid_id = request.value.grid_id
    if (problem := await migration_gate(scope, services)) is not None:
        return ToolOutcome(problem=problem)
    try:

        def locate() -> tuple[dict[str, Any], Path, GridGeneration, VersionManager, dict[str, Any]]:
            project = services.projects.load_project(scope.project_name)
            project_path = services.projects.get_project_path(scope.project_name)
            grid = load_grid_or_404(project_path, grid_id)
            versions = VersionManager(project_path)
            return project, project_path, grid, versions, versions.get_versions("grids", grid_id)

        try:
            project, project_path, grid, versions, history = await asyncio.to_thread(locate)
        except ApiError as exc:
            return _api_problem(exc)
        records = [r for r in history.get("versions", []) if isinstance(r, Mapping)]
        available = [r["version"] for r in records if isinstance(r.get("version"), int)]
        current_version = int(history.get("current_version") or 0)
        requested = request.value.version
        if requested is not None and requested not in available:
            return tool_problem(
                f"grid {grid_id} has no composite version {requested}",
                code="version_not_found",
                params={"grid_id": grid_id, "available_versions": available},
            )
        shown_version = requested if requested is not None else (current_version or None)
        read_version = requested
        reads: list[str] = []
        if requested is not None:
            record = next(r for r in records if r.get("version") == requested)
            if isinstance(record.get("file"), str):
                reads.append(record["file"])
        elif grid.grid_image_path:
            reads.append(grid.grid_image_path)

        async with local_work_files(project_path, reads):
            content, _record = await asyncio.to_thread(_composite_bytes, project_path, versions, grid, read_version)

        in_flight = await grid_is_in_flight(
            grid, queue=services.queue, project_name=scope.project_name, user_id=caller.user_id
        )
        composite: dict[str, Any] = {
            "version": shown_version,
            "current_version": current_version or None,
            "available_versions": available,
            "is_current": requested is None or requested == current_version,
            "status": "missing",
        }
        version_record = next((r for r in records if r.get("version") == shown_version), None)
        if version_record is not None:
            composite["source"] = version_record.get("source") or "generated"
            composite["created_at"] = version_record.get("created_at")
        jpeg: bytes | None = None
        if content is not None:
            composite["sha256"] = hashlib.sha256(content).hexdigest()
            composite["size_bytes"] = len(content)
            size = await asyncio.to_thread(_image_size, content)
            if size is not None:
                composite["width"], composite["height"] = size
            try:
                jpeg = await asyncio.to_thread(
                    compress_image_bytes, content, max_long_edge=MAX_COMPOSITE_EDGE, quality=_JPEG_QUALITY
                )
                composite["status"] = "ok"
                composite["image"] = 1
            except ValueError:
                composite["status"] = "unreadable"

        cells = [
            {
                "index": cell.index,
                "row": cell.row,
                "col": cell.col,
                "frame_type": cell.frame_type,
                "scene_id": cell.next_scene_id if cell.frame_type != "placeholder" else None,
                "split_image_path": cell.image_path,
            }
            for cell in grid.frame_chain
        ]
        record = _grid_summary(grid, current_version)
        record.update(
            {
                "in_flight": in_flight,
                "cell_count": grid.cell_count,
                "video_aspect_ratio": grid.video_aspect_ratio,
                "error_message": grid.error_message,
                "cells": cells,
                "composite": composite,
                "writable": _write_block(project) is None,
                "write_block": _write_block(project),
            }
        )
        # The guard is offered only for the current composite that split_grids would actually split.
        if composite["is_current"] and "sha256" in composite and not in_flight:
            record["split_guard"] = {"grid_id": grid_id, "sha256": composite["sha256"], "version": shown_version}
        return ToolOutcome(value=InspectedGrid(record=record, jpeg=jpeg))
    except Exception as exc:
        return tool_error("inspect_grid", exc)


def inspect_grid_projection(value: InspectedGrid) -> dict[str, Any]:
    return {"inspect_grid": value.record}


def inspect_grid_images(value: InspectedGrid) -> list[ToolImage]:
    return [ToolImage(data=value.jpeg, mime_type="image/jpeg")] if value.jpeg is not None else []


def inspect_grid_summary(value: InspectedGrid) -> str:
    record = value.record
    composite = record["composite"]
    seen = "composite attached as image 1" if value.jpeg is not None else "no viewable composite"
    return (
        f"Grid {record['grid_id']} ({record['rows']}x{record['cols']}, state {record['state']}), "
        f"composite v{composite['version']}: {seen}. Split only after the user explicitly approves this composite."
    )


# ==================== replace_grid_composite ====================


class ReplaceGridCompositeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    grid_id: str = Field(min_length=1, description="Grid ID whose composite is replaced")
    filename: str = Field(
        min_length=1,
        max_length=255,
        description="Original plain filename with an image extension (.png/.jpg/.jpeg/.webp)",
    )
    content_base64: str | SkipJsonSchema[None] = Field(
        default=None,
        min_length=1,
        max_length=MAX_CONTENT_BASE64_CHARS,
        description="Base64 bytes of the user-approved composite (at most 20 MiB of base64); exclusive with staged_upload_id",
    )
    staged_upload_id: str | SkipJsonSchema[None] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description=(
            "upload_id of a completed begin_media_upload/append_media_upload_chunk staging for this project "
            "(remote MCP only), for composites larger than the inline limit; exclusive with content_base64"
        ),
    )
    expected_current_version: StrictInt | SkipJsonSchema[None] = Field(
        default=None,
        ge=0,
        description="Refuse with version_conflict when the current composite version differs (0 = no composite version yet); protects a composite the user was looking at",
    )

    @model_validator(mode="after")
    def _one_source(self) -> ReplaceGridCompositeRequest:
        if (self.content_base64 is None) == (self.staged_upload_id is None):
            raise ValueError("provide exactly one of content_base64 or staged_upload_id")
        name = self.filename
        if "/" in name or "\\" in name or name in {".", ".."} or "\x00" in name:
            raise ValueError("filename must be a plain filename without directories")
        return self


async def _read_client_bytes(
    scope: ProjectScope, services: Services, value: ReplaceGridCompositeRequest, max_bytes: int
) -> bytes:
    """Inline base64 or a digest-verified staged upload, read up to ``max_bytes + 1`` so oversize is detectable."""
    if value.content_base64 is not None:
        try:
            return await asyncio.to_thread(base64.b64decode, value.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise _ClientBytesProblem("invalid_request", "Invalid base64 content") from exc
    assert value.staged_upload_id is not None
    try:
        staged = await resolve_staged_upload(
            services.projects, scope.project_name, value.staged_upload_id, purposes=("grid_composite",)
        )
    except MediaTransportError as exc:
        raise _ClientBytesProblem(exc.code, exc.detail, exc.params) from exc
    try:
        return await asyncio.to_thread(staged.stream.read, max_bytes + 1)
    finally:
        await asyncio.to_thread(staged.close)


class _ClientBytesProblem(Exception):
    def __init__(self, code: str, detail: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.params = params or None


async def replace_grid_composite(
    request: ToolRequest[ReplaceGridCompositeRequest],
    scope: ProjectScope,
    caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    value = request.value
    try:
        try:
            max_bytes = validate_upload(value.filename, None, kind="image")
        except UploadValidationError as exc:
            return tool_problem(translate(exc.key, DEFAULT_LOCALE, **exc.params), code=exc.key, params=exc.params)
        try:
            content = await _read_client_bytes(scope, services, value, max_bytes)
        except _ClientBytesProblem as exc:
            return tool_problem(exc.detail, code=exc.code, params=exc.params)
        if len(content) > max_bytes:
            return tool_problem(
                "Composite image is too large", code="upload_too_large", params={"max_bytes": max_bytes}
            )

        def prepare() -> tuple[dict[str, Any], Path, GridGeneration, int]:
            project = load_project_for_grid_write(services.projects, scope.project_name)
            project_path = services.projects.get_project_path(scope.project_name)
            grid = load_grid_or_404(project_path, value.grid_id)
            return project, project_path, grid, VersionManager(project_path).get_current_version("grids", grid.id)

        try:
            project, project_path, grid, previous_version = await asyncio.to_thread(prepare)
            if value.expected_current_version is not None and value.expected_current_version != previous_version:
                return _version_conflict(previous_version)
            await ensure_grid_idle(services.queue, scope.project_name, grid, caller.user_id)
            result = await install_grid_composite(
                queue=services.queue,
                project_name=scope.project_name,
                project=project,
                project_path=project_path,
                grid=grid,
                content=content,
                filename=value.filename,
                user_id=caller.user_id,
                change_source="worker",
                # Bind the install to the version observed above; compared again under the versions lock in the commit.
                expected_current_version=previous_version,
            )
        except CurrentVersionChangedError as exc:
            return _version_conflict(exc.actual)
        except ApiError as exc:
            return _api_problem(exc)
        if value.staged_upload_id is not None:
            # Installed: release the staging now; a failed release is left to the staging TTL sweep.
            with suppress(Exception):
                await discard_staged_upload(services.projects, scope.project_name, value.staged_upload_id)

        def installed_digest() -> str | None:
            for record in VersionManager(project_path).get_versions("grids", grid.id).get("versions", []):
                if isinstance(record, Mapping) and record.get("version") == result["version"]:
                    digest = record.get("content_digest")
                    return digest if isinstance(digest, str) else None
            return None

        digest = await asyncio.to_thread(installed_digest)
        return ToolOutcome(
            value={
                "grid_id": grid.id,
                "version": result["version"],
                "previous_version": previous_version or None,
                "sha256": digest,
                "state": "awaiting_split",
                "previous_split_at": grid.split_at,
                "split_reset": True,
                "storyboard_cells_changed": False,
                "artifact_path": result["path"],
                "split_guard": {"grid_id": grid.id, "sha256": digest, "version": result["version"]}
                if digest is not None
                else None,
            }
        )
    except Exception as exc:
        return tool_error("replace_grid_composite", exc)


def _version_conflict(current_version: int) -> ToolOutcome[Any]:
    return tool_problem(
        f"current composite version changed to {current_version}; inspect_grid again and confirm with the user",
        code="version_conflict",
        params={"current_version": current_version},
    )


def replace_grid_composite_summary(value: dict[str, Any]) -> str:
    return (
        f"Grid {value['grid_id']} composite replaced as version {value['version']}; nothing was split and storyboard "
        "cells are unchanged. Show the new composite (inspect_grid) and split only after explicit user approval."
    )


__all__ = [
    "InspectGridRequest",
    "InspectedGrid",
    "ListGridsRequest",
    "ReplaceGridCompositeRequest",
    "grid_state",
    "inspect_grid",
    "inspect_grid_images",
    "inspect_grid_projection",
    "inspect_grid_summary",
    "list_grids",
    "list_grids_summary",
    "replace_grid_composite",
    "replace_grid_composite_summary",
]
