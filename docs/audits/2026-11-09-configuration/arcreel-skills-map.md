# ArcReel native skills map

**Reviewed again on 2026-11-09:** request descriptions were checked by their owning operation, not reused by field name. Cross-field/handler constraints, native UI/configuration interfaces, profile support files and adapter-specific result encoding were checked against the same pinned upstream. No production operations were executed.

Scope: **original ArcReel upstream only**, pinned to [`7149433a21b3981da521e35b517a1fbe3356cc87`](https://github.com/ArcReel/ArcReel/tree/7149433a21b3981da521e35b517a1fbe3356cc87), main resolved on 2026-11-09; commit timestamp 2026-11-09T17:06:15Z. Descriptions explain the original source in English without changing its functional names or contracts. This is not a running-instance configuration audit.

Companions: [MCP](arcreel-mcp-map.md), [production inputs](production-inputs-by-use-case.md), [project configuration](project-configuration-inputs.md).

Reference boundary: use this map with its three companion maps to understand the pinned original application. It does not inventory extensions or credentials in a customized installation, prescribe host-agent responsibilities, or authorize execution. A later integration plan must establish those responsibilities against its actual target version.

## What is a skill here?

A skill is an instruction package for the ArcReel Agent: when to act, what context to read, which native tools/subagents to use and how to report or confirm results. It is not a model, a credential, a project settings field or a new deterministic generation capability. Its runtime effect still depends on the implementation, available inputs, model/provider constraints and authorized scope.

The original runtime profile contains **10 logical production skills in 12 source files**: video-workflow has three content-mode variants. It also ships **7 subagent definitions** and **2 official generic remote-integration skills** under skills/. These are separate roles, listed below. No development/host skill catalog is included.

## Production skills by use case

| Skill | Use case | Primary result |
| --- | --- | --- |
| `video-workflow` | End-to-end creation, continuation, next-step or progress requests; not a single isolated image correction. | Read get_workflow_plan, dispatch the matching native specialist, present results/confirmations and continue from the returned state. |
| `manage-project` | Project/asset definitions, overview, permitted settings, asset rename/merge and capability queries. | Apply native metadata operations, preserve references during rename/merge and report capabilities/impact. |
| `generate-script` | Internal prompt-authoring stage; the workflow chooses direct ad authoring or the appropriate specialist dispatch. | Fill pending image/video layers or reference-unit bodies; create a whole ad script when appropriate. |
| `generate-assets` | Generate or regenerate character, scene, prop or product sheets, including supported character variants. | Generate missing/explicit asset targets, inspect results and route local corrections versus regeneration. |
| `generate-storyboard` | Create missing storyboard frames or explicitly redraw named frames. | Queue images and perform the native image-review checkpoint. |
| `generate-grid` | Use storyboard grid assembly where the original project supports/enables it. | Preview/group composites, generate grids, then split approved cells into storyboard frames. |
| `generate-video` | Generate/recreate episode videos or an explicit unit selection. | Precheck scope/cost tiers, submit native video batch and summarize outcomes/recovery. |
| `generate-narration-audio` | Generate missing or explicitly requested separate narrator voiceover. | Produce eligible narration audio through the native queue and report per-target results. |
| `edit-video` | Edit ready episode media, respond to clip changes, mix BGM, render/export or manage timeline revisions. | Review versions, choose clips, submit trims/holds/gain/transitions/BGM changes and deliver requested output. |
| `adapt-custom-endpoint` | Connect a JSON-submit/poll image or video provider or author/validate an endpoint definition. | Validate definition/response extraction, preview request, run only authorized real trials, then save explicitly. |
## `video-workflow`

| Item | Description |
| --- | --- |
| When used | End-to-end creation, continuation, next-step or progress requests; not a single isolated image correction. |
| Inputs/context | Project/content mode, existing state, requested episode and original requirements. |
| What it does | Read get_workflow_plan, dispatch the matching native specialist, present results/confirmations and continue from the returned state. |
| Tools/dependencies | Server plan, native subagents, project/source registry and applicable asset/media steps. |
| Effects/cost | Text/Agent usage and downstream paid generation are possible; a progress-only request should only report state. |
| Limits | Three content-mode variants install as one logical skill; route/capability and user confirmation still govern actions. |

Original sources: [agent_runtime_profile/.claude/skills/video-workflow/SKILL.ad.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/video-workflow/SKILL.ad.md), [agent_runtime_profile/.claude/skills/video-workflow/SKILL.drama.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/video-workflow/SKILL.drama.md), [agent_runtime_profile/.claude/skills/video-workflow/SKILL.narration.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/video-workflow/SKILL.narration.md).

## `manage-project`

| Item | Description |
| --- | --- |
| When used | Project/asset definitions, overview, permitted settings, asset rename/merge and capability queries. |
| Inputs/context | Project identity, target table/names, sparse field maps and intended change. |
| What it does | Apply native metadata operations, preserve references during rename/merge and report capabilities/impact. |
| Tools/dependencies | patch_project, rename_asset, merge_asset, get_video_capabilities and source/episode planning tools. |
| Effects/cost | Writes metadata or structural changes; merge/reset can affect existing work. Preview and native confirmations apply. |
| Limits | Frontmatter also sets user-invocable=false. Its settings branch has a seven-key allowlist; it does not expose every UI project-setting field. |

Original sources: [agent_runtime_profile/.claude/skills/manage-project/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/manage-project/SKILL.md).

## `generate-script`

| Item | Description |
| --- | --- |
| When used | Internal prompt-authoring stage; the workflow chooses direct ad authoring or the appropriate specialist dispatch. |
| Inputs/context | Formal pending content, project definitions/model settings and optional authoring instructions. |
| What it does | Fill pending image/video layers or reference-unit bodies; create a whole ad script when appropriate. |
| Tools/dependencies | generate_episode_script and native text/draft validation. |
| Effects/cost | Configured text-model inference unless dry_run is used. |
| Limits | Frontmatter sets user-invocable=false. The ad workflow can call generate_episode_script directly; narration/drama formal authoring dispatches create-episode-script, which preloads this skill. Existing content replacement uses native overwrite acceptance. |

Original sources: [agent_runtime_profile/.claude/skills/generate-script/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-script/SKILL.md).

## `generate-assets`

| Item | Description |
| --- | --- |
| When used | Generate or regenerate character, scene, prop or product sheets, including supported character variants. |
| Inputs/context | Stored definitions/style and selection by type/names or episode references; applicable originals. |
| What it does | Generate missing/explicit asset targets, inspect results and route local corrections versus regeneration. |
| Tools/dependencies | generate_assets, list_pending_assets, inspect_images, edit_images and review-images. |
| Effects/cost | Provider image generation/editing is paid; Agent/reviewer usage is separate from media calls. |
| Limits | A sheet must be referenced by a shot/body to become its visual input. Existing usable sheets are not blanket regeneration targets. |

Original sources: [agent_runtime_profile/.claude/skills/generate-assets/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-assets/SKILL.md).

## `generate-storyboard`

| Item | Description |
| --- | --- |
| When used | Create missing storyboard frames or explicitly redraw named frames. |
| Inputs/context | Formal script/image prompts, shot IDs, ratio/style and named approved sheets. |
| What it does | Queue images and perform the native image-review checkpoint. |
| Tools/dependencies | generate_storyboards, inspect_images and review-images. |
| Effects/cost | Paid image generation; explicit selected targets can redraw existing imagery. |
| Limits | Storyboard route only; no replacement of the formal prompt by a random compatibility request body. |

Original sources: [agent_runtime_profile/.claude/skills/generate-storyboard/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-storyboard/SKILL.md).

## `generate-grid`

| Item | Description |
| --- | --- |
| When used | Use storyboard grid assembly where the original project supports/enables it. |
| Inputs/context | storyboard route, grid_storyboard=true, script groups and applicable asset references. |
| What it does | Preview/group composites, generate grids, then split approved cells into storyboard frames. |
| Tools/dependencies | generate_grid(list_only), generate_grid and split_grids. |
| Effects/cost | Generation can cost; planning preview does not enqueue. Splitting writes covered frames. |
| Limits | Ad mode does not support grids. Split is separate from composite generation and requires the native approval flow. |

Original sources: [agent_runtime_profile/.claude/skills/generate-grid/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-grid/SKILL.md).

## `generate-video`

| Item | Description |
| --- | --- |
| When used | Generate/recreate episode videos or an explicit unit selection. |
| Inputs/context | Formal script/body, selected route/model capabilities, source frames or references and duration target scope. |
| What it does | Precheck scope/cost tiers, submit native video batch and summarize outcomes/recovery. |
| Tools/dependencies | generate_videos, get_video_capabilities, get_generation_batch and native admission. |
| Effects/cost | Paid provider work except preview/reuse; force can pay again. |
| Limits | Frame and reference routes differ. Preserve the original full target set and accepted tier mapping after admission confirmation. |

Original sources: [agent_runtime_profile/.claude/skills/generate-video/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-video/SKILL.md).

## `generate-narration-audio`

| Item | Description |
| --- | --- |
| When used | Generate missing or explicitly requested separate narrator voiceover. |
| Inputs/context | Narrator-owned canonical text, project TTS snapshot and script/segment IDs. |
| What it does | Produce eligible narration audio through the native queue and report per-target results. |
| Tools/dependencies | generate_narration_audio and applicable narrator-setting updates. |
| Effects/cost | Paid TTS synthesis; omission fills missing eligible audio, explicit selections define deliberate scope. |
| Limits | Not character voice audition, cast dialogue replacement or lip-sync generation. Separate narration is not required to generate native-audio videos. |

Original sources: [agent_runtime_profile/.claude/skills/generate-narration-audio/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-narration-audio/SKILL.md).

## `edit-video`

| Item | Description |
| --- | --- |
| When used | Edit ready episode media, respond to clip changes, mix BGM, render/export or manage timeline revisions. |
| Inputs/context | Native timeline, selected media candidates, review reports, requested editorial changes and output variant. |
| What it does | Review versions, choose clips, submit trims/holds/gain/transitions/BGM changes and deliver requested output. |
| Tools/dependencies | Timeline/version tools, inspect_video_units, review-footage, render_final_cut and export_jianying_draft. |
| Effects/cost | Metadata editing and local render/export do not generate new provider media by themselves; paid remedies are separate. |
| Limits | Contact-sheet review is visual evidence, not automatic audio/acting/lip-sync approval. Timeline completion is not editorial acceptance. |

Original sources: [agent_runtime_profile/.claude/skills/edit-video/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/edit-video/SKILL.md).

## `adapt-custom-endpoint`

| Item | Description |
| --- | --- |
| When used | Connect a JSON-submit/poll image or video provider or author/validate an endpoint definition. |
| Inputs/context | Provider protocol docs, definition/test JSON, example responses and applicable image/audio files/credential reference. |
| What it does | Validate definition/response extraction, preview request, run only authorized real trials, then save explicitly. |
| Tools/dependencies | scripts/custom_endpoint.py and references/definition-format.md. |
| Effects/cost | Real trial-run makes provider requests and can cost; validation/preview and saving have different effects. |
| Limits | Not a universal adapter for signed/multipart/input-dependent protocols. Existing endpoint overwrite and paid testing require explicit consent. |

Original sources: [agent_runtime_profile/.claude/skills/adapt-custom-endpoint/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/adapt-custom-endpoint/SKILL.md).

## Workflow variants

| Source variant | Installed purpose | Main path |
| --- | --- | --- |
| SKILL.ad.md | Advertising and general creative shorts | Brief/product intent → formal ad script → asset/media generation → timeline/editing. No ad script_plan or grids. |
| SKILL.drama.md | Dialogue-led adaptation | Source/episode planning → normalized drama script_plan → confirmation → formal visual authoring → media/editing. |
| SKILL.narration.md | Narration/commentary adaptation | Source/episode planning → narration segment plan → confirmation/authoring → images/video → applicable separate narration/editing. |

One variant is selected by content_mode and installed at the ordinary video-workflow/SKILL.md destination. Generation mode is a second axis: reference_video skips storyboard generation and uses self-contained unit bodies. It does not create a fourth workflow skill.

## Native subagents

Subagents are specialist dispatch targets, not additional SKILL.md packages. They return focused results to the main Agent, which owns sequencing and user-facing confirmation.

| Subagent | Input | Responsibility / return | Constraints |
| --- | --- | --- | --- |
| `create-episode-script` | Project/episode identity and optional original additional instructions. | Invoke generate-script for the formal script and return a summary. | Does not replace the main workflow orchestrator. |
| `generate-assets` | Explicit task/command list, project context and validation instructions. | Execute only assigned asset/storyboard/video/narration tasks and return DONE / DONE_WITH_CONCERNS / PARTIAL / BLOCKED. | The name is shared with a skill but denotes a separate generic execution subagent. |
| `normalize-drama-script` | Drama episode/source, project context and planning directions. | Generate/revise drama normalized script_plan and return statistics. | Preconfirmation editing uses native drafts; confirmed content follows the whole-redo contract. |
| `review-footage` | Script, video unit IDs, candidates/versions and review questions. | Compare contact sheets and return usable ranges, candidate ranking and editorial recommendations. | Read/Glob/Grep/inspect_video_units only; visual sampling is not full AV performance assessment. |
| `review-images` | Asset/storyboard type, IDs, versions, script and comparison questions. | Inspect definitions, prompts and references; report usable / regenerate recommendation / uncertain. | Read/Glob/Grep/inspect_images only; no generation or mutation. |
| `split-narration-segments` | Narration episode/source and planning directions. | Split a narration episode into paced script-plan segments. | Narration only; return statistics and native validation issues. |
| `split-reference-video-units` | Reference-video episode/source and unit-planning directions. | Build self-contained reference unit plan and return statistics. | Requires reference_video; respects capability-derived unit constraints. |

Sources: [agent_runtime_profile/.claude/agents/create-episode-script.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/agents/create-episode-script.md), [agent_runtime_profile/.claude/agents/generate-assets.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/agents/generate-assets.md), [agent_runtime_profile/.claude/agents/normalize-drama-script.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/agents/normalize-drama-script.md), [agent_runtime_profile/.claude/agents/review-footage.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/agents/review-footage.md), [agent_runtime_profile/.claude/agents/review-images.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/agents/review-images.md), [agent_runtime_profile/.claude/agents/split-narration-segments.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/agents/split-narration-segments.md), [agent_runtime_profile/.claude/agents/split-reference-video-units.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/agents/split-reference-video-units.md).

## Original generic remote-integration skills

| Skill package | Inputs | Purpose | Boundaries |
| --- | --- | --- | --- |
| skills/setup-arcreel-skills | ArcReel mcp_url, arc- API key and native host configuration mechanism | Persist one consistent streamable-HTTP connection, synchronize .arcreel/settings.json and validate with list_projects. | Existing matching configuration is reused. Endpoint/key validation, file tracking and native user-consent rules apply. This document configures no host. |
| skills/video-workflow | Explicit target project, native plan, original user requirements and accepted temporary choices | Drive the original remote production tools according to server workflow/admission and batch state. | Generic original remote-client package; no host-specific extension or session-control layer is added by this catalog. |

Sources: [skills/setup-arcreel-skills/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/setup-arcreel-skills/SKILL.md), [skills/video-workflow/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/video-workflow/SKILL.md).

## Installation, configuration and supporting references

| Component | What it controls | Source |
| --- | --- | --- |
| agent_runtime_profile | Original built-in production instructions, skills and subagents, separate from development configuration. | [lib/agent/agent_profile.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/agent/agent_profile.py) |
| Profile manifest/synchronization | Tracks installed baselines, preserves customizations and selects content-mode files. | [lib/agent/profile_manifest.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/agent/profile_manifest.py) |
| Project Agent-profile status/reset | Shows customized files; explicit reset restores shipped content and may discard customizations. | [server/routers/projects.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/routers/projects.py) |
| generation-modes reference | Mode/skeleton, media and prompt-language rules. The original profile specifies Chinese image/video prompts. | [agent_runtime_profile/.claude/references/generation-modes.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/references/generation-modes.md) |
| workflow-plan reference | Server plan fields, admission, next actions and boundaries. | [agent_runtime_profile/.claude/references/workflow-plan.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/references/workflow-plan.md) |
| generation-results reference | Native batch/task outcomes, partial failures and retry reporting. | [agent_runtime_profile/.claude/references/generation-results.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/references/generation-results.md) |

The original profile includes generic image 1K/video 1080p prose. Treat that as profile guidance, not a universal provider capability or an executed resolution value: native model capabilities and actual project settings still govern requests. Editing an instruction does not regenerate media.

## Invocation, review and recovery rules verified during review

| Skill / component | Verified behavior omitted from the first map |
| --- | --- |
| Workflow route | Read next_action.args.preprocessor from the server plan. Do not replace that decision with a locally guessed content-mode table; reference-video is a second route axis. |
| Internal invocation | Both manage-project and generate-script declare user-invocable:false. A user can request their supported work; that is separate from exposing an invocation command. create-episode-script explicitly preloads generate-script; other subagents do not claim that preload. |
| Successful asset/storyboard review | Main Agent dispatches review-images for successful outputs, in groups up to 20. A nested executor returns first instead of spawning a nested reviewer; summarize review and obtain the creator’s correction choice. |
| Image edits versus regeneration | Native local edits preserve the original description/image_prompt. Later full regeneration uses that original creation intent and can discard the visual correction unless authoring is separately changed. |
| Narration first fill and repeats | use_tts selection admits the initial missing-audio fill during first automatic editing. Omission reuses stale usable audio; explicit segment_ids may synthesize again. Audition the result. Existing TTS snapshots do not follow later global defaults. |
| Grids | Missing-only resumes ready unsplit/in-flight work. Explicit scene_ids requests paid redo. Whole-batch admission cannot be bypassed by running only a healthy half. Generation writes composites; splitting is a separate approved overwrite of all covered storyboard frames with history retained. |
| First editing review | Inspect every used unit and candidates. Main Agent dispatches review-footage groups of roughly 6-10 units and compares versions before editorial choices. |
| Editing round scope | Duplicate a timeline before major restructuring where instructed. Existing-version selection and native editorial repairs are separate from paid replacement/voiceover changes. Present a creator checklist and execute accepted items once per round; do not automatically perform another paid redo. |
| Output issues | Blocking issues prevent the applicable output variant. Overrun/collision warnings are reported and rendered as declared; applies_to can restrict a problem to narrated output. Do not describe every warning as a render blocker. |
| Output choice | Default requested output is a final cut; export Jianying only when asked. The native draft tool does not hand over a direct completed-download payload in every state. No timeline-deletion tool is declared. |
| Remote workflow | Every project call has explicit project. Alternatives require choice; progress-only requests do not modify. Generation-batch polling uses poll_after_seconds until terminal; wait_for_task uses its separate max_poll_attempts bound. |
| Generic setup | Endpoint must end in /mcp, key starts arc-, HTTPS except loopback HTTP. Reuse matching settings; a conflict between host/workspace values requires the user’s choice. Each repository-local credential file needs a repository .gitignore rule and must be untracked. Native remediation requires consent; an already committed key needs revocation rather than an assumption that untracking erases history. |

Sources: [agent_runtime_profile/.claude/references/workflow-plan.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/references/workflow-plan.md), [agent_runtime_profile/.claude/skills/video-workflow/SKILL.ad.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/video-workflow/SKILL.ad.md), [agent_runtime_profile/.claude/skills/generate-assets/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-assets/SKILL.md), [agent_runtime_profile/.claude/skills/generate-storyboard/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-storyboard/SKILL.md), [agent_runtime_profile/.claude/skills/generate-grid/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-grid/SKILL.md), [agent_runtime_profile/.claude/skills/generate-narration-audio/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-narration-audio/SKILL.md), [agent_runtime_profile/.claude/skills/edit-video/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/edit-video/SKILL.md), [skills/video-workflow/references/plan-safety.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/video-workflow/references/plan-safety.md), [skills/setup-arcreel-skills/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/setup-arcreel-skills/SKILL.md).

## Runtime profile inheritance and permissions

| Input / layer | Actual original implementation |
| --- | --- |
| Profile directory | ARCREEL_PROFILE_DIR can select a profile directory; otherwise the original repository agent_runtime_profile is used. |
| Content-mode projection | Matching CLAUDE.<mode>.md/SKILL.<mode>.md files become ordinary CLAUDE.md/SKILL.md. Common-plus-variant collisions or missing required variants are errors, not a silent precedence choice. |
| Synchronization | With a matching baseline, user modifications/deletions are preserved. Missing/corrupt or incompatible manifest/profile/schema/content-mode state has its native reset/rebuild semantics; do not promise unconditional preservation. |
| Runtime settings sources | Session manager sets project-only settings sources. Project CLAUDE is auto-loaded and locale/session/project/user-memory context is appended. Runtime flag settings override autoMemoryDirectory and add sandbox settings. |
| Shipped settings file | Original .claude/settings.json supplies WorktreeCreate pwd and WorktreeRemove true hooks. It is not the production tool permission allowlist. |
| Review permissions | review-images/review-footage have restrictive frontmatter and an enforcing PreToolUse policy: Read, Glob, Grep and only the corresponding inspect tool. They cannot generate or mutate. |
| Other specialists | The other five subagent definitions do not declare that same read-only tools list. They remain governed by the runtime’s allowed tools/policy; do not label all seven read-only. |

Sources: [lib/agent/agent_profile.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/agent/agent_profile.py), [lib/agent/profile_manifest.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/lib/agent/profile_manifest.py), [server/agent_runtime/session_manager.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_runtime/session_manager.py), [server/agent_runtime/options_assembler.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_runtime/options_assembler.py), [server/agent_runtime/agent_access_policy.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/server/agent_runtime/agent_access_policy.py), [agent_runtime_profile/.claude/settings.json](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/settings.json).

## Custom-endpoint helper command inputs

These commands belong to the original adapt-custom-endpoint helper, not extra MCP tools. They are documented, not executed.

| Command | Inputs | Effect / limit |
| --- | --- | --- |
| validate | definition file; optional --exclude-id | Local/native schema and duplication validation. |
| check-response | definition; --stage submit/poll/result; --response sample | Checks supplied response/extraction examples. |
| preview-request | definition; --parameters file; optional --credentials file, --start-image, --end-image, repeated --reference-images/--reference-audio-files | Builds the redacted request/material preview without submitting generation. |
| trial-run | Same applicable definition/parameter/credential/media inputs; --confirm-cost | Makes real provider requests and can incur cost; explicit agreement required. |
| trial-status | run_id | Reads the existing trial state. |
| save | definition; optional --endpoint-id plus --confirm-overwrite | Saves a new definition or explicitly accepted replacement. Duplicate default is a copy; stop on unsuccessful trials unless an unverified save is explicitly accepted. |

Connection input comes from the same-instance workspace mcp_url/api_key. Embedded mode prefers ARCREEL_API_BASE/ARCREEL_API_TOKEN; the native token lasts 15 minutes without renewal, so a 401 requires reopening the session. AUTH_ENABLED=false local operation may leave the token empty. No credential was read to document these inputs.

Sources: [agent_runtime_profile/.claude/skills/adapt-custom-endpoint/scripts/custom_endpoint.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/adapt-custom-endpoint/scripts/custom_endpoint.py); [agent_runtime_profile/.claude/skills/adapt-custom-endpoint/SKILL.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/adapt-custom-endpoint/SKILL.md).

## Complete supporting-reference inventory

| Original support file | Purpose |
| --- | --- |
| [agent_runtime_profile/CLAUDE.ad.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/CLAUDE.ad.md) | Ad/creative-short top-level production instructions. |
| [agent_runtime_profile/CLAUDE.drama.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/CLAUDE.drama.md) | Drama top-level production instructions. |
| [agent_runtime_profile/CLAUDE.narration.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/CLAUDE.narration.md) | Narration top-level production instructions. |
| [agent_runtime_profile/.claude/settings.json](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/settings.json) | Shipped runtime hook settings. |
| [agent_runtime_profile/.claude/skills/generate-video/references/veo_prompts.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/generate-video/references/veo_prompts.md) | Veo-specific prompting guidance; not a universal H3/provider contract. |
| [agent_runtime_profile/.claude/skills/adapt-custom-endpoint/references/definition-format.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/adapt-custom-endpoint/references/definition-format.md) | Native endpoint-definition structure and constraints. |
| [agent_runtime_profile/.claude/skills/adapt-custom-endpoint/scripts/custom_endpoint.py](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/agent_runtime_profile/.claude/skills/adapt-custom-endpoint/scripts/custom_endpoint.py) | Helper CLI implementations and exact flags. |
| [skills/video-workflow/references/plan-safety.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/video-workflow/references/plan-safety.md) | Blockers, confirmation, paid/destructive actions and recovery. |
| [skills/video-workflow/references/generation-modes.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/video-workflow/references/generation-modes.md) | Generic original remote workflow’s mode/reference rules. |
| [skills/video-workflow/references/generation-results.md](https://github.com/ArcReel/ArcReel/blob/7149433a21b3981da521e35b517a1fbe3356cc87/skills/video-workflow/references/generation-results.md) | Generic original remote workflow’s batch/result interpretation. |

The runtime generation-modes/workflow-plan/generation-results references are linked in the installation section above. All source skill/subagent paths were independently checked against the upstream Git tree, including the complete list of matching SKILL files; the source tree response was not truncated.

## Coverage and verification

Every runtime SKILL*.md and subagent definition in the pinned original profile is represented above; the three workflow variants count as one logical skill. Both official skills/ packages are separately identified. Source paths were checked in the upstream archive. No skill was executed, installed, reset or modified, and no generation or Agent session was started.
