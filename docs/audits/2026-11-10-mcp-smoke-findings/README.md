# MCP extension smoke test: remaining findings

**Status:** implemented and verified in isolation. The operator then enabled it in the local instance, and the production Codex session recorded its own checks (see [Status](#status)). No paid call, provider connection, generation or production data was used during implementation or testing.

**Input evidence (historical, read-only):** `ArcReelProduction/outputs/mcp-extension-smoke-test.json`. Its external client saw 119 ArcReel tools, and it recorded two limitations:

1. No provider or endpoint configuration tools appeared in the catalog.
2. In the diagnostics for task `0d7e58b178414b8d80d8ad183b6e7d90`, `provider_error.code` was null and `provider_error.message` was generic. The provider's real error was only in `last_provider_response.body`.

Follows [../2026-11-10-mcp-coverage/](../2026-11-10-mcp-coverage/README.md).

## Finding 1: global configuration was not in the catalog

### Root cause: authorization (intended default deny), not missing code

The evidence for each possible cause:

| Possible cause | Result | Evidence |
|---|---|---|
| Missing implementation | No | Eight tools exist in `server/agent_toolset/global_config.py`, with handlers in `server/media_tools/global_config.py` and shared services in `server/services/configuration/`. |
| Missing registration | No | `build_remote_mcp_server` registers them through `build_global_config_tools`. That function returns `[]` when no API-key name is granted. |
| **Authorization** | **Yes** | At investigation time, `ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS` was not set in the repository `.env` (only the variable's presence was checked, not its value). The tools are hidden from, and refused to, every key not named there. |
| Stale client catalog | No | At HEAD, an ungranted remote catalog has exactly 119 tools: 106 `AGENT_TOOLSET` + 5 media transport + 8 session tools. That equals the observed count. |
| Running app differs from checkout | Not indicated | 119 matches this build without the grant. The running process was not inspected. |

The embedded Agent never receives these tools, and neither do project sessions. The policy is kept as it was: no access was widened.

What was really missing was **discoverability**. A client without the grant could not tell "not granted" from "not implemented". That is why the smoke test recorded the tools as absent.

### Changes

- `server/agent_toolset/global_config.py`: adds `GLOBAL_CONFIG_INSTRUCTIONS`, a note with no secrets. It names the 8 tools and the `ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS` setting. It says a server restart is needed after granting, and that a missing tool or an "Unknown tool" error means this key is not granted. It asks for a grant only when the user requested a configuration change, matching `public/agent-installation-guide.md`. It never names granted keys.
- `server/remote_mcp.py`: sends `REMOTE_MCP_INSTRUCTIONS` as the server `instructions` at initialize, identical for every key. Logs the number of granted key names at startup, never the names: `Remote MCP global configuration tools granted to N API key name(s)`.
- `website/docs/ops/deployment.md` (Chinese source): adds the restart requirement and the startup log line. The English page (`website/i18n/en/.../ops/deployment.md`) gets the matching env-table row and note, and `website/i18n/translation.lock.json` records the new source hash.
- `public/agent-installation-guide.md`: says the setting takes key names, not values, needs a restart, and is announced in the initialize instructions.

No handler or service changed. A capability audit found every required operation already reachable through MCP for a granted key, with no UI, REST or SQL fallback.

### Tools and authorization

All 8 tools are on the remote MCP only. They are registered only when at least one API-key name is granted. Only those `apikey:<name>` subjects can list them, and each call is checked again in two layers: the tool wrapper and the handler. Every other key receives `Unknown tool: <name>`. All request models forbid extra fields.

| Tool | Input | Effect |
|---|---|---|
| `list_global_providers` | `{}` | Built-in providers (credential status by opaque ref, catalog models) and custom providers (sanitized config, models, credential ref, revision) |
| `list_global_endpoints` | `{}` | Built-in and custom endpoints, with kind, media type and revisions |
| `get_endpoint_definition` | `endpoint_key` | Definition, plus revision and impact for custom endpoints |
| `validate_endpoint_definition` | `definition`, `exclude_endpoint_key?` | Shared validator and duplicate check. Offline. |
| `preview_endpoint_request` | `definition`, `parameters{model, prompt, duration_seconds, aspect_ratio, resolution?, generate_audio}`, `base_url?` | Renders the submit, poll and result requests with the credential masked as `****`. Offline; this is not Test connection. |
| `copy_builtin_endpoint` | `endpoint_key`, `allow_duplicate=false` | Creates an editable `ce-<id>` copy |
| `update_custom_endpoint` | `endpoint_key`, `definition`, `expected_revision`, `apply=false` | Dry run reports changed fields, duplicates and impact. A stale revision returns `revision_conflict`. |
| `configure_custom_provider` | `provider_id?`, `display_name`, `discovery_format?`, `base_url`, `credential_ref?`, `models?[…]`, `expected_revision?`, `*_max_workers?`, `apply=false` | Creates or updates a provider and its model associations. The credential is reused only through an opaque ref, and only when the host matches (otherwise `credential_host_mismatch`). |

The handlers call the same services as the Web routers: `endpoint_definitions`, `custom_providers`, `endpoint_preview`, and the market-core `validate_definition`. Cache invalidation runs through those services. Applied writes go to the `arcreel.audit.global_config` audit log with the caller identity, the operation, the target and the changed field names, never values.

## Finding 2: historical provider error hidden behind a generic summary

### Root cause: the read model ignored the persisted body

`_provider_error` in `lib/generation/generation_diagnostics.py` read only two places:
- the task-failure params, which exist only for failures recorded after `extract.error_code` support was added;
- the usage record's `error_code` and `error_message`.

It never read `last_provider_response`. The historical task failed before that support existed. Its task message is "provider reported failure (status: failed)" and its record's `error_code` is null.

Separately, the old code reported `api_calls.error_code` as `provider_error.code`. That column holds ArcReel's own failure class from `lib/billing/call_failure.py` (`rate_limited`, `timeout`, …), not a provider code. This mislabeling is now corrected.

### Changes

- New module `lib/generation/persisted_provider_error.py`. It is a pure function, `extract_persisted_provider_error(body)`: no I/O, no writes, no provider calls.
- `lib/backends/backend_runtime.py` exports `PROVIDER_ERROR_PATHS` and `PROVIDER_ERROR_MESSAGE_KEYS`, and the runtime extractor uses them. The persisted reader extends them explicitly, so the shapes are defined in one place. Runtime behaviour is unchanged.
- `lib/generation/generation_diagnostics.py`: applies precedence and provenance, and adds a recovery note.
- `server/media_tools/generation_diagnostics.py` and `UsageRepository.get_record_owner_id`: a `record_id` owned by another user is refused, like a `task_id`. On the `task_id` path, a linked record owned by another user is left out.

### Precedence and provenance

`provider_error` comes from the first source that applies:

1. **`task_failure`**: the structured task failure params. `source_path` is `$.task.error_message.params`.
2. **`last_provider_response`**: the persisted response body, used only when the task or record is `failed`. The reader looks at these locations in order:
   - `error`
   - `data.error`
   - `task.error`
   - MiniMax `base_resp`, but only with a non-zero `status_code`

   Each location may be an object with `code` or `error_code`, and `message`, `name` or `msg`, or it may be a non-empty string. Details:
   - A body cut at persistence (`{"truncated": true, "body": "<prefix>"}`) never yields a verdict. `bound_provider_response` always keeps a cut prefix of oversized JSON, which is never complete JSON, so the code stays unknown and `truncation.source_truncated` is true. A plain string body is decoded only if it is complete JSON.
   - `source_path` is relative to the read model, e.g. `$.last_provider_response.body.task.error`. `source_encoding` is `json` for a stored structure, or `json_text` when the error was decoded from a raw string body. Paths under `last_provider_response.body` resolve only when `include_provider_response=true`.
   - `source_truncated` is always false for this source, because a verdict is read only from an uncut body. The read model's `truncation.source_truncated` still reports whether persistence cut the stored body.
3. **`stored_message`**: the generic stored text. Its `code` is null and `code_known` is false. It comes from the failed usage record's `error_message`, or, when there is none, from the task's reason, but only if the task submitted a provider job (`provider_job_id`). So a task that failed inside ArcReel before any provider job (missing input, storage, promotion) has no `provider_error`, as at HEAD. A failed usage record whose stored message is ArcReel's own failure (for example a download after the provider succeeded) still appears with `source: stored_message`, unchanged from HEAD's `usage_record` source; its `internal_error_code` tells it apart.

**Contract change for external consumers.** The `source` value `usage_record` no longer exists; that path is now `stored_message`. On it, `code` used to carry `api_calls.error_code`, ArcReel's internal failure class. That class now appears only as `internal_error_code` and `usage_record.error_code`. The new fields are `code_known`, `source_path`, `source_truncated`, `source_encoding`, `conflicts` and `stored_message`. No consumer inside the repository reads `provider_error`. Prompts or notes outside it that test `source == "usage_record"` or read `code` on that path must be updated. The tool description states the precedence.

Rules that apply to every source:

- **Codes are never invented.** Integer and string codes are stringified. Success codes (`0`) do not count as a verdict. A code longer than 128 characters, or of any other type, is treated as unknown.
- **The generic text is kept.** When a more specific source wins, `stored_message` still holds the generic text.
- **Disagreements are reported, not resolved.** `conflicts` lists each lower-precedence source whose code or message differs. It never overrides the chosen value.
- **Internal codes stay in their own fields.** `problem.code` and `usage_record.error_code` are unchanged. The internal class is also echoed as `provider_error.internal_error_code`, and it never becomes `provider_error.code`.
- **Everything is sanitized and bounded.** The whole `provider_error` passes through `sanitize_for_agent`, including `conflicts` and `stored_message`. Credentials, auth headers, cookies, signed URL queries and media payloads are removed, and every truncation path is listed.
- **The observation time is not inferred.** `observed_at` stays unknown.
- **Recovery is never automatic.** The recovery action is not changed. When it is `retry` and the body supplied a known code, `recovery.provider_verdict_note` says the provider's verdict is more specific than the stored reason, to inspect `provider_error` and `internal_error_code` before any resubmission, and that a resubmission is a new paid generation that needs the user's spending authorization.
- **Stored records are untouched.** There is no backfill or migration. The usage and financial listing is unchanged, so pending tasks are still excluded there.

Result for the historical-style fixture:
- `code: "2013"`, `code_known: true`
- message: the `.x-wav` audio-format rejection
- `source: last_provider_response`, `source_path: $.last_provider_response.body.task.error`
- `stored_message`: the generic text
- `problem.code`: `generation_task_failed`

The endpoint definition is not resolved for historical rows, because `api_calls` does not record which definition revision produced them. So `2013` is not reclassified to `fix_input`.

## Verification

All commands were run from the repository root with `env -u ARCREEL_DATA_DIR PYTHON_DOTENV_DISABLED=1`, on disposable databases and data roots, fake credentials and simulated providers. Outbound HTTP was patched to fail.

**Final results on the committed tree:**

| Check | Result |
|---|---|
| `uv run pytest tests/integration/server/test_global_config_mcp.py tests/integration/server/test_mcp_only_journey.py tests/integration/server/test_generation_diagnostics_tool.py tests/integration/server/test_remote_mcp.py tests/integration/server/agent_toolset tests/unit/lib/generation/test_generation_diagnostics.py tests/unit/lib/backends/test_backend_runtime.py tests/unit/lib/db/repositories tests/unit/server/routers/test_custom_endpoints_api.py tests/unit/server/routers/test_custom_providers_api.py tests/unit/server/routers/test_custom_providers_comfyui.py tests/unit/lib/custom_provider tests/unit/test_public_contract.py tests/integration/server/routers/test_usage_router.py tests/integration/server/routers/test_usage_router_summary.py tests/integration/server/routers/test_usage_router_agent_sessions.py tests/integration/server/agent_runtime/test_session_manager_usage_billing.py -q` | 3998 passed, 0 failed |
| `uv run ruff check` and `uv run ruff format --check` on the 17 changed Python files | clean |
| `uv run basedpyright --warnings` on the changed source files | 0 errors, 0 warnings |
| Independent MCP client journey (outside the repository) against the official `build_remote_mcp_server`, using a real `mcp` `ClientSession` over streamable HTTP | 2 passed: a granted key sees 127 tools, an ungranted key 119; the historical fixture returns `2013` from `last_provider_response`; no outbound HTTP; no new rows |

**Red-green checks** (each change reverted temporarily, then restored):
- **Diagnostics:** with `lib/generation/generation_diagnostics.py` reverted to HEAD, the 3 historical tests (unit, tool and MCP journey) fail with the original symptom, `assert None == '2013'`.
- **Provider-involvement guard:** with the `provider_job_id` condition removed, both new cases fail.
- **Configuration:** with `server/remote_mcp.py` and `server/agent_toolset/global_config.py` reverted, the new tests fail at import (`REMOTE_MCP_INSTRUCTIONS`). That shows the tests depend on the change, but it does not show each assertion failing on its own.
- **Updated stale tests:** renaming the `novel_text_coverage` code makes all 5 coverage tests fail. Removing the lowercasing of language codes makes the `ZH → zh` test fail.

**Stale test expectations fixed in the same change.** Twenty tests outside this feature were failing at HEAD on expectations that earlier deliberate commits had changed:
- `f997d91b8` translated Agent-facing receipts and default messages to English (ADR 0122).
- `7b012052e` made language codes case-insensitive, so `ZH` is stored as `zh`.

They were updated as follows:
- **Narration checks** (`test_split_narration_segments.py`, 10 tests): they now assert the stable violation codes (`[novel_text_coverage]`, `[duration_off_tier]`, `[duplicate_segment_id]`, `[blank_novel_text]`, `[unregistered_asset]`) instead of prose. The structure-validation case asserts the English text.
- **ComfyUI** (`test_custom_providers_comfyui.py`, 4 tests): they assert `node bindings`.
- **Usage router** (`test_usage_router.py`, `test_usage_router_summary.py`, 5 tests): the default-locale cases assert the English catalog strings. The request-locale test now asks for `zh`, so the Chinese catalog stays covered.
- **`ZH`** (`test_patch_tools.py`, 1 test): moved from the rejected list to a new normalization test (`ZH` → `zh`, ` en ` → `en`, `pt_br` → `pt-BR`).

### Required tests and where they are covered

**Configuration**

| # | Requirement | Covered by |
|---|---|---|
| 1 | An authorized client lists and calls the tools | `test_official_remote_server_grants_global_config_only_to_named_keys`, `test_reproduces_ce1_custom1_configuration_through_mcp_tools`, journey `test_catalog_has_no_escape_hatches_and_scope_is_enforced` |
| 2 | An unauthorized client gets "Unknown tool" | the same official-server test, `test_unauthorized_key_neither_lists_nor_calls_global_config_tools` |
| 3 | Embedded and remote exposure follow their policies | `test_global_config_tools_are_not_registered_without_granted_keys`: ungranted remote = shared + media + session tools, and `AGENT_TOOLSET` contains none of the 8 |
| 4 | No secret in any readback or log | the official-server test and the ce1 test |
| 5 | The opaque credential is checked on the server | the ce1 test, `test_credentials_without_a_single_api_key_or_known_origin_are_not_reusable` |
| 6 | A different host is refused | the ce1 test, `test_credential_reuse_refuses_*` |
| 7 | Invalid definitions, stale revisions and other-host requests write nothing | the official-server test, using full row snapshots |
| 8 | Validate and preview make no outbound HTTP and add no rows | the official-server test |
| 9 | Native REST configuration behaviour is unchanged | `test_custom_endpoints_api.py`, `test_custom_providers_api.py` |

**Diagnostics**

| # | Requirement | Covered by |
|---|---|---|
| 1–3 | The historical fixture returns `2013` and the real message; rows are unchanged; no provider call, task or retry | unit tests, `test_generation_diagnostics_tool.py`, and journey `test_historical_generic_failure_diagnostics_read_the_persisted_provider_verdict` (real MCP client) |
| 4–6 | Internal codes stay separate; unknown values stay unknown; malformed, truncated and secret-bearing bodies are handled safely | unit tests |
| 7 | Cross-project and cross-user `task_id` and `record_id` are refused | `test_generation_diagnostics_tool.py` |
| 8 | Current structured errors still work | unit test for structured task failure precedence |

### Independent review

**Architecture and security (C).** No blocker or major findings. Of its seven minor or nit findings, five were fixed:
- `source_encoding` for decoded text;
- an error object carrying a success code was being read as a verdict;
- the error-path definition was duplicated (CODING_STANDARDS general.md, "Define a value's format or range once");
- provider codes now have a length cap;
- the owner of the linked record is now checked on the `task_id` path.

Fixed afterwards: the English deployment page now carries the row and the note (`pnpm check` and `translation-lock.mjs status` pass). Not fixed: one test still asserts exact log text, which the operator docs quote.

The reviewer also tried an origin bypass that rebinds an endpoint to a foreign poll URL. It was refused, and nothing was written.

**Final code review (fresh reviewer, no session context).** Verdict: ready with fixes; no critical findings.
- **Fixed, important:**
  - The generic-reason fallback reported failures from inside ArcReel as `provider_error`. It now requires `provider_job_id`.
  - The `source` rename was undocumented. It is now documented in the report and the tool description.
- **Fixed, minor:**
  - The initialize instructions now ask for a grant only when the user requested a configuration change, matching `public/agent-installation-guide.md`. The guide now mentions the restart.
  - A success code in one field no longer hides a failure code in the other.
  - The verdict note now requires a known code.
- **Not changed:**
  - The record lookup runs two queries, a low-impact cost.
  - The tests guard against outbound HTTP by patching httpx instead of using respx. They only assert that no call was made.
  - Some tests assert exact log text, which the operator docs quote verbatim.
  - The official-server test is one large case.

**Pre-commit review (fresh reviewer, no session context).** Verdict: ready with fixes; no critical or important findings.
- **Fixed:**
  - The verdict note's wording implied fixing inputs even for transient or auth failures. It is now neutral and points at `internal_error_code`.
  - The tool description now says that `source_path` under the body resolves only with `include_provider_response=true`.
  - The unreachable decode inside the truncation wrapper was removed. Wrapped bodies are always cut prefixes, so they now yield no verdict, and a test uses the real `bound_provider_response` output.
  - The one-line `_source_truncated` wrapper was inlined.
  - The report's "as at HEAD" sentence is now scoped to the task-reason path.
- **Kept:**
  - The exact startup log assertion, because `deployment.md` quotes that line to operators.

**MCP protocol (D).** D wrote its own journey and passed every check:
- A granted key sees 127 tools and an ungranted key sees 119. The difference is exactly the 8 configuration tools.
- Copy, dry run, apply and stale-revision conflict all behaved as specified.
- A credential was reused by ref, and a different host was refused.
- The secret never appeared in any result.
- `2013` was extracted with provenance through both `task_id` and `record_id`.
- Other-project and other-user reads were refused.
- No outbound HTTP was made, and no rows changed.

## Status

| Stage | Configuration | Diagnostics |
|---|---|---|
| Implemented | Yes. The tools already existed; discoverability, the activation log and tests were added. | Yes |
| Tested in isolation | Yes | Yes |
| Discoverable through the isolated MCP client | Yes, for a granted key | Yes |
| Activated in the local instance | The operator set the grant to one key name and restarted `arcreel`. The startup log reports `granted to 1 API key name(s)`. | Active after a restart; no setting needed |
| Checked in the production Codex session (recorded by that session in `ArcReelProduction/docs/mcp-validation-status.md`, not re-verified here) | 127 tools listed. Provider and endpoint listings, reading `ce-1` and `minimax-h3`, validation and a synthetic preview worked, and no credential value was returned. Copy and update were not executed there. | `get_generation_diagnostics` by task and by record `114` returned `code: "2013"` with the `.x-wav` message from `last_provider_response` |

That session ran before the pre-commit review fixes (the recovery-note wording, the truncation-wrapper removal and the tool-description note). Restart `arcreel` on the committed build to load them.

## Activation (operator; not executed)

The project runs locally through the `arcreel` shell alias, which calls `scripts/run_local.sh`. That script starts the servers with an empty environment (`env -i`), and the backend reads its settings from the repository-root `.env` (`lib/infra/env_init.py`). A shell `export` therefore never reaches the server.

1. Check out this build in `ArcReelBR`.
2. Optional, to grant global configuration: add the line `ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS=<api-key name>` to `ArcReelBR/.env`. Use the key's name as shown under access tokens, never its value, and list only keys trusted to change provider configuration.
3. Restart: stop the running `arcreel` (Ctrl+C in its terminal) and run `arcreel` again.
4. Check the startup log for `Remote MCP global configuration tools granted to 1 API key name(s)`.
5. Start a **new** MCP client session with that key. Expect 127 tools, including `list_global_providers`. A key that is not listed still sees 119 tools, and the initialize instructions explain how to get the grant.
6. Diagnostics need no configuration. After the restart, `get_generation_diagnostics` for the historical task should report code `2013` from `last_provider_response`. Reading it does not change the record.

Do not run Test connection to verify. It can create billable jobs.

## Rollback (not executed)

- Remove the `ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS` line from `.env` and restart `arcreel`. The 8 tools disappear, and the other 119 tools are unaffected.
- Or check out the previous commit and restart `arcreel`. No schema, data or record depends on these changes; diagnostics are computed when read.

## Open decisions and limitations

- **The grant is a policy, not a security boundary.** Any `arc-` key already has administrative REST access. Narrowing that would need a separate authorization design.
- **Historical `2013` stays `retry`.** A historical row cannot be bound to the definition revision that produced it, so `2013` is not reclassified to `fix_input`. The verdict note and the spending-authorization guidance cover this.
- **Only the listed body shapes are read.** A body cut at persistence that is no longer valid JSON yields no code.
- **Image calls persist no provider response** through the media generator, so diagnostics for them depend on the task failure params.
- **The audit trail is log-only,** with no database table.
