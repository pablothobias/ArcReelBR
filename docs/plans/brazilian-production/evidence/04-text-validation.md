# Ticket #4 validation

Opt-in selection: `claude-subscription/claude-opus-5-5` through existing default/simple/complex text settings. Existing provider defaults and embedded Agent conversation configuration are unchanged.

| Criterion | Evidence |
| --- | --- |
| Selectable backend preserving tiers/callers | Existing settings/project API validation and TextBackend factory support the explicit pair; real DB resolution tests and existing TextGenerator consumer pass. |
| Isolated structured/vision operation | Fresh temporary cwd, no production tools, MCP, skills or plugins; explicit Opus5.5 medium. Structured schema, image input, truncation and cache TTL tests pass. |
| Official subscription authentication | Official bundled CLI verifies local subscription; API/bearer/cloud overrides fail closed. No credential extraction or paid API fallback. On macOS, USER/LOGNAME must remain available for official credential discovery. |
| Usage and resumable quota | Token totals and cache TTLs preserved; no catalog API price invented. Rejected RateLimitEvent/429 retain subscription_quota_paused with action none and resumable true through consumer wrappers, queues and tool results. |
| Real consumer and error handling | Three actual operations: structured marker, uniform-blue image identification and existing ProjectManager.generate_overview. Formal overview persistence and real ledger were inspected. Timeout/failure/cancellation and legacy backends covered deterministically. |
| ADR0124 boundary | Text-only opt-in backend; no merged credential store or change to embedded Agent conversation model selection. |

[Sanitized real evidence](04-live-text.json) records exact model/effort and outputs. Three operations used 3,924 input tokens and 858 output tokens. The consumer ledger records cost_amount null with no_entry rather than fabricating an API charge. SDK-reported theoretical dollar estimates are explicitly separate from actual subscription fees.

Validation: 487 backend/config/accounting/pause/result/i18n regression tests passed. Targeted Ruff, basedpyright and test audit passed; provider documentation typecheck and both-locale production build passed. A final concurrency fixture validates independent simultaneous calls and cancellation isolation.

Independent reviewer `implement_ptbr` found and verified fixes for rejected SDK quota events and lost pause identity in consumer wrappers. It independently ran 184 focused tests and reproduced preserved pause semantics through queue serialization. Final independent review also inspected all three live receipts and the actual persisted project and SQLite ledger read-only; 26 focused adapter/ledger/pause tests passed. No remaining findings. Final adapter unit file: 22 passed including concurrent isolated calls.

No media generation, separate text API or metered evaluation calls. These tests validate the specified text consumer and contracts, not all subsequent creative quality.
