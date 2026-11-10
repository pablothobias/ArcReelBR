"""configure_project rejects model_settings resolutions the endpoint renderer cannot accept (MCP-005)."""

from __future__ import annotations

import pytest

from lib.config.resolver import ConfigResolver
from lib.generation.generation_queue import GenerationQueue
from lib.project.project_manager import get_project_manager
from server.agent_toolset.declaration import invoke_declaration
from server.agent_toolset.workflow_access import WORKFLOW_ACCESS_TOOLS
from server.tool_runtime import CallerContext, ProjectScope, Services


@pytest.fixture
async def access(isolated_data_root, file_db_factory):
    pm = get_project_manager()
    pm.create_project("demo", content_mode="drama")
    pm.create_project_metadata("demo", "Demo")
    services = Services(
        projects=pm,
        workflow_planner=None,
        capabilities=ConfigResolver(file_db_factory),
        sessions=file_db_factory,
        queue=GenerationQueue(session_factory=file_db_factory, project_manager=pm),
    )

    async def call(**arguments):
        declaration = next(t for t in WORKFLOW_ACCESS_TOOLS if t.name == "configure_project")
        return await invoke_declaration(
            declaration,
            arguments,
            ProjectScope(project_name="demo", data_root=pm.data_root),
            CallerContext(user_id="test", source="mcp"),
            services,
        )

    return pm, call


async def test_unrenderable_resolution_is_refused_with_valid_values_and_zero_writes(access):
    pm, call = access
    project_file = pm.get_project_path("demo") / "project.json"
    before = project_file.read_bytes()
    result = await call(title="Changed", model_settings={"minimax/MiniMax-H3": {"resolution": "2K"}})
    assert result.problem is not None
    assert result.problem.code == "model_setting_value_unsupported"
    assert result.problem.params == {
        "model_key": "minimax/MiniMax-H3",
        "field": "resolution",
        "value": "2K",
        "allowed_values": ["768p", "2k"],
        "suggestion": "2k",
    }
    assert project_file.read_bytes() == before


async def test_renderable_resolution_saves_and_replaces_the_whole_map(access):
    pm, call = access
    pm.update_project("demo", lambda p: p.update({"model_settings": {"other/model": {"resolution": "1080p"}}}))
    result = await call(model_settings={"minimax/MiniMax-H3": {"resolution": "2k"}})
    assert result.problem is None
    assert pm.load_project("demo")["model_settings"] == {"minimax/MiniMax-H3": {"resolution": "2k"}}


async def test_unconstrained_models_and_cleared_values_are_untouched(access):
    pm, call = access
    result = await call(
        model_settings={
            "gemini-aistudio/veo-3.1-generate-preview": {"resolution": "1080p"},
            "minimax/MiniMax-H3": {"resolution": None},
        }
    )
    assert result.problem is None
    assert pm.load_project("demo")["model_settings"]["gemini-aistudio/veo-3.1-generate-preview"] == {
        "resolution": "1080p"
    }
