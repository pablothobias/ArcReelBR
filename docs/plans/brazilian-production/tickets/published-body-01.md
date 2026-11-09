## Parent

https://github.com/pablothobias/ArcReelBR/issues/2

## What to build

Codex connects to the existing local ArcReel MCP and delegates one operation to the embedded Agent, follows its actual state, answers its questions and observes the resulting project state without a separate Agent runtime.

## Acceptance criteria

- [ ] Configure the existing authenticated MCP connection without exposing access tokens or adding credential-management tools.
- [ ] Expose existing session service operations for send/create, state and cursor-based entries, pending questions, answers and interrupt.
- [ ] Preserve ownership checks, accepted versus queued messages and client-key idempotency; a turn result alone never means the session or production is complete.
- [ ] Demonstrate a no-media local delegation, question/answer flow and reconnect; repeated send does not duplicate accepted work.
- [ ] Reuse existing production tools, confirmation parameters and media-batch polling; keep the current harness.
