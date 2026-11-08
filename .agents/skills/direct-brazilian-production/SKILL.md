---
name: direct-brazilian-production
description: Direct or resume Brazilian ArcReel production through the existing embedded Agent, checking approved spending, quality attempts and pending jobs before each production action.
---

# Direct Brazilian production

Codex owns research, adaptation, review and the owner's approved allowance. The embedded ArcReel Agent executes production through the existing authenticated MCP session and production tools. Apply this skill while Codex and the local application run; ending the chat execution ends supervision. Keep the recovery record ready for explicit resumption.

## Establish the round

Read the current specification #2, current ticket and native dependencies in `pablothobias/ArcReelBR`, plus the owner's current objective. Preserve formal scripts and approved Portuguese speech; use English technical instructions. Production authority stays in ArcReel workflow state, formal artifacts, selected versions, tasks, provider checkpoints, existing quotes and usage records.

The current objective requires three separate approvals: capability sample #9, one pilot #11, then the two-episode continuity sample #12 after #11 completes. The capability sample precedes the pilot under that explicit objective; #8's older “first round is one pilot” wording does not combine those allowances. Approval for one round never authorizes another round or the 30-request collection. Before opening a later round, verify prerequisite completion and record its evidence pointer.

Before any billable generation or evaluation, obtain a concrete current quote from the existing preview/quote path. Present the video IDs, original resolution and any delivery conversion, provider/model, exact target set, priced actions, uncertainty, a numeric per-video ceiling, a numeric round ceiling, and currency. Obtain the owner's explicit approval of those numbers and scope in this chat. A missing price, `amount: null`, `unpriced: true`, or any unpriced quote item pauses submission. A partial priced sum is not the batch price. Subscription token telemetry has no invented per-token charge; subscription exhaustion still pauses dependent work.

Use one local recovery JSON file outside the public repository. Read [recovery format](references/recovery-format.md) when initializing it or when an interruption needs reconciliation. Store approval and quote evidence pointers, pending intent, session/client keys, job/batch/usage IDs, reviews and attempt counters. Keep source text, scripts, assets, provider requests and the billing ledger in their existing ArcReel locations, referenced by ID or path. The record is directing context, not a second production database or billing system.

## Authorize one action

1. Read current ArcReel workflow, task/batch/provider-checkpoint and artifact-version state. Read existing usage for every preceding submission. Reconcile pending intentions before asking for another generation. A completed job is reused and reviewed; a timeout or absent local reply is not a failed provider submission.
2. Build a bounded candidate with the existing quote reference and a stable intent/session client key. For a batch, reserve its complete priced target set before any delegation and respect all-or-nothing admission. This helper serializes unresolved submissions; use one candidate representing a fully quoted batch only when its attempt scope is one segment. Otherwise approve and direct individual segment calls from the start, never split an already-admitted batch during recovery.
3. Run `uv run python .agents/skills/direct-brazilian-production/scripts/policy.py reserve --record /absolute/private/recovery.json --input /absolute/private/action.json`. A successful `reserve_before_delegating` result atomically records the pending reservation **before** sending the instruction. `reconcile_existing` and `reuse_complete` authorize inspection of the existing work, not another submission. `pause` stops dependent new submissions.
4. Delegate that exact approved action to the embedded Agent using the existing session tools, retaining its `client_key`. Use the production tool's supported confirmation fields only for facts covered by the owner's approval, such as `confirmed_request_durations` copied unchanged from current `preview: true`. For overwrites and source edits, carry the actual returned revision/confirmation parameters and verify that the approval covers their effects. A budget approval does not approve a script change or a changed duration tier. Keep the selected provider/model and target set within the approved quote.
5. Reconcile the returned individual task/batch IDs and authoritative usage before the next action. `get_generation_batch` with its `poll_after_seconds` reads existing work without spending or incrementing attempts. Report task, provider submission, artifact currency and review status separately. A terminal Agent reply does not establish production completion.

A separately approved `evaluation-10` round is limited to the six named audiovisual artifacts, exact model and USD ceilings in [recovery format](references/recovery-format.md#separately-approved-audiovisual-evaluation). Reserve each artifact once, preserve provider response/usage evidence, and reconcile before the next call. This exception does not change generation-round counts or quality attempts.

A separately approved `diagnostic-10` round uses a fresh recovery record for the four frozen cases in [the diagnostic scope](references/recovery-format.md#separately-approved-four-case-diagnostic). Preserve the closed evaluation record, reserve each case once, and retain its raw request, response and usage evidence before proceeding.

The helper reads and updates only the local directing record. It makes no provider call, controls no worker and enforces no backend cap. Its inputs are evidence snapshots that Codex must verify against the actual approval, current quotes and application state. The arithmetic cannot authenticate an evidence pointer or guarantee a provider's eventual charge. A changed quote, tier, target set or unexpected charge is reviewed against the original allowance before any next submission.

## Rejection, transport and quota

Each video segment gets an initial quality generation plus at most two quality regenerations. Record a rejected completed result with its review evidence before a quality regeneration; preserve approved speech. Switching back to a usable historical version uses existing version-selection operations and spends nothing. Mark discarded work in the recovery record and retain its actual usage in the allowance calculation. Use separate resource IDs for independently produced assets; do not represent an asset image as the segment's initial video generation.

A transport retry requires authoritative evidence that the earlier job failed and is not still executing or recoverable. Read its provider checkpoint and follow its existing `problem.action`: resume retrieval or wait for an existing task when supported. Count every billable transport attempt and every discarded result, even when they do not consume another quality regeneration. Keep the original quote reservation for unsettled usage. Settlement replaces that reservation once with referenced ledger usage; it does not add a second local charge. Unknown outcomes retain their reservation and pause resubmission.

On `subscription_quota_paused`, record the pause immediately and preserve pending intention, counters and job references. Poll existing jobs if needed; stop new dependent submissions. Continue only after explicit owner resumption and verified available subscription quota. Use the official subscription authentication path without a paid API fallback.

## Stop and resume

Before yielding or stopping, reconcile what can be verified and save the pending intention, next decision, allowance, spent/reserved amounts, quality counters, latest reviews and authoritative evidence links. Tell the owner the exact remaining action and recovery-record location. State whether anything remains in flight; promise no background supervision after Codex stops.

On re-entry, load that record, reconnect to the existing session and query its accepted/queued client keys, questions, entries, jobs, provider checkpoints, artifacts and ledger. Reconcile completed work before requesting anything new. If authoritative evidence cannot rule out an existing charged submission, retain the reservation and pause. A deliberate retry after verified non-submission gets a new recorded intent; retain the original evidence rather than deleting history.
