"""Resume retrieval of an artifact the provider already produced, shared by the Web route and the Agent tool.

A task that failed with ``artifact_download_failed`` keeps its provider job ID and its original usage call. Resuming
reopens that same task and call in place and hands the task to the running generation worker, which polls the existing
provider job and downloads the result. Nothing is submitted to the provider again and no new task or usage row is
created; callers that want a new generation must use the generation tools instead.
"""

from __future__ import annotations

from typing import Any, Protocol


class ArtifactDownloadQueue(Protocol):
    async def retry_artifact_download(self, task_id: str) -> dict[str, Any]: ...


class ArtifactDownloadWorker(Protocol):
    """The running generation worker's retrieval resume surface (``GenerationWorker`` satisfies it)."""

    async def read_video_poll_timeout_seconds(self) -> int: ...

    async def retry_artifact_download(self, task: dict[str, Any], *, poll_timeout_seconds: int) -> None: ...


class ArtifactDownloadRetryUnavailable(Exception):
    """The task cannot resume retrieval now: no generation worker runs in this process, or the task is ineligible."""

    def __init__(self, task_id: str, *, worker_unavailable: bool) -> None:
        super().__init__(task_id)
        self.task_id = task_id
        self.worker_unavailable = worker_unavailable


async def retry_artifact_download(
    task_id: str, *, queue: ArtifactDownloadQueue, worker: ArtifactDownloadWorker | None
) -> dict[str, Any]:
    """Reopen one ``artifact_download_failed`` task and dispatch retrieval of its existing provider job.

    Eligibility (failed with ``artifact_download_failed``, provider job and provider recorded, a settleable call) is
    checked by the queue under its own transaction. Returns the reopened task row.

    Raises :class:`ArtifactDownloadRetryUnavailable` when no worker is available or the task is ineligible. Other
    exceptions (such as an unreadable polling timeout) propagate unchanged."""
    if worker is None:
        raise ArtifactDownloadRetryUnavailable(task_id, worker_unavailable=True)
    try:
        # Read the polling timeout before changing state: configuration reads can fail, with no rollback point after commit,
        # leaving the task permanently running, unclaimed by the queue and ineligible for retry-download.
        poll_timeout_seconds = await worker.read_video_poll_timeout_seconds()
        task = await queue.retry_artifact_download(task_id)
        await worker.retry_artifact_download(task, poll_timeout_seconds=poll_timeout_seconds)
    except ValueError as exc:
        raise ArtifactDownloadRetryUnavailable(task_id, worker_unavailable=False) from exc
    return task


__all__ = [
    "ArtifactDownloadQueue",
    "ArtifactDownloadRetryUnavailable",
    "ArtifactDownloadWorker",
    "retry_artifact_download",
]
