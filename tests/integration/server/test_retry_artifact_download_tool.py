"""retry_artifact_download through the shared MCP declaration, against a disposable database and a fake worker."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import pytest
from sqlalchemy import func, select

from lib.config.resolver import ConfigResolver
from lib.db.models.api_call import ApiCall
from lib.db.models.task import Task
from lib.db.repositories.task_repo import TaskRepository
from lib.db.repositories.usage_repo import SettlementInput, UsageRepository
from lib.generation.generation_queue import GenerationQueue
from lib.generation.task_failure import encode_failure
from lib.project.project_manager import get_project_manager
from server.agent_toolset.artifact_download import RETRY_ARTIFACT_DOWNLOAD
from server.agent_toolset.declaration import invoke_declaration
from server.services.tasks.artifact_download_retry import ArtifactDownloadRetryUnavailable, retry_artifact_download
from server.tool_runtime import CallerContext, ProjectScope, Services


@dataclass
class _FakeWorker:
    resumed: list[dict[str, Any]] = field(default_factory=list)
    timeout_error: Exception | None = None

    async def read_video_poll_timeout_seconds(self) -> int:
        if self.timeout_error is not None:
            raise self.timeout_error
        return 900

    async def retry_artifact_download(self, task: dict[str, Any], *, poll_timeout_seconds: int) -> None:
        self.resumed.append({"task_id": task["task_id"], "poll_timeout_seconds": poll_timeout_seconds})


@pytest.fixture
async def retry(isolated_data_root, file_db_factory):
    pm = get_project_manager()
    for name in ("demo", "other"):
        pm.create_project(name, content_mode="drama")
        pm.create_project_metadata(name, name.title())
    worker = _FakeWorker()
    services = Services(
        projects=pm,
        workflow_planner=None,
        capabilities=ConfigResolver(file_db_factory),
        sessions=file_db_factory,
        queue=GenerationQueue(session_factory=file_db_factory, project_manager=pm),
        artifact_download_worker=worker,
    )

    async def call(project: str = "demo", *, user_id: str = "test", services: Services = services, **arguments):
        return await invoke_declaration(
            RETRY_ARTIFACT_DOWNLOAD,
            arguments,
            ProjectScope(project_name=project, data_root=pm.data_root),
            CallerContext(user_id=user_id, source="mcp"),
            services,
        )

    return call, file_db_factory, worker, services


async def _download_failed(factory, project: str = "demo", *, failure: str = "artifact_download_failed") -> str:
    """The state the worker leaves when the provider produced output but retrieval failed (no provider involved)."""
    async with factory() as session:
        repo, usage = TaskRepository(session), UsageRepository(session)
        task = await repo.enqueue(
            project_name=project,
            task_type="video",
            media_type="video",
            resource_id="E1S01",
            payload={},
            user_id="test",
            provider_id="custom-1",
        )
        call_id = await usage.start_call(
            project_name=project, call_type="video", model="m", provider="custom-1", task_id=task["task_id"]
        )
        await usage.finish_call(
            call_id, status="failed", settlement=SettlementInput(cost_amount=0), error_message="download failed"
        )
        await repo.claim_next("video")
        await repo.persist_provider_job_id(task["task_id"], "job-1", endpoint="ce-1")
        await repo.mark_failed(task["task_id"], encode_failure(failure, detail="403"))
    return str(task["task_id"])


async def _counts(factory) -> tuple[int, int]:
    async with factory() as session:
        tasks = (await session.execute(select(func.count()).select_from(Task))).scalar_one()
        calls = (await session.execute(select(func.count()).select_from(ApiCall))).scalar_one()
    return int(tasks), int(calls)


async def test_resumes_retrieval_of_the_same_task_without_new_tasks_or_calls(retry):
    call, factory, worker, services = retry
    task_id = await _download_failed(factory)
    before = await _counts(factory)

    result = await call(task_id=task_id)

    assert result.problem is None
    assert result.value["task_id"] == task_id
    assert result.value["status"] == "running"
    assert result.value["new_task_created"] is False
    assert worker.resumed == [{"task_id": task_id, "poll_timeout_seconds": 900}]
    assert await _counts(factory) == before
    stored = await services.queue.get_task(task_id)
    assert stored["status"] == "running"
    assert stored["provider_job_id"] == "job-1"


async def test_foreign_project_foreign_caller_and_missing_tasks_read_as_not_found(retry):
    call, factory, worker, services = retry
    foreign = await _download_failed(factory, project="other")
    own = await _download_failed(factory)

    outcomes = [
        (await call(task_id=foreign), foreign),
        (await call(task_id="missing"), "missing"),
        (await call(task_id=own, user_id="someone-else"), own),
    ]

    for outcome, task_id in outcomes:
        assert outcome.problem is not None
        assert outcome.problem.code == "task_not_found"
        assert outcome.problem.detail == f"Task {task_id} does not exist in this project"
    assert worker.resumed == []
    assert (await services.queue.get_task(foreign))["status"] == "failed"
    assert (await services.queue.get_task(own))["status"] == "failed"


async def test_ineligible_task_is_refused_without_changes(retry):
    call, factory, worker, services = retry
    task_id = await _download_failed(factory, failure="provider_rejected")

    result = await call(task_id=task_id)

    assert result.problem is not None
    assert result.problem.code == "task_retry_download_ineligible"
    assert worker.resumed == []
    assert (await services.queue.get_task(task_id))["status"] == "failed"


async def test_missing_worker_is_a_stable_problem_and_changes_nothing(retry):
    call, factory, _worker, services = retry
    task_id = await _download_failed(factory)

    result = await call(task_id=task_id, services=replace(services, artifact_download_worker=None))

    assert result.problem is not None
    assert result.problem.code == "task_retry_download_unavailable"
    assert (await services.queue.get_task(task_id))["status"] == "failed"


async def test_unreadable_poll_timeout_leaves_task_retryable(retry):
    _call, factory, worker, services = retry
    task_id = await _download_failed(factory)
    worker.timeout_error = RuntimeError("config database unavailable")

    with pytest.raises(RuntimeError):
        await retry_artifact_download(task_id, queue=services.queue, worker=worker)

    assert (await services.queue.get_task(task_id))["status"] == "failed"


async def test_service_reports_missing_worker_distinctly(retry):
    _call, factory, _worker, services = retry
    task_id = await _download_failed(factory)

    with pytest.raises(ArtifactDownloadRetryUnavailable) as raised:
        await retry_artifact_download(task_id, queue=services.queue, worker=None)

    assert raised.value.worker_unavailable is True
