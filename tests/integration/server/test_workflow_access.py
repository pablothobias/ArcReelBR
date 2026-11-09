"""Native settings, references and financial readers through the shared MCP declarations."""

from __future__ import annotations

import asyncio
import base64
import json
import threading
from io import BytesIO
from typing import cast

import pytest
from PIL import Image

from lib.config.resolver import ConfigResolver
from lib.db.repositories.usage_repo import SettlementInput, UsageRepository
from lib.generation.generation_queue import GenerationQueue
from lib.project.project_manager import get_project_manager
from server.agent_toolset.declaration import invoke_declaration
from server.agent_toolset.workflow_access import WORKFLOW_ACCESS_TOOLS
from server.tool_runtime import CallerContext, ProjectScope, Services


@pytest.fixture
async def access(isolated_data_root, file_db_factory):
    pm = get_project_manager()
    tmp_path = pm.data_root
    pm.create_project("demo", content_mode="drama")
    pm.create_project_metadata("demo", "Demo")
    pm.update_project("demo", lambda p: p.update({"characters": {"Ana": {"description": "A fictional person"}}}))
    services = Services(
        projects=pm,
        workflow_planner=None,
        capabilities=ConfigResolver(file_db_factory),
        sessions=file_db_factory,
        queue=GenerationQueue(session_factory=file_db_factory, project_manager=pm),
    )
    scope = ProjectScope(project_name="demo", data_root=tmp_path)

    async def call(tool_name, **arguments):
        declaration = next(t for t in WORKFLOW_ACCESS_TOOLS if t.name == tool_name)
        return await invoke_declaration(
            declaration, arguments, scope, CallerContext(user_id="test", source="mcp"), services
        )

    return pm, call


async def test_settings_persist_and_invalid_settings_leave_project_unchanged(access):
    pm, call = access
    result = await call("configure_project", style="Photorealistic", source_language="pt-BR", aspect_ratio="9:16")
    assert result.problem is None
    before = pm.load_project("demo")
    assert before["style"] == "Photorealistic"
    assert before["source_language"] == "pt-BR"
    for invalid in ({"generation_mode": "reference_video"}, {"character_voice_binding": "unsupported"}):
        rejected = await call("configure_project", **invalid)
        assert rejected.problem is not None
        assert pm.load_project("demo") == before


@pytest.mark.parametrize("grid", [True, False, None])
async def test_settings_handler_revalidates_web_requests_before_writing(access, grid):
    from server.media_tools.workflow_access import ConfigureProjectRequest, configure_project
    from server.routers.projects import UpdateProjectRequest
    from server.tool_runtime import ToolRequest

    pm, _ = access
    project_file = pm.get_project_path("demo") / "project.json"
    before = project_file.read_bytes()
    web_request = UpdateProjectRequest(grid_storyboard=grid, title="Must not be applied")
    result = await configure_project(
        ToolRequest(cast(ConfigureProjectRequest, web_request)),
        ProjectScope("demo", pm.data_root),
        CallerContext("test", "mcp"),
        Services.defaults(pm),
    )
    assert result.problem is not None
    assert result.problem.code == "invalid_request"
    assert project_file.read_bytes() == before


async def test_automated_settings_keep_omitted_and_clear_semantics(access):
    pm, call = access
    pm.update_project(
        "demo",
        lambda p: p.update(
            {
                "grid_storyboard": True,
                "source_language": "pt-BR",
                "speech_rate_units_per_second": 3,
                "default_image_backend": "agnes/agnes-image-2.5-flash",
            }
        ),
    )
    result = await call("configure_project", title="O café", character_voice_binding="prompt")
    assert result.problem is None
    project = pm.load_project("demo")
    assert project["source_language"] == "pt-BR"
    assert project["grid_storyboard"] is True
    assert project["speech_rate_units_per_second"] == 3
    assert project["default_image_backend"] == "agnes/agnes-image-2.5-flash"
    cleared = await call("configure_project", speech_rate_units_per_second=None, default_image_backend="")
    assert cleared.problem is None
    project = pm.load_project("demo")
    assert "speech_rate_units_per_second" not in project
    assert "default_image_backend" not in project
    assert project["source_language"] == "pt-BR"
    assert project["grid_storyboard"] is True


def png():
    data = BytesIO()
    Image.new("RGB", (16, 16), "blue").save(data, format="PNG")
    return base64.b64encode(data.getvalue()).decode()


async def test_reference_upload_uses_native_metadata_without_generating_a_sheet(access):
    pm, call = access
    result = await call(
        "upload_reference", kind="character_image", name="Ana", filename="reference.png", content_base64=png()
    )
    assert result.problem is None, result
    character = pm.load_project("demo")["characters"]["Ana"]
    assert character["reference_image"]
    assert (pm.get_project_path("demo") / character["reference_image"]).is_file()
    assert not character.get("character_sheet")
    missing = await call(
        "upload_reference", kind="character_image", name="Nobody", filename="reference.png", content_base64=png()
    )
    assert missing.problem is not None
    assert not (pm.get_project_path("demo") / "characters/refs/Nobody.png").exists()


@pytest.mark.parametrize(
    "overrides",
    [
        {"filename": "../bad.png"},
        {"content_base64": "invalid!"},
        {"content_base64": base64.b64encode(b"not an image").decode()},
        {"kind": "style_image"},
        {"name": "../bad"},
    ],
)
async def test_reference_rejects_unsafe_or_unconfirmed_input_without_writes(access, overrides):
    pm, call = access
    before = pm.load_project("demo")
    args = {"kind": "character_image", "name": "Ana", "filename": "reference.png", "content_base64": png()}
    args.update(overrides)
    result = await call("upload_reference", **args)
    assert result.problem is not None
    assert pm.load_project("demo") == before


async def test_usage_is_scoped_paginated_and_does_not_expose_diagnostics(access, file_db_factory):
    _, call = access
    async with file_db_factory() as session:
        repo = UsageRepository(session)
        for project in ("demo", "other", "demo"):
            cid = await repo.start_call(project_name=project, call_type="image", model="test", provider="test")
            await repo.finish_call(
                cid,
                status="success",
                settlement=SettlementInput(cost_amount=0.25, currency="USD"),
                output_path="/private/secret.png",
            )
    result = await call("get_project_usage", limit=1)
    assert result.problem is None
    assert len(result.value["items"]) == 1
    assert result.value["total"] == 2
    assert result.value["items"][0]["cost_amount"] == 0.25
    assert "secret" not in str(result.value)
    page2 = await call("get_project_usage", limit=1, cursor=result.value["next_cursor"])
    assert page2.value["items"][0]["id"] != result.value["items"][0]["id"]
    assert page2.value["next_cursor"] is None
    invalid = await call("get_project_usage", cursor="bad")
    assert invalid.problem.code == "invalid_request"


async def test_asset_quote_selects_native_targets_without_submitting(access):
    pm, call = access
    pm.update_project("demo", lambda p: p.update({"default_image_backend": "agnes/agnes-image-2.5-flash"}))
    result = await call("quote_assets", type="character", names=["Ana"])
    assert result.problem is None, result
    assert result.value["targets"] == [{"unit_id": "character/Ana", "depends_on": None}]
    assert result.value["unpriced_count"] == 0
    assert result.value["estimated_cost"]["USD"] > 0
    usage = await call("get_project_usage")
    assert usage.value["total"] == 0
    costs = await call("get_project_costs")
    assert costs.problem is None, costs


async def test_effective_configuration_and_unpriced_quote_are_read_only(access):
    pm, call = access
    pm.update_project(
        "demo",
        lambda p: p.update(
            {"default_image_backend": "agnes/agnes-image-2.5-flash", "default_text_backend": "google/gemini-3.8-flash"}
        ),
    )
    result = await call("get_effective_configuration")
    assert result.problem is None, result
    assert result.value["models"]["t2i"] == "agnes/agnes-image-2.5-flash"
    assert result.value["models"]["script"] == "google/gemini-3.8-flash"
    assert result.value["subscription_login"] == "not_selected"
    await call("upload_reference", kind="character_image", name="Ana", filename="ref.png", content_base64=png())
    quote = await call("quote_assets", type="character", names=["Ana"])
    assert quote.value["unpriced_count"] == 1
    assert quote.value["estimated_cost"] is None


async def test_quotes_report_missing_episode_without_submitting(access):
    _, call = access
    for tool in ("quote_assets", "quote_storyboards"):
        result = await call(tool, episode_id=999)
        assert result.problem is not None
        assert result.problem.code == "quote_unavailable"
    usage = await call("get_project_usage")
    assert usage.value["total"] == 0


def _write_legacy_reference_episode(pm, *, generation_mode="reference_video"):
    path = pm.get_project_path("demo") / "scripts/episode_1.json"
    script = {
        "episode": 1,
        "content_mode": "drama",
        "video_units": [
            {
                "unit_id": "E1U01",
                "text": 'Ana diz: "Olá, Ana!"',
                "duration_seconds": 8,
                "duration_override": False,
                "shots": [{"text": "Olá, Ana!", "duration": 8}],
            }
        ],
    }
    path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    pm.update_project(
        "demo",
        lambda p: p.update(
            {
                "source_language": "pt-BR",
                "generation_mode": generation_mode,
                "episodes": [{"episode": 1, "title": "O café", "script_file": "scripts/episode_1.json"}],
            }
        ),
    )
    return path


async def test_cost_consultation_adopts_legacy_in_memory_without_writes(access):
    pm, call = access
    script = _write_legacy_reference_episode(pm)
    project = pm.get_project_path("demo") / "project.json"
    before = script.read_bytes(), project.read_bytes()
    legacy = await call("get_project_costs")
    assert legacy.problem is None
    assert (script.read_bytes(), project.read_bytes()) == before
    adopted = await asyncio.to_thread(pm.load_script, "demo", "episode_1.json")
    assert "duration_override" not in adopted["video_units"][0]
    assert adopted["video_units"][0]["duration_seconds"] == 8
    assert adopted["video_units"][0]["text"] == 'Ana diz: "Olá, Ana!"'
    assert script.read_bytes() != before[0]
    current_before = script.read_bytes(), project.read_bytes()
    current = await call("get_project_costs")
    assert current.problem is None
    assert current.value == legacy.value
    assert (script.read_bytes(), project.read_bytes()) == current_before


async def test_cancelled_cost_reader_cannot_persist_a_late_migration(access, file_db_factory):
    from lib.project.project_manager import ProjectManager
    from server.media_tools.workflow_access import get_project_costs
    from server.tool_runtime import NoArguments, ToolRequest

    pm, _ = access
    script = _write_legacy_reference_episode(pm)
    before = script.read_bytes()
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()

    class PausedProjectManager(ProjectManager):
        def observe(self, reader, *args):
            entered.set()
            assert release.wait(5), "Reader was not released"
            try:
                return reader(*args)
            finally:
                completed.set()

        def load_script(self, project_name: str, filename: str) -> dict:
            return self.observe(super().load_script, project_name, filename)

        def load_script_readonly(self, project_name: str, filename: str) -> dict:
            return self.observe(super().load_script_readonly, project_name, filename)

    observed = PausedProjectManager(pm.data_root)
    services = Services(
        projects=observed,
        workflow_planner=None,
        capabilities=ConfigResolver(file_db_factory),
        sessions=file_db_factory,
        queue=GenerationQueue(session_factory=file_db_factory, project_manager=observed),
    )
    task = asyncio.create_task(
        get_project_costs(
            ToolRequest(NoArguments()), ProjectScope("demo", pm.data_root), CallerContext("test", "mcp"), services
        )
    )
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        assert await asyncio.to_thread(completed.wait, 5)
        assert script.read_bytes() == before
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("preview", [True, False])
async def test_storyboard_edit_preview_preserves_legacy_but_real_edit_still_adopts(access, file_db_factory, preview):
    from server.media_tools.image_edits import EditImagesRequest, edit_images
    from server.tool_runtime import ToolRequest

    pm, _ = access
    script = _write_legacy_reference_episode(pm)
    before = script.read_bytes()
    queue = GenerationQueue(session_factory=file_db_factory, project_manager=pm)
    services = Services(
        projects=pm,
        workflow_planner=None,
        capabilities=ConfigResolver(file_db_factory),
        sessions=file_db_factory,
        queue=queue,
    )
    result = await edit_images(
        ToolRequest(
            EditImagesRequest(
                resource_type="storyboard",
                script_file="episode_1.json",
                edits=[{"id": "E1U01", "instruction": "Preserve Portuguese speech"}],
                preview=preview,
            )
        ),
        ProjectScope("demo", pm.data_root),
        CallerContext("test", "mcp"),
        services,
    )
    assert result.problem is None
    if preview:
        assert script.read_bytes() == before
        assert "image_edit_quote" in result.value
    else:
        assert script.read_bytes() != before
    assert (await queue.list_tasks(project_name="demo", task_type="image_edit"))["items"] == []


@pytest.mark.parametrize("generation_mode", ["reference_video", "storyboard"])
async def test_storyboard_quote_refusal_never_adopts_a_legacy_script(access, generation_mode):
    pm, call = access
    script = _write_legacy_reference_episode(pm, generation_mode=generation_mode)
    before = script.read_bytes()
    result = await call("quote_storyboards", episode_id=1)
    assert result.problem is not None
    assert result.problem.code == "quote_unavailable"
    assert script.read_bytes() == before


async def test_storyboard_quote_preserves_targets_prices_and_current_script(access):
    pm, call = access
    path = pm.get_project_path("demo") / "scripts/episode_1.json"
    script = {
        "episode": 1,
        "content_mode": "drama",
        "scenes": [
            {"scene_id": "E1S01", "image_prompt": "A Brazilian café", "duration_seconds": 8},
            {"scene_id": "E1S02", "image_prompt": "Ana smiles", "duration_seconds": 8, "segment_break": True},
        ],
    }
    path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    pm.update_project(
        "demo",
        lambda p: p.update(
            {
                "source_language": "pt-BR",
                "default_image_backend": "agnes/agnes-image-2.5-flash",
                "episodes": [{"episode": 1, "title": "O café", "script_file": "scripts/episode_1.json"}],
            }
        ),
    )
    before = path.read_bytes(), (pm.get_project_path("demo") / "project.json").read_bytes()
    first = await call("quote_storyboards", episode_id=1)
    second = await call("quote_storyboards", episode_id=1)
    assert first.problem is None
    assert second.problem is None
    assert first.value == second.value
    assert first.value["targets"] == [{"unit_id": "E1S01"}, {"unit_id": "E1S02"}]
    assert first.value["unpriced_count"] == 0
    assert first.value["estimated_cost"]["USD"] > 0
    assert (path.read_bytes(), (pm.get_project_path("demo") / "project.json").read_bytes()) == before
    assert (await call("get_project_usage")).value["total"] == 0
