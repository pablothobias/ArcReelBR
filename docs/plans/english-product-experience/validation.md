# English product experience implementation record

Status: locally validated candidate complete. Independent source/bilingual reviews and final coordinator consistency review are complete; live-model evaluation remains pending.

## Approved scope and baseline

Owner approval: “Pode executar o plano em outro agente, adotando inglês como padrão da interface e das respostas, preservando os históricos e o idioma dos conteúdos dos projetos, até concluir a candidata validada localmente.”

Source baseline: `a779b5d511d873854d81e12c4a932629b1c58995`, `main`. Initially only this untracked plan directory existed. No commit, push, deployment, workflow dispatch, paid calls, real-project/session mutations or dependency changes are included. The implementation uses writing-for-agents and diagnosing-bugs guidance; the frontend helper uses agent-browser and React Doctor. No `docs/LESSONS.md` access.

## Confirmed causes and unknown screenshot

The baseline frontend HTML and branding literals independently supplied Chinese metadata, i18next used navigator detection and Chinese fallback, REST/SSE sent Chinese when its language was absent, backend presentation default was Chinese, and runtime unknown locales fell back to Chinese. The old Agent rule coupled conversational and all creative output language. These source-level defects are confirmed independently of the screenshot. The screenshot-session request and persisted prompt were not inspected, so its specific cause remains unknown. No live service was restarted or real session read. Read-only process inspection showed the existing uvicorn service running from a different checkout, `Projects/worktrees/ArcReelBR/local-subscription-run-17c182`, whose HEAD was `e2e5dbfe5600a2eccadef4f72b4471cfa893be0a`; it therefore does not demonstrate behavior of this candidate. This difference does not establish the screenshot-conversation cause.

## Locale consumer inventory

`lib.i18n.DEFAULT_LOCALE` governs presentation: catalogs/errors/events/templates, validation text, provider/model display names, market message-key membership checks, tool problem summaries and project-change hint labels. Consumers were searched before changing the default. Locale key sets remain identical. Runtime option assembly and service/session entry defaults also use it for conversational presentation. `server.i18n.get_locale` keeps its existing ordered supported-range selection and regional normalization, falling back to English. The library/runtime share supported-base-tag normalization. `lib.infra.validation_messages.default_translate` is explicitly pinned to legacy Chinese: internal comparison fingerprints and script-batch location parsing consume its output. Request boundaries still supply their request translator and default to English. A regression test verifies structured/literal locations and explicit English presentation without changing legacy diagnostics.

ProjectManager's missing target-language fallback to `中文`, source-language/duration/reading-unit rules, creative template variants, migration literals and source content remain unchanged. No project-schema migration or preference subsystem is introduced.

## Session trace and preservation

REST language reaches `AssistantService.send_or_create` and rewrite/branch paths, then session creation or `SessionManager.send_message`. A new accepted message records its normalized locale in the in-memory queued object. SDK frames prepend one application conversation-language block to original content, preserving image blocks and unchanged visible/accepted entries. The original content remains the resend source, so rebuilding a delivery does not duplicate context. Queued/unsent state is already memory-only and does not survive a server process restart; the accepted locale shares that existing lifecycle and no persistence guarantee is added. Recorded accepted user entries retain their content across restart; a newly accepted continuation uses its new request locale. The first application text block is authoritative, and markers quoted later in source/user text remain data. Each generated block is bound to the CLI message UUID. Event-log normalization removes only an exact first generated block for that same UUID, preserving literal user lookalikes and avoiding context leakage during branch/backfill. Same-key retries return their original acceptance and locale. Unsent resend, send-now and CLI-discard redelivery retain the accepted locale. REST/SSE reconnect alone does not create a user turn or change accepted queued context.

Installed SDK `types.py::SystemPromptPreset.snapshot` documents that false rebuilds on every request including resume; minimum CLI is 2.1.257 and bundled CLI reports 2.1.309. The options assembler now passes false, so legacy frozen Chinese system rules are replaced on normal resume rather than contradicted by a lower-priority user frame. A resident new-code session has a stable system clause explicitly honoring current per-message context. Compaction rebuilds the same current policy; current message context remains attached to its delivery. Local mocks prove options/frame routing, not actual CLI/model compaction behavior. Previously running old-code clients require normal owner-managed process upgrade/restart; they were not touched.

Initial source/session baseline tests passed (78 tests). After implementation seven existing assertions failed because they intentionally expected the former coupled language rule or unwrapped SDK content. Each was updated at its actual producer boundary; user-content and creative-preservation assertions were strengthened. No stored transcript, session ID, event-log content, memory, artifact basis or frozen generation request was translated or reset.

## Residual Chinese dispositions

The complete targeted [residual inventory](residual-inventory.md) records consumers and final actions. Identified model-facing overwrite/dry-run/repair/admission/pricing wrappers have been translated and independently reviewed, rather than deferred merely because they were preexisting. Raw interpolated provider/legacy diagnostics, user/source text and compatible syntax remain intentional exceptions.

| Source/consumer | Classification | Disposition |
| --- | --- | --- |
| `frontend/src/i18n/zh`, `lib/i18n/zh` | Supported locale values | Preserve all Chinese resources and locale selection |
| `lib/infra/validation_messages.py::default_translate` | Internal comparison and location-parser compatibility | Pin legacy Chinese; request presentation remains localized independently |
| `lib/project/project_manager.py` source/target language and creative workflows | Creative default and source content | Preserve `中文` fallback and all segmentation/speech contracts |
| `lib/prompts/.../agent_language_rule.md` | Live model instruction | Split reply language from creative language; independently review |
| `frontend/index.html`, `frontend/src/branding.ts` | Presentation default | English startup/runtime defaults; owner overrides remain literal |
| `agent_runtime_profile/**`, generated profile copies | Mode instructions, examples, compatibility syntax | No profile source file changed in this initiative; existing manifest sync stays authoritative |
| `docs/`, `website/docs/**`, localized public examples | Chinese-source public pipeline and historical records | Preserve pipeline and editions; new maintenance record in English |
| Hidden configuration, migrations, test inputs, legacy style bodies | Consumer syntax, multilingual fixtures, historical compatibility | Preserve; no blanket replacement |
| `server/i18n.py` display-name failure log | Passive maintenance log | Translate touched log to English |
| User histories, project source, memory, customized/deleted profile files | User-owned content | Not accessed or rewritten; disposable lifecycle fixtures only |
| Official provider/catalog/marketplace URLs and attribution | External dependencies/legal/source history | Preserve |
| No-release 404 state | Separate optional update behavior | Deferred optional independent-repository behavior; no release created |

This targeted inventory reconciles this initiative with the earlier [preserved-content inventory](../english-translation/preserved-content.md); it is not a claim that every Chinese character is a defect or every source was retranslated.

## Validation

Python 3.12.16, Claude Agent SDK 0.2.173, bundled CLI 2.1.309; frontend Node 24.22.2. No dependencies were upgraded. Logs are retained in [evidence/](evidence/), with [owner command selections](evidence/owner-commands.json). Passing runs overlap; counts below must not be summed.

| Actual command/selection | Result and scope |
| --- | --- |
| `uv run python -m pytest tests/unit/server/agent_runtime tests/unit/lib/i18n tests/unit/lib/agent/test_profile_translation_lifecycle.py tests/unit/lib/prompts/prompt_templates tests/unit/test_public_contract.py -q --tb=short` | 834 passed in the initial candidate iteration. Reuse unchanged profile/schema/public-contract evidence; later refined runtime and model-facing sources have the owner checks below. |
| `uv run python -m pytest tests/unit/server/agent_runtime/test_event_log.py tests/integration/server/agent_runtime/test_session_branch.py -q --tb=short` | 118 passed, including new real DB transcript/branch/backfill tests preserving quoted lookalike markers. |
| Runtime locale/queue/options + `tests/unit/lib/i18n` + `tests/unit/lib/infra/test_validation_messages.py` | 95 passed after the internal legacy-renderer pin. |
| Full backend `uv run python -m pytest -n 4 --dist loadfile --max-worker-restart=0 -q --tb=short` | Interrupted deliberately after source refinement and concurrent host contention: 8,783 passed, 353 failed, 11 skipped. This stale partial run is not a complete-suite pass. [353 unique full IDs and dispositions](partial-backend-diagnostics.json) preserve exact parameterized IDs. |
| Serial affected-file selection, all 22 files from those failures | 1,946 passed, 19 failed; all 19 were subsequently rechecked after producer-specific expectations were corrected. One FIFO subprocess timeout passed in the lower-contention affected-file run, with no timeout relaxation. |
| [Final selection command](evidence/final-selection-command.json), owner receipt/draft/runtime paths plus all remaining consumer failures | 380 passed and two newly translated receipt count assertions failed; neither assertion was removed, both were updated and passed below. |
| Full split receipt suite + the two exact receipt count cases + asset/voice/task/default HTTP locale suites | 113 passed. Includes missing/unsupported HTTP language -> English and explicit `zh-CN` -> Chinese. Source text, reference markers, no-save preview assertions and structured payloads remain checked. |
| Terminal result/context/quote + complete integration media-tool directory | 313 passed, 34 presentation assertions failed after the final wrapper translation. All 34 are covered by the successful 172-test rerun of result/context/quote/video owner files. Structured/price/admission assertions were retained. |
| Text handlers, tool runtime entry/source/batch/planning paths, drama/narration/ad/reference/incremental generator owner files | 574 passed, 10 translated-wrapper assertions failed; the exact ten reran successfully (10 passed). Raw diagnostic/source literals and machine contracts were preserved. |
| Frontend focused initialization/branding tests | 13 passed, including legacy sessionStorage and regional saved preferences. |
| Frontend `pnpm check` | TypeScript, ESLint and knip passed. Broad Vitest: 4,038 passed, 23 failed under simultaneous heavy host load. All nine failing files reran unchanged with `--maxWorkers=1`: 220 passed, resolving every broad failure without relaxing tests or timeouts. |
| `pnpm e2e --project=1440x900 --workers=2 e2e/regions/language-policy.spec.ts e2e/regions/settings.spec.ts e2e/regions/project-settings.spec.ts e2e/regions/agent-session-projection.spec.ts` | 43 passed, using recorded fixtures only. Fresh supported/non-supported navigators, saved regional preferences, storage precedence and explicit switches, metadata and request headers checked. No real backend/project/session mutation. |
| Broad frontend E2E | Intentionally stopped for resource containment: 316 passed, 8 interrupted, 1,222 not run. Not a complete E2E pass. |
| Frontend final typecheck + changed-file ESLint + `npx react-doctor@latest --verbose --scope changed` | Passed; React Doctor 100/100, no findings. Isolated browser and preview server closed. |
| Frontend production `pnpm build` with Node 24.22.2 | Passed (typecheck and Vite production build); generated `dist/index.html` has English title/description and `lang="en"`. Chunk-size warnings remain informational. Initial Node 22 shell build also passed but warned about the engine; final evidence uses the required Node 24 runtime. |
| Runtime profile lint | Passed. No profile source/schema change or forced materialization/reset. |
| Final `uv run basedpyright --warnings`, Ruff check and format check on changed Python files, `scripts/audit_tests.py --check`, `scripts/audit_conventions.py --check` | Passed: 0 type errors/warnings, lint clean, 48 Python files formatted, audit tests 0 violations, conventions exit 0; Source whitespace checks passed; raw tool-output logs retain emitted whitespace. |

All known failed cases were closed by passing post-fix evidence. The complete backend/full browser suites were not rerun to completion; local scope uses the affected-owner checks above and retains partial-run limits explicitly. Website/docs build not run because the public site, public editions and their source/translation pipeline were unchanged.

## Lifecycle evidence and review

| Boundary | Local evidence and limit |
| --- | --- |
| Fresh session and unknown/regional locale | Rendered options use normalized language and English fallback; per-message original content/images preserved. |
| Resident session after UI switch | Separate accepted queued messages carry their own locales without reconnecting, resetting or rewriting entries. Same-key retry remains idempotent. |
| Reconnect/resume/restart | Options use supported `snapshot=False` with resume/session identity unchanged; session-flow fake clients exercise cold revival, concurrent sends, unsent transfer and resend. Existing memory-only queue lifetime is preserved. |
| Compaction | SDK contract documents prompt rebuild with false, and the current message carries its context; actual CLI/model compaction behavior was not invoked. This remains a live-model validation boundary. |
| Branch/rewrite/backfill | Real `DbSessionStore` prefix copy, `SdkTranscriptAdapter`, and event-log backfill preserve original content/UUID and strip only exact UUID-bound application prefix. Quoted user lookalikes remain. |
| Profile/custom/deleted files and rollback | Existing disposable translation lifecycle/profile roundtrip tests pass; no profile source changed in this initiative. No real session/profile reset. |
| Creative/media requests | Mode/source duration and content rules remain; owner tests across drama, narration, ad and reference modes preserve tool parameters, paths, prompt text, overwrite consent and artifact state. No paid call or submitted-request mutation. |

Independent native reviewer approved the runtime/prompt policy, the UUID-bound backfill correction and all subsequent bilingual model-facing receipt, repair, overwrite/dry-run, video admission/pricing and terminal-result changes. The preferred opposite-Harness Claude reviewer was unavailable; this was independent same-Harness review, not cross-Harness or live-model certification. Reviewed source hashes are captured in [review-and-files.json](review-and-files.json).

Review caught and closed: application context leaking into branch/backfill, truncated parameterized failure IDs in the evidence manifest, and incorrectly English expectations on explicitly legacy-Chinese internal diagnostics. Counts, field/marker checks, confirmation boundaries and source-content assertions were retained rather than weakened. The final text-handler batch has one intentional display expression change: canonical English asset type replaces a local Chinese label lookup; structured types and actual names stay unchanged.

English storage precedence is supported localStorage > supported cookie > supported sessionStorage > English. URL hints and navigator/html language are excluded for fresh detection. Metadata is an owner literal with English defaults; document `lang` follows the supported UI selection. Legacy explicit preferences and automatically populated valid caches are preserved conservatively.

## Rollback

Revert the changed source batches together, including the owner-facing instruction/receipt batches. Preserve browser storage: valid saved locales need no migration or clearing. Fresh clients that cached English now have a valid preference, and rollback must preserve it conservatively. There is no persisted locale/schema migration to reverse. Existing project/profile/history/media data needs no rewriting. This change does not alter any materialized profile source; existing manifest-based customized/deleted/colliding-file protections remain in force and are exercised by disposable profile tests.

On a disposable session, resuming with old options restores snapshot=true behavior but can reuse the prompt most recently recorded by the CLI. Reverting Git alone cannot restore a historical frozen system-prompt snapshot. To retain conversation and return to an old policy, explicitly rebuild the desired old append with snapshot=false on normal resume before choosing to freeze it; do not delete transcript or force a reset. That operational CLI/model rollback has not been run because no live SDK/model session is authorized. Local tests verify source/profile roundtrip and option reconstruction only. Interrupted/pending paid requests remain frozen and must resume unchanged.

## Pending real-model evaluations

The maintenance equivalence track retains its original baseline and invariants in [evaluation.md](../english-translation/evaluation.md). The new product-policy track compares this initiative with `a779b5d511d873854d81e12c4a932629b1c58995` and explicitly allows English defaults, saved-only locale detection, English fallback, uncoupled creative language and future-turn reply context with snapshot refresh. Both require fixed model/configuration, disposable inputs, three runs per scenario, sanitized traces, independent scoring and recorded costs. Neither was run, and neither follows from local/browser checks. No live-model behavioral release is claimed.


## Negative assertion follow-up, 2026-11-08

Resolved the review finding about negative assertions still searching for Chinese diagnostics after the English-default change. Four exclusions in `test_promote_draft.py` now use the English catalog for missing-scene notices, missing formal scripts and pending authoring drafts. Two analogous exclusions in `test_grids_router.py` now use the current default translator and actual invalid-project-name message instead of an obsolete Chinese fragment. All six assertions remain present. Creative fixtures, reference markers and deliberately Chinese compatibility/locale assertions remain unchanged; no production code changed.

- `uv run --frozen --no-sync pytest tests/integration/server/agent_toolset/test_promote_draft.py -q --tb=short`: **70 passed**, [log](evidence/negative-language-assertions-promote.log).
- `uv run --frozen --no-sync pytest tests/unit/server/routers/test_grids_router.py -q --tb=short`: **72 passed**, [log](evidence/negative-language-assertions-grids.log).
- Ruff lint and format checks on both files passed; source-only whitespace checks passed. Existing Starlette deprecation and SQLite expression-index reflection warnings remain informational.

These two selections are disjoint, but overlap earlier candidate runs and are not additional unique coverage beyond them. Source/test hashes in `review-and-files.json` were refreshed for the two changed tests. No commit or push was performed.


## Commit preparation, 2026-11-08

Whitespace validation excludes `evidence/*.log`: pytest and build-tool output contains emitted trailing spaces and terminal blank lines. The raw logs are preserved verbatim. `git show --format= --check HEAD -- . ':!docs/plans/english-product-experience/evidence/*.log'` passed for the candidate commit; source/test hashes and the exact task-file inventory were also verified. No source or test behavior changed during commit preparation.
