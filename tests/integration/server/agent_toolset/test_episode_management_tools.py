"""Episode-management and replan-candidate Agent tools against a real project ledger.

Covers MCP-017: empty-episode creation, playback reordering, loss-reviewed deletion, manual boundary edits with dry-run
and confirmation, whole-source file reordering, and a replan candidate read/adopted/discarded across a fresh harness
(a reconnect) without any planning task. Every case asserts that no generation task was enqueued.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lib.episode.episode_replan import create_replan_candidate
from lib.generation.generation_queue import GenerationQueue
from lib.project.project_manager import ProjectManager
from server.agent_toolset.episode_management import (
    CREATE_EPISODE,
    DELETE_EPISODE,
    EDIT_EPISODE_BOUNDARIES,
    GET_EPISODE_LAYOUT,
    MOVE_EPISODE,
    MOVE_SOURCE_FILE,
)
from server.agent_toolset.episode_planning import (
    ADOPT_EPISODE_REPLAN,
    DISCARD_EPISODE_REPLAN,
    GET_EPISODE_REPLAN,
    PLAN_EPISODES,
    START_EPISODE_REPLAN,
)
from server.tool_runtime import CallerContext
from tests.integration.server.agent_tool_support import ToolHarness, problem_of, run_declared_tool

NOVEL = "少年下山。城里起火。夜雨。"
SEQUEL = "第二卷开始。"


def _cut(episode: int, start: int, end: int, source_file: str = "source/novel.txt") -> dict[str, Any]:
    return {
        "episode": episode,
        "title": f"旧{episode}",
        "script_file": f"scripts/episode_{episode}.json",
        "source_origin": "whole_source",
        "source_range": {"source_file": source_file, "start": start, "end": end},
        "ledger_status": "planned",
    }


class _TaskQueue:
    """Real queue plus injected queued tasks for the active-task checks (``list_tasks`` only)."""

    def __init__(self, queue: GenerationQueue):
        self._queue = queue
        self.queued: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._queue, name)

    async def list_tasks(self, *, project_name: str, status: str, page: int, page_size: int) -> dict[str, Any]:
        if status == "queued" and self.queued:
            return {"items": list(self.queued)}
        return await self._queue.list_tasks(project_name=project_name, status=status, page=page, page_size=page_size)


@pytest.fixture
def series(tmp_path: Path, db_factory, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Drama-free narration series: two extracted episodes over source/novel.txt plus one own-source episode 3."""
    pm = ProjectManager(tmp_path / "projects")
    monkeypatch.setenv("ARCREEL_DATA_DIR", str(pm.data_root))
    pm.create_project("demo")
    pm.create_project_metadata("demo", "Demo", "Anime", "narration")
    own = {"episode": 3, "title": "番外", "script_file": "scripts/episode_3.json", "source_origin": "own"}
    episodes = [_cut(1, 0, 5), _cut(2, 5, 13), own]
    pm.update_project(
        "demo",
        lambda project: project.update(
            whole_source_files=[{"source_file": "source/novel.txt"}], episodes=episodes, episode_id_high_water=3
        ),
    )
    source_dir = pm.get_project_path("demo") / "source"
    (source_dir / "novel.txt").write_text(NOVEL, encoding="utf-8")
    (source_dir / "episode_1.txt").write_text(NOVEL[0:5], encoding="utf-8")
    (source_dir / "episode_2.txt").write_text(NOVEL[5:13], encoding="utf-8")
    (source_dir / "episode_3.txt").write_text("番外原文", encoding="utf-8")
    queue = _TaskQueue(GenerationQueue(session_factory=db_factory))
    return {"pm": pm, "queue": queue, "data_root": tmp_path, "db_factory": db_factory}


def _harness(series: dict[str, Any], *, source: str = "mcp") -> ToolHarness:
    """A fresh harness models a reconnecting external client: new ProjectManager instance, same data root and queue."""
    return ToolHarness(
        "demo",
        series["data_root"],
        pm=ProjectManager(series["data_root"] / "projects"),
        queue=series["queue"],
        caller=CallerContext(user_id="default", source=source),
    )


async def _assert_no_generation(series: dict[str, Any]) -> None:
    queue: GenerationQueue = series["queue"]._queue
    for status in ("queued", "running", "succeeded", "failed"):
        listing = await queue.list_tasks(project_name="demo", status=status, page=1, page_size=50)
        assert listing["items"] == [], status


def _ledger(series: dict[str, Any]) -> list[int]:
    return [entry["episode"] for entry in series["pm"].load_project("demo")["episodes"]]


def _project_bytes(series: dict[str, Any]) -> bytes:
    return (series["pm"].get_project_path("demo") / "project.json").read_bytes()


async def test_layout_names_episodes_by_title_and_position_without_long_text(series) -> None:
    outcome = await run_declared_tool(GET_EPISODE_LAYOUT, _harness(series), {})

    assert outcome.problem is None
    value = outcome.value
    assert [(e["episode"], e["position"], e["title"], e["origin"]) for e in value["episodes"]] == [
        (1, 1, "旧1", "whole_source"),
        (2, 2, "旧2", "whole_source"),
        (3, 3, "番外", "own"),
    ]
    (novel,) = value["files"]
    assert [(s["kind"], s["episode"], s["start"], s["end"]) for s in novel["segments"]] == [
        ("episode", 1, 0, 5),
        ("episode", 2, 5, 13),
    ]
    assert all("text" not in s for s in novel["segments"])
    assert value["replan"] is None
    assert value["replan_generating"] is False
    await _assert_no_generation(series)


async def test_empty_episode_is_inserted_and_reordered_without_touching_ids_or_sources(series) -> None:
    ctx = _harness(series)

    created = await run_declared_tool(CREATE_EPISODE, ctx, {"after_episode_id": 1, "title": "插曲", "hook": "谁来了"})
    assert created.problem is None
    assert created.value == {"episode_id": 4, "position": 2}
    entry = series["pm"].load_project("demo")["episodes"][1]
    assert (entry["episode"], entry["title"], entry["hook"], entry["source_origin"]) == (4, "插曲", "谁来了", "none")

    moved = await run_declared_tool(MOVE_EPISODE, ctx, {"episode_id": 3, "after_episode_id": None})
    assert moved.problem is None
    assert moved.value["playback_order"] == [3, 1, 4, 2]

    # Extracted episodes keep source order: moving episode 1 after episode 2 is refused and nothing changes.
    before = _project_bytes(series)
    refused = await run_declared_tool(MOVE_EPISODE, ctx, {"episode_id": 1, "after_episode_id": 2})
    assert problem_of(refused).code == "episode_manage_cut_order_locked"
    assert _project_bytes(series) == before
    await _assert_no_generation(series)


async def test_move_requires_an_explicit_destination(series) -> None:
    outcome = await run_declared_tool(MOVE_EPISODE, _harness(series), {"episode_id": 3})

    assert problem_of(outcome).code == "invalid_request"


async def test_boundary_dry_run_writes_nothing_then_the_edit_applies(series) -> None:
    ctx = _harness(series)
    before = _project_bytes(series)

    preview = await run_declared_tool(
        EDIT_EPISODE_BOUNDARIES, ctx, {"action": "move_boundary", "episode_id": 1, "at": 10, "dry_run": True}
    )
    assert preview.problem is None
    assert preview.value["status"] == "confirmation_required"
    assert _project_bytes(series) == before

    applied = await run_declared_tool(
        EDIT_EPISODE_BOUNDARIES, ctx, {"action": "move_boundary", "episode_id": 1, "at": 10}
    )
    assert applied.problem is None
    assert applied.value["status"] == "applied"
    ranges = {
        e["episode"]: (e["source_range"]["start"], e["source_range"]["end"])
        for e in series["pm"].load_project("demo")["episodes"]
        if "source_range" in e
    }
    assert ranges == {1: (0, 10), 2: (10, 13)}
    assert _ledger(series) == [1, 2, 3]
    await _assert_no_generation(series)


async def test_split_of_an_episode_with_outputs_needs_confirmation_of_the_listed_episodes(series) -> None:
    ctx = _harness(series)
    scripts = series["pm"].get_project_path("demo") / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "episode_2.json").write_text("{}", encoding="utf-8")
    before = _project_bytes(series)

    pending = await run_declared_tool(EDIT_EPISODE_BOUNDARIES, ctx, {"action": "split", "episode_id": 2, "at": 10})
    assert pending.value["status"] == "confirmation_required"
    assert pending.value["impact"]["restaled"] == [2]
    assert "旧2" in pending.value["impact"]["text"]
    assert _project_bytes(series) == before

    # Confirming a different list (stale confirmation) is asked again without writing.
    stale = await run_declared_tool(
        EDIT_EPISODE_BOUNDARIES, ctx, {"action": "split", "episode_id": 2, "at": 10, "confirm_episodes": [1]}
    )
    assert stale.value["status"] == "confirmation_required"
    assert _project_bytes(series) == before

    applied = await run_declared_tool(
        EDIT_EPISODE_BOUNDARIES, ctx, {"action": "split", "episode_id": 2, "at": 10, "confirm_episodes": [2]}
    )
    assert applied.value["status"] == "applied"
    assert applied.value["episode"] == 4
    assert _ledger(series) == [1, 2, 4, 3]


async def test_boundary_edit_is_refused_while_a_displaced_episode_has_active_tasks(series) -> None:
    series["queue"].queued = [{"resource_id": "script_plan", "script_file": None, "payload": {"episode": 2}}]
    before = _project_bytes(series)

    refused = await run_declared_tool(
        EDIT_EPISODE_BOUNDARIES, _harness(series), {"action": "clear_after", "episode_id": 1}
    )

    problem = problem_of(refused)
    assert problem.code == "manual_split_tasks_active"
    assert problem.params == {"episode": 2}
    assert _project_bytes(series) == before


async def test_boundary_arguments_are_validated_per_action(series) -> None:
    ctx = _harness(series)
    for arguments in (
        {"action": "cut", "end": 5},
        {"action": "split", "episode_id": 1},
        {"action": "merge_next", "episode_id": 1, "at": 3},
    ):
        assert problem_of(await run_declared_tool(EDIT_EPISODE_BOUNDARIES, ctx, arguments)).code == "invalid_request"


async def test_episode_deletion_needs_the_current_loss_list_revision(series) -> None:
    ctx = _harness(series)
    before = _project_bytes(series)

    first = await run_declared_tool(DELETE_EPISODE, ctx, {"episode_id": 3})
    assert first.value["status"] == "confirmation_required"
    assert first.value["impact"]["text"]
    stale = await run_declared_tool(DELETE_EPISODE, ctx, {"episode_id": 3, "revision": "stale"})
    assert stale.value["status"] == "confirmation_required"
    assert _project_bytes(series) == before

    series["queue"].queued = [{"resource_id": "script_plan", "script_file": None, "payload": {"episode": 3}}]
    busy = await run_declared_tool(
        DELETE_EPISODE, ctx, {"episode_id": 3, "revision": first.value["impact"]["revision"]}
    )
    assert problem_of(busy).code == "episode_manage_tasks_active"
    assert _project_bytes(series) == before

    series["queue"].queued = []
    deleted = await run_declared_tool(
        DELETE_EPISODE, ctx, {"episode_id": 3, "revision": first.value["impact"]["revision"]}
    )
    assert deleted.value["status"] == "deleted"
    assert _ledger(series) == [1, 2]
    await _assert_no_generation(series)


async def test_whole_source_files_are_reordered_through_the_native_revision(series) -> None:
    pm: ProjectManager = series["pm"]
    (pm.get_project_path("demo") / "source" / "sequel.txt").write_text(SEQUEL, encoding="utf-8")
    pm.update_project(
        "demo",
        lambda project: project["whole_source_files"].append({"source_file": "source/sequel.txt"}),
    )
    ctx = _harness(series)

    edge = await run_declared_tool(MOVE_SOURCE_FILE, ctx, {"filename": "novel.txt", "direction": "up"})
    assert problem_of(edge).code == "source_file_change_move_out_of_range"

    outcome = await run_declared_tool(MOVE_SOURCE_FILE, ctx, {"filename": "sequel.txt", "direction": "up"})
    if outcome.value["status"] == "confirmation_required":
        stale = await run_declared_tool(
            MOVE_SOURCE_FILE, ctx, {"filename": "sequel.txt", "direction": "up", "revision": "stale"}
        )
        assert stale.value["status"] == "confirmation_required"
        outcome = await run_declared_tool(
            MOVE_SOURCE_FILE, ctx, {"filename": "sequel.txt", "direction": "up", "revision": outcome.value["revision"]}
        )
    assert outcome.value["status"] == "applied"
    assert [f["source_file"] for f in pm.load_project("demo")["whole_source_files"]] == [
        "source/sequel.txt",
        "source/novel.txt",
    ]
    await _assert_no_generation(series)


# ---------------------------------------------------------------------------
# Replan candidate lifecycle.
# ---------------------------------------------------------------------------


def _seed_candidate(series: dict[str, Any]) -> str:
    pm: ProjectManager = series["pm"]
    candidate_id = create_replan_candidate(pm.get_project_path("demo"), episode=2, instructions="按句切")

    def fill(project: dict) -> None:
        project["episode_replan"]["episodes"] = [
            {"title": "新1", "hook": "", "source_range": {"source_file": "source/novel.txt", "start": 5, "end": 10}},
            {"title": "新2", "hook": "", "source_range": {"source_file": "source/novel.txt", "start": 10, "end": 13}},
        ]
        project["episode_replan"]["complete"] = True

    pm.update_project("demo", fill)
    return candidate_id


async def test_candidate_is_recovered_after_reconnect_and_adopted_without_planning(series) -> None:
    candidate_id = _seed_candidate(series)

    # A new client session reads the same candidate.
    read = await run_declared_tool(GET_EPISODE_REPLAN, _harness(series), {})
    assert read.problem is None
    assert read.value["replan"]["id"] == candidate_id
    assert read.value["replan"]["instructions"] == "按句切"
    assert read.value["generating"] is False

    # plan_episodes stays refused while the candidate is pending and points at the replan tools.
    refused = await run_declared_tool(PLAN_EPISODES, _harness(series), {})
    assert problem_of(refused).params["reason"] == "replan_candidate_pending"
    assert "get_episode_replan" in PLAN_EPISODES.description

    ctx = _harness(series)
    pending = await run_declared_tool(ADOPT_EPISODE_REPLAN, ctx, {"candidate_id": candidate_id})
    assert pending.value["status"] == "confirmation_required"
    assert pending.value["impact"]["text"]
    stale = await run_declared_tool(ADOPT_EPISODE_REPLAN, ctx, {"candidate_id": candidate_id, "revision": "stale"})
    assert stale.value["status"] == "confirmation_required"
    assert _ledger(series) == [1, 2, 3]

    adopted = await run_declared_tool(
        ADOPT_EPISODE_REPLAN,
        _harness(series),
        {"candidate_id": candidate_id, "revision": pending.value["impact"]["revision"]},
    )
    assert adopted.value == {"status": "adopted", "episodes": [4, 5], "deleted": []}
    assert _ledger(series) == [1, 4, 5, 3]
    assert (await run_declared_tool(GET_EPISODE_REPLAN, _harness(series), {})).value["replan"] is None
    await _assert_no_generation(series)


async def test_adoption_is_refused_while_a_replaced_episode_has_active_tasks(series) -> None:
    candidate_id = _seed_candidate(series)
    ctx = _harness(series)
    revision = (await run_declared_tool(ADOPT_EPISODE_REPLAN, ctx, {"candidate_id": candidate_id})).value["impact"][
        "revision"
    ]
    series["queue"].queued = [{"resource_id": "script_plan", "script_file": None, "payload": {"episode": 2}}]

    refused = await run_declared_tool(ADOPT_EPISODE_REPLAN, ctx, {"candidate_id": candidate_id, "revision": revision})

    assert problem_of(refused).code == "episode_replan_tasks_active"
    assert _ledger(series) == [1, 2, 3]


async def test_candidate_is_discarded_after_reconnect_without_touching_the_ledger(series) -> None:
    candidate_id = _seed_candidate(series)
    before = series["pm"].load_project("demo")["episodes"]

    unknown = await run_declared_tool(DISCARD_EPISODE_REPLAN, _harness(series), {"candidate_id": "missing"})
    assert problem_of(unknown).code == "episode_replan_candidate_not_found"

    discarded = await run_declared_tool(DISCARD_EPISODE_REPLAN, _harness(series), {"candidate_id": candidate_id})
    assert discarded.value == {"status": "discarded"}
    assert series["pm"].load_project("demo")["episodes"] == before
    assert (await run_declared_tool(GET_EPISODE_REPLAN, _harness(series), {})).value["replan"] is None
    await _assert_no_generation(series)


async def test_replan_dry_run_reports_scope_without_a_model_call(series) -> None:
    outcome = await run_declared_tool(START_EPISODE_REPLAN, _harness(series), {"episode_id": 2, "dry_run": True})

    assert outcome.problem is None
    assert outcome.value == {"status": "preview", "replaced": [2], "started": []}
    assert series["pm"].load_project("demo").get("episode_replan") is None
    await _assert_no_generation(series)
