"""Grid composite review through declaration entries: list, inspect before split, replace, guarded split, restore.

Real project files and the real split service; no provider is called and no generation task is enqueued.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lib.artifacts.version_manager import VersionManager
from lib.project.project_manager import ProjectManager
from lib.script.grid.grid_manager import GridManager
from lib.script.grid.models import GridGeneration
from server.agent_toolset.grid_storyboards import INSPECT_GRID, LIST_GRIDS, REPLACE_GRID_COMPOSITE, SPLIT_GRIDS
from server.agent_toolset.media_versions import SELECT_MEDIA_VERSION
from server.media_tools import grid_review
from server.services.grid.grid_composite import install_grid_composite
from server.services.media_transport import (
    MediaTransportError,
    append_upload_chunk,
    begin_upload,
    resolve_staged_upload,
)
from tests.fakes import use_project_manager
from tests.integration.server.agent_tool_support import ToolHarness, problem_of, run_declared_tool


def _png(color: tuple[int, int, int], size: tuple[int, int] = (200, 360)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _script() -> dict[str, Any]:
    return {
        "episode": 1,
        "title": "E1",
        "content_mode": "narration",
        "segments": [
            {
                "segment_id": f"E1S{i:02d}",
                "episode": 1,
                "segment_break": False,
                "duration_seconds": 4,
                "novel_text": "text",
                "characters_in_segment": [],
                "scenes": [],
                "props": [],
                "image_prompt": {"scene": f"scene{i}", "composition": {"shot_type": "medium"}},
                "video_prompt": {"action": f"action{i}", "camera_motion": "static"},
                "generated_assets": {"storyboard_image": None, "video_clip": None, "status": "pending"},
            }
            for i in range(1, 5)
        ],
    }


@pytest.fixture
def grid_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ToolHarness, GridGeneration]:
    """Sync fixture (outside the event loop): grid-enabled narration project with one ready-to-fill grid record."""
    pm = ProjectManager(tmp_path)
    pm.create_project("demo")
    pm.create_project_metadata(
        "demo", "Demo", "Anime", "narration", extras={"generation_mode": "storyboard", "grid_storyboard": True}
    )
    pm.save_script("demo", _script(), "episode_1.json", validate=False)
    grid = GridGeneration.create(
        episode=1,
        script_file="episode_1.json",
        scene_ids=["E1S01", "E1S02", "E1S03", "E1S04"],
        rows=2,
        cols=2,
        grid_size="grid_4",
        provider="p",
        model="m",
        video_aspect_ratio="9:16",
    )
    grid.status = "completed"
    GridManager(pm.get_project_path("demo")).save(grid)
    use_project_manager(monkeypatch, pm)
    return ToolHarness("demo", tmp_path, pm), grid


async def _replace(ctx: ToolHarness, grid_id: str, content: bytes, **extra: Any):
    return await run_declared_tool(
        REPLACE_GRID_COMPOSITE,
        ctx,
        {
            "grid_id": grid_id,
            "filename": "approved.png",
            "content_base64": base64.b64encode(content).decode(),
            **extra,
        },
    )


async def _task_count(ctx: ToolHarness) -> int:
    """Active tasks for the project; the queue database outlives one test, so tests cancel what they enqueue."""
    listing = await ctx.queue.list_tasks(project_name=ctx.project_name, page_size=500)
    return sum(1 for task in listing["items"] if task["status"] in {"queued", "running"})


async def test_inspect_returns_the_composite_before_split_and_split_uses_the_reviewed_version(grid_project) -> None:
    ctx, grid = grid_project
    first = await _replace(ctx, grid.id, _png((200, 10, 10)))
    assert first.problem is None, first.problem
    second = await _replace(ctx, grid.id, _png((10, 10, 200)), expected_current_version=first.value["version"])
    assert second.problem is None, second.problem
    assert second.value["storyboard_cells_changed"] is False
    assert second.value["state"] == "awaiting_split"

    listed = await run_declared_tool(LIST_GRIDS, ctx, {})
    assert listed.problem is None, listed.problem
    assert listed.value["writable"] is True
    assert listed.value["capability"]["max_cell_count"] >= 4
    [entry] = listed.value["grids"]
    assert entry["state"] == "awaiting_split"
    assert entry["current_version"] == second.value["version"]

    inspected = await run_declared_tool(INSPECT_GRID, ctx, {"grid_id": grid.id})
    assert inspected.problem is None, inspected.problem
    record = inspected.value.record
    assert inspected.value.jpeg is not None
    assert INSPECT_GRID.images(inspected.value)[0].mime_type == "image/jpeg"
    composite_file = ctx.project_path / "grids" / f"{grid.id}.png"
    current_sha = hashlib.sha256(await asyncio.to_thread(composite_file.read_bytes)).hexdigest()
    assert record["composite"]["sha256"] == current_sha
    assert record["composite"]["version"] == second.value["version"]
    assert [c["scene_id"] for c in record["cells"]] == ["E1S01", "E1S02", "E1S03", "E1S04"]
    assert record["split_guard"] == {"grid_id": grid.id, "sha256": current_sha, "version": second.value["version"]}

    # Historical composite is viewable for comparison but offers no split guard.
    old = await run_declared_tool(INSPECT_GRID, ctx, {"grid_id": grid.id, "version": first.value["version"]})
    assert old.value.record["composite"]["sha256"] == first.value["sha256"]
    assert "split_guard" not in old.value.record

    # A split bound to the composite the user did not approve is refused and writes nothing.
    stale = await run_declared_tool(
        SPLIT_GRIDS,
        ctx,
        {"grid_ids": [grid.id], "reviewed_composites": [{"grid_id": grid.id, "sha256": first.value["sha256"]}]},
    )
    assert problem_of(stale).params["results"][0]["status"] == "composite_changed"
    assert not await asyncio.to_thread((ctx.project_path / "storyboards" / "scene_E1S01.png").exists)
    stale_version = await run_declared_tool(
        SPLIT_GRIDS,
        ctx,
        {
            "grid_ids": [grid.id],
            "reviewed_composites": [{"grid_id": grid.id, "sha256": current_sha, "version": first.value["version"]}],
        },
    )
    assert problem_of(stale_version).params["results"][0]["status"] == "composite_changed"

    split = await run_declared_tool(
        SPLIT_GRIDS, ctx, {"grid_ids": [grid.id], "reviewed_composites": [record["split_guard"]]}
    )
    assert split.problem is None, split.problem
    assert split.value["results"][0]["status"] == "split"
    assert sorted(split.value["results"][0]["updated_scene_ids"]) == ["E1S01", "E1S02", "E1S03", "E1S04"]
    assert await _task_count(ctx) == 0


async def test_replacing_a_split_composite_resets_split_without_touching_cells(grid_project) -> None:
    ctx, grid = grid_project
    installed = await _replace(ctx, grid.id, _png((50, 120, 50)))
    guard = installed.value["split_guard"]
    assert (
        await run_declared_tool(SPLIT_GRIDS, ctx, {"grid_ids": [grid.id], "reviewed_composites": [guard]})
    ).problem is None
    cell = ctx.project_path / "storyboards" / "scene_E1S01.png"
    cell_before = await asyncio.to_thread(cell.read_bytes)

    replaced = await _replace(ctx, grid.id, _png((250, 250, 0)))

    assert replaced.problem is None, replaced.problem
    assert replaced.value["previous_split_at"] is not None
    assert replaced.value["split_reset"] is True
    assert await asyncio.to_thread(cell.read_bytes) == cell_before
    saved = await asyncio.to_thread(GridManager(ctx.project_path).get, grid.id)
    assert saved.split_at is None
    assert saved.status == "completed"
    assert await _task_count(ctx) == 0


async def test_restoring_a_composite_version_resets_split_and_never_splits(grid_project) -> None:
    ctx, grid = grid_project
    first = await _replace(ctx, grid.id, _png((1, 2, 3)))
    second = await _replace(ctx, grid.id, _png((4, 5, 6)))
    split = await run_declared_tool(
        SPLIT_GRIDS, ctx, {"grid_ids": [grid.id], "reviewed_composites": [second.value["split_guard"]]}
    )
    assert split.problem is None
    cell = ctx.project_path / "storyboards" / "scene_E1S02.png"
    cell_before = await asyncio.to_thread(cell.read_bytes)

    restored = await run_declared_tool(
        SELECT_MEDIA_VERSION,
        ctx,
        {"kind": "grid_composite", "id": grid.id, "version": first.value["version"]},
    )

    assert restored.problem is None, restored.problem
    assert restored.value["current_version"] == first.value["version"]
    assert restored.value["split_reset"] is True
    assert restored.value["state"] == "awaiting_split"
    assert restored.value["storyboard_cells_changed"] is False
    assert await asyncio.to_thread(cell.read_bytes) == cell_before
    inspected = await run_declared_tool(INSPECT_GRID, ctx, {"grid_id": grid.id})
    assert inspected.value.record["composite"]["sha256"] == first.value["sha256"]
    assert inspected.value.record["state"] == "awaiting_split"
    assert await _task_count(ctx) == 0


async def test_replace_and_restore_refuse_a_grid_with_an_active_generation_task(grid_project) -> None:
    ctx, grid = grid_project
    first = await _replace(ctx, grid.id, _png((9, 9, 9)))
    await _replace(ctx, grid.id, _png((8, 8, 8)))

    def mark_generating() -> None:
        record = GridManager(ctx.project_path).get(grid.id)
        record.status = "generating"
        GridManager(ctx.project_path).save(record)

    await asyncio.to_thread(mark_generating)
    task = await ctx.queue.enqueue_task(
        project_name=ctx.project_name,
        task_type="grid",
        media_type="image",
        resource_id=grid.id,
        payload={"scene_ids": grid.scene_ids},
        script_file=grid.script_file,
        source="webui",
        user_id=ctx.caller.user_id,
    )
    versions_before = await asyncio.to_thread(VersionManager(ctx.project_path).get_current_version, "grids", grid.id)

    try:
        replace = await _replace(ctx, grid.id, _png((7, 7, 7)))
        restore = await run_declared_tool(
            SELECT_MEDIA_VERSION, ctx, {"kind": "grid_composite", "id": grid.id, "version": first.value["version"]}
        )
    finally:
        await ctx.queue.cancel_task(task["task_id"])

    assert problem_of(replace).code == "grid_generation_in_progress"
    assert problem_of(restore).code == "active_task_conflict"
    assert (
        await asyncio.to_thread(VersionManager(ctx.project_path).get_current_version, "grids", grid.id)
        == versions_before
    )


async def test_replace_rejects_bad_input_without_writing(grid_project) -> None:
    ctx, grid = grid_project

    not_image = await _replace(ctx, grid.id, b"not-an-image")
    bad_base64 = await run_declared_tool(
        REPLACE_GRID_COMPOSITE, ctx, {"grid_id": grid.id, "filename": "a.png", "content_base64": "%%%"}
    )
    missing = await _replace(ctx, "grid_000000000000", _png((1, 1, 1)))
    conflict = await _replace(ctx, grid.id, _png((1, 1, 1)), expected_current_version=3)

    assert problem_of(not_image).code == "invalid_image_file"
    assert problem_of(bad_base64).code == "invalid_request"
    assert problem_of(missing).code == "grid_not_found"
    assert problem_of(conflict).code == "version_conflict"
    assert await asyncio.to_thread(VersionManager(ctx.project_path).get_current_version, "grids", grid.id) == 0


async def test_inspect_reports_missing_composite_and_unknown_grid(grid_project) -> None:
    ctx, grid = grid_project

    inspected = await run_declared_tool(INSPECT_GRID, ctx, {"grid_id": grid.id})
    unknown = await run_declared_tool(INSPECT_GRID, ctx, {"grid_id": "grid_000000000000"})
    no_version = await run_declared_tool(INSPECT_GRID, ctx, {"grid_id": grid.id, "version": 2})

    assert inspected.problem is None
    assert inspected.value.jpeg is None
    assert inspected.value.record["composite"]["status"] == "missing"
    assert "split_guard" not in inspected.value.record
    assert problem_of(unknown).code == "grid_not_found"
    assert problem_of(no_version).code == "version_not_found"


async def test_split_guard_must_cover_every_grid(grid_project) -> None:
    ctx, grid = grid_project

    out = await run_declared_tool(
        SPLIT_GRIDS,
        ctx,
        {"grid_ids": [grid.id], "reviewed_composites": [{"grid_id": "grid_000000000000", "sha256": "a" * 64}]},
    )

    assert problem_of(out).params == {"missing": [grid.id], "unexpected": ["grid_000000000000"]}


async def test_ad_projects_can_read_but_not_write_grids(grid_project) -> None:
    ctx, grid = grid_project

    def make_ad() -> None:
        project = ctx.pm.load_project("demo")
        project["content_mode"] = "ad"
        ctx.pm.save_project("demo", project)

    await asyncio.to_thread(make_ad)

    listed = await run_declared_tool(LIST_GRIDS, ctx, {})
    replaced = await _replace(ctx, grid.id, _png((3, 3, 3)))

    assert listed.value["writable"] is False
    assert listed.value["write_block"] == "ad_grid_not_supported"
    assert problem_of(replaced).code == "ad_grid_not_supported"


async def test_replace_accepts_a_staged_upload_and_releases_it(grid_project) -> None:
    ctx, grid = grid_project
    content = _png((12, 34, 56), size=(400, 720))
    status = await begin_upload(
        ctx.pm,
        "demo",
        filename="big.png",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        purpose="grid_composite",
        client_id=None,
    )
    await append_upload_chunk(ctx.pm, "demo", status.upload_id, index=0, content=content, client_id=None)

    out = await run_declared_tool(
        REPLACE_GRID_COMPOSITE,
        ctx,
        {"grid_id": grid.id, "filename": "big.png", "staged_upload_id": status.upload_id},
    )

    assert out.problem is None, out.problem
    assert out.value["version"] == 1
    with pytest.raises(MediaTransportError) as released:
        await resolve_staged_upload(ctx.pm, "demo", status.upload_id)
    assert released.value.code == "upload_not_found"
    missing = await run_declared_tool(
        REPLACE_GRID_COMPOSITE, ctx, {"grid_id": grid.id, "filename": "big.png", "staged_upload_id": status.upload_id}
    )
    assert problem_of(missing).code == "upload_not_found"


async def test_replace_refuses_an_upload_staged_for_another_purpose(grid_project) -> None:
    ctx, grid = grid_project
    content = _png((12, 34, 56), size=(400, 720))
    status = await begin_upload(
        ctx.pm,
        "demo",
        filename="big.png",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        purpose="storyboard_image",
        client_id=None,
    )
    await append_upload_chunk(ctx.pm, "demo", status.upload_id, index=0, content=content, client_id=None)

    out = await run_declared_tool(
        REPLACE_GRID_COMPOSITE,
        ctx,
        {"grid_id": grid.id, "filename": "big.png", "staged_upload_id": status.upload_id},
    )

    assert problem_of(out).code == "upload_purpose_mismatch"
    listed = await run_declared_tool(LIST_GRIDS, ctx, {})
    assert listed.problem is None
    [entry] = listed.value["grids"]
    assert entry["current_version"] is None
    assert not (ctx.project_path / "grids" / f"{grid.id}.png").exists()


@pytest.mark.parametrize(
    "sources",
    [{}, {"content_base64": "aGk=", "staged_upload_id": "abc"}],
    ids=["neither", "both"],
)
async def test_replace_requires_exactly_one_byte_source(grid_project, sources: dict[str, str]) -> None:
    ctx, grid = grid_project

    out = await run_declared_tool(REPLACE_GRID_COMPOSITE, ctx, {"grid_id": grid.id, "filename": "a.png", **sources})

    assert problem_of(out).code == "invalid_request"


async def test_replace_refuses_when_a_concurrent_upload_lands_after_the_version_check(
    grid_project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The expected version is compared again inside the commit lock: a concurrent native upload between the handler's
    read and its commit wins, and this replacement writes nothing."""
    ctx, grid = grid_project
    first = await _replace(ctx, grid.id, _png((1, 1, 1)))
    concurrent_bytes = _png((99, 0, 0))
    original_idle = grid_review.ensure_grid_idle

    async def idle_then_concurrent_upload(queue, project_name, current_grid, user_id) -> None:
        await original_idle(queue, project_name, current_grid, user_id)
        project = await asyncio.to_thread(ctx.pm.load_project, "demo")
        project_path = await asyncio.to_thread(lambda: ctx.project_path)
        await install_grid_composite(
            queue=queue,
            project_name=project_name,
            project=project,
            project_path=project_path,
            grid=current_grid,
            content=concurrent_bytes,
            filename="web.png",
            user_id=user_id,
            change_source="webui",
        )

    monkeypatch.setattr(grid_review, "ensure_grid_idle", idle_then_concurrent_upload)

    out = await _replace(ctx, grid.id, _png((0, 99, 0)), expected_current_version=first.value["version"])

    problem = problem_of(out)
    assert problem.code == "version_conflict"
    assert problem.params == {"current_version": first.value["version"] + 1}
    project_path = await asyncio.to_thread(lambda: ctx.project_path)
    versions = await asyncio.to_thread(VersionManager(project_path).get_versions, "grids", grid.id)
    assert [v["version"] for v in versions["versions"]] == [1, 2]
    composite = await asyncio.to_thread((project_path / "grids" / f"{grid.id}.png").read_bytes)
    assert hashlib.sha256(composite).hexdigest() == versions["versions"][1]["content_digest"]
