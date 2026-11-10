"""Artifact-download recovery declaration: resume retrieval of provider output without resubmitting generation."""

from __future__ import annotations

from server.agent_toolset.declaration import BLOCKED, ToolDeclaration
from server.media_tools.artifact_download import (
    RetryArtifactDownloadRequest,
    retry_artifact_download_summary,
    retry_artifact_download_tool,
)

RETRY_ARTIFACT_DOWNLOAD = ToolDeclaration(
    name="retry_artifact_download",
    description=(
        "Resume retrieval for one generation task of this project that failed with artifact_download_failed "
        "(recovery action retry_artifact_download): the provider already produced the output but the download failed. "
        "Reopens the same task and its original usage record and lets the running generation worker poll the existing "
        "provider job and download the result. It never resubmits generation, creates no new task, and creates no new "
        "charge; do not call a generation tool to recover these tasks, which would pay again. Returns immediately "
        "with the reopened task (status running); follow progress with get_generation_diagnostics. Returns "
        "task_not_found for IDs outside this project, task_retry_download_ineligible when the task is not an "
        "artifact_download_failed task with a recorded provider job, and task_retry_download_unavailable when no "
        "generation worker runs in this host; in every refusal nothing is changed."
    ),
    request_model=RetryArtifactDownloadRequest,
    migration=BLOCKED,
    domain_key="retry_artifact_download",
    handler=retry_artifact_download_tool,
    summary=retry_artifact_download_summary,
)

ARTIFACT_DOWNLOAD_TOOLS = (RETRY_ARTIFACT_DOWNLOAD,)

__all__ = ["ARTIFACT_DOWNLOAD_TOOLS", "RETRY_ARTIFACT_DOWNLOAD"]
