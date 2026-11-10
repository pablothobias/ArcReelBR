# MCP coverage: open decisions and documented restrictions

These items are deliberately **not** implemented. Each one needs a product or authorization decision from the operator. This round documents them and does not widen any permission.

## MCP-022: Agent writes to the product `brand` field

**Current state (unchanged).** `brand` is user free text on product assets (`lib/project/asset_types.py`, product `AssetSpec`, `extra_string_fields=("brand",)`). It is not in `agent_editable_extra_fields`; only `selling_points` is. `patch_project` reports `brand` under `dropped_fields`. The ad prompt builder consumes the field (`lib/prompts/prompt_builders_ad.py`).

**MCP behaviour delivered in this round.** None of the new tools write `brand`:
- `arrange_product_reference_images` changes only `reference_images`, and its description says `brand` stays outside Agent writes.
- `upload_product_reference_images` adds photos and does not touch text fields.

**Options for the operator:**
1. **Keep it user-only (recommended default).** `brand` is a legal and identity claim that the user supplies, and an Agent writing it could invent or alter a trademark. An external agent asks the user and relays the value through the Web UI.
2. **Allow writes, but only from a verbatim user value.** Add a dedicated tool such as `set_product_brand(product, brand, expected_brand)`. Its description must require the exact user-supplied string. Use compare-and-swap on `expected_brand` and audit-log the change, but do **not** add `brand` to `agent_editable_extra_fields`, because that would also open it to the embedded Agent's generic patch path.
3. **Widen `agent_editable_extra_fields`.** Not recommended: it silently grants the embedded Agent the same power.

**Acceptance if option 2 is chosen.** Stale `expected_brand` returns a conflict. The `dropped_fields` behaviour of `patch_project` stays unchanged. The ad prompt preview shows the new brand. No generation is enqueued.

## MCP-023: Toggling `grid_storyboard` on an existing project

**Current state (unchanged).** `create_project` covers the initial choice. Changing the setting on an existing project is Web-only: `UpdateProjectRequest.grid_storyboard` is in `server/routers/projects.py` (around line 404, applied around 1142), and it is absent from the MCP `ConfigureProjectRequest` (`server/media_tools/workflow_access.py`). Ad projects refuse grids.

**Why it stays restricted.** The toggle changes which storyboard route later generations use. Turning it on marks existing grouping as needing grids, and grid generation can then incur image cost. That is a workflow choice the user owns. It is also not a discovery bug: `get_workflow_plan` reports the current mode.

**Options for the operator:**
1. **Keep it Web-only (recommended default).** An external agent tells the user to change it in project settings.
2. **Expose it behind explicit confirmation.** Add `grid_storyboard` to `configure_project` with `confirm_workflow_change: StrictBool`. Return the same ad-project refusal as the Web, and report which existing grids or storyboards become stale. Nothing is generated automatically.

## Storyboard route and character voice references (H3)

**Finding (documented, not fixed).** On the storyboard route, the video executor forwards the start frame, end frame and prompt, but no `reference_audio_files`. Only `server/services/tasks/reference_video_tasks.py` forwards reference audio; the storyboard video branch in `server/services/tasks/generation_tasks.py` does not. The official MiniMax H3 contract (<https://platform.minimax.io/docs/api-reference/video-generation-v2-create>, verified 2026-11-10) allows `role: reference_audio` **only in the reference-to-video scenario**. It cannot be combined with `first_frame` or `last_frame` in the same request.

**Consequence.** Character voice timbre from reference audio is available only on the `reference_video` route. Adding the audio field to storyboard requests would make H3 reject them. Silently switching the user's workflow to `reference_video` would also change their production. Neither change was made.

**Path forward (separate requirement).**
- A route- and model-aware capability flag (for example, `voice_reference_with_frames: false`) surfaced through `get_video_capabilities`, so agents can see the limitation before submitting.
- Any change of the native storyboard executor must be specified and approved separately.

## MCP-007: Chinese reference markers in rendered prompts (evidence only)

The `@图片N` and `@音频N` markers are functional literals emitted by `prompt_render.py`. They were preserved in successful H3 output. The official H3 page examined does not say whether they are required or translatable, so they are left untouched. `get_prompt_preview` and the new captured-submission view (`get_prompt_preview` with `task_id`) let an agent see the exact rendered prompt without running a generation.
