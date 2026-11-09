# Project-wide configuration inputs

**Reviewed again on 2026-11-09:** request descriptions were checked by their owning operation, not reused by field name. Cross-field/handler constraints, native UI/configuration interfaces, profile support files and adapter-specific result encoding were checked against the same pinned upstream. No production operations were executed.

Scope: **original ArcReel upstream only**, pinned to [`7149433a21b3981da521e35b517a1fbe3356cc87`](https://github.com/ArcReel/ArcReel/tree/7149433a21b3981da521e35b517a1fbe3356cc87), main resolved on 2026-11-09; commit timestamp 2026-11-09T17:06:15Z. All contracts below come from that upstream snapshot, not from the local installation or its project data. Descriptions are English explanations of the original source; functional names/enums are preserved.

Companions: [production inputs](production-inputs-by-use-case.md), [skills](arcreel-skills-map.md), [MCP](arcreel-mcp-map.md).

Reference boundary: use this map with its three companion maps to understand the pinned original application. It does not inventory extensions or credentials in a customized installation, prescribe host-agent responsibilities, or authorize execution. A later integration plan must establish those responsibilities against its actual target version.

## Layer map

| Layer | Inputs / owner | What it controls |
| --- | --- | --- |
| Project creation | Native create_project and creation UI | Identity, content mode, fixed generation route, ratio, ad target/brief and narrator setup. |
| Mutable project preferences | Original project settings / UpdateProjectRequest | Style, model lanes, resolutions, pacing, narrator snapshot and voice binding. |
| Legacy MCP settings branch | patch_project.settings | Only the original seven-key allowlist below. It is not the complete project settings API. |
| Assets | Native asset upsert, uploads, library/version selection | Persistent character/room/object/product identity and approved references. |
| Application defaults | Global settings, provider/model catalog and credentials | Inherited choices and runtime availability. |
| Agent profile and memory | Original agent_runtime_profile and native project memory | Skills, subagents, workflow instructions and remembered project context. |
| Script/editorial state | Native authoring, presentations and timelines | Actual content, selected versions, timing, mix and delivery. |

## Project creation through MCP

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string | Required | Unique project identifier; subsequent native tools locate the project by this name. |
| `title` | string | Default "" | User-visible project title; the MCP default is an empty string. |
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

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py).

## Project creation through the UI / REST

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string or null | Optional; omit | Optional explicit project identifier; if omitted, derive an identifier from title. The route requires a nonblank title or name. |
| `title` | string or null | Optional; omit | User-visible project title; the route requires a nonblank title or explicit name. |
| `style` | string or null | Default "" | Custom visual-direction prose used by native generation. |
| `content_mode` | "narration" / "drama" / "ad" or null | Default "narration" | Content type: narration for narrated storytelling/commentary, drama for episodic drama, or ad for advertising/general short films. |
| `aspect_ratio` | string or null | Default "9:16" | Output aspect ratio, for example 9:16 or 16:9. |
| `default_duration` | integer or null | Optional; omit | Default planned shot duration in seconds; omitted means do not persist a value and use model capabilities. Unavailable for ad projects. |
| `episode_target_duration` | integer or null | Optional; omit | Non-ad soft episode-duration target; explicit null clears it. |
| `target_duration` | integer or null | Optional; omit | Target final-video duration in seconds; available only for ad projects. |
| `brief` | string or null | Optional; omit | Creative brief, including selling points or intended audience; available only for ad projects. |
| `generation_mode` | "storyboard" / "reference_video" | Required | Creation route: storyboard generates storyboard images before video; reference_video generates video directly from reference images. |
| `grid_storyboard` | boolean | Default false | Enable grid storyboards; unsupported for ad projects. |
| `speech_rate_units_per_second` | number or null | Optional; omit | Absolute planning estimate in language-dependent reading units/s, not native speech speed. |
| `style_template_id` | string or null | Optional; omit | Known built-in style-template selection. |
| `video_backend` | string or null | Optional; omit | Project fallback video provider/model. |
| `video_provider_i2v` | string or null | Optional; omit | Project image-to-video lane provider/model. |
| `video_provider_r2v` | string or null | Optional; omit | Project reference-to-video lane provider/model; does not change the fixed route. |
| `image_provider_t2i` | string or null | Optional; omit | Project text-to-image generation model. |
| `image_provider_i2i` | string or null | Optional; omit | Project image-to-image correction model. |
| `default_image_backend` | string or null | Optional; omit | Project fallback image provider/model. |
| `text_backend_simple` | string or null | Optional; omit | Project simple auxiliary-text model; empty restores global inheritance. |
| `text_backend_complex` | string or null | Optional; omit | Project complex auxiliary-text model; empty restores global inheritance. |
| `default_text_backend` | string or null | Optional; omit | Project fallback auxiliary-text model, separate from main Agent routing. |
| `model_settings` | map&lt;string, map&lt;string, string or null&gt;&gt; or null | Optional; omit | Complete provider/model-keyed settings map; resolution is consumed by current media paths and the supplied map replaces prior entries. |
| `narration_delivery` | "post_production" / "use_tts" | Default "post_production" | post_production delivers voiceover text/subtitles for the creator to dub later; use_tts generates narrator audio in ArcReel. The user can change this later in project settings. |
| `audio_backend` | string or null | Optional; omit | TTS provider/model, used only for use_tts; omitted values are filled from the global default at creation and become a project snapshot. |
| `narration_voice` | string or null | Optional; omit | Narrator voice ID, used only for use_tts; omitted values are filled from the global default at creation. |
| `narration_speed` | number or null | Optional; omit | Positive TTS rate multiplier, used only for use_tts; omission fills the global default, while explicit null omits rate from the provider request. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py).

Creation defaults come from the tables, not from a running project. content_mode and generation_mode are creation choices; the latter cannot be switched through ordinary project PATCH. Ad rejects default_duration and grid_storyboard; target_duration and brief are ad-only. The original MCP creation schema has no source_language field.

## All mutable project inputs

The original UpdateProjectRequest declares **28 fields**. Omitted fields preserve current values; explicit null is validated per field, not a universal reset.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `title` | string or null | Optional; omit | User-visible project title. |
| `style` | string or null | Optional; omit | Custom visual-direction prose used by native generation. |
| `aspect_ratio` | string or null | Optional; omit | Desired project image/video delivery ratio; actual provider route behavior still applies. |
| `default_duration` | integer or null | Optional; omit | Non-ad default planned unit seconds; ad mode rejects it. |
| `episode_target_duration` | integer or null | Optional; omit | Non-ad soft episode-duration target; explicit null clears it. |
| `target_duration` | integer or null | Optional; omit | Ad/short-film positive total target seconds; cannot be cleared in an ad PATCH. |
| `brief` | string or null | Optional; omit | Ad/short-film creative brief; other content modes reject this field. |
| `grid_storyboard` | boolean or null | Optional; omit | Storyboard grid assembly toggle; not a separate route and unavailable in ad mode. |
| `video_backend` | string or null | Optional; omit | Project fallback video provider/model. |
| `video_provider_i2v` | string or null | Optional; omit | Project image-to-video lane provider/model. |
| `video_provider_r2v` | string or null | Optional; omit | Project reference-to-video lane provider/model; does not change the fixed route. |
| `image_provider_t2i` | string or null | Optional; omit | Project text-to-image generation model. |
| `image_provider_i2i` | string or null | Optional; omit | Project image-to-image correction model. |
| `default_image_backend` | string or null | Optional; omit | Project fallback image provider/model. |
| `video_generate_audio` | boolean or null | Optional; omit | Native-video audio intent where the selected channel supports a switch. |
| `character_voice_binding` | string or null | Optional; omit | prompt uses soft voice_style guidance; reference_audio additionally needs an admitted reference-video route and character audio. |
| `narration_delivery` | "post_production" / "use_tts" or null | Optional; omit | post_production defers separate narration; use_tts enables narrator synthesis; neither substitutes native character voices. |
| `audio_backend` | string or null | Optional; omit | Project TTS model in provider/model form; use_tts requires a valid saved model/voice snapshot. |
| `narration_voice` | string or null | Optional; omit | Project separate-narrator voice ID. |
| `narration_speed` | number or null | Optional; omit | Positive finite narrator rate multiplier where supported; null means no rate parameter. |
| `speech_rate_units_per_second` | number or null | Optional; omit | Absolute planning estimate in language-dependent reading units/s, not native speech speed. |
| `text_backend_simple` | string or null | Optional; omit | Project simple auxiliary-text model; empty restores global inheritance. |
| `text_backend_complex` | string or null | Optional; omit | Project complex auxiliary-text model; empty restores global inheritance. |
| `default_text_backend` | string or null | Optional; omit | Project fallback auxiliary-text model, separate from main Agent routing. |
| `style_template_id` | string or null | Optional; omit | Known built-in style-template selection. |
| `clear_style_image` | boolean or null | Optional; omit | Explicit clear operation for the existing style-image choice. |
| `episodes` | array&lt;EpisodePatch&gt; or null | Optional; omit | EpisodePatch list: stable episode identity plus writable script_file binding; unspecified fields stay unchanged. |
| `model_settings` | map&lt;string, map&lt;string, string or null&gt;&gt; or null | Optional; omit | Complete provider/model-keyed settings map; resolution is consumed by current media paths and the supplied map replaces prior entries. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py).

## Exact MCP setting and overview allowlists

The native patch_project tool accepts exactly one branch: table+entries, settings, or overview.

| Branch | Accepted inputs | Meaning |
| --- | --- | --- |
| settings | `episode_target_units`, `episode_target_duration`, `source_language`, `brief`, `narration_voice`, `narration_speed`, `character_voice_binding` | Sparse updates to these top-level preferences only. episode_target_units is explicit source reading volume; episode_target_duration is soft seconds; brief is ad-only; narrator and binding fields retain their separate roles. |
| overview | `synopsis`, `genre`, `theme`, `world_setting` | Merge supplied story-context fields; do not overwrite unspecified user content. |
| table + entries | characters/scenes/props/products and named editable entry maps | Upsert definitions and supported character derivatives; media paths use native upload/selection actions. |

For source_language the original setter accepts `zh`, `en`, `vi`, `ru`. This is the original contract, not a statement about language support in a different installation. It is not a field in this upstream UpdateProjectRequest. Episode source role/kind and source-file order use native source/episode actions. Additional authoring instructions are saved through original per-episode instruction forms or passed temporarily according to the relevant form.

Source: [server/tool_runtime.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/tool_runtime.py); [lib/episode/episode_target_volume.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/episode/episode_target_volume.py).

## Asset configuration

| Input | What it does | How it takes effect |
| --- | --- | --- |
| Character description | Canonical appearance/costume traits | Drives future sheet generation; does not rewrite paid media. |
| Character voice_style | Timbre/accent/performance prose | Soft prompt guidance, distinct from a saved audio sample. |
| Character reference_image | Approved original identity image | Conditions sheet generation through native upload/selection. |
| Character character_sheet | Selected registered identity sheet | Used when a shot references the character. |
| Character reference_audio | Approved voice recording/audition | Sent only when voice binding, route and provider capability permit it. |
| Character aliases | Alternative identification names | Planning/name matching, not extra visual references. |
| Character derivatives.&lt;name&gt;.description / character_sheet | Required appearance variation relative to the same base | Native derivative creation/edit/upload; shares base identity/voice. |
| Scene description / scene_sheet / aliases | Persistent room/location identity | The sheet is attached only where a shot names the scene. |
| Prop description / prop_sheet / aliases | Persistent recurring-object identity | Bind actual required props; an unused registered asset is not sent. |
| Product description / brand / selling_points | Product identity and promotional context | Used by appropriate ad planning; not mandatory for unrelated creative shorts. |
| Product reference_images / product_sheet | Approved originals and optional sheet | Originals preserve the supplied product identity; native assembly rules choose actual references. |
| Voice stamps, fingerprints, provider links, selected-version IDs | Managed registration/notification facts | Not editable fidelity knobs to fabricate. |

Source: [lib/project/asset_types.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/project/asset_types.py); [lib/artifacts/generation_input.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/artifacts/generation_input.py).

## Inheritance, narration and route constraints

- Model selection is resolved per lane: relevant request/project choices precede corresponding global choices and automatic eligible-model selection. A blank saved value can still resolve a working model. Main Agent models and auxiliary text models are separate sources.
- model_settings uses full provider/model keys. The current consumer reads resolution; preserve the full map on updates because the API replaces the dictionary. Source image, generated video and final render dimensions are separate layers.
- Project TTS settings are a snapshot. New use_tts projects prefill missing model/voice/rate from application defaults; later global changes do not silently update that project.
- post_production leaves separate narration for later recording. Character audition uses explicit text/voice; it is not enabled by switching narrator delivery.
- character_voice_binding=reference_audio needs a capable reference-video route and approved per-character samples. A model selection does not switch a creation-fixed route.
- The reading-rate field is a planning estimate, not native speech speed. Source reading-volume targets and exact media duration are different.
- Uploading a style image runs analysis and replaces the prior custom style/template state. A reference stored in the asset catalog is distinct from actual per-shot binding.

Sources: [lib/config/resolver.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/config/resolver.py), [server/services/project/narration_settings.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/services/project/narration_settings.py), [server/routers/files.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/files.py), [lib/speech/character_voice.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/speech/character_voice.py).

## Global application inputs

The original SystemConfigPatchRequest declares **24 fields**. These belong to the application rather than one project. No credential values are documented.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `default_video_backend` | string or null | Optional; omit | Application fallback video model. |
| `default_video_backend_i2v` | string or null | Optional; omit | Application image-to-video lane model. |
| `default_video_backend_r2v` | string or null | Optional; omit | Application reference-to-video lane model. |
| `default_image_backend` | string or null | Optional; omit | Application fallback image model. |
| `default_image_backend_t2i` | string or null | Optional; omit | Application image-creation lane model. |
| `default_image_backend_i2i` | string or null | Optional; omit | Application image-edit lane model. |
| `default_text_backend` | string or null | Optional; omit | Application fallback auxiliary text model. |
| `default_audio_backend` | string or null | Optional; omit | Application speech-synthesis model/default prefill. |
| `narration_voice` | string or null | Optional; omit | Application-wide project separate-narrator voice ID. |
| `narration_speed` | number or null | Optional; omit | Application-wide positive finite narrator rate multiplier where supported; null means no rate parameter. |
| `market_github_proxy_prefix` | string or null | Optional; omit | Proxy prefix for market/GitHub retrieval. |
| `video_generate_audio` | boolean or null | Optional; omit | Application-wide native-video audio intent where the selected channel supports a switch. |
| `video_poll_timeout_seconds` | integer or null | Optional; omit | Asynchronous video polling timeout, not clip duration. |
| `anthropic_api_key` | string or null | Optional; omit | Legacy Agent API credential compatibility input; current native credential records are managed separately. |
| `anthropic_base_url` | string or null | Optional; omit | Legacy compatible Agent API endpoint, not ArcReel MCP URL. |
| `anthropic_model` | string or null | Optional; omit | Main embedded-Agent model override. |
| `anthropic_default_haiku_model` | string or null | Optional; omit | Agent Haiku-tier model override. |
| `anthropic_default_opus_model` | string or null | Optional; omit | Agent Opus-tier model override. |
| `anthropic_default_sonnet_model` | string or null | Optional; omit | Agent Sonnet-tier model override. |
| `claude_code_subagent_model` | string or null | Optional; omit | Agent subagent model override. |
| `agent_session_cleanup_delay_seconds` | integer or null | Optional; omit | Session runtime cleanup delay in seconds. |
| `agent_max_concurrent_sessions` | integer or null | Optional; omit | Maximum concurrent native Agent sessions. |
| `text_backend_simple` | string or null | Optional; omit | Application-wide project simple auxiliary-text model; empty restores global inheritance. |
| `text_backend_complex` | string or null | Optional; omit | Application-wide project complex auxiliary-text model; empty restores global inheritance. |

Source: [server/routers/system_config.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/system_config.py).

## Other native application configuration families

| Family | Inputs / purpose | Boundary |
| --- | --- | --- |
| Provider setup | Credentials, base URL, enabled/disabled models and applicable provider fields | Provider-specific schemas apply; credentials remain in the native store. |
| Model catalog / custom provider | Model/channel capabilities, defaults, pricing and endpoint templates | Arbitrary custom endpoint JSON is not a fixed universal field list. Capabilities still need actual provider support. |
| Reference-copy processing | reference_total_max_bytes, reference_single_max_bytes and native compression policy | Byte budgets are not a promise that reference pixels are transmitted unchanged. |
| Worker/rate limits | Provider throughput and waiting behavior | Operational controls, not guaranteed creative-quality improvements. |
| Provider asset library and storage | Provider account, storage and inference-credential binding | Explicit provider-library actions are distinct from local project originals. |
| Embedded Agent credentials and model routing | Native Agent credential records and global model/tier overrides | Separate from auxiliary text task defaults. |
| Native MCP access | ArcReel endpoint and API-key access | Transport authentication does not authorize production spend. See the MCP reference. |

## Native instructions and managed state

Original profile files live under agent_runtime_profile and are copied/synchronized into a project’s CLAUDE.md/.claude tree. Workflow skill variants depend on content_mode. The Agent profile status/reset UI manages customizations; reset is not a generic quality upgrade. Native project memory carries requirements and context but is not itself a renderer parameter. See [skills](arcreel-skills-map.md).

Do not hand-write project.schema_version, timestamps, episode allocation/ranges, generated_assets, selected-version facts, manifest digests, stale/current status, queue state or render registrations. Use native lifecycle operations. Existing media does not change merely because a default/description changes.

## Additional original configuration forms found during review

The first map summarized these as configuration families. Their actual input models are now enumerated below. Secrets are field names only; no credential values are read or published.

### `projects.EpisodePatch`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `episode` | integer | Required | Stable episode identity, not playback position. |
| `script_file` | string or null | Optional; omit | Formal script filename identifying this episode. |

Source: [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py#L330).

### `agent_config.CreateCredentialRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `preset_id` | string | Required | Built-in Agent-provider preset identity or the native custom-preset sentinel. |
| `display_name` | string or null | Optional; omit | User-facing provider/credential/model/entry label. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |
| `from_custom_provider_id` | integer or null | Optional; omit | Existing custom-provider credential source; creation uses this instead of an inline API key. |
| `model` | string or null | Optional; omit | Provider request model identity for the Agent or endpoint trial. |
| `haiku_model` | string or null | Optional; omit | Agent Haiku-tier model override. |
| `sonnet_model` | string or null | Optional; omit | Agent Sonnet-tier model override. |
| `opus_model` | string or null | Optional; omit | Agent Opus-tier model override. |
| `subagent_model` | string or null | Optional; omit | Agent subagent model override. |
| `multiplier` | number | Default 1.0 | Nonnegative local price/accounting multiplier; zero recorded price does not establish a free provider request. Bounds: min 0. |
| `tier_bindings` | map&lt;string, string or null&gt; or null | Optional; omit | Agent tier to existing text-model catalog-entry binding; update merges supplied tiers and null removes a binding. |
| `activate` | boolean or null | Optional; omit | Whether to make the new Agent credential active; omission follows native automatic activation when none is active. |

Source: [server/routers/agent_config.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/agent_config.py#L124).

### `agent_config.UpdateCredentialRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `display_name` | string or null | Optional; omit | User-facing provider/credential/model/entry label. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |
| `model` | string or null | Optional; omit | Provider request model identity for the Agent or endpoint trial. |
| `haiku_model` | string or null | Optional; omit | Agent Haiku-tier model override. |
| `sonnet_model` | string or null | Optional; omit | Agent Sonnet-tier model override. |
| `opus_model` | string or null | Optional; omit | Agent Opus-tier model override. |
| `subagent_model` | string or null | Optional; omit | Agent subagent model override. |
| `multiplier` | number or null | Optional; omit | Nonnegative local price/accounting multiplier; zero recorded price does not establish a free provider request. |
| `tier_bindings` | map&lt;string, string or null&gt; or null | Optional; omit | Agent tier to existing text-model catalog-entry binding; update merges supplied tiers and null removes a binding. |

Source: [server/routers/agent_config.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/agent_config.py#L143).

### `agent_config.TierBindingRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `entry_binding` | string | Required | Existing same-media catalog entry linked to this provider model/tier. |

Source: [server/routers/agent_config.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/agent_config.py#L157).

### `agent_config.TestConnectionRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `preset_id` | string or null | Optional; omit | Built-in Agent-provider preset identity or the native custom-preset sentinel. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string | Required | Provider/Agent secret key for this connection; never a project prompt parameter. |
| `model` | string or null | Optional; omit | Provider request model identity for the Agent or endpoint trial. |

Source: [server/routers/agent_config.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/agent_config.py#L428).

### `providers.ProviderMultiplierUpdate`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `multiplier` | number or null | Required | Nonnegative local price/accounting multiplier; zero recorded price does not establish a free provider request. |

Source: [server/routers/providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/providers.py#L225).

### `providers.CreateCredentialRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string | Required | User-visible credential label; not a project or character identity. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `access_key` | string or null | Optional; omit | Provider access-key component required by the selected provider credential format. |
| `secret_key` | string or null | Optional; omit | Provider secret-key component; store through the credential API and never publish its value. |

Source: [server/routers/providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/providers.py#L231).

### `providers.UpdateCredentialRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string or null | Optional; omit | User-visible credential label; not a project or character identity. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `access_key` | string or null | Optional; omit | Provider access-key component required by the selected provider credential format. |
| `secret_key` | string or null | Optional; omit | Provider secret-key component; store through the credential API and never publish its value. |

Source: [server/routers/providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/providers.py#L239).

### `provider_models.ProviderModelEnabledUpdate`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model_id` | string | Required | Provider-facing model identity for the model row. |
| `enabled` | boolean | Required | Whether the model is eligible for selection. |

Source: [server/routers/provider_models.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/provider_models.py#L158).

### `provider_models.AddProviderModelRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model_id` | string | Required | Provider-facing model identity for the model row. Bounds: min length 1, max length 128. |
| `media_type` | "text" / "image" / "video" / "audio" or null | Optional; omit | Declared image/video/text/audio domain, subject to this contract’s enum. |
| `entry_binding` | string or null | Optional; omit | Existing same-media catalog entry linked to this provider model/tier. |
| `endpoint` | string or null | Optional; omit | Selected supported endpoint/channel identity; this is distinct from base_url and custom path overrides. |

Source: [server/routers/provider_models.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/provider_models.py#L165).

### `provider_models.EntryUpdate`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `maker` | string | Required | Catalog model-maker identifier. |
| `name` | string | Required | Catalog model name under the maker/media-type namespace. |
| `media_type` | "text" / "image" / "video" / "audio" | Required | Declared image/video/text/audio domain, subject to this contract’s enum. |
| `display_name` | string or null | Optional; omit | User-facing provider/credential/model/entry label. |
| `facts` | object or null | Optional; omit | Media-specific model facts/capabilities validated by the catalog schema. |
| `price` | object or null | Optional; omit | Structured catalog pricing dimensions/rates; not provider account balance or guaranteed settlement. |

Source: [server/routers/provider_models.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/provider_models.py#L303).

### `provider_models.ProviderModelSettingsUpdate`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `enabled` | boolean or null | Optional; omit | Whether the model is eligible for selection. |
| `is_default` | boolean or null | Optional; omit | Whether this custom-provider model is the provider’s default under native media rules. |
| `model_id` | string or null | Optional; omit | Provider-facing model identity for the model row. |
| `multiplier` | number or null | Optional; omit | Nonnegative local price/accounting multiplier; zero recorded price does not establish a free provider request. |
| `capability_overrides` | object or null | Optional; omit | Complete capability override map; native validation applies and null/empty clears under the model-settings contract. |
| `endpoint` | string or null | Optional; omit | Selected supported endpoint/channel identity; this is distinct from base_url and custom path overrides. |
| `path_overrides` | map&lt;string, string&gt; or null | Optional; omit | Supported request-path overrides keyed by the endpoint’s named request slots. |
| `resolution` | string or null | Optional; omit | Provider/model-specific resolution setting. |
| `entry` | EntryUpdate or null | Optional; omit | Editable catalog-entry values; saving a user copy stops that entry following official updates. |
| `entry_binding` | string or null | Optional; omit | Existing same-media catalog entry linked to this provider model/tier. |
| `new_entry` | NewEntryBody or null | Optional; omit | New catalog entry created/bound when the model has no existing suitable entry; native atomic validation applies. |

Source: [server/routers/provider_models.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/provider_models.py#L316).

### `custom_providers.ModelInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model_id` | string | Required | Provider-facing model identity for the model row. |
| `display_name` | string | Required | User-facing provider/credential/model/entry label. |
| `endpoint` | string | Required | Selected supported endpoint/channel identity; this is distinct from base_url and custom path overrides. |
| `is_default` | boolean | Default false | Whether this custom-provider model is the provider’s default under native media rules. |
| `is_enabled` | boolean | Default true | Whether this custom-provider model is eligible. |
| `resolution` | string or null | Optional; omit | Provider/model-specific resolution setting. |
| `capability_overrides` | object or null | Optional; omit | Complete capability override map; native validation applies and null/empty clears under the model-settings contract. |
| `path_overrides` | map&lt;string, string&gt; or null | Optional; omit | Supported request-path overrides keyed by the endpoint’s named request slots. |
| `multiplier` | number | Default 1.0 | Nonnegative local price/accounting multiplier; zero recorded price does not establish a free provider request. Bounds: min 0. |
| `entry_binding` | string or null | Optional; omit | Existing same-media catalog entry linked to this provider model/tier. |

Source: [server/routers/custom_providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/custom_providers.py#L166).

### `custom_providers.CreateProviderRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `display_name` | string | Required | User-facing provider/credential/model/entry label. |
| `discovery_format` | "openai" / "google" / "comfyui" | Required | Native discovery/protocol format choosing model discovery and supported endpoint behavior. |
| `base_url` | string | Required | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string | Required | Provider/Agent secret key for this connection; never a project prompt parameter. |
| `models` | array&lt;ModelInput&gt; | Default [] | Custom-provider model configuration list. |
| `image_max_workers` | integer or null | Optional; omit | Maximum concurrent image tasks for this provider, under native queue/rate limits. |
| `video_max_workers` | integer or null | Optional; omit | Maximum concurrent video tasks for this provider. |
| `audio_max_workers` | integer or null | Optional; omit | Maximum concurrent audio tasks for this provider. |

Source: [server/routers/custom_providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/custom_providers.py#L242).

### `custom_providers.UpdateProviderRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `display_name` | string or null | Optional; omit | User-facing provider/credential/model/entry label. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |

Source: [server/routers/custom_providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/custom_providers.py#L253).

### `custom_providers.FullUpdateProviderRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `display_name` | string | Required | User-facing provider/credential/model/entry label. |
| `base_url` | string | Required | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |
| `models` | array&lt;ModelInput&gt; or null | Optional; omit | Custom-provider model configuration list. |
| `image_max_workers` | integer or null | Optional; omit | Maximum concurrent image tasks for this provider, under native queue/rate limits. |
| `video_max_workers` | integer or null | Optional; omit | Maximum concurrent video tasks for this provider. |
| `audio_max_workers` | integer or null | Optional; omit | Maximum concurrent audio tasks for this provider. |

Source: [server/routers/custom_providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/custom_providers.py#L259).

### `custom_providers.ConnectivityCheckRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `discovery_format` | string | Required | Native discovery/protocol format choosing model discovery and supported endpoint behavior. |
| `base_url` | string | Required | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string | Required | Provider/Agent secret key for this connection; never a project prompt parameter. |

Source: [server/routers/custom_providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/custom_providers.py#L276).

### `custom_providers.DiscoverAnthropicRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |

Source: [server/routers/custom_providers.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/custom_providers.py#L346).

### `endpoint_tests.TestParametersInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model` | string | Required | Provider request model identity for the Agent or endpoint trial. |
| `prompt` | string | Default "" | Prompt sent by the endpoint preview/trial, not a saved formal-script edit. |
| `duration_seconds` | integer | Default 5 | Planned duration in seconds, subject to route/model validation. |
| `aspect_ratio` | string | Default "9:16" | Desired image/video ratio supported by the selected endpoint. |
| `resolution` | string or null | Optional; omit | Provider/model-specific resolution setting. |
| `generate_audio` | boolean | Default true | Endpoint trial native-audio intent, subject to channel support. |

Source: [server/routers/endpoint_tests.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/endpoint_tests.py#L109).

### `endpoint_tests.TestCredentialsInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `provider_id` | string or null | Optional; omit | Canonical configured provider identity. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |

Source: [server/routers/endpoint_tests.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/endpoint_tests.py#L130).

### `endpoint_tests.ModelRefInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `provider_id` | string | Required | Canonical configured provider identity. |
| `model_id` | string | Required | Provider-facing model identity for the model row. |

Source: [server/routers/endpoint_tests.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/endpoint_tests.py#L138).

### `endpoint_tests.PreviewRequestInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `definition` | schema-defined value | Required | Complete native declarative endpoint or ComfyUI workflow definition, validated under its format schema. |
| `parameters` | TestParametersInput | Required | Endpoint test/preview model, prompt, duration, ratio, resolution and audio-intent values. |
| `credentials` | TestCredentialsInput or null | Optional; omit | Test credential reference or explicit base_url/API key; native rules select one source. |

Source: [server/routers/endpoint_tests.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/endpoint_tests.py#L145).

### `endpoint_tests.CheckResponseInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `definition` | schema-defined value | Required | Complete native declarative endpoint or ComfyUI workflow definition, validated under its format schema. |
| `stage` | "submit" / "poll" / "result" | Required | Response stage being checked: submit, poll or result. |
| `response_body` | schema-defined value | Optional; omit | Actual supplied provider response sample to validate/extract; not a request to the provider. |

Source: [server/routers/endpoint_tests.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/endpoint_tests.py#L151).

### `endpoint_tests.TrialRunInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `definition` | schema-defined value | Optional; omit | Complete native declarative endpoint or ComfyUI workflow definition, validated under its format schema. |
| `model_ref` | ModelRefInput or null | Optional; omit | Existing provider/model row whose configured endpoint should be used for the trial. |
| `parameters` | TestParametersInput | Required | Endpoint test/preview model, prompt, duration, ratio, resolution and audio-intent values. |
| `credentials` | TestCredentialsInput or null | Optional; omit | Test credential reference or explicit base_url/API key; native rules select one source. |

Source: [server/routers/endpoint_tests.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/endpoint_tests.py#L158).

### `object_storage.NewImageTargetBody`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `target` | "local" / "object_storage" | Required | Storage destination for newly saved images; choose the native local/object-storage target value. |

Source: [server/routers/object_storage.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/object_storage.py#L79).

### `object_storage.SaveObjectStorageConnectionRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `kind` | "tos" | Default "tos" | Native object-storage connection/backend kind. |
| `region` | string | Required | Configured object-storage/provider-library region. Bounds: max length 2048. |
| `endpoint` | string | Required | Selected supported endpoint/channel identity; this is distinct from base_url and custom path overrides. Bounds: max length 2048. |
| `bucket` | string | Required | Object-storage bucket name. Bounds: max length 2048. |
| `access_key_id` | string or null | Optional; omit | Storage/provider-library access-key identifier; document the field, not its saved secret value. Bounds: max length 2048. |
| `secret_access_key` | string or null | Optional; omit | Secret storage/provider-library access key; retain only in native credential storage. Bounds: max length 2048. |

Source: [server/routers/object_storage.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/object_storage.py#L83).

### `object_storage.WorkCacheCleanupRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `min_idle_seconds` | integer | Default 0 | Minimum idle age for native local work-cache cleanup; active/in-use work remains protected. Bounds: min 0. |

Source: [server/routers/object_storage.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/object_storage.py#L98).

### `asset_library.CreateAccountRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `site` | "volcengine" / "byteplus" | Required | Native provider asset-library site. |
| `name` | string | Required | User-visible provider-library account label. Bounds: min length 1, max length 128. |
| `region` | string or null | Optional; omit | Configured object-storage/provider-library region. |
| `project_name` | string | Default "default" | Provider-side project/namespace for this account, not the local ArcReel project name. Bounds: min length 1, max length 128. |
| `access_key_id` | string | Required | Storage/provider-library access-key identifier; document the field, not its saved secret value. Bounds: max length 2048. |
| `secret_access_key` | string | Required | Secret storage/provider-library access key; retain only in native credential storage. Bounds: max length 2048. |

Source: [server/routers/asset_library.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/asset_library.py#L65).

### `asset_library.UpdateAccountRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string or null | Optional; omit | User-visible provider-library account label. |
| `site` | "volcengine" / "byteplus" or null | Optional; omit | Native provider asset-library site. |
| `region` | string or null | Optional; omit | Configured object-storage/provider-library region. |
| `project_name` | string or null | Optional; omit | Provider-side project/namespace for this account, not the local ArcReel project name. |
| `access_key_id` | string or null | Optional; omit | Storage/provider-library access-key identifier; document the field, not its saved secret value. |
| `secret_access_key` | string or null | Optional; omit | Secret storage/provider-library access key; retain only in native credential storage. |

Source: [server/routers/asset_library.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/asset_library.py#L74).

### `asset_library.ConfirmBindingRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `account_id` | integer | Required | Configured provider asset-library account identity. |

Source: [server/routers/asset_library.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/asset_library.py#L104).

### `catalog.CatalogEntryKey`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `maker` | string | Required | Catalog model-maker identifier. |
| `name` | string | Required | Catalog model name under the maker/media-type namespace. |
| `media_type` | "text" / "image" / "video" / "audio" | Required | Declared image/video/text/audio domain, subject to this contract’s enum. |

Source: [server/routers/catalog.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/catalog.py#L85).

### `catalog.NewEntryBody`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `maker` | string | Required | Catalog model-maker identifier. |
| `name` | string | Required | Catalog model name under the maker/media-type namespace. |
| `media_type` | "text" / "image" / "video" / "audio" | Required | Declared image/video/text/audio domain, subject to this contract’s enum. |
| `display_name` | string or null | Optional; omit | User-facing provider/credential/model/entry label. |
| `facts` | object or null | Optional; omit | Media-specific model facts/capabilities validated by the catalog schema. |
| `price` | object or null | Optional; omit | Structured catalog pricing dimensions/rates; not provider account balance or guaranteed settlement. |

Source: [server/routers/catalog.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/catalog.py#L93).

### Nested `provider_models.ProviderModelSettingsUpdate.EntryUpdate`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `maker` | string | Required | Catalog model-maker identifier. |
| `name` | string | Required | Catalog model name under the maker/media-type namespace. |
| `media_type` | "text" / "image" / "video" / "audio" | Required | Declared image/video/text/audio domain, subject to this contract’s enum. |
| `display_name` | string or null | Optional; omit | User-facing provider/credential/model/entry label. |
| `facts` | object or null | Optional; omit | Media-specific model facts/capabilities validated by the catalog schema. |
| `price` | object or null | Optional; omit | Structured catalog pricing dimensions/rates; not provider account balance or guaranteed settlement. |

### Nested `provider_models.ProviderModelSettingsUpdate.NewEntryBody`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `maker` | string | Required | Catalog model-maker identifier. |
| `name` | string | Required | Catalog model name under the maker/media-type namespace. |
| `media_type` | "text" / "image" / "video" / "audio" | Required | Declared image/video/text/audio domain, subject to this contract’s enum. |
| `display_name` | string or null | Optional; omit | User-facing provider/credential/model/entry label. |
| `facts` | object or null | Optional; omit | Media-specific model facts/capabilities validated by the catalog schema. |
| `price` | object or null | Optional; omit | Structured catalog pricing dimensions/rates; not provider account balance or guaranteed settlement. |

### Nested `custom_providers.CreateProviderRequest.ModelInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model_id` | string | Required | Provider-facing model identity for the model row. |
| `display_name` | string | Required | User-facing provider/credential/model/entry label. |
| `endpoint` | string | Required | Selected supported endpoint/channel identity; this is distinct from base_url and custom path overrides. |
| `is_default` | boolean | Default false | Whether this custom-provider model is the provider’s default under native media rules. |
| `is_enabled` | boolean | Default true | Whether this custom-provider model is eligible. |
| `resolution` | string or null | Optional; omit | Provider/model-specific resolution setting. |
| `capability_overrides` | object or null | Optional; omit | Complete capability override map; native validation applies and null/empty clears under the model-settings contract. |
| `path_overrides` | map&lt;string, string&gt; or null | Optional; omit | Supported request-path overrides keyed by the endpoint’s named request slots. |
| `multiplier` | number | Default 1.0 | Nonnegative local price/accounting multiplier; zero recorded price does not establish a free provider request. Bounds: min 0. |
| `entry_binding` | string or null | Optional; omit | Existing same-media catalog entry linked to this provider model/tier. |

### Nested `custom_providers.FullUpdateProviderRequest.ModelInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model_id` | string | Required | Provider-facing model identity for the model row. |
| `display_name` | string | Required | User-facing provider/credential/model/entry label. |
| `endpoint` | string | Required | Selected supported endpoint/channel identity; this is distinct from base_url and custom path overrides. |
| `is_default` | boolean | Default false | Whether this custom-provider model is the provider’s default under native media rules. |
| `is_enabled` | boolean | Default true | Whether this custom-provider model is eligible. |
| `resolution` | string or null | Optional; omit | Provider/model-specific resolution setting. |
| `capability_overrides` | object or null | Optional; omit | Complete capability override map; native validation applies and null/empty clears under the model-settings contract. |
| `path_overrides` | map&lt;string, string&gt; or null | Optional; omit | Supported request-path overrides keyed by the endpoint’s named request slots. |
| `multiplier` | number | Default 1.0 | Nonnegative local price/accounting multiplier; zero recorded price does not establish a free provider request. Bounds: min 0. |
| `entry_binding` | string or null | Optional; omit | Existing same-media catalog entry linked to this provider model/tier. |

### Nested `endpoint_tests.PreviewRequestInput.TestCredentialsInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `provider_id` | string or null | Optional; omit | Canonical configured provider identity. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |

### Nested `endpoint_tests.PreviewRequestInput.TestParametersInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model` | string | Required | Provider request model identity for the Agent or endpoint trial. |
| `prompt` | string | Default "" | Prompt sent by the endpoint preview/trial, not a saved formal-script edit. |
| `duration_seconds` | integer | Default 5 | Planned duration in seconds, subject to route/model validation. |
| `aspect_ratio` | string | Default "9:16" | Desired image/video ratio supported by the selected endpoint. |
| `resolution` | string or null | Optional; omit | Provider/model-specific resolution setting. |
| `generate_audio` | boolean | Default true | Endpoint trial native-audio intent, subject to channel support. |

### Nested `endpoint_tests.TrialRunInput.ModelRefInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `provider_id` | string | Required | Canonical configured provider identity. |
| `model_id` | string | Required | Provider-facing model identity for the model row. |

### Nested `endpoint_tests.TrialRunInput.TestCredentialsInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `provider_id` | string or null | Optional; omit | Canonical configured provider identity. |
| `base_url` | string or null | Optional; omit | Provider/Agent service base address, normalized/validated by its native contract. |
| `api_key` | string or null | Optional; omit | Provider/Agent secret key for this connection; never a project prompt parameter. |

### Nested `endpoint_tests.TrialRunInput.TestParametersInput`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `model` | string | Required | Provider request model identity for the Agent or endpoint trial. |
| `prompt` | string | Default "" | Prompt sent by the endpoint preview/trial, not a saved formal-script edit. |
| `duration_seconds` | integer | Default 5 | Planned duration in seconds, subject to route/model validation. |
| `aspect_ratio` | string | Default "9:16" | Desired image/video ratio supported by the selected endpoint. |
| `resolution` | string or null | Optional; omit | Provider/model-specific resolution setting. |
| `generate_audio` | boolean | Default true | Endpoint trial native-audio intent, subject to channel support. |

## Original endpoint definition: `json_poll`

Whole-definition payloads are validated against this original JSON Schema, including conditional/media-specific checks in its native validator. Project schema_version is managed state; **endpoint definition schema_version is a required format input**.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `kind` | "declarative" | Required | Definition-kind discriminator selecting this exact native schema/protocol. |
| `schema_version` | semver | Required | Endpoint/workflow definition format version; separate from managed project schema_version. |
| `media_type` | "image" / "video" | Default "video" | Declared image/video/text/audio domain, subject to this contract’s enum. |
| `meta` | meta | Required | Definition identity/version/documentation metadata. |
| `auth` | auth | Required | Native authentication-template object; absence/empty behavior depends on the definition kind. |
| `inputs` | map&lt;string, inputDecl&gt; | Optional; omit | Named media inputs encoded for use in endpoint templates, or ComfyUI node inputs for that owner. |
| `enum_maps` | map&lt;string, map&lt;string, scalar&gt;&gt; | Optional; omit | Maps internal scalar parameter values to provider request values before template rendering. |
| `defaults` | map&lt;string, scalar&gt; | Optional; omit | Endpoint parameter defaults applied when no request value is supplied. |
| `submit` | submitRequest | Required | Generation-submission request template and task-ID extraction. |
| `poll` | pollRequest | Required | Provider-job polling request template and status/result extraction. |
| `result` | resultRequest | Optional; omit | Optional result/retrieval request stage. |
| `status_map` | map&lt;string, string&gt; | Optional; omit | Provider status strings mapped to queued/running/succeeded/failed. |
| `capabilities` | capabilities | Optional; omit | Locally declared channel capabilities validated against the endpoint/media schema. |

Source: [packages/arcreel-market-core/src/arcreel_market_core/endpoint_definition/schema.json](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/packages/arcreel-market-core/src/arcreel_market_core/endpoint_definition/schema.json).

### Definition object `json_poll.eachDirective`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `in` | string | Required | List expression traversed by the native $each template directive. Bounds: pattern ^inputs\.[a-z][a-z0-9_]*$. |
| `as` | identifier | Required | Variable alias for each element of the $each template list. |
| `item` | jsonTemplate | Optional; omit | Template for each list element. |
| `key` | template | Optional; omit | Template key for each map entry under the native directive. |
| `value` | jsonTemplate | Optional; omit | Template value for each generated map entry. |

### Definition object `json_poll.meta`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string | Required | Endpoint/workflow definition name used with author to identify its lineage. Bounds: min length 1, max length 80. |
| `author` | string | Required | Definition author namespace used with name for lineage/duplicate checks. Bounds: min length 1, max length 80. |
| `version` | semver | Required | Definition version or native stored revision identity as defined by its owner. |
| `min_app_version` | semver | Optional; omit | Minimum app-version hint attached to a definition. |
| `description` | string | Optional; omit | Human-readable definition documentation, not a generated scene prompt. Bounds: max length 2000. |
| `homepage` | string | Optional; omit | Definition author/project documentation URL. Bounds: pattern ^https?://[^\s/?#]+\S*$. |
| `hints` | object | Optional; omit | Optional suggested connection/model metadata; not automatic creation of a provider. |

### Definition object `json_poll.auth`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `headers` | headerMap | Optional; omit | Header-name to native credential/template value mapping. |
| `query` | queryMap | Optional; omit | Query-parameter to native credential/template value mapping. |

### Definition object `json_poll.inputDecl`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `source` | "start_image" / "end_image" / "reference_images" / "reference_audio_files" | Required | Native media/parameter source for this declared input. |
| `encoding` | "data_uri" / "base64" | Required | Encoding applied to this declared media input before template use. |
| `required` | boolean | Default false | Whether a declared endpoint input must be supplied. |

### Definition object `json_poll.requestBase`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `method` | "GET" / "POST" / "PUT" | Required | HTTP method for this request stage. |
| `url` | urlTemplate | Required | Native request URL/template, not a project-file path. |
| `headers` | headerMap | Optional; omit | Header-name to native credential/template value mapping. |
| `body` | jsonTemplate | Optional; omit | JSON request-body template. |

### Definition object `json_poll.submitRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `method` | "GET" / "POST" / "PUT" | Required | HTTP method for this request stage. |
| `url` | urlTemplate | Required | Native request URL/template, not a project-file path. |
| `headers` | headerMap | Optional; omit | Header-name to native credential/template value mapping. |
| `body` | jsonTemplate | Optional; omit | JSON request-body template. |
| `extract` | object | Required | Named response extraction paths for this stage. |

### Definition object `json_poll.pollRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `method` | "GET" / "POST" / "PUT" | Required | HTTP method for this request stage. |
| `url` | urlTemplate | Required | Native request URL/template, not a project-file path. |
| `headers` | headerMap | Optional; omit | Header-name to native credential/template value mapping. |
| `body` | jsonTemplate | Optional; omit | JSON request-body template. |
| `expire_on_404` | boolean | Default true | On resumed polling, whether an HTTP 404 means the provider task expired; the runtime defaults to true when omitted. |
| `extract` | object | Required | Named response extraction paths for this stage. |

### Definition object `json_poll.resultRequest`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `method` | "GET" / "POST" / "PUT" | Required | HTTP method for this request stage. |
| `url` | urlTemplate | Required | Native request URL/template, not a project-file path. |
| `headers` | headerMap | Optional; omit | Header-name to native credential/template value mapping. |
| `extract` | object | Required | Named response extraction paths for this stage. |

### Definition object `json_poll.capabilities`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `text_to_video` | boolean | Default true | Whether the channel declares text-to-video support. |
| `text_to_image` | boolean | Default false | Whether the channel declares text-to-image support. |
| `image_to_image` | boolean | Default false | Whether the channel declares image-edit/reference input support. |
| `first_frame` | boolean | Default false | Whether the video channel accepts a starting frame. |
| `last_frame` | boolean | Default false | Whether the video channel accepts a final frame. |
| `max_reference_images` | integer | Default 0 | Maximum declared image-reference count. Bounds: min 0. |
| `reference_audio_mode` | "none" / "direct" | Default "none" | Native reference-audio submission mode. |
| `max_reference_audio_count` | integer | Default 0 | Maximum reference-audio clip count per request. Bounds: min 0. |
| `max_reference_audio_total_seconds` | ['number', 'null'] | Optional; omit | Maximum combined duration of submitted audio references. Bounds: min 0. |
| `reference_audio_per_image` | boolean | Default false | Whether each audio reference must be paired with a particular visual reference. |
| `max_prompt_chars` | ['integer', 'null'] | Optional; omit | Maximum supported prompt character count. Bounds: min 1. |
| `first_frame_ratio_adaptive_only` | boolean | Default false | Whether a first-frame request must use adaptive ratio. |
| `audio_track` | "controllable" / "always_on" / "always_off" | Default "controllable" | Native output-audio behavior for the channel. |
| `reference_route_audio_track` | "controllable" / "always_on" / "always_off" / null | Optional; omit | Reference-route-specific output-audio behavior. |

## Original endpoint definition: `comfyui`

Whole-definition payloads are validated against this original JSON Schema, including conditional/media-specific checks in its native validator. Project schema_version is managed state; **endpoint definition schema_version is a required format input**.

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `kind` | "comfyui" | Required | Definition-kind discriminator selecting this exact native schema/protocol. |
| `schema_version` | semver | Required | Endpoint/workflow definition format version; separate from managed project schema_version. |
| `meta` | meta | Required | Definition identity/version/documentation metadata. |
| `media_type` | "image" / "video" | Required | Declared image/video/text/audio domain, subject to this contract’s enum. |
| `auth` | auth | Optional; omit | Native authentication-template object; absence/empty behavior depends on the definition kind. |
| `workflow` | workflow | Required | ComfyUI API-format workflow node graph. |
| `bindings` | bindings | Required | Explicit mapping between ArcReel production parameters/media and ComfyUI graph inputs/outputs. |

Source: [packages/arcreel-market-core/src/arcreel_market_core/comfyui/schema.json](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/packages/arcreel-market-core/src/arcreel_market_core/comfyui/schema.json).

### Definition object `comfyui.meta`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `name` | string | Required | Endpoint/workflow definition name used with author to identify its lineage. Bounds: min length 1, max length 80. |
| `author` | string | Required | Definition author namespace used with name for lineage/duplicate checks. Bounds: min length 1, max length 80. |
| `version` | semver | Required | Definition version or native stored revision identity as defined by its owner. |
| `min_app_version` | semver | Optional; omit | Minimum app-version hint attached to a definition. |
| `description` | string | Optional; omit | Human-readable definition documentation, not a generated scene prompt. Bounds: max length 2000. |
| `homepage` | string | Optional; omit | Definition author/project documentation URL. Bounds: pattern ^https?://[^\s/?#]+\S*$. |
| `hints` | object | Optional; omit | Optional suggested connection/model metadata; not automatic creation of a provider. |

### Definition object `comfyui.auth`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `headers` | headerMap | Optional; omit | Header-name to native credential/template value mapping. |
| `query` | queryMap | Optional; omit | Query-parameter to native credential/template value mapping. |

### Definition object `comfyui.workflowNode`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `inputs` | object | Optional; omit | Named media inputs encoded for use in endpoint templates, or ComfyUI node inputs for that owner. |
| `_meta` | object | Optional; omit | ComfyUI node metadata, such as its editor label. |

### Definition object `comfyui.writeTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "write" | Optional; omit | Declared binding direction for this graph target. |

### Definition object `comfyui.steppedTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "write" | Optional; omit | Declared binding direction for this graph target. |
| `step` | integer | Optional; omit | Native numeric quantization step for the mapped graph value. Bounds: min 1. |

### Definition object `comfyui.framesTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "write" | Optional; omit | Declared binding direction for this graph target. |
| `step` | integer | Optional; omit | Native numeric quantization step for the mapped graph value. Bounds: min 1. |
| `fps` | number | Optional; omit | Frame-rate input/basis used for frame-count/duration conversion. Bounds: greater than 0. |

### Definition object `comfyui.readTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "read" | Required | Declared binding direction for this graph target. |

### Definition object `comfyui.seedTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "write" | Optional; omit | Declared binding direction for this graph target. |
| `policy` | "random" / "keep" | Default "random" | Native seed behavior policy for this graph binding. |

### Definition object `comfyui.orderedMediaTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "write" | Optional; omit | Declared binding direction for this graph target. |
| `consumer` | object | Optional; omit | Ordered-media consumer declaration for a graph binding. |

### Definition object `comfyui.outputTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "write" | Optional; omit | Declared binding direction for this graph target. |

### Definition object `comfyui.bindings`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `prompt` | array&lt;writeTarget&gt; | Optional; omit | Graph target receiving the positive production prompt. |
| `negative_prompt` | array&lt;writeTarget&gt; | Optional; omit | ComfyUI graph binding for supported negative-prompt input; not a universal video API parameter. |
| `start_image` | array&lt;writeTarget&gt; | Optional; omit | Graph binding for the first-frame image. |
| `end_image` | array&lt;writeTarget&gt; | Optional; omit | Graph binding for the end-frame image. |
| `reference_images` | array&lt;orderedMediaTarget&gt; | Optional; omit | Ordered graph binding for visual references. |
| `width` | array&lt;steppedTarget&gt; | Optional; omit | Graph binding for output width. |
| `height` | array&lt;steppedTarget&gt; | Optional; omit | Graph binding for output height. |
| `frames` | array&lt;framesTarget&gt; | Optional; omit | Graph frame-count binding, optionally converted/quantized using step/fps; not inspector sampling. |
| `fps` | array&lt;readTarget&gt; | Optional; omit | Frame-rate input/basis used for frame-count/duration conversion. |
| `seed` | array&lt;seedTarget&gt; | Optional; omit | Generic compatibility seed; actual effect depends on provider/channel transmission. |
| `output` | array&lt;outputTarget&gt; | Optional; omit | Graph node/output binding from which to collect generated media. Bounds: max items 1. |
| `reference_audio` | array&lt;orderedMediaTarget&gt; | Optional; omit | Ordered graph binding for audio references. |
| `aspect_ratio` | array&lt;aspectRatioTarget&gt; | Optional; omit | Graph aspect-ratio binding with its declared supported value map. |

### Definition object `comfyui.aspectRatioTarget`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |
| `direction` | "write" | Optional; omit | Declared binding direction for this graph target. |
| `values` | map&lt;string, string&gt; | Required | Supported graph aspect-ratio value mapping. |

### Inline definition object `json_poll.meta.hints`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `base_url` | string | Optional; omit | Suggested provider base URL metadata; not automatically saved as a connection. Bounds: pattern ^https?://[^\s/?#]+\S*$. |
| `suggested_models` | array&lt;object&gt; | Optional; omit | Suggested provider-model metadata supplied by the endpoint author; not automatic model registration. |

### Inline definition object `json_poll.submitRequest.extract`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `task_id` | extractSpec | Required | Response extraction path(s) for task_id; named usage entries follow the native extraction grammar. |
| `error` | extractSpec | Optional; omit | Response extraction path(s) for error; named usage entries follow the native extraction grammar. |

### Inline definition object `json_poll.pollRequest.extract`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `status` | extractSpec | Required | Response extraction path(s) for status; named usage entries follow the native extraction grammar. |
| `video_url` | extractSpec | Optional; omit | Response extraction path(s) for video_url; named usage entries follow the native extraction grammar. |
| `image_url` | extractSpec | Optional; omit | Response extraction path(s) for image_url; named usage entries follow the native extraction grammar. |
| `image_b64` | extractSpec | Optional; omit | Response extraction path(s) for image_b64; named usage entries follow the native extraction grammar. |
| `error` | extractSpec | Optional; omit | Response extraction path(s) for error; named usage entries follow the native extraction grammar. |
| `failure` | extractSpec | Optional; omit | Response extraction path(s) for failure; named usage entries follow the native extraction grammar. |
| `result_id` | extractSpec | Optional; omit | Response extraction path(s) for result_id; named usage entries follow the native extraction grammar. |
| `usage` | map&lt;string, extractSpec&gt; | Optional; omit | Response extraction path(s) for usage; named usage entries follow the native extraction grammar. |

### Inline definition object `json_poll.resultRequest.extract`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `video_url` | extractSpec | Optional; omit | Response extraction path(s) for video_url; named usage entries follow the native extraction grammar. |
| `image_url` | extractSpec | Optional; omit | Response extraction path(s) for image_url; named usage entries follow the native extraction grammar. |
| `image_b64` | extractSpec | Optional; omit | Response extraction path(s) for image_b64; named usage entries follow the native extraction grammar. |
| `error` | extractSpec | Optional; omit | Response extraction path(s) for error; named usage entries follow the native extraction grammar. |
| `usage` | map&lt;string, extractSpec&gt; | Optional; omit | Response extraction path(s) for usage; named usage entries follow the native extraction grammar. |

### Inline definition object `comfyui.meta.hints`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `base_url` | string | Optional; omit | Suggested provider base URL metadata; not automatically saved as a connection. Bounds: pattern ^https?://[^\s/?#]+\S*$. |
| `suggested_models` | array&lt;object&gt; | Optional; omit | Suggested provider-model metadata supplied by the endpoint author; not automatic model registration. |

### Inline definition object `comfyui.workflowNode._meta`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `title` | string | Optional; omit | User-visible title for this object. |

### Inline definition object `comfyui.orderedMediaTarget.consumer`

| Input | Type / allowed values | Required / default | Description |
| --- | --- | --- | --- |
| `node` | node | Required | ComfyUI node identifier to bind. |
| `input` | string | Required | Named node input socket to write. Bounds: min length 1. |
| `class_type` | string | Required | Expected ComfyUI node class for binding validation. Bounds: min length 1. |
| `title` | string | Optional; omit | User-visible title for this object. |

## Cross-field configuration rules

- Creating an Agent credential chooses inline api_key or from_custom_provider_id under the native validator. Model tier bindings must reference existing text entries; updates merge supplied tiers and null clears a binding. Activation and model selection are separate inputs.
- Provider/account multipliers change local accounting. A zero multiplier is not proof that remote generation is free.
- ProviderModelSettingsUpdate applies different permissions to official/user-managed/custom-provider rows. Capability overrides replace their map; catalog entry edits create a user copy; new_entry and binding changes are validated atomically.
- Endpoint preview/check-response and real trial-run are different operations. Real connection trials can send generation requests and incur cost; documenting them does not authorize testing.
- Raw custom definition/workflow graph objects can contain arbitrary provider node/body values. The declared schema and native validator, not this finite parameter index, determine which combinations can be saved and executed.
- Object-storage connection, new-image destination and work-cache cleanup are distinct actions. Cache cleanup does not authorize deleting current project media.

## Native API-key and memory configuration inputs

| Interface | Inputs | Native behavior |
| --- | --- | --- |
| POST /api/v1/api-keys | name; expires_days integer >=0 or null | Name labels the credential. Omitted/null expiry uses 30 days; 0 means no expiry. Creation returns the full arc- key once. |
| API-key list/delete | Existing key identity for deletion | Native key management requires JWT-authenticated access; an API key cannot manage itself. Documentation does not create/revoke a key. |
| User/project Agent memory file write | Scope route; filename; raw Markdown/text request body | The memory store validates the admitted filename; body is text, not a JSON settings map. User and project memory are separate scopes. |
| Memory read/delete | Scope route and filename | Reads or deletes the named native memory record; these are UI/REST operations, not additions to the 61-tool MCP catalog. |

Sources: [server/routers/api_keys.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/api_keys.py); [server/routers/agent_memory.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/agent_memory.py).

## Coverage and verification

This document was rebuilt from the original upstream creation schemas, all 28 mutable project fields, all 24 global fields, native legacy allowlists and asset definitions. Per-shot/UI operation forms are in the production companion. This is an original-product reference, not an audit of a running customized project. No settings were applied and no production was executed.
