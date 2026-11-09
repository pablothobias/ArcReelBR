## Parent

https://github.com/pablothobias/ArcReelBR/issues/2

## What to build

A dedicated Codex directing skill authorizes or pauses the next production action using existing ArcReel quotes and usage, records outstanding intent and resumes safely while the chat and local application are running.

## Acceptance criteria

- [ ] Keep budget and quality-attempt enforcement entirely in Codex context and its recovery record; do not add backend spend caps or duplicate billing.
- [ ] Require explicit per-video/per-round numeric amounts and currency before paid submissions; the first round is one pilot and unknown prices pause.
- [ ] Include pending authorized spend, discarded work and billable transport retries; distinguish polling from new generation and apply initial generation plus at most two quality regenerations per rejected segment.
- [ ] Use existing confirmation parameters for authorized autonomy and existing workflow state as the production authority.
- [ ] Persist pending intent, review decisions, budget allowance and attempt counts without duplicating assets/scripts; reconcile completed jobs before resubmission.
- [ ] Pause on subscription quota exhaustion without paid fallback; demonstrate budget-stop and interruption/re-entry scenarios with controlled fixtures.
- [ ] Do not promise continued supervision after the Codex execution ends; provide explicit resumable state.
