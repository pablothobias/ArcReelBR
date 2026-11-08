# Ticket #3 validation

The existing authenticated `/mcp` exposes six external-only tools backed by the running AssistantService. The embedded production toolset is preserved; it cannot recursively call these session controls.

| Criterion | Evidence |
| --- | --- |
| Authenticated connection | Codex used the official Python MCP client against an isolated local application on port 1242, with an access token issued through existing authenticated management routes and kept outside the repository. All six tools were listed. No credential-management MCP tools were added. |
| Existing session operations | Send/create, state, cursor entries, pending questions, answer and interrupt are covered by authenticated HTTP integration tests. |
| Ownership, queue and idempotency | All six tools reject a session from a different project; accepted and queued retries preserve service receipts. Real duplicate initial send returned the same accepted entry. |
| Real delegation and reconnect | The actual subscription-backed embedded Agent asked the marker question. A new MCP connection recovered the pending question, answered Alpha, read entries after cursor 1, and observed the assistant's Alpha response at sequence 3. Authoritative state completed, queue/questions empty and draft null. |
| Reuse production contract | Existing production-tool parity and host consistency tests pass; session controls are external-only, with no new Agent runtime. |

[Sanitized live receipt](03-live-session.json) contains the question/answer, authoritative state, cursor and usage facts. The request prohibited media generation and project modification. This fixture is not evidence of a production-quality video or general recovery of paid media jobs.

Validation: `uv run python -m pytest tests/integration/server/test_session_mcp.py tests/integration/server/test_remote_mcp.py tests/integration/server/agent_toolset/test_host_consistency.py -q`: 928 passed, 2 warnings. Targeted Ruff, basedpyright (zero errors/warnings), test audit and whitespace checks passed.

Independent Codex reviewer `implement_text` reviewed the adapter against existing service semantics and inspected the actual local receipts, logs and usage evidence. No actionable findings. Implementation was by `implement_mcp`; live validation and integration by coordinator.

No native Codex desktop tool registration or production-instance credential configuration is claimed: the verified connection is through the available official MCP client, driven from this Codex execution. The installation guide documents the existing authenticated transport. The local access token remains private.
