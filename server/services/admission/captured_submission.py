"""Read a submitted video task's captured inputs from its native execution checkpoint.

Distinct from prompt previews: a preview renders *current* files and configuration, while this reads the immutable
facts the worker froze when it submitted the provider request (prompt, ordered task-local media with digests,
audio targets, model identity). Read-only; staged locators stay internal."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from lib.script.reference_video.execution_checkpoint import load_task_video_checkpoint


class CapturedSubmissionError(LookupError):
    """``code`` is stable: ``task_not_found``, ``task_target_mismatch`` or ``captured_submission_unavailable``."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def captured_video_submission(
    task: dict[str, Any] | None, *, project_name: str, user_id: str, script_file: str, item_id: str
) -> dict[str, Any]:
    """Project the task's execution checkpoint after verifying it belongs to this project/caller/script/entry."""

    # Another project's or caller's task is indistinguishable from an absent one: no existence oracle.
    if task is None or task.get("project_name") != project_name or task.get("user_id") != user_id:
        raise CapturedSubmissionError("task_not_found", "Task not found")
    row_script = PurePosixPath(str(task.get("script_file") or "")).name
    if str(task.get("resource_id")) != item_id or row_script != PurePosixPath(script_file).name:
        raise CapturedSubmissionError("task_target_mismatch", "The task does not belong to this script and entry")
    if not task.get("execution_checkpoint_json"):
        raise CapturedSubmissionError(
            "captured_submission_unavailable",
            "The task has no execution checkpoint (not yet submitted to the provider, or not a video task)",
        )
    try:
        checkpoint = load_task_video_checkpoint(task)
    except ValueError as exc:
        raise CapturedSubmissionError("captured_submission_unavailable", str(exc)) from exc
    return {
        "task_id": checkpoint.task_id,
        "task_status": task.get("status"),
        "kind": checkpoint.kind,
        "schema_version": checkpoint.schema_version,
        "generation_type": checkpoint.generation_type,
        "provider_id": checkpoint.provider_id,
        "provider_model_id": checkpoint.provider_model_id,
        "backend_model_id": checkpoint.backend_model_id,
        "prompt": checkpoint.prompt,
        "prompt_sha256": checkpoint.prompt_sha256,
        "duration_seconds": checkpoint.duration_seconds,
        "aspect_ratio": checkpoint.aspect_ratio,
        "resolution": checkpoint.resolution,
        "generate_audio": checkpoint.generate_audio,
        "media": [
            {
                "index": media.index,
                "role": media.role,
                "logical_type": media.logical_type,
                "logical_name": media.logical_name,
                "kind": media.kind,
                "source_artifact_path": media.source_locator,
                "sha256": media.sha256,
                "size_bytes": media.size_bytes,
                "target_index": media.target_index,
            }
            for media in checkpoint.media
        ],
        "reference_audio_targets": list(checkpoint.reference_audio_targets)
        if checkpoint.reference_audio_targets is not None
        else None,
        "request_digest": checkpoint.request_digest,
    }


__all__ = ["CapturedSubmissionError", "captured_video_submission"]
