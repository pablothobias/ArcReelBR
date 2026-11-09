# Refactoring and agreement register

> Final local implementation status: stages 0-7 are complete without a commit. [Stage-7 review and results](../../plans/native-framework-boundary/stage-7-results.md) accounts for all 17 entries, complementary safe R12 error propagation, 1,472 passing cases and two test failures reproduced on the base. Earlier stage-specific pending statements below are historical. Installed-skill/MCP/auth readiness remains separately owned.

> Current consolidated checklist: [reviewed dispositions](consolidated-dispositions.md). It distinguishes removals, confirmed adapter corrections, contract decisions and preserved product behavior. Historical entries below do not override current dispositions.

Started: 2026-11-09. Purpose: retain the decisions emerging from the investigation for later refactoring, removal or updates. This register does not authorize implementation, production, spending or configuration changes.

## Status rules

- **Confirmed finding**: supported by inspected evidence; not agreement to change it.
- **Proposed**: agent recommendation awaiting the user's decision.
- **Agreed**: the user has explicitly accepted the particular change and scope.
- **Implemented**: change completed with its actual verification recorded.
- **Withdrawn**: a previous recommendation was not justified by sufficient evidence; it is not pending implementation.

The user requested this ongoing register. The architectural boundary A01 below is explicitly agreed. The user authorized the responsibility review and this documentation update, not implementation of the dispositions below. Recommendations must not be silently promoted to agreements. Preserve the distinctions between native capability, external access and instructions when implementing any later decision.

## Agreed architectural boundary

### A01: Codex is an external production client; preserve product customizations

**Status: agreed by the user's explicit clarification on 2026-11-09.**

For production, Codex acts outside ArcReel and connects through the project's own tools. It must not take over the framework's internal production responsibilities. The project owns its production workflow and decisions; Codex supplies the user's requirements/inputs, carries authorization, communicates through supported interfaces and observes/reports native results.

The user explicitly distinguished this responsibility boundary from the optimizations and customizations already made to the product. Do not treat all local changes as an external harness to remove. Brazilian Portuguese creative-content support is an explicit example that must be preserved.

Historical interpretation, now qualified by A02 below: apply this boundary to the previously selected embedded-Agent delegation architecture: use the native session/tools rather than creating an external creative planner, reviewer, version selector, editor, production state authority or direct file/database repair path. Supplying explicit user feedback or requested input through those tools remains external client activity.

This is a production responsibility decision. It does not prohibit separately authorized development work on the product. It also does not constitute approval to remove a particular skill, revert a commit, discard other customizations, configure MCP, generate media or spend money. Identify each conflicting mechanism and its concrete effect before proposing its disposition. The user's description of the framework as validated does not replace verification of a particular feature or editorial result.

**Disposition criterion:** keep native product capabilities/customizations and supported access adapters; assess mechanisms that transfer internal production ownership to Codex against A01. Classify by responsibility and behavior, not by whether Codex authored the implementation or whether a file was inherited.

### A02: official skill and MCP are the exclusive production interface

**Status: explicitly required by the user on 2026-11-09.** This clarifies A01 and supersedes the agent-added assumption that every operation must pass through `send_agent_message`. The official public skill itself permits execution of native `next_action` through MCP. That supported route is not an unauthorized second harness.

Remove locally imposed workflow/directing rules under the interference criterion, without requiring proof of an editorial regression. Preserve product customizations and the underlying tools independently from custom instructions that make their use mandatory. The current detailed list is [workflow-interference-review.md](workflow-interference-review.md), W01-W08 and all 16 CLAUDE clauses. Earlier ownership-only or harm-only recommendations are historical and superseded where they conflict with this review. Only list preparation is authorized; no source removal has occurred.

## Current recommendations

| ID | Area | Confirmed finding | Recommended disposition | Status |
|---|---|---|---|---|
| R01 | `edit-video` speech review instructions | The local edit adds mandatory per-unit ASR before voice/timing acceptance and a report handoff, absent from the parent editing flow. | W08: remove the mandatory general-stage insertion and adjust dependent references. Preserve speech review/measured timing as product capabilities for explicit supported requests and preserve factual evidence limits. | Implemented locally for stage 1 only; 1,178 selected tests and profile lint passed. See the stage-0/1 results. No host setup or later-stage correction performed. |
| R02 | `generate-assets` quotation instruction | The local edit inserts quote_assets before every paid batch; the parent asset workflow has no separate mandatory quotation step. | W04: remove the added blanket quotation requirement from the skill/profiles and shared cost-tool description. Keep quote tools, financial evidence, user limits and original native confirmation/video-preview rules. | Implemented locally for stage 1 only; 1,178 selected tests and profile lint passed. See the stage-0/1 results. No host setup or later-stage correction performed. |
| R03 | Drama/narration `video-workflow` project creation | Only the entry instruction changed: project creation may happen through Web or external `create_project` before the session. Content/generation modes remain immutable. | Retain. This enables an existing entry route and does not introduce another production plan. | Proposed retain; not a current refactoring candidate. |
| R04 | `CLAUDE.*.md` delegated production section | Ownership alone did not detect interference: locally required native calls/policies also alter the official sequence. All 16 clauses have now been compared with the parent flow. | W03/W04/W05/W06/W07: remove universal project/config preflight, blanket image quotation, compulsory accounting calls, broad optional-reference policy and custom controller-ceiling attribution. Preserve native routing, capability/API semantics and original permission safeguards. | Implemented locally for stage 1 only; 1,178 selected tests and profile lint passed. See the stage-0/1 results. No host setup or later-stage correction performed. |
| R05 | Old `.agents/skills/direct-brazilian-production/` director and policy package | Codex creative ownership and custom per-action reservation/recovery workflow are independent playbooks beyond the official skill. | W01/W02: retire the active directing skill and its mandatory helper workflow without building a replacement harness. Preserve historical receipts and actual user permission/financial evidence. | Implemented locally for stage 1 only; 1,178 selected tests and profile lint passed. See the stage-0/1 results. No host setup or later-stage correction performed. |
| R06 | Codex production-client behavior | The official public skill itself supports executing native next_action through MCP; a session-message-only rule would incorrectly restrict that route. Derived external briefs/creative plans remain separate interventions. | Follow only the official skill and MCP in production, including its supported direct-tool or session routes. Forward requirements/authorized feedback faithfully; do not add a private planner, gate, stage table or acceptance authority. | User criterion explicitly established; behavioral requirements recorded. No host setup or production performed. |
| R07 | MCP Settings field/host permissions | Shared configure_project inherits grid_storyboard from Web Settings and exposes it to the embedded Agent, contrary to the retained native user-only grid rule. Both host schemas accept it; the handler persistence route has no host-specific field exclusion. | MC01: align adapter permissions with the native restriction while preserving Web grids and supported MCP settings. Do not silently rewrite the native restriction to justify the widened adapter. | Implemented locally in stage 2; 1,150 distinct cases passed plus Ruff/format/types. See stage-2 results. No live configuration or later-stage work. |
| R08 | MCP tool descriptions as workflow instructions | The shared get_project_costs description tells callers to quote before paid actions; removing CLAUDE/skill prose would leave this added instruction visible in both hosts. | MC02: extend W04 removal scope to the blanket pre-action directive in the declaration. Preserve tool semantics, financial evidence and inherited preview/permission rules. | Implemented locally for stage 1 only; 1,178 selected tests and profile lint passed. See the stage-0/1 results. No host setup or later-stage correction performed. |
| R09 | Remote image-edit preview contract | edit_images is always marked long_task, so the remote description promises a generation_batch to poll even when preview=true returns an immediate quote without a batch. | MC03: distinguish preview response and real submitted-batch polling in metadata/guidance. Preserve the preview and actual native execution. | Implemented locally in stage 2; 1,150 distinct cases passed plus Ruff/format/types. See stage-2 results. No live configuration or later-stage work. |
| R10 | Persistence/cancellation in diagnostic operations | Isolated reproductions confirm legacy migration writes in costs/preview; the cost caller can finish cancelled before its worker writes. Speech inspection materializes artifacts even with apply_timing=false and unavailable ASR. Storyboard quotes reject valid reference routes before loading; migration on rejected quotes was reproduced only with a mismatched route/skeleton. | MC04/R10a-e: adjust the cost cancellation boundary; clarify diagnostic/preview persistence contracts. Keep native migrations, materialization, optional speech and pt-BR. Materialization itself is not a proven regression or a removal target. | R10a+b/c/d implemented locally in stage 3: native read-only script loading, 1,263 distinct cases passed and clean lint/types. R10e clarified and validated in stage 6: inspection may materialize even before unavailable ASR; false skips new measurements and retains valid prior timing. 1,203 cases pass; native materialization is unchanged. No general zero-write guarantee or live-model claim. |
| R11 | Character-reference upload race | After the existing-host check, real native character deletion can complete before upload resumes. Upload then reports success and leaves a file without its registered character. The no-deletion control registers the reference correctly. | MC05: make the retained MCP existing-host guarantee valid through commit, with coherent refusal/cleanup while preserving Web semantics, upload capability, native deletion and supplied content. | Implemented locally in stage 4 using the native rollback-capable transaction; 1,379 distinct cases passed, including 14 new cases. No configuration/auth or stage-5 work. See stage-4 results. |
| R12 | Agent authentication-route and zero-cost inference | With no stored API key, real configuration selects Agent multiplier 0.0, but synthetic Bedrock/Vertex/Foundry mode flags survive the installed SDK child-environment merge. Three isolated pre-spawn cases passed with process creation intercepted. | Tie zero-price classification to an explicitly allowed/verified route or consistently refuse/contain incompatible inherited routes. Preserve subscription integration; do not add a Codex preflight. Coordinate launch-state verification with the separate configuration audit. | Implemented locally in stage 5: known enabled inherited cloud selectors are refused in the no-key subscription fallback; shared parser and 218 distinct cases pass with clean lint/types. Stage 7 also preserves safe typed route-conflict guidance through the MCP startup wrapper, with six before/after cases and a generic-diagnostic privacy control. Current configuration/auth readiness remains separate. |

## Evidence

- R01: `agent_runtime_profile/.claude/skills/edit-video/SKILL.md:19,27,40-42`; commit `39487c317`; `server/media_tools/speech_review.py:40-95`.
- R02: `agent_runtime_profile/.claude/skills/generate-assets/SKILL.md:14`; commit `b88d14cd0`.
- R03: `agent_runtime_profile/.claude/skills/video-workflow/SKILL.drama.md:27` and `SKILL.narration.md:27`; commit `b88d14cd0`.
- R04: `agent_runtime_profile/CLAUDE.ad.md:17-23`, equivalent drama/narration sections; commit `b88d14cd0`.
- R04 materialization: `lib/agent/profile_manifest.py:118-165` retains only the requested content-mode variant.
- Current R04 per-rule dispositions: [workflow-interference review](workflow-interference-review.md). The earlier [ownership-only assessment](claude-rule-ownership.md) remains historical; its two-adjustment-only conclusion is superseded.
- R05: `.agents/skills/direct-brazilian-production/SKILL.md:8-18,28-44` in HEAD; `scripts/policy.py:181-291,362-394`; `references/recovery-format.md:39-64`. In the current working copy, an independently added frontmatter line shifts skill body locations by one. The skill's role wording and per-action workflow remain present.
- R06: session `7409a38e-b7b2-4177-9064-bbaae6585c9a`, root seq 2 and 98 (derived original-adaptation brief, provisional duration and external creative constraints), 186/209 (later faithful-adaptation correction/delegation). See the source-qualified reconstruction. Do not attribute every external message literally to the human or declare every historical intervention unauthorized.
- The preceding conversation inspected the diffs against independent-maintenance anchor `a779b5d51`. Detailed findings: [responsibility boundary](codex-responsibility-boundary.md), [actual skill/MCP use](mcp-skill-usage-verification.md), and [native responsibility map](native-harness-responsibilities.md).

- R07-R11: [MCP adapter assessment](mcp-adapter-assessment.md), [schema evidence](mcp-adapter-schema-evidence.json), [session-source review](mcp-session-adapter-review.md), and [workflow-access source review](mcp-workflow-access-review.md). The central assessment records 69 isolated tests passing and limits of that coverage.

## Decision log

| Date | Decision or event | Scope |
|---|---|---|
| 2026-11-09 | User requested an ongoing record of emerging agreements for future changes. | Documentation only. |
| 2026-11-09 | Agent recommends R01 and R04 as refactoring candidates; R02 and R03 as retain. | Recommendations only. No user agreement to these changes is assumed. |
| 2026-11-09 | User requested that recommendations be checked for actual validity without assuming investment. Source recheck found that R01 already contains the proposed evidence distinctions and conditional timing application; R04 variants are selected individually and agree on ownership. Agent withdrew both refactoring recommendations. | All four items currently have a retain recommendation. No refactoring work or investment is authorized or justified by these findings alone. |
| 2026-11-09 | User explicitly clarified that Codex belongs outside the production framework, connecting through the project's own tools, and that product customizations such as Portuguese content are excluded from blanket removal. Recorded A01 as agreed. | Architectural production boundary and explicit preservation of Portuguese content; no concrete removal, implementation or spending approval. |
| 2026-11-09 | User requested a review of local changes against A01 and an updated list without implementation. Review identified R05 as the concrete source/instruction package with mixed responsibility and R06 as the corresponding operational adjustment. Product capabilities and access adapters remain retain recommendations. | Documentation review completed. No source, host settings or production changes. |
| 2026-11-09 | User challenged the apparent inconsistency between acknowledging modified native profiles and recommending retain. Agent corrected R04 to separate architecture ownership from behavioral compatibility. | No duplicated runtime controller was established in these profiles; functional changes are confirmed and potential regression is not ruled out. No unconditional safety or retain decision is implied. |
| 2026-11-09 | User requested review of each rule added to the three CLAUDE mode profiles. All 16 identical clauses were classified by owner. R04.08 and R04.15 received narrow wording proposals; native tool/permission rules and product customizations remain preserved. | Only the register and detailed audit were updated. No runtime instruction, code, configuration, production or authorization was changed. |

## A01 review: scope, preservation and exclusions

The review used local change history after independent-maintenance anchor `a779b5d51`, the specific personal-fork implementation commits, current source and the recorded native production session. The broad diff contains 860 changed paths, including branding and other repository changes; this is not a claim of a new correctness review of every line in that diff. Responsibility-bearing source changes were checked at their owning seams, with prior source evidence reused where unchanged. No fresh upstream equivalence or universal quality claim is made.

### Product changes to preserve

| Change | Why it does not transfer production ownership to Codex | Source / provenance |
|---|---|---|
| Brazilian Portuguese content and English technical prose | Native content-language normalization, speech-rate handling and prompt policy; not external creative supervision. Portuguese content is explicitly protected by A01. | `7b012052e`; `lib/infra/content_language.py:7-27`; `lib/prompts/prompt_rules/content_language.py:6-17` |
| Subscription-backed internal text | Implements the native TextBackend seam. The isolated SDK request has no tools/MCP/skills/plugins and one turn; it does not become another production Agent. | `ecd6ead43`; `lib/backends/text_backends/claude_subscription.py:157-180` |
| Session MCP | Uses the existing running AssistantService and native session/question/queue operations. This is how an external client can delegate, not a second runtime. | `5e6626de5`; `server/session_mcp.py:71-75,100-204` |
| Settings/reference/quotation/usage MCP | Reuses native validated settings, upload services, batch planners and estimators. | `b88d14cd0`; `server/media_tools/workflow_access.py:45-121,252-300` |
| Native speech evidence and measured subtitle timing | Runs in the native handler and presentation transaction; preserves explicit limits for acting/lip sync. | `39487c317`; `server/media_tools/speech_review.py:66-95`; `lib/speech/audio_review.py:153-159` |
| Gemini output/MIME and accounting fixes | Native backend correctness and charge-evidence handling; no external production planner. | `81c6740f1`, `95cbaf27a`; `lib/backends/image_backends/gemini.py:214-231,305-312`; `lib/backends/data_uri.py:21-54` |
| Local subscription launcher, English presentation and RafaCena identity | Development/runtime setup and product presentation; no creative stage ownership. | `ffdb580b0`, `401488f40`, `f997d91b8`, `037c5aa30`; `scripts/run_local.sh:78-111,152-174` |
| Offline audio/AV diagnostics and fixtures | Write separate evidence/fixture directories, not canonical production state. The validator sets `automatic_quality_pass=False`; no automatic native production gate was found. Keep as research tools, not a replacement quality authority. | `e98612c83`, `62ec64a23`; `scripts/validate_av_review.py:154-169,256-288`; `scripts/inspect_audio_evidence.py:128,217-218`; `scripts/build_av_review_fixtures.py:26-29,69-101` |

This preservation table classifies product capabilities, not immutable adapter implementations. A02 and R07-R11 qualify the earlier A01 assessment: retain the capabilities while removing imposed workflow instructions and correcting the confirmed adapter defects. No claim is made that each feature is defect-free or every optimization proven valuable.

### What R05 removes from the operating model, and what it preserves

The offending mechanism is the external director role and its per-action production workflow, not the mere existence of a private permission record. `policy.py` does not generate media or repair the database automatically. Its local lifecycle is documented as snapshots, and financial checks can legitimately constrain an external client's permission. Retiring the package does not justify discarding those financial obligations or rewriting settled records.

The concrete conflict is the skill's assignment of adaptation/review to Codex and requirement that Codex prepare and delegate each exact production candidate. Its helper/recovery format are retirement scope because they support that obsolete operating mode, not because every state field is inherently wrong. Do not create a replacement policy engine merely to reduce the number of fields. Preserve source, evidence and accounting history according to the eventual archive/removal decision.

An unstaged `disable-model-invocation: true` has appeared in the working copy from concurrent work. It was not made by this review. It changes invocation eligibility, but does not remove the conflicting body or the historical helper instructions. No claim of complete retirement or automatic invocation is made; confirm host behavior if a later implementation relies on that flag.

### Not new removal candidates

- The public `skills/video-workflow` and `setup-arcreel-skills` are supported inherited interfaces. Do not remove or rewrite them just because an external caller can use them. Follow the official skill through its supported direct-tool or session route; do not require embedded-session-only delegation or introduce a second independent driver.
- The absence of a persistent ArcReel MCP connection/public-skill installation in the earlier verified Codex host is an integration gap, not duplicated native production logic. Setup would be a separate authorized task using the project's existing connection path, not a new harness. No installation or credential change is included here.
- The old planning README already labels its former role division historical. Preserve that evidence. No blanket documentation purge or issue mutation is justified. If a future active entry point presents an old plan as current authority, update that entry point with direct evidence.
- Native acceptance problems remain native quality work. The known seating error was detected and accepted by the native reviewer. A01 does not justify moving review back to Codex or claiming that retiring R05 will fix that defect.

### Acceptance criteria for a later authorized change

1. The old directing package no longer serves as current production instructions; references from active entry points are reconciled. Historical receipts and permission/spending evidence remain intact.
2. Codex communicates through supported native interfaces with one selected production owner. It forwards requirements and authorized feedback without silently converting its own creative decisions into user requirements.
3. The native Agent remains responsible for scripts, prompts, reviews, versions, correction choices and editing. Job state, provider recovery, selected artifacts and actual usage remain native authorities.
4. Portuguese creative content, existing histories/artifacts and the native capabilities/access adapters listed above remain preserved. Verify changes proportionally if implementation is later authorized.
5. No new production, configuration change or expenditure follows from this register. Permission tracking remains scoped to the user's actual authorization.

## Historical reassessment of the withdrawn recommendations

The dispositions in this section predate A02 and are superseded where the current workflow-interference review differs. They are retained as decision history.

R01's prior proposal conflated a possible future optimization with an established defect. `review_speech` does transcribe when called, but this audit did not establish harmful redundant execution, quantify an operational bottleneck, or show that the current acceptance trigger causes an incorrect result. The distinction between word recognition, timing and audiovisual acceptance is already present in the skill. The last production's limited acceptance evidence remains a real observation, but does not establish a need to refactor these instructions rather than follow them.

R04's original source-deduplication proposal conflated repetition in mode-specific files with multiple simultaneous controllers. `profile_file_map` selects one mode variant, and the sections explicitly preserve native creative ownership. That observation addresses duplicated orchestration only. It does not demonstrate that inserting these new instructions leaves the Agent's choices, calls or confirmation behavior unchanged.

The added global-authorization interpretation, configuration checks, optional-reference wording, quotation/accounting calls and controller ceiling are actual behavioral policy changes. They can affect how an Agent proceeds, even when all business tools are native. Their stated scope and source integration were inspected, but no controlled before/after production comparison isolated their effects. Therefore regression is neither established nor ruled out, and successful tool tests are insufficient to certify equivalent editorial behavior. The last production's defects do not by themselves prove causation by these clauses either.

The previous blanket retain wording was too strong. The subsequent per-rule review now provides two narrow semantic proposals rather than a broad retain/removal verdict; their runtime compatibility still has not been established by controlled before/after production. The user's explicit preservation of Portuguese content does not automatically approve every orchestration-related profile clause; those are separate modifications. No new shared-source mechanism, rollback, model evaluation, estimate or implementation is authorized by these documentation updates.

## Implementation boundary

No source or configuration was changed while creating this register. A pre-existing modification to `.agents/skills/direct-brazilian-production/SKILL.md` belongs to concurrent work and was not edited or attributed by this action. Removal of skills, host setup and current provider configuration are separate items to register when discussed and agreed; they are not implicitly included in R01-R04.

## Latest decision-log update

2026-11-09: the user restated that Codex must use exclusively the official skill and MCP and requested an itemized review of workflow interference without requiring proven regression. The source comparison confirmed W01-W08. R01, R02 and R04 dispositions were corrected accordingly. The user-facing criteria do not mandate a session-message-only route, since the official skill also supports direct native next-action calls. No source, skill, host configuration, service, production artifact or Git ref was changed by this update.

The current W01-W08 list supersedes the earlier statements that only two wording edits were supported or that lack of a reproduced regression justified retaining all four changes. Historical sections remain to explain the corrections; they are not the current implementation plan. R03 remains retain because it enables an already supported official MCP entry route. Factual audio-evidence limits remain retain because they do not insert another processing stage.

## MCP-adapter follow-up

2026-11-09: the user explicitly requested adapter verification for workflow interference/regression risk. The review found MC01/MC02/MC03 concrete inconsistencies or instruction changes and MC04/MC05 conditional effects/risks, recorded as R07-R11 above. Schema inspection was isolated and did not invoke handlers. The existing session/workflow-access/remote/image-edit test files passed 69 cases with one existing SQLite reflection warning; no new tests or implementation were added, and no live application/model calls occurred.

This supersedes any earlier blanket statement that service reuse makes all MCP adapters neutral or suitable to retain unchanged. The native capability preservation table concerns the underlying features, not unconditional acceptance of their adapter schemas, descriptions or side effects. In particular, full-ledger cursor guidance is conditional on full reconciliation and is not classified as a compulsory production step. Preserve original user authorization safeguards and pt-BR throughout any later authorized adjustment.

## R10/R11 reproduction follow-up

2026-11-09: user requested isolated verification without corrections. [The reproduction report](r10-r11-isolated-reproduction.md), [retained source](reproduce_r10_r11.py) and [captured output](r10-r11-pytest-output.txt) supersede the earlier pending-reproduction status for R10/R11. The final 13-case set passed with controls. R10 now separates native side effects, the handler cancellation defect and route limits. R11 is a reproduced false-success/orphan-reference defect under concurrent native deletion. No product implementation, production data or customization was changed.

## Consolidation completeness review

2026-11-09: checked all 16 profile additions, W01-W08, R07-R11 and preservation entries against the prior 25-item presentation. [The reviewed checklist](consolidated-dispositions.md) adds explicit preservation of Gemini/MIME/accounting fixes and offline diagnostics, makes active-reference cleanup explicit, qualifies Settings/upload retention and narrows reproduction claims. Four confirmed adjustment items are separate from four persistence-contract decisions. External installation/configuration remains a parallel scope. No implementation or new tests.

## Expanded discovery review after completeness challenge

2026-11-09: the prior consolidation checked known clauses/findings but did not establish discovery completeness. [The expanded review](expanded-scope-review.md) starts from an [860-path inventory](expanded-change-inventory.json), inspects additional executable seams and records review limits. It adds R12 from three isolated SDK pre-spawn reproductions and explicitly describes prompt snapshots/memory refresh, per-message language context, isolated subscription text execution/quota behavior, persistent measured-timing reuse, and Gemini retry/token-cap changes. These intentional product changes are preserved with their real effects and validation limits, rather than described as cosmetic or unchanged framework behavior. A further 53 targeted existing tests passed. No implementation, paid/live request, authentication check or current configuration mutation.

## Scope and side-effect recommendation review

2026-11-09: user requested concrete scopes for eight removals, five adjustments and four contract decisions, preserving external-only Codex access through official skill/MCP. [The scoped recommendation](change-scope-and-side-effects.md) maps all 17 entries to actions, dependencies and acceptance checks. Preferred contract resolutions are read-only native script loading for costs/preview/quote (R10a+b share one fix) and retaining/documenting speech materialization (R10e). R07 excludes user-only grid mutations from automated configure_project pending a separate explicit authority contract. R11 should reuse native byte+metadata transactions rather than late unlink. R12 should reject incompatible cloud-route classification in the no-key subscription branch instead of silently switching routes or inventing a Codex gate. Obsolete helper tests/imports are part of W01/W02 retirement; existing history/evidence is preserved. Recommendations only; no source, tests, credentials, production or configuration changed.

## Staged implementation plan

2026-11-09: user requested a staged plan with tests/acceptance, preserving product customizations and separating configuration investigation. [The proposed plan](../../plans/native-framework-boundary/README.md) maps all findings to stages 0-7, identifies shared-file ownership and the R12 code-versus-live-auth boundary, defines regression seeds/acceptance, and protects production/history. Existing audit reproductions that pass while asserting defects must become corrected-invariant regressions during implementation. Plan only: no product source, active instructions, tests, settings, auth or production changed; no tests executed for this documentation update.

## Stages 0 and 1 executed

2026-11-09: user authorized only stages 0/1 and requested results before stage 2. [The completion report](../../plans/native-framework-boundary/stages-0-1-results.md) records W01-W08/R08 implementation, retirement of exclusive helper tests, preservation of the pre-existing flag patch, and unchanged hashes for 4,712 protected tracked files. Profile lint passed and 1,178 tests passed with one existing SQLite reflection warning. No configuration/authentication/production change or stage-2+ work. All remaining contract/defect findings retain their pending status.

## Stage 2 executed

2026-11-09: user authorized R07/R09 and results before stage 3. [The completion report](../../plans/native-framework-boundary/stage-2-results.md) records common/Web request separation, restricted automated schemas plus handler revalidation, conditional batch polling guidance, 1,150 distinct passing cases and clean targeted lint/types. The public installation guide had a missed W04 quotation imperative; it was corrected with R07/R09 documentation while install/connection steps remained unchanged. 4,709 protected files are unchanged from this stage's baseline. No current config/auth/production change; stage 3 has not started.

## Stage 3 executed

2026-11-09: user authorized non-persistent diagnostics and results before stage 4. [The completion report](../../plans/native-framework-boundary/stage-3-results.md) records costs/cancellation R10a+b, preview R10c and quote R10d corrections using native readers/planner options. Default migration behavior is retained for real edits and ordinary generation. Four defects failed before correction; controls and final 1,263 distinct cases pass. 4,710 protected tracked files remain unchanged; all workflow_access members outside cost/quote are AST-identical to the stage baseline. No configuration/authentication/production changes; R11/R12 and R10e remain pending and stage 4 has not started.

## Stage 4 executed

2026-11-09: user authorized R11 and results before stage 5. [The completion report](../../plans/native-framework-boundary/stage-4-results.md) records the native character-image installer, restricted MCP upload branch, preserved Web/audio/style/deletion behavior, 14 new race/rollback/cancellation/Unicode cases and 1,379 distinct passing cases. Native transaction/deletion implementations and 4,714 protected tracked files are unchanged. No current config/auth/production mutation; R12/stage 5 remains pending.

## Stage 5 executed

2026-11-09: user authorized R12 and results before stage 6. [The completion report](../../plans/native-framework-boundary/stage-5-results.md) records native no-key route refusal, a shared selector list/parser consistent with inspected CLI semantics, preserved configured-API/subscription/accounting behavior, and 218 distinct passing cases. 4,711 protected tracked files remain unchanged. No current settings/auth/credentials, CLI login probe, provider call or historical cost rewrite. The fix covers inherited process selectors, not arbitrary CLI settings precedence; current readiness remains configuration-investigation scope. Stage 6 has not started.

## Stage 6 executed

2026-11-09: user authorized R10e contract clarification and results before stage 7. [The completion report](../../plans/native-framework-boundary/stage-6-results.md) records aligned tool/schema/skill/documentation wording, four isolated real-persistence cases covering available/unavailable ASR and valid prior timing, and 1,203 passing selected cases. Ruff, types and native profile lint pass. The handler is AST-identical and 4,711 protected tracked files are unchanged. Native materialization and eligible measured timing are preserved; no zero-write or live-ASR-quality guarantee is claimed. Configuration investigation remains separate. Changes are uncommitted and stage 7 has not started.

## Stage 7 executed

2026-11-09: user authorized integrated review, preservation checks and planned tests without a commit. [The completion report](../../plans/native-framework-boundary/stage-7-results.md) records all eight removals, five adjustments and four contract decisions. Independent standards review identified suppressed R12 guidance at the MCP startup boundary; six cases failed before its narrow typed-cause correction, then passed while generic diagnostics remained private. No other actionable review finding remained. An isolated execution of the actual launcher clean function covers inherited-selector containment without running setup/auth/services. Final selection: 1,472 passed and two Web test language-expectation failures also reproduced on main at the same base revision. These pre-existing failures are recorded, not concealed or fixed by changing product language. Ruff/format/types pass; unchanged profile checks are reused. All 4,688 regular files and 48 symlink entries outside the accumulated changed paths match HEAD. Three shared source files with the other worktree combine textually in disposable checks, but no foreign source/settings are imported or claimed functionally integrated. Configuration readiness remains separate; no commit, live process or paid operation.

## Subsequent language-stage rollback

2026-11-09: the owner authorized reverting the later fixed-language behavior changes while preserving prior customizations and completed stages 0-7. [Rollback results](../../plans/fixed-language-policy/rollback-results.md) record 22 exact baseline restorations, retained independent Web-error assertion, rejected ADR 0123 and fresh validation: 2,039 backend cases, 4,070 frontend cases and 55 language page cases passed. The generic Chinese prompt-reference conflict remains separately scoped; no new production policy, data migration or live restart was introduced. No commit.
