---
status: rejected
---

# Fixed English presentation and Brazilian Portuguese production

## Withdrawal

Withdrawn on 2026-11-09 at the owner's request after scope review. The fixed-language implementation changed native locale selection, message delivery and production workflow beyond the existing Brazilian customization. Its behavioral changes have been reverted. ADR 0122 and the pre-existing pt-BR English-technical/Portuguese-content rule remain effective. The original proposal below is historical evidence, not active production authority.

Rollback results are recorded in [the rollback report](../plans/fixed-language-policy/rollback-results.md). The generic Chinese prompt reference is restored to its baseline and remains a separately scoped documentation concern; no replacement workflow is introduced by this rollback.

## Decision

On 2026-11-09 the owner selected one language policy for this personal product: English interface and technical prompts, Brazilian Portuguese dialogue. Narration, subtitles and visible story text retain the established pt-BR production customization. This supersedes ADR 0122's selectable presentation/reply language and source-selected production output. ADR 0121's maintenance language, compatibility preservation and public Chinese-source documentation pipeline remain effective.

Application startup selects English before REST/SSE construction regardless of cached/browser locale. General Settings displays English as fixed. Translation resources and locale parser contracts remain for historical compatibility and explicit isolated tests. Stored locale values are not rewritten/deleted. Backend localization APIs retain their existing contracts.

New Agent deliveries and reconstructed system instructions select English. Historical language-block recognition remains unchanged so transcript backfill removes only the exact original application prefix bound to its message, not user text or quoted lookalikes. Queue identities, original content, replay, retry and native snapshot lifecycle remain intact.

Built-in generation output rules select English technical directions and pt-BR creative speech independently of source-language arguments. Mixed prompts retain approved Portuguese quotations verbatim, including accents/punctuation. Source-language metadata, literal source anchors, reference names, JSON keys and enums retain their meanings. Source-language-dependent reading metrics are not globally changed to Portuguese.

A workflow requiring verbatim speech/narration needs approved pt-BR production material. Foreign input therefore requires an approved adaptation before that workflow. This policy does not silently translate existing scripts or weaken native verbatim validation. Original source files remain references.

## Preservation and limits

No existing project, source, script, memory, media, selected version, measured timing, receipt or frozen provider submission is migrated or regenerated. Native profile synchronization continues preserving user-customized files and collisions. No live process restart, paid call, credential change, host installation or external production harness is authorized by this policy.

Rules and deterministic tests establish instruction/transport wiring, not guaranteed model compliance or observed spoken audio. Old resident processes or customized materialized profiles can retain old instructions until normal owner-managed refresh; do not overwrite them to enforce source policy.

See [implementation evidence](../plans/fixed-language-policy/README.md).
