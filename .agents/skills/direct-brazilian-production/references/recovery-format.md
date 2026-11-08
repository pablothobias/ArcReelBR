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

## Separately approved audiovisual evaluation

`evaluation-10` is a fixed six-artifact review allowance, independent of production generation rounds. Set `currency` to `USD`, `round_limit` to `0.25`, `model` to `gemini-3.8-flash`, `max_calls` to `6`, and `allow_retries` to `false`. Its compatibility field `per_video` identifies the approved review artifacts: `h3-native-audio-sample: 0.04`, `known-good-av: 0.06`, `subtitle-delayed-av: 0.06`, `identity-story-error-av: 0.06`, `wrong-speech-audio: 0.01`, `missing-speech-audio: 0.01`. Retain the actual separate owner approval and quote references.

Use one initial intention per artifact and reconcile its actual provider response/usage before the next call. Changing segment IDs, a zero settlement, failed requests and verified non-submission do not authorize another request for the same artifact. An existing intent returns its recovery decision rather than another submission. This scope authorizes no media generation, replacement model, extra evaluation or automatic retry. The helper controls only the Codex directing record; the bounded SDK caller must independently verify exact input-token admission caps, output limit, actual media identity and provider/account configuration.

## Separately approved four-case diagnostic

`diagnostic-10` is a new, separate record for the approved frozen four-cell diagnostic. Set `currency` to `USD`, `round_limit` to `0.04`, `model` to `gemini-3.8-flash`, `max_calls` to `4`, and `allow_retries` to `false`. Its exact `per_video` keys are `case-a`, `case-b`, `case-c` and `case-d`, each with ceiling `0.01`. These compatibility IDs identify cases, not production videos. Keep the prior `evaluation-10` record closed and unchanged.

The frozen case mapping is A: silence with original contract; B: wrong speech with modality-only contract; C: wrong speech with original contract; D: silence with modality-only contract. The treatment removes only the four original root visual properties and their required entries. Keep the approved quote/proposal and exact request/media hashes referenced in the new private record. Its `user_evidence_ref` must retain the owner's separate four-case approval, not the earlier six-artifact approval. Current approval provenance is question `call_8dbd2f9d4fcf4ac18808e025c157549e` and the owner's affirmative USD 0.04 response.

Reserve a full `0.01` for each case before its sole dispatch. Reconcile one case's actual response, provider request ID, usage and settlement before admitting another. An unknown outcome keeps its reservation and blocks further dispatch. Existing intentions authorize recovery inspection only; changed intent/segment IDs, zero-cost outcomes, failure or verified non-submission never authorize another request for a used case. Retain raw provider evidence even when response validation rejects it. No retry, replacement model, fifth case, production generation or automatic quality acceptance is included. The bounded caller independently verifies the frozen request identity, token/output admission, transport retry settings and account configuration; this arithmetic helper makes no provider call and installs no backend cap.

## Separately approved Pro comparison

`pro-comparison-10` uses a fresh record with exact model `gemini-3.1-pro-preview`, currency `USD`, `round_limit: 0.17`, `max_calls: 3` and `allow_retries: false`. Its `per_video` keys are `pro-wrong-speech: 0.03`, `pro-silence: 0.03` and `pro-h3: 0.11`. Retain the owner's separate approval from question `call_f6a7075bf0194dfca268603fdbe67917` and the frozen comparison quote. The completed six-case and four-case records remain immutable.

Reserve each case's full ceiling before its sole dispatch. The bounded caller verifies the frozen model/account, media, prompts, request configuration and actual serialized body before forwarding, in the approved wrong-speech, silence, H3 order. Settle each response once before the next case. Any unknown outcome keeps its reservation and stops further calls; zero settlement or changed identifiers do not authorize replacement. This record permits no fourth call, retry, media generation, production-model change or automatic quality approval.

## Separately approved image fixture

`image-fixture-6` is a fresh record for the owner's approval in question `call_8270214e39304501a7f6d1f5d53d60a2`: “Sim, aprovo US$ 2,04 para esta amostra”. Set currency `USD`, round limit `2.04`, compatibility field `per_video: {"character/Ana": "2.04"}`, provider `gemini-aistudio`, model `gemini-3.1-flash-image`, resolution `1K`, aspect ratio `16:9`, `max_calls: 1` and `allow_retries: false`. This identifier denotes an asset, not a video generation.

Use the prepared project `image-handoff-fixture-6-20261108`, one initial character-sheet target, no references and the frozen final prompt/quote under `/tmp/arcreel-goal-state/image-fallback-fixture/`. Revalidate the actual nonempty preview and reserve its complete USD 2.031616 upper bound before delegating the one generation to the existing embedded Agent. The helper authenticates neither quote nor model configuration: Codex must verify both against current formal state and the owner's actual approval. The current quote is a full-context/output upper bound, not expected usage.

Reconcile the task, selected artifact and existing ledger once. Unknown delivery or unsettled usage retains the reservation and pauses further submission. Changed identifiers, zero settlement, verified non-submission and rejected output grant no additional generation under this record. Existing backend retries only for definitely-unsent connection failures do not constitute a second accepted provider request. Keep the same result for authenticated reusable-asset/storyboard upload and downstream preview checks. This round includes no second image, quality regeneration, video, pilot or paid evaluation; prior closed rounds remain unchanged.
