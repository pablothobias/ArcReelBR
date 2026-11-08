"""Director-side allowance and replay decisions use only controlled evidence fixtures."""

import copy
import json
import runpy
from pathlib import Path

import pytest

_POLICY = runpy.run_path(
    str(Path(__file__).resolve().parents[3] / ".agents/skills/direct-brazilian-production/scripts/policy.py")
)
Pause = _POLICY["Pause"]
decide = _POLICY["decide"]
reserve = _POLICY["reserve"]
reconcile = _POLICY["reconcile"]
resume = _POLICY["resume"]
commitment = _POLICY["commitment"]


def record():
    return {
        "approval": {
            "round": "sample-9",
            "currency": "USD",
            "round_limit": "10.00",
            "per_video": {"sample": "10.00"},
            "user_evidence_ref": "chat:explicit-approval",
            "quote_refs": ["quote:unit"],
        },
        "intents": [],
    }


def action(identifier="intent-1", kind="initial", maximum="3.00", segment="E1U01"):
    return {
        "intent_id": identifier,
        "client_key": f"key-{identifier}",
        "kind": kind,
        "video_id": "sample",
        "segment_id": segment,
        "quote_ref": "quote:unit",
        "currency": "USD",
        "maximum": maximum,
    }


def observed(identifier="intent-1", status="complete", settled="3.00", **fields):
    return {
        "intent_id": identifier,
        "status": status,
        "job_ref": f"task:{identifier}",
        "state_evidence_ref": f"state:{identifier}",
        "usage_ref": f"usage:{identifier}",
        "currency": "USD",
        "settled_amount": settled,
        **fields,
    }


@pytest.mark.parametrize(("field", "value"), [("round_limit", None), ("user_evidence_ref", ""), ("quote_refs", [])])
def test_missing_numeric_approval_or_evidence_pauses(field, value):
    state = record()
    state["approval"][field] = value
    with pytest.raises(Pause):
        reserve(state, action())
    assert state["intents"] == []


@pytest.mark.parametrize("price", [None, True, "NaN", "Infinity", "-1"])
def test_unknown_or_unusable_price_never_authorizes_submission(price):
    with pytest.raises(Pause):
        reserve(record(), action(maximum=price))


def test_budget_includes_settled_discarded_work_and_billable_transport_retry():
    state, _ = reserve(record(), action(maximum="6.00"))
    state = reconcile(state, observed(status="failed", settled="6.00", discarded=True, resubmission_safe=True))
    state, decision = reserve(state, action("retry", "transport_retry", "3.00"))
    assert decision["quality_attempt"] == 1
    assert commitment(state) == 9
    state = reconcile(state, observed("retry", status="failed", settled="3.00", resubmission_safe=True))
    with pytest.raises(Pause, match="allowance exhausted"):
        reserve(state, action("retry-2", "transport_retry", "2.00"))
    assert commitment(state) == 9


def test_pending_commitment_is_reserved_and_timeout_does_not_authorize_a_new_submission():
    state, _ = reserve(record(), action(maximum="8.00"))
    assert commitment(state) == 8
    with pytest.raises(Pause, match="pending"):
        reserve(state, action("another", maximum="1.00", segment="E1U02"))
    assert decide(state, action())["decision"] == "reconcile_existing"
    with pytest.raises(Pause, match="Absence or timeout"):
        reconcile(state, {"intent_id": "intent-1", "status": "not_submitted", "state_evidence_ref": "timeout"})


def test_interruption_reentry_reuses_finished_authoritative_job_without_duplicate_submission(tmp_path):
    path = tmp_path / "recovery.json"
    state, decision = reserve(record(), action())
    submissions = []
    path.write_text(json.dumps(state))
    if decision["decision"] == "reserve_before_delegating":
        submissions.append("application-job-1")
    recovered = json.loads(path.read_text())
    assert decide(recovered, action())["decision"] == "reconcile_existing"
    recovered = reconcile(recovered, observed())
    path.write_text(json.dumps(recovered))
    updated, decision = reserve(json.loads(path.read_text()), action())
    if decision["decision"] == "reserve_before_delegating":
        submissions.append("duplicate")
    assert decision["decision"] == "reuse_complete"
    assert submissions == ["application-job-1"]
    assert len(updated["intents"]) == 1
    assert commitment(updated) == 3


def test_polling_preserves_reservation_and_quality_attempts_even_during_quota_pause():
    state, _ = reserve(record(), action())
    state = reconcile(state, observed(status="pending", settled=None))
    state["pause_code"] = "subscription_quota_paused"
    unchanged, decision = reserve(state, {"kind": "poll", "intent_id": "intent-1"})
    assert decision == {"decision": "poll_existing", "job_ref": "task:intent-1", "new_spend": "0"}
    assert unchanged == state
    with pytest.raises(Pause, match="subscription_quota_paused"):
        reserve(state, action("later", segment="E1U02"))
    with pytest.raises(Pause, match="Explicit resume"):
        resume(state, {"quota_available": True})
    cleared = resume(
        state, {"quota_available": True, "quota_state_ref": "official:available", "user_evidence_ref": "chat:resume"}
    )
    assert "pause_code" not in cleared
    assert cleared["intents"] == state["intents"]


def test_quality_generation_cap_is_initial_plus_two_and_requires_review():
    state = record()
    state["approval"]["round_limit"] = "100"
    state["approval"]["per_video"]["sample"] = "100"
    for number in range(1, 4):
        kind = "initial" if number == 1 else "quality_regeneration"
        state, decision = reserve(state, action(str(number), kind))
        assert decision["quality_attempt"] == number
        state = reconcile(state, observed(str(number), review="rejected", review_ref=f"review:{number}"))
    with pytest.raises(Pause, match="two quality regenerations exhausted"):
        reserve(state, action("fourth", "quality_regeneration"))
    assert len(state["intents"]) == 3
    assert commitment(state) == 9


def test_accepted_result_cannot_be_regenerated_under_quality_retry_allowance():
    state, _ = reserve(record(), action())
    state = reconcile(state, observed(review="accepted", review_ref="review:accepted"))
    with pytest.raises(Pause, match="rejected segment"):
        reserve(state, action("retry", "quality_regeneration"))


def test_three_rounds_require_separate_approval_and_matching_currency():
    state = record()
    wrong = action()
    wrong["currency"] = "BRL"
    with pytest.raises(Pause, match="currencies differ"):
        reserve(state, wrong)
    for phase in ["pilot-11", "continuity-12"]:
        separate = copy.deepcopy(state)
        separate["approval"]["round"] = phase
        if phase == "continuity-12":
            separate["approval"]["per_video"]["second"] = "5"
        with pytest.raises(Pause, match="prerequisite completion"):
            reserve(separate, action())
        separate["approval"]["prerequisite_evidence_ref"] = "github:closed-prerequisite"
        assert decide(separate, action())["decision"] == "reserve_before_delegating"


def test_reconciliation_cannot_rewrite_counters_or_release_unsettled_spend():
    state, _ = reserve(record(), action(maximum="6"))
    with pytest.raises(Pause, match="quality counter"):
        reconcile(state, observed(quality_attempt=0))
    state = reconcile(state, observed(settled=None))
    assert commitment(state) == 6
    assert state["intents"][0]["quality_attempt"] == 1


def test_transport_failure_keeps_existing_recoverable_provider_work_from_resubmission():
    state, _ = reserve(record(), action())
    state = reconcile(state, observed(status="failed"))
    with pytest.raises(Pause, match="recoverable provider work"):
        reserve(state, action("transport", "transport_retry"))


def test_video_ceiling_is_enforced_independently_of_larger_round_allowance():
    state = record()
    state["approval"]["round_limit"] = "20"
    state["approval"]["per_video"]["sample"] = "2"
    with pytest.raises(Pause, match="allowance exhausted"):
        reserve(state, action(maximum="3"))
    assert state["intents"] == []


def test_new_provider_state_requires_fresh_resubmission_safety_evidence():
    state, _ = reserve(record(), action())
    state = reconcile(state, observed(status="failed", resubmission_safe=True))
    assert decide(state, action("transport", "transport_retry"))["decision"] == "reserve_before_delegating"
    state = reconcile(state, observed(status="pending", settled=None))
    state = reconcile(state, observed(status="failed", settled=None))
    with pytest.raises(Pause, match="recoverable provider work"):
        reserve(state, action("transport", "transport_retry"))
    assert len(state["intents"]) == 1


def evaluation_record():
    return {
        "approval": {
            "round": "evaluation-10",
            "currency": "USD",
            "round_limit": "0.25",
            "model": "gemini-3.8-flash",
            "max_calls": 6,
            "allow_retries": False,
            "per_video": {key: str(value) for key, value in _POLICY["EVALUATION_ARTIFACT_LIMITS"].items()},
            "user_evidence_ref": "chat:explicit-six-evaluation-approval",
            "quote_refs": ["quote:unit"],
        },
        "intents": [],
    }


def evaluation_action(artifact="h3-native-audio-sample", **changes):
    candidate = action(identifier=artifact, maximum=evaluation_record()["approval"]["per_video"][artifact])
    return {**candidate, "video_id": artifact, **changes}


def test_evaluation_round_admits_exact_six_targets_once_and_reuses_receipts():
    state = evaluation_record()
    for artifact in state["approval"]["per_video"]:
        candidate = evaluation_action(artifact)
        state, decision = reserve(state, candidate)
        assert decision["decision"] == "reserve_before_delegating"
        assert decide(state, candidate)["decision"] == "reconcile_existing"
        state = reconcile(state, observed(artifact, settled=candidate["maximum"]))
        assert decide(state, candidate)["decision"] == "reuse_complete"
    assert len(state["intents"]) == 6
    assert commitment(state) == _POLICY["Decimal"]("0.24")
    with pytest.raises(Pause, match="one request per approved artifact"):
        reserve(state, evaluation_action(intent_id="seventh", client_key="seventh", segment_id="changed"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("round_limit", "0.26"),
        ("currency", "EUR"),
        ("model", "another-model"),
        ("max_calls", 7),
        ("allow_retries", True),
    ],
)
def test_evaluation_scope_cannot_expand_or_substitute_model(field, value):
    state = evaluation_record()
    state["approval"][field] = value
    with pytest.raises(Pause, match="exact six targets"):
        reserve(state, evaluation_action())
    assert state["intents"] == []


@pytest.mark.parametrize("change", ["missing", "extra", "raised_cap"])
def test_evaluation_artifact_set_and_per_artifact_caps_are_fixed(change):
    state = evaluation_record()
    if change == "missing":
        state["approval"]["per_video"].pop("known-good-av")
    elif change == "extra":
        state["approval"]["per_video"]["extra"] = "0.01"
    else:
        state["approval"]["per_video"]["known-good-av"] = "0.07"
    with pytest.raises(Pause, match="exact six targets"):
        reserve(state, evaluation_action())
    assert state["intents"] == []


@pytest.mark.parametrize("status", ["complete", "failed", "not_submitted"])
def test_evaluation_never_retries_an_artifact_after_zero_settlement_or_changed_segment(status):
    candidate = evaluation_action()
    state, _ = reserve(evaluation_record(), candidate)
    state = reconcile(
        state,
        observed(
            candidate["intent_id"], status=status, settled="0", non_submission_evidence_ref="verified:not-submitted"
        ),
    )
    with pytest.raises(Pause, match="one request per approved artifact"):
        reserve(state, evaluation_action(intent_id="new", client_key="new", segment_id="different"))
    assert len(state["intents"]) == 1


def test_evaluation_pending_reservation_and_per_artifact_limit_stop_independent_dispatch():
    state, _ = reserve(evaluation_record(), evaluation_action())
    with pytest.raises(Pause, match="pending"):
        reserve(state, evaluation_action("known-good-av"))
    assert commitment(state) == _POLICY["Decimal"]("0.04")
    with pytest.raises(Pause, match="allowance exhausted"):
        reserve(evaluation_record(), evaluation_action(maximum="0.04001"))
