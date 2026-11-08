"""Local directing-policy arithmetic and recovery transitions; never submits work."""

from __future__ import annotations

import argparse
import copy
import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

# This separately approved review round has a fixed six-artifact scope.
EVALUATION_MODEL = "gemini-3.8-flash"
EVALUATION_ARTIFACT_LIMITS = {
    "h3-native-audio-sample": Decimal("0.04"),
    "known-good-av": Decimal("0.06"),
    "subtitle-delayed-av": Decimal("0.06"),
    "identity-story-error-av": Decimal("0.06"),
    "wrong-speech-audio": Decimal("0.01"),
    "missing-speech-audio": Decimal("0.01"),
}
DIAGNOSTIC_CASE_LIMITS = dict.fromkeys(("case-a", "case-b", "case-c", "case-d"), Decimal("0.01"))
PRO_COMPARISON_MODEL = "gemini-3.1-pro-preview"
PRO_COMPARISON_LIMITS = {
    "pro-wrong-speech": Decimal("0.03"),
    "pro-silence": Decimal("0.03"),
    "pro-h3": Decimal("0.11"),
}


class Pause(ValueError):
    """A directing decision requires evidence or explicit owner approval."""


def amount(value: Any) -> Decimal:
    if value is None or isinstance(value, bool):
        raise Pause("Unknown price or allowance: obtain a numeric quote and approval")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise Pause("Amount must be a finite nonnegative number") from exc
    if not result.is_finite() or result < 0:
        raise Pause("Amount must be a finite nonnegative number")
    return result


def approval(record: dict) -> dict:
    approved = record["approval"]
    if not approved.get("user_evidence_ref") or not approved.get("quote_refs"):
        raise Pause("Explicit owner approval and existing quote references are required")
    if approved.get("round") == "evaluation-10":
        if (
            approved.get("currency") != "USD"
            or amount(approved.get("round_limit")) != Decimal("0.25")
            or approved.get("model") != EVALUATION_MODEL
            or approved.get("max_calls") != 6
            or approved.get("allow_retries") is not False
            or set(approved.get("per_video", {})) != set(EVALUATION_ARTIFACT_LIMITS)
            or any(amount(approved["per_video"][key]) != limit for key, limit in EVALUATION_ARTIFACT_LIMITS.items())
        ):
            raise Pause("Evaluation approval must retain the exact six targets, model, USD ceilings and no-retry scope")
        return approved
    if approved.get("round") == "diagnostic-10":
        if (
            approved.get("currency") != "USD"
            or amount(approved.get("round_limit")) != Decimal("0.04")
            or approved.get("model") != EVALUATION_MODEL
            or approved.get("max_calls") != 4
            or approved.get("allow_retries") is not False
            or set(approved.get("per_video", {})) != set(DIAGNOSTIC_CASE_LIMITS)
            or any(amount(approved["per_video"][key]) != limit for key, limit in DIAGNOSTIC_CASE_LIMITS.items())
        ):
            raise Pause("Diagnostic approval must retain the exact four cases, model, USD ceilings and no-retry scope")
        return approved
    if approved.get("round") == "pro-comparison-10":
        if (
            approved.get("currency") != "USD"
            or amount(approved.get("round_limit")) != Decimal("0.17")
            or approved.get("model") != PRO_COMPARISON_MODEL
            or approved.get("max_calls") != 3
            or approved.get("allow_retries") is not False
            or set(approved.get("per_video", {})) != set(PRO_COMPARISON_LIMITS)
            or any(amount(approved["per_video"][key]) != limit for key, limit in PRO_COMPARISON_LIMITS.items())
        ):
            raise Pause("Pro comparison approval must retain the exact three cases, model, USD ceilings and no-retry scope")
        return approved
    if approved.get("round") == "image-fixture-6":
        if (
            approved.get("currency") != "USD"
            or amount(approved.get("round_limit")) != Decimal("2.04")
            or approved.get("model") != "gemini-3.1-flash-image"
            or approved.get("provider") != "gemini-aistudio"
            or approved.get("resolution") != "1K"
            or approved.get("aspect_ratio") != "16:9"
            or approved.get("max_calls") != 1
            or approved.get("allow_retries") is not False
            or set(approved.get("per_video", {})) != {"character/Ana"}
            or amount(approved["per_video"]["character/Ana"]) != Decimal("2.04")
        ):
            raise Pause("Image fixture approval must retain the exact Ana target, model, shape and USD ceilings")
        return approved
    if approved.get("round") not in {"sample-9", "pilot-11", "continuity-12"}:
        raise Pause("Choose a separately approved sample, pilot or continuity round")
    videos = approved["per_video"]
    required = 2 if approved["round"] == "continuity-12" else 1
    if len(videos) != required:
        raise Pause("Round scope must be one sample, one pilot, or two continuity videos")
    if approved["round"] != "sample-9" and not approved.get("prerequisite_evidence_ref"):
        raise Pause("Verify prerequisite completion before this production round")
    if not approved.get("currency"):
        raise Pause("Explicit approval currency is required")
    amount(approved["round_limit"])
    for value in videos.values():
        amount(value)
    return approved


def commitment(record: dict, video_id: str | None = None) -> Decimal:
    """Sum authoritative settlement snapshots or outstanding quote reservations once per intent."""
    total = Decimal(0)
    for intent in record.get("intents", []):
        if video_id is not None and intent["video_id"] != video_id:
            continue
        if intent["status"] == "not_submitted":
            continue
        settled = intent.get("settled_amount")
        total += amount(intent["maximum"] if settled is None else settled)
    return total


def decide(record: dict, action: dict) -> dict:
    """Authorize a bounded intention only; application state remains authoritative."""
    intents = record.get("intents", [])
    if action["kind"] == "poll":
        existing = next((item for item in intents if item["intent_id"] == action["intent_id"]), None)
        if not existing or not existing.get("job_ref"):
            raise Pause("Reconcile the pending intent with authoritative jobs before polling")
        return {"decision": "poll_existing", "job_ref": existing["job_ref"], "new_spend": "0"}
    if record.get("pause_code"):
        raise Pause(f"{record['pause_code']}: preserve state and resume explicitly; no paid fallback")
    allowed = {"intent_id", "client_key", "kind", "video_id", "segment_id", "quote_ref", "currency", "maximum"}
    if action.keys() - allowed:
        raise Pause("A new intent cannot carry settlement, review or attempt-counter overrides")
    approved = approval(record)
    existing = next((item for item in intents if item["intent_id"] == action["intent_id"]), None)
    if existing is not None:
        return {
            "decision": "reuse_complete" if existing["status"] == "complete" else "reconcile_existing",
            "intent_id": existing["intent_id"],
            "job_ref": existing.get("job_ref"),
            "new_spend": "0",
        }
    video_id = action["video_id"]
    if video_id not in approved["per_video"]:
        raise Pause("This video is outside the explicitly approved round")
    if action.get("currency") != approved["currency"]:
        raise Pause("Quote and allowance currencies differ; obtain explicit matching approval")
    if action.get("quote_ref") not in approved["quote_refs"] or not action.get("client_key"):
        raise Pause("Retain the current ArcReel quote reference and stable session client key")
    if any(item.get("client_key") == action["client_key"] for item in intents):
        raise Pause("A session client key already belongs to another intent; reconcile that intent")
    maximum = amount(action.get("maximum"))
    # Any unresolved submission in the round may already be charged or producing media.
    if any(item["status"] == "pending" for item in intents):
        raise Pause("Reconcile all pending jobs before authorizing another submission")
    if approved["round"] in {"evaluation-10", "diagnostic-10", "pro-comparison-10", "image-fixture-6"} and (
        action["kind"] != "initial"
        or len(intents) >= approved["max_calls"]
        or any(item["video_id"] == video_id for item in intents)
    ):
        raise Pause(f"Review permits one request per approved artifact, {approved['max_calls']} total, without retries")
    history = [
        item
        for item in intents
        if item["video_id"] == video_id
        and item["segment_id"] == action["segment_id"]
        and item["status"] != "not_submitted"
    ]
    latest = history[-1] if history else None
    kind = action["kind"]
    if kind == "initial":
        if history:
            raise Pause("This segment already has an initial generation; reconcile or review it")
        attempt = 1
    elif kind == "quality_regeneration":
        if (
            latest is None
            or latest["status"] != "complete"
            or latest.get("review") != "rejected"
            or not latest.get("review_ref")
        ):
            raise Pause("Quality regeneration requires a completed rejected segment and review evidence")
        attempt = latest["quality_attempt"] + 1
        if attempt > 3:
            raise Pause("Initial generation plus two quality regenerations exhausted")
    elif kind == "transport_retry":
        if (
            latest is None
            or latest["status"] != "failed"
            or not latest.get("state_evidence_ref")
            or latest.get("resubmission_safe") is not True
        ):
            raise Pause(
                "Reconcile authoritative failure and rule out in-flight or recoverable provider work before resubmission"
            )
        attempt = latest["quality_attempt"]
    else:
        raise Pause("Use initial, quality_regeneration, transport_retry or poll")
    round_total = commitment(record) + maximum
    video_total = commitment(record, video_id) + maximum
    if round_total > amount(approved["round_limit"]) or video_total > amount(approved["per_video"][video_id]):
        raise Pause("Approved allowance exhausted, including pending, discarded and transport spend")
    return {
        "decision": "reserve_before_delegating",
        "quality_attempt": attempt,
        "round_commitment": str(round_total),
        "video_commitment": str(video_total),
    }


def reserve(record: dict, action: dict) -> tuple[dict, dict]:
    decision = decide(record, action)
    updated = copy.deepcopy(record)
    if decision["decision"] == "reserve_before_delegating":
        updated.setdefault("intents", []).append(
            {
                **action,
                "status": "pending",
                "quality_attempt": decision["quality_attempt"],
            }
        )
    return updated, decision


def reconcile(record: dict, observation: dict) -> dict:
    """Record references to queried application state, never infer failure from elapsed time."""
    if not observation.get("state_evidence_ref"):
        raise Pause("Authoritative job/session state evidence is required")
    updated = copy.deepcopy(record)
    intent = next(item for item in updated["intents"] if item["intent_id"] == observation["intent_id"])
    status = observation["status"]
    if status not in {"pending", "complete", "failed", "not_submitted"}:
        raise Pause("Unknown job outcome must remain pending")
    if status == "not_submitted" and (
        amount(intent.get("settled_amount") or 0) > 0 or amount(observation.get("settled_amount") or 0) > 0
    ):
        raise Pause("Known charged work cannot be erased as not submitted")
    if status == "not_submitted" and not observation.get("non_submission_evidence_ref"):
        raise Pause(
            "Absence or timeout is insufficient: verify the session client key and authoritative non-submission"
        )
    if status != "not_submitted" and not observation.get("job_ref"):
        raise Pause("Keep an existing application job or batch reference")
    settled = observation.get("settled_amount")
    if settled is not None:
        amount(settled)
        if not observation.get("usage_ref") or observation.get("currency") != updated["approval"]["currency"]:
            raise Pause("Settled amounts require existing usage evidence in the approved currency")
    if observation.get("review") and (status != "complete" or not observation.get("review_ref")):
        raise Pause("A review decision requires completed media and an evidence reference")
    if observation.get("review") not in {None, "accepted", "rejected"}:
        raise Pause("Review is accepted or rejected; discarded work retains its usage")
    if intent["status"] == "complete" and status != "complete":
        raise Pause("Completed jobs are reused; a new generation needs its own reviewed intent")
    if observation.get("usage_ref") and any(
        item["intent_id"] != intent["intent_id"] and item.get("usage_ref") == observation["usage_ref"]
        for item in updated["intents"]
    ):
        raise Pause("This usage entry is already reconciled; reconcile duplicate intent ownership")
    allowed = {
        "status",
        "job_ref",
        "state_evidence_ref",
        "non_submission_evidence_ref",
        "settled_amount",
        "usage_ref",
        "currency",
        "review",
        "review_ref",
        "discarded",
        "resubmission_safe",
    }
    if observation.keys() - allowed - {"intent_id"}:
        raise Pause("Reconciliation cannot change the approved intent or its quality counter")
    intent.pop("resubmission_safe", None)
    intent.update(observation)
    return updated


def resume(record: dict, evidence: dict) -> dict:
    if (
        not evidence.get("user_evidence_ref")
        or not evidence.get("quota_state_ref")
        or evidence.get("quota_available") is not True
    ):
        raise Pause("Explicit resume and verified available subscription quota are required")
    updated = copy.deepcopy(record)
    updated.pop("pause_code", None)
    updated["resume_evidence"] = evidence
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["decide", "reserve", "reconcile", "pause", "resume"])
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.record.read_text())
    data = json.loads(args.input.read_text())
    try:
        decision = None
        if args.command == "decide":
            print(json.dumps(decide(record, data)))
            return 0
        if args.command == "reserve":
            updated, decision = reserve(record, data)
        elif args.command == "reconcile":
            updated = reconcile(record, data)
        elif args.command == "pause":
            updated = {**record, "pause_code": data["code"]}
        else:
            updated = resume(record, data)
        temporary = args.record.with_suffix(args.record.suffix + ".tmp")
        temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, args.record)
        print(json.dumps(decision or {"decision": "record_updated"}))
        return 0
    except (Pause, KeyError, StopIteration) as exc:
        print(json.dumps({"decision": "pause", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
