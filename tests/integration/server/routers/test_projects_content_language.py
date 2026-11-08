"""Project content language persists independently of presentation language."""

from lib.project.project_manager import ProjectManager
from tests.integration.server.routers.projects_router_support import build_projects_client


def test_brazilian_language_create_edit_read_and_clear(tmp_path, monkeypatch):
    manager = ProjectManager(tmp_path / "projects")
    with build_projects_client(monkeypatch, manager) as client:
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "cafe",
                "title": "O café",
                "content_mode": "drama",
                "generation_mode": "storyboard",
                "source_language": "PT_br",
                "speech_rate_units_per_second": 3,
            },
        )
        assert response.status_code == 200, response.text
        assert manager.load_project("cafe")["source_language"] == "pt-BR"
        read = client.get("/api/v1/projects/cafe", headers={"Accept-Language": "en"})
        assert read.status_code == 200, read.text
        assert read.json()["project"]["source_language"] == "pt-BR"
        edited = client.patch("/api/v1/projects/cafe", json={"source_language": "pt-br", "title": "Novo título"})
        assert edited.status_code == 200, edited.text
        persisted = manager.load_project("cafe")
        assert persisted["source_language"] == "pt-BR"
        assert persisted["speech_rate_units_per_second"] == 3
        assert persisted["title"] == "Novo título"
        rejected = client.patch("/api/v1/projects/cafe", json={"source_language": "pt-PT"})
        assert rejected.status_code == 422
        assert manager.load_project("cafe")["source_language"] == "pt-BR"
        cleared = client.patch("/api/v1/projects/cafe", json={"source_language": None})
        assert cleared.status_code == 200, cleared.text
        assert "source_language" not in manager.load_project("cafe")


async def test_tool_create_edit_and_read_preserve_canonical_content_language(tmp_path):
    import asyncio

    from server.tool_runtime import (
        CallerContext,
        CreateProjectToolRequest,
        NoArguments,
        PatchProjectRequest,
        ProjectScope,
        Services,
        ToolRequest,
        create_project,
        get_project_content,
        patch_project,
    )

    manager = ProjectManager(tmp_path / "projects")
    services = Services.defaults(manager)
    caller = CallerContext(user_id="default", source="mcp")
    created = await create_project(
        ToolRequest(CreateProjectToolRequest(name="cafe", title="O café", source_language="pt_br")),
        caller,
        services,
    )
    assert created.problem is None, created.problem
    assert created.value["project"]["source_language"] == "pt-BR"
    scope = ProjectScope(project_name="cafe", data_root=manager.data_root)
    edited = await patch_project(
        ToolRequest(PatchProjectRequest(settings={"source_language": "PT-BR"})),
        scope,
        caller,
        services,
    )
    assert edited.problem is None, edited.problem
    read = await get_project_content(ToolRequest(NoArguments()), scope, caller, services)
    assert read.problem is None, read.problem
    persisted = await asyncio.to_thread(manager.load_project, "cafe")
    assert persisted["source_language"] == "pt-BR"
