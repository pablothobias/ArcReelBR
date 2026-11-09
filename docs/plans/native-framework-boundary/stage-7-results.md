# Stage 7: integrated review, preservation and final evidence

Date: 2026-11-09. Base revision `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. User authorized stage 7, preservation of product customizations and separation from configuration investigation, without a commit. Repository implementation stages 0-7 are complete locally. The final selected suite has two reproduced baseline test failures, documented below; this is not an entirely green test run or a claim of live production readiness.

## Combined review

Independent standards and approved-plan reviews examined the uncommitted diff and new regression files. Matching standards were selected through `CODING_STANDARDS.md`. Claude Code was unavailable as a reviewer harness, so both reviewers used the internal Codex `gpt-6.1-sol` medium fallback. [Review record](evidence/stage-7-review.json).

**Standards:** one actionable finding was confirmed and corrected: the R12 route-conflict exception carried safe guidance but the session MCP startup sanitizer replaced it with generic advice. The applicable rule is `docs/standards/backend.md`, “Handle exceptions carrying guidance or identity separately before broad catches.” After correction, read-only re-review found no remaining actionable finding.

**Spec:** no actionable implementation mismatch, missing workflow removal or unintended product change was found. Launcher/non-launcher coverage needed explicit evidence; the additional isolated launcher check closes that evidence gap. This review does not prove absence of every possible defect.

## Complementary R12 correction

`server/session_mcp.py` now relays the direct typed `SubscriptionRouteConflictError` cause of `AgentStartupError`. Other startup errors retain the existing generic diagnostic sanitizer. SessionManager startup wrapping, Web behavior, authorization, production workflow, route selection and the stage-5 refusal are unchanged.

Six new tests invoke the real authenticated MCP server, native session service, isolated database and options/environment construction. Each known enabled selector previously produced the generic error instead of actionable guidance: **six failed before correction**, while the generic SDK-error privacy control passed. After correction, the cases expose the selector name and corrective guidance, with no SDK client construction, secret value or server data-root path in the response. The generic SDK-error control continues hiding private diagnostics. [Before-fix evidence](evidence/stage-7-before-fix.txt).

One additional integration test executes only the actual `clean()` function extracted from `scripts/run_local.sh`, with a synthetic environment, temporary HOME and a local Python environment probe. All six inherited selectors are excluded. Existing tests cover direct/non-launcher native environment construction and intercepted SDK merging. The full launcher, .env, authentication probe, live services and real CLI were not executed. This validates the clean subprocess boundary, not current deployment readiness or every startup setting source.

## Final disposition of the 17 scoped entries

| Entry | Final local disposition | Preservation |
| --- | --- | --- |
| W01 | Custom director package retired, stage 1. | Official skill routes remain; installed host copies are separate scope. |
| W02 | Exclusive policy/recovery helper and its two tests retired, stage 1. | Native recovery, idempotency and historical receipts retained. |
| W03 | Universal project/configuration preflight removed from three profiles. | Supplied settings, workflow routing and capability checks retained. |
| W04 / R08 | Blanket image quotation prerequisite removed from profiles, asset skill, shared cost description and public guide. | Native video preview/confirmations and optional quote tools retained. |
| W05 | Compulsory accounting call pair removed. | Ledger, pagination and factual financial evidence retained. |
| W06 | Broad optional-reference rule removed. | Native required-input/capability admission and uploads retained. |
| W07 | External controller-ceiling authority removed. | User limits, scope and permission remain authoritative. |
| W08 | Mandatory per-unit ASR/reviewer handoff removed. | Optional timing correction, visual review and evidence limits retained. |
| R07 | Shared automated Settings contract excludes grid toggles, stage 2. | Web user settings and supported MCP fields retained. |
| R09 | Remote guidance conditions polling on an actual batch handle, stage 2. | Real submission/waiting/envelopes and preview retained. |
| R10b | Writing cost reader replaced with native read-only reader, stage 3. | Cancellation may leave computation running, without the reproduced script migration write. |
| R11 | MCP character-image bytes/pointer commit through native transaction, stage 4. | Rollback, deletion, Web and other reference paths retained. |
| R12 | Native no-key pricing refuses enabled inherited cloud selectors, stage 5; safe MCP error propagation completed in stage 7. | Configured API behavior, subscription backend and frozen accounting basis retained. |
| R10a | In-memory cost compatibility, implemented jointly with R10b. | One fix, not a second counted implementation. |
| R10c | Native read-only script reader for image-edit preview, stage 3. | Actual editing retains migration behavior. |
| R10d | Quote caller opts out of script migration in shared planner, stage 3. | Ordinary generation keeps its migration default and route checks. |
| R10e | Native speech materialization retained; inspection contract clarified/tested, stage 6. | Valid applied timing, native invalidation, canonical speech and media retained. |

The final repository scan found no active reference to the retired helper or the specified removed prerequisite phrases across `.agents`, `agent_runtime_profile`, `server`, `public`, `skills`, `docs/testing` and `AGENTS.md`. Source review, not phrase matching alone, accounts for all eight mechanisms. No new external production harness was added. Official direct-tool next-action and embedded-session routes both remain supported.

## Tests and checks actually executed

The authoritative final selection contains 23 files, listed in [the selection manifest](evidence/stage-7-test-selection.json). It covers native session send/retry/reconnect/questions/cursors/interrupt, both shared tool hosts, all changed regression files, upload transactions, route/pricing, native workflow/preview, measured final-cut rendering, profile lifecycle, pt-BR prompts, generation queue/recovery, and Gemini request/billing controls. Provider/SDK boundaries use existing fakes/interception; local media fixtures use ffmpeg.

Command: `PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider`, followed by the exact paths in the selection manifest.

- **Final: 1,472 passed, 2 failed, 1 warning in 62.37s**, exit 1. [Full output](evidence/stage-7-final-pytest.txt). The two failures are the baseline cases below; no other case failed.
- The initial integrated 21-file selection passed **1,434 cases** before the complementary fix. [Output](evidence/stage-7-pytest.txt). These overlap the final selection and must not be added to its count.
- The affected startup/route/session/Web follow-up produced **64 passed, 2 baseline failures** before final consolidation. [Output](evidence/stage-7-correction-pytest.txt). These also overlap the final selection.
- Ruff check and format check passed on the three stage-7 Python files. [Output](evidence/stage-7-lint.txt).
- Basedpyright on those files: **0 errors, 0 warnings, 0 notes**. [Output](evidence/stage-7-types.txt).
- Prior-stage checks are reused for unchanged sources, including stage-6 profile lint and speech read/presentation coverage, and stages 2-5 lint/types and transaction/settings/admission characterization. Final selection repeats the relevant integrated controls; no complete gate was requested.
- `git diff --check` passed. The one pytest warning is SQLAlchemy's unsupported reflection of expression index `idx_tasks_dedupe_active`.

An initial evidence script rejected a tracked directory symlink and the shell briefly started unfiltered pytest collection without the intended selection. It was interrupted before any test ran: **0 cases executed**. The evidence script was corrected to hash symlink entries explicitly and use a validated subprocess argument list. [Interrupted collection log](evidence/stage-7-interrupted-collection.txt). No full suite result is claimed.

## Two pre-existing failures, preserved rather than concealed

Both cases are in `tests/unit/server/routers/test_assistant_routes.py::TestAssistantRoutes::test_queued_message_reconnect_failures_explain_the_cause`, with `resend_queued_message-/resend` and `send_queued_message_now-/send-now` parameters. The actual Web error is English, while the test compares it to a default Chinese `make_translator()` result.

The same two cases fail in the main checkout at the same base revision, whose test/route sources are unchanged. [Baseline reproduction](evidence/stage-7-baseline-web-failures.txt): **2 failed, 22 deselected**, with the same mismatch. This establishes pre-existing test debt, not a newly demonstrated product-language regression. Neither the test expectation nor product locale/default policy was changed to obtain a green result. These failures remain unresolved outside the boundary cleanup.

## Preservation and other-worktree boundary

The cumulative comparison checks **4,688 regular tracked files and 48 tracked symlink entries** outside the accumulated changed paths against HEAD. Stage 7 changes only the MCP error branch and two regression files relative to the stage-6 state. All other prior-stage tracked content remains unchanged. [Scope evidence](evidence/stage-7-scope-check.json).

This protects frontend/RafaCena, supported language/content handling, technical-prompt policy, snapshot/history/media/version implementations, Gemini backend/accounting source, native speech implementation, official public skills and the local launcher. Tests substantiate the selected contracts; no pt-BR transcription, real-model adherence, editorial acceptance, live compaction or actual client-disconnect propagation is inferred.

A read-only overlap check of the other worktree found shared tracked changes in `lib/config/env_keys.py`, `lib/config/service.py` and `server/routers/projects.py`. Three-way textual merges are clean in disposable files; no combined source was installed, executed or functionally validated. The custom skill is deleted here versus disabled there, an intentional disposition that must retain retirement during later integration. [Overlap evidence](evidence/stage-7-worktree-overlap.json). No claim of coordination with the other operator or approval of its settings is made.

No credentials, saved/current models, endpoints, host skills, MCP installation, auth state, live process, production project or historical usage record was modified. Current host/auth readiness and the separate configuration investigation remain pending with their owner. No commit, push, merge or paid action was performed.
