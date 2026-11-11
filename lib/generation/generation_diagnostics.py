"""Sanitized generation diagnostics: one task's or usage record's state, provider verdict, and recovery guidance.

The financial usage reader deliberately omits provider responses, and the Web usage detail returns the stored response
as is. Agents need the provider's real failure reason (for example MiniMax ``task.error.code=2013`` with its message)
without UI access, but never credentials, signed URLs, or media payloads. This module builds that read model from rows
the worker already persisted — the task row and the latest ``api_calls`` row — and never contacts a provider.

Sanitization is recursive and explicit:

* sensitive keys (``Authorization``, ``api_key``, ``cookie``, tokens …) are masked by the shared
  :func:`lib.infra.logging_utils.sanitize_diagnostic_payload` key rules;
* every string drops ``data:`` URIs and long base64 runs (media payloads), then URL query strings and inline
  credentials (:func:`lib.backends.backend_runtime.redact_provider_text`);
* long strings, long lists, deep nesting and oversized totals are cut with visible markers, and every cut is listed
  in ``truncation.paths``; a response already bounded at persistence (``{"truncated": true, "body": …}``) is
  reported as ``truncation.source_truncated``.

``provider_error`` is chosen by explicit precedence with provenance (see :func:`_provider_error`); for historical
failures that stored only a generic reason, the provider's real code and message are read from the persisted response
body (:mod:`lib.generation.persisted_provider_error`).

Timestamps the worker did not persist stay ``None`` with an explicit ``*_known: false`` flag; nothing is inferred.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from lib.backends.backend_runtime import redact_provider_text
from lib.generation.generation_result import (
    GenerationAction,
    GenerationProblem,
    problem_from_task_failure,
)
from lib.generation.persisted_provider_error import extract_persisted_provider_error, is_truncation_wrapper
from lib.infra.logging_utils import sanitize_diagnostic_payload

#: Longest string kept verbatim; longer strings keep a prefix plus a marker.
MAX_STRING_CHARS = 2000
#: Longest list kept; longer lists keep the head plus a marker item.
MAX_LIST_ITEMS = 50
#: Deepest nesting kept; deeper values become a marker.
MAX_DEPTH = 12
#: Approximate serialized budget for one sanitized payload; past it, remaining strings collapse to markers.
MAX_TOTAL_CHARS = 32_000

_DATA_URI_RE = re.compile(r"data:([A-Za-z0-9.+/-]*)((?:;[A-Za-z0-9=._-]+)*),[A-Za-z0-9+/=%._~-]*")
_BASE64_RUN_RE = re.compile(r"[A-Za-z0-9+/]{256,}={0,2}")


def _strip_media(text: str) -> str:
    text = _DATA_URI_RE.sub(lambda m: f"<data-uri removed: {m.group(1) or 'unknown'}, {len(m.group(0))} chars>", text)
    return _BASE64_RUN_RE.sub(lambda m: f"<base64 removed: {len(m.group(0))} chars>", text)


def redact_agent_text(value: object) -> str:
    """Remove media payloads, URL queries and credentials from one string destined for an agent."""
    text = value if isinstance(value, str) else str(value)
    return redact_provider_text(_strip_media(text))


@dataclass
class _Cut:
    paths: list[str] = field(default_factory=list)
    used: int = 0

    def note(self, path: str) -> None:
        if path not in self.paths:
            self.paths.append(path)


def _limit(value: Any, path: str, depth: int, cut: _Cut) -> Any:
    if depth > MAX_DEPTH:
        cut.note(path)
        return "<truncated: nesting too deep>"
    if isinstance(value, str):
        if cut.used >= MAX_TOTAL_CHARS:
            cut.note(path)
            return f"<truncated: diagnostic budget exhausted, {len(value)} chars>"
        if len(value) > MAX_STRING_CHARS:
            cut.note(path)
            value = f"{value[:MAX_STRING_CHARS]}…<truncated: {len(value) - MAX_STRING_CHARS} more chars>"
        cut.used += len(value)
        return value
    if isinstance(value, Mapping):
        return {key: _limit(item, f"{path}.{key}", depth + 1, cut) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        items = [_limit(item, f"{path}[{index}]", depth + 1, cut) for index, item in enumerate(value[:MAX_LIST_ITEMS])]
        if len(value) > MAX_LIST_ITEMS:
            cut.note(path)
            items.append(f"<truncated: {len(value) - MAX_LIST_ITEMS} more items>")
        return items
    cut.used += 8
    return value


def sanitize_for_agent(value: object, *, path: str = "$") -> tuple[Any, list[str]]:
    """Recursively redact and bound a JSON-compatible value; return it with the paths that were truncated."""
    redacted = sanitize_diagnostic_payload(value, redact_text=redact_agent_text)
    cut = _Cut()
    return _limit(redacted, path, 0, cut), cut.paths


#: Next-step wording per closed action. Agents dispatch on ``action``; ``guidance`` explains it without prose parsing.
_ACTION_GUIDANCE: dict[str, str] = {
    GenerationAction.WAIT_FOR_TASK: (
        "The task is still active. Keep polling get_generation_batch with the same batch handle at its "
        "poll_after_seconds; do not resubmit, which could create a second paid provider job."
    ),
    GenerationAction.FIX_INPUT: (
        "The failure is deterministic for the same request. Fix the reported input or endpoint configuration first; "
        "resubmitting unchanged is billed again for the same rejection."
    ),
    GenerationAction.CONFIGURE_PROVIDER: (
        "The endpoint definition or provider configuration could not render or read this request; fix the "
        "configuration before any resubmission."
    ),
    GenerationAction.RETRY_ARTIFACT_DOWNLOAD: (
        "The provider finished the job but the artifact was not retrieved; retry the download from the same job "
        "without regenerating."
    ),
    GenerationAction.RETRY: (
        "A resubmission is allowed by the failure classification but is a new paid generation; it requires the "
        "user's spending authorization."
    ),
    GenerationAction.GENERATE_DEPENDENCY: "Generate the failed dependency first; this unit was never submitted.",
    GenerationAction.NONE: "No action is required.",
}


def _guidance(action: str) -> str:
    return _ACTION_GUIDANCE.get(action, "Follow the problem's action; no automatic resubmission is implied.")


#: Added when a retry classification rests on a generic stored reason while the persisted response holds a verdict.
PROVIDER_VERDICT_NOTE = (
    "The provider's persisted verdict is more specific than the stored task reason, which did not classify it. "
    "Inspect provider_error (and internal_error_code when present) before any resubmission: it may call for fixing "
    "inputs or configuration rather than retrying. A resubmission is a new paid generation and requires the user's "
    "spending authorization."
)


def _recovery(action: str, provider_error: Mapping[str, Any] | None) -> dict[str, Any]:
    """Recovery advice; the action itself is never upgraded from a body-derived verdict."""
    recovery: dict[str, Any] = {"action": action, "guidance": _guidance(action)}
    if (
        action == GenerationAction.RETRY
        and provider_error is not None
        and provider_error.get("source") == "last_provider_response"
        # A message without a code (for example a quota text) is no evidence of a deterministic input rejection.
        and provider_error.get("code_known") is True
    ):
        recovery["provider_verdict_note"] = PROVIDER_VERDICT_NOTE
    return recovery


def _stage(task: Mapping[str, Any] | None, record: Mapping[str, Any] | None) -> str:
    if task is None:
        status = (record or {}).get("status")
        return f"usage_{status}" if status else "unknown"
    status = task.get("status")
    if status == "queued":
        return "queued"
    if status == "running":
        return "provider_job_active" if task.get("provider_job_id") else "executing_before_provider_job"
    return str(status or "unknown")


def _checkpoint_state(task: Mapping[str, Any]) -> str | None:
    """Resume classification of the persisted checkpoint/job pair; raw checkpoint JSON never leaves the server."""
    if task.get("task_type") not in {"video", "reference_video"}:
        return None
    from lib.script.reference_video.execution_checkpoint import classify_video_resume_state

    state, _checkpoint = classify_video_resume_state(dict(task))
    return state.value


def task_checkpoint_summary(task: Mapping[str, Any]) -> dict[str, Any]:
    """Provider submission facts persisted on the task row, shared by batch members and diagnostics."""
    provider_job_id = task.get("provider_job_id")
    return {
        "submitted": bool(provider_job_id),
        "provider_id": task.get("provider_id"),
        "provider_job_id": provider_job_id,
        "checkpoint_state": _checkpoint_state(task),
        "started_at": task.get("started_at"),
        "updated_at": task.get("updated_at"),
    }


def _same_text(left: object, right: object) -> bool:
    return str(left).strip() == str(right).strip()


def _provider_error(
    problem: GenerationProblem | None,
    task: Mapping[str, Any] | None,
    record: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """The provider's own verdict with provenance, chosen by explicit precedence.

    1. ``task_failure``: structured task failure params (``provider_error_code`` lifted by the backend);
    2. ``last_provider_response``: a real error object in the persisted response body (well-known shapes,
       :mod:`lib.generation.persisted_provider_error`), considered only when the task or record failed;
    3. ``stored_message``: the generic stored failure text, with the code explicitly unknown.

    The usage record's ``error_code`` is ArcReel's internal call-failure class (:mod:`lib.billing.call_failure`,
    e.g. ``rate_limited``), not a provider code, so it never becomes ``code``; it is echoed as
    ``internal_error_code`` and stays in ``usage_record.error_code``.

    Lower-precedence sources never override the chosen one; when they carry a different non-null code or message they
    are listed in ``conflicts``. A code is never inferred: ``code_known`` is false whenever the chosen source has none.
    The generic stored text stays available as ``stored_message`` when a more specific source was chosen.
    ``source_encoding`` is set for the body source: ``json`` when the stored body was structured, ``json_text`` when
    it was a raw JSON string decoded here, in which case ``source_path`` addresses the decoded document. A body cut at
    persistence never yields a verdict, so the body source is never truncated.
    """
    task_failed = task is not None and task.get("status") == "failed"
    record_failed = record is not None and record.get("status") == "failed"

    stored_message: str | None = None
    stored_path: str | None = None
    if record_failed and record is not None and record.get("error_message"):
        stored_message, stored_path = record.get("error_message"), "$.usage_record.error_message"
    elif (
        task_failed
        and task is not None
        # Only with evidence of provider involvement: a task that never submitted a provider job failed inside ArcReel
        # (missing input, storage, promotion), and its reason is not the provider's verdict.
        and task.get("provider_job_id")
        and problem is not None
        and "provider_error_code" not in problem.params
        and problem.detail
    ):
        stored_message, stored_path = problem.detail, "$.task.error_message"

    candidates: list[dict[str, Any]] = []
    if problem is not None and "provider_error_code" in problem.params:
        candidates.append(
            {
                "code": problem.params.get("provider_error_code"),
                "message": problem.params.get("provider_error_message"),
                "stage": problem.params.get("stage"),
                "source": "task_failure",
                "source_path": "$.task.error_message.params",
                "source_truncated": False,
                "source_encoding": None,
            }
        )
    if (task_failed or record_failed) and record is not None:
        found = extract_persisted_provider_error(record.get("last_provider_response"))
        if found is not None:
            candidates.append(
                {
                    "code": found.code,
                    "message": found.message,
                    "stage": None,
                    "source": "last_provider_response",
                    # Relative to this read model, where the sanitized body is exposed at ``$.last_provider_response.body``.
                    "source_path": f"$.last_provider_response.body{found.path.removeprefix('$')}",
                    # A verdict is only read from untruncated bodies (see persisted_provider_error).
                    "source_truncated": False,
                    "source_encoding": found.source_encoding,
                }
            )
    if not candidates and stored_message is not None:
        candidates.append(
            {
                "code": None,
                "message": stored_message,
                "stage": None,
                "source": "stored_message",
                "source_path": stored_path,
                "source_truncated": False,
                "source_encoding": None,
            }
        )
    if not candidates:
        return None

    chosen, *others = candidates
    conflicts = [
        {key: other[key] for key in ("source", "source_path", "code", "message")}
        for other in others
        if (other["code"] is not None and chosen["code"] is not None and not _same_text(other["code"], chosen["code"]))
        or (other["code"] is not None and chosen["code"] is None)
        or (
            other["message"] is not None
            and chosen["message"] is not None
            and not _same_text(other["message"], chosen["message"])
        )
    ]
    code = chosen["code"]
    result = {
        **chosen,
        "code": None if code is None else str(code),
        "code_known": code is not None,
        "conflicts": conflicts,
    }
    internal_error_code = record.get("error_code") if record is not None else None
    if internal_error_code is not None:
        result["internal_error_code"] = internal_error_code
    if chosen["source"] != "stored_message" and stored_message is not None:
        result["stored_message"] = stored_message
    return result


def build_generation_diagnostics(
    *,
    project_name: str,
    task: Mapping[str, Any] | None,
    record: Mapping[str, Any] | None,
    include_provider_response: bool,
) -> dict[str, Any]:
    """Assemble the sanitized diagnostic read model from persisted rows only (no provider calls)."""
    truncated: list[str] = []

    def clean(value: object, path: str) -> Any:
        cleaned, paths = sanitize_for_agent(value, path=path)
        truncated.extend(paths)
        return cleaned

    problem: GenerationProblem | None = None
    task_view: dict[str, Any] | None = None
    if task is not None:
        status = task.get("status")
        if status in {"failed", "cancelled"}:
            problem = problem_from_task_failure(task.get("error_message"), cancelled=status == "cancelled")
        task_view = {
            "task_id": task.get("task_id"),
            "task_type": task.get("task_type"),
            "resource_id": task.get("resource_id"),
            "status": status,
            "queued_at": task.get("queued_at"),
            "finished_at": task.get("finished_at"),
            **task_checkpoint_summary(task),
        }

    if problem is not None:
        action: str = problem.action
    elif (task is not None and task.get("status") in {"queued", "running"}) or (
        task is None and record is not None and record.get("status") == "pending"
    ):
        action = GenerationAction.WAIT_FOR_TASK
    else:
        action = GenerationAction.NONE

    record_view: dict[str, Any] | None = None
    last_response: dict[str, Any] = {"recorded": False, "observed_at": None, "observed_at_known": False}
    source_truncated = False
    if record is not None:
        record_view = {
            "record_id": record.get("id"),
            "task_id": record.get("task_id"),
            "status": record.get("status"),
            "provider": record.get("provider"),
            "model": record.get("model"),
            "media_type": record.get("media_type"),
            "started_at": record.get("started_at"),
            "finished_at": record.get("finished_at"),
            "error_code": record.get("error_code"),
            "error_params": clean(record.get("error_params"), "$.usage_record.error_params"),
            "error_message": clean(record.get("error_message"), "$.usage_record.error_message"),
        }
        body = record.get("last_provider_response")
        if body is not None:
            source_truncated = is_truncation_wrapper(body)
            last_response = {
                "recorded": True,
                # The worker overwrites the last response without a timestamp; the observation time is unknown.
                "observed_at": None,
                "observed_at_known": False,
                "source_truncated": source_truncated,
            }
            if include_provider_response:
                last_response["body"] = clean(body, "$.last_provider_response.body")

    problem_view = None
    if problem is not None:
        problem_view = {
            "code": problem.code,
            "action": problem.action,
            "params": clean(problem.params, "$.problem.params"),
            "detail": clean(problem.detail, "$.problem.detail"),
        }
    provider_error = _provider_error(problem, task, record)
    if provider_error is not None:
        provider_error = clean(provider_error, "$.provider_error")

    return {
        "project": project_name,
        "stage": _stage(task, record),
        "task": task_view,
        "usage_record": record_view,
        "problem": problem_view,
        "provider_error": provider_error,
        "last_provider_response": last_response,
        "recovery": _recovery(action, provider_error),
        "truncation": {
            "truncated": bool(truncated) or source_truncated,
            "paths": truncated,
            "source_truncated": source_truncated,
            "limits": {
                "max_string_chars": MAX_STRING_CHARS,
                "max_list_items": MAX_LIST_ITEMS,
                "max_depth": MAX_DEPTH,
                "max_total_chars": MAX_TOTAL_CHARS,
            },
        },
        "provider_calls": 0,
    }


def diagnostics_json_size(model: Mapping[str, Any]) -> int:
    """Serialized size, used by tests to keep the read model bounded."""
    return len(json.dumps(model, ensure_ascii=False, default=str))


__all__ = [
    "MAX_STRING_CHARS",
    "build_generation_diagnostics",
    "diagnostics_json_size",
    "redact_agent_text",
    "sanitize_for_agent",
    "task_checkpoint_summary",
]
