# Native framework boundary: staged implementation plan

> Subsequent fixed-language behavior changes were withdrawn. [Rollback results](../fixed-language-policy/rollback-results.md) restore the language baseline while preserving stages 0-7. The independent English Web-error test expectation is retained; historical stage-7 test results below remain unchanged.

Status: stages 0-7 completed locally at the user's request, without a commit. Final integrated validation: 1,472 passed and 2 pre-existing test failures reproduced on the base revision; current host/configuration readiness remains separate. See [stage-7 results](stage-7-results.md). See [stage-6 results](stage-6-results.md). See [stage-5 results](stage-5-results.md). See [stage-4 results](stage-4-results.md). See [stage-3 results](stage-3-results.md). See [stage-2 results](stage-2-results.md). Prepared 2026-11-09 against `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. See [implementation results](stages-0-1-results.md). No credentials, host configuration or production artifacts were changed. The pre-existing skill-disable edit was preserved as evidence before authorized package retirement.

## Outcome and authoritative inputs

Codex operates externally through the official ArcReel skill and MCP. Original requirements, supplied inputs, authorized feedback and permission scope enter through supported interfaces. Native production decisions, state, admission, generation, review and editing remain governed by ArcReel, including the official skill's direct next-action route. Session delegation remains supported; it is not an exclusive mandatory route.

Evidence: [scoped recommendations](../../audits/2026-11-09-framework/change-scope-and-side-effects.md), [consolidated dispositions](../../audits/2026-11-09-framework/consolidated-dispositions.md), [R10/R11 reproductions](../../audits/2026-11-09-framework/r10-r11-isolated-reproduction.md), [expanded review](../../audits/2026-11-09-framework/expanded-scope-review.md), and [R12 reproduction/source analysis](../../audits/2026-11-09-framework/expanded-runtime-review.md).

Preserve ADR 0087's shared declarations/handlers and host-envelope differences, ADR 0091's action admission rather than a compulsory stage chain, and ADR 0122's language/history policy. R12 must retain ADR 0102's spawn-time pricing basis, token/catalog reference-cost semantics and distinction from SDK price estimates. It must not substitute a model preset or absence of a key for established authentication-route facts.

## Protected behavior and explicit exclusions

Every stage preserves:

- pt-BR creative content, English technical instructions, supported localization and saved preferences; no translation/regeneration of existing work.
- RafaCena branding, native subscription text/backend/launcher, language-context/snapshot policy and original native creative workflow.
- Project/session histories, native tasks/provider checkpoints, media bytes, selected versions, applied measured timing, reference-cost/usage records and historical permission/receipt evidence.
- Official skills, shared MCP tools, Web capabilities, native confirmation/admission/idempotency/recovery, and Gemini MIME/accounting/retry/output-limit safeguards.

No paid media/model request, real ASR, authentication attempt, host skill installation, connection setup, live process restart, data migration or production repair is required or implied. Do not add another Codex director, preflight gate, stage table, financial engine or reviewer. A source change that would expand this scope must be separately justified before implementation; do not silently weaken these invariants to make tests pass.

## Separation from the configuration investigation

| Owner | Work included | Work excluded / coordination boundary |
|---|---|---|
| This implementation plan | Repository instruction retirement; shared tool contracts; read/persistence behavior; upload transaction; code-level route/pricing consistency; isolated regressions. | No selection/change of current models, credentials, endpoints, project settings or auth state. |
| Parallel configuration investigation | External official-skill installation/discovery, Codex MCP connection, saved/effective settings and precedence, live launch/auth readiness, subscription/API classification of the current process, Settings warning diagnosis. | Its observations do not automatically authorize this worktree to alter credentials or infer current billing from synthetic reproductions. |
| Shared-source coordination | `server/media_tools/workflow_access.py`, `server/agent_runtime/options_assembler.py`, `lib/config/service.py`, `lib/config/env_keys.py`, native subscription guards and corresponding tests. | Establish one editor/integrator per overlapping file before implementation; exchange changed paths, source revision and non-secret contract conclusions. Do not run conflicting edits in separate worktrees and discover them only at merge. |

R07 changes the automated tool contract, not live saved grids. R12 fixes a code-level inference shown by synthetic tests; it does not require the live configuration investigation to finish. If that investigation changes the same contract or source, reconcile ownership before the overlapping stage, continuing independent stages in the meantime. Claims about current connection/auth readiness remain with that investigation. Installed copies of the old custom skill must be reported to that owner; repository retirement alone cannot certify host retirement.

## Stage 0: freeze scope, ownership and preservation baseline

**Work:** when implementation starts, record current HEAD, status and relevant diffs in the reused worktree. Compare drift from this plan without resetting concurrent edits. Confirm W01-W08/R07-R12 locations and ownership of shared files. Prepare isolated fixtures containing pt-BR dialogue, legacy/current scripts, supplied references, existing measured timing and both MCP hosts. Reuse existing audit evidence; never copy private credentials or production projects into committed fixtures.

**Checks:** source/reference inventory and review of applicable standards; no application startup or full test gate. Confirm reproduction source imports/fixtures remain valid before promoting them into focused regression coverage.

**Acceptance:** agreed file ownership for overlapping work; every finding mapped to a later stage; concurrent skill edit accounted for; protection/exclusion list intact. No need to block this stage on live setup/configuration answers.

**Stop condition:** unexpected drift touching production semantics or unidentified ownership is resolved at the affected seam before edits there, without discarding work or expanding into current configuration.

## Stage 1: retire the extra instruction workflow coherently

**Coverage:** W01-W08, including R01/R02/R04/R05/R08. One coherent instruction change set; no blanket commit revert.

**Work:**

1. Remove the custom director package from active repository skill discovery and retire its mandatory helper/protocol. Preserve provenance in Git/history and existing receipts; do not publish private records.
2. Retire only tests/imports that exclusively execute the removed helper; reconcile active references. Preserve native recovery tests and historical documentation clearly labeled as historical.
3. Remove universal configuration/accounting calls, added blanket image quotation, broad optional-reference policy and controller attribution from all three profiles.
4. Remove mandatory ASR acceptance/handoff and repair dependent prose. Preserve optional timing-correction mechanics and native first-round visual review.
5. Remove the shared cost-tool quote-before-paid directive together with profile/skill occurrences. Preserve native video preview/consent, user limits, unknown prices and factual evidence limits. Do not move these deleted obligations into the official external skill.

**Validation:** review all 16 profile clauses against the before/after diff and original W matrix; run `scripts/lint_agent_runtime_profile.py` via its documented entry and relevant profile manifest/materialization tests. Inspect final rendered tool descriptions on both hosts. Search for active helper paths/imports, explicitly distinguishing historical mentions. Avoid new brittle tests that merely assert replacement prose verbatim.

Existing test seeds: `tests/unit/lib/agent/test_profile_manifest.py`, `tests/unit/lib/agent/test_profile_translation_lifecycle.py`, `tests/unit/scripts/test_agent_profile_lint.py`, `tests/integration/server/routers/test_projects_agent_profile.py`, and affected host contract tests. Select actual cases according to changed files and `docs/agents/testing.md`.

**Acceptance:** active repository discovery/imports no longer depend on the director; every specified instruction occurrence is retired; all modes still materialize; official direct-tool/session routes and native confirmations remain available; no project/history/artifact mutation. Host-installed-copy retirement remains separately tracked, not falsely marked complete.

## Stage 2: align MCP permissions and response guidance

**Coverage:** R07 and R09. Shared declarations remain the single source for both hosts.

**Work:**

- R07: give configure_project an explicit supported automated-field contract, excluding grid_storyboard for both hosts until separately designed native user-authorized MCP semantics exist. Preserve Web Settings and project creation's existing separate contract. Reject forbidden field presence, including false/null, before changing any other supplied setting; do not silently ignore or partially apply.
- R09: describe immediate preview versus actual submitted-batch polling correctly. Retain long_task semantics, current envelopes, external handle behavior and embedded waiting. No preview task/fake batch/new queue.

**Focused regression coverage:** both host schemas and invocation paths; rejection of true/false/null grid fields leaves all other settings untouched; normal omitted/null/value semantics for supported settings including pt-BR; Web user grid behavior unchanged. For edit preview, assert quote/no batch/no submission; for actual generation, retain remote handle and embedded wait contracts. If changing the generic long-task note, cover the existing grid list-only preview as another affected consumer.

Test seeds: `tests/integration/server/test_workflow_access.py`, `tests/integration/server/test_remote_mcp.py`, `tests/integration/server/agent_toolset/test_host_consistency.py`, `tests/integration/server/media_tools/test_image_edits.py`, relevant project Settings/grid tests.

**Acceptance:** no automated grid bypass or partial settings write; no false polling promise; real generation/waiting and Web grid capability retained. Intentional schema restriction documented without resetting stored settings.

## Stage 3: make diagnostic script reads non-persistent

**Coverage:** R10a + R10b as one fix, then R10c and R10d as narrow subchanges. Do not implement four competing read abstractions.

**Work:**

- Costs: use native load_script_readonly, preserving in-memory compatibility and estimator inputs. Eliminate the reproduced migration-writing worker after cost-handler cancellation.
- Edit preview: use the non-writing reader only for preview=true, retaining actual editing's existing transaction behavior and shared validation/builders.
- Storyboard quotation: add a narrowly scoped read-only-script option to the existing planner/loader. Keep existing default behavior for generation/Web callers; do not duplicate planning logic or globally switch native readers.

**Focused regression coverage:** legacy/current scripts, pt-BR dialogue and durations; cost/target/skip/pricing parity; unchanged script/project bytes for consultation and preview; no batch/provider submission. Controlled cancellation must produce no later script write, without asserting that a thread is forcibly stopped. Mismatched storyboard route/skeleton is refused without migration; valid reference_video remains rejected before script loading. Real edit/generation paths retain existing migration/admission and supported submissions. Use mocked/fake provider boundaries, not actual generation.

Test seeds: `tests/integration/server/test_workflow_access.py`, `tests/integration/server/media_tools/test_image_edits.py`, `tests/integration/server/services/admission/test_storyboard_batch.py`, `tests/integration/server/services/admission/test_cost_estimation_service.py`, `tests/integration/lib/script/reference_video/test_reference_video_duration_migration.py` and the retained R10 reproductions.

**Acceptance:** successful and refused diagnostics do not persist the reproduced script migration; results retain compatible semantics; actual native production still supports legacy data. No changes to source text, timing or saved model selections. Snapshot estimates are not reservations or guarantees of later admission.

## Stage 4: make MCP character-image upload transactional

**Coverage:** R11; keep unrelated character-audio/style/Web behavior stable.

**Work:** reuse the native byte+metadata transaction pattern (`install_character_reference_audio` / `_update_project_with_files`) for the MCP existing-character image guarantee. Under the same project transaction as deletion: resolve/recheck host, install reference bytes and update metadata with rollback. Normalize/validate through existing services; do not add nested acquisition of a lock already reacquired by the old setter.

**Focused regression coverage:** the original deterministic race with real native deletion; upload-first and deletion-first orderings; initially missing host; valid replacement; failure after staging/install; concurrent same-target uploads. Assert coherent success or refusal, no recreated character, no orphan from the refused request and preservation/restoration of prior bytes/pointer. Test cancellation settles started native writes. Blind unlink of a stable filename is not an acceptable rollback.

Test seeds: `tests/integration/server/test_workflow_access.py`, `tests/integration/server/routers/test_files_router.py`, relevant ProjectManager transaction/deletion tests and the retained R11 reproduction. Keep Web missing-host semantics explicitly exercised if the shared helper is touched.

**Acceptance:** success has registered owner and file at its commit point; later native deletion can legitimately delete it. Concurrent refusal/failure does not destroy a previous or another upload's reference. Existing Web, audio/style upload and deletion/trash contracts preserved.

## Stage 5: align authentication-route facts and zero-price classification

**Coverage:** R12. This is a native code correction, not current auth setup or Codex production policy.

**Work:** in the new no-stored-key/zero-price branch, refuse incompatible enabled inherited cloud modes before starting inference. Use a shared native route definition consistent with the subscription backend. Do not silently replace an explicitly selected cloud route, implement new cloud-provider support, infer route from a model preset, or use SDK total_cost_usd for settlement. Preserve clean subscription behavior, configured API paths, token/catalog reference costs and the spawn-time pricing basis.

**Focused regression coverage:** real environment construction with synthetic Bedrock/Vertex/Foundry values and intercepted SDK spawn; conflict is rejected before inference, not merely assigned a different unsupported price. Cover actual enabled/disabled flag semantics, clean no-key subscription, configured API credentials and retained injection-time pricing. Test launcher/non-launcher construction without real processes/auth/secrets. Verify no automatic paid fallback or unconditional auth-status call was inserted per production action.

Test seeds: `tests/unit/lib/config/test_anthropic_env_dict.py`, `tests/unit/server/agent_runtime/test_options_assembler.py`, `tests/unit/lib/backends/text_backends/test_claude_subscription.py`, related accounting characterization tests and the retained R12 reproductions. Coordinate any env_keys/service/options edits with the configuration worktree before changing them.

**Acceptance:** contradictory route/zero-price state cannot reach inference; normal supported subscription/API paths retain behavior; actionable native errors can be relayed through MCP. No claim of verified current login or actual historical underbilling, no credential changes, no rewriting historical usage.

## Stage 6: clarify speech-inspection persistence without rewriting it

**Coverage:** R10e and preservation of previously applied measured timing.

**Work:** retain native materialization; clarify model-facing parameter/tool documentation and testing documentation that apply_timing=false prevents applying new measured timing, not all presentation/subtitle/manifest writes. Explain that ASR unavailability may be returned after successful materialization. Preserve source-bound policies, existing applied timing, evidence limits and no-paid-ASR fallback. No second materializer, zero-write speech API or new mandatory production stage.

**Validation:** reuse existing isolated ASR-available/unavailable/content-stability evidence while sources remain unchanged. Run affected speech contract tests and measured presentation/read/render tests if descriptions/schema or consumers change. Add only meaningful missing regression assertions, such as existing measured timing surviving an unavailable inspection; do not infer zero filesystem activity from stable hashes.

Test seeds: `tests/integration/server/media_tools/test_speech_review.py`, `tests/integration/server/services/presentation/test_presentation_read_model.py`, `tests/integration/server/services/presentation/test_timeline_final_cut.py`, `tests/unit/lib/speech/test_audio_review.py` and relevant speech-presentation tests.

**Acceptance:** no mandatory ASR restored; canonical speech/media and prior eligible measured timing retained; no new measured timing applied when false; contract matches writes on failure/success. Local render fixtures verify mechanics, not editorial/ASR quality.

## Stage 7: integrate, verify preservation and close evidence

**Work:** review combined diff and cross-stage references against the protected baseline. Keep repository-owned maintenance prose in English and preserve functional/localized literals. Reconcile any actual source overlap with the other worktree, without importing its credential or configuration changes. Update audit statuses only for work actually completed, with exact checks and residuals.

**Checks:** choose changed-file/domain validation under `docs/agents/testing.md`; reuse passing results for unchanged sources. Beyond stage regressions, exercise native session send/retry/question/interrupt with fake SDK, both host contracts, pt-BR prompt/language handling, existing measured render, and Gemini no-duplicate-submission/accounting cases when the integrated diff can affect those consumers. Source/instruction scan confirms no removed prerequisite was relocated into Codex. No automatic full gate, paid evaluation or UI/browser run solely because a commit/PR is prepared. If actual frontend behavior/types change beyond this plan, apply the corresponding type/consumer/UI checks rather than silently skipping them.

Existing integration seeds include `tests/integration/server/test_session_mcp.py`, `tests/unit/lib/prompts/test_brazilian_content.py`, `tests/unit/lib/generation/test_generation_queue_client.py`, `tests/integration/lib/generation/test_restart_recovery.py` and targeted Gemini tests.

**Final acceptance:**

1. All eight removals are accounted for at every active surface, with official skill/MCP access retained and no substitute external harness.
2. R07/R09/R10b/R11/R12 have targeted passing regression evidence; R10a/c/d/e contracts match their chosen implementation/documentation. R10a+b is recorded as one change, not double-counted success.
3. Protected language/content/settings/history/media/version/timing behavior remains covered by appropriate tests. No unrelated product customization, snapshot policy or provider correction reverted.
4. Host configuration/auth verification remains separately owned and visibly pending when not done. Repository-only retirement is not mislabeled end-to-end host readiness.
5. No unrequested paid operation, live restart, mass migration, historical cost rewrite, direct production repair or production data mutation occurred.
6. Report distinguishes reference costs/usage records from provider invoices, successful tests from live-model compliance, and successful render from editorial acceptance.

If an acceptance check fails, stop integration of the affected unit and correct it; do not delete the failing reproduction or reset saved data. Whole source-change rollback is possible by reverting the isolated unit in Git; never roll back production files/DB as an implied step. Do not re-enable the retired director as a workaround or silently reopen a paid submission path.

## Coverage and execution order

| Findings | Stage | Dependency |
|---|---|---|
| W01-W08 / R08 | 1 | Scope baseline; obsolete helper imports/tests retire together. |
| R07, R09 | 2 | Baseline; Stage 1 removes shared-description workflow first. |
| R10a + R10b, R10c, R10d | 3 | Baseline; separate subchanges with shared native contracts. |
| R11 | 4 | Baseline; transaction/deletion fixtures available. |
| R12 | 5 | Shared-file ownership resolved with configuration investigation; no live setup dependency. |
| R10e | 6 | Stage 1's optional-use wording; preserve Stage 3's distinct script-read contracts. |
| All protections / integrated evidence | 7 | All included source units checked; external readiness kept separate. |

The recommended order is 0 through 7. These are reviewable implementation units, not new production stages or a requirement for one PR per row. No concurrency or new worktree is prescribed; overlapping files should be edited serially by their agreed owner.

## Evidence already available versus future work

Historical isolated results: 69 adapter tests; 13 R10/R11 reproduction cases; 53 expanded-review cases; 3 R12 pre-spawn cases passed as recorded in their audit reports. Some reproduction cases intentionally assert the existing defect. Their passing status is not evidence of a fix: promote/adapt them into regressions asserting the desired invariant, demonstrate the current failure where appropriate, then verify the actual correction.

No tests were run to create the initial plan. The subsequent stage-1 test run is recorded in [the results](stages-0-1-results.md). The completed stage reports list commands, source revision, cases run, isolation and unresolved failures. Any later validation must retain those distinctions. Reuse existing unchanged-feature evidence proportionally; do not run real providers to compensate for inadequate isolated coverage. Real-model creative quality, live compaction, actual connected-client disconnect propagation and current subscription availability remain outside what these isolated checks establish.
