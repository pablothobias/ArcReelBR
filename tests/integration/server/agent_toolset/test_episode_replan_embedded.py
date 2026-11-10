"""The embedded ArcReel Agent starts and continues a replan through the declared tools and receives the first window's
result. The text model is a fake planner generator; the queued window runs inline in place of the worker."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from lib.backends.text_backends.base import TextGenerationResult
from lib.episode.episode_planner import EpisodePlanner
from lib.episode.episode_replan import create_replan_candidate
from lib.generation.generation_queue import GenerationQueue
from lib.project.project_manager import ProjectManager
from server.agent_toolset.envelope import encode_outcome
from server.agent_toolset.episode_planning import CONTINUE_EPISODE_REPLAN, START_EPISODE_REPLAN
from server.tool_runtime import CallerContext, ReplanWindowResult, execute_queued_text_task
from tests.integration.server.agent_tool_support import ToolHarness, run_declared_tool

NOVEL = "少年下山。城里起火。夜雨。"
_ANCHORS = ("城里起火。", "夜雨。")


class _Generator:
    """Fake text model: one episode per anchor present in the window."""

    model = "fake-model"
    max_output_tokens = 64000

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, request: Any, project_name: str | None = None) -> TextGenerationResult:
        del project_name
        self.prompts.append(request.prompt)
        window = request.prompt.rsplit("---", 2)[-2]
        episodes = [
            {"title": f"新{index + 1}", "hook": "悬念", "end_anchor": anchor}
            for index, anchor in enumerate(_ANCHORS)
            if anchor in window
        ]
        body = json.dumps({"episodes": episodes}, ensure_ascii=False)
        return TextGenerationResult(text=body, provider="fake", model="fake-model")


def _cut(episode: int, start: int, end: int) -> dict[str, Any]:
    return {
        "episode": episode,
        "title": f"旧{episode}",
        "script_file": f"scripts/episode_{episode}.json",
        "source_origin": "whole_source",
        "source_range": {"source_file": "source/novel.txt", "start": start, "end": end},
        "ledger_status": "planned",
    }


@pytest.fixture
async def embedded(tmp_path: Path, db_factory, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    pm = ProjectManager(tmp_path / "projects")
    monkeypatch.setenv("ARCREEL_DATA_DIR", str(pm.data_root))
    pm.create_project("demo")
    pm.create_project_metadata("demo", "Demo", "Anime", "narration")
    episodes = [_cut(1, 0, 5), _cut(2, 5, 13)]
    pm.update_project(
        "demo",
        lambda project: project.update(
            whole_source_files=[{"source_file": "source/novel.txt"}], episodes=episodes, episode_id_high_water=2
        ),
    )
    source_dir = pm.get_project_path("demo") / "source"
    (source_dir / "novel.txt").write_text(NOVEL, encoding="utf-8")
    (source_dir / "episode_1.txt").write_text(NOVEL[0:5], encoding="utf-8")
    (source_dir / "episode_2.txt").write_text(NOVEL[5:13], encoding="utf-8")

    generator = _Generator()

    async def create(_cls, path):
        return await asyncio.to_thread(EpisodePlanner, path, generator=generator)

    monkeypatch.setattr(EpisodePlanner, "create", classmethod(create))
    queue = GenerationQueue(session_factory=db_factory)
    # Admission requires an online worker; the inline stand-in below executes windows instead of a running worker.
    assert await queue.acquire_or_renew_worker_lease(name="default", owner_id="inline-test-worker", ttl_seconds=60)

    async def run_inline(task_id: str, *, queue: GenerationQueue) -> dict[str, Any]:
        """Stand-in for the worker: execute the queued window with the embedded collaborators, then report it."""
        task = await queue.get_task(task_id)
        assert task is not None
        result = await execute_queued_text_task(task)
        return {**task, "status": "succeeded", "result": result}

    monkeypatch.setattr("server.tool_runtime.wait_for_task", run_inline)
    ctx = ToolHarness("demo", tmp_path, pm=pm, queue=queue, caller=CallerContext(user_id="default", source="embedded"))
    return {"ctx": ctx, "pm": pm, "generator": generator}


async def test_embedded_start_returns_the_first_window_result(embedded) -> None:
    ctx: ToolHarness = embedded["ctx"]

    outcome = await run_declared_tool(START_EPISODE_REPLAN, ctx, {"episode_id": 2, "instructions": "慢一点"})

    assert outcome.problem is None
    assert isinstance(outcome.value, ReplanWindowResult)
    assert (outcome.value.planned, outcome.value.total, outcome.value.complete) == (2, 2, True)
    assert encode_outcome(START_EPISODE_REPLAN, outcome).structured["episode_replan"]["planned"] == 2
    project = embedded["pm"].load_project("demo")
    assert [entry["episode"] for entry in project["episodes"]] == [1, 2]
    assert [draft["title"] for draft in project["episode_replan"]["episodes"]] == ["新1", "新2"]
    assert all("慢一点" in prompt for prompt in embedded["generator"].prompts)


async def test_embedded_continue_resumes_an_interrupted_candidate(embedded) -> None:
    ctx: ToolHarness = embedded["ctx"]
    pm: ProjectManager = embedded["pm"]
    candidate_id = create_replan_candidate(pm.get_project_path("demo"), episode=2, instructions="保留悬念")
    pm.update_project("demo", lambda project: project["episode_replan"].update(interrupted="failed"))

    outcome = await run_declared_tool(CONTINUE_EPISODE_REPLAN, ctx, {"candidate_id": candidate_id})

    assert outcome.problem is None
    assert isinstance(outcome.value, ReplanWindowResult)
    assert outcome.value.complete is True
    candidate = pm.load_project("demo")["episode_replan"]
    assert candidate["id"] == candidate_id
    assert candidate.get("interrupted") is None
    assert all("保留悬念" in prompt for prompt in embedded["generator"].prompts)
