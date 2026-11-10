"""Host-neutral episode-management tools: read the episode layout, create/move/delete episodes, edit whole-source
episode boundaries, reorder whole-source files, and read/adopt/discard/start/continue a replan candidate.

Every write reuses :mod:`server.services.project.episode_operations` (shared with the Web routers) or the native
:mod:`lib.episode` command directly, so the native confirmation protocol applies unchanged: the first call returns the
server-written impact and writes nothing; the confirmed call recomputes it under the project lock and asks again if it
changed. Writes are tagged with the ``worker`` change source, like other Agent-tool writes. Nothing here calls a model
except ``start_episode_replan`` / ``continue_episode_replan``, which submit the native text-planning task.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from pydantic.json_schema import SkipJsonSchema

from lib.episode.episode_ids import episode_position
from lib.episode.episode_management import EpisodeManagementError, create_episode, move_episode
from lib.episode.episode_manual_split import ManualSplitError
from lib.episode.episode_replan import ReplanError, ReplanScope, replan_candidate_summary
from lib.episode.episode_source_commands import EpisodeSourceError
from lib.episode.source_file_changes import SourceFileChangeError, move_whole_source_file
from lib.generation.generation_batch import GenerationBatchReadModel
from lib.i18n import DEFAULT_LOCALE
from lib.i18n import _ as translate_message
from lib.infra.api_errors import ApiError
from lib.infra.async_thread import run_sync_transaction
from lib.project.project_change_hints import project_change_source
from server.draft_workflow import EPISODE_ID_DESCRIPTION, PositiveEpisode
from server.media_tools.context import tool_error
from server.services.project.episode_operations import (
    EpisodeOperationRefused,
    ManualSplitCommand,
    adopt_replan_reviewed,
    apply_manual_split,
    delete_episode_reviewed,
    discard_replan,
    episodes_view_payload,
    run_source_file_change,
)
from server.services.tasks.episode_activity import episode_has_active_tasks
from server.text_generation import MAX_INSTRUCTIONS_LEN
from server.tool_runtime import (
    CallerContext,
    PlanEpisodesRequest,
    ProjectScope,
    ReplanWindowResult,
    Services,
    ToolOutcome,
    ToolProblem,
    ToolRequest,
    continue_episode_replan,
    episode_planning_active,
    migration_gate,
    start_episode_replan,
)

#: Agent-tool writes use the generation-tool change source, not ``webui`` (see ``server.media_tools.project_trash``).
_CHANGE_SOURCE = "worker"


def _translate(key: str, **params: Any) -> str:
    return translate_message(key, DEFAULT_LOCALE, **params)


# ---------------------------------------------------------------------------
# Request models.
# ---------------------------------------------------------------------------


class EpisodeLayoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    include_segment_text: StrictBool = Field(
        default=False,
        description="Include each whole-source segment's full text. Off by default because segments can be long; use get_source_text or the episode first/last sentences instead when possible",
    )


class CreateEpisodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    after_episode_id: PositiveEpisode | SkipJsonSchema[None] = Field(
        default=None,
        description="Episode ID to insert after in playback order; omit to append at the end of playback order",
    )
    title: str = Field(default="", max_length=200, description="Episode title; blank displays as Episode N by position")
    hook: str = Field(default="", max_length=2000, description="Episode hook; blank leaves it unset")


class MoveEpisodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: PositiveEpisode = Field(description=EPISODE_ID_DESCRIPTION)
    after_episode_id: PositiveEpisode | None = Field(
        description="Episode ID to place it after in playback order; null moves it to the beginning. Required so the destination is always explicit",
    )


class DeleteEpisodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: PositiveEpisode = Field(description=EPISODE_ID_DESCRIPTION)
    revision: str | SkipJsonSchema[None] = Field(
        default=None,
        description="impact.revision from the previous confirmation_required response, sent only after showing impact.text to the user and obtaining explicit consent. Omit on the first call",
    )


BoundaryAction = Literal["cut", "split", "move_boundary", "merge_next", "clear_after"]


class EditEpisodeBoundariesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: BoundaryAction = Field(
        description=(
            "cut: make a new episode from the start of the unsplit text containing `end` in source_file up to `end`; "
            "split: split episode_id at `at` (first part keeps the ID, second gets a new ID right after it); "
            "move_boundary: move the boundary between episode_id and the next extracted episode to `at`, keeping both IDs; "
            "merge_next: merge the next extracted episode (by source position) into episode_id; "
            "clear_after: clear every extracted episode after episode_id by source position"
        )
    )
    episode_id: PositiveEpisode | SkipJsonSchema[None] = Field(
        default=None, description="Extracted episode ID; required for every action except cut"
    )
    at: Annotated[int, Field(ge=0)] | SkipJsonSchema[None] = Field(
        default=None,
        description="split / move_boundary: offset inside source_file in normalized source-text coordinates (as reported by get_episode_layout segments)",
    )
    end: Annotated[int, Field(gt=0)] | SkipJsonSchema[None] = Field(
        default=None, description="cut: end offset of the new episode inside source_file (normalized coordinates)"
    )
    source_file: str | SkipJsonSchema[None] = Field(
        default=None,
        description="Whole-source file path such as source/novel.txt. Required for cut; split defaults to the file containing the episode start, move_boundary to the file containing its end",
    )
    title: str = Field(default="", max_length=200, description="cut: optional title of the new episode")
    confirm_episodes: list[PositiveEpisode] = Field(
        default_factory=list,
        description="Episode IDs listed in impact.restaled + impact.retired of the previous confirmation_required response, sent only after the user confirmed impact.text",
    )
    confirm_merged_units: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="merge_next: impact.merged_units the user confirmed (unsplit text absorbed between the two episodes)",
    )
    dry_run: StrictBool = Field(default=False, description="Return the impact only, without writing")

    @model_validator(mode="after")
    def _arguments_match_action(self) -> EditEpisodeBoundariesRequest:
        if self.action == "cut":
            if self.source_file is None or self.end is None:
                raise ValueError("cut requires source_file and end")
            if self.episode_id is not None or self.at is not None:
                raise ValueError("cut does not take episode_id or at")
            return self
        if self.episode_id is None:
            raise ValueError(f"{self.action} requires episode_id")
        if self.end is not None:
            raise ValueError(f"{self.action} does not take end")
        if self.action in ("split", "move_boundary") and self.at is None:
            raise ValueError(f"{self.action} requires at")
        if self.action in ("merge_next", "clear_after") and (self.at is not None or self.source_file is not None):
            raise ValueError(f"{self.action} does not take at or source_file")
        if self.action != "merge_next" and self.confirm_merged_units:
            raise ValueError("confirm_merged_units applies only to merge_next")
        return self

    def command(self) -> ManualSplitCommand:
        return ManualSplitCommand(
            action=self.action,
            episode=self.episode_id,
            at=self.at,
            end=self.end,
            source_file=self.source_file,
            title=self.title,
            confirm_episodes=tuple(self.confirm_episodes),
            confirm_merged_units=self.confirm_merged_units,
            dry_run=self.dry_run,
        )


class MoveSourceFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str = Field(
        min_length=1, description="Whole-source file name under source/, without the source/ prefix (e.g. novel.txt)"
    )
    direction: Literal["up", "down"] = Field(description="Move one position earlier (up) or later (down)")
    revision: str | SkipJsonSchema[None] = Field(
        default=None,
        description="revision from the previous confirmation_required response, sent only after the user confirmed impact.text. Omit on the first call",
    )


class ReplanCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1, description="Candidate id from get_episode_replan (replan.id)")


class AdoptReplanRequest(ReplanCandidateRequest):
    revision: str | SkipJsonSchema[None] = Field(
        default=None,
        description="impact.revision from the previous confirmation_required response, sent only after the user confirmed impact.text (and impact.delete_text when delete_retired). Omit on the first call",
    )
    delete_retired: StrictBool = Field(
        default=False,
        description="Also move retired episodes (in production, now without source) to project trash after adoption. Only with explicit user consent to impact.delete_text",
    )


class StartReplanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: PositiveEpisode = Field(
        description="Extracted episode ID from which to replan through the end of the whole source"
    )
    instructions: Annotated[str, Field(max_length=MAX_INSTRUCTIONS_LEN)] | SkipJsonSchema[None] = Field(
        default=None,
        description="Optional verbatim user planning instructions, stored with the candidate and reused by continue_episode_replan",
    )
    dry_run: StrictBool = Field(
        default=False,
        description="Return only the replan scope (replaced extracted episodes and those already in production) without calling a model",
    )


# ---------------------------------------------------------------------------
# Shared helpers.
# ---------------------------------------------------------------------------


def _problem_from(exc: BaseException) -> ToolProblem | None:
    """Native refusal → stable problem code (the i18n key the Web shows) with default-language text."""
    params: dict[str, Any] = {}
    if isinstance(exc, ManualSplitError):
        key = f"manual_split_{exc.code}"
    elif isinstance(exc, EpisodeManagementError):
        key = f"episode_manage_{exc.code}"
    elif isinstance(exc, EpisodeSourceError):
        key = "episode_source_episode_not_found" if exc.code == "episode_not_found" else exc.code
    elif isinstance(exc, SourceFileChangeError):
        key = f"source_file_change_{exc.code}"
    elif isinstance(exc, ReplanError):
        key = f"episode_replan_{exc.code}"
    elif isinstance(exc, EpisodeOperationRefused):
        key = exc.code
        if exc.episode is not None:
            params["episode"] = exc.episode
    elif isinstance(exc, ApiError):
        key = exc.key
        params = dict(exc.params or {})
    else:
        return None
    return ToolProblem(key, _translate(key, **params), params=params or None)


async def _guarded(operation: str, call: Callable[[], Awaitable[Any]]) -> ToolOutcome[Any]:
    try:
        with project_change_source(_CHANGE_SOURCE):
            value = await call()
    except Exception as exc:
        problem = _problem_from(exc)
        return ToolOutcome(problem=problem) if problem is not None else tool_error(operation, exc)
    return ToolOutcome(value=value)


def _active_check(scope: ProjectScope, services: Services) -> Callable[[int], Awaitable[bool]]:
    return lambda episode: episode_has_active_tasks(services.queue, scope.project_name, episode)


def _layout_value(payload: dict[str, Any], project: dict[str, Any], *, include_text: bool) -> dict[str, Any]:
    """Name episodes by title and playback position next to their internal IDs; drop long segment text unless asked."""
    ledger = {entry.get("episode"): entry for entry in project.get("episodes") or () if isinstance(entry, dict)}
    for episode in payload["episodes"]:
        entry = ledger.get(episode["episode"], {})
        episode["title"] = entry.get("title") or ""
        episode["hook"] = entry.get("hook") or ""
        episode["position"] = episode_position(project, episode["episode"])
    if not include_text:
        for file in payload["files"]:
            for segment in file["segments"]:
                segment.pop("text", None)
    return payload


# ---------------------------------------------------------------------------
# Handlers.
# ---------------------------------------------------------------------------


async def get_episode_layout(
    request: ToolRequest[EpisodeLayoutRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    if problem := await migration_gate(scope, services):
        return ToolOutcome(problem=problem)

    def _read() -> dict[str, Any]:
        payload = episodes_view_payload(services.projects, scope.project_name, _translate)
        project = services.projects.load_project(scope.project_name)
        return _layout_value(payload, project, include_text=request.value.include_segment_text)

    async def _call() -> dict[str, Any]:
        value = await asyncio.to_thread(_read)
        value["replan_generating"] = await episode_planning_active(scope, caller, services)
        return value

    return await _guarded("get_episode_layout", _call)


async def create_empty_episode(
    request: ToolRequest[CreateEpisodeRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value

    def _create() -> dict[str, Any]:
        episode = create_episode(
            services.projects, scope.project_name, after=req.after_episode_id, title=req.title, hook=req.hook
        )
        project = services.projects.load_project(scope.project_name)
        return {"episode_id": episode, "position": episode_position(project, episode)}

    return await _guarded("create_episode", lambda: run_sync_transaction(_create))


async def move_episode_tool(
    request: ToolRequest[MoveEpisodeRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value

    def _move() -> dict[str, Any]:
        move_episode(services.projects, scope.project_name, req.episode_id, after=req.after_episode_id)
        project = services.projects.load_project(scope.project_name)
        return {
            "episode_id": req.episode_id,
            "position": episode_position(project, req.episode_id),
            "playback_order": [
                entry.get("episode") for entry in project.get("episodes") or () if isinstance(entry, dict)
            ],
        }

    return await _guarded("move_episode", lambda: run_sync_transaction(_move))


async def delete_episode_tool(
    request: ToolRequest[DeleteEpisodeRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value
    return await _guarded(
        "delete_episode",
        lambda: delete_episode_reviewed(
            services.projects,
            scope.project_name,
            req.episode_id,
            revision=req.revision,
            is_active=_active_check(scope, services),
            translate=_translate,
        ),
    )


async def edit_episode_boundaries(
    request: ToolRequest[EditEpisodeBoundariesRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    return await _guarded(
        "edit_episode_boundaries",
        lambda: apply_manual_split(
            services.projects,
            scope.project_name,
            request.value.command(),
            is_active=_active_check(scope, services),
            translate=_translate,
        ),
    )


async def move_source_file(
    request: ToolRequest[MoveSourceFileRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value
    return await _guarded(
        "move_source_file",
        lambda: run_source_file_change(
            services.projects,
            scope.project_name,
            req.revision,
            lambda pm, dry_run: move_whole_source_file(
                pm, scope.project_name, req.filename, direction=req.direction, revision=req.revision, dry_run=dry_run
            ),
            is_active=_active_check(scope, services),
            translate=_translate,
        ),
    )


async def get_episode_replan(
    _request: ToolRequest[Any], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    if problem := await migration_gate(scope, services):
        return ToolOutcome(problem=problem)

    def _read() -> dict[str, Any] | None:
        project_dir = services.projects.get_project_path(scope.project_name)
        return replan_candidate_summary(project_dir, services.projects.load_project(scope.project_name))

    async def _call() -> dict[str, Any]:
        replan = await asyncio.to_thread(_read)
        return {"replan": replan, "generating": await episode_planning_active(scope, caller, services)}

    return await _guarded("get_episode_replan", _call)


async def adopt_episode_replan(
    request: ToolRequest[AdoptReplanRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value
    return await _guarded(
        "adopt_episode_replan",
        lambda: adopt_replan_reviewed(
            services.projects,
            scope.project_name,
            req.candidate_id,
            revision=req.revision,
            delete_retired=req.delete_retired,
            planning_active=lambda: episode_planning_active(scope, caller, services),
            is_active=_active_check(scope, services),
            translate=_translate,
        ),
    )


async def discard_episode_replan(
    request: ToolRequest[ReplanCandidateRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    return await _guarded(
        "discard_episode_replan",
        lambda: discard_replan(
            services.projects,
            scope.project_name,
            request.value.candidate_id,
            planning_active=lambda: episode_planning_active(scope, caller, services),
        ),
    )


async def start_episode_replan_tool(
    request: ToolRequest[StartReplanRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[Any]:
    req = request.value
    outcome = await start_episode_replan(
        ToolRequest(PlanEpisodesRequest(instructions=req.instructions)),
        scope,
        caller,
        services,
        episode=req.episode_id,
        dry_run=req.dry_run,
    )
    if outcome.problem is not None or not isinstance(outcome.value, ReplanScope):
        return outcome
    scope_value = outcome.value
    return ToolOutcome(
        value={
            "status": "preview",
            "replaced": list(scope_value.replaced),
            "started": list(scope_value.started),
        }
    )


async def continue_episode_replan_tool(
    request: ToolRequest[ReplanCandidateRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[Any]:
    return await continue_episode_replan(request.value.candidate_id, scope, caller, services)


def replan_structured(value: GenerationBatchReadModel | ReplanWindowResult | dict[str, Any]) -> dict[str, Any]:
    """Batch handles (external callers) under ``generation_batch``; the embedded host's first-window result and the
    dry-run scope under ``episode_replan``."""
    from server.agent_toolset.envelope import json_value

    if isinstance(value, GenerationBatchReadModel):
        return {"generation_batch": json_value(value)}
    return {"episode_replan": json_value(value)}


__all__ = [
    "AdoptReplanRequest",
    "CreateEpisodeRequest",
    "DeleteEpisodeRequest",
    "EditEpisodeBoundariesRequest",
    "EpisodeLayoutRequest",
    "MoveEpisodeRequest",
    "MoveSourceFileRequest",
    "ReplanCandidateRequest",
    "StartReplanRequest",
    "adopt_episode_replan",
    "continue_episode_replan_tool",
    "create_empty_episode",
    "delete_episode_tool",
    "discard_episode_replan",
    "edit_episode_boundaries",
    "get_episode_layout",
    "get_episode_replan",
    "move_episode_tool",
    "move_source_file",
    "replan_structured",
    "start_episode_replan_tool",
]
