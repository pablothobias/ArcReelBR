# Codex and ArcReel production responsibility boundary

> Follow-up qualification: [the adapter assessment](mcp-adapter-assessment.md) identifies field-permission and contract issues plus tool-description workflow interference. Earlier keep/access-wrapper classifications are not a guarantee of adapter neutrality. Apply A02 and the current register for dispositions.

Audit date: 2026-11-09, America/Sao_Paulo. Checkout: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`, detached worktree `0372/ArcReelBR`. Scope: determine which production responsibilities the embedded ArcReel harness already owns, which Codex additions expose or extend it, and where external instructions duplicate or displace it. This is a source/history audit and responsibility assessment, not a configuration audit or implementation. Only audit documents were written.

## Assessment

There is concrete duplication of **responsibility in instructions and external decision state**, but the inspected additions do not constitute a complete replacement Agent runtime, generation queue, billing ledger or video renderer.

The principal overlap is the old Codex directing skill. It says Codex owns research, adaptation and review, directs individual actions, and maintains its own pending/review/attempt transitions. Current repository policy assigns creative planning, references, prompts, generation, review, version choice and editing to the embedded Agent instead. A different issue is the public external workflow skill: it tells its external caller to execute each native next action. That is a legitimate external-driver interface, but using it as a second production driver alongside the embedded Agent conflicts with the delegation architecture selected for this project.

The recent session/settings/reference/quotation MCP work is largely an access layer over existing ArcReel services. Local speech review is a real new capability integrated into the native system. Neither category should be discarded merely because it was implemented during Codex work.

Primary sources: `AGENTS.md:5-9`; `.agents/skills/direct-brazilian-production/SKILL.md:8-18,28-44`; `skills/video-workflow/SKILL.md:8-18`; `docs/testing/native-mcp-production.md:3-18`. The detailed native source and Git provenance map is [native-harness-responsibilities.md](native-harness-responsibilities.md).

## What is already native and what Codex is adding

| Responsibility | Native ArcReel owner | Codex behavior or retained customization | Assessment |
|---|---|---|---|
| Interpret user intent and interview | Embedded main Agent and mode profile | Old directing skill assigns research/adaptation to Codex | Overlapping creative ownership. Codex may relay user inputs or supply explicitly requested research; it should not silently replace the creative brief. |
| Choose next production step | Server workflow plan and embedded workflow skill | Public external `video-workflow` routes and executes `next_action`; directing skill reserves each candidate | Two potential drivers. Monitoring the plan is compatible; independently deciding and executing its stages alongside the embedded Agent duplicates orchestration. |
| Episode/script planning and shot structure | Native mode workflow, script generation, normalization and authoring subagents | Historical plan P4 gives Codex adaptation, scripts, direction and correction | Duplicated role, retained as historical text. No second formal-script store was established in the inspected helper. |
| References, assets and prompts | Native asset registry, reference assembly, image/script tools and Agent decisions | Codex selects/transports sources, old skill verifies frozen prompts and controls exact actions | Transport is useful. Choosing each creative reference/prompt externally is an intervention in native ownership, unless explicitly requested as an input. |
| Generation and technical admission | Shared deterministic tools, batch admission, queue, workers and provider checkpoints | External intent admission and manual per-action delegation | Native business execution remains reused. The external helper is an additional permission layer; it is not a substitute for native admission. |
| Task/session recovery and duplicate protection | SessionActor, client-key handling, queue conflicts and provider recovery | Local intent IDs, pending/completed/failed status, reuse/pause/resume decisions | Partially overlapping state. Keep authorization provenance/client keys if useful; derive actual job/provider state from ArcReel rather than infer it locally. |
| Quality review and versions | Native image/footage reviewers; main Agent chooses versions and corrections | Old skill says Codex owns review and records rejected/discarded attempts | Creative review/acceptance overlaps. Financial authorization limits can stay external without making Codex the footage director. |
| Retry policy | Native recovery handles transport; native editing skill defines correction checklist and post-regeneration comparison | Policy distinguishes initial/quality/transport attempts and hard-codes three quality attempts | Different mechanisms with overlap. Native operational recovery stays native; the user may impose a stricter spending/attempt ceiling. Old three-attempt allowance is not current authorization. |
| Budget and permission | Native quotes, unpriced flags, accounting and usage; no universal user round cap established | Codex carries user ceiling/exclusions and optionally reserves quoted exposure | Complementary responsibility. Do not remove permission controls on the assumption that native technical admission authorizes spending. |
| Timeline, subtitles and export | Native presentation, edit timelines, renderer and export tools | Historical external audiovisual diagnostics and proposed Codex correction responsibility | Native editing already exists. External analysis may add evidence; it must not become another subtitle/rendering or direct project-write path. No such automatic replacement path was identified in the inspected application entry points. |
| Actual speech evidence | New native `review_speech`, blind ASR and conditional measured timing | Earlier standalone local audio evidence and offline review validator | There was a genuine native evidence gap. The new integrated tool closes part of it; old diagnostics should stay research tools, not a parallel production gate. |
| Authentication, content language and product identity | Existing runtime/backend interfaces with local customizations | Subscription TextBackend, pt-BR policy, English defaults and RafaCena branding | Intentional behavior extensions, not another production orchestrator. Retain or assess separately against requirements. |

Native responsibility sources, exact lines and provenance are in the companion source map. External ownership and policy mechanisms are substantiated below. “Native” means implemented inside the ArcReel architecture, not necessarily inherited unchanged from upstream.

## Specific overlaps and overrides

### 1. The old directing skill contradicts current ownership

Current authority: `AGENTS.md:7` assigns creative planning, references, prompts, generation, review, versions and editing to the embedded Agent. `docs/testing/native-mcp-production.md:3` says the external client does not author a second production plan. `agent_runtime_profile/CLAUDE.ad.md:17-23` keeps the native Agent responsible for its workflow and subagents while the controller holds the financial ceiling.

Conflicting retained instruction: `.agents/skills/direct-brazilian-production/SKILL.md:8` says Codex owns research, adaptation and review. Lines 28-32 tell it to prepare and reserve a candidate and delegate that exact action before the next one; lines 42-46 supply attempt and quota-pause policy; lines 50-52 prescribe its external recovery workflow.

This is a real instruction conflict, not evidence that the policy helper runs automatically. The skill remains present with a trigger description at lines 1-4 and no historical/retired marker in its own content. `AGENTS.md` explicitly says that the disabled skill is not production authority. Its stronger ownership boundary should prevail even when this file is discoverable.

### 2. Disablement is path-specific in the inspected Codex configuration

Read-only inspection of `/Users/pablo.carminatti.br/.codex/config.toml` found a `skills.config` entry with `enabled=false` for:

`/Users/pablo.carminatti.br/Projects/ArcReelBR/.agents/skills/direct-brazilian-production/SKILL.md`

The skill path in this chat's available-skill catalog is instead:

`/Users/pablo.carminatti.br/.codex/worktrees/0372/ArcReelBR/.agents/skills/direct-brazilian-production/SKILL.md`

The configuration has no corresponding entry for that worktree path. Its inclusion in this session's catalog proves it is discoverable here; it does not prove it was invoked during any production. Therefore “disabled” must not be treated as universal removal of every worktree copy. No Codex configuration was edited. This finding concerns controller instruction discovery, not the parallel media/provider configuration audit.

**Recommendation:** retire or narrow the skill source itself and align discovery/disablement across intended checkouts if a follow-up implementation is authorized. A path-specific user setting alone is an incomplete portable retirement mechanism.

### 3. The helper stores more than a financial ceiling

`.agents/skills/direct-brazilian-production/scripts/policy.py` is manually invoked. Its `main` reads JSON inputs and atomically writes a private JSON record, without starting the SDK or calling production services (`:362-394`). Repository search found no references to this helper from `server/`, `lib/`, `frontend/` or `agent_runtime_profile/`; its known callers are the skill instructions and tests. This supports “not an application-installed scheduler,” not a claim that no private/manual script ever invokes it.

The record nevertheless includes local job-like state: `pending`, `complete`, `failed`, `not_submitted`, `review`, `discarded`, `quality_attempt`, `resubmission_safe`, and next decision. `decide` emits `reuse_complete`, `reconcile_existing`, `poll_existing`, `reserve_before_delegating` or pause. It blocks any new intent while another is pending (`:181-215`) and computes quality/transport attempts (`:229-277`). `reserve` persists pending state (`:280-291`). The format repeats authoritative job/usage/review facts as snapshots (`references/recovery-format.md:39-64`).

This is an external permission/recovery state machine with partial duplication of native state. It is not a second authoritative billing ledger: `commitment` sums settlements or unresolved quotes (`policy.py:168-178`), and the skill admits that evidence authenticity and provider charges must be verified externally (`SKILL.md:38`). The financial ceiling is complementary; the copied lifecycle and editorial decisions are the parts to narrow.

The helper also contains exact historical experiment branches and target/model/ceiling constants (`policy.py:13-30,49-165`). Those are not universal production rules. Its three-quality-attempt ceiling (`:244-254`) differs from the last production instruction's preference for no more than one targeted retry. Current user scope takes precedence; merely having remaining attempts in this helper grants no permission.

### 4. The public external workflow skill can become a second driver

`skills/video-workflow/SKILL.md:12-18` tells its external Agent to create projects, query the native plan, execute its next action, poll batches and refresh state. The embedded `agent_runtime_profile/.claude/skills/video-workflow/SKILL.ad.md:13-40` also follows the authoritative plan and dispatches actions/subagents.

These are two supported caller positions. Using an external Agent as the driver is not inherently broken, and the public skill was inherited rather than newly invented by the latest Codex integration (`git log -- skills/video-workflow/SKILL.md`, including `c9a50fddf`, `956758f4f`, `4ea57ba3b`). But this project selected **delegation to the embedded Agent**. In that mode Codex should use session controls and monitoring, not independently execute every business stage while the embedded Agent also does so.

Shared backend tools ensure common validation. They do not ensure common creative ownership if both callers issue decisions. `send_agent_message` delegation and direct `generate_videos` orchestration should not be treated as interchangeable evidence of native autonomous direction.

### 5. Historical documents retain the previous division

`docs/plans/brazilian-production/README.md:3` now explicitly marks its plan historical. Its body still assigns Codex adaptation/script/direction/review (`:11`) and defines a directing workflow (`:71-79`). Read under its historical banner, that is provenance, not a live instruction. The old skill lacks an equivalent marker.

`GLOSSARY.md:1272-1278` also retains a reference-led Brazilian workflow definition: every production has a reference and adaptation is an original story based on narrative mechanisms. Those definitions should not be promoted to universal native prerequisites or used to override a user's faithful-adaptation request. The native ad flow supports independent creative shorts without products; no reference upload is mandatory unless the request requires it (`agent_runtime_profile/CLAUDE.ad.md:21,135-141`). This is terminology/expectation drift, not proof of an enforced backend restriction.

### 6. Codex did intervene in the historical creative brief

The prior source audit reconstructed native session `7409a38e-b7b2-4177-9064-bbaae6585c9a`. Evidence references here are its SDK `subpath=''` sequence numbers, as defined in [session-reconstruction.md](session-reconstruction.md):

| External message | What it changed | Responsibility assessment |
|---|---|---|
| Root seq 2 | Asked for an original premise-inspired Brazilian short around 20 seconds | This was a derived brief, not the later faithful-adaptation objective. The first native output followed that request. The 20-second target was later acknowledged as the client's provisional choice. |
| Root seq 98 | Requested two characters, fewer paid assets, clearer turns and specific pacing constraints | External creative/production steering beyond transport. This may be authorized feedback; the record does not establish that each phrase was literal human wording. |
| Root seq 160 | Supplied verified source availability and instructed memory update without rewriting | Evidence/input transport with an explicit scope restriction. Compatible with a thin controller. |
| Root seq 186 and 209 | Relayed the clarified faithful-adaptation goal, budget and resumption context; allowed the native Agent to choose a passage | Corrected the derived brief and restored native production ownership. User authorization and communication are legitimate controller duties. |

The final source passage, five-shot script, keyframe corrections, native image/footage reviews, opening regeneration and timeline came from the embedded Agent. The known seating contradiction was detected and accepted by a native reviewer and recorded in the native timeline. The missing resolution was also recognized by the native script reviewer. These defects cannot be attributed solely to an external harness replacing native review.

This historical evidence proves intervention, not that every intervention was unauthorized or caused the final editorial rejection. It also prevents claiming that every production choice was autonomous inside ArcReel. Exact seq/timestamps and artifacts are in the prior report; no production session was resumed for this follow-up.

## Changes that are useful extensions rather than duplicated orchestration

| Change | Why it is distinct | Recommended disposition |
|---|---|---|
| Session MCP (`5e6626de5`) | Exposes existing AssistantService/session lifecycle; no second SDK runner | Keep. Needed to delegate, observe and answer the existing Agent. |
| Settings/reference/quote/usage MCP (`b88d14cd0`) | Shares transactions, file validation, estimators and repositories with native operations; adds aggregation/access | Keep. Inspect gaps at their owning service instead of replacing the service. |
| Native speech review (`39487c317`) | Adds a previously missing actual-speech evidence/timing path inside presentation and the shared toolset | Keep, with its explicit acting/lip-sync/identity limitations. |
| pt-BR content policy (`7b012052e`) | Adds supported content language, speech-rate treatment and English technical prose with Portuguese speech preserved | Keep or evaluate independently for behavioral quality. It is a real prompt-policy customization, not a second planner. |
| Subscription internal text (`ecd6ead43`) | Implements the existing TextBackend seam; isolated one-turn text calls do not replace the full embedded Agent | Keep if desired authentication/model policy remains. No tool-free limitation should be projected onto the main Agent. |
| English product defaults / RafaCena | Presentation and brand changes | Outside orchestration retirement scope. |
| Standalone audio/AV research (`e98612c83`, `62ec64a23`) | Collects local evidence and checks review output; not wired as an application auto-gate in the searched source | Retain as explicitly research/diagnostic tooling; route production speech/timing through the native tool. Do not treat offline schema validation as audiovisual approval. |

Sources: native companion map; `lib/prompts/prompt_rules/content_language.py:6-16`; `lib/backends/text_backends/claude_subscription.py:149-179`; `scripts/inspect_audio_evidence.py:1-5,45-99,116-135`; `scripts/validate_av_review.py:1,90-110`; `docs/testing/native-speech-review.md:5-11,25-31`. Earlier paid evaluator experiments are documented in `docs/plans/brazilian-production/evidence/10-multimodal-trial.md:7-11,33-44`, with failed controls. They were experiments, not evidence of a dependable production evaluator now integrated into the harness.

## Recommended target boundary

**Codex owns the user's instruction and permission context:** original requirements, supplied inputs, explicit constraints and changes, budget/exclusions, permission to answer native questions, session monitoring, user-facing delivery and honest reporting of acceptance limits. Input transport may include requested research, but derived creative choices must be identified as such rather than silently presented as original user requirements.

**The embedded Agent owns creative and operational direction:** interview as needed, native plan, script and prompts, reference design, asset generation, review delegation, version choice, correction proposal/execution within permission, timeline and exports. Native services own validated data, admission, queue/tasks, checkpoints, presentations and actual usage.

**A user permission cap and a native operation admission are both needed where applicable.** The former answers whether the user authorized scope/spend; the latter answers whether the requested operation is valid for current native state. Neither substitutes for editorial acceptance.

Suggested follow-up, without executing changes here:

1. Retire or rewrite the old directing skill's broad creative ownership and historical experiment-specific production triggers. Keep a minimal permission/session recovery note only if still needed.
2. Make the selected external-client mode explicit: delegate through session MCP for this workflow. Avoid concurrently loading an external stage-execution playbook as another production owner.
3. Reduce external records to authorization/exclusions, session/client keys, submitted instruction and pointers. Derive workflow/job/version/review/usage state from ArcReel. Keep any local exposure arithmetic clearly non-authoritative and bounded to the user's permission.
4. Preserve access adapters and native capability extensions. Improve deficient reviews/instructions in their existing native ownership seam, rather than creating an external creative supervisor.
5. Qualify with a bounded test only after authorization: one original brief forwarded, native session selected once, no external shot/prompt plan, native trace of stages/review/versions, reconciled usage and separately reported editorial acceptance. This audit authorizes no test spending.

## Validation and uncertainty

No whole-harness validation claim is justified. Existing documents report selected tests and bounded local exercises; the last production exposed native editorial weaknesses. Deterministic tool validation, provider execution, session completion and a funny/coherent accepted output are different results. The native source map lists the relevant limits.

Read-only comparison of four important materialized files in `br-viral-reuniao-impossivel` found byte-identical copies of the current source variants: project CLAUDE.md/ad profile, video-workflow/ad skill, edit-video skill and review-footage agent. This reduces the chance that those four behaviors were overridden by private project edits; it does not audit all 125 profile files, project memory or dynamic appended context. Profile materialization intentionally preserves user changes (`lib/agent/profile_manifest.py:1-10`).

No app/backend/frontend source, project artifacts, Codex settings, credentials, services, Git refs or issues were changed. No generation/model calls or implementation tests ran. No fresh upstream comparison, global private-script inventory or full configuration audit was performed. The existence of a named `scripts/perf/harness.py` is unrelated: it is performance-test infrastructure, not this production controller. Recommendations above are reviewable boundaries, not changes already applied.
