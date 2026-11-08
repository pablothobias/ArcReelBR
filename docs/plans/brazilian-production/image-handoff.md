# Local image handoff

Use the existing authenticated HTTP upload routes. A separate MCP image store or provider is unnecessary for local file ingestion.

## Procedure

1. Keep the image outside formal project directories until upload. Obtain its actual local output path from the image-producing tool. Respect its usage policy and any required approved allowance.
2. Use an existing ArcReel access token in memory or a protected local credential file. Never print it or place it in a URL, issue, committed file or shell argument.
3. Confirm the target project, registered character/scene, script and storyboard item through existing reads. Upload the reusable asset with multipart `file` to `/api/v1/projects/{project}/upload/character?name={character}` (or the existing scene route).
4. Upload the storyboard with multipart `file` to `/api/v1/projects/{project}/shots/{shot}/upload/storyboard?script_file={script}`. Use each route's returned path; do not copy bytes directly into the project.
5. Read version history at `/api/v1/projects/{project}/versions/{resource_type}/{resource_id}` and workflow state. Confirm formal artifact registration and current selected version.
6. Read `/api/v1/projects/{project}/script-items/{item}/prompt-preview?script_file={script}`. Check the selected reference identity and resulting prompt before submission. Preview success alone does not prove provider availability or all provider request fields.
7. If local image generation/handoff is unavailable, use the already selected Nano Banana 2 (`gemini-3.1-flash-image`) integration only after exact-model capability, credentials and quote checks. Do not silently substitute another model.

## Evidence and limits

On 2026-11-08, a real isolated local application on port 1242 accepted both uploads through an access token. The separate validation data directory contains only synthetic fixtures. Both artifacts were current; each had one manual-upload version and a content digest. The shared generation-input assembler resolved character `Ana` to `characters/Ana.png`, and HTTP prompt preview returned 200 with the character reference and intended Portuguese literal.

[Sanitized local evidence](evidence/06-image-upload-local.json) records responses without credentials. Fixture setup used ProjectManager and a minimal narration script with validation disabled, so this is not evidence for the source/script preparation ticket or a production-ready episode.

The image was a deterministic synthetic PNG, not an AI-generated image. No paid image generation or provider request occurred. The actual Codex-generated-image round trip remains pending; the downstream preview follow-up and its limits are recorded below. Ticket #6 remains open.

Existing regression tests: `uv run python -m pytest tests/integration/server/routers/test_files_router_asset_sheet_upload.py tests/integration/server/routers/test_shot_uploads_currency.py tests/integration/server/services/admission/test_prompt_preview.py -q`: 52 passed, 2 warnings. These tests include version/currentness and prompt-reference behavior; they do not prove media-provider access.


## Exact H3 downstream preview follow-up

On 2026-11-08, a read-only follow-up used the same isolated fixture and existing selected manual-upload versions. [Sanitized downstream evidence](evidence/06-downstream-preview.json) records both role mappings into exact `MiniMax-H3` at the international `/v2/video_generation` endpoint, 2K and five seconds:

- Existing generation-input assembly selected reusable character identity `Ana`, role `asset_sheet`, from `characters/Ana.png`. An in-memory supported H3 reference-image preview maps that selected file to provider `role: reference_image`, with no first-frame/last-frame inputs. This probe does not change the saved storyboard project into a reference-video project or claim that a formal reference-video workflow was executed.
- The current selected storyboard for item `E1S01`, `storyboards/scene_E1S01.png`, maps to `role: first_frame`, with no reference-image inputs. The preview correctly resolves `ratio: adaptive` for H3 first-frame input; the provider follows the image ratio rather than the requested ratio in that mode.

For both cases, the shared production `encode_inputs` function encoded the actual selected file bytes. Decoding the resulting data URI matched the SHA-256 digest of the current version returned by the authenticated version-history route. The artifact manifest still reports current currency and version 1. The downstream preview uses the existing renderer with `placeholder_missing_assets=False`, so absent images/audio are omitted instead of appearing as demonstration placeholders. Credentials in this local preview are synthetic placeholders; the isolated server received only authenticated read requests, and no provider request or media job was created.

The existing fixture is only 64 × 96 pixels. [H3's documented image constraints](https://platform.minimax.io/docs/api-reference/video-generation-v2-create) require each dimension to be at least 256 pixels. These results therefore prove formal ingestion, selected-byte identity and downstream input-role construction, not readiness of this tiny fixture for a real H3 submission. The eventual AI-produced image must meet actual provider dimensions and be uploaded/selected through the same formal routes before the remaining end-to-end criterion can pass.

## Codex image-generation usage status

Available `image_gen__imagegen` tool metadata was inspected without invoking the tool. It exposes image creation/edit inputs and returned `image_url`/`output_hint`, but provides no numeric tariff, currency, billing unit, account allowance or actual-charge usage report. No price or zero-cost entitlement can be established from that metadata. The quote remains unknown, and no generation was invoked or allowance inferred. The actual AI-image handoff remains pending its applicable usage policy/approval; the exact Nano Banana 2 fallback remains conditional on a genuine image need, its current quote and an explicit allowance.
