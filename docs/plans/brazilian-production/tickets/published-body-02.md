## Parent

https://github.com/pablothobias/ArcReelBR/issues/2

## What to build

An existing internal text operation completes through the official Claude Agent SDK using the owner's Claude Code login, with Opus 5.5 and medium effort, without a separate text-provider API.

## Acceptance criteria

- [ ] Add a selectable TextBackend through existing resolution and preserve simple/complex tiers and current callers.
- [ ] Use isolated sessions without production tools; preserve structured-schema validation, image inputs, truncation handling and usage accounting.
- [ ] Use official local authentication; never extract OAuth tokens or silently fall back to a paid API key.
- [ ] Record subscription token usage without fabricating per-token API charges; surface quota exhaustion as a resumable pause condition to the director.
- [ ] Verify structured text and an image-input operation, timeout/failure handling and one real existing text consumer; retain existing provider behavior.
- [ ] Honor ADR 0124 while preserving credential separation and the original Agent conversation-model boundary.
