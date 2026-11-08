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

The image was a deterministic synthetic PNG, not an AI-generated image. No paid image generation or provider request occurred. This historical synthetic test alone did not establish an AI-image round trip. The actual generated Nano Banana 2 fallback handoff is recorded below. No Codex image_gen origin is claimed.

Existing regression tests: `uv run python -m pytest tests/integration/server/routers/test_files_router_asset_sheet_upload.py tests/integration/server/routers/test_shot_uploads_currency.py tests/integration/server/services/admission/test_prompt_preview.py -q`: 52 passed, 2 warnings. These tests include version/currentness and prompt-reference behavior; they do not prove media-provider access.


## Exact H3 downstream preview follow-up

On 2026-11-08, a read-only follow-up used the same isolated fixture and existing selected manual-upload versions. [Sanitized downstream evidence](evidence/06-downstream-preview.json) records both role mappings into exact `MiniMax-H3` at the international `/v2/video_generation` endpoint, 2K and five seconds:

- Existing generation-input assembly selected reusable character identity `Ana`, role `asset_sheet`, from `characters/Ana.png`. An in-memory supported H3 reference-image preview maps that selected file to provider `role: reference_image`, with no first-frame/last-frame inputs. This probe does not change the saved storyboard project into a reference-video project or claim that a formal reference-video workflow was executed.
- The current selected storyboard for item `E1S01`, `storyboards/scene_E1S01.png`, maps to `role: first_frame`, with no reference-image inputs. The preview correctly resolves `ratio: adaptive` for H3 first-frame input; the provider follows the image ratio rather than the requested ratio in that mode.

For both cases, the shared production `encode_inputs` function encoded the actual selected file bytes. Decoding the resulting data URI matched the SHA-256 digest of the current version returned by the authenticated version-history route. The artifact manifest still reports current currency and version 1. The downstream preview uses the existing renderer with `placeholder_missing_assets=False`, so absent images/audio are omitted instead of appearing as demonstration placeholders. Credentials in this local preview are synthetic placeholders; the isolated server received only authenticated read requests, and no provider request or media job was created.

The existing fixture is only 64 × 96 pixels. [H3's documented image constraints](https://platform.minimax.io/docs/api-reference/video-generation-v2-create) require each dimension to be at least 256 pixels. These results therefore prove formal ingestion, selected-byte identity and downstream input-role construction, not readiness of this tiny fixture for a real H3 submission. The eventual AI-produced image must meet actual provider dimensions and be uploaded/selected through the same formal routes before the remaining end-to-end criterion can pass.

## Codex image-generation usage status

Available `image_gen__imagegen` tool metadata was inspected without invoking the tool. It exposes image creation/edit inputs and returned `image_url`/`output_hint`, but provides no numeric tariff, currency, billing unit, account allowance or actual-charge usage report. No price or zero-cost entitlement can be established from that metadata. The quote remains unknown, and no generation was invoked or allowance inferred. The unknown Codex-tool tariff was not bypassed. The separately approved existing Nano Banana 2 fallback subsequently produced the actual image used in the isolated technical handoff below.


## Actual generated fallback image handoff

The existing Nano Banana 2 fallback produced Ana version 2 under a separately approved single quality retry. That generation round is closed and settled at USD 0.0682895. The earlier rejected artificial-looking version 1 and its USD 0.0679845 charge remain preserved. Neither closed allowance was reopened for this technical test.

The original goal authorizes ticket #6's reversible ingestion validation independently of production quality acceptance. The coordinator explicitly authorized reusing the existing version 2 only in `image-handoff-fixture-6-20261108`. Two authenticated local HTTP uploads, each once, accepted that actual generated PNG: the reusable character `Ana` and storyboard `E1S01` in `episode_1.json`. No provider request, image/video generation, paid evaluation or pilot promotion occurred.

[Sanitized generated-image evidence](evidence/06-generated-image-handoff.json) records the source digest, upload responses, version history, currency and downstream construction. The 1,062,470-byte PNG is 1376 × 768, SHA-256 `1c3ed5bfce25a3ee8499a7fe4e2182086be897281070c704493ca868d18bf90a`. Existing normalization returned these bytes unchanged. Character upload registered and selected manual version 3; storyboard upload registered and selected manual version 1. Both artifact claims are current and carry the same source digest. Generated character versions 1 and 2 remain intact, as do both closed directing records.

Storyboard registration changed only its formal `generated_assets.storyboard_image`, derived status and script `metadata.updated_at`. Restoring those three values in a private read-only reconstruction reproduces the frozen original script SHA-256 `2f7dc3d635105fd2f86131e0af3844f49dc2840ef874861c5bd30a179aea0e7b`; creative script content was preserved. No other project was modified.

The existing generation-input assembler selects character identity `Ana` from the current uploaded sheet. The production declarative asset loader and `encode_inputs` read actual selected bytes, produce `image/png` data URIs, and decode back to the source digest. Existing no-send endpoint preview renders exact `MiniMax-H3` at the international `/v2/video_generation` endpoint, 2K and five seconds. The reusable-asset probe maps that selected sheet to `reference_image`; the actual selected storyboard maps to `first_frame`, with adaptive ratio as required by that input mode. The former is an in-memory supported reference-input probe, not a saved reference-video workflow. Preview uses placeholder credentials and sends nothing to MiniMax. The evidence contains redacted data-URI summaries, not image bytes or authentication headers.

This establishes that local image handoff is practical through existing transport, formal registration and selected-image request construction, without another asset store or wrapper. It uses the agreed Nano Banana 2 fallback, not a Codex image_gen artifact. The current sheet is more photographic but cropped around the thighs, with no knees or feet; owner creative acceptance and production composition suitability remain unestablished. Uploading that sheet as an isolated storyboard tests ingestion and does not make it a production-approved storyboard or pilot asset. No further generation allowance follows from this test.
