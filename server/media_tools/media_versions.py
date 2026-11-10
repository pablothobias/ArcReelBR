"""Host-neutral tools to list and select current versions of images, grid composites and narration audio.

Selection reuses the Web version-restore transaction
(:func:`server.services.currency.media_version_selection.restore_media_version`): it rewrites the owner
metadata, the version pointer and the Artifact Manifest claim together, honours the manual-upload record
policy, and never regenerates or re-uploads bytes. Video selection stays with ``select_video_version``;
``inspect_images``/``inspect_grid`` only look at versions. Restoring a grid composite resets its split
state and never splits. Character voice samples follow their own lifecycle and are not handled here.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt
from pydantic.json_schema import SkipJsonSchema

from lib.artifacts.artifact_currency import active_artifact_currency_resolver, resolve_artifact_episode
from lib.artifacts.artifact_manifest import ArtifactKey
from lib.artifacts.artifact_version_provenance import IMAGE_ARTIFACT_BASIS_FIELD
from lib.artifacts.version_manager import MANUAL_UPLOAD_VERSION_SOURCE, VersionManager
from lib.generation.generation_result import observe_artifact_status
from lib.i18n import DEFAULT_LOCALE
from lib.i18n import _ as translate
from lib.infra.api_errors import ApiError
from lib.project.asset_derivatives import DERIVATIVE_TASK_TYPE
from lib.project.resource_paths import CHARACTER_DERIVATIVE_RESOURCE_TYPE, resource_relative_path
from lib.script.grid.grid_access import ensure_grid_writable
from lib.script.grid.grid_manager import GridManager
from lib.script.script_editor import ScriptEditError, resolve_items
from lib.script.storyboard_sequence import get_storyboard_items
from server.media_tools.context import tool_error, tool_problem
from server.services.currency.media_version_selection import (
    CurrentVersionChangedError,
    active_media_writer_tasks,
    describe_resource_versions,
    restore_media_version,
)
from server.services.grid.grid_submission import grid_is_in_flight
from server.services.tasks.image_edit_tasks import resolve_current_image_pointer
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolRequest, migration_gate

logger = logging.getLogger(__name__)

type MediaVersionKind = Literal[
    "character",
    "scene",
    "prop",
    "product",
    "character_derivative",
    "storyboard",
    "grid_composite",
    "narration_audio",
]

#: Selector kind → VersionManager resource type.
KIND_RESOURCE_TYPES: dict[str, str] = {
    "character": "characters",
    "scene": "scenes",
    "prop": "props",
    "product": "products",
    "character_derivative": CHARACTER_DERIVATIVE_RESOURCE_TYPE,
    "storyboard": "storyboards",
    "grid_composite": "grids",
    "narration_audio": "audio",
}
_ASSET_KINDS = frozenset({"character", "scene", "prop", "product"})
#: Version-record provenance fields safe to expose (no filesystem paths).
_PROVENANCE_FIELDS = (
    "source",
    "provider",
    "model",
    "grid_id",
    "original_filename",
    "task_id",
    "duration_seconds",
)
_PROMPT_PREVIEW_CHARS = 400

_ID_DESCRIPTION = (
    "Resource identity: asset name for character/scene/prop/product; base name/derivative name for character_derivative; "
    "storyboard ID (for example E1S05) for storyboard; grid_id for grid_composite; narration unit ID (segment ID, for example E1S05) for narration_audio"
)


@dataclass(frozen=True, slots=True)
class MediaTarget:
    """A resolved, existing selection target."""

    kind: str
    resource_type: str
    resource_id: str
    episode: int | None = None
    script_file: str | None = None
    #: Item fields used to find dependents (storyboard/audio unit item).
    item: Mapping[str, Any] | None = None


class MediaTargetNotFoundError(LookupError):
    pass


def _scan_items(services: Services, project_name: str, project: Mapping[str, Any], kind: str, item_id: str):
    for script_name in sorted(services.projects.list_scripts(project_name)):
        try:
            script = services.projects.load_script_readonly(project_name, script_name)
            if kind == "storyboard":
                items, id_field, *_ = get_storyboard_items(script)
            else:
                items, id_field, _kind = resolve_items(script)
        except (ScriptEditError, ValueError, OSError):
            logger.warning("Skipping unreadable script while resolving a media version target: %s", script_name)
            continue
        for item in items:
            if isinstance(item, dict) and str(item.get(id_field)) == item_id:
                try:
                    episode = resolve_artifact_episode(project=project, script=script, script_filename=script_name)
                except ValueError:
                    episode = None
                return script_name, episode, item
    return None


def resolve_media_target(services: Services, project_name: str, kind: str, item_id: str) -> MediaTarget:
    """Resolve a selector to an existing owner and its canonical version identity (synchronous).

    D1's ``describe_media`` may reuse this for ``asset_sheet``/``character_derivative``/``storyboard_image``/
    ``grid_composite``/``narration_audio`` selectors. Raises :class:`MediaTargetNotFoundError` when absent."""

    resource_type = KIND_RESOURCE_TYPES[kind]
    project = services.projects.load_project(project_name)
    if kind in _ASSET_KINDS or kind == "character_derivative":
        singular = DERIVATIVE_TASK_TYPE if kind == "character_derivative" else kind
        try:
            canonical, _pointer = resolve_current_image_pointer(project, singular, item_id, None)
        except KeyError as exc:
            raise MediaTargetNotFoundError(item_id) from exc
        return MediaTarget(kind=kind, resource_type=resource_type, resource_id=canonical)
    if kind == "grid_composite":
        project_path = services.projects.get_project_path(project_name)
        try:
            grid = GridManager(project_path).get(item_id)
        except ValueError as exc:
            raise MediaTargetNotFoundError(item_id) from exc
        if grid is None:
            raise MediaTargetNotFoundError(item_id)
        return MediaTarget(
            kind=kind,
            resource_type=resource_type,
            resource_id=grid.id,
            episode=grid.episode,
            script_file=grid.script_file,
        )
    found = _scan_items(services, project_name, project, kind, item_id)
    if found is None:
        raise MediaTargetNotFoundError(item_id)
    script_name, episode, item = found
    return MediaTarget(
        kind=kind,
        resource_type=resource_type,
        resource_id=item_id,
        episode=episode,
        script_file=script_name,
        item=item,
    )


def _version_entry(resource_type: str, record: Mapping[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "version": record.get("version"),
        "is_current": bool(record.get("is_current")),
        "created_at": record.get("created_at"),
        "restorable": bool(record.get("restorable", True)),
    }
    for name in _PROVENANCE_FIELDS:
        if record.get(name) is not None:
            entry[name] = record[name]
    entry.setdefault("source", "generated")
    if isinstance(record.get("content_digest"), str):
        entry["sha256"] = record["content_digest"]
    prompt = record.get("prompt")
    if isinstance(prompt, str) and prompt:
        entry["prompt"] = prompt if len(prompt) <= _PROMPT_PREVIEW_CHARS else prompt[:_PROMPT_PREVIEW_CHARS] + "…"
    if resource_type == "audio":
        entry["presentation_available"] = bool(record.get("presentation_available"))
    # Whether selecting this version keeps a verifiable Manifest claim: images need a recorded basis or a manual-upload
    # record; typed audio needs its complete descriptor. Selecting an unverifiable image drops the claim (status missing).
    entry["provenance_verified"] = (
        bool(record.get("restorable"))
        if resource_type == "audio"
        else IMAGE_ARTIFACT_BASIS_FIELD in record or record.get("source") == MANUAL_UPLOAD_VERSION_SOURCE
    )
    return entry


def _artifact_key(target: MediaTarget) -> ArtifactKey | None:
    try:
        if target.kind in _ASSET_KINDS:
            return ArtifactKey.asset_sheet(target.kind, target.resource_id)
        if target.episode is None:
            return None
        if target.kind == "storyboard":
            return ArtifactKey.episode_storyboard(target.episode, target.resource_id)
        if target.kind == "grid_composite":
            return ArtifactKey.episode_grid(target.episode, target.resource_id)
        if target.kind == "narration_audio":
            return ArtifactKey.episode_audio(target.episode, target.resource_id)
    except ValueError:
        return None
    return None


def _status_value(status: Any) -> str | None:
    return None if status is None else str(getattr(status, "value", status))


def _currency_signals(services: Services, project_name: str, target: MediaTarget) -> dict[str, Any]:
    """Native currency of the selected artifact and of direct dependents that may now be stale (synchronous)."""

    project = services.projects.load_project(project_name)
    project_path = services.projects.get_project_path(project_name)
    try:
        resolver = active_artifact_currency_resolver(project_path, project)
    except Exception as exc:
        return {"artifact_status": None, "currency_unavailable": type(exc).__name__}
    artifact_path = resource_relative_path(target.resource_type, target.resource_id)
    status, _blocker = observe_artifact_status(
        resolver=resolver, key=_artifact_key(target), artifact_path=artifact_path
    )
    signals: dict[str, Any] = {"artifact_path": artifact_path, "artifact_status": _status_value(status)}
    dependents: list[dict[str, Any]] = []
    if target.kind == "storyboard" and target.item is not None and target.episode is not None:
        video = (target.item.get("generated_assets") or {}).get("video_clip")
        if isinstance(video, str) and video:
            video_status, _ = observe_artifact_status(
                resolver=resolver,
                key=ArtifactKey.episode_video(target.episode, target.resource_id),
                artifact_path=video,
            )
            dependents.append({"kind": "unit_video", "id": target.resource_id, "status": _status_value(video_status)})
    elif target.kind in _ASSET_KINDS:
        dependents.extend(_asset_storyboard_dependents(services, project_name, project, resolver, target))
    signals["dependents"] = dependents
    signals["stale_dependents"] = [d["id"] for d in dependents if d["status"] == "stale"]
    return signals


def _asset_storyboard_dependents(
    services: Services, project_name: str, project: Mapping[str, Any], resolver: Any, target: MediaTarget
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for script_name in sorted(services.projects.list_scripts(project_name)):
        try:
            script = services.projects.load_script_readonly(project_name, script_name)
            items, id_field, char_field, scene_field, prop_field = get_storyboard_items(script)
            episode = resolve_artifact_episode(project=project, script=script, script_filename=script_name)
        except (ScriptEditError, ValueError, OSError):
            continue
        field_name = {
            "character": char_field,
            "scene": scene_field,
            "prop": prop_field,
            "product": "products_in_shot",
        }[target.kind]
        for item in items:
            if not isinstance(item, dict):
                continue
            names = item.get(field_name) or []
            if not isinstance(names, list) or target.resource_id not in names:
                continue
            pointer = (item.get("generated_assets") or {}).get("storyboard_image")
            if not isinstance(pointer, str) or not pointer:
                continue
            item_id = str(item.get(id_field))
            status, _ = observe_artifact_status(
                resolver=resolver,
                key=ArtifactKey.episode_storyboard(episode, item_id),
                artifact_path=pointer,
            )
            out.append({"kind": "storyboard", "id": item_id, "status": _status_value(status)})
    return out


def _api_problem(exc: ApiError, params: dict[str, Any] | None = None) -> ToolOutcome[Any]:
    merged = {**(exc.params or {}), **(params or {})} or None
    return tool_problem(translate(exc.key, DEFAULT_LOCALE, **exc.params), code=exc.key, params=merged)


def _version_conflict(current_version: int) -> ToolOutcome[Any]:
    return tool_problem(
        f"current version changed to {current_version}; list versions again and confirm with the user",
        code="version_conflict",
        params={"current_version": current_version},
    )


def _not_found(kind: str, item_id: str) -> ToolOutcome[Any]:
    return tool_problem(
        f"{kind} '{item_id}' does not exist in this project",
        code="resource_not_found",
        params={"kind": kind, "id": item_id},
    )


# ==================== list_media_versions ====================


class ListMediaVersionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: MediaVersionKind = Field(description="Media kind whose versions to list")
    id: str = Field(min_length=1, description=_ID_DESCRIPTION)


async def list_media_versions(
    request: ToolRequest[ListMediaVersionsRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    kind, item_id = request.value.kind, request.value.id
    if (problem := await migration_gate(scope, services)) is not None:
        return ToolOutcome(problem=problem)
    try:

        def read() -> dict[str, Any] | None:
            try:
                target = resolve_media_target(services, scope.project_name, kind, item_id)
            except MediaTargetNotFoundError:
                return None
            versions = VersionManager(services.projects.get_project_path(scope.project_name))
            info = describe_resource_versions(versions, target.resource_type, target.resource_id)
            records = [r for r in info.get("versions", []) if isinstance(r, Mapping)]
            value: dict[str, Any] = {
                "kind": kind,
                "id": target.resource_id,
                "current_version": info.get("current_version") or None,
                "versions": [_version_entry(target.resource_type, r) for r in records],
            }
            value.update(_currency_signals(services, scope.project_name, target))
            return value

        try:
            value = await asyncio.to_thread(read)
        except ApiError as exc:
            return _api_problem(exc)
        if value is None:
            return _not_found(kind, item_id)
        return ToolOutcome(value=value)
    except Exception as exc:
        return tool_error("list_media_versions", exc)


def list_media_versions_summary(value: dict[str, Any]) -> str:
    return (
        f"{value['kind']} {value['id']}: {len(value['versions'])} version(s), current v{value['current_version']}"
        if value["current_version"]
        else f"{value['kind']} {value['id']}: no recorded versions"
    )


# ==================== select_media_version ====================


class SelectMediaVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: MediaVersionKind = Field(description="Media kind whose current version to select")
    id: str = Field(min_length=1, description=_ID_DESCRIPTION)
    version: StrictInt = Field(ge=1, description="Recorded version number to make current (from list_media_versions)")
    expected_current_version: StrictInt | SkipJsonSchema[None] = Field(
        default=None,
        ge=0,
        description="Refuse with version_conflict when the current version differs (0 = no current version); use the current_version you showed the user",
    )


async def select_media_version(
    request: ToolRequest[SelectMediaVersionRequest],
    scope: ProjectScope,
    caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    value = request.value
    kind, item_id = value.kind, value.id
    try:

        def prepare() -> tuple[MediaTarget, Path, list[int], int, dict[str, Any]] | None:
            try:
                target = resolve_media_target(services, scope.project_name, kind, item_id)
            except MediaTargetNotFoundError:
                return None
            project_path = services.projects.get_project_path(scope.project_name)
            info = VersionManager(project_path).get_versions(target.resource_type, target.resource_id)
            available = [
                r["version"]
                for r in info.get("versions", [])
                if isinstance(r, Mapping) and isinstance(r.get("version"), int)
            ]
            grid_state: dict[str, Any] = {}
            if kind == "grid_composite":
                ensure_grid_writable(services.projects.load_project(scope.project_name))
                grid = GridManager(project_path).get(target.resource_id)
                if grid is not None:
                    grid_state = {"grid": grid}
            return target, project_path, available, int(info.get("current_version") or 0), grid_state

        try:
            prepared = await asyncio.to_thread(prepare)
        except ApiError as exc:
            return _api_problem(exc)
        if prepared is None:
            return _not_found(kind, item_id)
        target, _project_path, available, current_version, grid_state = prepared
        if value.version not in available:
            return tool_problem(
                f"{kind} '{target.resource_id}' has no version {value.version}",
                code="version_not_found",
                params={"available_versions": available},
            )
        if value.expected_current_version is not None and value.expected_current_version != current_version:
            return _version_conflict(current_version)

        if value.version == current_version:
            # Already current: nothing is written, so there is nothing for an active task to race.
            signals = await asyncio.to_thread(_currency_signals, services, scope.project_name, target)
            return ToolOutcome(
                value={
                    "kind": kind,
                    "id": target.resource_id,
                    "previous_version": current_version,
                    "current_version": current_version,
                    "changed": False,
                    **signals,
                }
            )

        active = await active_media_writer_tasks(
            services.queue,
            project_name=scope.project_name,
            resource_type=target.resource_type,
            resource_id=target.resource_id,
        )
        grid = grid_state.get("grid")
        if grid is not None and await grid_is_in_flight(
            grid, queue=services.queue, project_name=scope.project_name, user_id=caller.user_id
        ):
            active = active or ["grid"]
        if active:
            return tool_problem(
                f"{kind} '{target.resource_id}' has an active generation task; wait for it to finish and review the result first",
                code="active_task_conflict",
                params={"task_ids": [task for task in active if task != "grid"]},
            )

        previous_split_at = grid.split_at if grid is not None else None
        try:
            restored = await restore_media_version(
                project_manager=services.projects,
                versions=VersionManager(_project_path),
                project_name=scope.project_name,
                resource_type=target.resource_type,
                resource_id=target.resource_id,
                version=value.version,
                change_source="worker",
                # Bind the write to the version observed above (which equals expected_current_version when given):
                # it is compared again under the versions lock inside the restore transaction.
                expected_current_version=current_version,
            )
        except CurrentVersionChangedError as exc:
            return _version_conflict(exc.actual)
        except ApiError as exc:
            return _api_problem(exc)

        signals = await asyncio.to_thread(_currency_signals, services, scope.project_name, target)
        result: dict[str, Any] = {
            "kind": kind,
            "id": target.resource_id,
            "previous_version": current_version or None,
            "current_version": restored["current_version"],
            "changed": True,
            **signals,
        }
        if kind == "grid_composite":
            result.update(
                {
                    "split_reset": True,
                    "previous_split_at": previous_split_at,
                    "storyboard_cells_changed": False,
                    "state": "awaiting_split",
                }
            )
        return ToolOutcome(value=result)
    except Exception as exc:
        return tool_error("select_media_version", exc)


def select_media_version_summary(value: dict[str, Any]) -> str:
    if not value["changed"]:
        return f"{value['kind']} {value['id']} already uses v{value['current_version']}; nothing changed"
    text = f"{value['kind']} {value['id']} current version is now v{value['current_version']} (was v{value['previous_version']})"
    if value.get("stale_dependents"):
        text += f"; now stale: {', '.join(value['stale_dependents'])}"
    if value["kind"] == "grid_composite":
        text += "; split state reset, nothing split, storyboard cells unchanged"
    return text


__all__ = [
    "KIND_RESOURCE_TYPES",
    "ListMediaVersionsRequest",
    "MediaTarget",
    "MediaTargetNotFoundError",
    "SelectMediaVersionRequest",
    "list_media_versions",
    "list_media_versions_summary",
    "resolve_media_target",
    "select_media_version",
    "select_media_version_summary",
]
