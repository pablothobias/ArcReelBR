# ArcReel native MCP map

**Reviewed again on 2026-11-09:** request descriptions were checked by their owning operation, not reused by field name. Cross-field/handler constraints, native UI/configuration interfaces, profile support files and adapter-specific result encoding were checked against the same pinned upstream. No production operations were executed.

Scope: **original ArcReel upstream only**, pinned to [`7149433a21b3981da521e35b517a1fbe3356cc87`](https://github.com/ArcReel/ArcReel/tree/7149433a21b3981da521e35b517a1fbe3356cc87), main resolved on 2026-11-09; commit timestamp 2026-11-09T17:06:15Z. Descriptions explain the original source in English without changing its functional names or contracts. This is not a running-instance configuration audit.

Companions: [skills](arcreel-skills-map.md), [production inputs](production-inputs-by-use-case.md), [project configuration](project-configuration-inputs.md).

Reference boundary: use this map with its three companion maps to understand the pinned original application. It does not inventory extensions or credentials in a customized installation, prescribe host-agent responsibilities, or authorize execution. A later integration plan must establish those responsibilities against its actual target version.

## What MCP exposes

The original pinned upstream declares **61 tools** once in AGENT_TOOLSET and projects them through two adapters: the embedded ArcReel Agent server and the remote streamable-HTTP server. A skill supplies workflow instructions; an MCP tool supplies a validated operation. The tool name itself does not establish user approval, price, image quality or editorial acceptance.

| Host | Project binding | Execution / result |
| --- | --- | --- |
| Embedded Agent | Session supplies ProjectScope; callers omit project. | In-process handlers run in the application service. Generation waits through the existing native waiter for terminal result. |
| Remote MCP | Every scoped call explicitly supplies project. list_projects/create_project are unscoped. | Same underlying handlers; long tasks return generation_batch immediately and are polled through get_generation_batch. |

Sources: [server/agent_toolset/toolset.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/toolset.py), [server/agent_toolset/declaration.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/declaration.py), [server/agent_toolset/embedded.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/embedded.py), [server/agent_toolset/remote.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/remote.py), [server/agent_runtime/arcreel_mcp.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_runtime/arcreel_mcp.py), [server/remote_mcp.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/remote_mcp.py).

## Native connection inputs

| Input / behavior | Description |
| --- | --- |
| Endpoint | ArcReel remote endpoint ending in /mcp, through the deployment backend or supported proxy. |
| Transport | Streamable HTTP; server is stateless_http and supports its native streamed responses. |
| Authentication | Bearer API key with arc- prefix, checked by ArcApiKeyVerifier through the native API-key verifier. |
| Host configuration | The original setup skill uses the host’s normal persistent MCP mechanism; it is not a project creative setting. |
| Workspace settings | Original generic integration file .arcreel/settings.json has mcp_url and api_key for the same instance. It is a credential-bearing local connection file, not production content. |
| Call timeout | Original setup instructions request at least 600 seconds where the host supports a timeout. It does not change provider clip duration. |
| Browser session | A web-login cookie is not the static MCP API-key credential. |
| OAuth | This upstream verifier accepts static arc- keys and does not publish an OAuth authorization flow. |

This reference does not store a key, certify the validity of an existing connection or invoke list_projects as a test. Sources: [server/remote_mcp.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/remote_mcp.py); [skills/setup-arcreel-skills/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/setup-arcreel-skills/SKILL.md).

## Common inputs and results

| Contract item | Meaning |
| --- | --- |
| project | Required root property on remote scoped calls; identifies the target independently of client cwd. |
| Stable IDs | Episode/unit/clip/timeline identities are not current playback positions. Obtain them from native reads. |
| revision/base_revision | Canonical revision or impact token for native concurrency/confirmation checks. |
| Result encoding | Remote results expose machine-readable structuredContent alongside content text/image blocks. Embedded results carry JSON text and image content blocks plus isError; the embedded adapter does not set structuredContent. |
| domain key | Default declared result wrapper, listed below. Custom projections can return a batch handle or terminal form instead. |
| isError / structured problems | Wire-level MCP error flag plus native stable problem codes/per-item admission. Internal is_error determines encoding but is not the wire property name. |
| generation_batch | Retain batch_id and poll get_generation_batch at poll_after_seconds until done. Then read terminal per-target results. |
| long task | Declaration-level asynchronous/waiter behavior, not a statement that an operation is paid. Local rendering also uses batches. |
| migration policy | Blocked rejects after failed project migration; Exempt admits the declared repair/read path; ReadCheck reports migration state through its handler. These are not user authorization scopes. |

A batch can be partially successful. Empty/idle state and a successful render do not imply editorial acceptance. Cancellation does not reverse provider work already submitted. Stale/current describe artifact input currency; paid replacement is a separate decision.

## Tool catalog

The following effect labels explain handlers; they are not MCP permission annotations. Read/inspection can still involve access metadata, local derived caches or provider status queries where documented.

| Tool | What it does | Effect | Long task | Default result key |
| --- | --- | --- | --- | --- |
| `list_projects` | List available projects. | Read/resolve; no provider generation requested | No | `projects` |
| `create_project` | Create and initialize one project. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `project` |
| `upload_source` | Register text source and its role/kind. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `source` |
| `edit_source_text` | Edit registered source with native revision/impact handling. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `source_change` |
| `get_workflow_plan` | Read authoritative content state, admission and next action. | Read/resolve; no provider generation requested | No | `workflow_plan` |
| `get_video_capabilities` | Resolve effective video limits for this project. | Read/resolve; no provider generation requested | No | `video_capabilities` |
| `get_prompt_preview` | Render current native prompt preview for one script item. | Read/resolve; no provider generation requested | No | `prompt_preview` |
| `get_generation_batch` | Read durable batch progress and terminal results. | Read/resolve; no provider generation requested | No | `generation_batch` |
| `cancel_generation_batch` | Request cancellation through the existing batch mechanism. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `generation_batch_cancellation` |
| `get_project_content` | Read project metadata and definitions. | Read/resolve; no provider generation requested | No | `project_content` |
| `list_source_files` | List registered source material. | Read/resolve; no provider generation requested | No | `source_files` |
| `get_source_text` | Read one source text. | Read/resolve; no provider generation requested | No | `source_text` |
| `get_episode_script` | Read formal script and canonical revision. | Read/resolve; no provider generation requested | No | `episode_script` |
| `get_script_plan_content` | Read a native script plan. | Read/resolve; no provider generation requested | No | `script_plan_content` |
| `list_project_files` | List admitted project files. | Read/resolve; no provider generation requested | No | `project_files` |
| `read_project_file` | Read an admitted project file. | Read/resolve; no provider generation requested | No | `project_file` |
| `list_pending_assets` | List definitions missing sheets. | Read/resolve; no provider generation requested | No | `list_pending_assets` |
| `generate_assets` | Generate asset sheets for missing or explicit targets. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `generation_result` |
| `generate_storyboards` | Generate storyboard images from formal script and references. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `generation_result` |
| `edit_images` | Apply local instruction-based image corrections. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `generation_result` |
| `generate_narration_audio` | Synthesize eligible separate narrator speech. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `generation_result` |
| `generate_videos` | Admit/quote or generate frame/reference-route video targets. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `generation_result` |
| `generate_grid` | Plan or generate storyboard composites. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `generation_result` |
| `split_grids` | Split approved grid cells into storyboard images. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `split_grids` |
| `inspect_images` | Inspect current/specified image versions. | Visual inspection/local derived material; no new provider generation | No | `inspect_images` |
| `get_provider_asset_links` | Read or refresh provider ingestion/link state. | Provider-library access and/or persisted link/selection changes | No | `provider_asset_links` |
| `list_provider_library_assets` | Browse the configured provider asset library. | Provider-library access and/or persisted link/selection changes | No | `provider_library_assets` |
| `upload_to_provider_asset_library` | Upload an explicitly requested asset to provider library. | Provider-library access and/or persisted link/selection changes | No | `provider_asset_link` |
| `select_provider_library_asset` | Apply a provider-library image as a selected native asset. | Provider-library access and/or persisted link/selection changes | No | `provider_asset_selection` |
| `release_provider_asset_link` | Unlink a local asset from a provider library record. | Provider-library access and/or persisted link/selection changes | No | `provider_asset_link` |
| `select_video_version` | Select an existing native video version. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `select_video_version` |
| `inspect_video_units` | Build/read visual contact-sheet inspection of video units. | Visual inspection/local derived material; no new provider generation | No | `inspect_video_units` |
| `create_timeline` | Create timeline from script or copy an existing revision. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `edit_timeline` |
| `list_timelines` | List episode/project editing timelines. | Read/resolve; no provider generation requested | No | `edit_timelines` |
| `read_timeline` | Read timeline and editing state. | Read/resolve; no provider generation requested | No | `edit_timeline` |
| `edit_timeline` | Apply ordered native editorial operations atomically. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `timeline_edit` |
| `rename_timeline` | Change a timeline display name. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `edit_timeline_summary` |
| `list_revisions` | List immutable timeline revisions. | Read/resolve; no provider generation requested | No | `edit_timeline_revisions` |
| `restore_revision` | Restore an older editorial revision through native lifecycle. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `timeline_edit` |
| `list_bgm` | List native BGM library material. | Read/resolve; no provider generation requested | No | `bgm` |
| `render_final_cut` | Render one timeline/revision and output variant locally. | Local render/export and artifact writes; not paid provider generation by itself | Yes | `final_cut` |
| `export_jianying_draft` | Export one editable Jianying draft locally. | Local render/export and artifact writes; not paid provider generation by itself | Yes | `jianying_draft` |
| `generate_episode_script` | Author missing visual layers or a native ad script. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `text_generation` |
| `generate_script_plan` | Generate appropriate per-episode script-plan structure. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `text_generation` |
| `confirm_script_review` | Confirm plan, register decided assets and materialize formal content. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `text_generation` |
| `open_draft` | Read or create a formal-content editing draft. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `draft` |
| `patch_draft` | Replace native draft body by canonical revision. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `draft` |
| `promote_draft` | Validate/promote draft to formal content. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `draft` |
| `discard_draft` | Discard a native editing draft. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `draft` |
| `patch_project` | Apply one allowlisted asset/settings/overview branch. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `project_patch` |
| `patch_episode_meta` | Update permitted episode/script title metadata. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `episode_meta_patch` |
| `rename_asset` | Rename an asset while rewriting native references. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `asset_rename` |
| `merge_asset` | Preview or merge two asset registrations. | Impact preview or persisted merge; dry_run distinguishes them | No | `asset_merge` |
| `retry_project_migration` | Retry the native project-upgrade/backfill mechanism. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `migration_retry` |
| `patch_episode_script` | Apply revision-checked script operations. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `script_patch` |
| `plan_episodes` | Plan remaining whole-source episodes with native text workflow. | Generation/text inference; native preview/dry_run/reuse exceptions only where declared | Yes | `episode_plan` |
| `reset_episode_planning` | Reset selected planning scope under impact confirmation. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `episode_reset` |
| `complete_script_plan_rebuild` | Acknowledge the rebuilt stale plan revision. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `script_plan_rebuild` |
| `delete_project_file` | Move an admitted project file into native trash. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `delete_project_file` |
| `list_trash_records` | List native trash records. | Read/resolve; no provider generation requested | No | `trash_records` |
| `restore_trash_record` | Restore a native trash record. | Native project/editorial/lifecycle mutation; no new model call implied by the name | No | `restore_trash_record` |

## Inputs for each native tool

The tables preserve the original request fields/types/defaults. Add project as described above for remote scoped calls. Conditional rules still apply even when a schema marks a selector optional. Nested types are described in the production companion.

### `list_projects`

List available projects.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Read/resolve; no provider generation requested. Migration policy: `NoneType`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `create_project`

Create and initialize one project.

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

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `NoneType`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `upload_source`

Register text source and its role/kind.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `filename` | string | Required | Plain filename ending in .txt or .md, without directories or a leading dot. |
| `content` | string | Required | Text content of the source file. |
| `on_conflict` | "fail" / "replace" / "rename" | Default "fail" | Existing source/ filename handling: fail rejects, replace overwrites, rename allocates another filename. Not applicable when role=episode. |
| `role` | "whole_source" / "episode" | Default "whole_source" | whole_source appends a registered whole-source file for episode planning; episode appends a self-sourced episode in playback order, assigns a new episode ID and proceeds directly to per-episode script planning. |
| `source_kind` | "novel" / "screenplay" or null | Optional; omit | Drama-only source kind; ignored for other content modes. novel (default) is AI-adapted; screenplay preserves the author's episode divisions, dialogue and voiceover. Replacing a registered same-name whole source preserves its existing kind. |
| `revision` | string | Optional; omit | When replacing a registered whole-source file affects split episodes, return the previous affected-episode-list revision unchanged after user confirmation; only then is replacement written. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `edit_source_text`

Edit registered source with native revision/impact handling.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `filename` | string | Optional; omit | Registered whole-source filename under source/, for example novel.txt; choose exactly one of filename and episode_id. |
| `episode_id` | integer | Optional; omit | Episode ID whose own source is edited; only self-sourced or no-source episodes qualify. Edit a split episode through its whole-source file. Choose exactly one of episode_id and filename. |
| `replacements` | array&lt;SourceReplacement&gt; | Optional; omit | Ordered exact replacements applied sequentially to the current source; choose exactly one of replacements and text. Bounds: min length 1. |
| `text` | string | Optional; omit | Complete replacement source text; choose exactly one of text and replacements. |
| `revision` | string | Optional; omit | When editing a whole-source file affects split episodes, return the previous affected-episode-list revision unchanged after user confirmation; only then is the edit written. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `get_workflow_plan`

Read authoritative content state, admission and next action.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer or null | Optional; omit | Episode ID to plan; omission selects the current episode in playback order. |
| `confirmed_request_durations` | map&lt;string, integer&gt; | Optional; omit | User-accepted request-duration tiers as unit-ID to seconds mapping; applies only to this workflow plan's video-admission check. |

Effects: Read/resolve; no provider generation requested. Migration policy: `ReadCheck`. Source: [lib/workflow/workflow_plan.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/workflow/workflow_plan.py).

### `get_video_capabilities`

Resolve effective video limits for this project.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `get_prompt_preview`

Render current native prompt preview for one script item.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. Bounds: min length 1. |
| `item_id` | string | Required | Entry ID: segment_id, scene_id, shot_id or unit_id, for example E1S01. Bounds: min length 1. |

Effects: Read/resolve; no provider generation requested. Migration policy: `ReadCheck`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `get_generation_batch`

Read durable batch progress and terminal results.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `batch_id` | string | Required | Durable generation-batch ID from generation_batch.batch_id returned by a generation tool. Bounds: min length 1. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `cancel_generation_batch`

Request cancellation through the existing batch mechanism.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `batch_id` | string | Required | Durable generation-batch ID from generation_batch.batch_id returned by a generation tool. Bounds: min length 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `get_project_content`

Read project metadata and definitions.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `list_source_files`

List registered source material.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `get_source_text`

Read one source text.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `path` | string | Required | Project-relative source path under source/, taken from list_source_files, for example source/episode_1.txt. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `get_episode_script`

Read formal script and canonical revision.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |

Effects: Read/resolve; no provider generation requested. Migration policy: `ReadCheck`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `get_script_plan_content`

Read a native script plan.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `list_project_files`

List admitted project files.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `read_project_file`

Read an admitted project file.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `path` | string | Required | Project-relative business-file path from list_project_files, for example project.json or scripts/episode_1.json. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `list_pending_assets`

List definitions missing sheets.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `type` | "character" / "scene" / "prop" / "product" | Optional; omit | Asset type to filter; omission aggregates pending assets of all types. |
| `episode_id` | integer | Optional; omit | Only assets referenced by this episode's formal script, including products and derivatives and their base characters; matches the Web episode-level scope. Cannot combine with type or names. |

Effects: Read/resolve; no provider generation requested. Migration policy: `ReadCheck`. Source: [server/media_tools/assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/assets.py).

### `generate_assets`

Generate asset sheets for missing or explicit targets.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `type` | "character" / "scene" / "prop" / "product" | Optional; omit | Asset type; omission covers all types in character, scene, prop, product order. |
| `names` | array&lt;string&gt; | Optional; omit | Explicit names to generate, using base/derivative for character derivatives. Requires type; mutually exclusive with all and episode_id. Omission selects only missing sheets. Bounds: min items 1. |
| `all` | boolean | Default false | Explicitly scan all missing sheets in the selected types; mutually exclusive with names. Omitting names already means missing sheets only. |
| `episode_id` | integer | Optional; omit | Only assets referenced by this episode's formal script, including products and derivatives and their base characters; matches the Web episode-level scope. Cannot combine with type or names. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/media_tools/assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/assets.py).

### `generate_storyboards`

Generate storyboard images from formal script and references.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `segment_ids` | array&lt;string&gt; | Optional; omit | Storyboard IDs to generate or regenerate; omission selects only entries missing storyboard images. Bounds: min items 1. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/media_tools/storyboards.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/storyboards.py).

### `edit_images`

Apply local instruction-based image corrections.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "storyboard" / "character_derivative" | Required | Image type to edit; one type per call. |
| `edits` | array&lt;ImageEdit&gt; | Required | Batch of target ID and natural-language instruction pairs; duplicate IDs retain only their first edit. Bounds: min items 1. |
| `script_file` | string | Optional; omit | Script filename without directories, for example episode_1.json; required when resource_type=storyboard. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/media_tools/image_edits.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/image_edits.py).

### `generate_narration_audio`

Synthesize eligible separate narrator speech.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `segment_ids` | array&lt;string&gt; | Optional; omit | Unit IDs in the current script skeleton; omission selects only narrator-owned units missing narrator audio. Explicit IDs deliberately resynthesize eligible selected units even when audio already exists. Bounds: min items 1. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/media_tools/narration_audio.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/narration_audio.py).

### `generate_videos`

Admit/quote or generate frame/reference-route video targets.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `target` | EpisodeTarget or AllTarget or SceneTarget or SelectedTarget | Required | Video target selector with scope episode, all, scene or selected; identifies video units within the supplied script. |
| `force` | boolean | Default false | Force regeneration of existing usable videos; default reuses current/stale selected videos. Permitted only for scene or selected scope. |
| `confirmed_request_duration_seconds` | integer | Optional; omit | User-accepted provider request-duration tier after reference-video cross-tier confirmation. Does not freeze text, references or provider; a changed projected tier requires confirmation again. Bounds: min 1. |
| `confirmed_request_durations` | map&lt;string, integer&gt; | Optional; omit | Per-unit accepted request tiers, for example {"E1U1": 8}; resend the original full target set as one batch. This mapping overrides the scalar tier for named units and leaves unnamed units unaffected. Return the preview mapping unchanged after acceptance. |
| `preview` | boolean | Default false | Run the same admission as submission but enqueue nothing; return video_quote with per-unit disposition, planned/requested duration, tier changes, estimated costs and gaps. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/media_tools/videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/videos.py).

### `generate_grid`

Plan or generate storyboard composites.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `scene_ids` | array&lt;string&gt; | Optional; omit | Regenerate grids containing these storyboard IDs; omission generates only groups still missing storyboard images. Bounds: min items 1. |
| `list_only` | boolean | Default false | Preview grid tiers, existing grid IDs/status and proposed actions; no queue, cost or pollable batch. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/media_tools/grid.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/grid.py).

### `split_grids`

Split approved grid cells into storyboard images.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `grid_ids` | array&lt;string&gt; | Required | Grid IDs to split into storyboard frames, for example grid_a1b2c3d4e5f6. Splitting overwrites every covered storyboard image while preserving version history. Bounds: min items 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/grid.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/grid.py).

### `inspect_images`

Inspect current/specified image versions.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "storyboard" / "character_derivative" | Required | Image type to inspect; one type per call. |
| `ids` | array&lt;string&gt; | Required | Image IDs: asset names, storyboard entry IDs, or base/derivative for character derivatives. Bounds: min items 1. |
| `version` | integer or null | Optional; omit | Use this version number for every listed item; omission inspects each item's current version. |

Effects: Visual inspection/local derived material; no new provider generation. Migration policy: `Blocked`. Source: [server/media_tools/image_review.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/image_review.py).

### `get_provider_asset_links`

Read or refresh provider ingestion/link state.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "character_derivative" | Required | Image type whose provider-library associations are queried. |
| `resource_id` | string | Required | Image resource ID: asset name, or base/derivative for a character derivative. Bounds: min length 1, max length 512. |
| `recheck` | boolean | Default false | Ask the backend to recheck pending ingestion immediately; needed only when polling=false and the status remains unresolved. |

Effects: Provider-library access and/or persisted link/selection changes. Migration policy: `Exempt`. Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py).

### `list_provider_library_assets`

Browse the configured provider asset library.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `account_id` | integer | Required | Provider-library account ID from get_provider_asset_links accounts[].id. Bounds: min 1. |
| `page` | integer | Default 1 | Page number, starting at 1. Bounds: min 1, max 200. |
| `page_size` | integer | Default 20 | Number of provider-library items per page. Bounds: min 1, max 100. |

Effects: Provider-library access and/or persisted link/selection changes. Migration policy: `Exempt`. Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py).

### `upload_to_provider_asset_library`

Upload an explicitly requested asset to provider library.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "character_derivative" | Required | Image type to upload. |
| `resource_id` | string | Required | Image resource ID: asset name, or base/derivative for a character derivative. Bounds: min length 1, max length 512. |
| `account_id` | integer | Required | Provider-library account ID from get_provider_asset_links accounts[].id. Bounds: min 1. |
| `user_requested` | true | Required | Pass true only when the user explicitly requested uploading this image to the provider library. Rejected generation, an agent's belief that upload would help, and questions about the library are not authorization. |

Effects: Provider-library access and/or persisted link/selection changes. Migration policy: `Blocked`. Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py).

### `select_provider_library_asset`

Apply a provider-library image as a selected native asset.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `resource_type` | "character" / "scene" / "prop" / "product" / "character_derivative" | Required | Destination native image type. |
| `resource_id` | string | Required | Image resource ID: asset name, or base/derivative for a character derivative. Bounds: min length 1, max length 512. |
| `account_id` | integer | Required | Provider-library account ID from get_provider_asset_links accounts[].id. Bounds: min 1. |
| `asset_id` | string | Required | Provider asset ID from list_provider_library_assets items[].id. Bounds: min length 1, max length 256. |

Effects: Provider-library access and/or persisted link/selection changes. Migration policy: `Blocked`. Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py).

### `release_provider_asset_link`

Unlink a local asset from a provider library record.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `link_id` | integer | Required | Association ID from get_provider_asset_links links[].id. Bounds: min 1. |

Effects: Provider-library access and/or persisted link/selection changes. Migration policy: `Exempt`. Source: [server/media_tools/provider_assets.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/provider_assets.py).

### `select_video_version`

Select an existing native video version.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `unit_id` | string | Required | Video-unit ID: storyboard entry ID for storyboard video, or unit_id for reference video. Bounds: min length 1. |
| `version` | integer | Required | Existing video version number to make current, starting at 1; applies to this one unit. Bounds: min 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/video_versions.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/video_versions.py).

### `inspect_video_units`

Build/read visual contact-sheet inspection of video units.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `unit_ids` | array&lt;string&gt; | Required | Video-unit IDs to inspect: storyboard entry IDs for storyboard video, or unit_id for reference video. Bounds: min items 1. |
| `version` | integer or null | Optional; omit | Use this video version for every listed unit; omission inspects each unit's current version. |
| `frames` | integer | Default 8 | Per-unit contact-sheet frame budget, default 8; when shot count exceeds the budget, prioritize at least one frame per shot and increase actual frames up to 24. This does not assess audio. Bounds: min 1, max 24. |

Effects: Visual inspection/local derived material; no new provider generation. Migration policy: `Blocked`. Source: [server/media_tools/video_review.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/video_review.py).

### `create_timeline`

Create timeline from script or copy an existing revision.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `from` | "script" / "timeline" | Required | script creates full-length hard-cut clips in current script order and requires episode; timeline copies an existing timeline in the same episode and requires timeline, with optional revision. |
| `name` | string | Required | Creator-recognizable display name, unique within the episode, for example Full version or Faster cut. Bounds: min length 1, max length 40. This names the timeline. |
| `episode` | integer or null | Optional; omit | Episode ID, not playback position; required when from=script. |
| `timeline` | string or null | Optional; omit | Timeline ID to copy from list_timelines/create_timeline; required when from=timeline. |
| `revision` | integer or null | Optional; omit | Revision to copy from list_revisions; omission copies the latest. Only permitted when from=timeline. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py).

### `list_timelines`

List episode/project editing timelines.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode` | integer or null | Optional; omit | Filter to this episode ID; omission lists timelines for all episodes. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Blocked`. Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py).

### `read_timeline`

Read timeline and editing state.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Blocked`. Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py).

### `edit_timeline`

Apply ordered native editorial operations atomically.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `base_revision` | integer | Required | Timeline revision this atomic operation batch is based on, taken from read_timeline revision. Bounds: min 1. |
| `summary` | string | Required | One-sentence change summary for the creator. Bounds: min length 1, max length 200. |
| `operations` | array&lt;TimelineOperation&gt; | Required | Ordered native timeline operations, committed atomically as one batch; use the TimelineOperation discriminated union, not script-patch operations. Bounds: min items 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py).

### `rename_timeline`

Change a timeline display name.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `name` | string | Required | New display name, unique within the episode. Bounds: min length 1, max length 40. This names the timeline. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py).

### `list_revisions`

List immutable timeline revisions.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Blocked`. Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py).

### `restore_revision`

Restore an older editorial revision through native lifecycle.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `revision` | integer | Required | Historical timeline revision number to restore, from list_revisions; restoration appends a new revision. Bounds: min 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/edit_timelines.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/edit_timelines.py).

### `list_bgm`

List native BGM library material.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Blocked`. Source: [server/media_tools/bgm.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/bgm.py).

### `render_final_cut`

Render one timeline/revision and output variant locally.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `revision` | integer | Optional; omit | Timeline revision to render; omission takes the latest revision at submission time. |
| `narration` | DraftNarration | Optional; omit | without_narration excludes narrator audio; with_narration includes it and is available only for TTS projects. Omission selects with_narration for TTS projects, otherwise without_narration. |
| `burn_subtitles` | boolean | Default true | Burn subtitles into the rendered image; false produces video without burned subtitles. |

Effects: Local render/export and artifact writes; not paid provider generation by itself. Migration policy: `Blocked`. Source: [server/media_tools/final_cuts.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/final_cuts.py).

### `export_jianying_draft`

Export one editable Jianying draft locally.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `timeline` | string | Required | Timeline ID from list_timelines or create_timeline, for example tl-3f9a0c21. Bounds: min length 1. |
| `revision` | integer | Optional; omit | Timeline revision to export; omission takes the latest revision at submission time. |
| `narration` | DraftNarration | Optional; omit | without_narration omits the narrator track; with_narration includes it and is available only for TTS projects. Omission selects with_narration for TTS projects, otherwise without_narration. |

Effects: Local render/export and artifact writes; not paid provider generation by itself. Migration policy: `Blocked`. Source: [server/media_tools/jianying_drafts.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/jianying_drafts.py).

### `generate_episode_script`

Author missing visual layers or a native ad script.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `instructions` | string | Optional; omit | Original additional instructions for this generation, injected verbatim at the end of the prompt; express strictness in the text. Omitted or blank means absent; maximum 4000 characters. Bounds: max length 4000. |
| `entry_ids` | array&lt;string&gt; | Optional; omit | Authoring scope of storyboard/unit IDs; omission covers all pending entries. Naming entries limits scope but does not authorize overwriting existing content. |
| `rewrite` | boolean | Default false | Explicitly rewrite all visual layers in scope; default fills gaps only, preserving each existing image/video prompt and filling only the missing side. |
| `regenerate` | boolean | Default false | Ad only: regenerate the entire formal script directly, replacing existing content. Cannot combine with entry_ids or rewrite. Existing formal content first returns a script_overwrite loss list. |
| `overwrite_revision` | string | Optional; omit | Token returned only after the user accepts the loss list: prompt_overwrite.revision for visual rewriting or script_overwrite.revision for a full redo. Prefixed sha256-v1: and bare hex forms are equivalent; not needed without overwrite. |
| `dry_run` | boolean | Default false | Return the constructed prompt only, without model inference. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `generate_script_plan`

Generate appropriate per-episode script-plan structure.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `source` | string | Optional; omit | Optional project-relative source path; omission reads source/episode_N.txt for this episode. |
| `instructions` | string | Optional; omit | Original additional instructions for this generation, injected verbatim at the end of the prompt; express strictness in the text. Omitted or blank means absent; maximum 4000 characters. Bounds: max length 4000. |
| `dry_run` | boolean | Default false | Return the constructed prompt only, without model inference. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `confirm_script_review`

Confirm plan, register decided assets and materialize formal content.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `overwrite_revision` | string | Optional; omit | script_overwrite.revision token returned after the user accepts the loss list. Prefixed sha256-v1: and bare hex forms are equivalent; unnecessary when no formal script exists. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `open_draft`

Read or create a formal-content editing draft.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `source` | string | Optional; omit | Optional novel-source path used to rejudge provenance only when first creating a draft from a formal script_plan; defaults to source/episode_N.txt. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py).

### `patch_draft`

Replace native draft body by canonical revision.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `content` | object | Required | Complete replacement draft body; intermediate content may fail business validation. |
| `base_revision` | string | Required | Draft revision returned by open_draft or the last patch_draft; sha256-v1: prefix and bare hexadecimal forms are equivalent. |
| `accept_formal_revision` | string or null | Optional; omit | After reconciling concurrent formal changes, explicitly accept formal_revision returned by open_draft. Prefixed/bare hex are equivalent. Explicit null accepts that the formal document is absent; omission means no acceptance. |
| `source` | string or null | Optional; omit | Optional source scope for rejudging a script_plan draft; explicit null clears the scope, omission preserves it. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py).

### `promote_draft`

Validate/promote draft to formal content.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `base_revision` | string | Required | Draft revision returned by open_draft or the last patch_draft; sha256-v1: prefix and bare hexadecimal forms are equivalent. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py).

### `discard_draft`

Discard a native editing draft.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `doc_type` | "drama_script_plan" / "narration_script_plan" / "reference_script_plan" / "reference_prompt_authoring" | Required | Document kind: drama_script_plan, narration_script_plan, reference_script_plan, or reference_prompt_authoring for reference-video formal-script prompt authoring. |
| `base_revision` | string | Required | Draft revision returned by open_draft or the last patch_draft; sha256-v1: prefix and bare hexadecimal forms are equivalent. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/draft_workflow.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/draft_workflow.py).

### `patch_project`

Apply one allowlisted asset/settings/overview branch.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `table` | "characters" / "scenes" / "props" / "products" / null | Optional; omit | Asset-upsert branch selector, supplied together with entries; characters, scenes, props or products. |
| `entries` | object or null | Optional; omit | Nonempty asset-name to editable-fields map; new names are added and existing names merge supplied fields. Character derivatives merge by derivative name: supplied descriptions update/add, omitted variants survive. Describe changes relative to the base. |
| `settings` | object or null | Optional; omit | Exclusive settings branch; allowlisted keys: episode_target_units, episode_target_duration, source_language, brief, narration_voice, narration_speed, character_voice_binding. Null clears a field where its domain rules permit. |
| `overview` | object or null | Optional; omit | Exclusive overview branch; merge only supplied synopsis, genre, theme and world_setting fields, creating overview if absent. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `patch_episode_meta`

Update permitted episode/script title metadata.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories, for example episode_1.json. |
| `field` | "title" | Required | Script top-level metadata field; only title is allowed. |
| `value` | string | Required | New title; must be nonempty after trimming leading and trailing whitespace. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `rename_asset`

Rename an asset while rewriting native references.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `table` | "characters" / "scenes" / "props" / "products" | Required | Asset table to rename within: characters, scenes, props or products. |
| `old_name` | string | Required | Existing asset name. |
| `new_name` | string | Required | New asset name; reject the whole rename on an NFC-normalized collision within this table. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `merge_asset`

Preview or merge two asset registrations.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `table` | "characters" / "scenes" / "props" | Required | Asset table to merge within: characters, scenes or props; products are unsupported. |
| `source` | string | Required | Asset to merge away and remove from the table. |
| `target` | string | Required | Other asset in the same table to keep unchanged. |
| `as_derivative` | boolean | Default false | Characters only: merge source as a derivative of target using the source name and description; the derivative sheet remains pending generation. |
| `dry_run` | boolean | Default false | Return per-episode impact only, without changing anything. |

Effects: Impact preview or persisted merge; dry_run distinguishes them. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `retry_project_migration`

Retry the native project-upgrade/backfill mechanism.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `patch_episode_script`

Apply revision-checked script operations.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `script` | string | Required | Script filename without directories; one episode per file and one call per episode. Bounds: min length 1. |
| `base_revision` | string | Required | Current revision from get_episode_script; sha256-v1: prefix and bare hexadecimal forms are equivalent. Bounds: pattern ^(?:sha256-v1:)?[0-9a-f]{64}$. |
| `operations` | array&lt;PatchUpdateOperation or PatchInsertOperation or PatchMoveOperation or PatchRemoveOperation or PatchSplitOperation&gt; | Required | Ordered script operations update, insert, move, remove or split, committed atomically. Bounds: min items 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `plan_episodes`

Plan remaining whole-source episodes with native text workflow.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `instructions` | string | Optional; omit | Original additional episode-planning instructions, for example aligning splits to chapters; inserted verbatim into the planning prompt. Express strictness in the text and repeat them for each batch. Omitted or blank means absent; maximum 4000 characters. |

Effects: Generation/text inference; native preview/dry_run/reuse exceptions only where declared. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `reset_episode_planning`

Reset selected planning scope under impact confirmation.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Optional; omit | Split episode ID from which to reset: omission or the first split episode means a full reset; a later split episode preserves episodes earlier in playback order. Bounds: min 1. |
| `confirm_consumed` | boolean | Default false | Set true only after explaining affected consumed episodes and receiving user confirmation. Omit on the first call so the tool returns the impact list. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `complete_script_plan_rebuild`

Acknowledge the rebuilt stale plan revision.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode_id` | integer | Required | Persistent episode ID from episodes[].episode or the workflow plan, not playback position. Bounds: min 1. |
| `expected_stale_script_plan_revision` | string or null | Required | Rebuild baseline copied unchanged from next_action.args.expected_stale_script_plan_revision; explicit null is required when null. Prefixed/bare hex are equivalent. Reject if it differs from the project record. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `delete_project_file`

Move an admitted project file into native trash.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `path` | string | Required | Project-relative path using forward slashes, for example storyboards/scene_E1S02.png; only admitted unreferenced files/history may be trashed, not arbitrary project state. Bounds: min length 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/project_trash.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/project_trash.py).

### `list_trash_records`

List native trash records.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| No operation-specific fields | object | Empty object | This is a callable tool with no operation-specific arguments. Remote project-scoped calls still require the common `project` input; unscoped calls do not. |

Effects: Read/resolve; no provider generation requested. Migration policy: `Exempt`. Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

### `restore_trash_record`

Restore a native trash record.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `record_id` | string | Required | Trash-record ID from list_trash_records or delete_project_file. Bounds: min length 1. |

Effects: Native project/editorial/lifecycle mutation; no new model call implied by the name. Migration policy: `Blocked`. Source: [server/media_tools/project_trash.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/project_trash.py).

## Important native limitations

- patch_project only exposes its asset/overview and seven-key settings branches. The UI project-settings model exposes additional fields; these are not arbitrary patch_project arguments.
- edit_images submits image editing; this original request has no preview field. Video preview belongs to generate_videos, and grid planning preview is list_only.
- Generic MCP source upload accepts text content. Rich file upload, character voice auditions, original-reference upload, style analysis and end-frame actions also exist through native UI/REST paths; their names are not extra tools in this 61-tool catalog.
- A narrator TTS operation is distinct from character reference-audio generation and binding. Native capability/route rules govern actual provider submission.
- Target and duration confirmation maps preserve native admission; unpriced targets do not become free and confirmation tokens do not create a budget.
- Native tools share existing application services. They are not an alternate production database or a reason to write project/manifest state directly.

## Typical native flows

| Case | Native sequence |
| --- | --- |
| Inspect progress | list_projects/get_project_content → get_workflow_plan → appropriate read/batch query |
| New source production | create_project → upload_source → plan/author according to native mode → confirm applicable content → generate assets/media → timeline |
| Correct an image | inspect_images/read definitions → authorized edit_images or explicit regeneration → inspect selected version |
| Generate videos | get_video_capabilities/get_workflow_plan → generate_videos(preview=true) where confirmation needed → accept tiers → submit original full selection → poll batch |
| Edit/deliver | inspect_video_units/list_timelines/read_timeline → edit_timeline/select_video_version → requested render_final_cut or export_jianying_draft → poll batch |

Examples describe API routing, not instructions to execute production. The main ArcReel Agent and native skills retain creative and confirmation responsibilities.

## Handler constraints and side effects verified during review

These conditions live in handlers/skill contracts as well as input schemas. A field-presence checklist alone does not establish them.

| Operation / case | Verified native rule |
| --- | --- |
| create_project name/title | name identifies a project, not a character. MCP requires name; the REST route requires a nonblank title or explicit name and can derive the identifier from title. |
| generate_videos target | episode/all fill missing videos and reuse usable ones; scene contains exactly one ID; selected is an explicit list. force is admitted only for scene/selected. |
| generate_narration_audio segment_ids | Omit to fill eligible narrator units missing audio; explicit selected IDs can resynthesize existing eligible audio and cost again. |
| inspect_images | At most 20 images per call. Inspection copies are JPEG q85, longest edge at most 2000 pixels; they are review representations, not replacement asset originals. |
| inspect_video_units version/frames | These select a shared candidate version/sampling for the inspected group, not final rendering resolution or a spoken-audio review. |
| Timeline revision inputs | create/copy/restore/render/export use timeline revision numbers. They are not source-file impact tokens. edit_timeline.operations uses its timeline operation union, not script update/insert/move/remove/split operations. |
| select_video_version | Requires one explicit existing version; it mutates current selection. It is not the optional version filter of a read-only inspector. |
| select_provider_library_asset | Creator explicitly chooses the remote asset; the handler downloads its image, creates/selects a new native version and records an active link. It is not just linking a URL. |
| release_provider_asset_link | Requires agreement to unlink. Removes the relation, deleting neither local nor provider image; later submission falls back to ordinary-image input where applicable. |
| merge_asset | Preview impact and obtain native acceptance. Source descriptions/images/voice/originals/version data go to trash; script references are rewritten. Restoring trashed data does not automatically undo those reference rewrites. |
| delete_project_file | Only explicitly requested unreferenced files/noncurrent snapshots in admitted scope; it is not a tool for deleting arbitrary current materials, timelines or purging trash. |
| restore_trash_record | Adds/restores without overwriting current output. Conflicts are handled through history/renaming/new native identities, not silent replacement. |
| open_draft | Can create an editing copy when absent, so reading/opening it is not universally side-effect-free. |
| Local render/export | Writes local jobs/artifacts. No new paid provider media is generated by the render/export itself; a requested paid remedy is separate. |

Sources: [server/media_tools/image_review.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/image_review.py), [server/media_tools/videos.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/videos.py), [server/media_tools/narration_audio.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/media_tools/narration_audio.py), [server/agent_toolset/asset_library.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/asset_library.py), [server/agent_toolset/project_trash.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/project_trash.py), [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py), [server/agent_toolset/embedded.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/embedded.py), [server/agent_toolset/remote.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_toolset/remote.py).

## Native API-key and memory configuration inputs

| Interface | Inputs | Native behavior |
| --- | --- | --- |
| POST /api/v1/api-keys | name; expires_days integer >=0 or null | Name labels the credential. Omitted/null expiry uses 30 days; 0 means no expiry. Creation returns the full arc- key once. |
| API-key list/delete | Existing key identity for deletion | Native key management requires JWT-authenticated access; an API key cannot manage itself. Documentation does not create/revoke a key. |

Native memory-file routes are documented in the project companion; they do not enlarge this MCP catalog.

Source: [server/routers/api_keys.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/api_keys.py).

## Scope verification

All 61 declared tools are represented exactly once in the catalog and input section. Source was the original upstream archive, with schema inspection only; no runtime authentication, provider call, session execution, native reset or project mutation was used to create this document. This catalog is versioned to the pinned commit and should not be treated as a claim about a differently deployed server.
