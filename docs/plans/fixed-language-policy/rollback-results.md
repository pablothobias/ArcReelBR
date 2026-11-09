# Language-stage behavioral rollback

Date: 2026-11-09. HEAD remains `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. The owner authorized reverting the last language stage's behavioral changes, preserving existing customizations and native-framework stages 0-7, executing tests and making no commit.

## Result

Restored 22 tracked files byte-for-byte to the recorded pre-language baseline. Before writing, every restoration candidate was verified against `/tmp/arcreel-language-baseline.json`; HEAD was used only for files whose content hash matched that baseline. No worktree-wide reset was used.

The public installation guide was handled separately: only its appended Product language section was removed. The resulting bytes match the baseline containing all stage-0/7 corrections. Restoring the entire guide from HEAD would have lost those corrections and was not performed.

Restored behavior:

- English remains the default presentation language, while supported saved preferences, locale caching and the Settings language selector work as before.
- Native request/accepted-message locale again supplies system and delivery language context; retries/resends retain their original message context. History-prefix recognition, snapshots and profile synchronization were not modified.
- The pre-existing pt-BR customization again selects English technical/image/video prompts and Brazilian Portuguese creative content only for Brazilian projects. Other languages retain their prior output contracts.
- The universal pt-BR policy and new mandatory approved-adaptation prerequisite were removed. Source-language instructions, schema contracts and native extraction/verbatim rules are restored.
- Tests and shared frontend fixture setup were restored with their corresponding behavior.

The generic generation reference's Chinese prompt wording is restored to its prior state. Its conflict with the Brazilian customization remains a separately scoped documentation issue; this rollback introduces no replacement policy. Existing Brazilian prompt policy and the earlier generated media remain untouched.

## Independently retained change

The single `make_translator("en")` expectation in `tests/unit/server/routers/test_assistant_routes.py` remains. It is exercised by two parameterized cases and fixes a pre-existing mismatch between the test expectation and the route's English error. No route implementation was changed. These cases pass in the current selected backend run.

## Documentation and preservation

ADR 0122 and AGENTS.md were restored. ADR 0123 is marked rejected with an explicit withdrawal notice; its old proposal is retained only as historical evidence. The previous language report/logs remain intact under a withdrawal banner. The native-framework plan banner now links to this rollback rather than claiming that the withdrawn global policy supersedes the baseline.

[Scope comparison](evidence/rollback/scope-check.json) verifies all 22 restored paths against the pre-language baseline, **4,748 other tracked entries unchanged during rollback**, and all three untracked stage-0/7 regression files unchanged. Stage-0/7 code, instruction retirement, MCP fixes, transaction/read/cancellation behavior, route/pricing corrections and evidence remain preserved. The retained Web assertion is unchanged during rollback.

No current credentials, providers/models/endpoints, installed skills, saved project settings, production database, original source, media, selected versions, measured timing, history or live application process was modified. RafaCena and the native subscription backend/launcher remain intact. No paid model, generation or ASR request was run.

## Tests actually executed

| Check | Result | Evidence |
| --- | --- | --- |
| Backend selected integration/unit suite | **2,039 passed, one warning in 112.39s**, exit 0 | [Output](evidence/rollback/backend.txt), [29 selected paths](evidence/rollback/backend-selection.json) |
| Complete frontend component/unit suite, four workers | **4,070 passed in 307 files, 79.89s**, exit 0 | [Output](evidence/rollback/frontend.txt) |
| Language page suite, all five registered viewports, one worker | **55 passed, 35.7s**, exit 0 | [Output](evidence/rollback/pages.txt) |
| Complete frontend/e2e TypeScript check | Passed | [Output](evidence/rollback/frontend-types.txt) |
| ESLint on restored frontend/e2e paths | Passed | [Output](evidence/rollback/frontend-lint.txt) |
| Ruff and format check on eight Python files | Passed | [Output](evidence/rollback/lint.txt) |
| Basedpyright on those eight files | **0 errors, 0 warnings, 0 notes** | [Output](evidence/rollback/backend-types.txt) |
| Native Agent profile lint in disposable data/database root | Passed | [Output](evidence/rollback/profile-lint.txt) |
| Git whitespace check | Passed | `git diff --check` |

React Doctor `--scope changed` skipped because the rollback leaves no changed frontend source relative to HEAD. This is not represented as a new health score. [Output](evidence/rollback/react-doctor.txt).

Backend command: `PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider`, followed by the paths in the selection manifest. The union covers restored prompt/language tests plus native session lifecycle/branch/replay/idempotency, both MCP hosts, R07/R09/R10/R11/R12 regressions, measured render, queue/recovery and Gemini accounting protections.

Frontend commands, under Node v24.22.2: `pnpm exec vitest run --maxWorkers=4`, `pnpm typecheck`, targeted ESLint, and `pnpm exec playwright test e2e/regions/language-policy.spec.ts --workers=1`. Browser tests replay recorded API fixtures and block external traffic. The backend warning is SQLAlchemy's existing expression-index reflection limitation. Non-failing pnpm/Vite/jsdom notices are retained in frontend logs.

No test failed in these rollback runs. These are fresh results for the restored state; earlier fixed-policy test results are not reused as rollback validation. No complete backend gate, broad regional screenshot suite, real model/ASR quality test or live-client readiness check was performed. Tests establish local wiring and preservation, not universal model compliance or editorial acceptance.

Frontend dependencies were reused via a temporary symlink to the existing main-checkout node_modules, removed after validation. No manifest/lockfile change. No commit, push, merge or live restart was performed.
