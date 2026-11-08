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


def diagnostic_record():
    state = evaluation_record()
    state["approval"].update(
        round="diagnostic-10",
        round_limit="0.04",
        max_calls=4,
        per_video={key: str(value) for key, value in _POLICY["DIAGNOSTIC_CASE_LIMITS"].items()},
        user_evidence_ref="chat:explicit-four-case-diagnostic-approval",
    )
    return state


def diagnostic_action(case="case-a", **changes):
    candidate = action(identifier=case, maximum="0.01")
    return {**candidate, "video_id": case, **changes}


def test_diagnostic_reserves_four_fixed_cases_once_and_reuses_existing_receipts():
    state = diagnostic_record()
    for case in ("case-a", "case-b", "case-c", "case-d"):
        candidate = diagnostic_action(case)
        state, decision = reserve(state, candidate)
        assert decision["decision"] == "reserve_before_delegating"
        assert decide(state, candidate)["decision"] == "reconcile_existing"
        state = reconcile(state, observed(case, settled="0.01"))
        assert decide(state, candidate)["decision"] == "reuse_complete"
    assert len(state["intents"]) == 4
    assert commitment(state) == _POLICY["Decimal"]("0.04")
    with pytest.raises(Pause, match="one request per approved artifact"):
        reserve(state, diagnostic_action(intent_id="fifth", client_key="fifth", segment_id="different"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("round_limit", "0.05"),
        ("currency", "BRL"),
        ("model", "another-model"),
        ("max_calls", 5),
        ("allow_retries", True),
        ("per_video", {"case-a": "0.01", "case-b": "0.01", "case-c": "0.01"}),
        ("per_video", {"case-a": "0.02", "case-b": "0.01", "case-c": "0.01", "case-d": "0.01"}),
        ("per_video", {"case-a": "0.01", "case-b": "0.01", "case-c": "0.01", "extra": "0.01"}),
    ],
)
def test_diagnostic_approval_cannot_change_fixed_scope_model_or_limits(field, value):
    state = diagnostic_record()
    state["approval"][field] = value
    with pytest.raises(Pause, match="exact four cases"):
        reserve(state, diagnostic_action())
    assert state["intents"] == []


@pytest.mark.parametrize("status", ["complete", "failed", "not_submitted"])
def test_diagnostic_case_cannot_be_retried_after_zero_settlement_or_changed_segment(status):
    state, _ = reserve(diagnostic_record(), diagnostic_action())
    state = reconcile(
        state,
        observed("case-a", status=status, settled="0", non_submission_evidence_ref="verified:not-submitted"),
    )
    with pytest.raises(Pause, match="one request per approved artifact"):
        reserve(state, diagnostic_action(intent_id="replacement", client_key="replacement", segment_id="changed"))
    assert len(state["intents"]) == 1


@pytest.mark.parametrize("kind", ["quality_regeneration", "transport_retry"])
def test_diagnostic_does_not_admit_quality_or_transport_attempts(kind):
    with pytest.raises(Pause, match="without retries"):
        reserve(diagnostic_record(), diagnostic_action(kind=kind))


def test_diagnostic_unknown_outcome_keeps_reservation_and_blocks_next_case():
    state, _ = reserve(diagnostic_record(), diagnostic_action())
    state = reconcile(state, observed("case-a", status="pending", settled=None))
    assert commitment(state) == _POLICY["Decimal"]("0.01")
    with pytest.raises(Pause, match="pending"):
        reserve(state, diagnostic_action("case-b"))
    with pytest.raises(Pause, match="allowance exhausted"):
        reserve(diagnostic_record(), diagnostic_action(maximum="0.01001"))
    with pytest.raises(Pause, match="outside the explicitly approved round"):
        reserve(diagnostic_record(), evaluation_action())


def pro_comparison_record():
    state = evaluation_record()
    state["approval"].update(
        round="pro-comparison-10",
        round_limit="0.17",
        model="gemini-3.1-pro-preview",
        max_calls=3,
        per_video={"pro-wrong-speech": "0.03", "pro-silence": "0.03", "pro-h3": "0.11"},
        user_evidence_ref="chat:explicit-three-case-pro-comparison-approval",
    )
    return state


def pro_comparison_action(case="pro-wrong-speech", **changes):
    candidate = action(identifier=case, maximum="0.11" if case == "pro-h3" else "0.03")
    return {**candidate, "video_id": case, **changes}


def test_pro_comparison_reserves_distinct_case_caps_and_closes_without_replacement():
    state = pro_comparison_record()
    for case, cost in [("pro-wrong-speech", "0.03"), ("pro-silence", "0.03"), ("pro-h3", "0.11")]:
        candidate = pro_comparison_action(case)
        state, decision = reserve(state, candidate)
        assert decision["decision"] == "reserve_before_delegating"
        assert decide(state, candidate)["decision"] == "reconcile_existing"
        state = reconcile(state, observed(case, settled=cost))
        assert decide(state, candidate)["decision"] == "reuse_complete"
    assert commitment(state) == _POLICY["Decimal"]("0.17")
    with pytest.raises(Pause, match="one request per approved artifact"):
        reserve(state, pro_comparison_action(intent_id="fourth", client_key="fourth", segment_id="changed"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "gemini-3.8-flash"),
        ("round_limit", "0.18"),
        ("currency", "BRL"),
        ("max_calls", 4),
        ("allow_retries", True),
        ("per_video", {"pro-wrong-speech": "0.11", "pro-silence": "0.03", "pro-h3": "0.03"}),
    ],
)
def test_pro_comparison_rejects_model_or_scope_changes(field, value):
    state = pro_comparison_record()
    state["approval"][field] = value
    with pytest.raises(Pause, match="exact three cases"):
        reserve(state, pro_comparison_action())
    assert state["intents"] == []


def test_pro_comparison_pending_and_zero_settlement_do_not_authorize_retry():
    state, _ = reserve(pro_comparison_record(), pro_comparison_action())
    with pytest.raises(Pause, match="pending"):
        reserve(state, pro_comparison_action("pro-h3"))
    state = reconcile(state, observed("pro-wrong-speech", status="failed", settled="0"))
    with pytest.raises(Pause, match="without retries"):
        reserve(state, pro_comparison_action(intent_id="retry", client_key="retry", kind="transport_retry"))
    with pytest.raises(Pause, match="allowance exhausted"):
        reserve(pro_comparison_record(), pro_comparison_action(maximum="0.03001"))
    with pytest.raises(Pause, match="outside the explicitly approved round"):
        reserve(pro_comparison_record(), diagnostic_action())


def image_fixture_record():
    state = record()
    state["approval"].update(
        round="image-fixture-6",
        round_limit="2.04",
        per_video={"character/Ana": "2.04"},
        model="gemini-3.1-flash-image",
        provider="gemini-aistudio",
        resolution="1K",
        aspect_ratio="16:9",
        max_calls=1,
        allow_retries=False,
    )
    return state


def image_fixture_action(**changes):
    return {**action(maximum="2.031616"), "video_id": "character/Ana", **changes}


@pytest.mark.parametrize("status", ["complete", "failed", "not_submitted"])
def test_image_fixture_allows_one_reserved_image_and_never_replacement(status):
    candidate = image_fixture_action()
    state, decision = reserve(image_fixture_record(), candidate)
    assert decision["decision"] == "reserve_before_delegating"
    assert commitment(state) == _POLICY["Decimal"]("2.031616")
    assert decide(state, candidate)["decision"] == "reconcile_existing"
    state = reconcile(state, observed(status=status, settled="0", non_submission_evidence_ref="verified:no-submission"))
    for kind in ("initial", "quality_regeneration", "transport_retry"):
        with pytest.raises(Pause, match="without retries"):
            reserve(state, image_fixture_action(intent_id="other", client_key="other", segment_id="changed", kind=kind))
    assert len(state["intents"]) == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "different-model"),
        ("provider", "different-provider"),
        ("resolution", "2K"),
        ("aspect_ratio", "1:1"),
        ("round_limit", "2.05"),
        ("currency", "BRL"),
        ("max_calls", 2),
        ("allow_retries", True),
        ("per_video", {"character/Other": "2.04"}),
    ],
)
def test_image_fixture_rejects_scope_changes(field, value):
    state = image_fixture_record()
    state["approval"][field] = value
    with pytest.raises(Pause, match="exact Ana target"):
        reserve(state, image_fixture_action())
    assert state["intents"] == []


def test_image_fixture_unknown_outcome_preserves_reservation_and_ceiling():
    state, _ = reserve(image_fixture_record(), image_fixture_action())
    state = reconcile(state, observed(status="failed", settled=None))
    assert commitment(state) == _POLICY["Decimal"]("2.031616")
    with pytest.raises(Pause, match="without retries"):
        reserve(state, image_fixture_action(intent_id="replacement", client_key="replacement"))
    with pytest.raises(Pause, match="allowance exhausted"):
        reserve(image_fixture_record(), image_fixture_action(maximum="2.040001"))
    with pytest.raises(Pause, match="outside the explicitly approved round"):
        reserve(image_fixture_record(), image_fixture_action(video_id="storyboard/E1S01"))


def image_quality_record():
    state = image_fixture_record()
    state["approval"].update(
        round="image-quality-6", reference_count=0, user_evidence_ref="chat:separate-one-quality-attempt-approval"
    )
    state.update(
        project_ref="image-handoff-fixture-6-20261108",
        frozen_prompt_sha256=_POLICY["ANA_QUALITY_PROMPT_SHA256"],
        prior_quality_attempt={
            "round": "image-fixture-6",
            "record_closed": True,
            "record_ref": "private:closed-initial-record",
            "record_sha256": "a" * 64,
            "video_id": "character/Ana",
            "segment_id": "character/Ana",
            "status": "complete",
            "review": "rejected",
            "discarded": True,
            "quality_attempt": 1,
            "currency": "USD",
            "settled_amount": "0.0679845",
            "job_ref": "task:initial",
            "usage_ref": "ledger:initial",
            "state_evidence_ref": "state:initial",
            "review_ref": "owner:rejected",
        },
    )
    return state


def image_quality_action(**changes):
    return image_fixture_action(**{"kind": "quality_regeneration", "segment_id": "character/Ana", **changes})


def test_new_image_quality_round_counts_attempt_two_without_rebilling_closed_history():
    original = image_quality_record()
    unchanged = copy.deepcopy(original)
    state, decision = reserve(original, image_quality_action())
    assert original == unchanged
    assert decision["quality_attempt"] == 2
    assert decision["round_commitment"] == "2.031616"
    assert state["intents"][0]["quality_attempt"] == 2
    assert state["prior_quality_attempt"] == original["prior_quality_attempt"]
    assert commitment(state) == _POLICY["Decimal"]("2.031616")
    assert decide(state, image_quality_action())["decision"] == "reconcile_existing"
    state = reconcile(state, observed(settled="0.07", review="rejected", review_ref="review:new"))
    assert commitment(state) == _POLICY["Decimal"]("0.07")
    assert decide(state, image_quality_action())["decision"] == "reuse_complete"
    assert state["prior_quality_attempt"]["settled_amount"] == "0.0679845"


@pytest.mark.parametrize("status", ["complete", "failed", "not_submitted"])
def test_new_image_quality_round_never_authorizes_replacement_after_any_settlement(status):
    state, _ = reserve(image_quality_record(), image_quality_action())
    state = reconcile(state, observed(status=status, settled="0", non_submission_evidence_ref="verified:not-sent"))
    for kind in ("initial", "quality_regeneration", "transport_retry"):
        with pytest.raises(Pause, match="no replacement or retries"):
            reserve(state, image_quality_action(intent_id="other", client_key="other", kind=kind))
    assert len(state["intents"]) == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "pending"),
        ("review", "accepted"),
        ("discarded", False),
        ("record_closed", False),
        ("quality_attempt", 2),
        ("record_sha256", "not-a-digest"),
        ("review_ref", ""),
        ("settled_amount", "0"),
        ("video_id", "character/Other"),
        ("record_ref", None),
    ],
)
def test_new_image_quality_round_requires_closed_rejected_initial_usage_evidence(field, value):
    state = image_quality_record()
    state["prior_quality_attempt"][field] = value
    with pytest.raises(Pause):
        reserve(state, image_quality_action())
    assert state["intents"] == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "different-model"),
        ("provider", "other-provider"),
        ("resolution", "2K"),
        ("aspect_ratio", "1:1"),
        ("reference_count", 1),
        ("round_limit", "2.05"),
        ("max_calls", 2),
        ("allow_retries", True),
        ("per_video", {"character/Other": "2.04"}),
    ],
)
def test_new_image_quality_round_rejects_scope_expansion(field, value):
    state = image_quality_record()
    state["approval"][field] = value
    with pytest.raises(Pause, match="exact Ana project"):
        reserve(state, image_quality_action())
    assert state["intents"] == []


def test_new_image_quality_round_binds_project_prompt_shape_and_full_request_reservation():
    for field in ("frozen_prompt_sha256", "project_ref"):
        state = image_quality_record()
        state[field] = "changed"
        with pytest.raises(Pause, match="exact Ana project"):
            reserve(state, image_quality_action())
    for changes in ({"maximum": "0.01"}, {"segment_id": "other"}, {"kind": "initial"}):
        with pytest.raises(Pause, match="exact bound"):
            reserve(image_quality_record(), image_quality_action(**changes))
    state, _ = reserve(image_quality_record(), image_quality_action())
    state = reconcile(state, observed(status="failed", settled=None))
    assert commitment(state) == _POLICY["Decimal"]("2.031616")
    with pytest.raises(Pause, match="no replacement or retries"):
        reserve(state, image_quality_action(intent_id="replacement", client_key="replacement"))
