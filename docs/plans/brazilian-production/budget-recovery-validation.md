# Directing allowance and recovery validation

## Scope

Issue [#8](https://github.com/pablothobias/ArcReelBR/issues/8) is implemented in `.agents/skills/direct-brazilian-production/`. Its policy helper is a local, manually invoked decision/checkpoint command. It never starts an Agent, submits media, polls automatically, edits the application, or changes backend billing. The embedded Agent and ArcReel's existing workflow, quotes, task/provider checkpoints, artifacts and ledger remain authoritative.

The explicit current objective requires three independent monetary approvals: the capability sample in #9, the one-video pilot in #11, and the two-episode continuity sample in #12. This reconciles #8's older “first round is one pilot” phrase with the separately required earlier capability sample. A record grants only its listed video scope and round, with verified prerequisite evidence for pilot and continuity. No allowance is inferred for the collection.

## Acceptance evidence

| Criterion | Implementation and verification |
|---|---|
| Director-side enforcement | Skill instructions and local `scripts/policy.py`; no backend caps, provider integration or second accounting ledger |
| Explicit numeric approval | Requires quote references, owner-message evidence, numeric round and per-video limits, matching currency and scoped video IDs; null, bool, non-finite and negative prices pause |
| Pending, discarded and transport spend | Every intention reserves its quoted commitment before delegation; authoritative settlement replaces that reservation once; discarded and billable failed attempts remain counted; unsettled results keep their reservation |
| Quality-attempt limit | Initial generation computes attempt 1; completed rejected media and review evidence are required before attempts 2 and 3; attempt 4 pauses; transport retries preserve the quality index but reserve another quoted cost |
| Existing confirmations | Skill directs `preview: true`, all-or-nothing admission and unchanged `confirmed_request_durations`; actual returned revision/confirmation fields remain required for independently approved effects |
| Safe re-entry | Pending intent and stable session client key are saved before dispatch; replay requests reconciliation; completed authoritative jobs produce `reuse_complete`; unresolved or recoverable provider work never authorizes a replacement |
| Subscription quota | Persisted `subscription_quota_paused` stops new dependent intentions; existing job polling and reconciliation remain possible; explicit resume plus verified quota availability clears only the pause |
| End of supervision | Skill requires a recovery path, pending intent, next decision and in-flight status; it explicitly states supervision ends with Codex execution |

## Controlled scenarios

`tests/unit/skills/test_direct_brazilian_policy.py` exercises approval and unknown-price stops, independent per-video limits, discarded charged work, billable transport retries, unresolved reservations, non-submission evidence, accepted/rejected decisions, three-attempt exhaustion, quota pause/resume, currency/round separation, protected attempt/settlement fields, and invalidation of stale resubmission-safety evidence after a new provider-state observation.

In the budget-stop fixture, a USD 10 allowance retains USD 6 of discarded charged work and reserves another USD 3 for a verified transport retry. A further USD 2 request pauses because the total would be USD 11. The retry does not consume a quality regeneration. These are controlled numeric fixtures, not owner approval or actual provider prices.

The interruption fixture saves a pending intention before a simulated application dispatch, reloads the JSON after interruption, reconciles an already completed authoritative job, and replays the original intent. Exactly one simulated submission and one intention remain. The helper never executes the simulated submission; the test uses its decision to demonstrate that recovery does not authorize a duplicate.

`tests/integration/skills/test_direct_brazilian_policy_cli.py` additionally invokes the actual standalone CLI with temporary files. It verifies durable pre-dispatch reservation, repeated-intent reconciliation, completed-job reuse and an over-budget pause that leaves the record unchanged.

## Commands and results

On 2026-11-08:

```text
uv run python -m pytest tests/unit/skills/test_direct_brazilian_policy.py tests/integration/skills/test_direct_brazilian_policy_cli.py -q --no-cov
20 passed

uv run ruff check .agents/skills/direct-brazilian-production/scripts/policy.py tests/unit/skills/test_direct_brazilian_policy.py tests/integration/skills/test_direct_brazilian_policy_cli.py
All checks passed

uv run python scripts/audit_tests.py --check --tests tests/unit/skills --tests tests/integration/skills
0 violations

uv run python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" .agents/skills/direct-brazilian-production
Skill is valid
```

Independent Codex reviewer `implement_mcp` reviewed the skill, recovery format and helper, independently ran all 20 tests and separate-process CLI recovery, and reproduced a stale resubmission-safety defect. The author fixed it; the reviewer repeated the original failed-to-pending-to-failed sequence and verified that a retry now pauses unless current authoritative evidence reconfirms safety. No remaining actionable findings.

## Operational limits

The helper trusts evidence snapshots and the actual owner's approval, which Codex must verify. It cannot authenticate a pointer, infer an unknown provider outcome, guarantee final charges from an estimate, or stop a separately operated application. It permits one unresolved segment submission at a time; a multi-segment batch requires separate per-segment bookkeeping and is not silently split during recovery. One writer owns each local recovery file.

No paid provider or evaluation calls were made for these tests. No actual media-production recovery is claimed: the implemented criterion here is the explicitly requested controlled budget-stop and interruption/re-entry behavior. Actual provider recovery remains part of the pilot validation. The checkpoint stores references and directing choices, not copies of formal scripts, assets or authoritative jobs.
