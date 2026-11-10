"""Sanitized generation diagnostics read model (MCP-006)."""

from __future__ import annotations

import json

from lib.custom_provider.declarative_backend import ProviderJobRejectedError
from lib.generation.generation_diagnostics import (
    MAX_STRING_CHARS,
    build_generation_diagnostics,
    sanitize_for_agent,
)
from lib.generation.task_failure_encoding import encode_task_failure_message

SECRET = "sk-live-0123456789abcdef"


def test_nested_secrets_signed_urls_and_media_are_removed():
    body = {
        "headers": {"Authorization": f"Bearer {SECRET}", "Cookie": "session=abc", "x-api-key": SECRET},
        "nested": [{"api_key": SECRET, "note": f"retry with token={SECRET}"}],
        "video": "https://cdn.example/out.mp4?X-Amz-Signature=deadbeef&Expires=1",
        "audio_url": "data:audio/mpeg;base64," + "A" * 5000,
        "raw": "B" * 600,
        "task": {"error": {"code": 2013, "message": 'audio format ".mpeg" not allowed'}},
    }
    cleaned, truncated = sanitize_for_agent(body)
    text = json.dumps(cleaned)
    assert SECRET not in text
    assert "session=abc" not in text
    assert "deadbeef" not in text
    assert "AAAA" not in text
    assert "BBBB" not in text
    assert "<data-uri removed: audio/mpeg" in cleaned["audio_url"]
    assert cleaned["task"]["error"] == {"code": 2013, "message": 'audio format ".mpeg" not allowed'}
    assert truncated == []


def test_truncation_is_explicit_and_located():
    cleaned, truncated = sanitize_for_agent({"message": "word " * MAX_STRING_CHARS, "items": list(range(80))})
    assert cleaned["message"].endswith("more chars>")
    assert cleaned["items"][-1] == "<truncated: 30 more items>"
    assert truncated == ["$.message", "$.items"]


def _failed_task(**overrides):
    error = ProviderJobRejectedError(
        provider_error_code="2013",
        provider_error_message='content[6].audio_url: invalid param: audio format ".mpeg" not allowed',
        stage="poll",
        classification="fix_input",
        provider_status="failed",
    )
    task = {
        "task_id": "t1",
        "task_type": "reference_video",
        "resource_id": "E1U1",
        "status": "failed",
        "provider_id": "custom-1",
        "provider_job_id": "461931189367168",
        "execution_checkpoint_json": "{}",
        "error_message": encode_task_failure_message(error),
        "queued_at": "2026-11-10T10:00:00+00:00",
        "started_at": "2026-11-10T10:00:01+00:00",
        "finished_at": "2026-11-10T10:03:00+00:00",
        "updated_at": "2026-11-10T10:03:00+00:00",
        "payload": {"prompt": "never exposed"},
    }
    task.update(overrides)
    return task


def test_failed_task_reports_provider_verdict_and_fix_input_guidance():
    record = {
        "id": 7,
        "task_id": "t1",
        "status": "failed",
        "provider": "custom-1",
        "model": "MiniMax-H3",
        "error_message": "provider rejected",
        "last_provider_response": {
            "task": {"status": "failed", "error": {"code": 2013, "message": "bad"}},
            "headers": {"Authorization": f"Bearer {SECRET}"},
        },
    }
    model = build_generation_diagnostics(
        project_name="demo", task=_failed_task(), record=record, include_provider_response=True
    )
    assert model["stage"] == "failed"
    assert model["provider_error"] == {
        "code": "2013",
        "message": 'content[6].audio_url: invalid param: audio format ".mpeg" not allowed',
        "stage": "poll",
        "source": "task_failure",
    }
    assert model["problem"]["code"] == "provider_job_rejected"
    assert model["recovery"]["action"] == "fix_input"
    assert model["task"]["provider_job_id"] == "461931189367168"
    assert model["task"]["submitted"] is True
    assert model["last_provider_response"]["observed_at"] is None
    assert model["last_provider_response"]["observed_at_known"] is False
    assert model["last_provider_response"]["body"]["task"]["error"]["code"] == 2013
    assert model["provider_calls"] == 0
    text = json.dumps(model)
    assert SECRET not in text
    assert "never exposed" not in text


def test_running_task_advises_waiting_and_flags_source_truncation():
    task = _failed_task(status="running", error_message=None, finished_at=None)
    record = {"id": 8, "task_id": "t1", "status": "pending", "last_provider_response": {"truncated": True, "body": "{"}}
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    assert model["stage"] == "provider_job_active"
    assert model["recovery"]["action"] == "wait_for_task"
    assert model["problem"] is None
    assert "body" not in model["last_provider_response"]
    assert model["truncation"]["source_truncated"] is True
    assert model["truncation"]["truncated"] is True


def test_queued_task_without_any_call_is_explicitly_unknown():
    task = _failed_task(status="queued", error_message=None, provider_job_id=None, execution_checkpoint_json=None)
    model = build_generation_diagnostics(project_name="demo", task=task, record=None, include_provider_response=True)
    assert model["stage"] == "queued"
    assert model["task"]["submitted"] is False
    assert model["last_provider_response"] == {"recorded": False, "observed_at": None, "observed_at_known": False}
    assert model["usage_record"] is None
