"""MCP-level authoring/preview tools through the shared declaration entry with real project files.

Covers ``get_prompt_preview`` for reference-video units, ``start_blank_script``, ``get_asset_prompt_preview`` and
``generate_project_overview``. Every case asserts that no generation task reaches the queue; the overview case uses a
fake text generator only."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.generation.generation_queue import GenerationQueue
from lib.infra.content_digest import sha256_file_with_size
from lib.project.project_manager import ProjectManager
from lib.project.project_migrations.runner import migrate_project_dir
from lib.project.project_migrations.v7_to_v8_artifact_manifest import migrate_v7_to_v8
from lib.script.draft_quarantine import QUARANTINE_KIND_DRAMA_SCRIPT_PLAN, write_quarantine
from server.agent_toolset.authoring_previews import (
    GENERATE_PROJECT_OVERVIEW,
    GET_ASSET_PROMPT_PREVIEW,
    START_BLANK_SCRIPT,
)
from server.agent_toolset.envelope import json_value
from server.agent_toolset.orientation import GET_PROMPT_PREVIEW
from server.auth import CurrentUserInfo, get_current_user
from server.error_handlers import register_error_handlers
from server.routers import reference_videos as router_mod
from tests.auth_deps import AUTH_DEPENDENCIES
from tests.fakes import (
    fake_reference_request_facts,
    fake_reference_request_projector,
    use_project_manager,
    use_text_generator,
)
from tests.integration.server.agent_tool_support import ToolHarness, run_declared_tool

_UNIT_TEXT = "@[Tavern] doorway, @[Zed/Armor] pushes the door open.\n@[Zed/Armor]: {Come in}\n@[Lee]: {Fine}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _build_project(tmp_path: Path, *, generation_mode: str, script: dict[str, Any] | None) -> Path:
    project_dir = tmp_path / "projects" / "demo"
    characters = {
        "Zed": {
            "description": "Young swordsman",
            "character_sheet": "characters/Zed.png",
            "reference_audio": "characters/refs_audio/Zed.mp3",
            "voice_style": "Deep",
            "derivatives": {
                "Armor": {"description": "Black fighting outfit", "character_sheet": "characters/Zed-Armor.png"}
            },
        },
        "Lee": {
            "description": "Innkeeper",
            "character_sheet": "characters/Lee.png",
            "reference_audio": "characters/refs_audio/Lee.mp3",
        },
    }
    _write_json(
        project_dir / "project.json",
        {
            "schema_version": 7,
            "title": "T",
            "content_mode": "drama",
            "generation_mode": generation_mode,
            "style": "Ink wash",
            "style_description": "Warm cinematic texture",
            "characters": characters,
            "scenes": {"Tavern": {"description": "Old tavern", "scene_sheet": "scenes/Tavern.png"}},
            "props": {},
            "episodes": [{"episode": 1, "title": "E1", "script_file": "scripts/episode_1.json"}],
        },
    )
    for relative, data in {
        "characters/Zed.png": b"base",
        "characters/Zed-Armor.png": b"derivative",
        "characters/Lee.png": b"li",
        "scenes/Tavern.png": b"tavern",
        "characters/refs_audio/Zed.mp3": b"audio-zed",
        "characters/refs_audio/Lee.mp3": b"audio-lee",
    }.items():
        (project_dir / relative).parent.mkdir(parents=True, exist_ok=True)
        (project_dir / relative).write_bytes(data)
    (project_dir / "scripts").mkdir(exist_ok=True)
    if script is not None:
        _write_json(project_dir / "scripts" / "episode_1.json", script)
    migrate_v7_to_v8(project_dir)
    migrate_project_dir(project_dir)
    return project_dir


def _reference_script() -> dict[str, Any]:
    return {
        "episode": 1,
        "title": "E1",
        "content_mode": "drama",
        "generation_mode": "reference_video",
        "summary": "x",
        "novel": {"title": "t", "chapter": "c"},
        "duration_seconds": 3,
        "video_units": [{"unit_id": "E1U1", "text": _UNIT_TEXT, "duration_seconds": 3}],
    }


@pytest.fixture
def preview_queue(db_factory) -> GenerationQueue:
    return GenerationQueue(session_factory=db_factory)


def _harness(tmp_path: Path, queue: GenerationQueue) -> ToolHarness:
    return ToolHarness("demo", tmp_path, ProjectManager(tmp_path), queue=queue)


async def _no_tasks(queue: GenerationQueue) -> None:
    listed = await queue.list_tasks(project_name="demo")
    assert listed["total"] == 0, listed["items"]


def _files_unchanged(project_dir: Path, before: dict[Path, bytes]) -> bool:
    after = {path: path.read_bytes() for path in project_dir.rglob("*") if path.is_file()}
    return after == before


def _use_projection(monkeypatch: pytest.MonkeyPatch, **facts: Any) -> None:
    projector = fake_reference_request_projector(request_facts=fake_reference_request_facts(durations=(3,), **facts))
    monkeypatch.setattr("server.services.admission.reference_prompt_preview.project_reference_unit_request", projector)
    monkeypatch.setattr("server.routers.reference_videos.project_reference_unit_request", projector)


# ---------------------------------------------------------------------------
# MCP-002 / MCP-007: reference-video unit prompt preview
# ---------------------------------------------------------------------------


async def test_reference_unit_preview_reports_send_order_bindings_and_digests(tmp_path, preview_queue, monkeypatch):
    project_dir = _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    _use_projection(monkeypatch, voice_consistency="native", max_reference_audio_count=2)
    before = {path: path.read_bytes() for path in project_dir.rglob("*") if path.is_file()}
    ctx = _harness(tmp_path, preview_queue)

    outcome = await run_declared_tool(GET_PROMPT_PREVIEW, ctx, {"script": "episode_1.json", "item_id": "E1U1"})

    assert outcome.problem is None, outcome.problem
    preview = json_value(outcome.value)
    assert preview["generation_mode"] == "reference_video"
    assert preview["preview_basis"] == "current_configuration"
    assert preview["captured_submission"] is None
    assert preview["storyboard_image"]["unavailable"] == "prompt_preview_not_applicable"
    text = preview["video"]["text"]
    # Reference markers use the English form Seedance documents, in send order (resolves MCP-007).
    assert "<Tavern>@Image 1, <Zed/Armor>@Image 2." in text
    assert "@Audio 1" in text
    assert "@Audio 2" in text
    assert "@图片" not in text
    assert "@音频" not in text
    request = preview["reference_video"]
    images = request["images"]
    assert [(image["marker"], image["type"], image["name"]) for image in images] == [
        ("@Image 1", "scene", "Tavern"),
        ("@Image 2", "character", "Zed/Armor"),
    ]
    derivative = images[1]
    assert (derivative["base_name"], derivative["is_derivative"], derivative["kind"]) == ("Zed", True, "sheet")
    assert derivative["artifact_path"] == "characters/Zed-Armor.png"
    assert derivative["sha256"] == sha256_file_with_size(project_dir / "characters/Zed-Armor.png")[0]
    # Speech binds to base characters; audio numbers follow first speaker mention and match the request order.
    audio = request["audio"]
    assert [(entry["marker"], entry["speaker"], entry["artifact_path"]) for entry in audio] == [
        ("@Audio 1", "Zed", "characters/refs_audio/Zed.mp3"),
        ("@Audio 2", "Lee", "characters/refs_audio/Lee.mp3"),
    ]
    assert all(entry["sha256"] for entry in audio)
    # Every reported marker is literally present in the rendered text: preview rows and prompt cannot drift.
    assert all(entry["marker"] in text for entry in [*images, *audio])
    assert request["provider_id"] == "fake"
    assert request["request_duration_seconds"] == 3
    assert _files_unchanged(project_dir, before)
    await _no_tasks(preview_queue)


async def test_reference_unit_preview_matches_the_web_unit_preview_text(tmp_path, preview_queue, monkeypatch):
    _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    _use_projection(monkeypatch, voice_consistency="native", max_reference_audio_count=2)
    ctx = _harness(tmp_path, preview_queue)
    use_project_manager(monkeypatch, ctx.pm)
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router_mod.router, prefix="/api/v1", dependencies=AUTH_DEPENDENCIES)
    app.dependency_overrides[get_current_user] = lambda: CurrentUserInfo(id="u1", sub="test", role="admin")
    web = TestClient(app).post(
        "/api/v1/projects/demo/reference-videos/episodes/1/units/E1U1/prompt-preview", json={"prompt": _UNIT_TEXT}
    )

    outcome = await run_declared_tool(GET_PROMPT_PREVIEW, ctx, {"script": "episode_1.json", "item_id": "E1U1"})

    assert web.status_code == 200, web.text
    assert outcome.problem is None
    assert outcome.value.video.text == web.json()["text"]
    assert [(i.type, i.name, i.artifact_path) for i in outcome.value.reference_video.images] == [
        (ref["type"], ref["name"], ref["path"]) for ref in web.json()["references"]
    ]


async def test_reference_unit_preview_reports_clamped_references_and_warnings(tmp_path, preview_queue, monkeypatch):
    _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    _use_projection(monkeypatch, max_reference_images=1)

    outcome = await run_declared_tool(
        GET_PROMPT_PREVIEW, _harness(tmp_path, preview_queue), {"script": "episode_1.json", "item_id": "E1U1"}
    )

    assert outcome.problem is None, outcome.problem
    request = outcome.value.reference_video
    assert [image.name for image in request.images] == ["Tavern"]
    assert {"type": "character", "name": "Zed/Armor", "reason": "clamped"} in request.unavailable_references
    assert any(warning["key"] == "reference_images_clamped" for warning in outcome.value.video.warnings)
    # Soft voice tier: no audio binding is sent, so no audio marker is promised.
    assert request.audio == ()
    assert "@音频" not in outcome.value.video.text
    await _no_tasks(preview_queue)


async def test_reference_unit_preview_unavailable_capability_is_a_stable_code(tmp_path, preview_queue, monkeypatch):
    from lib.generation.video_request_facts import VideoRequestFactsFailure

    _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    failure = VideoRequestFactsFailure("video_model_not_configured", ())
    projector = fake_reference_request_projector(
        request_facts=fake_reference_request_facts(failures={"r2v": failure, "i2v": failure})
    )
    monkeypatch.setattr("server.services.admission.reference_prompt_preview.project_reference_unit_request", projector)

    outcome = await run_declared_tool(
        GET_PROMPT_PREVIEW, _harness(tmp_path, preview_queue), {"script": "episode_1.json", "item_id": "E1U1"}
    )

    assert outcome.problem is None, outcome.problem
    assert outcome.value.video.text is None
    assert outcome.value.video.unavailable == "video_model_not_configured"
    assert outcome.value.reference_video is not None
    await _no_tasks(preview_queue)


async def test_unknown_reference_unit_is_item_not_found(tmp_path, preview_queue, monkeypatch):
    _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    _use_projection(monkeypatch)

    outcome = await run_declared_tool(
        GET_PROMPT_PREVIEW, _harness(tmp_path, preview_queue), {"script": "episode_1.json", "item_id": "E1U9"}
    )

    assert outcome.problem is not None
    assert outcome.problem.code == "item_not_found"


async def test_captured_submission_requires_a_task_of_this_entry(tmp_path, preview_queue, monkeypatch):
    _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    _use_projection(monkeypatch)
    ctx = _harness(tmp_path, preview_queue)

    missing = await run_declared_tool(
        GET_PROMPT_PREVIEW, ctx, {"script": "episode_1.json", "item_id": "E1U1", "task_id": "nope"}
    )

    assert missing.problem is not None
    assert missing.problem.code == "task_not_found"
    await _no_tasks(preview_queue)


async def _insert_task(
    db_factory,
    *,
    checkpoint: str | None,
    task_id: str = "t1",
    project_name: str = "demo",
    resource_id: str = "E1U1",
    user_id: str | None = None,
) -> None:
    from lib.db.models.task import Task

    owner = {} if user_id is None else {"user_id": user_id}

    async with db_factory() as session:
        session.add(
            Task(
                task_id=task_id,
                project_name=project_name,
                task_type="reference_video",
                media_type="video",
                resource_id=resource_id,
                script_file="scripts/episode_1.json",
                payload_json="{}",
                status="succeeded",
                source="webui",
                execution_checkpoint_json=checkpoint,
                queued_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                **owner,
            )
        )
        await session.commit()


async def test_captured_submission_hides_other_projects_tasks(tmp_path, preview_queue, monkeypatch, db_factory):
    _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    _use_projection(monkeypatch)
    ctx = _harness(tmp_path, preview_queue)
    await _insert_task(db_factory, checkpoint=None, task_id="foreign", project_name="other")
    await _insert_task(db_factory, checkpoint=None, task_id="sibling", resource_id="E1U2")
    await _insert_task(db_factory, checkpoint=None, task_id="stranger", user_id="another-user")
    args = {"script": "episode_1.json", "item_id": "E1U1"}

    foreign = await run_declared_tool(GET_PROMPT_PREVIEW, ctx, {**args, "task_id": "foreign"})
    stranger = await run_declared_tool(GET_PROMPT_PREVIEW, ctx, {**args, "task_id": "stranger"})
    sibling = await run_declared_tool(GET_PROMPT_PREVIEW, ctx, {**args, "task_id": "sibling"})

    # A task of another project answers exactly like an absent one: no existence oracle across projects.
    assert foreign.problem is not None
    assert foreign.problem.code == "task_not_found"
    # Another user's task in the same project is equally invisible.
    assert stranger.problem is not None
    assert stranger.problem.code == "task_not_found"
    assert sibling.problem is not None
    assert sibling.problem.code == "task_target_mismatch"


async def test_captured_submission_reads_the_task_execution_checkpoint(
    tmp_path, preview_queue, monkeypatch, db_factory
):
    project_dir = _build_project(tmp_path, generation_mode="reference_video", script=_reference_script())
    _use_projection(monkeypatch)
    ctx = _harness(tmp_path, preview_queue)
    await _insert_task(db_factory, checkpoint=_checkpoint_json(project_dir))

    outcome = await run_declared_tool(
        GET_PROMPT_PREVIEW, ctx, {"script": "episode_1.json", "item_id": "E1U1", "task_id": "t1"}
    )

    assert outcome.problem is None, outcome.problem
    captured = outcome.value.captured_submission
    assert captured["task_id"] == "t1"
    assert captured["prompt"] == "captured prompt"
    assert [media["logical_name"] for media in captured["media"]] == ["Tavern"]
    assert "staged_locator" not in captured["media"][0]
    assert outcome.value.preview_basis == "current_configuration"


def _checkpoint_json(project_dir: Path) -> str:
    """A real reference-video checkpoint built by the native writer over task-local staged media."""
    from lib.artifacts.artifact_manifest import ArtifactBasis, compose_video_artifact_basis
    from lib.artifacts.video_artifact_facts import VideoArtifactCurrencyFacts
    from lib.script.reference_video.execution_checkpoint import (
        ProviderMediaInput,
        ReferenceSubmissionCheckpoint,
        stage_provider_media,
    )

    staged = stage_provider_media(
        project_dir,
        "t1",
        (
            ProviderMediaInput(
                path=project_dir / "scenes" / "Tavern.png",
                role="reference_image",
                logical_type="scene",
                logical_name="Tavern",
                kind="sheet",
            ),
        ),
    )
    visual = ArtifactBasis.build(
        "artifact-visual/video-reference",
        kind_version=1,
        inputs={
            "unit_id": "E1U1",
            "visual_lines": ["Pushes the door"],
            "style": "Ink wash",
            "canvas": {"aspect_ratio": "9:16"},
            "request_references": [],
        },
    )
    speech = ArtifactBasis.build("artifact-speech/video", kind_version=1, inputs={"mode": "silent"})
    duration = ArtifactBasis.build(
        "artifact-speech/video-duration", kind_version=1, inputs={"request_duration_seconds": 3}
    )
    return ReferenceSubmissionCheckpoint.create(
        task_id="t1",
        project_name="demo",
        script_file="scripts/episode_1.json",
        unit_id="E1U1",
        generation_type="r2v",
        provider_id="fake",
        provider_model_id="fake-model",
        backend_model_id="fake-model",
        endpoint_guard=None,
        prompt="captured prompt",
        duration_seconds=3,
        aspect_ratio="9:16",
        resolution="1080p",
        generate_audio=True,
        service_tier="default",
        seed=None,
        visual_basis_digest="a" * 64,
        artifact_currency=VideoArtifactCurrencyFacts(
            episode=1,
            request_duration_seconds=3,
            visual_basis=visual,
            speech_basis=speech,
            duration_basis=duration,
            video_basis=compose_video_artifact_basis(visual=visual, speech=speech, duration=duration),
            voice_style_speakers=(),
            duration_tiers=(3,),
            reference_image_limit=9,
            parent_version=0,
        ),
        media=staged,
        reference_audio_targets=None,
    ).to_json()


# ---------------------------------------------------------------------------
# Storyboard regression through the routed entry
# ---------------------------------------------------------------------------


async def test_storyboard_entry_keeps_the_storyboard_route(tmp_path, preview_queue):
    script = {
        "episode": 1,
        "title": "E1",
        "content_mode": "drama",
        "summary": "x",
        "novel": {"title": "t", "chapter": "c"},
        "duration_seconds": 8,
        "scenes": [
            {
                "scene_id": "E1S01",
                "duration_seconds": 8,
                "segment_break": False,
                "characters_in_scene": [],
                "scenes": [],
                "props": [],
                "image_prompt": None,
                "video_prompt": None,
            }
        ],
    }
    _build_project(tmp_path, generation_mode="storyboard", script=script)

    outcome = await run_declared_tool(
        GET_PROMPT_PREVIEW, _harness(tmp_path, preview_queue), {"script": "episode_1.json", "item_id": "E1S01"}
    )

    assert outcome.problem is None, outcome.problem
    assert outcome.value.generation_mode == "storyboard"
    assert outcome.value.reference_video is None
    assert outcome.value.video.unavailable == "prompt_preview_pending"
    await _no_tasks(preview_queue)


# ---------------------------------------------------------------------------
# MCP-001: start_blank_script
# ---------------------------------------------------------------------------


async def test_start_blank_script_creates_once_and_discards_unconfirmed_planning(tmp_path, preview_queue):
    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)
    write_quarantine(project_dir, 1, QUARANTINE_KIND_DRAMA_SCRIPT_PLAN, content={"scenes": []}, violations=[])
    ctx = _harness(tmp_path, preview_queue)

    first = await run_declared_tool(START_BLANK_SCRIPT, ctx, {"episode_id": 1})
    created = (project_dir / "scripts" / "episode_1.json").read_bytes()
    again = await run_declared_tool(START_BLANK_SCRIPT, ctx, {"episode_id": 1})

    assert first.problem is None, first.problem
    assert first.value["episode_id"] == 1
    assert first.value["script_file"] == "episode_1.json"
    assert first.value["discarded_drafts"] == [QUARANTINE_KIND_DRAMA_SCRIPT_PLAN]
    assert json.loads(created)["scenes"] == []
    assert again.problem is not None
    assert again.problem.code == "formal_script_exists"
    assert (project_dir / "scripts" / "episode_1.json").read_bytes() == created
    await _no_tasks(preview_queue)


async def test_start_blank_script_refuses_an_unknown_episode(tmp_path, preview_queue):
    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)

    outcome = await run_declared_tool(START_BLANK_SCRIPT, _harness(tmp_path, preview_queue), {"episode_id": 9})

    assert outcome.problem is not None
    assert outcome.problem.code == "episode_not_found"
    assert not (project_dir / "scripts" / "episode_9.json").exists()


async def test_start_blank_script_is_blocked_after_failed_migration(tmp_path, preview_queue):
    from lib.project.project_migration_failure import record_migration_failure

    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)
    record_migration_failure(project_dir, RuntimeError("injected"), schema_version=7)

    outcome = await run_declared_tool(START_BLANK_SCRIPT, _harness(tmp_path, preview_queue), {"episode_id": 1})

    assert outcome.problem is not None
    assert outcome.problem.code == "project_migration_failed"
    assert not (project_dir / "scripts" / "episode_1.json").exists()


# ---------------------------------------------------------------------------
# MCP-019: get_asset_prompt_preview
# ---------------------------------------------------------------------------


async def test_asset_prompt_preview_renders_base_sheet_with_style(tmp_path, preview_queue):
    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)
    before = {path: path.read_bytes() for path in project_dir.rglob("*") if path.is_file()}

    outcome = await run_declared_tool(
        GET_ASSET_PROMPT_PREVIEW, _harness(tmp_path, preview_queue), {"asset_type": "character", "name": "Zed"}
    )

    assert outcome.problem is None, outcome.problem
    value = outcome.value
    assert value["target_kind"] == "asset_sheet"
    assert value["preview_basis"] == "current_configuration"
    assert value["text"]
    assert "Young swordsman" in value["text"]
    assert value["style"] == "Ink wash"
    assert value["description"] == "Young swordsman"
    assert value["occupancy"] is None
    assert _files_unchanged(project_dir, before)
    await _no_tasks(preview_queue)


async def test_asset_prompt_preview_reports_and_renders_scene_occupancy(tmp_path, preview_queue):
    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)
    harness = _harness(tmp_path, preview_queue)
    empty = await run_declared_tool(GET_ASSET_PROMPT_PREVIEW, harness, {"asset_type": "scene", "name": "Tavern"})
    project_file = project_dir / "project.json"
    project = json.loads(project_file.read_text(encoding="utf-8"))
    project["scenes"]["Tavern"]["occupancy"] = "occupied"
    project_file.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")

    occupied = await run_declared_tool(GET_ASSET_PROMPT_PREVIEW, harness, {"asset_type": "scene", "name": "Tavern"})

    assert empty.value["occupancy"] == "empty"
    assert "empty environment reference" in empty.value["text"]
    assert occupied.value["occupancy"] == "occupied"
    assert "occupied environment reference" in occupied.value["text"]
    await _no_tasks(preview_queue)


async def test_asset_prompt_preview_derivative_uses_the_base_sheet_reference(tmp_path, preview_queue):
    _build_project(tmp_path, generation_mode="storyboard", script=None)

    outcome = await run_declared_tool(
        GET_ASSET_PROMPT_PREVIEW,
        _harness(tmp_path, preview_queue),
        {"asset_type": "character", "name": "Zed", "derivative": "Armor", "description": "White fighting outfit"},
    )

    assert outcome.problem is None, outcome.problem
    value = outcome.value
    assert value["target_kind"] == "derivative_sheet"
    assert value["draft_description"] is True
    assert "White fighting outfit" in value["text"]
    assert value["style"] is None
    sent = [reference for reference in value["references"] if reference["sent"]]
    assert [reference["artifact_path"] for reference in sent] == ["characters/Zed.png"]
    # Digests are exposed only as the shared generation input observes them; never computed from prompt text.
    assert "content_digest" in sent[0]
    assert value["limits"]["sent_reference_count"] == 1
    await _no_tasks(preview_queue)


async def test_asset_prompt_preview_unknown_asset_is_a_problem(tmp_path, preview_queue):
    _build_project(tmp_path, generation_mode="storyboard", script=None)
    ctx = _harness(tmp_path, preview_queue)

    unknown = await run_declared_tool(GET_ASSET_PROMPT_PREVIEW, ctx, {"asset_type": "prop", "name": "Sword"})
    no_derivatives = await run_declared_tool(
        GET_ASSET_PROMPT_PREVIEW, ctx, {"asset_type": "scene", "name": "Tavern", "derivative": "Night"}
    )

    assert unknown.problem is not None
    assert unknown.problem.code == "asset_not_found"
    assert no_derivatives.problem is not None
    assert no_derivatives.problem.code == "derivatives_not_supported"


# ---------------------------------------------------------------------------
# MCP-020: generate_project_overview
# ---------------------------------------------------------------------------


def _fake_overview_generator(calls: list[str]):
    class _Generator:
        async def generate(self, _request, project_name=None):
            calls.append("generate")

            class _Result:
                text = json.dumps(
                    {
                        "synopsis": "A swordsman returns to the tavern",
                        "genre": "Wuxia",
                        "theme": "Return",
                        "world_setting": "The martial world",
                        "language": "en",
                    },
                    ensure_ascii=False,
                )

            return _Result()

    async def create(task_type, project_name=None, **_kwargs):
        calls.append(f"create:{task_type}")
        return _Generator()

    return create


async def test_overview_authorization_must_be_a_real_boolean(tmp_path, preview_queue, monkeypatch):
    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)
    (project_dir / "source").mkdir()
    (project_dir / "source" / "novel.txt").write_text("Zed enters the tavern.", encoding="utf-8")
    calls: list[str] = []
    use_text_generator(monkeypatch, _fake_overview_generator(calls))

    outcome = await run_declared_tool(
        GENERATE_PROJECT_OVERVIEW, _harness(tmp_path, preview_queue), {"confirm_text_model_call": "true"}
    )

    assert outcome.problem is not None
    assert outcome.problem.code == "invalid_request"
    assert calls == []


async def test_overview_requires_explicit_authorization_and_calls_nothing(tmp_path, preview_queue, monkeypatch):
    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)
    (project_dir / "source").mkdir()
    (project_dir / "source" / "novel.txt").write_text("Zed enters the tavern.", encoding="utf-8")
    calls: list[str] = []
    use_text_generator(monkeypatch, _fake_overview_generator(calls))

    outcome = await run_declared_tool(GENERATE_PROJECT_OVERVIEW, _harness(tmp_path, preview_queue), {})

    assert outcome.problem is not None
    assert outcome.problem.code == "confirmation_required"
    assert outcome.problem.params["sources"] == [
        {"filename": "novel.txt", "chars_used": 22, "total_chars": 22, "truncated": False}
    ]
    assert calls == []
    assert "overview" not in json.loads((project_dir / "project.json").read_text(encoding="utf-8"))


async def test_overview_generates_with_the_fake_text_model_and_reports_impacts(tmp_path, preview_queue, monkeypatch):
    project_dir = _build_project(tmp_path, generation_mode="storyboard", script=None)
    (project_dir / "source").mkdir()
    (project_dir / "source" / "novel.txt").write_text("Zed enters the tavern.", encoding="utf-8")
    calls: list[str] = []
    use_text_generator(monkeypatch, _fake_overview_generator(calls))

    outcome = await run_declared_tool(
        GENERATE_PROJECT_OVERVIEW, _harness(tmp_path, preview_queue), {"confirm_text_model_call": True}
    )

    assert outcome.problem is None, outcome.problem
    value = outcome.value
    assert calls == ["create:overview", "generate"]
    assert value["overview"]["synopsis"] == "A swordsman returns to the tavern"
    assert value["previous_overview"] is None
    assert value["stale_impacts"]["changed_fields"] == ["synopsis", "genre", "theme", "world_setting"]
    assert value["stale_impacts"]["basis_changed"] is True
    saved = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    assert saved["overview"]["synopsis"] == "A swordsman returns to the tavern"
    await _no_tasks(preview_queue)


async def test_overview_without_sources_is_refused_before_any_model_call(tmp_path, preview_queue, monkeypatch):
    _build_project(tmp_path, generation_mode="storyboard", script=None)
    calls: list[str] = []
    use_text_generator(monkeypatch, _fake_overview_generator(calls))

    outcome = await run_declared_tool(
        GENERATE_PROJECT_OVERVIEW, _harness(tmp_path, preview_queue), {"confirm_text_model_call": True}
    )

    assert outcome.problem is not None
    assert outcome.problem.code == "source_empty"
    assert calls == []
