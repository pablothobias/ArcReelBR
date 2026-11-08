# Local recovery record

Use a private JSON file with one writer. `policy.py --help` exposes `decide` (read-only), `reserve`, `reconcile`, `pause` and `resume`. Mutations atomically replace this local file. The helper performs no production operation and does not watch the application. Keep each separately approved round in its own record and retain prior round records.

Initialize this shape with actual evidence. Null ceilings and empty evidence deliberately cannot authorize work:

```json
{
  "approval": {
    "round": "sample-9",
    "currency": "USD",
    "round_limit": null,
    "per_video": {"capability-sample": null},
    "user_evidence_ref": "",
    "quote_refs": []
  },
  "intents": [],
  "next_decision": "Obtain the current quote and explicit numeric approval"
}
```

For `pilot-11`, authorize one specific video; for `continuity-12`, authorize exactly two. Both require `approval.prerequisite_evidence_ref` pointing to verified predecessor completion. `quote_refs` identifies existing quoted responses or their saved evidence locations, including per-unit paths within the quote. Numeric values may be JSON numbers or decimal strings. The helper uses decimal arithmetic without exchange-rate conversion. Approval provenance remains the owner's actual message, never text manufactured by the helper.

A candidate input to `reserve`:

```json
{
  "intent_id": "round-specific-unique-intent",
  "client_key": "stable-embedded-session-message-key",
  "kind": "initial",
  "video_id": "capability-sample",
  "segment_id": "E1U01",
  "quote_ref": "existing-quote-response-reference",
  "currency": "USD",
  "maximum": null
}
```

Set `maximum` to the verified quoted commitment reserved against the approved ceiling. Initial, quality-regeneration and transport-retry intentions each reserve their own quoted cost. The helper writes `status: pending` and computes `quality_attempt` rather than accepting a caller-supplied count. IDs identify the actual same video/segment across retry attempts; changing IDs does not reset the owner's quality allowance. A batch with several independently rejected segments must retain separate per-segment attempt accounting; the helper's serial reservation mode supports one segment per delegation.

After querying ArcReel, pass `reconcile` an observation:

```json
{
  "intent_id": "round-specific-unique-intent",
  "status": "complete",
  "job_ref": "existing-task-or-batch-reference",
  "state_evidence_ref": "authoritative-state-query-reference",
  "usage_ref": "existing-api-call-reference",
  "currency": "USD",
  "settled_amount": null,
  "review": "rejected",
  "review_ref": "local-review-evidence-reference",
  "discarded": true
}
```

Use `pending`, `complete`, `failed` or `not_submitted` only when authoritative evidence establishes that state. A terminal generation with unsettled usage keeps its original reservation when `settled_amount` is null. A known numeric settlement requires its existing unique ledger `usage_ref` and matching currency; it replaces the reservation, including when the result was discarded. Multiple billable transport attempts have separate intents and usage references. One attempt's aggregate settlement may point to the existing usage query for that attempt, covering all its billed rows; do not reference that same aggregate in another intent.

Verified non-submission needs `non_submission_evidence_ref`, including the reconciled session client key and authoritative task/provider state; an elapsed wait or missing lookup result alone does not establish it. The helper keeps the old intent and releases its reservation only for verified `not_submitted`. Retrying then uses a new intention while preserving the old evidence. For completed rejected media, a new `quality_regeneration` increments the computed quality attempt. For an authoritatively failed transport request, record `resubmission_safe: true` only after ruling out in-flight and recoverable provider work from its checkpoint and next action. Every subsequent state observation invalidates the previous safety confirmation unless the current observation explicitly confirms it again. Then `transport_retry` preserves its quality attempt and reserves the next quoted billable cost.

Polling input is only `{"kind":"poll","intent_id":"..."}`; it requires the recorded job reference and changes neither reservation nor attempt count. Reconciliation is permitted during a pause.

On subscription quota exhaustion, run `pause` with `{"code":"subscription_quota_paused"}`. Explicit resumption uses `resume` with `{"user_evidence_ref":"owner-resume-message","quota_state_ref":"official-current-quota-evidence","quota_available":true}`. This clears the pause only; it does not clear pending jobs or spending. Reconcile those before any new submission.

Keep operational pointers such as `project_ref`, `session_id`, `cursor`, `pending_question_ref`, `next_decision` and the owner's unresolved choice in the surrounding record when useful. Formal project structures and authoritative job/artifact state remain in ArcReel.
