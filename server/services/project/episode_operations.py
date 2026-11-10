"""Episode-ledger operations shared by the Web episode routers and the Agent episode-management tools.

Each operation keeps the native confirmation protocol of :mod:`lib.episode`: a first call without the confirmed
token returns the server-computed impact and writes nothing; the confirmed call recomputes the impact under the
project lock and refuses again if it changed. Before a confirmed call that would retire or remove episodes, every
displaced episode is checked for queued/running generation tasks through ``is_active`` so tasks never outlive the
episode they target.

Entry points supply ``is_active`` (the Web uses the process queue, Agent tools use ``Services.queue``) and the
translator used for server-written confirmation text, and wrap the call in ``project_change_source`` (``webui`` for the
Web, ``worker`` for Agent tools); the context variable follows the work into its threads. Domain
refusals propagate as their native exceptions (``ManualSplitError``, ``EpisodeManagementError``,
``EpisodeSourceError``, ``SourceFileChangeError``, ``ReplanError``); task or planning conflicts raise
:class:`EpisodeOperationRefused` whose ``code`` is the i18n key the Web already shows.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Collection, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from lib.episode.episode_deletion import EpisodeDeletionResult, delete_episode, render_episode_deletion_text
from lib.episode.episode_layout import build_episode_layout
from lib.episode.episode_manual_split import (
    ManualSplitOutcome,
    ManualSplitResult,
    clear_cuts_after,
    cut_unsplit_source,
    merge_with_next_episode,
    move_episode_boundary,
    render_manual_split_impact_text,
    split_episode,
)
from lib.episode.episode_replan import (
    ReplanAdoptionResult,
    ReplanConfirmationRequired,
    adopt_replan_candidate,
    discard_replan_candidate,
    render_replan_adoption_text,
    replan_candidate_summary,
)
from lib.episode.source_file_changes import (
    SourceFileChangeError,
    SourceFileChangeOutcome,
    accept_external_source_change,
    render_source_file_impact_text,
)
from lib.infra.api_errors import NotFoundError
from lib.infra.async_thread import run_sync_transaction
from lib.project.project_manager import ProjectManager

type Translate = Callable[..., str]
type ActiveCheck = Callable[[int], Awaitable[bool]]

ManualSplitAction = Literal["cut", "split", "move_boundary", "merge_next", "clear_after"]


class EpisodeOperationRefused(Exception):
    """A confirmed operation was refused before writing; ``code`` is the i18n key of the refusal text."""

    def __init__(self, code: str, episode: int | None = None):
        super().__init__(code)
        self.code = code
        self.episode = episode


def require_project(manager: ProjectManager, project_name: str) -> None:
    if not manager.project_exists(project_name):
        raise NotFoundError("project_not_found", name=project_name)


async def _first_active(episodes: Collection[int], is_active: ActiveCheck) -> int | None:
    for episode in episodes:
        if await is_active(episode):
            return episode
    return None


# ---------------------------------------------------------------------------
# Episodes view (read-only).
# ---------------------------------------------------------------------------


def source_file_change_payload(
    outcome: SourceFileChangeOutcome, project: Mapping[str, Any], translate: Translate
) -> dict[str, Any]:
    """``status=applied`` after execution; otherwise the server-written affected-episode list with its ``revision``.

    ``project`` must be the pre-change project so the list names episodes by their pre-change titles or positions."""
    impact = outcome.impact.to_dict()
    if outcome.applied:
        return {"status": "applied", "impact": impact}
    text = render_source_file_impact_text(impact, project, translate)
    return {"status": "confirmation_required", "impact": {**impact, "text": text}, "revision": outcome.revision}


def episodes_view_payload(manager: ProjectManager, project_name: str, translate: Translate) -> dict[str, Any]:
    """Whole-source layout, pending replan candidate summary and externally changed files; read-only, call in a thread."""
    require_project(manager, project_name)
    project = manager.load_project(project_name)
    project_dir = manager.get_project_path(project_name)
    layout = build_episode_layout(project_dir, project)

    def _external_change(filename: str) -> dict[str, Any]:
        try:
            outcome = accept_external_source_change(manager, project_name, filename, dry_run=True)
        except SourceFileChangeError as exc:
            return {
                "source_file": f"source/{filename}",
                "impact": None,
                "revision": None,
                "problem": translate(f"source_file_change_{exc.code}"),
            }
        payload = source_file_change_payload(outcome, project, translate)
        return {
            "source_file": f"source/{filename}",
            "impact": payload["impact"],
            "revision": payload["revision"],
            "problem": None,
        }

    return {
        **asdict(layout),
        "replan": replan_candidate_summary(project_dir, project),
        "external_changes": [_external_change(file.name) for file in layout.files if file.changed_outside],
    }


# ---------------------------------------------------------------------------
# Manual source-boundary edits.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManualSplitCommand:
    """One manual-split command in the native coordinate system (whole-source file + normalized offset)."""

    action: ManualSplitAction
    episode: int | None = None
    at: int | None = None
    end: int | None = None
    source_file: str | None = None
    title: str = ""
    confirm_episodes: Collection[int] = field(default_factory=tuple)
    confirm_merged_units: int = 0
    dry_run: bool = False


def run_manual_split(
    project_dir: Path, command: ManualSplitCommand, *, dry_run: bool | None = None
) -> ManualSplitOutcome:
    """Dispatch a manual-split command to :mod:`lib.episode.episode_manual_split`; synchronous, call in a thread."""
    options = {
        "confirm_episodes": command.confirm_episodes,
        "dry_run": command.dry_run if dry_run is None else dry_run,
    }
    if command.action == "cut":
        assert command.source_file is not None
        assert command.end is not None
        return cut_unsplit_source(
            project_dir, source_file=command.source_file, end=command.end, title=command.title, **options
        )
    assert command.episode is not None
    if command.action == "split":
        assert command.at is not None
        return split_episode(project_dir, command.episode, at=command.at, source_file=command.source_file, **options)
    if command.action == "move_boundary":
        assert command.at is not None
        return move_episode_boundary(
            project_dir, command.episode, at=command.at, source_file=command.source_file, **options
        )
    if command.action == "merge_next":
        return merge_with_next_episode(
            project_dir, command.episode, confirm_merged_units=command.confirm_merged_units, **options
        )
    return clear_cuts_after(project_dir, command.episode, **options)


async def apply_manual_split(
    manager: ProjectManager,
    project_name: str,
    command: ManualSplitCommand,
    *,
    is_active: ActiveCheck,
    translate: Translate,
) -> dict[str, Any]:
    """Run a manual split: ``status=applied`` or ``status=confirmation_required`` with server-written ``impact.text``.

    Outside ``dry_run``, displaced (retired or removed) episodes with queued/running tasks refuse with
    ``manual_split_tasks_active`` before writing."""

    def _displaced() -> list[int]:
        require_project(manager, project_name)
        preview = run_manual_split(manager.get_project_path(project_name), command, dry_run=True)
        return [*preview.impact.retired, *preview.impact.removed]

    if not command.dry_run:
        active = await _first_active(await asyncio.to_thread(_displaced), is_active)
        if active is not None:
            raise EpisodeOperationRefused("manual_split_tasks_active", active)

    def _sync() -> dict[str, Any]:
        require_project(manager, project_name)
        outcome = run_manual_split(manager.get_project_path(project_name), command)
        impact = outcome.impact.to_dict()
        if isinstance(outcome, ManualSplitResult):
            return {"status": "applied", "episode": outcome.episode, "impact": impact}
        project = manager.load_project(project_name)
        text = render_manual_split_impact_text(impact, project, translate)
        return {"status": "confirmation_required", "impact": {**impact, "text": text}}

    return await run_sync_transaction(_sync)


# ---------------------------------------------------------------------------
# Episode deletion with loss review.
# ---------------------------------------------------------------------------


async def delete_episode_reviewed(
    manager: ProjectManager,
    project_name: str,
    episode: int,
    *,
    revision: str | None,
    is_active: ActiveCheck,
    translate: Translate,
) -> dict[str, Any]:
    """Move an episode into project trash after loss review.

    Without ``revision`` (or with a stale one) return ``status=confirmation_required`` and the loss list; with the
    current revision delete and return ``status=deleted``. A confirmed call on an episode with queued/running tasks
    refuses with ``episode_manage_tasks_active``."""
    if revision is not None and await is_active(episode):
        raise EpisodeOperationRefused("episode_manage_tasks_active", episode)

    def _sync() -> dict[str, Any]:
        require_project(manager, project_name)
        outcome = delete_episode(manager, project_name, episode, revision=revision)
        impact = outcome.impact.to_dict()
        if isinstance(outcome, EpisodeDeletionResult):
            return {"status": "deleted", "impact": impact}
        text = render_episode_deletion_text(impact, manager.load_project(project_name), translate)
        return {"status": "confirmation_required", "impact": {**impact, "text": text}}

    return await run_sync_transaction(_sync)


# ---------------------------------------------------------------------------
# Whole-source file changes (edit/replace/move/delete/accept-external).
# ---------------------------------------------------------------------------


async def ensure_no_displaced_source_tasks(
    revision: str | None,
    preview: Callable[[], SourceFileChangeOutcome],
    is_active: ActiveCheck,
) -> None:
    """Before a confirmed whole-source file change, refuse when retired or removed episodes still have active tasks.

    Skipped when ``revision`` is absent or no longer matches: the command itself returns a fresh confirmation."""
    if revision is None:
        return
    outcome = await run_sync_transaction(preview)
    if outcome.revision != revision:
        return
    active = await _first_active((*outcome.impact.retired, *outcome.impact.removed), is_active)
    if active is not None:
        raise EpisodeOperationRefused("source_file_change_tasks_active", active)


async def run_source_file_change(
    manager: ProjectManager,
    project_name: str,
    revision: str | None,
    command: Callable[[ProjectManager, bool], SourceFileChangeOutcome],
    *,
    is_active: ActiveCheck,
    translate: Translate,
) -> dict[str, Any]:
    """``command(manager, dry_run)`` runs a whole-source file-change command that already carries ``revision``."""

    def _manager() -> ProjectManager:
        require_project(manager, project_name)
        return manager

    def _sync() -> dict[str, Any]:
        project = _manager().load_project(project_name)
        outcome = command(manager, False)
        return source_file_change_payload(outcome, project, translate)

    await ensure_no_displaced_source_tasks(revision, lambda: command(_manager(), True), is_active)
    return await run_sync_transaction(_sync)


# ---------------------------------------------------------------------------
# Replan candidate adoption / discard (no model call).
# ---------------------------------------------------------------------------


async def adopt_replan_reviewed(
    manager: ProjectManager,
    project_name: str,
    candidate_id: str,
    *,
    revision: str | None,
    delete_retired: bool,
    planning_active: Callable[[], Awaitable[bool]],
    is_active: ActiveCheck,
    translate: Translate,
) -> dict[str, Any]:
    """Adopt a replan candidate after reviewing its change list; never calls a model.

    Without ``revision`` (or with a stale one) return ``status=confirmation_required`` with ``impact.text`` /
    ``impact.delete_text`` and ``impact.revision``. Refuses with ``episode_replan_generating`` while candidate
    windows are queued/running, and with ``episode_replan_tasks_active`` when retired/removed episodes still have tasks."""
    project_dir = await asyncio.to_thread(manager.get_project_path, project_name)

    async def _run[T](action: Callable[[], T]) -> T:
        if await planning_active():
            raise EpisodeOperationRefused("episode_replan_generating")

        def _sync() -> T:
            return action()

        return await run_sync_transaction(_sync)

    if revision is not None:
        preview = await _run(lambda: adopt_replan_candidate(project_dir, candidate_id))
        if isinstance(preview, ReplanConfirmationRequired):
            active = await _first_active((*preview.impact.retired, *preview.impact.removed), is_active)
            if active is not None:
                raise EpisodeOperationRefused("episode_replan_tasks_active", active)

    def _adopt() -> dict[str, Any]:
        outcome = adopt_replan_candidate(project_dir, candidate_id, revision=revision, delete_retired=delete_retired)
        if isinstance(outcome, ReplanAdoptionResult):
            return {"status": "adopted", "episodes": outcome.episodes, "deleted": outcome.deleted}
        impact = outcome.impact.to_dict()
        texts = render_replan_adoption_text(impact, manager.load_project(project_name), translate)
        return {"status": "confirmation_required", "impact": {**impact, **texts}}

    return await _run(_adopt)


async def discard_replan(
    manager: ProjectManager,
    project_name: str,
    candidate_id: str,
    *,
    planning_active: Callable[[], Awaitable[bool]],
) -> dict[str, Any]:
    """Discard a replan candidate without changing the ledger; refused while candidate windows are generating."""
    if await planning_active():
        raise EpisodeOperationRefused("episode_replan_generating")

    def _sync() -> dict[str, Any]:
        discard_replan_candidate(manager.get_project_path(project_name), candidate_id)
        return {"status": "discarded"}

    return await run_sync_transaction(_sync)


__all__ = [
    "EpisodeOperationRefused",
    "ManualSplitCommand",
    "adopt_replan_reviewed",
    "apply_manual_split",
    "delete_episode_reviewed",
    "discard_replan",
    "ensure_no_displaced_source_tasks",
    "episodes_view_payload",
    "require_project",
    "run_manual_split",
    "run_source_file_change",
    "source_file_change_payload",
]
