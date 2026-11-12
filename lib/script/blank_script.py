"""“Start from blank”: create an empty formal script when an episode has none, for creator-authored timeline entries.

All four skeletons use one action, selecting entry arrays by project axes. Discard unconfirmed plans and their repair
drafts, deleting confirmation records too: future plans have no confirmed fingerprint and remain pending until overwrite confirmation.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any

from lib.artifacts.artifact_currency import active_artifact_currency_resolver
from lib.artifacts.artifact_manifest import ArtifactKey
from lib.project.project_manager import ProjectManager, find_episode
from lib.script import script_review
from lib.script.draft_quarantine import (
    DRAFT_OWNER_AGENT,
    QUARANTINE_KIND_PROMPT_AUTHORING,
    draft_owner,
    quarantine_path,
    read_quarantine,
)
from lib.script.planning_draft_trash import discard_quarantine
from lib.script.script_document import build_blank_script


class BlankScriptError(ValueError):
    """Starting from blank refused; ``code`` is a stable reason.

    - ``episode_not_found``: episode absent from the ledger;
    - ``formal_script_exists``: formal script exists (by artifact manifest, matching production status), or the
      canonical path contains another episode's script;
    - ``draft_agent_owned``: Agent is editing this episode's script-plan draft.
    """

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


@dataclass(frozen=True)
class BlankScriptResult:
    """Outcome of starting from blank: the created script and the unconfirmed planning moved to project trash."""

    episode: int
    script_file: str
    #: The unconfirmed formal script plan was moved to project trash.
    discarded_script_plan: bool
    #: Quarantine draft kinds moved to project trash (creator-owned drafts only; Agent-owned drafts refuse the call).
    discarded_drafts: tuple[str, ...]
    #: A previous script-plan confirmation record was cleared from the episode ledger.
    cleared_review: bool


def start_blank_script(pm: ProjectManager, project_name: str, episode: int) -> str:
    """Create an empty formal episode script and return its filename (see :func:`start_blank_script_detailed`)."""
    return start_blank_script_detailed(pm, project_name, episode).script_file


def start_blank_script_detailed(pm: ProjectManager, project_name: str, episode: int) -> BlankScriptResult:
    """Create an empty formal episode script and report what unconfirmed planning was discarded.

    Lock order matches content confirmation: draft → formal script plan → formal script. Write the script before discarding
    plans: discard failure leaves an unconfirmed plan, never deleted planning with no script. Script files at canonical
    paths but unregistered in the artifact manifest are not formal scripts and are overwritten by the empty script.
    """
    project = pm.load_project(project_name)
    if find_episode(project, episode) is None:
        raise BlankScriptError("episode_not_found", f"Episode (id={episode}) is not in the episode ledger")
    project_path = pm.get_project_path(project_name)
    plan_path = script_review.script_plan_path(project_path, project, episode)
    draft_kinds = [
        kind
        for kind in (
            script_review.script_plan_quarantine_kind(project),
            QUARANTINE_KIND_PROMPT_AUTHORING if script_review.script_plan_kind(project) == "reference_video" else None,
        )
        if kind is not None
    ]

    with ExitStack() as locks:
        for kind in draft_kinds:
            locks.enter_context(pm.file_lock(quarantine_path(project_path, episode, kind)))
        if plan_path is not None:
            locks.enter_context(script_review.formal_script_plan_lock(project_path, episode, plan_path))
        project = pm.load_project(project_name)
        try:
            filename = script_review.formal_script_filename(project_path, project, episode)
        except script_review.ForeignFormalScriptError as exc:
            raise BlankScriptError("formal_script_exists", str(exc)) from exc
        resolver = active_artifact_currency_resolver(project_path, project)
        key = ArtifactKey.episode_script(episode)
        if resolver.resolve_usable_entry(key, artifact_path=f"scripts/{filename}") is not None:
            raise BlankScriptError(
                "formal_script_exists", f"Episode (id={episode}) already has a formal script scripts/{filename}"
            )
        for kind in draft_kinds:
            draft = read_quarantine(project_path, episode, kind)
            if draft is not None and draft_owner(draft) == DRAFT_OWNER_AGENT:
                raise BlankScriptError(
                    "draft_agent_owned", f"The draft of episode (id={episode}) is being edited by the Agent"
                )

        cleared_review = False

        def _drop_review(p: dict[str, Any]) -> None:
            nonlocal cleared_review
            entry = find_episode(p, episode)
            if entry is None:
                raise BlankScriptError("episode_not_found", f"Episode (id={episode}) is not in the episode ledger")
            # Old confirmation belongs to the discarded plan; retaining it would falsely confirm later identical plans.
            cleared_review = entry.pop(script_review.REVIEW_FIELD, None) is not None

        pm.save_script(project_name, build_blank_script(project, episode), filename, project_update=_drop_review)

        discarded_script_plan = False
        if plan_path is not None and plan_path.exists():
            script_review.trash_script_plan_locked(project_path, episode, plan_path)
            discarded_script_plan = True
        discarded_drafts = tuple(kind for kind in draft_kinds if discard_quarantine(project_path, episode, kind))
    return BlankScriptResult(
        episode=episode,
        script_file=filename,
        discarded_script_plan=discarded_script_plan,
        discarded_drafts=discarded_drafts,
        cleared_review=cleared_review,
    )


__all__ = ["BlankScriptError", "BlankScriptResult", "start_blank_script", "start_blank_script_detailed"]
