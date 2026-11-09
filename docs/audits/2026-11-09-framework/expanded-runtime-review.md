# Expanded runtime and internal-text review

> Stage-5 update: [R12 implementation results](../../plans/native-framework-boundary/stage-5-results.md) records native inherited-route validation and passing tests. Earlier zero-pricing observations describe pre-fix source; current configuration readiness and stage 6 remain separate/pending.

Date: 2026-11-09. Source revision: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. This source-only review responds to the completeness concern after [the consolidated dispositions](consolidated-dispositions.md). It compares `a779b5d51..HEAD` in `server/agent_runtime/`, `server/text_generation.py`, `lib/backends/text_backends/` and `lib/config/`, then follows the changed seams into their local callers and tests. No product files, running sessions, authentication state or provider configuration were changed. No SDK/provider/auth-status process was spawned. Three isolated pre-spawn environment/pricing cases were executed as described under XR05; no actual authentication or inference occurred.

## Conclusion

The previous preserve list was too compressed to describe the actual runtime changes. English product defaults and subscription text are not merely cosmetic or authentication substitutions: they change how prompts are rebuilt, what context reaches each accepted user turn, which internal runtime/model runs, and how quota exhaustion is surfaced. These should be visible as separate reviewed customizations with their tradeoffs, rather than hidden behind a generic preserve label.

Within this assigned slice, source review did not establish another independent Codex director, altered permission/tool allowlists or replacement session scheduler beyond the already identified profile/director package. The focused XR05 follow-up did reproduce a pricing/auth-route mismatch before subprocess launch, which warrants a targeted adjustment rather than subscription removal. This negative finding is bounded to these files; it is not a certificate of all fork behavior or proof that the new execution contracts are equivalent to the base.

## XR01: system-prompt snapshot semantics actually changed

- `f997d91b8` changes `SystemPromptPreset.snapshot=True` to `False` in `server/agent_runtime/options_assembler.py:389-397`. The constructor still uses the native Claude preset, the existing hooks, allowed-tools derivation, in-process ArcReel MCP server and sandbox.
- The rebuilt append prompt is not language-only. `_build_append_prompt` combines reply-language regulation, static project context and the user-memory segment (`options_assembler.py:150-174`). Mutable project metadata continues to be read on demand, not frozen into this append.
- The local ADR explicitly records that reconnection refreshes user memory too, and that prompt-prefix caching, token counts and request fingerprints may differ (`docs/adr/0122-english-product-defaults-preserve-project-language.md:17-23`). Its live-model compliance and equivalence evaluations remain pending there.

**Disposition:** keep this as an intentional native product-language/lifecycle customization under ADR 0122, with the broader effect and evaluation limit explicit. Do not classify it as cosmetic or regression-free. A proposal to revert snapshot policy would be a separate product decision, not a consequence of retiring Codex's extra harness. Do not claim every accepted message reconnects/rebuilds the runtime: resident sessions reuse their client; per-message context covers later turns.

## XR02: accepted user messages receive application instruction context

- New `server/agent_runtime/conversation_language.py:8-18` creates a reply-language context block which explicitly preserves project/source creative language.
- `_user_message_frame` prepends that block to the actual SDK user-message delivery (`server/agent_runtime/session_manager.py:223-243`). The accepted queue entry keeps its own normalized `reply_locale` (`:1381-1390`), and delivery/retries use that locale (`:1429-1432`). This affects model-facing instructions, not only UI labels.
- The visible/backfilled user record removes only the exact generated prefix matching the message UUID and a supported locale (`conversation_language.py:22-32`; `event_log.py:357-363`). It does not generically strip arbitrary quoted language-like user text.
- Existing tests inspect per-message locale retention/retry behavior (`tests/unit/server/agent_runtime/test_session_manager_user_input.py:98-126`) and snapshot wiring (`tests/unit/server/agent_runtime/test_options_assembler.py:208`). They are not real-model compliance proof.

**Disposition:** preserve as native conversational-language behavior, distinct from Portuguese creative content. It is application context, not literally user-authored requirements; production reconstructions should keep that distinction. No new production stage or independent Codex decision-maker is introduced by this block. No claim of complete historical transcript/compaction equivalence is made.

## XR03: internal subscription text uses a separate constrained SDK invocation

- `ecd6ead43` adds `ClaudeSubscriptionTextBackend`, selected at the existing backend factory seam only when the configured provider is `claude-subscription` (`lib/backends/text_backends/factory.py:28-36`). It is not the embedded production Agent and does not consume that Agent's session/history.
- This is more than exchanging a key. The backend permits the fixed model in `lib/config/claude_subscription.py:3-5`; validates it in `claude_subscription.py:115-126`; uses effort `medium`, a fresh temporary cwd, empty tools/allowlist/MCP/skills/plugins/settings sources, one turn, and no session persistence (`:140-180`). It sends the native request's prompt/system prompt/images and structured-output schema. Cleanup uses the native cancellation-safe mechanisms.
- Before inference it runs official CLI `auth status --json` and refuses API/bearer/cloud overrides in the parent process (`:53-93`). This review inspected that code but did not run authentication or read credential values.
- The result path rejects unexpected returned model identity, missing terminal results, errors, and invalid/truncated structured output (`:192-245`). These are actual new backend constraints; compatibility with every future SDK/CLI/model response is not proven by this source review.

**Disposition:** preserve the user-selected subscription integration at the native backend seam, including its isolation and no-paid-fallback safeguards. It is not evidence of a second creative harness simply because it uses Agent SDK internally. Do not describe it as behaviorally identical to the old text backend or assume live availability. Fixed model/effort, timeout/output behavior and auth requirements should remain explicit product contracts, not silently moved into Codex or removed in the workflow cleanup.

## XR04: quota exhaustion changes native retry/resume signaling

- The new `SubscriptionQuotaPaused` is nonretryable with code `subscription_quota_paused` and `resumable=True` (`lib/backends/text_backends/base.py:113-125`). The subscription backend raises it on rejected rate-limit events/messages or 429 terminal status (`claude_subscription.py:192-215`), rather than selecting a separately billed API fallback.
- `server/text_generation.py:1115,1878,2028` preserves this identity through the drama/reference/narration script-plan exception boundaries; other changes inspected in this file are predominantly English receipts/error guidance rather than additional production gates.
- `server/tool_runtime.py:720-742` unwraps the exception and returns `GenerationAction.NONE` plus resumable metadata. This is a request to stop and explicitly resume, not proof of a new durable paused-job scheduler or guaranteed automatic resumption.

**Disposition:** preserve the quota/no-paid-fallback contract, and distinguish it from the retired external attempt/recovery policy. The field name `resumable` alone must not be used to promise automatic recovery. No additional retry engine was found in this slice.

## XR05: subscription Agent cost inference has a bounded basis

- `ffdb580b0` changes only the no-active-credential fallback in `lib/config/service.py:112-117`: absent stored API key yields `AgentPricing(multiplier=0.0)`. Active credential pricing still comes from the same credential row (`:99-110`).
- The runtime injects these credential/pricing facts through `AgentEnv`, and clears the existing list of other-provider environment overrides (`server/agent_runtime/options_assembler.py:55-93`). The clearing of `ANTHROPIC_AUTH_TOKEN` and `CLAUDE_CODE_OAUTH_TOKEN` predates this fork baseline (`lib/config/env_keys.py:20-26`); it is not a new bypass discovered here.
- The no-key pricing decision is not itself a successful login check. Existing unit tests assert the selected pricing basis (`tests/unit/lib/config/test_anthropic_env_dict.py:55-71,98-99`), not current actual subscription authentication or every possible CLI authentication source.

**Disposition:** retain as an explicit marginal-cost policy for the intended subscription route, with its authentication premise visible. Do not infer authentication readiness, free media generation or no recurring subscription charge from zero Agent per-request pricing. Current connection/configuration verification belongs to the parallel configuration investigation. The follow-up below establishes a conditional code-level mismatch without claiming an actual underbilling incident or requiring subscription removal.

### XR05 follow-up: inherited cloud mode plus zero multiplier reproduced

A parent-requested targeted check found that the clearing list omits `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX` and `CLAUDE_CODE_USE_FOUNDRY` (`lib/config/env_keys.py:9-50`). The new internal subscription backend explicitly treats those flags as incompatible alternatives (`claude_subscription.py:31-45,57-60`), but the embedded Agent's environment path does not. The installed SDK merges parent environment and then options overrides immediately before `anyio.open_process` (`claude_agent_sdk/_internal/transport/subprocess_cli.py:819-826,875-883`, in the existing main-checkout virtual environment). The clean `env -i` launcher documents protection for its own entry (`scripts/run_local.sh:4-6`); it does not cover arbitrary service launch methods.

**Reproduction:** [audit source](reproduce_agent_pricing_inheritance.py), [captured output](agent-pricing-inheritance-output.txt). With mocked empty credential/settings repositories, the real `build_anthropic_env` produces multiplier 0.0. The real provider-environment loader leaves each synthetic cloud-mode flag unoverridden. The real SDK environment assembly passes the flag value `1` to the intercepted spawn boundary while emptying API key/bearer/OAuth variables. Three parametrized cases passed, one existing SQLite reflection warning, 1.39 seconds. SDK version checking and process creation were intercepted, so no process, network, credential lookup or inference ran. Only flag names and synthetic values were observed, not actual environment secrets.

**Updated classification:** confirmed conditional auth-route/accounting mismatch before launch. The new inference “no stored API key means subscription, therefore zero per-request cost” is broader than the runtime containment guarantees outside the clean launcher. Cloud-mode inheritance predates the new zero multiplier, but the zero-pricing conclusion is new, so attributing the entire issue to unchanged infrastructure would miss the interaction. This does **not** establish that a real cloud call succeeds or is charged, that a current user process has these flags, or that an actual ledger entry was underpriced.

**Proposed targeted adjustment:** tie zero-price classification to an explicit/verified allowed authentication route, or consistently refuse/contain incompatible routes across launch methods. Keep the intended subscription feature and no-paid-fallback protections. Coordinate current launch/auth findings with the parallel configuration audit; do not turn this into an extra Codex pre-generation gate. No correction was implemented.

The temporary test copy under `tests/integration/server/test_audit_agent_pricing_tmp.py` was removed after execution. The reproduction is retained outside the normal suite. It loaded existing repository test fixtures, which isolate data roots and SQLite databases. No application/product source was changed.

## Coverage limits and suggested list improvement

Add XR01-XR05 as explicit reviewed preservation/qualification entries so the audit shows these changes were inspected rather than accidentally omitted. XR01-XR04 are not new proven defects or removal recommendations. XR05 now has a confirmed pre-spawn mismatch and a narrow adjustment proposal; it is not a reason to delete the subscription capability. Keep prior W01-W08 and R07-R11 intact unless the owning review changes their evidence.

This review did not audit every language-template edit, every billing/provider path, live CLI behavior, real compaction, real subscription success, or the current external host installation. The full fork contains hundreds of other changed paths. A trustworthy completeness claim needs a path-to-review coverage inventory and clear residuals, not a larger speculative removal count. No regression absence is claimed.
