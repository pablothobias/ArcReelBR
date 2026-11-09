# Production inputs by use case

**Reviewed again on 2026-11-09:** request descriptions were checked by their owning operation, not reused by field name. Cross-field/handler constraints, native UI/configuration interfaces, profile support files and adapter-specific result encoding were checked against the same pinned upstream. No production operations were executed.

Scope: **original ArcReel upstream only**, pinned to [`7149433a21b3981da521e35b517a1fbe3356cc87`](https://github.com/ArcReel/ArcReel/tree/7149433a21b3981da521e35b517a1fbe3356cc87), main resolved on 2026-11-09; commit timestamp 2026-11-09T17:06:15Z. All contracts below come from that upstream snapshot, not from the local installation or its project data. Descriptions are English explanations of the original source; functional names/enums are preserved.

Companions: [project configuration](project-configuration-inputs.md), [skills](arcreel-skills-map.md), [MCP](arcreel-mcp-map.md).

Reference boundary: use this map with its three companion maps to understand the pinned original application. It does not inventory extensions or credentials in a customized installation, prescribe host-agent responsibilities, or authorize execution. A later integration plan must establish those responsibilities against its actual target version.

## Reading guide

Persistent inputs belong to the project, asset registry or script. Per-operation inputs choose one action, selection or preview. IDs/revisions/confirmation tokens control identity and concurrency; they are not quality parameters or spending permission. Optional in a schema does not mean irrelevant to a specific creative objective.

The original upstream has **61 shared MCP declarations**. They are grouped below with every top-level request input. Additional original UI/REST forms, per-shot content and nested operations are mapped separately. External scoped calls add `project`; embedded calls are already project-bound. Listing/creating projects is unscoped.

## Cases at a glance

| Goal | Relevant native inputs | Main limit |
| --- | --- | --- |
| Adapt source text | source role/kind, ordered files, episode planning and authoring instructions | Source text does not establish audiovisual performance. |
| Preserve a character | description, original reference, approved sheet, actual shot/body binding | Uploading an original does not rewrite existing media. |
| Preserve a room/object | scene/prop definition and sheet plus references in each relevant shot | A registered but unreferenced sheet is not sent. |
| Condition a character voice | approved audio, voice_style and compatible reference-audio binding | Route/capability must admit it; narrator settings are separate. |
| Generate narration | narrator text, use_tts model/voice/rate snapshot | Does not replace native character speech. |
| Control shot appearance/action | image scene/composition, video action/camera/audio/dialogue, duration, optional end frame | No deterministic framing, acting or lip-sync guarantee. |
| Correct one image | approved image, edit target and explicit instruction | Editing and regenerating from the old prompt have different effects. |
| Edit final pacing/audio | selected version, trims, holds, source gain, transitions, BGM and narration carrier | Measured media can differ from planned duration. |
| Export | timeline, revision, narration variant and subtitle mode | Render canvas and generation resolution are different layers. |

## Native MCP inputs by use case

### Source and episode planning

#### `upload_source`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `filename` | string | Required | Plain filename ending in .txt or .md, without directories or a leading dot. |
| `content` | string | Required | Text content of the source file. |
| `on_conflict` | "fail" / "replace" / "rename" | Default "fail" | Existing source/ filename handling: fail rejects, replace overwrites, rename allocates another filename. Not applicable when role=episode. |
| `role` | "whole_source" / "episode" | Default "whole_source" | whole_source appends a registered whole-source file for episode planning; episode appends a self-sourced episode in playback order, assigns a new episode ID and proceeds directly to per-episode script planning. |
| `source_kind` | "novel" / "screenplay" or null | Optional; omit | Drama-only source kind; ignored for other content modes. novel (default) is AI-adapted; screenplay preserves the author's episode divisions, dialogue and voiceover. Replacing a registered same-name whole source preserves its existing kind. |
| `revision` | string | Optional; omit | When replacing a registered whole-source file affects split episodes, return the previous affected-episode-list revision unchanged after user confirmation; only then is replacement written. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1733).

#### `edit_source_text`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `filename` | string | Optional; omit | Registered whole-source filename under source/, for example novel.txt; choose exactly one of filename and episode_id. |
| `episode_id` | integer | Optional; omit | Episode ID whose own source is edited; only self-sourced or no-source episodes qualify. Edit a split episode through its whole-source file. Choose exactly one of episode_id and filename. |
| `replacements` | array&lt;SourceReplacement&gt; | Optional; omit | Ordered exact replacements applied sequentially to the current source; choose exactly one of replacements and text. Bounds: min length 1. |
| `text` | string | Optional; omit | Complete replacement source text; choose exactly one of text and replacements. |
| `revision` | string | Optional; omit | When editing a whole-source file affects split episodes, return the previous affected-episode-list revision unchanged after user confirmation; only then is the edit written. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1861).

#### `list_source_files`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1067).

#### `get_source_text`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `path` | string | Required | Project-relative source path under source/, taken from list_source_files, for example source/episode_1.txt. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1073).

#### `plan_episodes`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `instructions` | string | Optional; omit | Original additional episode-planning instructions, for example aligning splits to chapters; inserted verbatim into the planning prompt. Express strictness in the text and repeat them for each batch. Omitted or blank means absent; maximum 4000 characters. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L2506).

#### `reset_episode_planning`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Optional; omit | Split episode ID from which to reset: omission or the first split episode means a full reset; a later split episode preserves episodes earlier in playback order. Bounds: min 1. |
| `confirm_consumed` | boolean | Default false | Set true only after explaining affected consumed episodes and receiving user confirmation. Omit on the first call so the tool returns the impact list. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L2535).

### Script planning, authoring and confirmation

#### `generate_script_plan`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `source` | string | Optional; omit | Optional project-relative source path; omission reads source/episode_N.txt for this episode. |
| `instructions` | string | Optional; omit | Original additional instructions for this generation, injected verbatim at the end of the prompt; express strictness in the text. Omitted or blank means absent; maximum 4000 characters. Bounds: max length 4000. |
| `dry_run` | boolean | Default false | Return the constructed prompt only, without model inference. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L935).

#### `confirm_script_review`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `overwrite_revision` | string | Optional; omit | script_overwrite.revision token returned after the user accepts the loss list. Prefixed sha256-v1: and bare hex forms are equivalent; unnecessary when no formal script exists. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1039).

#### `generate_episode_script`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `instructions` | string | Optional; omit | Original additional instructions for this generation, injected verbatim at the end of the prompt; express strictness in the text. Omitted or blank means absent; maximum 4000 characters. Bounds: max length 4000. |
| `entry_ids` | array&lt;string&gt; | Optional; omit | Authoring scope of storyboard/unit IDs; omission covers all pending entries. Naming entries limits scope but does not authorize overwriting existing content. |
| `rewrite` | boolean | Default false | Explicitly rewrite all visual layers in scope; default fills gaps only, preserving each existing image/video prompt and filling only the missing side. |
| `regenerate` | boolean | Default false | Ad only: regenerate the entire formal script directly, replacing existing content. Cannot combine with entry_ids or rewrite. Existing formal content first returns a script_overwrite loss list. |
| `overwrite_revision` | string | Optional; omit | Token returned only after the user accepts the loss list: prompt_overwrite.revision for visual rewriting or script_overwrite.revision for a full redo. Prefixed sha256-v1: and bare hex forms are equivalent; not needed without overwrite. |
| `dry_run` | boolean | Default false | Return the constructed prompt only, without model inference. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L881).

#### `patch_episode_script`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories; one episode per file and one call per episode. Bounds: min length 1. |
| `base_revision` | string | Required | Current revision from get_episode_script; sha256-v1: prefix and bare hexadecimal forms are equivalent. Bounds: pattern ^(?:sha256-v1:)?[0-9a-f]{64}$. |
| `operations` | array&lt;PatchUpdateOperation or PatchInsertOperation or PatchMoveOperation or PatchRemoveOperation or PatchSplitOperation&gt; | Required | Ordered script operations update, insert, move, remove or split, committed atomically. Bounds: min items 1. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L524).

#### `patch_episode_meta`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `field` | "title" | Required | Script top-level metadata field; only title is allowed. |
| `value` | string | Required | New title; must be nonempty after trimming leading and trailing whitespace. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L2616).

#### `get_episode_script`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1081).

#### `get_script_plan_content`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1087).

#### `complete_script_plan_rebuild`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `expected_stale_script_plan_revision` | string or null | Required | Rebuild baseline copied unchanged from next_action.args.expected_stale_script_plan_revision; explicit null is required when null. Prefixed/bare hex are equivalent. Reject if it differs from the project record. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L2723).

### Draft validation

#### `open_draft`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `source` | string | Optional; omit | Optional novel-source path used to rejudge provenance only when first creating a draft from a formal script_plan; defaults to source/episode_N.txt. |

Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py#L131).

#### `patch_draft`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `content` | object | Required | Complete replacement draft body; intermediate content may fail business validation. |
| `base_revision` | string | Required | Draft revision returned by open_draft or the last patch_draft; sha256-v1: prefix and bare hexadecimal forms are equivalent. |
| `accept_formal_revision` | string or null | Optional; omit | After reconciling concurrent formal changes, explicitly accept formal_revision returned by open_draft. Prefixed/bare hex are equivalent. Explicit null accepts that the formal document is absent; omission means no acceptance. |
| `source` | string or null | Optional; omit | Optional source scope for rejudging a script_plan draft; explicit null clears the scope, omission preserves it. |

Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py#L141).

#### `promote_draft`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `base_revision` | string | Required | Draft revision returned by open_draft or the last patch_draft; sha256-v1: prefix and bare hexadecimal forms are equivalent. |

Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py#L159).

#### `discard_draft`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `base_revision` | string | Required | Draft revision returned by open_draft or the last patch_draft; sha256-v1: prefix and bare hexadecimal forms are equivalent. |

Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py#L163).

### Asset definitions and generation

#### `patch_project`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `table` | "characters" / "scenes" / "props" / "products" / null | Optional; omit | Asset-upsert branch selector, supplied together with entries; characters, scenes, props or products. |
| `entries` | object or null | Optional; omit | Nonempty asset-name to editable-fields map; new names are added and existing names merge supplied fields. Character derivatives merge by derivative name: supplied descriptions update/add, omitted variants survive. Describe changes relative to the base. |
| `settings` | object or null | Optional; omit | Exclusive settings branch; allowlisted keys: episode_target_units, episode_target_duration, source_language, brief, narration_voice, narration_speed, character_voice_binding. Null clears a field where its domain rules permit. |
| `overview` | object or null | Optional; omit | Exclusive overview branch; merge only supplied synopsis, genre, theme and world_setting fields, creating overview if absent. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L2561).

#### `rename_asset`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `table` | "characters" / "scenes" / "props" / "products" | Required | Asset table to rename within: characters, scenes, props or products. |
| `old_name` | string | Required | Existing asset name. |
| `new_name` | string | Required | New asset name; reject the whole rename on an NFC-normalized collision within this table. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L2644).

#### `merge_asset`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `table` | "characters" / "scenes" / "props" | Required | Asset table to merge within: characters, scenes or props; products are unsupported. |
| `source` | string | Required | Asset to merge away and remove from the table. |
| `target` | string | Required | Other asset in the same table to keep unchanged. |
| `as_derivative` | boolean | Default false | Characters only: merge source as a derivative of target using the source name and description; the derivative sheet remains pending generation. |
| `dry_run` | boolean | Default false | Return per-episode impact only, without changing anything. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L2670).

#### `list_pending_assets`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `type` | "character" / "scene" / "prop" / "product" | Optional; omit | Asset type to filter; omission aggregates pending assets of all types. |
| `episode_id` | integer | Optional; omit | Only assets referenced by this episode's formal script, including products and derivatives and their base characters; matches the Web episode-level scope. Cannot combine with type or names. |

Source: [server/media_tools/assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/assets.py#L69).

#### `generate_assets`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `type` | "character" / "scene" / "prop" / "product" | Optional; omit | Asset type; omission covers all types in character, scene, prop, product order. |
| `names` | array&lt;string&gt; | Optional; omit | Explicit names to generate, using base/derivative for character derivatives. Requires type; mutually exclusive with all and episode_id. Omission selects only missing sheets. Bounds: min items 1. |
| `all` | boolean | Default false | Explicitly scan all missing sheets in the selected types; mutually exclusive with names. Omitting names already means missing sheets only. |
| `episode_id` | integer | Optional; omit | Only assets referenced by this episode's formal script, including products and derivatives and their base characters; matches the Web episode-level scope. Cannot combine with type or names. |

Source: [server/media_tools/assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/assets.py#L131).

### Storyboard and grid images

#### `generate_storyboards`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `segment_ids` | array&lt;string&gt; | Optional; omit | Storyboard IDs to generate or regenerate; omission selects only entries missing storyboard images. Bounds: min items 1. |

Source: [server/media_tools/storyboards.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/storyboards.py#L82).

#### `generate_grid`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `scene_ids` | array&lt;string&gt; | Optional; omit | Regenerate grids containing these storyboard IDs; omission generates only groups still missing storyboard images. Bounds: min items 1. |
| `list_only` | boolean | Default false | Preview grid tiers, existing grid IDs/status and proposed actions; no queue, cost or pollable batch. |

Source: [server/media_tools/grid.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/grid.py#L194).

#### `split_grids`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `grid_ids` | array&lt;string&gt; | Required | Grid IDs to split into storyboard frames, for example grid_a1b2c3d4e5f6. Splitting overwrites every covered storyboard image while preserving version history. Bounds: min items 1. |

Source: [server/media_tools/grid.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/grid.py#L538).

#### `get_prompt_preview`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. Bounds: min length 1. |
| `item_id` | string | Required | Entry ID: segment_id, scene_id, shot_id or unit_id, for example E1S01. Bounds: min length 1. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1343).

### Image correction and inspection

#### `edit_images`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "storyboard" / "character_derivative" | Required | Image type to edit; one type per call. |
| `edits` | array&lt;ImageEdit&gt; | Required | Batch of target ID and natural-language instruction pairs; duplicate IDs retain only their first edit. Bounds: min items 1. |
| `script_file` | string | Optional; omit | Script filename without directories, for example episode_1.json; required when resource_type=storyboard. |

Source: [server/media_tools/image_edits.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/image_edits.py#L213).

#### `inspect_images`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "storyboard" / "character_derivative" | Required | Image type to inspect; one type per call. |
| `ids` | array&lt;string&gt; | Required | Image IDs: asset names, storyboard entry IDs, or base/derivative for character derivatives. Bounds: min items 1. |
| `version` | integer or null | Optional; omit | Use this version number for every listed item; omission inspects each item's current version. |

Source: [server/media_tools/image_review.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/image_review.py#L53).

### Video generation and selection

#### `generate_videos`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `target` | EpisodeTarget or AllTarget or SceneTarget or SelectedTarget | Required | Video target selector with scope episode, all, scene or selected; identifies video units within the supplied script. |
| `force` | boolean | Default false | Force regeneration of existing usable videos; default reuses current/stale selected videos. Permitted only for scene or selected scope. |
| `confirmed_request_duration_seconds` | integer | Optional; omit | User-accepted provider request-duration tier after reference-video cross-tier confirmation. Does not freeze text, references or provider; a changed projected tier requires confirmation again. Bounds: min 1. |
| `confirmed_request_durations` | map&lt;string, integer&gt; | Optional; omit | Per-unit accepted request tiers, for example {"E1U1": 8}; resend the original full target set as one batch. This mapping overrides the scalar tier for named units and leaves unnamed units unaffected. Return the preview mapping unchanged after acceptance. |
| `preview` | boolean | Default false | Run the same admission as submission but enqueue nothing; return video_quote with per-unit disposition, planned/requested duration, tier changes, estimated costs and gaps. |

Source: [server/media_tools/videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/videos.py#L165).

#### `get_video_capabilities`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1067).

#### `inspect_video_units`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `unit_ids` | array&lt;string&gt; | Required | Video-unit IDs to inspect: storyboard entry IDs for storyboard video, or unit_id for reference video. Bounds: min items 1. |
| `version` | integer or null | Optional; omit | Use this video version for every listed unit; omission inspects each unit's current version. |
| `frames` | integer | Default 8 | Per-unit contact-sheet frame budget, default 8; when shot count exceeds the budget, prioritize at least one frame per shot and increase actual frames up to 24. This does not assess audio. Bounds: min 1, max 24. |

Source: [server/media_tools/video_review.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/video_review.py#L42).

#### `select_video_version`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `unit_id` | string | Required | Video-unit ID: storyboard entry ID for storyboard video, or unit_id for reference video. Bounds: min length 1. |
| `version` | integer | Required | Existing video version number to make current, starting at 1; applies to this one unit. Bounds: min 1. |

Source: [server/media_tools/video_versions.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/video_versions.py#L30).

### Separate narrator audio

#### `generate_narration_audio`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `segment_ids` | array&lt;string&gt; | Optional; omit | Unit IDs in the current script skeleton; omission selects only narrator-owned units missing narrator audio. Explicit IDs deliberately resynthesize eligible selected units even when audio already exists. Bounds: min items 1. |

Source: [server/media_tools/narration_audio.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/narration_audio.py#L130).

### Timeline editing

#### `create_timeline`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `from` | "script" / "timeline" | Required | script creates full-length hard-cut clips in current script order and requires episode; timeline copies an existing timeline in the same episode and requires timeline, with optional revision. |
| `name` | string | Required | Creator-recognizable display name, unique within the episode, for example Full version or Faster cut. Bounds: min length 1, max length 40. This names the timeline. |
| `episode` | integer or null | Optional; omit | Episode ID, not playback position; required when from=script. |
| `timeline` | string or null | Optional; omit | Timeline ID to copy from list_timelines/create_timeline; required when from=timeline. |
| `revision` | integer or null | Optional; omit | Revision to copy from list_revisions; omission copies the latest. Only permitted when from=timeline. |

Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py#L35).

#### `list_timelines`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode` | integer or null | Optional; omit | Filter to this episode ID; omission lists timelines for all episodes. |

Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py#L79).

#### `read_timeline`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |

Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py#L85).

#### `edit_timeline`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `base_revision` | integer | Required | Timeline revision this atomic operation batch is based on, taken from read_timeline revision. Bounds: min 1. |
| `summary` | string | Required | One-sentence change summary for the creator. Bounds: min length 1, max length 200. |
| `operations` | array&lt;TimelineOperation&gt; | Required | Ordered native timeline operations, committed atomically as one batch; use the TimelineOperation discriminated union, not script-patch operations. Bounds: min items 1. |

Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py#L91).

#### `rename_timeline`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `name` | string | Required | New display name, unique within the episode. Bounds: min length 1, max length 40. This names the timeline. |

Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py#L104).

#### `list_revisions`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |

Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py#L115).

#### `restore_revision`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `revision` | integer | Required | Historical timeline revision number to restore, from list_revisions; restoration appends a new revision. Bounds: min 1. |

Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py#L121).

#### `list_bgm`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/media_tools/bgm.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/bgm.py#L16).

### Delivery

#### `render_final_cut`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `revision` | integer | Optional; omit | Timeline revision to render; omission takes the latest revision at submission time. |
| `narration` | DraftNarration | Optional; omit | without_narration excludes narrator audio; with_narration includes it and is available only for TTS projects. Omission selects with_narration for TTS projects, otherwise without_narration. |
| `burn_subtitles` | boolean | Default true | Burn subtitles into the rendered image; false produces video without burned subtitles. |

Source: [server/media_tools/final_cuts.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/final_cuts.py#L35).

#### `export_jianying_draft`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `revision` | integer | Optional; omit | Timeline revision to export; omission takes the latest revision at submission time. |
| `narration` | DraftNarration | Optional; omit | without_narration omits the narrator track; with_narration includes it and is available only for TTS projects. Omission selects with_narration for TTS projects, otherwise without_narration. |

Source: [server/media_tools/jianying_drafts.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/jianying_drafts.py#L28).

### Provider asset library

#### `get_provider_asset_links`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "character_derivative" | Required | Image type whose provider-library associations are queried. |
| `resource_id` | string | Required | Image resource ID: asset name, or base/derivative for a character derivative. Bounds: min length 1, max length 512. |
| `recheck` | boolean | Default false | Ask the backend to recheck pending ingestion immediately; needed only when polling=false and the status remains unresolved. |

Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py#L37).

#### `list_provider_library_assets`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `account_id` | integer | Required | Provider-library account ID from get_provider_asset_links accounts[].id. Bounds: min 1. |
| `page` | integer | Default 1 | Page number, starting at 1. Bounds: min 1, max 200. |
| `page_size` | integer | Default 20 | Number of provider-library items per page. Bounds: min 1, max 100. |

Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py#L48).

#### `upload_to_provider_asset_library`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "character_derivative" | Required | Image type to upload. |
| `resource_id` | string | Required | Image resource ID: asset name, or base/derivative for a character derivative. Bounds: min length 1, max length 512. |
| `account_id` | integer | Required | Provider-library account ID from get_provider_asset_links accounts[].id. Bounds: min 1. |
| `user_requested` | true | Required | Pass true only when the user explicitly requested uploading this image to the provider library. Rejected generation, an agent's belief that upload would help, and questions about the library are not authorization. |

Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py#L56).

#### `select_provider_library_asset`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "character_derivative" | Required | Destination native image type. |
| `resource_id` | string | Required | Image resource ID: asset name, or base/derivative for a character derivative. Bounds: min length 1, max length 512. |
| `account_id` | integer | Required | Provider-library account ID from get_provider_asset_links accounts[].id. Bounds: min 1. |
| `asset_id` | string | Required | Provider asset ID from list_provider_library_assets items[].id. Bounds: min length 1, max length 256. |

Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py#L70).

#### `release_provider_asset_link`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `link_id` | integer | Required | Association ID from get_provider_asset_links links[].id. Bounds: min 1. |

Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py#L81).

### Project entry and material reads

#### `list_projects`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1067).

#### `create_project`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string | Required | Unique project identifier containing only letters, digits and hyphens; subsequent tools address the project by this name. |
| `title` | string | Default "" | User-visible project title. |
| `content_mode` | "narration" / "drama" / "ad" | Default "narration" | Content type: narration for narrated storytelling/commentary, drama for episodic drama, or ad for advertising/general short films. |
| `generation_mode` | "storyboard" / "reference_video" | Default "storyboard" | Creation route: storyboard generates storyboard images before video; reference_video generates video directly from reference images. |
| `grid_storyboard` | boolean | Default false | Enable grid storyboards; unsupported for ad projects. |
| `aspect_ratio` | string | Default "9:16" | Output aspect ratio, for example 9:16 or 16:9. |
| `default_duration` | integer or null | Optional; omit | Default planned shot duration in seconds; omitted means do not persist a value and use model capabilities. Unavailable for ad projects. |
| `target_duration` | integer or null | Optional; omit | Target final-video duration in seconds; available only for ad projects. |
| `brief` | string or null | Optional; omit | Creative brief, including selling points or intended audience; available only for ad projects. |
| `narration_delivery` | "post_production" / "use_tts" | Default "post_production" | post_production delivers voiceover text/subtitles for the creator to dub later; use_tts generates narrator audio in ArcReel. The user can change this later in project settings. |
| `audio_backend` | string | Optional; omit | TTS provider/model, used only for use_tts; omitted values are filled from the global default at creation and become a project snapshot. |
| `narration_voice` | string | Optional; omit | Narrator voice ID, used only for use_tts; omitted values are filled from the global default at creation. |
| `narration_speed` | number or null | Optional; omit | Positive TTS rate multiplier, used only for use_tts; omission fills the global default, while explicit null omits rate from the provider request. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1684).

#### `get_project_content`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1067).

#### `list_project_files`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1067).

#### `read_project_file`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `path` | string | Required | Project-relative business-file path from list_project_files, for example project.json or scripts/episode_1.json. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1093).

### Workflow, batches and recovery

#### `get_workflow_plan`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer or null | Optional; omit | Episode ID to plan; omission selects the current episode in playback order. |
| `confirmed_request_durations` | map&lt;string, integer&gt; | Optional; omit | User-accepted request-duration tiers as unit-ID to seconds mapping; applies only to this workflow plan's video-admission check. |

Source: [lib/workflow/workflow_plan.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/workflow/workflow_plan.py#L37).

#### `get_generation_batch`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `batch_id` | string | Required | Durable generation-batch ID from generation_batch.batch_id returned by a generation tool. Bounds: min length 1. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L330).

#### `cancel_generation_batch`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `batch_id` | string | Required | Durable generation-batch ID from generation_batch.batch_id returned by a generation tool. Bounds: min length 1. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L330).

#### `retry_project_migration`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1067).

#### `delete_project_file`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `path` | string | Required | Project-relative path using forward slashes, for example storyboards/scene_E1S02.png; only admitted unreferenced files/history may be trashed, not arbitrary project state. Bounds: min length 1. |

Source: [server/media_tools/project_trash.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/project_trash.py#L29).

#### `list_trash_records`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py#L1067).

#### `restore_trash_record`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `record_id` | string | Required | Trash-record ID from list_trash_records or delete_project_file. Bounds: min length 1. |

Source: [server/media_tools/project_trash.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/project_trash.py#L35).

## Cross-field rules that change behavior

- Ad projects use target_duration/brief; they reject default_duration and grids. Generation route is creation-fixed.
- Asset names require a selected type; names/all/episode scope have their native mutual exclusions. Omission normally fills missing sheets; explicit names can request regeneration.
- A storyboard model request uses the current formal script prompt and registered input imagery. Changing a default or passing a compatibility prompt body does not replace canonical script content.
- generate_videos.preview=true returns native admission/quote without queueing; force applies only to scene/selected targets. Preserve native accepted duration-tier mappings after confirmation.
- **edit_images has no preview input in this upstream contract.** It submits paid editing. Do not assume another operation’s preview flag applies here.
- First/end-frame and reference-image/audio conditioning are route/provider contracts. Query current native capabilities; a declared provider limit is not a promise of exact likeness or voice.
- Confirmations/overwrite revisions guard user intent and concurrent changes. Stale means older usable input basis, not automatic permission to pay for replacement.
- Native inspector contact sheets support visual review; they do not independently assess spoken-word fidelity, vocal performance or lip synchronization.

## Additional native UI and REST forms

These original UI contracts include manual source/episode changes, per-episode instruction persistence, reference-video bodies, auditions, end-frame selection, timeline/output and library application. They are not extra arguments accepted by MCP tools. Source links identify the owning router. Project and item identifiers in route paths locate the object.

### `generate.GenerateStoryboardRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `prompt` | string or object | Required | Compatibility request prompt; queued storyboard/image/video work reads the authoritative current formal script prompt, not this replacement text. |
| `script_file` | string | Required | Formal script filename identifying this episode. |

Source: [server/routers/generate.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/generate.py#L83).

### `generate.GenerateVideoRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `prompt` | string or object | Required | Compatibility request prompt; queued storyboard/image/video work reads the authoritative current formal script prompt, not this replacement text. |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `duration_seconds` | integer or null | Optional; omit | Compatibility request duration fallback; current script planned duration is preferred by the queued worker before its capability-tier validation. |
| `seed` | integer or null | Optional; omit | Generic compatibility seed; actual effect depends on provider/channel transmission. |

Source: [server/routers/generate.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/generate.py#L88).

### `generate.GenerateTtsRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |

Source: [server/routers/generate.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/generate.py#L98).

### `generate.GenerateVoiceSampleRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `text` | string | Required | Exact text synthesized for this character-voice audition. |
| `voice` | string | Required | Explicit audio-provider voice selected for the character audition. |

Source: [server/routers/generate.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/generate.py#L102).

### `generate.ConfirmVoiceSampleRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `task_id` | string | Required | Completed validated voice-sample task to confirm as the character’s reference. |

Source: [server/routers/generate.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/generate.py#L107).

### `generate.EditImageRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | string | Required | Native asset/media category being addressed. |
| `resource_id` | string | Required | Stable identity/name of the selected asset or script unit. |
| `instruction` | string | Required | Local image-edit instruction describing the intended correction while preserving unrelated approved content. |
| `script_file` | string or null | Optional; omit | Formal script filename identifying this episode. |

Source: [server/routers/generate.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/generate.py#L111).

### `prompt_authoring.PromptAuthoringInstructions`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `instructions` | string or null | Optional; omit | Additional per-episode directions saved/prefilled by the native instruction workflow; whitespace clears the saved value. |

Source: [server/routers/prompt_authoring.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/prompt_authoring.py#L37).

### `prompt_authoring.AuthorPromptsRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `instructions` | string or null | Optional; omit | Additional per-episode directions saved/prefilled by the native instruction workflow; whitespace clears the saved value. |
| `entry_ids` | array&lt;string&gt; or null | Optional; omit | Formal script entries within authoring scope; selecting them does not itself authorize overwriting existing prompts. |
| `rewrite` | boolean | Default false | Replace existing visual layers in scope rather than only fill pending values. |
| `overwrite_revision` | string or null | Optional; omit | Native accepted formal-script overwrite revision from the server’s impact response. |

Source: [server/routers/prompt_authoring.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/prompt_authoring.py#L43).

### `script_plan.ScriptPlanInstructions`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `instructions` | string or null | Optional; omit | Additional per-episode directions saved/prefilled by the native instruction workflow; whitespace clears the saved value. |

Source: [server/routers/script_plan.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/script_plan.py#L36).

### `ad_script.AdScriptRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `instructions` | string or null | Optional; omit | Additional directions for this ad-script generation only; this form does not save them. |
| `regenerate` | boolean | Default false | Explicit whole-script regeneration subject to native overwrite impact acceptance. |
| `overwrite_revision` | string or null | Optional; omit | Native accepted formal-script overwrite revision from the server’s impact response. |

Source: [server/routers/ad_script.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/ad_script.py#L34).

### `reference_videos.ScriptPreviewRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `prompt` | string | Default "" | Reference-video unit body using native asset/speech syntax, edited or previewed before native validation. |

Source: [server/routers/reference_videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/reference_videos.py#L99).

### `reference_videos.AddUnitRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `prompt` | string | Required | Reference-video unit body using native asset/speech syntax, edited or previewed before native validation. |
| `duration_seconds` | integer or null | Optional; omit | Planned duration in seconds, subject to route/model validation. |
| `note` | string or null | Optional; omit | User annotation, not automatically spoken or rendered. |
| `after_unit_id` | string or null | Optional; omit | Reference-video unit after which to insert/move; omit according to the native route’s append/beginning behavior. |

Source: [server/routers/reference_videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/reference_videos.py#L103).

### `reference_videos.GenerateUnitRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `confirmed_request_duration_seconds` | integer or null | Optional; omit | Accepted request-duration tier from native cross-tier confirmation. |

Source: [server/routers/reference_videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/reference_videos.py#L116).

### `reference_videos.GenerateUnitsBatchRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `unit_ids` | array&lt;string&gt; or null | Optional; omit | Explicit reference-video unit selection; omission fills missing units, explicit IDs request the native selected regeneration flow. |
| `confirmed_request_durations` | map&lt;string, integer&gt; | Optional; omit | Per-unit accepted request-duration tiers; preserve the original batch selection. |

Source: [server/routers/reference_videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/reference_videos.py#L126).

### `reference_videos.PatchUnitRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `prompt` | string or null | Optional; omit | Reference-video unit body using native asset/speech syntax, edited or previewed before native validation. |
| `duration_seconds` | integer or null | Optional; omit | Planned duration in seconds, subject to route/model validation. |
| `note` | string or null | Optional; omit | User annotation, not automatically spoken or rendered. |

Source: [server/routers/reference_videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/reference_videos.py#L359).

### `reference_videos.MoveUnitRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `after_unit_id` | string or null | Required | Reference-video unit after which to insert/move; omit according to the native route’s append/beginning behavior. |

Source: [server/routers/reference_videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/reference_videos.py#L436).

### `reference_videos.UnitPromptPreviewRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `prompt` | string | Required | Reference-video unit body using native asset/speech syntax, edited or previewed before native validation. |

Source: [server/routers/reference_videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/reference_videos.py#L515).

### `episode_planning.PlanningGap`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `source_file` | string | Required | Registered whole-source file containing the source coordinate for this operation. |
| `end` | integer | Required | Source coordinate where the extracted range ends; not elapsed video time. Bounds: greater than 0. |

Source: [server/routers/episode_planning.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_planning.py#L59).

### `episode_planning.EpisodePlanningRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `instructions` | string or null | Optional; omit | Original additional instructions for this episode planning/replanning request; whitespace means no extra directions. |
| `gap` | PlanningGap or null | Optional; omit | Specific source gap to plan, including source file and endpoint. |

Source: [server/routers/episode_planning.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_planning.py#L66).

### `episode_planning.EpisodeReplanRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode` | integer | Required | Stable episode identity, not playback position. Bounds: greater than 0. |
| `instructions` | string or null | Optional; omit | Original additional instructions for this episode planning/replanning request; whitespace means no extra directions. |
| `dry_run` | boolean | Default false | Preview this planning/structural operation without adopting the changes or starting its model work. |

Source: [server/routers/episode_planning.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_planning.py#L144).

### `episode_planning.ReplanContinueRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `candidate_id` | string | Required | Existing replan candidate to continue, adopt or discard. |

Source: [server/routers/episode_planning.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_planning.py#L177).

### `episode_planning.ReplanAdoptRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `candidate_id` | string | Required | Existing replan candidate to continue, adopt or discard. |
| `revision` | string or null | Optional; omit | Server-provided source/episode impact revision confirming the exact affected state, not a timeline revision. |
| `delete_retired` | boolean | Default false | Apply the native deletion choice for episodes retired by adopting this replan candidate. |

Source: [server/routers/episode_planning.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_planning.py#L196).

### `episode_planning.ReplanDiscardRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `candidate_id` | string | Required | Existing replan candidate to continue, adopt or discard. |

Source: [server/routers/episode_planning.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_planning.py#L206).

### `episode_management.CreateEpisodeRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `after` | integer or null | Optional; omit | Existing episode after which to insert/move; not its playback position. |
| `title` | string | Default "" | User-visible title of the episode being created/edited. Bounds: max length 200. |
| `hook` | string | Default "" | Episode-ending hook/context. Bounds: max length 2000. |
| `source_text` | string or null | Optional; omit | Optional original text owned by the new manual episode; not an existing traceability-only excerpt. |
| `source_kind` | "novel" / "screenplay" or null | Optional; omit | Novel or screenplay source semantics for applicable drama content. |

Source: [server/routers/episode_management.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_management.py#L33).

### `episode_management.DeleteEpisodeRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `revision` | string or null | Optional; omit | Server-provided source/episode impact revision confirming the exact affected state, not a timeline revision. |

Source: [server/routers/episode_management.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_management.py#L46).

### `episode_management.MoveEpisodeRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `after` | integer or null | Required | Existing episode after which to insert/move; not its playback position. |

Source: [server/routers/episode_management.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_management.py#L53).

### `episodes_view.AdoptSourceFileRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `target` | "whole_source" / "episode" | Required | Adopt this unregistered file as a whole-source file or episode-owned source; the declared enum selects the destination. |
| `episode` | integer or null | Optional; omit | Stable episode identity, not playback position. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L119).

### `episodes_view.CutRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `confirm_episodes` | array&lt;integer&gt; | Optional; omit | Acknowledged episode IDs affected by this source-range operation. |
| `dry_run` | boolean | Default false | Preview this planning/structural operation without adopting the changes or starting its model work. |
| `action` | "cut" | Required | Native operation discriminator or described performance, according to its owning model. |
| `source_file` | string | Required | Registered whole-source file containing the source coordinate for this operation. |
| `end` | integer | Required | Source coordinate where the extracted range ends; not elapsed video time. |
| `title` | string | Default "" | User-visible title of the episode being created/edited. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L162).

### `episodes_view.SplitRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `confirm_episodes` | array&lt;integer&gt; | Optional; omit | Acknowledged episode IDs affected by this source-range operation. |
| `dry_run` | boolean | Default false | Preview this planning/structural operation without adopting the changes or starting its model work. |
| `action` | "split" | Required | Native operation discriminator or described performance, according to its owning model. |
| `episode` | integer | Required | Stable episode identity, not playback position. |
| `at` | integer | Required | Source coordinate for the split/moved episode boundary; not elapsed video time. |
| `source_file` | string or null | Optional; omit | Registered whole-source file containing the source coordinate for this operation. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L169).

### `episodes_view.MoveBoundaryRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `confirm_episodes` | array&lt;integer&gt; | Optional; omit | Acknowledged episode IDs affected by this source-range operation. |
| `dry_run` | boolean | Default false | Preview this planning/structural operation without adopting the changes or starting its model work. |
| `action` | "move_boundary" | Required | Native operation discriminator or described performance, according to its owning model. |
| `episode` | integer | Required | Stable episode identity, not playback position. |
| `at` | integer | Required | Source coordinate for the split/moved episode boundary; not elapsed video time. |
| `source_file` | string or null | Optional; omit | Registered whole-source file containing the source coordinate for this operation. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L177).

### `episodes_view.MergeNextRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `confirm_episodes` | array&lt;integer&gt; | Optional; omit | Acknowledged episode IDs affected by this source-range operation. |
| `dry_run` | boolean | Default false | Preview this planning/structural operation without adopting the changes or starting its model work. |
| `action` | "merge_next" | Required | Native operation discriminator or described performance, according to its owning model. |
| `episode` | integer | Required | Stable episode identity, not playback position. |
| `confirm_merged_units` | integer | Default 0 | Acknowledged merged reading-volume amount from the impact checklist, rechecked before commit. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L185).

### `episodes_view.ClearAfterRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `confirm_episodes` | array&lt;integer&gt; | Optional; omit | Acknowledged episode IDs affected by this source-range operation. |
| `dry_run` | boolean | Default false | Preview this planning/structural operation without adopting the changes or starting its model work. |
| `action` | "clear_after" | Required | Native operation discriminator or described performance, according to its owning model. |
| `episode` | integer | Required | Stable episode identity, not playback position. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L192).

### `episodes_view.SetSourceFileKindRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `source_kind` | "novel" / "screenplay" | Required | Novel or screenplay source semantics for applicable drama content. |
| `confirm` | boolean | Default false | Acceptance of the native operation’s reported impact; not permission for unrelated work. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L272).

### `episodes_view.EditSourceFileRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `revision` | string or null | Optional; omit | Server-provided source/episode impact revision confirming the exact affected state, not a timeline revision. |
| `text` | string | Required | Replacement source text or unit-body text for this operation. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L325).

### `episodes_view.MoveSourceFileRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `revision` | string or null | Optional; omit | Server-provided source/episode impact revision confirming the exact affected state, not a timeline revision. |
| `direction` | "up" / "down" | Required | Declared binding direction for this graph target. |

Source: [server/routers/episodes_view.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episodes_view.py#L329).

### `episode_drafts.SaveDraftRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `content` | object | Required | Replacement draft document body; not a project configuration map. |
| `base_revision` | string | Required | Current draft/script canonical revision required to avoid concurrent overwrite. |

Source: [server/routers/episode_drafts.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_drafts.py#L71).

### `episode_drafts.RepairDraftBody`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `base_revision` | string | Required | Current draft/script canonical revision required to avoid concurrent overwrite. |
| `instructions` | string or null | Optional; omit | Additional directions for repairing this selected draft; repair may run the configured text model. |

Source: [server/routers/episode_drafts.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/episode_drafts.py#L78).

### `edit_timelines.CreateEditTimelineRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `from` | "script" | Required | Timeline creation source; distinct copy forms accept a source revision. |
| `name` | string | Required | User-visible editing-timeline name, unique under the native episode rules. |

Source: [server/routers/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/edit_timelines.py#L156).

### `edit_timelines.CopyEditTimelineRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string | Required | User-visible editing-timeline name, unique under the native episode rules. |
| `revision` | integer or null | Optional; omit | Existing timeline revision number to copy, restore, render or export; omission selects the route’s latest revision. |

Source: [server/routers/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/edit_timelines.py#L163).

### `edit_timelines.RenameEditTimelineRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string | Required | User-visible editing-timeline name, unique under the native episode rules. |

Source: [server/routers/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/edit_timelines.py#L170).

### `edit_timelines.RestoreEditTimelineRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `revision` | integer | Required | Existing timeline revision number to copy, restore, render or export; omission selects the route’s latest revision. Bounds: min 1. |

Source: [server/routers/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/edit_timelines.py#L176).

### `edit_timelines.RenderFinalCutBody`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `revision` | integer or null | Optional; omit | Existing timeline revision number to copy, restore, render or export; omission selects the route’s latest revision. |
| `narration` | DraftNarration or null | Optional; omit | Separate-narration output variant; with_narration is available only to applicable TTS projects. |
| `subtitles` | SubtitleMode or null | Optional; omit | Final-cut subtitle variant, distinct from the MCP boolean burn_subtitles. |

Source: [server/routers/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/edit_timelines.py#L182).

### `edit_timelines.ExportJianyingDraftBody`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `revision` | integer or null | Optional; omit | Existing timeline revision number to copy, restore, render or export; omission selects the route’s latest revision. |
| `narration` | DraftNarration or null | Optional; omit | Separate-narration output variant; with_narration is available only to applicable TTS projects. |

Source: [server/routers/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/edit_timelines.py#L442).

### `assets.UpdateAssetRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string or null | Optional; omit | Global-library asset display name. |
| `description` | string or null | Optional; omit | Canonical appearance/change description for this asset or a descriptive metadata field in its owning schema. |
| `voice_style` | string or null | Optional; omit | Soft timbre/accent/performance description for character-voice prompting. |

Source: [server/routers/assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/assets.py#L309).

### `assets.FromProjectRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `project_name` | string | Required | ArcReel project supplying the referenced native asset. |
| `resource_type` | string | Required | Native asset/media category being addressed. |
| `resource_id` | string | Required | Stable identity/name of the selected asset or script unit. |
| `override_name` | string or null | Optional; omit | Optional display-name override when copying into the global library. |
| `overwrite` | boolean | Default false | Explicit replacement of an existing same-name library asset under native validation. |

Source: [server/routers/assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/assets.py#L412).

### `assets.ApplyToProjectRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `asset_ids` | array&lt;string&gt; | Required | Existing global-library assets to apply to the project. |
| `target_project` | string | Required | ArcReel project receiving selected global-library assets. |
| `conflict_policy` | string | Default "skip" | How same-name assets are handled when applying library content; use the declared enum. |

Source: [server/routers/assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/assets.py#L792).

### `provider_asset_links.UploadRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | string | Required | Native asset/media category being addressed. Bounds: min length 1, max length 64. |
| `resource_id` | string | Required | Stable identity/name of the selected asset or script unit. Bounds: min length 1, max length 512. |
| `account_id` | integer | Required | Configured provider asset-library account identity. |

Source: [server/routers/provider_asset_links.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/provider_asset_links.py#L31).

### `provider_asset_links.ImportRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | string | Required | Native asset/media category being addressed. Bounds: min length 1, max length 64. |
| `resource_id` | string | Required | Stable identity/name of the selected asset or script unit. Bounds: min length 1, max length 512. |
| `account_id` | integer | Required | Configured provider asset-library account identity. |
| `asset_id` | string | Required | Existing provider/global-library asset identity. Bounds: min length 1, max length 256. |

Source: [server/routers/provider_asset_links.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/provider_asset_links.py#L37).

### `asset_sheets.AssetSheetBatchRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `asset_type` | "character" / "scene" / "prop" / "product" or null | Optional; omit | Selected sheet-generation asset category. |
| `episode_id` | integer or null | Optional; omit | Stable episode identity selecting the referenced asset scope. |

Source: [server/routers/asset_sheets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/asset_sheets.py#L58).

### `end_frames.SelectEndFrameRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `source_path` | string | Required | Existing admitted project image copied into a canonical final-frame snapshot. |

Source: [server/routers/end_frames.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/end_frames.py#L41).

### Upload inputs and persistence

| Native interface | Inputs | Effect |
| --- | --- | --- |
| Generic upload | project_name, upload_type, multipart file; optional name, on_conflict, role, insert_at, source_kind, revision | Source import, approved sheets, character/product originals, character audio or BGM according to upload_type. Native validation and impact checks apply. |
| Character voice audition | project/character path; text, voice | Queues a candidate TTS sample. Confirmation with task_id saves it as the character reference. It is independent of narrator delivery and may incur synthesis cost. |
| End-frame upload/select/clear | project/shot path; script_file; multipart file or source_path | Copies a canonical end-frame snapshot or clears its binding. Generic script PATCH cannot write that path. |
| Script-plan instruction PUT | project/episode path; instructions | Saves additional per-episode script-planning instructions; whitespace clears them. |
| Prompt-authoring instruction PUT | project/episode path; instructions | Saves per-episode authoring direction; entry selection/rewrite belongs to the corresponding authoring operation. |
| Ad generation instructions | instructions, regenerate, overwrite_revision | Additional directions for that generation, without saving those temporary instructions. |

Upload types: source, character, character_ref, character_audio_ref, scene, prop, product, product_ref, bgm. Native source upload accepts .txt/.md/.docx/.epub/.pdf; the MCP upload_source body is text-only. Character audio accepts WAV/MP3, 2-10 seconds and at most 15 MB. Derivative images and style-image analysis use dedicated original routes. Style analysis replaces prior style text/template choice. These rules are inputs, not an instruction to upload or generate.

Sources: [server/routers/files.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/files.py), [server/routers/generate.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/generate.py), [server/routers/end_frames.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/end_frames.py), [server/routers/prompt_authoring.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/prompt_authoring.py), [server/routers/script_plan.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/script_plan.py), [server/routers/ad_script.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/ad_script.py).

## Persistent shot and unit inputs

### `AdShot`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `shot_id` | string | Required | Stable ad storyboard identity allocated by the server. |
| `section` | string | Required | Ad/short-film narrative or sales section label. |
| `duration_seconds` | integer | Required | Planned duration in seconds, subject to route/model validation. Bounds: min 1, max 60. |
| `voiceover_text` | string | Required | Canonical separate narrator copy; may be empty for dialogue-led ad shots. |
| `characters_in_shot` | array&lt;string&gt; | Optional; omit | Registered characters visually present in this ad shot. |
| `scenes` | array&lt;string&gt; | Optional; omit | Registered scene-sheet bindings actually referenced by this item. |
| `props` | array&lt;string&gt; | Optional; omit | Registered prop-sheet bindings actually referenced by this item. |
| `products_in_shot` | array&lt;string&gt; | Optional; omit | Registered products actually appearing in this ad shot. |
| `image_prompt` | ImagePrompt | Required | Structured static image scene/composition, supported text form, or pending null under native rules. |
| `video_prompt` | VideoPrompt | Required | Structured motion/camera/ambient audio and applicable speech, supported text form, or pending null. |

### `NarrationSegment`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `segment_id` | string | Required | Stable narration storyboard identity allocated by the server. |
| `duration_seconds` | integer | Required | Planned duration in seconds, subject to route/model validation. Bounds: min 1, max 60. |
| `segment_break` | boolean | Default false | Whether this narration/drama item starts a new scene/chapter and stops predecessor-storyboard conditioning. |
| `novel_text` | string | Required | Canonical source narration text for the narration segment. |
| `characters_in_segment` | array&lt;string&gt; | Required | Registered characters visually present in this narration segment. |
| `scenes` | array&lt;string&gt; | Optional; omit | Registered scene-sheet bindings actually referenced by this item. |
| `props` | array&lt;string&gt; | Optional; omit | Registered prop-sheet bindings actually referenced by this item. |
| `image_prompt` | ImagePrompt | Optional; omit | Structured static image scene/composition, supported text form, or pending null under native rules. |
| `video_prompt` | VideoPrompt | Optional; omit | Structured motion/camera/ambient audio and applicable speech, supported text form, or pending null. |

### `DramaScene`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `scene_id` | string | Required | Stable drama storyboard identity allocated by the server. Bounds: min length 1. |
| `duration_seconds` | integer | Default 8 | Planned duration in seconds, subject to route/model validation. Bounds: min 1, max 60. |
| `segment_break` | boolean | Default false | Whether this narration/drama item starts a new scene/chapter and stops predecessor-storyboard conditioning. |
| `characters_in_scene` | array&lt;string&gt; | Required | Registered characters visually present in this drama scene. |
| `scenes` | array&lt;string&gt; | Optional; omit | Registered scene-sheet bindings actually referenced by this item. |
| `props` | array&lt;string&gt; | Optional; omit | Registered prop-sheet bindings actually referenced by this item. |
| `image_prompt` | ImagePrompt | Optional; omit | Structured static image scene/composition, supported text form, or pending null under native rules. |
| `video_prompt` | DramaVideoPrompt | Optional; omit | Structured motion/camera/ambient audio and applicable speech, supported text form, or pending null. |
| `utterances` | array&lt;Utterance&gt; | Optional; omit | Ordered drama dialogue/voiceover speech entries. |
| `source_text` | string | Default "" | Source text assigned to this episode or its declared traceability excerpt. |

### `ReferenceVideoUnit`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `unit_id` | string | Required | Stable reference-video unit identity allocated by the server. |
| `text` | string | Required | Replacement source text or unit-body text for this operation. |
| `duration_seconds` | integer | Required | Planned duration in seconds, subject to route/model validation. Bounds: min 0, max 300. |

### `ImagePrompt`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `scene` | string | Required | Static image description; movement belongs in the video action. |
| `composition` | Composition | Required | Shot composition, lighting and atmosphere object. |

### `Composition`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `shot_type` | "Extreme Close-up" / "Close-up" / "Medium Close-up" / "Medium Shot" / "Medium Long Shot" / "Long Shot" / "Extreme Long Shot" / "Over-the-shoulder" / "Point-of-view" | Required | Shot-size/framing category from the native accepted values. |
| `lighting` | string | Required | Lighting direction, quality and color/ambience instructions for the static frame. |
| `ambiance` | string | Required | Overall visual atmosphere. |

### `VideoPrompt`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `action` | string | Required | Native operation discriminator or described performance, according to its owning model. |
| `camera_motion` | "Static" / "Pan Left" / "Pan Right" / "Tilt Up" / "Tilt Down" / "Zoom In" / "Zoom Out" / "Push In" / "Pull Out" / "Truck Left" / "Truck Right" / "Pedestal Up" / "Pedestal Down" / "Orbit" / "Tracking Shot" / "Shake" | Required | Camera movement; static camera alone does not explicitly prohibit internal cuts. |
| `ambiance_audio` | string | Required | Diegetic environmental sound, separate from narrator synthesis and timeline BGM. |
| `dialogue` | array&lt;Dialogue&gt; | Optional; omit | Ad/legacy dialogue entries naming speakers and their canonical spoken lines. |

### `DramaVideoPrompt`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `action` | string | Required | Native operation discriminator or described performance, according to its owning model. |
| `camera_motion` | "Static" / "Pan Left" / "Pan Right" / "Tilt Up" / "Tilt Down" / "Zoom In" / "Zoom Out" / "Push In" / "Pull Out" / "Truck Left" / "Truck Right" / "Pedestal Up" / "Pedestal Down" / "Orbit" / "Tracking Shot" / "Shake" | Required | Camera movement; static camera alone does not explicitly prohibit internal cuts. |
| `ambiance_audio` | string | Required | Diegetic environmental sound, separate from narrator synthesis and timeline BGM. |

### `Dialogue`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `speaker` | string | Required | Character owning dialogue; drama voiceover requires no character speaker. |
| `line` | string | Required | Canonical dialogue line to be spoken. |

### `Utterance`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `kind` | "dialogue" / "voiceover" | Required | dialogue attributes speech to a nonempty speaker; voiceover requires speaker=null. |
| `speaker` | string or null | Optional; omit | Character owning dialogue; drama voiceover requires no character speaker. |
| `text` | string | Required | Replacement source text or unit-body text for this operation. |

Important distinctions: ad dialogue lives in video_prompt.dialogue; drama speech is ordered utterances; narration novel_text and ad voiceover_text belong to narrator speech. Reference-video text uses native @[name] references and inline speech syntax. Source excerpts trace provenance and are not automatically read aloud. note is user annotation. End-frame binding is managed through its dedicated routes. Generated-asset references, pending/replan flags and manifest/version facts are managed state.

## Nested operation and content types

### `AllTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `scope` | "all" | Required | All units in the supplied script; fill only missing videos and reuse every usable existing video. |

### `Composition`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `shot_type` | "Extreme Close-up" / "Close-up" / "Medium Close-up" / "Medium Shot" / "Medium Long Shot" / "Long Shot" / "Extreme Long Shot" / "Over-the-shoulder" / "Point-of-view" | Required | Shot type |
| `lighting` | string | Required | Lighting description |
| `ambiance` | string | Required | Overall ambiance |

### `DeleteBgm`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "delete_bgm" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | BGM-track clip ID, for example b2. Bounds: min length 1. |

### `DeleteClip`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "delete" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Main-track editing clip ID, for example c3. Bounds: min length 1. |

### `Dialogue`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `speaker` | string | Required | Speaker name |
| `line` | string | Required | Dialogue text |

### `DraftNarration`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No object fields | "without_narration" / "with_narration" | Not applicable | Use this union/enum where referenced; it is not a callable tool. |

### `DramaVideoPrompt`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `action` | string | Required | Discriminator selecting this native source-range operation. |
| `camera_motion` | "Static" / "Pan Left" / "Pan Right" / "Tilt Up" / "Tilt Down" / "Zoom In" / "Zoom Out" / "Push In" / "Pull Out" / "Truck Left" / "Truck Right" / "Pedestal Up" / "Pedestal Down" / "Orbit" / "Tracking Shot" / "Shake" | Required | Camera movement |
| `ambiance_audio` | string | Required | Environmental sound effects (diegetic audio) |

### `EpisodeTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `scope` | "episode" | Required | Whole episode; fill only missing videos and reuse every usable existing video. |
| `episode_id` | integer | Required | Episode ID that must match the episode belonging to script. Bounds: min 1. |

### `ImageEdit`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `id` | string | Required | Target ID: asset name, storyboard entry ID, or base/derivative for a character derivative. |
| `instruction` | string | Required | Natural-language instruction describing the part to change. |

### `ImagePrompt`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `scene` | string | Required | Static image description; dynamic content belongs in video_prompt.action |
| `composition` | Composition | Required | Composition information |

### `InsertBgm`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "insert_bgm" | Required | Operation discriminator; use this definition's exact literal value. |
| `bgm_id` | string | Required | Project BGM ID from list_bgm, for example bgm-3f9a0c21. Bounds: min length 1. |
| `start` | number | Required | Absolute placement time in timeline seconds; must lie within the timeline. |
| `source_in` | number | Default 0.0 | BGM source in-point in seconds; omission starts at the beginning. |
| `source_out` | number or null | Optional; omit | BGM source out-point in seconds; must exceed source_in and not exceed media duration. Omission uses the end. |
| `volume` | number | Default 0.25 | Gain from 0 to 1 applied to media normalized to -16 LUFS; default 0.25. |
| `fade_in` | number | Default 1.0 | Fade-in duration in seconds; default 1. |
| `fade_out` | number | Default 1.0 | Fade-out duration in seconds; default 1. |

### `InsertClip`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "insert" | Required | Operation discriminator; use this definition's exact literal value. |
| `unit_id` | string | Required | Video-unit ID; the same video unit may be inserted multiple times. Bounds: min length 1. |
| `after` | string or null | Required | Place after this editing clip ID; null means prepend. |
| `source_volume` | number or null | Optional; omit | Native audio gain 0 to 1; default 0.3 for voiceover units, 1.0 for dialogue or no-speech units. |
| `trim` | TrimSpec or null | Optional; omit | Source in/out trim; omission uses the whole selected video. |
| `hold` | number | Default 0.0 | End-frame hold extension in seconds, from 0 to 10. |
| `reason` | string or null | Optional; omit | Creator-facing editing reason, ignored during rendering. |
| `transition_to_next` | TransitionSpec or null | Optional; omit | Transition to the following clip; omission means a hard cut. |

### `MoveClip`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "move" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Main-track editing clip ID, for example c3. Bounds: min length 1. |
| `after` | string or null | Required | Place after this editing clip ID; null means prepend. |

### `PatchInsertOperation`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "insert" | Required | Operation discriminator; use this definition's exact literal value. |
| `after_id` | string or null | Optional; omit | Insert after this entry ID; omission or null prepends, including the first entry of an empty script. |
| `item` | object | Required | Complete new entry body; the system allocates an ID above the episode high-water mark and never reuses deleted IDs. |

### `PatchMoveOperation`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "move" | Required | Operation discriminator; use this definition's exact literal value. |
| `id` | string | Required | Entry ID to move; content and generated media move with it. Bounds: min length 1. |
| `after_id` | string or null | Optional; omit | Move after this entry ID; omission or null prepends. |

### `PatchRemoveOperation`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "remove" | Required | Operation discriminator; use this definition's exact literal value. |
| `id` | string | Required | Entry ID to remove. Bounds: min length 1. |

### `PatchSplitOperation`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "split" | Required | Operation discriminator; use this definition's exact literal value. |
| `id` | string | Required | Entry ID to split; the first part retains it and subsequent parts receive newly allocated IDs. Bounds: min length 1. |
| `parts` | array&lt;object&gt; | Required | Complete bodies for the resulting parts in order; at least two parts. Bounds: min items 2. |

### `PatchUpdateOperation`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "update" | Required | Operation discriminator; use this definition's exact literal value. |
| `id` | string | Required | Entry ID to update: segment_id, scene_id, shot_id or unit_id. Bounds: min length 1. |
| `fields` | object | Required | Map of editable field paths to new values; use dotted paths for nested fields, for example image_prompt.scene. |

### `PlaceNarration`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "place_narration" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Clip of a voiceover-owned unit that will carry narration; removes narration carriage from another clip of the same video unit. Bounds: min length 1. |

### `SceneTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `scope` | "scene" | Required | Select exactly one video unit. |
| `ids` | array&lt;string&gt; | Required | Exactly one target ID: storyboard entry ID for storyboard video or unit_id for reference video. Bounds: min items 1, max items 1. |

### `SelectedTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `scope` | "selected" | Required | Select an explicit batch of video units. |
| `ids` | array&lt;string&gt; | Required | Target IDs: storyboard entry IDs for storyboard video or unit_id for reference video. Bounds: min items 1. |

### `SetBgm`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "set_bgm" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | BGM-track clip ID, for example b2. Bounds: min length 1. |
| `start` | number or null | Optional; omit | New absolute timeline start in seconds; omission leaves unchanged. |
| `source_in` | number or null | Optional; omit | New BGM source in-point in seconds; omission leaves unchanged. |
| `source_out` | number or null | Optional; omit | New BGM source out-point in seconds; omission leaves unchanged. |
| `volume` | number or null | Optional; omit | New BGM gain from 0 to 1; omission leaves unchanged. |
| `fade_in` | number or null | Optional; omit | New fade-in seconds; omission leaves unchanged. |
| `fade_out` | number or null | Optional; omit | New fade-out seconds; omission leaves unchanged. |

### `SetHold`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "set_hold" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Main-track editing clip ID, for example c3. Bounds: min length 1. |
| `hold` | number | Required | End-frame hold extension in seconds, from 0 to 10; zero removes the extension. |

### `SetReason`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "set_reason" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Main-track editing clip ID, for example c3. Bounds: min length 1. |
| `reason` | string or null | Required | New editing reason; null clears it. |

### `SetTransition`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "set_transition" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Main-track editing clip ID, for example c3. Bounds: min length 1. |
| `transition` | TransitionSpec or null | Required | Transition to the next clip; null restores a hard cut. |

### `SetTrim`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "set_trim" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Main-track editing clip ID, for example c3. Bounds: min length 1. |
| `trim` | TrimSpec or null | Required | New source in/out points; null removes trimming and uses the whole video. |

### `SetVolume`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `op` | "set_volume" | Required | Operation discriminator; use this definition's exact literal value. |
| `clip` | string | Required | Main-track editing clip ID, for example c3. Bounds: min length 1. |
| `volume` | number | Required | Native source-audio linear gain from 0 to 1; amplification is unsupported. |

### `SourceReplacement`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `old_text` | string | Required | Exact original text that must occur exactly once in the current source. Bounds: min length 1. |
| `new_text` | string | Required | Replacement text; an empty string deletes the matched fragment. |

### `TimelineOperation`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No object fields | InsertClip or DeleteClip or MoveClip or SetTrim or SetVolume or SetHold or SetReason or SetTransition or PlaceNarration or InsertBgm or SetBgm or DeleteBgm | Not applicable | Use this union/enum where referenced; it is not a callable tool. |

### `TransitionSpec`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `type` | TransitionType | Required | Transition preset type; each native value has Jianying and ffmpeg equivalents. Hard cut is represented by no transition. |
| `duration` | number | Required | Transition duration in seconds, from 0.1 to 2. |

### `TransitionType`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No object fields | "dissolve" / "fade_black" / "fade_white" / "push_left" / "push_right" / "push_up" / "push_down" / "wipe_left" / "wipe_right" / "wipe_up" / "wipe_down" / "circle" / "curtain_horizontal" / "curtain_vertical" / "mosaic" / "blur" / "radial" / "gradient_wipe" / "squeeze" | Not applicable | Use this union/enum where referenced; it is not a callable tool. |

### `TrimSpec`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `source_in` | number | Required | In-point seconds measured from the beginning of this unit's current video. |
| `source_out` | number | Required | Out-point seconds; must exceed source_in and not exceed video duration. |

### `Utterance`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `kind` | "dialogue" / "voiceover" | Required | Reference type to upload |
| `speaker` | string or null | Optional; omit | Speaker name |
| `text` | string | Required | Source/unit text, or the exact text to synthesize in an audition, according to the case. |

### `VideoPrompt`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `action` | string | Required | Discriminator selecting this native source-range operation. |
| `camera_motion` | "Static" / "Pan Left" / "Pan Right" / "Tilt Up" / "Tilt Down" / "Zoom In" / "Zoom Out" / "Push In" / "Pull Out" / "Truck Left" / "Truck Right" / "Pedestal Up" / "Pedestal Down" / "Orbit" / "Tracking Shot" / "Shake" | Required | Camera movement |
| `ambiance_audio` | string | Required | Environmental sound effects (diegetic audio) |
| `dialogue` | array&lt;Dialogue&gt; | Optional; omit | Dialogue list; populate only when the source contains quoted dialogue |

## Additional original project-editor inputs found during review

These original forms were missing from the first map. Their route-specific wrappers are distinct from adding arbitrary fields to a generation call. Names, revisions and timing refer to the object shown in each model, not another operation.

### `projects.InsertScriptItemRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `after_id` | string or null | Optional; omit | Existing script item after which to insert/move; the native operation defines omission behavior. |
| `novel_text` | string or null | Optional; omit | Canonical source narration text for the narration segment. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1396).

### `projects.MoveScriptItemRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `after_id` | string or null | Required | Existing script item after which to insert/move; the native operation defines omission behavior. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1531).

### `projects.UpdateSceneRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `updates` | object | Required | Sparse content update map validated by this shot/scene editor’s native allowlist. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1582).

### `projects.UpdateShotRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `updates` | object | Required | Sparse content update map validated by this shot/scene editor’s native allowlist. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1663).

### `projects.UpdateSegmentRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `duration_seconds` | integer or null | Optional; omit | Planned duration in seconds, subject to route/model validation. |
| `segment_break` | boolean or null | Optional; omit | Whether this narration/drama item starts a new scene/chapter and stops predecessor-storyboard conditioning. |
| `novel_text` | string or null | Optional; omit | Canonical source narration text for the narration segment. |
| `image_prompt` | object or string or null | Optional; omit | Structured static image scene/composition, supported text form, or pending null under native rules. |
| `video_prompt` | object or string or null | Optional; omit | Structured motion/camera/ambient audio and applicable speech, supported text form, or pending null. |
| `note` | string or null | Optional; omit | User annotation, not automatically spoken or rendered. |
| `characters_in_segment` | array&lt;string&gt; or null | Optional; omit | Registered characters visually present in this narration segment. |
| `scenes` | array&lt;string&gt; or null | Optional; omit | Registered scene-sheet bindings actually referenced by this item. |
| `props` | array&lt;string&gt; or null | Optional; omit | Registered prop-sheet bindings actually referenced by this item. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1766).

### `projects.UpdateOverviewRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `synopsis` | string or null | Optional; omit | Story/project synopsis supplied to applicable planning. |
| `genre` | string or null | Optional; omit | Story genre/tone context. |
| `theme` | string or null | Optional; omit | Central story theme. |
| `world_setting` | string or null | Optional; omit | World, time and location context. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1779).

### `projects.UpdateEpisodeRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `title` | string | Required | User-visible title of the episode being created/edited. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1786).

### `projects.UpdateEpisodeSourceRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `text` | string | Required | Replacement source text or unit-body text for this operation. |
| `source_kind` | "novel" / "screenplay" or null | Optional; omit | Novel or screenplay source semantics for applicable drama content. |
| `confirm` | boolean | Default false | Acceptance of the native operation’s reported impact; not permission for unrelated work. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L1790).

### `grids.GenerateGridRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script_file` | string | Required | Formal script filename identifying this episode. |
| `scene_ids` | array&lt;string&gt; or null | Optional; omit | Storyboard identities whose grid groups should be generated/recreated; omission fills missing applicable grid outputs. |

Source: [server/routers/grids.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/grids.py#L70).

## Additional native asset CRUD and preview forms

These factory-generated original UI forms were not named individually in the initial list. They are separate from arbitrary project-setting keys.

| Form / case | Inputs | Effect / default |
| --- | --- | --- |
| Asset creation | name, description | Create an asset definition under its route’s asset category; canonical asset-type validation applies. |
| Asset rename | new_name, dry_run=false | Cascade rename; dry_run only reports affected references/files. |
| Asset merge | target, as_derivative=false, dry_run=false | Merge into existing target or supported character variant; dry_run reports the native impact. Source records and reference rewrites follow native merge semantics. |
| Character derivative creation | name, description="" | Create a name unique within its base character; description states changes relative to the base. |
| Character derivative update | description | Change relative-appearance prose only; image paths and rename use separate actions. |
| Character derivative rename | new_name | Native identity/reference-preserving rename within the base. |
| Asset/derivative prompt preview | description | Preview the image prompt for current/pending description, without saving a definition or requesting image generation. |

Sources: [server/routers/_asset_router_factory.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/_asset_router_factory.py), [server/routers/_asset_derivatives.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/_asset_derivatives.py), [server/routers/_asset_prompt_preview.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/_asset_prompt_preview.py).

## Verification

This map was regenerated from the original upstream snapshot. All 61 native top-level schemas, nested request definitions, listed UI forms and content models were checked against that source. Importing declaration/model definitions was used only to inspect schemas; no application session, generation, remote provider test or live project mutation was executed.
