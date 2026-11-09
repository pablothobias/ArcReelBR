# MCP adapter assessment: workflow effects and regression risks

> Stage-7 closure (latest): [integrated results and disposition of all 17 entries](../../plans/native-framework-boundary/stage-7-results.md) records completed local stages, the complementary safe R12 MCP error correction, preserved customizations and 1,472 passing cases. Two pre-existing Web test failures reproduce on the base revision and remain recorded. Earlier pending-stage/recommendation statements below are historical. No commit; current host/configuration readiness remains separate.

> Stage-6 update (latest): [R10e contract and validation](../../plans/native-framework-boundary/stage-6-results.md) confirms inspection may materialize before ASR, including unavailable recognition; `apply_timing=false` skips new measurements and preserves still-valid prior timing. Native materialization is unchanged; 1,203 selected cases pass. Earlier pending-stage statements below are historical. Configuration readiness remains separate and stage 7 has not started.

> Stage-5 update: [R12 implementation results](../../plans/native-framework-boundary/stage-5-results.md) records native inherited-route validation and passing tests. Earlier zero-pricing observations describe pre-fix source; current configuration readiness and stage 6 remain separate/pending.

> Stage-4 update: [R11 implementation results](../../plans/native-framework-boundary/stage-4-results.md) records transactional MCP character-image upload and passing regression coverage. Earlier race outcomes describe pre-fix source; R12/stage 5 remains pending.

> Stage-3 update: [implementation results](../../plans/native-framework-boundary/stage-3-results.md) records R10a+b/c/d corrections and tests. Earlier reproduction outcomes describe the pre-fix source. R10e materialization is preserved; R11/R12 are still pending.

> R07/R09 implementation update: [stage-2 results](../../plans/native-framework-boundary/stage-2-results.md) records the local corrections and tests. Pre-fix schema/guidance findings below remain historical evidence; R10/R11/R12 corrections are still pending.

Date: 2026-11-09. Source revision: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. This follow-up applies A02: official skill and MCP are the production interface, while local instructions must not impose a second workflow. Native product capabilities, including pt-BR, remain protected. No implementation or production changes were made.

## Conclusion

The earlier blanket recommendation to preserve adapters because they reuse native services was too broad. Reuse does not establish preservation of the former field permissions, instruction surface, return contract or side effects.

Three concrete findings need adjustment in the list:

1. The shared Settings adapter newly exposes grid toggling to the embedded Agent despite an explicit retained native user-only restriction.
2. A tool description independently injects the added quote-before-paid-action workflow, so deleting the CLAUDE/skill instructions alone would not remove it.
3. The remote adapter gives image-edit previews unconditional batch/polling instructions even though previews return no batch.

The subsequent [isolated reproductions](r10-r11-isolated-reproduction.md) confirmed conditional diagnostic persistence, a cost-handler cancellation defect and the reference-upload false-success race. They also narrowed the storyboard-quote claim and distinguished inherited speech materialization from a defect. The 13-case set passed; no incident in an existing production project is claimed. No additional session lifecycle corruption was established.

## Scope and provenance

Reviewed `5e6626de5` (session controls), `b88d14cd0` (workflow access, shared Settings/upload extraction, image-edit preview and declarations), and relevant `39487c317` speech/presentation paths, each against its parent. The remote/embedded projection machinery and batch-handle-versus-waiting distinction predate these local additions and were inspected as the contract they use.

The scope includes more than files named adapter: `server/remote_mcp.py`, `server/session_mcp.py`, `server/agent_toolset/{remote,embedded,declaration,toolset,workflow_access,media_generation}.py`, the workflow/speech/image-edit handlers, shared Settings/uploads, native service entry points and relevant tests. It is not a global security audit, fresh upstream comparison or media-provider configuration audit.

## MC01: Settings adapter broadens a native Agent permission

**Confirmed behavior and policy contradiction.**

- `ConfigureProjectRequest` subclasses the entire Web `UpdateProjectRequest` (`server/media_tools/workflow_access.py:34-37`). Its schema includes `grid_storyboard` (`server/routers/projects.py:355`).
- The handler passes it to the Settings transaction without a host-specific field restriction (`workflow_access.py:45-54`). Non-ad updates persist that field (`projects.py:1137-1141`).
- Registration in `AGENT_TOOLSET` exposes the field to the embedded Agent and the external host. Existing main-Agent runtime tool policy does not add a field-specific exclusion.
- Native drama/narration profiles say the user controls grids in Settings and the Agent cannot bypass that via tools (`agent_runtime_profile/CLAUDE.drama.md:100`, same narration rule). The older `patch_project` settings allowlist omits that flag (`server/tool_runtime.py:2533-2541`).

An isolated schema check accepted `{"grid_storyboard": true}` and confirmed the field in both host schemas: [mcp-adapter-schema-evidence.json](mcp-adapter-schema-evidence.json). This check did not invoke the handler or toggle any live project. The persistence path was confirmed in source.

**Proposed disposition:** align the adapter's field/host permissions with the retained native restriction. Preserve Web grid functionality and supported MCP settings; do not simply broaden the native instruction to retroactively justify the adapter. The exact external-user versus embedded-Agent allowance must be explicit in the implementation design. No live misuse or causal effect on the prior sketch is asserted; that sketch is ad/storyboard and this grid issue concerns non-ad projects.

## MC02: workflow instructions are embedded in tool descriptions

**Confirmed instruction-level interference.**

`server/agent_toolset/workflow_access.py:85-86` tells callers to use quote tools or video preview before paid actions. This new declaration is published to both hosts. The cost reader itself does not need that extra production sequence to return costs. The description remains visible after removing the profile instructions identified in W04.

**Proposed disposition:** extend W04's removal scope to the blanket quotation directive in this description. Keep the cost reader, quote tools, correct unknown-cost semantics, actual user authorization and inherited official video-preview rules. Audit active tool descriptions alongside skills/profiles; they are part of the Agent's instruction surface.

Do not overclassify API guidance: `configure_project` explains use for supplied settings; it does not explicitly require a call on every generation. `get_project_usage` says to follow the cursor **to reconcile the full ledger** (`:97`). Full pagination is necessary for that purpose; the sentence does not establish a compulsory ledger-exhaustion stage on every call or production. No unconditional-pagination removal is justified from that wording alone.

## MC03: preview responses conflict with remote batch/polling instructions

**Confirmed description/response-contract mismatch.**

`EDIT_IMAGES` uses `generation_tool`, which sets `long_task=True` (`server/agent_toolset/media_generation.py:54-78,110-119`). `remote_description` appends the generic note promising a `generation_batch` handle and instructing polling (`server/agent_toolset/remote.py:39-42,98-102`). The added `preview=true` handler returns `image_edit_quote` before submission (`server/media_tools/image_edits.py:310-325`), with no batch to poll.

The isolated metadata check confirms that the same remote description contains the preview branch and unconditional batch promise. The existing preview test verifies targets and no submission/source-image replacement. These establish the contract mismatch, not actual duplicate generation or an observed client retry.

**Proposed disposition:** make the description accurately distinguish immediate previews from submitted batches. Preserve previews, actual generation semantics and native batch polling. The older grid list-only preview has a related generic-note tension; do not attribute all such behavior to the new local preview.

## MC04: inspection/read operations are not guaranteed to make zero writes

**Follow-up: conditional effects and the handler cancellation defect reproduced in isolation.** See [R10a-e and controls](r10-r11-isolated-reproduction.md). The source notes below predate those experiments; their unexercised-risk wording is historical, not the current status.

- Storyboard quoting loads scripts through a planner that can persist legacy migrations (`server/services/admission/storyboard_batch.py:153-154,392-393`). The actual cost reader also uses writing script loads (`server/media_tools/workflow_access.py:127-139`); storyboard image-edit preview uses the same kind of load (`server/media_tools/image_edits.py:254-272`). `ProjectManager.load_script` can persist compatibility conversion; `load_script_readonly` is a separate operation (`lib/project/project_manager.py:1386-1416`). Asset quoting uses the read-only variant and should not be included indiscriminately.
- The cost reader wraps its script loop in ordinary `asyncio.to_thread`, while the storyboard planner uses the native cancellation-safe transaction wrapper for possible migration writes. On cancellation, the new cost caller can complete before its writing worker does. This source-supported risk was not exercised on legacy data during this audit.
- `review_speech(apply_timing=False)` first calls `materialize_unit`, which can persist current presentation/subtitle artifacts, before ASR readiness or the timing-application branch (`server/media_tools/speech_review.py:49-67`; `server/services/presentation/presentation_read_model.py:329-341`). This materialization seam is inherited; the new tool reaches it. False means no requested measured-timing application, not necessarily no filesystem activity.

**Proposed disposition:** verify and define inspection/persistence contracts and cancellation handling with isolated legacy/current artifacts. If writes are intended native behavior, preserve their transaction semantics and disclose them. If a strict read-only operation is intended, use the appropriate native reader. No blanket migration removal, presentation rewrite or evaluator retirement is justified. No current production overwrite was demonstrated.

## MC05: reference host validation is not a commit-time guarantee

**Follow-up: false success/orphan reference reproduced with controlled concurrent native deletion.** See [R11 and its control](r10-r11-isolated-reproduction.md). No live production incident is claimed. The source notes below predate the reproduction.

MCP character-image upload adds an existing-character precheck (`server/routers/files.py:570-573`), then writes bytes and updates metadata (`:637-644`). The native character-image upload specification has no host bucket, and the inherited missing-host fallback tolerates a later `KeyError` (`:240-246,645-654`). If another supported operation deletes the character between precheck and metadata commit, the adapter can report a successful upload without the promised registered host. The setter's missing-host failure is at `lib/project/project_manager.py:3817-3821`.

**Proposed disposition:** reproduce that ordering in an isolated concurrent test before treating it as a production incident; then ensure the MCP existing-host guarantee is transactional if that contract is retained. Preserve intentional Web semantics, reference uploads and supplied content. The extra existing-character requirement itself is a documented access difference, not proof that the whole native workflow is broken.

## Adapters and differences with no additional defect established

| Area | What was verified | Practical limit |
|---|---|---|
| Core remote projection | Adds explicit project scope, validates through shared declarations and returns structured results; external generation returns handles while embedded generation waits | This is established native transport behavior, not a new second queue. Official skill polling must still be followed. |
| Session send/create | Calls the existing AssistantService; requires retry keys and nonempty text | Narrower than REST, which supports optional keys/attachments. No claim of complete Web feature parity is justified. |
| Locale | MCP uses explicit locale/default English; REST uses HTTP language selection | Conversation language is separate from pt-BR creative content. No Portuguese content regression was established here. |
| Session questions, cursor, queue and interruption | Delegate to native service/actor operations; interruption is not cancellation of already-submitted media | Selected tests passed with a fake SDK process, not a real model. No extra state machine was found in the bridge. |
| Style/reference uploads | Reuse native validation; MCP adds explicit confirmation for model-capable style analysis, required named owner and a transport size limit | These are capability-specific admission/access differences, not automatically workflow interference. They must not be silently claimed identical to every Web upload ordering. |
| Shared Settings extraction | Inspected mutation body preserves native Settings behavior, with caller source injection | Sharing Web code does not preserve old Agent permissions: MC01 is the important exception. |
| Effective configuration | Resolves native configuration and can invoke local subscription auth-status verification | Not a paid provider test or pure in-memory getter. No new universal readiness gate exists in this handler itself. |
| Speech/timing | Optional native capability with selected-media and source-bound validation | Keep it separate from the removed mandatory editing-stage instruction W08. |

## Validation actually run in this follow-up

Executed against this worktree using the existing main-checkout virtual environment, with dotenv reads and bytecode writes disabled:

```text
python -m pytest -q -p no:cacheprovider
  tests/integration/server/test_session_mcp.py
  tests/integration/server/test_workflow_access.py
  tests/integration/server/test_remote_mcp.py
  tests/integration/server/media_tools/test_image_edits.py
```

Result: **69 passed**, one pre-existing SQLite expression-index reflection warning, 11.42 seconds. The fixtures isolate project roots/databases and replace provider/SDK boundaries. No running application, actual model or media provider was called. No new tests were added.

The schema/description evidence check used a temporary isolated root, invoked no tool handler and made no application request. The temporary root was discarded; only the JSON result above was retained.

Passing tests do not settle MC01's documented policy conflict, MC03's model-facing guidance or the untested legacy/concurrent conditions in MC04/MC05. Both hosts can share the same mistake. Prior 1,011 host-consistency cases were not rerun; their historical results are not a substitute for this review.

## Updated list and next boundary

- Extend W04 to remove the quotation-sequencing instruction in the shared cost-tool description (MC02).
- Add separate adapter adjustment items for native field/host permissions (MC01) and preview/polling semantics (MC03).
- Apply the subsequent R10/R11 reproduction report: the cost-handler cancellation boundary and upload race are reproduced defects; the other observed writes require precise contract classification, not wholesale capability removal. No media failure or production incident is established.
- Preserve official MCP access, supported direct-tool/session routes, user authorization, pt-BR and product customizations. Do not assume all adapters should be retained unchanged or all should be removed.

Detailed source notes: [session/shared-host review](mcp-session-adapter-review.md) and [workflow-access review](mcp-workflow-access-review.md). The parent report records tests run centrally; the subreports' “no tests run” statements describe those individual source-only reviews. No adapter, skill source, configuration or production change was implemented.

## Isolated verification follow-up

The [R10/R11 reproduction report](r10-r11-isolated-reproduction.md) supersedes pending-reproduction conclusions for MC04/MC05. It records 13 passing cases, controls, exact doubles and remaining limits. No correction was applied.
