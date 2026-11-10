# MCP coverage of the official ArcReel workflows: implementation evidence

- **Date:** 2026-11-10
- **Base:** `f0d99b56a` (uncommitted working tree)
- **Spec workspace (read-only):** `ArcReelProduction/docs/mcp-workflow-completion-plan.md`, `mcp-workflow-coverage-matrix.md`, `mcp-coverage-gaps.json`, and workflow maps 01–08
- **Related documents:** [decisions.md](decisions.md) (MCP-022, MCP-023, storyboard voice, MCP-007) and [activation-and-rollback.md](activation-and-rollback.md)

**Scope of the claims.** All evidence comes from automated tests that use disposable directories and databases, simulated providers and fake credentials. Nothing here is verified production execution or audiovisual quality. No paid call, provider connection test, TTS or image/video generation was made. Production projects, configuration and data were not touched.

## Path every capability follows

External agent → official MCP (`server/remote_mcp.py`, or the embedded host `server/agent_toolset/embedded.py`) → declaration (`server/agent_toolset/*`) → handler (`server/media_tools/*`) → shared native service (`server/services/*`, also called by the Web router) → native queue, repositories and adapters.

- Router logic that MCP needed was extracted into services, and each refactored Web route keeps its status codes, i18n keys and response shapes.
- No REST-over-HTTP, generic SQL, shell, HTTP or filesystem tool was added.

## 1. Status matrix: MCP-ID → implementation → tests → status

| ID | Capability | Implementation (tools / services) | Main tests | Status |
|---|---|---|---|---|
| MCP-001 | Start a blank script | `start_blank_script` → `lib/script/blank_script.start_blank_script_detailed` (same transaction as Web) | `test_authoring_previews.py`, journey | Done |
| MCP-002 | Prompt preview for reference-video units | `get_prompt_preview` covers reference units; optional `task_id` returns the captured submitted prompt (`server/services/admission/{prompt_preview,reference_prompt_preview,captured_submission}.py`) | `test_authoring_previews.py` | Done |
| MCP-003 | Character reference audio through TTS | `list_tts_voices`, `generate_voice_sample` (native `voice_sample` queue task; `preview` quotes without enqueueing), `confirm_voice_sample` (requires `expected_reference_sha256` or `expect_unbound`) → `server/services/voice_references.py` | `test_voice_references.py` (37), journey | Done |
| MCP-004 | Inspect and recover voice samples | `list_voice_samples`, `inspect_voice_reference` (digest, duration, format; working files materialized for object storage); recovered by project and task, with no second generation | same | Done |
| MCP-005 | Resolution validation before submission | `configure_project` and Web create/PATCH refuse values the endpoint cannot render (`model_setting_value_unsupported`, with allowed values and a suggestion; unchanged stored entries exempt) → `server/services/project/model_settings_validation.py`; quote, preview, admission and facts share one representation | `test_configure_project_resolution.py`, `test_video_request_resolution_enum.py`, `test_projects_model_settings_validation.py` | Done |
| MCP-006 | Provider failure diagnostics | `get_generation_diagnostics` (task/record scoped, redacted, truncation marked); provider codes classified as `provider_job_rejected` (fix input), `provider_job_configuration_rejected` (configure) or `provider_job_failed_coded` (retry only with authorization); the Web toast shows `code: message` | `test_generation_diagnostics*.py`, `test_minimax_h3_contract.py`, journey | Done |
| MCP-007 | Chinese reference markers | Evidence only. Markers are preserved; captured-submission preview exposes the exact prompt | n/a | Documented ([decisions.md](decisions.md)) |
| MCP-008 | H3 reference audio MIME | Opt-in `container_mime` sniffs WAV/MP3 bytes, sends `audio/wav` / `audio/mp3`, never relabels or transcodes; schema, validator, renderer and preview | `test_minimax_h3_contract.py`, market-core tests | Done (definition copies made earlier keep their old definitions) |
| MCP-009 | Provider and endpoint configuration | Remote-only, gated (`ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS`) tools: `list_global_providers`, `list_global_endpoints`, `get_endpoint_definition`, `validate_endpoint_definition`, `preview_endpoint_request`, `copy_builtin_endpoint`, `update_custom_endpoint`, `configure_custom_provider` → `server/services/configuration/*`; dry-run by default and revision-checked; credential reuse by reference, origin-bound; no connection tests | `test_global_config_mcp.py` (28) | Done |
| MCP-010 | Retrieve media over MCP | Remote-only `describe_media` / `read_media_chunk` plus resource template `arcreel://media/{project}/{media_id}/{index}` (HMAC media ids, per-chunk sha256, octet-stream blobs, canonical-location allowlist per kind) → `server/services/media_transport/*` | `test_remote_media_transport.py`, `test_media_transport_resolution.py`, `test_reference_media_selectors.py` | Done |
| MCP-011 | Product reference photos | `upload_product_reference_images`, `list_product_reference_images`, `arrange_product_reference_images` (`confirm_detach` required to drop photos) | `test_media_ingest.py` | Done |
| MCP-012 | Install approved finished media | `install_finished_media` (asset sheet, derivative, storyboard image/video, reference unit video) through `server/services/currency/manual_media_install.py`; version comes from the install transaction | `test_media_ingest.py` | Done |
| MCP-013 | End frames | `set_end_frame` / `clear_end_frame` (stricter than the Web: refuses models without last-frame support) | `test_media_ingest.py` | Done |
| MCP-014 | Grid composites | `list_grids`, `inspect_grid` (composite attached as an image), `replace_grid_composite` (inline or staged, version-checked); `split_grids` gains an optional `reviewed_composites` guard | `test_grid_review.py`, `test_grid.py` | Done |
| MCP-015 | Media version selection | `list_media_versions` / `select_media_version` (image, grid, narration and other versioned kinds; version checked under the lock) | `test_media_versions.py` | Done |
| MCP-016 | Project BGM | `upload_bgm` (native validation; one error map shared with the Web) | `test_media_ingest.py` | Done |
| MCP-017 | Episode management and replanning | `get_episode_layout`, `create_episode`, `move_episode`, `delete_episode`, `edit_episode_boundaries`, `move_source_file`, `get_episode_replan`, `start/continue/adopt/discard_episode_replan` → `server/services/project/episode_operations.py` | `test_episode_management_tools.py`, `test_episode_replan_embedded.py` | Done |
| MCP-018 | Global character/scene/prop library | `list_global_library_assets`, `get_global_library_asset`, `save_asset_to_global_library` (overwriting another project's entry needs the owner and timestamp the refusal showed), `apply_global_library_assets` → `server/services/asset_library/global_library.py`; products stay excluded | `test_global_asset_library_tools.py` | Done |
| MCP-019 | Asset/derivative prompt preview | `get_asset_prompt_preview` (draft description supported, never saved) | `test_authoring_previews.py` | Done |
| MCP-020 | Automatic overview | `generate_project_overview` (strict boolean `confirm_text_model_call`; a text-model call, never implicit) | `test_authoring_previews.py` | Done |
| MCP-021 | Copy timeline revision | Already covered by `create_timeline(from="timeline")`; no duplicate tool | `test_edit_timelines*.py` | Covered (no change) |
| MCP-022 | Product `brand` writes | Deliberately restricted | — | Decision pending ([decisions.md](decisions.md)) |
| MCP-023 | Toggle `grid_storyboard` | Deliberately restricted | — | Decision pending ([decisions.md](decisions.md)) |
| Journey gap | Resume a failed artifact download | `retry_artifact_download` → `server/services/tasks/artifact_download_retry.py` (shared with `POST /tasks/{id}/retry-download`); resumes retrieval only | `test_retry_artifact_download_tool.py`, journey | Done |
| Journey gap | Staged reference images and their read-back | `upload_reference` accepts `staged_upload_id` and returns sha256; `describe_media` kinds `character_reference_image` and `style_image` | `test_reference_media_selectors.py`, journey | Done |

**Supporting transport.**
- Chunked uploads use `begin_media_upload` / `append_media_upload_chunk`, scoped by project and API-key client.
- Limits per upload: a purpose-specific size cap, at most 4 active uploads per client, a byte quota per project, a 2-hour TTL, and the declared purpose is enforced when the upload is consumed.
- `prepare_jianying_package` produces the Jianying draft zip. The draft version is re-checked after packaging.

## 2. Tools and contracts

- The shared catalog `AGENT_TOOLSET` grew from 69 to **106** tools, all served identically by the embedded and remote hosts (host-consistency test).
- The remote host alone adds **5** media-transport tools plus the media resource template.
- The **8** global configuration tools appear only for granted API keys.
- **Migration policy.** Every new write is `BLOCKED` on a project whose migration failed. Reads are `READ_CHECK`. `get_generation_diagnostics`, `describe_media` and `read_media_chunk` are `Exempt` with a stated reason.
- **Results.** Every result is a structured envelope (`{domain_key: value}` or `{problem: {code, detail, action, params}}`). Problem codes are stable and localized where the Web shares them.
- **Previews, quotes, reads and imports never enqueue tasks.** Tests assert zero tasks after each.

## 3. MCP-only end-to-end results

`tests/integration/server/test_mcp_only_journey.py` (16 tests) runs a real `mcp.ClientSession` over streamable HTTP against an isolated `build_remote_mcp_server`. It uses API-key bearer auth, a temporary projects root, a test DB, and the real planner, queue, ledger, version manager and executor. Providers are faked only at the backend seams.

- **Bootstrap.** Create project → episode → blank script → assets → script entry → workflow plan.
- **References.** Staged chunked uploads, product photos, sheet install, and byte-for-byte read-back via chunks and the resource template, in the original order.
- **Voices.** A character voice sample is distinct from the narrator voice. A blind confirm is refused, `expect_unbound` binds, and a repeat returns `already_bound`.
- **Previews and quotes.** Zero tasks and zero provider calls.
- **Reconnect.** Submit, restart the host, resubmit in a new session: the request dedupes to the same task (one provider call). The batch completes and the deliverable downloads with a matching sha256. A missing-only resend after completion creates no second paid task.
- **Failure recovery.**
  - A provider rejection carrying a secret and a signed URL produces sanitized diagnostics, a `retry` action that requires authorization, and no automatic retry.
  - A failed artifact download resumes through `retry_artifact_download` without a new task or charge. Foreign and missing tasks get the same `task_not_found`.
- **Escape checks.**
  - No SQL, shell, HTTP or filesystem tools are listed.
  - Global configuration tools are absent unless granted, and are hidden and refused for other keys.
  - Traversal, absolute paths and a foreign project's `media_id` are refused.
  - No result contains the server's root path, API keys, provider secrets or signed URL query strings.
- **All 8 workflow variants.** Derived from the live `create_project` schema: drama, narration and ad content modes × storyboard and reference-video, plus grid on the two non-ad storyboard routes. Every action the plans emit maps to a live MCP tool.

## 4. Guarantees and limitations

**Guaranteed by tests:**
- Every production write uses the native transaction and lock that the Web path uses.
- Stale-version and concurrent-change checks refuse instead of overwriting.
- No paid generation is retried automatically.
- Credentials are never returned. Reuse is bound to the credential's origin at configuration time (structural check plus hostile render) and at send time (`lib/custom_provider/credential_origin.py`).
- Redirects drop credentials when the origin changes.
- Exception text and SQL parameters never reach clients (`hide_parameters=True`; generic `internal_error`).
- Audio bytes are never transcoded or relabeled.

**Limitations:**
- The global-configuration grant is a tool-surface policy, not a security boundary, because any `arc-` key already has REST administration.
- The `expected_revision` check on endpoint and provider updates is not compare-and-swap. This is documented in code.
- Reference-audio container sniffing runs at execution (before any provider request), not at admission. The speaker-to-file binding exists only at execution.
- The installed-file sha256 returned by some installs is advisory under a concurrent replacement.
- Not verified:
  - Real Claude CLI and Codex handling of blob resources and resource templates. Only the Python MCP SDK client was tested.
  - Real `GenerationWorker` lease and heartbeat behaviour, video generation end to end, provider checkpoints, and audiovisual quality.
- The MiniMax error-code classification was checked against the official reference (<https://platform.minimax.io/docs/api-reference/errorcode>) on 2026-11-10:
  - Fix input: 2013 invalid parameters, 1026 input flagged, 1027 output flagged.
  - Configure provider: 1004 not authorized, 1008 insufficient balance.
  - Unclassified, so retried only with authorization: 1000 unknown and 1002 rate limit.
  - Only 2013 is also backed by replayed real failures.
- The MiniMax-H3-Highspeed catalog entry narrows resolution to 768p, while the official page also lists 480P. This is a catalog note and was not changed.

## 5. Outstanding decisions

MCP-022 (product `brand`) and MCP-023 (`grid_storyboard` toggle) remain restricted. Their options and recommended defaults are in [decisions.md](decisions.md). That document also records the storyboard-route character-voice limitation of the H3 contract.

## 6. Documentation changes

- **This audit folder:** this report, `decisions.md`, `activation-and-rollback.md`.
- **Built-in Agent references:**
  - `agent_runtime_profile/.claude/references/workflow-plan.md`: rows for `start_blank_script`, `collect_project_input`, `create_episode` and `retry_artifact_download` now name the MCP tools, while keeping the user-choice and no-resubmission rules.
  - `agent_runtime_profile/.claude/skills/adapt-custom-endpoint/references/definition-format.md`: `container_mime`, `error_code`, and the code sets.
- **Provider docs:** `docs/api-docs/endpoints/minimax-h3.md` (error-code sets and sources).
- **Operator and external-agent docs:**
  - `website/docs/ops/deployment.md` (Chinese source): `ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS` row and the "tool surface, not a security boundary" note. The English translation follows the translation workflow.
  - `public/agent-installation-guide.md`: remote media transport and the opt-in global configuration tools.
- Historical audit receipts and hashes were not modified.

**Suggested upstream documentation changes (not applied here, because public docs follow their own translation workflow):**
- The workflows guide could mention that every stage is also reachable by an external agent through the remote MCP.
- The Jianying guide could mention `prepare_jianying_package`, plus `describe_media` / `read_media_chunk`, for MCP clients.

## 7. Activation and rollback

See [activation-and-rollback.md](activation-and-rollback.md). Nothing was applied to a running instance.

## 8. Check results

All runs used `PYTHONPYCACHEPREFIX` pointing at a clean bytecode cache. Stale `tests/**/__pycache__` compiled at the repository's former path breaks the blocking-call guard.

**Full backend suite** (`pytest tests -n 4 --dist loadfile`):

| Tree | Passed | Failed |
|---|---|---|
| Working tree | 19,779 | 175 |
| Clean HEAD | 18,976 | 174 |

- The failure sets match, with two exceptions:
  - 10 tests that fail at HEAD now pass.
  - 1 timing-sensitive cost-estimation test failed only under parallel load; it passes in isolation.
- The pre-existing failures are mostly Chinese-text assertions after the English-default change (ADR 0122).

**Other checks:**
- Frontend: `tsc --noEmit` clean; `vitest` 307 files, 4,071 tests passed.
- market-core package tests: 747 passed.
- `ruff check`: clean except two pre-existing audit-receipt scripts under `docs/audits/2026-11-09-framework/`, left untouched. `ruff format --check`: the same two receipt scripts, unchanged.
- `lint-imports`: 8 kept, 1 broken. The broken contract is the pre-existing `lib.config.resolver -> lib.project.project_manager -> … image_backends.base` chain, identical at HEAD.
- Security probes: 51 passed, 2 documented non-regressions:
  - A direct call to the template renderer (send-time guard verified separately).
  - A host-level directory symlink of `characters/refs_audio`, which needs filesystem tampering and is still refused by media transport.

**No costs incurred and no production changes:** no provider, network or paid calls; no real data directory, database, credentials or production project touched; no commit, push, merge or deploy.

## Team, reviews and resolution

| Role | Scope | Outcome |
|---|---|---|
| Coordinator | Contract, registration (toolset, i18n, summaries, host-consistency), remote wiring, integration, docs | Done |
| Worker A | MCP-005/006/008, credential origin guard, error-code classification | Done after 3 review rounds |
| Worker B | MCP-001/002/007/019/020 | Done |
| Worker C | MCP-003/004 | Done after security fixes S1, S3, S6 |
| Worker D1 | MCP-010, Jianying, MCP-021 | Done after S1–S3 and architecture items |
| Worker D2 | MCP-011/012/013/016 | Done after S4 and architecture items |
| Worker E | MCP-009 | Done after blocking B1 (credential host bypass, 2 rounds) and B2 (exception leakage) |
| Worker F | MCP-017/018 | Done after the embedded replan fix and owner-bound overwrite consent |
| Worker G | MCP-014/015 | Done after in-lock version checks |
| Worker H | MCP-only end-to-end journey | Found 2 gaps (artifact-download resume, reference read-back) |
| Worker I | Both journey gaps | Done |
| Architecture supervisor | Rounds on shared contract, B/C/F/G, D1/D2/E, A | All findings resolved or documented |
| Security supervisor | Rounds on B/C/F/G, D1/D2/E, re-verification, final gate | Final gate: no blocking findings; one should-fix (stale `model_settings` entries blocking Web saves) fixed by the coordinator |

**Final code review** (`requesting-code-review`, verdict "With fixes"):

| # | Finding | Resolution |
|---|---|---|
| 1 | Web voice-sample conflict surfaced a video-specific message | Fixed: the route maps `ActiveTaskRequestConflict` to `voice_sample_in_progress` (4 locales). Regression test red-green verified. |
| 2 | Origin/authority logic duplicated across validator, configuration and send-time guard | Fixed: one authority rule (`arcreel_market_core.endpoint_definition.url_authority`) and one origin parser (`credential_origin.strict_origin`, urlsplit and httpx must agree) used by the validator, global configuration, the send-time guard and ComfyUI. A shared table test (`tests/unit/lib/custom_provider/test_credential_host_rule.py`) runs every hostile row through each caller. |
| 3 | Definition schema version not bumped for `container_mime` / `error_code` | Fixed: schema `1.3.0` (`$id`, `CURRENT_SCHEMA_VERSION`, factories, frontend draft and example templates, `definition-format.md`). Built-in definitions keep their declared versions, as in e6709b9ff; 1.2.0 definitions without the new fields still validate. |
| 4 | Env var and external-agent surface missing from operator docs | Fixed: see section 6. |
| 5 | English `detail` inside the translated `task_fail_credential_host_mismatch` | Fixed: `CredentialHostMismatchError` carries a `section` parameter, and the four locales translate it; `str(exc)` stays English for logs only. |
| 6 | Captured-submission reads checked project but not user | Fixed: `captured_video_submission` requires the caller's `user_id`; another user's task answers `task_not_found`. Test red-green verified. |
| 7 | PATCH reads stored `model_settings` outside the update transaction | Accepted: a concurrent edit can only make the "unchanged stale entry" exemption stale; execution-time request facts still refuse the value before any task exists. |
| 8 | Endpoint editor form does not model `container_mime` / `extract.error_code` | Accepted: unknown fields are preserved on write and editable in the JSON view. Follow-up for the form. |
| 9 | `expected_revision` is check-then-write, not compare-and-swap | Accepted and documented: single-process server; a conditional `UPDATE` on `updated_at` is the follow-up. |

The reviewer's untraced MCP `generate_voice_sample` race was checked: the handler re-reads the active task after a refused attach and returns `voice_sample_in_progress` (covered by `test_concurrent_mismatched_request_is_refused_not_attached`).

Re-verification after the fixes (coordinator, fresh runs): 3,153 backend tests across the touched areas passed; market-core 747 passed; frontend 307 files / 4,071 tests passed and `tsc` clean; `ruff check` and `ruff format --check` clean on all changed and new Python files; `lint-imports` unchanged (8 kept, 1 pre-existing broken). The market router tests show 32 failures, identical to clean HEAD (Chinese-text assertions).

**Residual notes** (accepted, documented):
- Process-local upload locks (single-process server).
- Any file under `versions/` is accepted for versioned kinds when `project.json` is hand-edited.
- A new `batch_id` is created per resubmission even when the task dedupes.
- Usage records keep their closed failure-code set, so provider verdicts live on the task.

**Lesson candidate:** stale bytecode from a moved checkout made several "pre-existing failures" look real. Running with `PYTHONPYCACHEPREFIX`, or clearing `tests/**/__pycache__`, avoided it. See `docs/agents/lessons.md`.
