"""Agent access to retrieval resume for generation tasks whose provider output could not be downloaded.

Delegates to :mod:`server.services.tasks.artifact_download_retry`, the same service the Web retry-download route
calls. The task must belong to the scoped project and the caller; anything else is reported exactly like a missing
task, so the tool cannot be used to probe other projects' task IDs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from server.services.tasks.artifact_download_retry import ArtifactDownloadRetryUnavailable, retry_artifact_download
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolProblem, ToolRequest


class RetryArtifactDownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(
        min_length=1,
        description=(
            "ID of a generation task of this project that failed with artifact_download_failed "
            "(recovery action retry_artifact_download in get_generation_diagnostics or the workflow plan)"
        ),
    )


def _not_found(task_id: str) -> ToolOutcome[dict[str, Any]]:
    return ToolOutcome(
        problem=ToolProblem(
            "task_not_found", f"Task {task_id} does not exist in this project", params={"task_id": task_id}
        )
    )


async def retry_artifact_download_tool(
    request: ToolRequest[RetryArtifactDownloadRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    task_id = request.value.task_id
    task = await services.queue.get_task(task_id)
    if task is None or task.get("project_name") != scope.project_name or task.get("user_id") != caller.user_id:
        return _not_found(task_id)
    try:
        reopened = await retry_artifact_download(
            task_id, queue=services.queue, worker=services.artifact_download_worker
        )
    except ArtifactDownloadRetryUnavailable as exc:
        if exc.worker_unavailable:
            return ToolOutcome(
                problem=ToolProblem(
                    "task_retry_download_unavailable",
                    "No generation worker runs in this host, so retrieval cannot be resumed now; nothing was changed. "
                    "Try again later; do not resubmit generation.",
                    params={"task_id": task_id},
                )
            )
        return ToolOutcome(
            problem=ToolProblem(
                "task_retry_download_ineligible",
                f"Task {task_id} is not eligible for retrieval resume: only failed tasks whose recovery action is "
                "retry_artifact_download (artifact_download_failed with a recorded provider job) can resume. "
                "Nothing was changed; check get_generation_diagnostics.",
                action="get_generation_diagnostics",
                params={"task_id": task_id, "status": task.get("status")},
            )
        )
    return ToolOutcome(
        value={
            "task_id": reopened["task_id"],
            "status": reopened.get("status"),
            "task_type": reopened.get("task_type"),
            "media_type": reopened.get("media_type"),
            "resource_id": reopened.get("resource_id"),
            "script_file": reopened.get("script_file"),
            "resumed": True,
            "new_task_created": False,
        }
    )


def retry_artifact_download_summary(value: dict[str, Any]) -> str:
    return (
        f"Resumed retrieval for task {value['task_id']} ({value.get('media_type')} {value.get('resource_id')}); "
        "no new generation was submitted. Check progress with get_generation_diagnostics."
    )


__all__ = ["RetryArtifactDownloadRequest", "retry_artifact_download_summary", "retry_artifact_download_tool"]
