# ArcReel external Agent connection task

Help the user connect the current Agent host to ArcReel. Complete these steps before ending; installed skills and MCP tool descriptions provide subsequent creative-workflow guidance.

## 1. Install ArcReel skills

Run in this Agent’s working directory:

```bash
npx skills add pablothobias/ArcReelBR --skill setup-arcreel-skills video-workflow
```

Verify both `setup-arcreel-skills` and `video-workflow` are installed.

## 2. Obtain connection information

Ask the user to open [Access tokens in ArcReel settings]({{BASE_URL}}/app/settings?section=access-tokens) and create an `arc-` prefixed token (API key). The full token appears only once; users may provide it to the current Agent they explicitly selected. `setup-arcreel-skills` persists the same connection through host/workspace local conventions for future sessions and skills.

MCP endpoint:

```text
{{BASE_URL}}/mcp
```

## 3. Connect

Immediately use `setup-arcreel-skills` after installation to configure the MCP endpoint, Bearer token, and connectivity. `video-workflow` triggers later for creative requests.

## 4. Completion

`list_projects` succeeds with structured `projects`, and host MCP/workspace configuration use the same connection. An empty list is successful.

## Embedded Agent delegation

The authenticated connection also exposes external-only session controls. They use the application's existing embedded Agent and its configured providers. Do not start a separate Agent runtime.

- `send_agent_message(project, content, client_key, session_id?, locale?)` creates or continues a session. Save a unique `client_key` before sending and reuse it unchanged after a transport failure. Preserve the returned session ID and authoritative `entry` or `queued_message`; queued messages have not entered the conversation yet. The locale selects technical replies, independently of the project's creative language.
- `get_agent_session(project, session_id)` reads actual runtime metadata, the queue and pending questions. `list_agent_questions` reads unresolved question cards. Submit their original IDs and answer keys with `answer_agent_question`.
- `list_agent_session_entries(project, session_id, after_seq?)` reads authoritative entries and the current draft/status. Save `next_after_seq` after processing each response and supply it on reconnect, starting at `-1`. Read state and questions again after reconnect, even when no new entries exist.
- `interrupt_agent_session` requests interruption through the existing session executor. Reconcile the resulting state and existing media jobs before another submission. Already submitted provider calls can still settle.

A result entry marks a turn ending. It does not prove session or production completion. Continue inspecting actual status, unresolved questions, queued work and project artifacts. An idle session may run again. Unsent queued messages require explicit recovery rather than automatic resubmission.

Production tools, confirmation parameters and media-batch polling keep their existing contracts. Reuse `get_generation_batch` at its suggested polling interval; an elapsed wait does not authorize another generation. A successful MCP connection establishes connectivity only. Verify actual no-media delegation, questions, reconnect and idempotent retry before claiming that embedded production works.

## Native configuration, references and speech review

Use `get_effective_configuration` to inspect resolved project models and `get_video_capabilities` for route-specific reference/audio support. `configure_project` applies explicitly supplied fields through the same validated Settings transaction as the application; changing settings does not regenerate existing media.

`upload_reference` accepts supplied base64 bytes with a filename and reference kind, not server-local paths. Character references require an existing character. Style-reference uploads invoke the configured text model and require explicit `confirm_style_analysis`; they are not read-only inspection.

Read `quote_assets`, `quote_storyboards`, or `generate_videos(preview=true)` before authorized generation. `edit_images(preview=true)` quotes an edit without submitting it. Keep unknown prices distinct from zero and conservative upper bounds distinct from expected spend. `get_project_costs` provides estimates and recorded costs; paginate `get_project_usage` until `next_cursor` is null for ledger reconciliation. Neither remaining budget nor a quote grants permission beyond the user's scope.

`review_speech` is available through the same native toolset but requires the operator to install the `speech-review` extra and provision a local faster-whisper model directory through `ARCREEL_SPEECH_REVIEW_MODEL`. Setup instructions are in `website/docs/ops/deployment.md#local-speech-review` (English translation: `website/i18n/en/docusaurus-plugin-content-docs/current/ops/deployment.md#local-speech-review`). Do not download models or change server configuration merely to inspect readiness.

Call with `project`, `unit_id`, optional `language`/`version`/`variant`, and `apply_timing=false` for inspection. Applying eligible subtitle timing requires `apply_timing=true` and mutates the native subtitle artifact. A text mismatch or uncertain boundaries leaves timing unchanged. The tool does not generate audio/video, assess acting or voice identity, or validate lip sync. Continue through native editing/rendering and report these limits explicitly.
