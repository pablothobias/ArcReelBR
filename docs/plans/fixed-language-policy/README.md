# Fixed product language policy

> Withdrawn implementation: its behavioral changes have been reverted at the owner’s request, preserving prior customizations and native-framework stages 0-7. [Rollback results](rollback-results.md) supersede the active-policy claims below. Original commands, outputs and observations remain historical evidence; they do not validate the restored state.

Date: 2026-11-09. Base HEAD `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`, retaining all uncommitted native-framework-boundary stages. The owner explicitly authorized English interface and technical prompts, Brazilian Portuguese dialogue, removal of the Chinese prompt instruction, preservation review and tests without a commit. [ADR 0123](../../adr/0123-fixed-english-presentation-and-brazilian-portuguese-production.md) records the superseding decision.

## Point-by-point scope and side effects

| Surface | Previous behavior | Current rule and preservation boundary |
| --- | --- | --- |
| Interface startup | English default, saved supported locales could select another language. | English is selected synchronously before REST/SSE headers. Saved localStorage/cookie/session values are ignored for presentation, not migrated or deleted. |
| General Settings | Language selector could change the interface. | Displays fixed English, disabled. Theme and onboarding actions retain their existing behavior. |
| Translation resources | Four locales and normalization APIs. | Files, identifiers and backend localization remain intact for compatibility and explicit resource tests. Normal product UI offers one language. |
| Embedded Agent system prompt | Request locale selected the conversational default. | System instructions always select English and distinguish technical prompts from pt-BR speech. Native snapshot rebuilding stays enabled. |
| New Agent message delivery | Each locale selected its application language prefix. | Newly delivered frames use English, retaining message UUID, priority, queued payload, user text and retry behavior. |
| Historical transcript context | Exact UUID-bound prefixes in all supported locales were removable. | Parser unchanged. It still removes genuine historical prefixes and preserves quoted/lookalike user content. No history rewrite. |
| Built-in generation templates | Source-selected output except the existing pt-BR split policy. | Shared output-language filter now selects English technical directions and pt-BR creative speech for every argument, including missing/legacy source context. |
| Native generation reference | Explicitly required Chinese image/video prompts. | Replaced with English technical/image/video prompts and verbatim approved pt-BR speech. Cultural examples and functional asset-reference syntax remain unchanged. |
| Source-language skill guidance | Could be mistaken for an output-language selector; examples omitted pt-BR/ru. | Input-language and reading-metric role is explicit, supported code examples include pt-BR/ru. No schema restriction or automatic setting reset. |
| Source metrics and metadata | Reading units/rates depend on actual source context. | Schemas, metrics, rate overrides, source detection and provenance implementations are unchanged. Production-language rules do not globally relabel foreign originals as pt-BR. |
| Verbatim workflows | Preserve source speech and narration exactly. | Keep native verbatim validation. Foreign material needs an approved pt-BR adaptation before a workflow that copies speech verbatim. No silent translation of existing approved scripts. |
| Existing artifacts and customizations | Native histories, profiles, media, timing and frozen submissions. | No production file/database mutation, regeneration, snapshot reset or forced overwrite of customized profiles. RafaCena, speech/timing, providers/accounting and previous boundary fixes are retained. |

The changed prompt rule affects future model inputs and can change prompt fingerprints. It does not establish real-model compliance, translate historical requests or authorize regeneration. Existing resident processes/materialized customized profiles can retain old instructions until normal owner-managed refresh. No live refresh/restart was performed.

The public installation guide and AGENTS pointer reference the new policy. ADR 0122 is explicitly superseded only for current presentation/reply/output choices. Maintenance English, preservation of source/history and the public Chinese-source documentation pipeline remain in force.

## Validation

- Backend: **1,715 passed, one warning in 182.00s**. [Output](evidence/backend.txt). Coverage includes all prompt tests, multilingual source preservation, options/frame delivery, event log/replay/branch/retry, native profile lifecycle and both MCP hosts. The warning is the existing SQLite expression-index reflection limitation.
- Complete frontend: **4,067 passed across 307 files in 136.16s**, using `pnpm exec vitest run --maxWorkers=4`. [Output](evidence/frontend-all-bounded.txt). The initial unbounded run had 4,064 passes and three five-second timeouts in endpoint tests. A controlled one-worker diagnosis of both files passed all 25 cases. The bounded complete run retained all cases and default timeouts; no test/production changes were made between those executions. This is evidence of a passing bounded run, not proof of the timeout root cause. [Initial run](evidence/frontend-all.txt), [isolated diagnosis](evidence/frontend-endpoint-diagnosis.txt).
- Focused frontend: **107 passed across four files**. [Output](evidence/frontend.txt). Includes startup with old cache/browser values, unchanged stored data, REST/SSE headers, fixed Settings language and preserved theme/onboarding actions.
- Browser page policy: **55 passed across five viewports** from 1024x600 to 2560x1440. [Output](evidence/pages-all-viewports.txt). Recorded backend API responses and blocked external traffic; no live account/provider service. These exercise login, document metadata, old preferences and fixed Settings after reload.
- TypeScript complete frontend/e2e typecheck passed. [Output](evidence/frontend-types.txt).
- Ruff check/format passed on the seven primary Python files and the separate route assertion file. [Output](evidence/lint.txt). Basedpyright passed on the seven source/prompt-test files, **0 errors, warnings or notes**. [Output](evidence/backend-types.txt).
- ESLint passed on all changed frontend/e2e files. [Output](evidence/frontend-lint.txt).
- Native profile lint passed against a disposable data/database root. [Output](evidence/profile-lint.txt).
- React Doctor scoped changed files: **100/100, no issues**. [Output](evidence/react-doctor.txt).
- The two pre-existing Web route locale expectations reported in stage 7 are now aligned explicitly with English. Only the expectation changed; route behavior and cause assertions remain intact. The full route-test file passed **24 cases** (3.64s), and types passed with zero diagnostics. Tests/lint/types are captured separately: [tests](evidence/assistant-routes.txt), [types](evidence/assistant-route-types.txt).
- Independent standards and spec reviews found no remaining actionable source defect. These reviews establish wiring consistency, not guaranteed model or spoken-audio behavior.
- [Scope evidence](evidence/scope-check.json) compares the cumulative worktree state before this authorization against current tracked content, preserving the earlier uncommitted stages and all unrelated files. Existing main-checkout frontend dependencies were reused through a temporary symlink, removed after checks; no manifest or lockfile was changed.

The first backend run found three obsolete expectations of source-selected language or a prohibition of any adaptation mention. Their replacements retain extraction-first, source/verbatim preservation and task/output/source ordering assertions, while checking the approved fixed output split. [Initial evidence](evidence/backend-initial.txt). The first page run collected old saved-locale/switching expectations before the test update; the final 55-case selection uses the new authorized contract. [Initial page output](evidence/pages.txt). Earlier passing selections overlap later runs and are not added to the authoritative totals.

The new ADR is shown with intent-to-add because the user’s global Git ignore excludes new `docs/adr` files. No source content was staged for a commit; no commit was created.

## Boundaries

No source/creative-language migration, current model/endpoint selection, credential/authentication change, installed host-skill change, live process restart, paid model/media request, ASR quality evaluation, commit or push was performed. Backend locale APIs and original queued-message metadata remain compatible. Source policy changes do not certify already-running clients as refreshed or assert editorial acceptance of existing videos.

The broader page screenshot suite retains historical localized fixtures; the executed browser selection validates the new language policy at all registered widths, not every region screenshot or every page interaction. No screenshot baseline was rewritten to conceal a discrepancy.
