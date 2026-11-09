# Stage 3: non-persistent diagnostic script loading

Date: 2026-11-09. Base revision: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`; earlier stage-1/2 changes are retained. User authorized stage 3 only. All changes remain local and uncommitted; stage 4 has not started.

## Implemented scope

| Finding | Change | Compatibility retained |
|---|---|---|
| R10a + R10b | get_project_costs uses native load_script_readonly. Legacy duration fields are adopted in memory, with no script migration write during the read or after handler cancellation. | Same native cost estimator and script normalization; the cancelled read worker may still finish but cannot persist the reproduced migration. No new cancellation engine. |
| R10c | edit_images chooses load_script_readonly for preview=true only. | Actual edits retain load_script and the existing transaction boundary. The current-source successful image preview test and missing/non-executable legacy-target test both pass. |
| R10d | Shared episode storyboard loading/planning accepts persist_legacy_migrations, default True; only quote_storyboards opts out. | Same native planner, targets, skips, lanes, dependencies and price estimator. Generation, Web and video-planner callers retain the previous default. No planner duplication or global reader change. |

Updated the MCP testing document and public installation guide to state the narrow script-persistence contract. Installation, connection, credentials, current settings, applied timing and speech materialization were not changed. These operations remain snapshots rather than reservations/admission guarantees.

## Regression evidence and controls

Before implementation, six selected cases gave **4 expected failures and 2 passing controls**, 9.65 seconds. [Pre-fix output](evidence/stage-3-before-fix.txt). Failures covered cost consultation persistence, a late write after cancellation, preview persistence and migration before route/skeleton refusal. Controls covered actual-edit migration and correct early reference_video refusal.

After correction, the same six cases passed. [Focused output](evidence/stage-3-focused.txt). Additional coverage checks:

- Real cost computation returns identical values for legacy in-memory adoption and the explicitly migrated current script. Text `Ana diz: "Olá, Ana!"`, duration 8 and project metadata are preserved by consultation.
- Cancellation uses event handshakes and an injected ProjectManager subclass that wraps the real public readers with a scheduling barrier. Both readers delegate to native super implementations, including real migration/persistence when applicable; no private persistence hook or outcome is fabricated. The test waits for actual reader completion before asserting no late write. It does not claim worker termination or connected-MCP-disconnect propagation.
- Both preview and actual-edit input loading are exercised against a legacy script. Preview leaves bytes unchanged; the default edit still adopts the legacy format. Those missing/non-executable targets submit no image-edit tasks or provider calls.
- A mismatched quote refuses without persisting; correctly configured reference_video remains refused before loading. An explicit native default-control test still persists adoption before the inherited mismatch refusal, proving the opt-out did not globally alter generation loading.
- Read-only and native valid storyboard plans match, including selected targets, missing-prompt outcomes, image lanes and generated task-spec dependencies. Valid repeated storyboard quotes preserve scripts/project metadata and return stable positively priced targets with no usage generated.

## Tests executed

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/integration/server/test_workflow_access.py \
  tests/integration/server/media_tools/test_image_edits.py \
  tests/integration/server/services/admission/test_storyboard_batch.py \
  tests/integration/server/services/admission/test_cost_estimation_service.py \
  tests/integration/lib/script/reference_video/test_reference_video_duration_migration.py \
  tests/integration/server/routers/test_storyboard_batches_router.py \
  tests/integration/server/agent_toolset/test_host_consistency.py \
  tests/integration/server/test_remote_mcp.py
```

**1,251 passed**, one existing SQLite expression-index reflection warning, 56.06 seconds. [Main output](evidence/stage-3-pytest.txt).

Final recheck ran `tests/unit/test_public_contract.py` plus the cancellation regression after correcting the test wrapper's method annotations/signatures: **13 passed**, same warning, 1.72 seconds. Twelve public-contract cases are additional; the cancellation case overlaps. [Final recheck](evidence/stage-3-final-recheck.txt).

Total: **1,263 distinct passing cases**. The intermediate focused run is not added to the count. No source behavior changed after the main suite; the test-wrapper signature correction preserved its behavior and the final recheck verified it.

Ruff check/format passed for the five changed Python files. [Lint output](evidence/stage-3-lint.txt). Targeted BasedPyright, using the existing environment via `--venvpath /Users/pablo.carminatti.br/Projects/ArcReelBR`, returned **0 errors, 0 warnings**. [Type output](evidence/stage-3-types.txt). An initial test-subclass varargs override produced two incompatible-signature diagnostics; matching the real public signatures resolved them without suppression. `git diff --check` passed.

## Preservation and stop boundary

[Baseline](evidence/stage-3-baseline.json) and [scope comparison](evidence/stage-3-scope-check.json) verify **4,710 protected tracked files unchanged** from the beginning of stage 3. Changed paths are three implementation files, two test files and two documentation files. Stage-1 profiles/retirement, stage-2 schemas/remote guidance, official skills, native providers, language policy, speech/presentation, branding and unrelated tests are preserved.

AST comparison confirms every top-level member in workflow_access.py outside get_project_costs/quote_storyboards is unchanged from the stage-3 baseline, including upload_reference and configure_project. R11 upload correction and R12 authentication correction remain pending. R10e speech-materialization contract remains scheduled for stage 6.

All tests used disposable projects/databases and existing provider/SDK substitutes; no live model, ASR, provider, authentication, running application or production project was invoked. Native internal writes in isolated controls demonstrate retained migration behavior, not direct production repair. No saved model/settings, credentials, host connection, private receipts, selected media/timing, live process or configuration was changed. No restart, commit, push, merge or deployment occurred.

Acceptance is limited to the observed script-loading contracts. It does not certify every dependency as globally write-free, establish actual model/creative quality, or prove connected-client disconnect behavior. Implementation stops before stage 4 for user review.
