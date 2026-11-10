"""get_generation_diagnostics through the shared MCP declaration, against a disposable database (MCP-006)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select, update

from lib.config.resolver import ConfigResolver
from lib.custom_provider.declarative_backend import ProviderJobRejectedError
from lib.db.models.task import Task
from lib.db.repositories.task_repo import TaskRepository
from lib.db.repositories.usage_repo import UsageRepository
from lib.generation.generation_queue import GenerationQueue
from lib.generation.task_failure_encoding import encode_task_failure_message
from lib.project.project_manager import get_project_manager
from server.agent_toolset.declaration import invoke_declaration
from server.agent_toolset.generation_diagnostics import GENERATION_DIAGNOSTICS_TOOLS
from server.tool_runtime import CallerContext, ProjectScope, Services

SECRET = "sk-live-0123456789abcdef"
MPEG_MESSAGE = 'content[6].audio_url: invalid param: audio format ".mpeg" not allowed'


@pytest.fixture
async def diag(isolated_data_root, file_db_factory):
    pm = get_project_manager()
    for name in ("demo", "other"):
        pm.create_project(name, content_mode="drama")
        pm.create_project_metadata(name, name.title())
    services = Services(
        projects=pm,
        workflow_planner=None,
        capabilities=ConfigResolver(file_db_factory),
        sessions=file_db_factory,
        queue=GenerationQueue(session_factory=file_db_factory, project_manager=pm),
    )

    async def call(project: str = "demo", **arguments):
        [declaration] = GENERATION_DIAGNOSTICS_TOOLS
        return await invoke_declaration(
            declaration,
            arguments,
            ProjectScope(project_name=project, data_root=pm.data_root),
            CallerContext(user_id="test", source="mcp"),
            services,
        )

    return call, file_db_factory


async def _failed_task_with_call(factory, project: str = "demo") -> tuple[str, int]:
    error = ProviderJobRejectedError(
        provider_error_code="2013",
        provider_error_message=MPEG_MESSAGE,
        stage="poll",
        classification="fix_input",
        provider_status="failed",
    )
    async with factory() as session:
        task = await TaskRepository(session).enqueue(
            project_name=project,
            task_type="reference_video",
            media_type="video",
            resource_id="E1U1",
            payload={"prompt": "private prompt"},
            user_id="test",
            provider_id="custom-1",
        )
        await session.execute(
            update(Task)
            .where(Task.task_id == task["task_id"])
            .values(
                status="failed",
                provider_job_id="461931189367168",
                error_message=encode_task_failure_message(error),
            )
        )
        await session.commit()
        repo = UsageRepository(session)
        call_id = await repo.start_call(
            project_name=project,
            call_type="video",
            model="MiniMax-H3",
            provider="custom-1",
            task_id=task["task_id"],
            user_id="test",
        )
        await repo.update_last_provider_response(
            call_id,
            {
                "task": {"status": "failed", "error": {"code": 2013, "message": MPEG_MESSAGE}},
                "debug": {"Authorization": f"Bearer {SECRET}", "url": "https://cdn.test/a?X-Amz-Signature=sig"},
                "echo": "data:audio/mpeg;base64," + "Q" * 4000,
            },
        )
    return task["task_id"], call_id


async def _task_count(factory) -> int:
    async with factory() as session:
        return int((await session.execute(select(func.count()).select_from(Task))).scalar_one())


async def test_task_diagnostics_expose_provider_verdict_sanitized_without_side_effects(diag):
    call, factory = diag
    task_id, call_id = await _failed_task_with_call(factory)
    before = await _task_count(factory)

    result = await call(task_id=task_id, include_provider_response=True)

    assert result.problem is None
    value = result.value
    assert value["provider_error"]["code"] == "2013"
    assert value["provider_error"]["message"] == MPEG_MESSAGE
    assert value["provider_error"]["stage"] == "poll"
    assert value["recovery"]["action"] == "fix_input"
    assert value["task"]["provider_job_id"] == "461931189367168"
    assert value["usage_record"]["record_id"] == call_id
    assert value["usage_record"]["status"] == "pending"
    assert value["last_provider_response"]["body"]["task"]["error"]["code"] == 2013
    assert value["provider_calls"] == 0
    text = json.dumps(value)
    for leaked in (SECRET, "X-Amz-Signature=sig", "QQQQ", "private prompt"):
        assert leaked not in text
    # Reading enqueues nothing.
    assert await _task_count(factory) == before


async def test_record_lookup_reaches_the_same_task(diag):
    call, factory = diag
    task_id, call_id = await _failed_task_with_call(factory)
    result = await call(record_id=call_id)
    assert result.problem is None
    assert result.value["task"]["task_id"] == task_id
    assert "body" not in result.value["last_provider_response"]
    assert result.value["last_provider_response"]["recorded"] is True


async def test_foreign_project_ids_are_not_found(diag):
    call, factory = diag
    task_id, call_id = await _failed_task_with_call(factory, project="other")
    for arguments in ({"task_id": task_id}, {"record_id": call_id}, {"task_id": "missing"}):
        result = await call(**arguments)
        assert result.problem is not None
        assert result.problem.code == "generation_diagnostics_not_found"
        assert "2013" not in json.dumps(result.problem.model_dump())


@pytest.mark.parametrize("arguments", [{}, {"task_id": "a", "record_id": 1}])
async def test_exactly_one_identifier_is_required(diag, arguments):
    call, _ = diag
    result = await call(**arguments)
    assert result.problem is not None
