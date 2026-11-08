---
status: accepted
---

# English product defaults preserve project language and conversation history

## Decision

The owner approved English as the default interface and Agent reply language for unconfigured clients on 2026-11-07. This narrowly supersedes ADR 0121's preservation of product defaults, presentation fallback, and interface-coupled generated-content language. ADR 0121 remains effective for maintenance sources, supported locales, compatibility literals, user content, profile synchronization and the Chinese-source public-documentation pipeline.

Keep `en`, `zh`, `vi`, and `ru`. Preserve valid existing supported saved selections and detector caches, whose provenance cannot distinguish deliberate selections from automatic detection. Fresh clients default to English even when navigator advertises another supported language. The application preference selects conversational replies for newly accepted messages. Existing accepted queued messages retain their accepted language through retries and resend. No separate conversation-preference schema is introduced.

Project/source creative language is independent of the interface and replies. Preserve explicit or established content language and existing mode/source defaults for scripts, dialogue, narration, subtitles and generation prompts. Preserve history, memories, artifacts and frozen submitted provider requests. Changing presentation never authorizes translation or regeneration.

## Runtime lifecycle

Use the SDK-supported `SystemPromptPreset.snapshot=False` option to rebuild instructions on request and resume, replacing old frozen language rules while retaining transcripts. This requires Claude Code CLI 2.1.257 or later; the bundled CLI tested locally is 2.1.309. Current user-message frames carry one reply-language context block. The system rule explicitly follows this current context over historical conversation language. Resident clients need no interruption or reconnect when a later accepted message selects another language. Accepted entries and visible queued payloads retain the original user content; application context exists only in the SDK delivery/transcript.

The normally upgraded server process must load the new code. A still-running old process retains its original behavior until its normal owner-managed restart; implementation does not mutate that live process. Rebuilding append instructions also refreshes user-memory context at reconnection. This trades stable historical prompt snapshots for current policy, with possible prompt-prefix cache, token and request-fingerprint differences. It does not rewrite submitted media-generation requests.

## Evidence and release boundary

Local options, queue, replay, resume, profile and browser tests demonstrate wiring and preservation, not live-model compliance. Both the original maintenance-translation equivalence evaluation and this intentionally changed product-language evaluation remain pending their separate approved model/configuration/budget. Independent review covers changed model-facing clauses. See the [implementation record](../plans/english-product-experience/validation.md) for actual results and rollback.
