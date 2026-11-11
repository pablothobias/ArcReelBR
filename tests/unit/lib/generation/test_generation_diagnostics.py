"""Sanitized generation diagnostics read model (MCP-006)."""

from __future__ import annotations

import json

import pytest

from lib.custom_provider.declarative_backend import ProviderJobRejectedError
from lib.db.repositories.usage_repo import MAX_PROVIDER_RESPONSE_BYTES, bound_provider_response
from lib.generation.generation_diagnostics import (
    MAX_STRING_CHARS,
    build_generation_diagnostics,
    sanitize_for_agent,
)
from lib.generation.persisted_provider_error import extract_persisted_provider_error
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
        "code_known": True,
        "message": 'content[6].audio_url: invalid param: audio format ".mpeg" not allowed',
        "stage": "poll",
        "source": "task_failure",
        "source_path": "$.task.error_message.params",
        "source_truncated": False,
        "source_encoding": None,
        # The body's same code with a different message is reported, never merged over the structured verdict.
        "conflicts": [
            {
                "source": "last_provider_response",
                "source_path": "$.last_provider_response.body.task.error",
                "code": "2013",
                "message": "bad",
            }
        ],
        "stored_message": "provider rejected",
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


# ---------------------------------------------------------------------------
# Historical failures: provider verdict read from the persisted response body
# ---------------------------------------------------------------------------

H3_MESSAGE = 'content[5].audio_url: invalid param: audio format ".x-wav" not allowed'
H3_BODY = {
    "task": {
        "id": "461931341250972",
        "model": "MiniMax-H3",
        "status": "failed",
        "error": {"code": "2013", "message": H3_MESSAGE},
    }
}
GENERIC = "provider reported failure (status: failed)"


def _historical(body=H3_BODY, *, record_status="failed", error_code=None):
    task = _failed_task(error_message=GENERIC, provider_job_id="461931341250972")
    record = {
        "id": 9,
        "task_id": "t1",
        "status": record_status,
        "provider": "custom-1",
        "model": "MiniMax-H3",
        "error_code": error_code,
        "error_message": GENERIC,
        "last_provider_response": body,
    }
    return task, record


def test_historical_generic_failure_reads_real_code_from_persisted_body():
    task, record = _historical()
    snapshot = json.dumps([task, record], sort_keys=True)
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    error = model["provider_error"]
    assert error["code"] == "2013"
    assert error["code_known"] is True
    assert error["message"] == H3_MESSAGE
    assert error["source"] == "last_provider_response"
    assert error["source_path"] == "$.last_provider_response.body.task.error"
    assert error["source_truncated"] is False
    assert error["source_encoding"] == "json"
    assert error["stored_message"] == GENERIC
    assert error["conflicts"] == []
    # Internal codes stay separate and unchanged.
    assert model["problem"]["code"] == "generation_task_failed"
    assert model["usage_record"]["error_code"] is None
    # No deterministic definition: the action is not upgraded, and retry guidance demands spending authorization.
    assert model["recovery"]["action"] == "retry"
    assert "new paid generation" in model["recovery"]["guidance"]
    assert "authorization" in model["recovery"]["guidance"]
    note = model["recovery"]["provider_verdict_note"]
    assert "before any resubmission" in note
    assert "internal_error_code" in note
    assert "spending authorization" in note
    assert model["provider_calls"] == 0
    # Read-only: the input rows are not mutated.
    assert json.dumps([task, record], sort_keys=True) == snapshot


def test_unknown_code_stays_explicitly_unknown():
    task, record = _historical(body={"task": {"status": "failed"}})
    error = build_generation_diagnostics(
        project_name="demo", task=task, record=record, include_provider_response=False
    )["provider_error"]
    assert error["code"] is None
    assert error["code_known"] is False
    assert error["message"] == GENERIC
    assert error["source"] == "stored_message"
    assert error["source_path"] == "$.usage_record.error_message"
    assert "stored_message" not in error


def test_body_message_without_code_keeps_code_unknown():
    task, record = _historical(body={"error": "quota exhausted for this month"})
    error = build_generation_diagnostics(
        project_name="demo", task=task, record=record, include_provider_response=False
    )["provider_error"]
    assert (error["code"], error["code_known"], error["message"]) == (None, False, "quota exhausted for this month")
    assert error["source_path"] == "$.last_provider_response.body.error"
    assert error["stored_message"] == GENERIC


def test_internal_usage_error_code_never_becomes_the_provider_code():
    task, record = _historical(error_code="rate_limited")
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    error = model["provider_error"]
    assert error["source"] == "last_provider_response"
    assert (error["code"], error["message"]) == ("2013", H3_MESSAGE)
    assert error["internal_error_code"] == "rate_limited"
    assert error["conflicts"] == []
    assert model["usage_record"]["error_code"] == "rate_limited"


def test_internal_usage_error_code_without_body_code_keeps_provider_code_unknown():
    task, record = _historical(body={"task": {"status": "failed"}}, error_code="rate_limited")
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    error = model["provider_error"]
    assert (error["code"], error["code_known"], error["source"]) == (None, False, "stored_message")
    assert error["message"] == GENERIC
    assert error["internal_error_code"] == "rate_limited"
    assert model["usage_record"]["error_code"] == "rate_limited"


def test_structured_task_failure_outranks_body_and_reports_conflict():
    _task, record = _historical(error_code="content_policy")
    error = build_generation_diagnostics(
        project_name="demo", task=_failed_task(), record=record, include_provider_response=False
    )["provider_error"]
    assert error["source"] == "task_failure"
    assert error["code"] == "2013"
    assert error["internal_error_code"] == "content_policy"
    # Same code, different message: listed, never merged over the structured verdict.
    assert error["conflicts"] == [
        {
            "source": "last_provider_response",
            "source_path": "$.last_provider_response.body.task.error",
            "code": "2013",
            "message": H3_MESSAGE,
        }
    ]


def test_body_is_ignored_while_nothing_failed():
    task = _failed_task(status="running", error_message=None, finished_at=None)
    record = {"id": 8, "task_id": "t1", "status": "pending", "last_provider_response": H3_BODY}
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    assert model["provider_error"] is None


@pytest.mark.parametrize(
    "body",
    [
        "not json at all",
        '{"task": {"error": {"code": "20',
        {"truncated": True, "body": '{"task":{"id":"1","error":{"code":"2013","mess'},
        {"truncated": True, "body": 12},
        ["a", "list"],
        12,
        {"error": None, "task": "failed", "data": [1, 2]},
        {"error": {"code": True, "message": ""}},
        {"base_resp": {"status_code": 0, "status_msg": "success"}},
        {"task": {"error": {"code": {"nested": "x"}, "message": ["x"]}}},
    ],
)
def test_malformed_or_truncated_bodies_fail_safe(body):
    task, record = _historical(body=body)
    error = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=True)[
        "provider_error"
    ]
    assert error["code"] is None
    assert error["code_known"] is False
    assert error["message"] == GENERIC
    assert error["source"] == "stored_message"


def test_body_bounded_at_persistence_yields_no_verdict_and_reports_truncation():
    """The real persistence bound keeps a cut prefix of oversized JSON, so the code stays unknown, never guessed."""
    oversized = {**H3_BODY, "padding": "x" * (MAX_PROVIDER_RESPONSE_BYTES * 2)}
    bounded = bound_provider_response(oversized)
    assert isinstance(bounded, dict)
    assert bounded["truncated"] is True
    task, record = _historical(body=bounded)
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    error = model["provider_error"]
    assert error["source"] == "stored_message"
    assert error["code"] is None
    assert error["code_known"] is False
    assert model["truncation"]["source_truncated"] is True


def test_minimax_base_resp_and_string_body_shapes():
    for body, path in (
        ({"base_resp": {"status_code": 1008, "status_msg": "insufficient balance"}}, "base_resp"),
        (json.dumps({"data": {"error": {"error_code": 400, "msg": "bad size"}}}), "data.error"),
    ):
        task, record = _historical(body=body)
        error = build_generation_diagnostics(
            project_name="demo", task=task, record=record, include_provider_response=False
        )["provider_error"]
        assert error["source_path"] == f"$.last_provider_response.body.{path}"
        assert error["source_encoding"] == ("json_text" if isinstance(body, str) else "json")
        assert error["code"] in {"1008", "400"}
        assert error["message"] in {"insufficient balance", "bad size"}


def test_secret_bearing_body_error_is_sanitized():
    body = {
        "error": {
            "code": 401,
            "message": f"invalid key={SECRET} for https://cdn.example/a.mp4?X-Amz-Signature=deadbeef "
            + "data:audio/wav;base64,"
            + "Q" * 3000,
        },
        "headers": {"Authorization": f"Bearer {SECRET}", "Cookie": "session=abc"},
    }
    task, record = _historical(body=body)
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=True)
    assert model["provider_error"]["code"] == "401"
    text = json.dumps(model)
    for leaked in (SECRET, "deadbeef", "session=abc", "QQQQ"):
        assert leaked not in text


def test_success_coded_error_object_is_not_a_verdict():
    for body in ({"error": {"code": 0, "message": "success"}}, {"task": {"error": {"code": "0", "message": "ok"}}}):
        task, record = _historical(body=body)
        model = build_generation_diagnostics(
            project_name="demo", task=task, record=record, include_provider_response=False
        )
        assert model["provider_error"]["source"] == "stored_message"
        assert model["provider_error"]["code"] is None
        assert "provider_verdict_note" not in model["recovery"]


def test_overlong_provider_code_is_unknown():
    task, record = _historical(body={"error": {"code": "9" * 129, "message": "rejected"}})
    error = build_generation_diagnostics(
        project_name="demo", task=task, record=record, include_provider_response=False
    )["provider_error"]
    assert (error["code"], error["code_known"], error["message"]) == (None, False, "rejected")
    assert error["source"] == "last_provider_response"
    task, record = _historical(body={"error": {"code": "9" * 128, "message": "rejected"}})
    error = build_generation_diagnostics(
        project_name="demo", task=task, record=record, include_provider_response=False
    )["provider_error"]
    assert error["code"] == "9" * 128


def test_verdict_note_only_for_body_sourced_retry():
    model = build_generation_diagnostics(
        project_name="demo", task=_failed_task(), record=None, include_provider_response=False
    )
    assert model["recovery"]["action"] == "fix_input"
    assert "provider_verdict_note" not in model["recovery"]


@pytest.mark.parametrize("record_status", [None, "succeeded"])
def test_failure_without_provider_involvement_is_not_a_provider_error(record_status):
    """A task that never submitted a provider job failed inside ArcReel; its reason is not the provider's verdict."""
    task = _failed_task(error_message="reference image not found: chars/a.png", provider_job_id=None)
    record = None
    if record_status is not None:
        record = {"id": 9, "task_id": "t1", "status": record_status, "error_code": None, "error_message": None}
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    assert model["provider_error"] is None
    assert "provider_verdict_note" not in model["recovery"]


def test_generic_task_reason_after_provider_submission_stays_an_unknown_provider_error():
    task = _failed_task(error_message=GENERIC, provider_job_id="461931341250972")
    error = build_generation_diagnostics(project_name="demo", task=task, record=None, include_provider_response=False)[
        "provider_error"
    ]
    assert error["source"] == "stored_message"
    assert error["source_path"] == "$.task.error_message"
    assert error["code"] is None
    assert error["code_known"] is False


def test_message_only_body_verdict_adds_no_deterministic_rejection_note():
    task, record = _historical(body={"error": {"message": "quota exhausted"}})
    model = build_generation_diagnostics(project_name="demo", task=task, record=record, include_provider_response=False)
    assert model["provider_error"]["source"] == "last_provider_response"
    assert model["provider_error"]["code_known"] is False
    assert model["recovery"]["action"] == "retry"
    assert "provider_verdict_note" not in model["recovery"]


@pytest.mark.parametrize(
    ("node", "expected_code"),
    [
        ({"code": "0", "error_code": "2013", "message": "bad audio"}, "2013"),
        ({"code": 0, "error_code": 0, "message": "success"}, None),
    ],
)
def test_success_code_does_not_hide_a_failure_code_in_the_same_error_object(node, expected_code):
    found = extract_persisted_provider_error({"error": node})
    if expected_code is None:
        assert found is None
    else:
        assert found is not None
        assert found.code == expected_code
