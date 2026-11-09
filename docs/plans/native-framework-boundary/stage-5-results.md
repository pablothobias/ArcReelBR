# Stage 5: inherited cloud routes and local-subscription pricing

Date: 2026-11-09. Base revision `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`, retaining prior local stage-1/2/3/4 changes. User authorized R12/stage 5 and results before stage 6. Changes are local and uncommitted; stage 6 has not started.

## Implemented scope

The no-active-credential fallback in build_anthropic_env now refuses enabled inherited Claude cloud-route selectors before assigning zero marginal Agent token pricing. The error is native and nonretryable, identifies flag names without values/secrets, and does not silently clear selectors or switch to another authentication route.

Cloud selector names are centralized in lib/config/env_keys.py. lib/config/claude_subscription.py provides the shared boolean resolver and SubscriptionRouteConflictError. The internal subscription text auth check uses the same resolver, with its existing API/bearer/endpoint guard keys also centralized. API credential/endpoint checks remain nonempty-string checks; they are not mistaken for boolean flags.

Supported true values are 1/true/yes/on with case/whitespace normalization; false/empty/unknown strings do not activate the selector. Disabled flags therefore no longer cause the internal subscription check's former blanket nonempty-string rejection. This is an intentional alignment with CLI semantics, not removal of the API/bearer isolation guard.

The installed CLI contains six selector names: Bedrock, Vertex, Foundry, Claude Platform on AWS, Anthropic Google Cloud and Mantle. Guarding only the three originally reproduced names would leave the same class of omission. Static CLI inspection identified the additional names and boolean helper; no CLI was executed. [Source evidence](evidence/stage-5-cli-source.json) records installed SDK version 0.2.173 and a CLI binary digest.

The [official environment-variable reference](https://code.claude.com/docs/en/env-vars) documents boolean values and the public cloud selectors; the additional Google Cloud selector is observed in the installed code and [Anthropic's source](https://github.com/anthropics/claude-code/blob/main/mods/telemetry/hooks/register.ts). That internal selector is not listed on the current public env reference; it is not claimed as a stable public integration API. The guard does not add support for any cloud provider.

## Preserved behavior

- The active credential branch is AST-identical to the baseline; legacy configured API keys keep reference pricing. Synthetic API controls retain credential multipliers and environment values, including when a cloud selector is present. This preserves existing configured-API behavior; it does not certify mixed API/cloud deployments as supported.
- Clean/no-enabled-cloud-selector construction retains zero marginal token pricing for the intended local route. This is not proof of a successful subscription login, zero recurring subscription cost or free media generation.
- SDK/environment injection, AgentEnv pricing snapshots, token/catalog reference-cost calculation and settlement code are unchanged. Existing tests verify credential/multiplier changes do not reprice already connected turns from current settings.
- The internal text backend's class, selected model/effort, constrained SDK options, quota handling, no-paid-fallback and cleanup are AST-identical. Only its auth precondition's shared route interpretation changed.
- The check runs at native environment construction. No Codex pre-generation stage, new auth-status probe, readiness polling or external financial harness was introduced.

## Reproduction and regression coverage

Before correction, three focused inherited-mode cases failed: real configuration/environment construction reached the intercepted SDK process boundary for Bedrock, Vertex and Foundry rather than refusing the conflicting zero-price route. [Pre-fix output](evidence/stage-5-before-fix.txt). Process creation was prevented; neither the version probe nor actual Claude/auth/inference ran.

Final new coverage includes 44 cases: 17 integration cases for actual isolated credential/settings repositories plus native environment construction/SDK merge, 15 pure selector/nonretryability cases, and 12 internal subscription auth-consistency cases. The integration fixture uses the repository's existing bind_session_factory to select disposable SQLite; no credential repository mock substitutes the read/pricing contract.

For enabled selectors, construction raises SubscriptionRouteConflictError and never reaches the capture boundary; the synthetic environment values remain unchanged. Disabled/clean controls reach the intercepted SDK boundary with their expected zero pricing and disabled values intact. The SDK's documented skip-version-check environment hook is used only in these test processes; anyio.open_process is intercepted. No private version-check function is patched. API controls persist only synthetic credential/settings values in disposable test databases. Internal auth checks use a fake process_factory returning synthetic auth JSON, not a real login query.

## Tests executed

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/unit/lib/config/test_anthropic_env_dict.py \
  tests/unit/lib/config/test_claude_subscription_routes.py \
  tests/unit/lib/config/test_env_keys.py \
  tests/unit/lib/config/test_config_service.py \
  tests/unit/server/agent_runtime/test_options_assembler.py \
  tests/unit/lib/backends/text_backends/test_claude_subscription.py \
  tests/integration/lib/backends/test_claude_subscription.py \
  tests/integration/server/agent_runtime/test_subscription_route_pricing.py \
  tests/integration/server/agent_runtime/test_session_manager_usage_billing.py \
  tests/unit/lib/backends/test_accounting_characterization.py \
  tests/unit/server/test_subscription_text_pause.py \
  tests/integration/server/test_session_mcp.py
```

**206 passed**, one known SQLite expression-index reflection warning, 9.23 seconds. [Main output](evidence/stage-5-pytest.txt). The earlier focused run of 64 cases is retained as [intermediate evidence](evidence/stage-5-focused.txt), not added to the total; the final suite includes expanded API controls.

After documenting the native conflict response in the public guide and MCP testing document, `tests/unit/test_public_contract.py` passed **12 cases**, same warning, 2.46 seconds. [Public output](evidence/stage-5-public-contract.txt). Total: **218 distinct passing cases**.

Ruff check/format passed for all seven changed Python files ([output](evidence/stage-5-lint.txt)); targeted BasedPyright returned **0 errors, 0 warnings** using the existing venv path ([output](evidence/stage-5-types.txt)). `git diff --check` passed. No dependency installation, repository tool-configuration change or gate suppression.

## Separation from current configuration and remaining limits

[Baseline](evidence/stage-5-baseline.json) and [scope comparison](evidence/stage-5-scope-check.json) verify **4,711 protected tracked files unchanged**. Changed paths are four native implementation files, three test files and two documentation files. The config service's only changed member is build_anthropic_env; the active-credential branch, options assembler, accounting/DB code, prior stages, official skills and native speech/presentation remain protected.

No current saved settings, models, credentials, login state, host connection, installed skill, launch environment, production data or historical cost record was inspected/changed. No actual Claude/authentication/provider/model/ASR process or request ran. The separate configuration investigation still owns current installation, saved/effective settings and readiness. No conclusions from that worktree were assumed or imported, and no cross-worktree edits were performed.

The guard covers the known inherited **process** selectors at environment construction. It is not a complete resolver of CLI-managed/project/user settings precedence or later settings updates, which remain configuration scope. It does not claim actual underbilling occurred, prove current cloud authentication or reconstruct past invoices. Newly discovered future route selectors require source-backed updates, not a claim that this list certifies all future CLI releases.

R12's reproduced inherited-route/zero-price mismatch is corrected under these bounds. R10e/stage 6 remains pending. No commit, push, merge, deployment or live restart occurred. Stop before stage 6 for user review.
