"""MCP read access to sanitized generation diagnostics by task ID or usage record ID.

Reads the task row and the latest usage record through the native repositories (the same data the Web usage detail
shows), sanitizes them through :mod:`lib.generation.generation_diagnostics`, and never polls a provider, enqueues a
task, or writes anything. IDs outside the caller's project, or owned by another user, are reported as not found.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.db.repositories.task_repo import TaskRepository
from lib.db.repositories.usage_repo import UsageRepository
from lib.generation.generation_diagnostics import build_generation_diagnostics
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolProblem, ToolRequest


class GenerationDiagnosticsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str | None = Field(
        default=None,
        min_length=1,
        description="Generation task ID (from a generation batch member or generation_result item); give exactly one of task_id or record_id",
    )
    record_id: int | None = Field(
        default=None,
        ge=1,
        description="Usage record ID (id from get_project_usage); give exactly one of task_id or record_id",
    )
    include_provider_response: bool = Field(
        default=False,
        description="Include the last recorded provider response body, sanitized (credentials, signed URL queries and media payloads removed) and bounded",
    )

    @model_validator(mode="after")
    def _exactly_one_id(self) -> Self:
        if (self.task_id is None) == (self.record_id is None):
            raise ValueError("give exactly one of task_id or record_id")
        return self


def _not_found(kind: str, value: object) -> ToolOutcome[dict[str, Any]]:
    return ToolOutcome(
        problem=ToolProblem(
            "generation_diagnostics_not_found",
            f"{kind} {value} does not exist in this project",
            params={kind: value},
        )
    )


async def get_generation_diagnostics(
    request: ToolRequest[GenerationDiagnosticsRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    args = request.value
    project_name = scope.project_name
    async with services.sessions() as session:
        task: dict[str, Any] | None = None
        record: dict[str, Any] | None = None
        if args.task_id is not None:
            task = await TaskRepository(session).get(args.task_id)
            if task is None or task.get("project_name") != project_name or task.get("user_id") != caller.user_id:
                return _not_found("task_id", args.task_id)
            usage = UsageRepository(session)
            record = await usage.get_latest_record_for_task(project_name, args.task_id)
            # A call settled under another user is omitted rather than exposed through this user's task.
            if record is not None and await usage.get_record_owner_id(int(record["id"])) != caller.user_id:
                record = None
        else:
            usage = UsageRepository(session)
            record_id = int(args.record_id or 0)
            record = await usage.get_record(record_id)
            if (
                record is None
                or record.get("project_name") != project_name
                or await usage.get_record_owner_id(record_id) != caller.user_id
            ):
                return _not_found("record_id", args.record_id)
            if record.get("task_id"):
                linked = await TaskRepository(session).get(str(record["task_id"]))
                if (
                    linked is not None
                    and linked.get("project_name") == project_name
                    and linked.get("user_id") == caller.user_id
                ):
                    task = linked
    return ToolOutcome(
        value=build_generation_diagnostics(
            project_name=project_name,
            task=task,
            record=record,
            include_provider_response=args.include_provider_response,
        )
    )


__all__ = ["GenerationDiagnosticsRequest", "get_generation_diagnostics"]
