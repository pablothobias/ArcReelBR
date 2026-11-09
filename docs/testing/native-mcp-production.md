# Native production through MCP

The external client follows the official ArcReel skill through MCP, including native next-action tools or delegation to the existing Agent through `send_agent_message`. It carries the user's authorization and follows the native workflow. Repository `AGENTS.md` defines that responsibility boundary.

## Existing services exposed

| MCP interface | Native owner |
| --- | --- |
| `configure_project` | Supported automated fields through the native Settings transaction; grid toggling remains user-controlled in Web Settings |
| `upload_reference` | Native character image/audio and style upload validation, normalization and metadata |
| `get_effective_configuration` | ConfigResolver and official local subscription authentication check |
| `quote_assets` | AssetSheet batch planner and image cost estimator, including explicit regeneration selections |
| `edit_images` with `preview=true` | Existing edit target validation and i2i cost estimator; no submission |
| `quote_storyboards` | Episode storyboard batch planner and image cost estimator for missing storyboards |
| `get_project_costs`, `get_project_usage` | Existing cost estimation service and paginated usage repository |
| `list_agent_sessions`, `act_on_agent_queued_message` | Existing AssistantService and SessionActor recovery |

The first seven declarations are shared with the embedded host. Session-control tools remain external-only. Character reference upload requires a registered character; it neither creates a finished sheet nor generates media. MCP character-image uploads recheck the owner and commit image bytes plus the metadata pointer in one native rollback-capable transaction. Web uploads keep their existing missing-owner semantics. Style analysis explicitly invokes the configured text provider. Audio references still depend on the effective video route and voice binding.

Automated `configure_project` calls reject `grid_storyboard`, including false/null, before changing any supplied setting. Web Settings and the existing creation contract retain grid controls. A generation response with a `generation_batch` handle is followed through `get_generation_batch`; an image-edit or list-only grid preview creates no batch to poll.

Cost consultation, storyboard quotation and image-edit preview adopt legacy script compatibility in memory without persisting the script. Actual editing and ordinary generation retain their native migration behavior. A quote remains a state-dependent estimate, not a reservation or submission admission.

In the no-active-credential fallback, zero marginal Agent token pricing requires no enabled inherited Claude cloud-route selector. Conflicting selectors are refused before runtime construction; they are not silently cleared or switched to another route. The internal subscription text auth check uses the same selector semantics. Configured API credential pricing and spawn-time accounting snapshots remain unchanged. This guard is not proof of current login readiness and does not rewrite prior usage.

`review_speech(apply_timing=false)` is inspection without new measured-timing application, not a zero-write query. Current native presentation materialization precedes ASR and may persist presentation/subtitle/manifest artifacts even on an unavailable-recognition error. Still-valid prior measured timing remains effective; normal source/media invalidation is unchanged. Speech inspection remains optional for supported requests, not a mandatory production acceptance stage.

## Verification

Integration tests in `tests/integration/server/test_workflow_access.py` cover settings persistence and refusal, real image upload, unsafe inputs, missing owners, native quotes, unpriced quotes, accounting pagination, and effective models. `test_session_mcp.py` exercises the real AssistantService over MCP with only the SDK process replaced: retry keys, reconnect/cursors, questions, ownership, interruption, discovery and queued-message withdrawal. Existing file-router and remote-MCP tests protect Web compatibility.

For a live run, restart the application after backend or profile changes. Confirm tool discovery and effective configuration through MCP. Reconcile the original request and spending scope, delegate once with a durable client key, and follow the existing session and cursor. Recover queued messages through the native action rather than creating a replacement request. Ask the user only when a native question exceeds prior authorization.

A live check on 2026-11-08 confirmed discovery of all nine additions, local subscription authentication, actual usage and image quotes after restart. The existing session accepted the delegated continuation and issued a native regeneration approval question. After approval, its native subagents regenerated and reviewed the character and generated/reviewed three storyboards. A live resend with the same client key returned the original accepted entry without another queued request. The storyboard reviewer then blocked a visible extra person and requested a paid correction. That exposed the missing image-edit quote; `edit_images(preview=true)` now covers it through the existing planner and estimator. An interruption/restart resumed the same session for that quote. After the separately authorized one-image correction, native review accepted the storyboard. The Agent generated all three H3 clips on the first submission, used `edit-video` and `review-footage`, corrected its own rejected timeline operation, and rendered both subtitle variants through `render_final_cut`. The native acceptance receipt measured matching video/audio duration of 15.333 seconds; the Agent checked the actual files as H.264, 1080x1920, 30 fps. The same session ended completed with no queued messages or pending questions. This proves delivery for the resumed run, not independent audio review or editorial acceptance. Earlier input preparation outside MCP remains part of the test provenance. Private inputs, media and transport receipts stay outside the repository.

## Remaining acceptance limits

The current `review-footage` interface provides visual contact sheets, not actual audio evaluation. Native mechanical subtitle timing is not speech alignment. The subsequent [native speech-review implementation](native-speech-review.md) adds local transcription and conditional measured subtitle timing; it does not establish voice performance or lip synchronization. Exposing APIs alone is not grounds to claim an editorially approved end-to-end test. No external production harness, subtitle sidecar or paid evaluator is introduced.
