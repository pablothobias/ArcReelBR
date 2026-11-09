# Ownership review of every added CLAUDE profile rule

> Historical ownership-only assessment. Its disposition column is superseded by [the workflow-interference review](workflow-interference-review.md), which compares added compulsory steps and policies with the pre-change workflow without requiring proven regression. Source facts remain useful; do not treat the earlier two-adjustment-only conclusion as current.

Date: 2026-11-09. Source revision: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. Scope: only the Delegated production section added by `b88d14cd0` to `agent_runtime_profile/CLAUDE.ad.md`, `CLAUDE.drama.md` and `CLAUDE.narration.md`, lines 17-23 in all three files. The sections were compared directly and are byte-identical. The table below therefore applies to all three modes without repeating it three times.

The user authorized analysis and a list update, not changes to runtime instructions, product code, settings or production. Proposed wording below is review material only. No model calls, paid evaluations or implementation tests ran.

## Ownership criterion

Under agreed A01, Codex is an external client. It carries original requirements, inputs, user permission and feedback through supported interfaces, monitors sessions and reports delivery. ArcReel owns the production plan, derived creative decisions, tool execution, native validation, reviews, selected versions and editing.

Financial permission has two complementary sides: Codex retains and communicates the user's actual ceiling/exclusions; the native Agent must respect the communicated constraints and ask before acting outside them. Removing native permission guards would not satisfy A01. Native technical admission does not establish financial permission.

## Clause-by-clause classification

Numbers identify atomic clauses, including clauses joined by a semicolon in the source. “Keep” means no ownership-based edit is justified by this review, not that behavioral equivalence to upstream has been proven.

| ID / source line | Added rule | Correct owner | Recommended disposition and reason |
|---|---|---|---|
| R04.01 / 19 | An external client may supply the user's request and inputs through MCP. | ArcReel interface contract; Codex supplies actual inputs as client. | **Keep.** Recognizes a supported input route. It does not give the external client creative ownership. Removing this context has no demonstrated benefit. |
| R04.02 / 19 | The embedded Agent remains responsible for the native workflow, planning/review subagents and editing. | ArcReel. | **Keep.** Directly enforces A01; do not move this responsibility into Codex. |
| R04.03 / 19 | Follow `get_workflow_plan`. | ArcReel. | **Keep.** The authoritative planner and the native workflow skill already own stage decisions. This rule preserves that authority rather than creating another stage table. |
| R04.04 / 19 | Supplied global authorization applies only within its stated scope. | Shared permission boundary: Codex carries scope; ArcReel respects it. | **Keep.** The sentence restricts authorization; it does not authorize blanket autonomous spending. It must not be read as bypassing native blockers, structural confirmations or explicit exclusions. No demonstrated conflict requires deleting it. |
| R04.05 / 21 | Before generation, reconcile explicit requirements with `get_project` and `get_effective_configuration`. | ArcReel. | **Keep.** Production must use native actual state and effective models. These tools do not delegate model or creative decisions back to Codex. No measured redundant-call problem was established. |
| R04.06 / 21 | Persist supplied settings through `configure_project`. | ArcReel's validated settings transaction. | **Keep.** Apply supplied authorized values through the native tool. Codex may transmit requirements; it must not repair project storage directly. This is not permission to invent settings or alter unrelated values. |
| R04.07 / 21 | Supplied reference bytes can enter through `upload_reference`. | Shared access contract: external transport; native validation, registration and consumption. | **Keep.** A native ingestion tool is consistent with A01. Its supported reference kinds, existing-owner requirements and paid style-analysis confirmation remain applicable. Transport is not creative reference selection. |
| R04.08 / 21 | A reference is optional unless the request requires it. | ArcReel's input/admission semantics; user requirements may add obligations. | **Adjust narrowly.** In context it appears to mean user-supplied uploads, but unqualified “a reference” can also describe required sheets/keyframes. Clarify that optional user uploads do not waive generation prerequisites or capability admission. This is an evidenced wording ambiguity, not a reproduced bypass or proven cause of the failed video. |
| R04.09 / 21 | Check effective video capabilities before claiming audio-reference support. | ArcReel. | **Keep.** The model/channel and selected route determine support. Codex should relay that evidence rather than promise support independently. |
| R04.10 / 21 | Reference upload does not regenerate an asset. | ArcReel tool semantics. | **Keep.** Correctly separates ingestion from generation and avoids silently authorizing new paid work. |
| R04.11 / 23 | Use image quotes and the native video preview before the relevant requests. | ArcReel's native planners and estimators. | **Keep.** Quotation is native production evidence, not an external creative plan. Use each tool within its actual target coverage; a quote itself does not grant spending permission. |
| R04.12 / 23 | Report unpriced targets and conservative estimate bases accurately. | ArcReel reports source facts; Codex preserves them when communicating with the user. | **Keep.** Unknown cost must not become zero and an upper bound must not be presented as expected spend. This reporting duty does not create a separate ledger. |
| R04.13 / 23 | Read project usage and costs to distinguish actual spending from estimates. | ArcReel owns the records; native Agent and external client can inspect them for different purposes. | **Keep.** Native use supports production reporting; Codex use reconciles user permission. Two readers of the same authority are not two accounting systems. |
| R04.14 / 23 | Ask before paid actions excluded by existing authorization. | ArcReel must stop/surface the question; Codex obtains a user decision when not already authorized. | **Keep.** This is a necessary native permission guard. Never remove it because the external client tracks a ceiling, or turn it into repetitive confirmation for actions already covered by a valid authorization. |
| R04.15 / 23 | The controller owns the financial ceiling. | External-client role policy, with native compliance retained. | **Move the controller-role description out of the runtime profiles and adjust native wording.** The user owns permission; Codex retains/communicates it. The native Agent remains accountable for respecting supplied financial limits and scope. Do not merely delete this clause and leave native budget compliance unspecified. No new backend cap or external budget engine is proposed. |
| R04.16 / 23 | This does not introduce a separate production state machine. | Architectural boundary, already recorded in repository instructions. | **Retain the principle; no mandatory runtime edit established.** It reinforces A01. It may be documented in architecture/client guidance if those documents are later revised, but removal/relocation solely for prose organization is not a justified task now. |

## Concrete proposed changes within R04

Only R04.08 and R04.15 have a specific wording adjustment proposed by this review. The remaining clauses have no demonstrated responsibility conflict requiring removal. Do not replace the whole section, add a new workflow, revert `b88d14cd0` wholesale or move native operational checks into Codex.

### R04.08: distinguish supplied uploads from required native inputs

Proposed meaning, not applied:

> User-supplied reference uploads are optional unless required by the request. Required generation inputs remain governed by the native workflow and capability admission.

Why: `upload_reference` accepts specific supplied character/style inputs, while storyboard/reference generation has its own required input rules. Optional initial photographs do not imply optional storyboard first frames or optional required sheets. Do not invent a universal requirement for the user to supply actor photographs.

### R04.15: separate permission custody from native compliance

In external Codex instructions, retain: the user's actual permission is authoritative; Codex records/transmits the ceiling, round scope and exclusions, and reconciles native quote/usage evidence. It does not direct each creative retry or become a new production-state authority.

Proposed native meaning, not applied:

> Respect the supplied financial ceiling and authorized round scope. Request authorization before taking an action outside either constraint.

The existing outside-authorization guard R04.14 remains. Any future edit should integrate these meanings without weakening native confirmation behavior or implying that the backend technically enforces a hard total cap. No new financial configuration field, gate, persistent policy database or repeated human approval is proposed.

## Evidence and checks

- The full addition is the same in all three files: `git diff a779b5d51..HEAD -- agent_runtime_profile/CLAUDE.ad.md agent_runtime_profile/CLAUDE.drama.md agent_runtime_profile/CLAUDE.narration.md`; introduced by `b88d14cd0`.
- Native workflow authority and actual prerequisites: `agent_runtime_profile/.claude/skills/video-workflow/SKILL.ad.md:13-25,49-69`; drama's capability guidance at `agent_runtime_profile/CLAUDE.drama.md:29-35`. Native stage selection is not an external client invention.
- Validated settings: `server/media_tools/workflow_access.py:34-54` reuses `UpdateProjectRequest` and `update_project_settings`.
- Effective configuration: `server/media_tools/workflow_access.py:186-232` resolves native image/video/script paths and reports problems/authentication availability.
- Supplied upload contract: `server/media_tools/workflow_access.py:235-300` limits kinds, requires the existing character where applicable, accepts supplied bytes and protects style analysis with explicit confirmation. It is not every generation reference/input type.
- Native quotations and usage: `server/media_tools/workflow_access.py:57-183`; `server/agent_toolset/workflow_access.py:58-97`. Missing-reference targets skipped in a quote are not zero-cost generatable targets.
- Native corrections and permission limits: `agent_runtime_profile/.claude/skills/edit-video/SKILL.md:62-85`; `agent_runtime_profile/.claude/references/workflow-plan.md:185-190`; `skills/video-workflow/references/plan-safety.md`.
- External session questions/answers: `server/session_mcp.py:100-118,149-164`; user scope in Codex and native ownership are already separated in `AGENTS.md:7-9`.
- Mode materialization: `lib/agent/profile_manifest.py:118-165` selects one matching profile. That does not certify that the added instructions have no effect on behavior.

## Product preservation and uncertainty

These proposed wording changes do not touch pt-BR language handling, Portuguese dialogue/subtitles/history, English technical prompts, branding, subscription backends, MCP adapters, speech review, generation queues or provider integrations. They are separate owning sources and capabilities.

No controlled before/after model evaluation isolated the behavioral effect of this section. No causal claim connects a particular clause to humor, acting or continuity defects. Classification by ownership and identification of ambiguous wording are supported; regression absence or universal end-to-end correctness is not established. Changes to the actual files still require a separately authorized implementation.
