# Local interference with the official production workflow

Review date: 2026-11-09. Source: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`, plus the already-present unstaged skill-disable flag. Only audit documents were changed.

## Governing criterion and correction

The user explicitly requires Codex to operate production exclusively through the official ArcReel skill and MCP. Identify and remove local instructions that add another director, insert compulsory steps or impose a parallel production policy. A demonstrated editorial regression is **not** a prerequisite for identifying workflow interference. Preserve product customizations, including Portuguese content, and native tools/capabilities independently of locally imposed automatic usage.

Earlier ownership reviews answered the narrower question “does the operation execute inside ArcReel?” That was insufficient. An extra mandatory step still changes the native workflow when a native tool performs it. This review supersedes earlier blanket retain recommendations for those instructions.

The official public workflow itself directs its external caller to execute the native `next_action` through MCP (`skills/video-workflow/SKILL.md:12-18`). Therefore “all production must use send_agent_message” is not an exclusive requirement established by the official skill. Session delegation is available, but must not become an invented mandatory replacement for the official direct route. The wrong boundary is independent external production planning, not every business-tool call issued by Codex under the official skill.

## Baselines actually compared

- `b88d14cd0` against its parent: the three added Delegated production sections, the asset quotation instruction and the drama/narration creation wording.
- `39487c317` against its parent: required speech review in editing and associated evidence-limit prose.
- The official/public workflow and native mode skills already present before those edits. Existing native video-preview and confirmation requirements are distinguished from new instructions.
- The local directing package and its policy/recovery files, introduced in `7f704b670` and expanded in subsequent local commits.

These comparisons establish local additions relative to their actual pre-change sources. They are not a claim of exact equivalence with the latest online upstream release. No model execution or paid comparison was needed to establish instruction-level changes.

## Detailed removal/adjustment list

### W01: retire the external Codex creative-director role

**Location:** `.agents/skills/direct-brazilian-production/SKILL.md:8-18,28-44` in HEAD; current working-copy lines are shifted by its new frontmatter flag.

**Added behavior:** Codex owns research/adaptation/review, prepares a bounded candidate and delegates that exact individual action. The skill also prescribes experiment-specific rounds and prerequisites.

**Interference:** a second directing playbook competes with the official skill and the native project's planning/review responsibilities. Using MCP for its eventual command does not remove the competing policy.

**Disposition:** remove this package from the active production-instruction path. Do not substitute another custom directing skill. Retain historical evidence/receipts. Keep the user's explicit requirements, feedback, spending ceiling and exclusions as client context.

The already-present `disable-model-invocation: true` was added by concurrent work, not this review. It does not rewrite the conflicting body. This document does not assert that the skill currently auto-runs or that disablement has completed retirement across hosts.

### W02: stop requiring the custom per-action admission/recovery engine

**Locations:** the same skill's Authorize one action and Stop and resume sections; `.agents/skills/direct-brazilian-production/scripts/policy.py:181-291,349-394`; `references/recovery-format.md:39-64`.

**Added behavior:** reserve an external intent before delegation, serialize unresolved submissions, maintain external pending/review/attempt transitions and apply historical hard-coded round/quality-attempt rules before the next instruction.

**Interference:** this is a mandatory local decision layer absent from the official skill. The helper itself makes no provider call and its data is documented as snapshots, but the directing instructions make its decisions prerequisites for production.

**Disposition:** retire the operational dependency together with W01, rather than refactor it into another harness. Preserve permission provenance, unresolved financial exposure and settled costs as evidence; preserve native task/provider recovery and idempotency. Existing user exclusions still constrain every call. This does not propose a new backend financial cap or remove the user's spending protection.

### W03: remove the universal additional pre-generation tool sequence

**Locations:** `agent_runtime_profile/CLAUDE.ad.md:21`, equivalent drama/narration line; clause R04.05 in the earlier review.

**Added rule:** before generation, reconcile requirements with both `get_project` and `get_effective_configuration`.

**Before:** the official workflow obtains the authoritative native plan, follows its operation admission, and uses relevant state/capabilities according to that workflow. This exact pair of mandatory calls was absent from the parent profiles and relevant workflow sources.

**Interference:** a new compulsory preflight is layered over official routing, regardless of whether the plan already supplies the needed state.

**Disposition:** remove the universal prerequisite. Preserve both tools and effective-configuration inspection as available product functionality. This is not permission to ignore actual configuration or invent capabilities; follow the official workflow and relevant tool contracts.

### W04: remove the locally imposed image-quotation stage

**Locations:** `agent_runtime_profile/.claude/skills/generate-assets/SKILL.md:14`; the `quote_assets` / `quote_storyboards` instruction in all three `CLAUDE.*.md:23`; clause R04.11. The subsequent adapter review also found the same blanket pre-action instruction in `server/agent_toolset/workflow_access.py:85-86`; W04 includes that description, published to both hosts.

**Added behavior:** quote asset batches before paid generation and impose explicit image-quotation calls in the top-level production instructions.

**Before:** the asset skill's workflow goes from loading missing metadata to enqueueing and native review. The separate required quote step was absent. Native video-preview quotation already existed, for example in the edit-video correction checklist at parent line 58.

**Interference:** extra image preflight/confirmation choreography is inserted into the native sequence. Correct estimators and useful financial evidence do not make the added mandatory sequence original workflow behavior.

**Disposition:** remove the blanket image-quotation instruction from the modified skill/profiles. Preserve image quote APIs, costs and accurate reporting. Preserve **existing official video-preview, paid-action confirmation and admission rules**. Do not delete the whole mixed sentence in a way that removes inherited video protections or treat an unknown price as permission to spend.

### W05: remove the compulsory runtime accounting-call checklist

**Locations:** all three `CLAUDE.*.md:23`; clause R04.13.

**Added rule:** read both `get_project_usage` and `get_project_costs` to distinguish actual spending from estimates.

**Interference:** it introduces another required pair of runtime calls through local profile prose. The instruction is not limited to a user-requested cost report or official workflow action, although the records themselves are native authorities.

**Disposition:** remove this universal checklist. Preserve accounting APIs and ledger data. Codex may use MCP to reconcile the user's authorized scope or report requested costs, following the official skill/tool contracts; that does not require a second authoritative ledger or a locally imposed stage in every native production.

### W06: remove the broad local optional-reference policy

**Locations:** all three `CLAUDE.*.md:21`; clause R04.08.

**Added rule:** “a reference is optional unless the request requires it.”

**Interference:** the unqualified term introduces a transversal reference policy outside the official mode/admission rules. The surrounding text appears to mean user-supplied uploads, but required generated sheets/first frames are also references in the native domain. No reproduced bypass is required to identify this local policy addition; no bypass is asserted here.

**Disposition:** remove the broad clause and defer required inputs to the official mode, capabilities and admission. Preserve optional supported uploads and all actual required native inputs. Do not replace it with another universal policy requiring human photographs or voice samples.

### W07: remove the external-controller role from runtime financial policy

**Locations:** all three `CLAUDE.*.md:23`; clause R04.15.

**Added rule:** “The controller owns the financial ceiling.”

**Interference:** it inserts the custom external-controller model into native runtime instructions. Under the selected approach, the external host uses the official skill and communicates the user's authorization; it does not acquire its own independent production-authority role.

**Disposition:** remove that controller-role attribution from the profiles. Preserve the user's actual financial limits and the native requirement to obtain permission for excluded paid actions. Do not add an external authorization engine, weaken original native confirmation gates, or imply that a provider queue technically enforces the full user ceiling.

### W08: remove mandatory ASR from the general editing/acceptance sequence

**Locations:** `agent_runtime_profile/.claude/skills/edit-video/SKILL.md:27`; the dependent “use the speech-evidence step above” wording at line 42; introduced in `39487c317`.

**Added behavior:** before voice/timing acceptance, call `review_speech` for each selected unit, compare transcripts, and give the report to the footage reviewer. When timing correction is requested and eligible, apply timing, reread the timeline and rerender affected outputs.

**Before:** the editing skill already had footage review, timeline decisions, sound, candidate selection, correction checklists and output; no required ASR step was present.

**Interference:** an additional acceptance stage and evidence handoff is imposed on normal editing. That is a workflow modification even though it uses a new native tool and no external paid model.

**Disposition:** remove the compulsory per-unit ASR prerequisite and automatic review handoff from the general skill. Adjust the dependent reference so it does not point to a mandatory stage that has been removed. Preserve `review_speech`, measured subtitle timing and their native presentation integration as product capabilities available for explicit requests/supported operations. Correcting requested subtitle timing can still legitimately require re-reading and rerendering; do not remove that feature's necessary mechanics. Preserve factual warnings that ASR is not acting/lip-sync verification.

## All 16 CLAUDE additions under this criterion

The three sections are identical; this table applies to each. Entries not listed for removal below are not certified regression-free: they simply do not impose a demonstrated independent workflow change under this review.

| Clause | Added rule | Finding and disposition |
|---|---|---|
| R04.01 | Client supplies requirements/inputs by MCP | Supported interface context; no new stage. No workflow-based removal required. |
| R04.02 | Native Agent owns workflow/subagents/editing | Preserves native responsibility. Do not interpret it as forbidding the official external skill's supported direct-tool route. |
| R04.03 | Follow get_workflow_plan | Restates the existing authoritative route. Keep. |
| R04.04 | Authorization applies only within its scope | Keep the permission limitation. Full-autonomy permission already existed in parent drama workflow line 98; specific blocking confirmations also existed at line 140. This addition does not explicitly waive them and should not be labeled a proven new bypass. |
| R04.05 | Before generation, call project/effective-configuration checks | W03: remove the universal added preflight, preserve tools. |
| R04.06 | Persist supplied settings via configure_project | Native transaction for requested settings, not a stage when no setting change was supplied. Preserve API semantics; no new per-generation call should be inferred. |
| R04.07 | Supplied bytes can enter via upload_reference | Optional input/API capability. No compulsory step added by “can.” Preserve. |
| R04.08 | Reference optional unless requested | W06: remove broad local policy; use official input admission. |
| R04.09 | Check capabilities before claiming audio-reference support | Factual capability constraint consistent with existing native capability rules. Preserve without the universal preflight in W03. |
| R04.10 | Upload does not regenerate an asset | Correct API semantics; no workflow stage. Preserve. |
| R04.11 | Image quotes and video preview | W04: remove the added blanket image-quote stage; preserve inherited video-preview rules and quote functionality. |
| R04.12 | Report unpriced targets/estimate bases accurately | Reporting accuracy, not a new tool call. Preserve. |
| R04.13 | Read both usage and costs | W05: remove compulsory accounting-call checklist; preserve APIs/evidence. |
| R04.14 | Ask before excluded paid actions | Existing permission protection, not a new director. Preserve. |
| R04.15 | Controller owns the ceiling | W07: remove custom controller attribution; retain actual user constraints and native safeguards. |
| R04.16 | No separate production state machine | Architectural boundary consistent with the user's request. Not an added executable step; no removal required on workflow grounds alone. |

## Other edits reviewed and preserved

- **Drama/narration project creation entry:** native wording now accepts Web or external MCP `create_project` before the session. It changes an entry option but matches the official public skill's existing project-creation route. It is not another directing plan. No removal proposed.
- **review-footage evidence limits:** accurately states that contact sheets do not establish actual speech, performance or lip sync. It adds reporting limits, not another generation call, approval engine or required processing stage. Preserve.
- **edit-video factual limits:** render success is not editorial acceptance; mechanical subtitles are not measured alignment; trimming does not independently fix subtitle cue timing. Preserve these facts while removing the mandatory ASR routing in W08.
- **pt-BR, English technical prompts, subscription text, branding, native MCP adapters, speech tools, image encoding/cost evidence and diagnostics:** preserve product behavior/capabilities, subject to adapter adjustments in the subsequent assessment. Their existence does not require the local mandatory playbooks above.

This is not a proposal to delete every added instruction or roll back entire commits. `b88d14cd0` and `39487c317` include native capabilities and tests that must not be removed merely to undo a workflow instruction. Implementation would require targeted edits and checking affected references, not a blanket Git revert.

## Evidence and implementation boundary

Source comparisons above can be reproduced with `git show <commit>^:<path>` and `git diff <commit>^ <commit> -- <path>`. The native/public skill at `skills/video-workflow/SKILL.md:12-18` specifies authoritative plan execution. The parent asset skill's Workflow section has no separate quotation stage; parent edit-video already has video-preview cost/consent rules. The new speech tool remains in `server/media_tools/speech_review.py:40-95`; settings/quote/accounting/upload tools remain in `server/media_tools/workflow_access.py`. None was executed in this review.

The findings establish additions to instructions and decision dependencies, not their measured effect on humor, acting or continuity. The list does not require a new model benchmark, does not approve paid work and does not claim a particular observed video defect came from a particular rule. No source, settings, service, skill installation, token or production artifact was changed. Only this analysis and the agreement register were updated.

## Adapter follow-up

The subsequent [MCP adapter assessment](mcp-adapter-assessment.md) extends W04's description scope and tracks field-permission, preview-contract and conditional persistence/concurrency findings separately. Preserving a tool capability does not imply keeping every wrapper or model-facing description unchanged.
