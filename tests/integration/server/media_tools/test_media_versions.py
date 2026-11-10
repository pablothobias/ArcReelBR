"""list_media_versions / select_media_version through declaration entries, with native consumers checked after selection.

Real project files and version history; no provider is called and selection never enqueues tasks.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from lib.artifacts.artifact_manifest import ArtifactBasisDescriptor
from lib.artifacts.version_manager import VersionManager
from lib.project.project_manager import ProjectManager
from lib.speech.narration_config import TtsSynthesisSettings
from lib.speech.narration_delivery import build_narration_audio_basis_from_canonical_text
from server.agent_toolset.media_versions import LIST_MEDIA_VERSIONS, SELECT_MEDIA_VERSION
from server.media_tools import media_versions
from server.services.currency.media_version_selection import active_media_writer_tasks
from server.services.presentation.timeline_preview import _narration_audio
from tests.integration.server.agent_tool_support import ToolHarness, problem_of, run_declared_tool


def _add_audio_version(project_path: Path, unit_id: str, content: bytes) -> None:
    current = project_path / "audio" / f"segment_{unit_id}.wav"
    current.parent.mkdir(parents=True, exist_ok=True)
    current.write_bytes(content)
    settings = TtsSynthesisSettings(provider_id="fake", model_id="fake-tts", voice="v", speed=None)
    basis = ArtifactBasisDescriptor.from_basis(build_narration_audio_basis_from_canonical_text("narration", settings))
    VersionManager(project_path).add_version(
        "audio",
        unit_id,
        "narration",
        source_file=current,
        artifact_episode=1,
        artifact_audio_basis=basis.to_dict(),
        execution_script_file="episode_1.json",
        tts_actual_duration_seconds=3.0,
        tts_provider_id="fake",
        tts_model_id="fake-tts",
        tts_voice="v",
        tts_speed=None,
        tts_basis_digest=basis.digest,
    )


def _add_image_version(project_path: Path, resource_type: str, resource_id: str, rel: str, content: bytes) -> None:
    current = project_path / rel
    current.parent.mkdir(parents=True, exist_ok=True)
    current.write_bytes(content)
    VersionManager(project_path).add_version(
        resource_type, resource_id, f"prompt {content.decode()}", source_file=current
    )


@pytest.fixture
def ctx(tmp_path: Path) -> ToolHarness:
    """Sync fixture: narration project with a storyboard, a unit video pointer, a character and two versions of each media."""
    pm = ProjectManager(tmp_path)
    pm.create_project("demo")
    pm.create_project_metadata("demo", "Demo", "Anime", "narration")
    pm.save_script(
        "demo",
        {
            "episode": 1,
            "title": "E1",
            "content_mode": "narration",
            "segments": [
                {
                    "segment_id": "E1S01",
                    "novel_text": "narration",
                    "characters_in_segment": ["Alice"],
                    "generated_assets": {
                        "storyboard_image": "storyboards/scene_E1S01.png",
                        "video_clip": "videos/scene_E1S01.mp4",
                    },
                }
            ],
        },
        "episode_1.json",
        validate=False,
    )
    pm.add_character("demo", "Alice", "A heroine")
    project_path = pm.get_project_path("demo")
    for content in (b"sb-1", b"sb-2"):
        _add_image_version(project_path, "storyboards", "E1S01", "storyboards/scene_E1S01.png", content)
    for content in (b"alice-1", b"alice-2"):
        _add_image_version(project_path, "characters", "Alice", "characters/Alice.png", content)
    pm.update_project_character_sheet("demo", "Alice", "characters/Alice.png")
    for content in (b"audio-1", b"audio-2"):
        _add_audio_version(project_path, "E1S01", content)
    return ToolHarness("demo", tmp_path, pm)


async def _tasks(ctx: ToolHarness) -> int:
    """Tasks of this test's project root; the queue database outlives one test, so tests cancel what they enqueue."""
    listing = await ctx.queue.list_tasks(project_name=ctx.project_name, page_size=500)
    return sum(1 for task in listing["items"] if task["status"] in {"queued", "running"})


async def _read(path: Path) -> bytes:
    return await asyncio.to_thread(path.read_bytes)


async def test_list_reports_versions_provenance_and_currency(ctx: ToolHarness) -> None:
    out = await run_declared_tool(LIST_MEDIA_VERSIONS, ctx, {"kind": "narration_audio", "id": "E1S01"})

    assert out.problem is None, out.problem
    assert out.value["current_version"] == 2
    assert [v["version"] for v in out.value["versions"]] == [1, 2]
    first = out.value["versions"][0]
    assert first["restorable"] is True
    assert first["provenance_verified"] is True
    assert len(first["sha256"]) == 64
    assert "file" not in first
    assert "file_url" not in first
    assert out.value["artifact_path"] == "audio/segment_E1S01.wav"


async def test_selecting_earlier_narration_audio_is_what_the_timeline_consumes(ctx: ToolHarness) -> None:
    out = await run_declared_tool(
        SELECT_MEDIA_VERSION,
        ctx,
        {"kind": "narration_audio", "id": "E1S01", "version": 1, "expected_current_version": 2},
    )

    assert out.problem is None, out.problem
    assert out.value["changed"] is True
    assert out.value["previous_version"] == 2
    assert out.value["current_version"] == 1
    assert await _read(ctx.project_path / "audio" / "segment_E1S01.wav") == b"audio-1"
    versions = await asyncio.to_thread(VersionManager, ctx.project_path)
    preview = await asyncio.to_thread(_narration_audio, ctx.project_path, versions, "E1S01")
    assert preview is not None
    assert preview.version == 1
    assert preview.path == "audio/segment_E1S01.wav"
    script = await asyncio.to_thread(ctx.pm.load_script_readonly, "demo", "episode_1.json")
    assert script["segments"][0]["generated_assets"]["narration_audio"] == "audio/segment_E1S01.wav"
    assert await _tasks(ctx) == 0


async def test_selecting_an_earlier_storyboard_feeds_the_video_start_frame(ctx: ToolHarness) -> None:
    out = await run_declared_tool(SELECT_MEDIA_VERSION, ctx, {"kind": "storyboard", "id": "E1S01", "version": 1})

    assert out.problem is None, out.problem
    assert out.value["current_version"] == 1
    script = await asyncio.to_thread(ctx.pm.load_script_readonly, "demo", "episode_1.json")
    pointer = script["segments"][0]["generated_assets"]["storyboard_image"]
    # The video task reads its start image from this script pointer.
    assert await _read(ctx.project_path / pointer) == b"sb-1"
    assert [d["kind"] for d in out.value["dependents"]] == ["unit_video"]
    assert await _tasks(ctx) == 0


async def test_selecting_an_earlier_character_sheet_reports_storyboards_using_it(ctx: ToolHarness) -> None:
    out = await run_declared_tool(SELECT_MEDIA_VERSION, ctx, {"kind": "character", "id": "Alice", "version": 1})

    assert out.problem is None, out.problem
    assert await _read(ctx.project_path / "characters" / "Alice.png") == b"alice-1"
    project = await asyncio.to_thread(ctx.pm.load_project, "demo")
    assert project["characters"]["Alice"]["character_sheet"] == "characters/Alice.png"
    assert [(d["kind"], d["id"]) for d in out.value["dependents"]] == [("storyboard", "E1S01")]


async def test_selection_refuses_while_a_generation_task_targets_the_resource(ctx: ToolHarness) -> None:
    task = await ctx.queue.enqueue_task(
        project_name=ctx.project_name,
        task_type="storyboard",
        media_type="image",
        resource_id="E1S01",
        payload={"prompt": "p"},
        script_file="episode_1.json",
        source="webui",
        user_id=ctx.caller.user_id,
    )

    try:
        out = await run_declared_tool(SELECT_MEDIA_VERSION, ctx, {"kind": "storyboard", "id": "E1S01", "version": 1})
    finally:
        await ctx.queue.cancel_task(task["task_id"])

    problem = problem_of(out)
    assert problem.code == "active_task_conflict"
    assert len(problem.params["task_ids"]) == 1
    assert await asyncio.to_thread(VersionManager(ctx.project_path).get_current_version, "storyboards", "E1S01") == 2


@pytest.mark.parametrize(
    ("arguments", "code"),
    [
        ({"kind": "storyboard", "id": "E1S99", "version": 1}, "resource_not_found"),
        ({"kind": "character", "id": "Nobody", "version": 1}, "resource_not_found"),
        ({"kind": "grid_composite", "id": "grid_000000000000", "version": 1}, "resource_not_found"),
        ({"kind": "storyboard", "id": "E1S01", "version": 9}, "version_not_found"),
        ({"kind": "storyboard", "id": "E1S01", "version": 1, "expected_current_version": 1}, "version_conflict"),
        ({"kind": "character_voice", "id": "Alice", "version": 1}, "invalid_request"),
    ],
)
async def test_selection_refusals_change_nothing(ctx: ToolHarness, arguments: dict[str, Any], code: str) -> None:
    out = await run_declared_tool(SELECT_MEDIA_VERSION, ctx, arguments)

    assert problem_of(out).code == code
    assert await asyncio.to_thread(VersionManager(ctx.project_path).get_current_version, "storyboards", "E1S01") == 2
    assert await _tasks(ctx) == 0


async def test_version_not_found_lists_available_versions(ctx: ToolHarness) -> None:
    out = await run_declared_tool(SELECT_MEDIA_VERSION, ctx, {"kind": "narration_audio", "id": "E1S01", "version": 5})

    assert problem_of(out).params == {"available_versions": [1, 2]}


async def test_selecting_the_current_version_is_a_no_op(ctx: ToolHarness) -> None:
    out = await run_declared_tool(SELECT_MEDIA_VERSION, ctx, {"kind": "storyboard", "id": "E1S01", "version": 2})

    assert out.problem is None
    assert out.value["changed"] is False


async def test_missing_snapshot_file_fails_without_selecting(ctx: ToolHarness) -> None:
    def drop_first_snapshot() -> None:
        records = VersionManager(ctx.project_path).get_versions("storyboards", "E1S01")["versions"]
        (ctx.project_path / records[0]["file"]).unlink()

    await asyncio.to_thread(drop_first_snapshot)

    out = await run_declared_tool(SELECT_MEDIA_VERSION, ctx, {"kind": "storyboard", "id": "E1S01", "version": 1})

    assert out.problem is not None
    assert await asyncio.to_thread(VersionManager(ctx.project_path).get_current_version, "storyboards", "E1S01") == 2
    assert await _read(ctx.project_path / "storyboards" / "scene_E1S01.png") == b"sb-2"


async def test_selection_refuses_when_a_concurrent_commit_lands_after_the_version_check(
    ctx: ToolHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The observed current version is compared again under the versions lock inside the restore transaction:
    a real generation-style commit between the handler's read and its write wins, and selection writes nothing."""

    async def probe_then_concurrent_commit(queue, **kwargs):
        found = await active_media_writer_tasks(queue, **kwargs)
        await asyncio.to_thread(
            lambda: _add_image_version(ctx.project_path, "storyboards", "E1S01", "storyboards/scene_E1S01.png", b"sb-3")
        )
        return found

    monkeypatch.setattr(media_versions, "active_media_writer_tasks", probe_then_concurrent_commit)

    out = await run_declared_tool(
        SELECT_MEDIA_VERSION,
        ctx,
        {"kind": "storyboard", "id": "E1S01", "version": 1, "expected_current_version": 2},
    )

    problem = problem_of(out)
    assert problem.code == "version_conflict"
    assert problem.params == {"current_version": 3}
    project_path = await asyncio.to_thread(lambda: ctx.project_path)
    assert await asyncio.to_thread(VersionManager(project_path).get_current_version, "storyboards", "E1S01") == 3
    assert await _read(project_path / "storyboards" / "scene_E1S01.png") == b"sb-3"
