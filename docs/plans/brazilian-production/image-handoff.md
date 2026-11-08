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

The image was a deterministic synthetic PNG, not an AI-generated image. No paid image generation or provider request occurred. The actual Codex-generated-image round trip and exact downstream provider request preview remain pending; ticket #6 remains open.

Existing regression tests: `uv run python -m pytest tests/integration/server/routers/test_files_router_asset_sheet_upload.py tests/integration/server/routers/test_shot_uploads_currency.py tests/integration/server/services/admission/test_prompt_preview.py -q`: 52 passed, 2 warnings. These tests include version/currentness and prompt-reference behavior; they do not prove media-provider access.
