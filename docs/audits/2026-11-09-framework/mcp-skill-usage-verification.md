# Verification of actual MCP and skill use

Verified on 2026-11-09 in worktree `0372/ArcReelBR`, source revision `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. Read-only UI, local configuration, source and native session-history checks. No connection setup, token creation, login, inference, generation or application changes were performed. This note narrows the preceding responsibility audit with direct evidence of use and non-use.

## Conclusion by layer

| Layer | Verified finding | Scope of conclusion |
|---|---|---|
| ArcReel remote MCP service | Both `http://127.0.0.1:1241/mcp` and `http://localhost:5173/mcp` responded HTTP 401 without credentials | The service is reachable and requires authentication. No authenticated tools/list was performed here. 401 does not mean the service is disabled. |
| This Codex chat's registered MCP tools | No ArcReel namespace/tool appeared in the available tool inventory | ArcReel is not available as a host-registered MCP service in this chat. This does not rule out historical HTTP MCP clients invoked manually. |
| Persisted Codex connection | Effective CODEX_HOME is `/Users/pablo.carminatti.br/.codex`; its config has no ArcReel MCP entry. No `.codex/config.toml`, `.mcp.json` or `.arcreel/settings.json` exists in this worktree or the main application checkout | The official persistent host/workspace connection is absent in the inspected locations. Do not generalize to every host, private file or older session. |
| Public setup/workflow skills in Codex | `setup-arcreel-skills` and `video-workflow` are absent from the inspected user skill directories (`~/.agents/skills`, `~/.codex/skills`) and workspace `.agents/skills`; no relevant entry exists in `~/.agents/.skill-lock.json`; neither is in this chat's skill catalog | The public skills are not installed/loaded through the verified Codex discovery locations. Their files in repository `skills/` are distribution sources, not proof of installation. |
| Embedded Agent skill | Production session `7409a38e-b7b2-4177-9064-bbaae6585c9a` explicitly invoked `video-workflow`, then loaded the materialized ad skill; later invoked `edit-video` | The native skill was used in that production. It is a different copy and caller position from the external public skill of the same name. |
| Embedded MCP tools | The session's main Agent issued 62 `mcp__arcreel__*` tool calls | Native MCP tools were actually used; a global claim that MCP was unused would be false. |
| Compliance with the loaded skill | Loaded instructions require refreshing the workflow plan after each action; only four plan calls appear across the entire recorded session, including subagents | There is concrete incomplete adherence to that rule. Skill invocation does not establish full compliance. |

## What the actual Settings page shows

Observed through an existing authenticated Chrome session, using a separate audit tab:

- `/app/settings?section=external-agent` displays the install command `npx skills add pablothobias/ArcReelBR --skill setup-arcreel-skills video-workflow`, setup skill name, endpoint `http://localhost:5173/mcp`, token-creation instructions and the installation-guide prompt.
- The page does not display a measured client-connection status, installed-skill inventory or usage history. Its component renders instructions and token-dialog state, without a client discovery/usage query: `frontend/src/components/pages/settings/agent-access/ExternalAgentSection.tsx:12-25,39-81`.
- Therefore the continued presence of setup steps is not evidence of non-use. Even a connected external client would still see this instructional page under the inspected implementation.
- The endpoint on port 5173 is intentional in local development: `frontend/vite.config.ts:20-26` proxies MCP and the installation guide to port 1241. Both endpoints answered the same unauthenticated 401 check. A different port alone does not prove misconfiguration.
- `/app/settings?section=arcreel-agent` displays “RafaCena Agent is not configured” and no Agent providers. SQLite read-only inspection confirmed zero `agent_anthropic_credentials` rows. This concerns the API-provider store, not whether the remote MCP endpoint exists.

The Agent warning has a customization mismatch. `frontend/src/stores/config-status-store.ts:88` derives `isEmbeddedAgentConfigured` from `anthropic_api_key.is_set`; lines 177-194 turn its absence into the warning. In contrast, `lib/config/service.py:112-117` explicitly supports the SDK CLI authenticating through the host's Claude Code subscription login when there is no API key. `scripts/run_local.sh:4-6` documents that intended route. The UI warning does not itself verify or disprove subscription authentication. No new login/status or model request was used to certify current subscription availability.

## Official setup completion versus this host

The public setup skill requires matching host MCP and workspace connection settings, plus a successful `list_projects` returning structured projects. Source: `skills/setup-arcreel-skills/SKILL.md`, Configuration steps 1-4 and Verification.

Those completion conditions are not established for this Codex host: the persisted connection/workspace files and loaded tools are absent. The installation guide remains reachable and documents both external setup and embedded-session delegation. Reading that guide or inspecting the setup skill is not executing installation or verification.

The previous restart handoff records authenticated remote MCP discovery and project reads. Retained receipts under `ArcReelData/editorial/framework-test-problema-resolvido/` also contain session-control response shapes. These are historical access records, not a new host-native connection in this chat. Their existence prevents saying the remote endpoint has never been used. This follow-up did not recover or use any bearer credential and did not repeat their authenticated requests.

## Exact native usage evidence

Source: SQLite opened with URI `file:/Users/pablo.carminatti.br/ArcReelData/arcreel.db?mode=ro`, table `agent_session_entries`, session ID above. `root seq` means `subpath=''`; all subpaths were also searched for workflow-plan calls.

| Record | Direct observation |
|---|---|
| Root seq 19, `2026-11-09T00:07:09.249Z` | `Skill` invocation with `skill=video-workflow` |
| Root seq 20 | Tool result: Launching skill: video-workflow |
| Root seq 21 | Loaded base directory is project `.claude/skills/video-workflow`; content starts with mode ad and contains “Refresh the plan after each action.” |
| Root seq 442, `2026-11-09T10:14:29.810Z` | `Skill` invocation with `skill=edit-video` |
| All main-Agent business tools | 62 calls with prefix `mcp__arcreel__` |
| Selected counts | `get_workflow_plan`: 4; `generate_episode_script`: 1; `generate_storyboards`: 2; `generate_videos`: 5; `review_speech`: 7; `render_final_cut`: 1 |

These are tool-invocation counts, not paid-attempt counts. A generate_videos call may be a preview or await an existing batch; it must not be counted as a fresh provider submission merely from its name.

The embedded server is explicitly in-process and bound to the session project (`server/agent_runtime/arcreel_mcp.py:22-35`), while the HTTP server separately publishes shared declarations and external session controls (`server/remote_mcp.py:68-74`). Native calls named `mcp__arcreel__*` prove use of the embedded tool host, not that Codex was connected to HTTP MCP through its own configuration.

## A confirmed compliance gap

All workflow-plan calls in the recorded session are root seq 36, 149, 335 and 476. No subagent plan calls were found.

For example, after seq 149 there are configuration changes at seq 247/256/287, project asset edits at 249, script edits at 267/278, asset generation at 312, a review subagent, and storyboard generation at 331. The next explicit workflow-plan call is only seq 335. This does not satisfy the loaded instruction to refresh after each action. Likewise, the next recorded plan call after 335 is 476, following further production and editing.

This is a specific operational deviation, not proof that every stage was invalid or that native backend admission was bypassed. Shared deterministic tools still apply their own validation. It also does not, by itself, establish why humor, continuity or acting failed. The preceding editorial audit separately documented native reviewers accepting known shortcomings.

## Practical interpretation

The evidence supports the user's narrower concern: the official external installation/connection path has not been completed for this Codex chat, and the native workflow was not followed consistently in at least one explicit rule. It does not support saying that the production ignored the native skill or never used MCP.

If a follow-up setup is authorized, establish one persistent host-native connection with existing authorized credentials where available, verify `list_projects`, and choose a single orchestration mode. If delegating to the embedded Agent, retain its native skill/tool ownership and observe adherence rather than recreating the workflow externally. No such setup or production action was executed in this verification.
