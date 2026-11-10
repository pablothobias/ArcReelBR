# MCP coverage: activation and rollback

**Status:** prepared only. Nothing here has been applied to a running ArcReel instance, its data directory, its database or its provider configuration. All verification used disposable directories, test databases, simulated providers and fake credentials.

## What changes on deploy

| Area | Effect when the new build starts | Operator action needed |
|---|---|---|
| New project-scoped MCP tools (authoring previews, voice references, media ingest, versions, grids, episodes, global library, diagnostics) | Listed for both the embedded Agent and the remote MCP | None. Every write uses the same native services and locks as the Web. |
| Remote-only media transport (`describe_media`, `read_media_chunk`, `begin_media_upload`, `append_media_upload_chunk`, `prepare_jianying_package`, plus the `arcreel://media/{project}/{media_id}/{index}` resource template) | Listed on the remote MCP only | None. Staged uploads live under `<project>/.arcreel/mcp_uploads/` with a 2-hour TTL and per-client quotas. Jianying packages go under `<project>/.arcreel/mcp_packages/`. Project export already skips dot directories. |
| Global configuration tools (8 remote-only tools) | **Not registered** until an operator grants them | Optional. See the next section. |
| MiniMax H3 built-in endpoint (`minimax-h3.json`) | Reference audio data URIs use `audio/wav` / `audio/mp3` from the sniffed container, and failures carry the provider's own error code | None for the built-in endpoint. User copies made earlier (`ce-N`) keep their old definitions: see below. |
| Voice-sample queue dedupe | A second sample request for the same character with **different** text or voice while one is active now returns 409 (`ActiveTaskRequestConflict`) instead of silently reusing the first task | Inform Web users. Identical repeats still dedupe. |
| Voice-sample confirmation | The confirm route can return 409 `voice_sample_content_changed` if the sample file no longer matches its recorded digest | None |
| Database engine | `hide_parameters=True`: SQL errors no longer echo bound parameters | None |
| Web task failure toasts | `provider_job_rejected` failures show `code: message` from the provider | None |

No schema migration, data migration or project rewrite is part of this change.

## Granting global configuration tools (optional)

The tools are off by default. To expose them to specific remote API keys, set the following on the server process and restart:

```bash
ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS=key-name-1,key-name-2
```

- Names are API-key names, the same `name` that appears in `apikey:<name>`. A key that is not listed neither sees nor can call the tools: listing hides them, a call returns "Unknown tool", and each handler re-checks the grant.
- The grant is a tool-surface policy, **not** a security boundary. Any `arc-` API key already has administrative REST access. Grant only keys whose holders are already trusted to change provider configuration.
- Global configuration tools are never granted to project sessions or the embedded Agent.
- Writes default to dry-run (`apply=false`). Applying requires `expected_revision`. Credential reuse is refused when any rendered submit, poll or result request would leave the credential's origin.
- Apply needs the worker's reload callback, which `server/app.py` injects. If it is missing, apply refuses with `reload_limits_unavailable`.
- Connection tests are not exposed. Nothing in these tools calls a provider.

## H3 endpoint copies made before this change

The existing `ce-1` endpoint and the `custom-1` provider are **not** modified, migrated or deleted automatically. A copy made from the H3 built-in before this change lacks `container_mime` and `error_code`, so it keeps sending `audio/mpeg` / `audio/x-wav` data URIs.

To adopt the fix explicitly and reversibly:
1. Record the current endpoint definition and revision with `get_endpoint_definition`, or through the Web.
2. Compare it with the built-in `minimax-h3` definition.
3. Use `update_custom_endpoint` with `apply=false` to review the diff, then with `apply=true` and the recorded `expected_revision`.
4. **Rollback:** submit the recorded definition with `update_custom_endpoint` against the new revision.

Do not run a connection test to verify. It can generate billable content.

## Rollback of the build

1. Redeploy the previous build. All new tools disappear, and no stored data depends on them.
2. Leftover staged uploads and Jianying packages under `<project>/.arcreel/mcp_uploads/` and `<project>/.arcreel/mcp_packages/` are inert. Remove them manually if wanted; the previous build ignores dot directories.
3. Unset `ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS`. The previous build ignores it anyway.
4. Voice samples, versions, grids, episodes and library entries written through the new tools are ordinary native records. The previous build reads them unchanged.

## Not verified

- Real Claude CLI and Codex client handling of `EmbeddedResource` blobs (`application/octet-stream`) and of the media resource template. The transport is verified with the official `mcp` Python client only.
- Real provider behaviour (MiniMax H3, TTS), audiovisual quality and billing. All provider interactions were simulated.
