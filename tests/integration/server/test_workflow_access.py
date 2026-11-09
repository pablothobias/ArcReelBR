"""Native settings, references and financial readers through the shared MCP declarations."""

from __future__ import annotations

import base64
from io import BytesIO

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
