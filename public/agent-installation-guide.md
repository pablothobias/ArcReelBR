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
