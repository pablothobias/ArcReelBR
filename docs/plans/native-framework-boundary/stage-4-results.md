# Stage 4: transactional MCP character-image references

Date: 2026-11-09. Base revision `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`, retaining prior local stage-1/2/3 changes. User authorized R11/stage 4 and results before stage 5. Changes are uncommitted; stage 5 has not started.

## Implementation

Added native ProjectManager.install_character_reference_image, following the existing reference-audio pattern. It confines the target to characters/refs and uses the unchanged _update_project_with_files primitive to recheck the character and commit image bytes plus the metadata pointer under the same project lock used by deletion, with native staging/backup/rollback.

The existing pointer-only setter and the new installer share a single in-memory character resolver/setter. The pointer-only setter's public behavior remains available. The installer does not call that setter's locking public transaction from inside another lock, avoiding nested lock acquisition.

The file-upload service selects this installer only for character_ref with require_reference_host=True, the existing MCP path. A missing character at commit returns the native 404/refusal, not success. Existing normalization, extension/naming rules and project change-source tracking remain. Audio, style, sheet uploads and Web missing-owner tolerance keep their original branches. No new external production or authorization policy was introduced.

The native transaction primitive and native deletion/trash implementation were not changed. No late blind unlink was added; failed replacement restores previous bytes rather than deleting another request's or an older valid reference. Success establishes the pointer/file invariant at commit, not a guarantee against a legitimate later deletion.

## Regression cases

Added `tests/integration/server/test_reference_upload_transaction.py`, with 14 parametrized cases:

1. Real native character deletion after a paused stale MCP precheck causes refusal, with no recreated character or new orphan file.
2. Successful image replacement retains the metadata pointer, pt-BR and absence of generated sheet content.
3. Simulated staging, install and metadata-write failures, each with and without an existing reference, preserve/restore metadata and image bytes (six cases).
4. Concurrent same-target uploads leave a coherent registered reference.
5. Cancellation during the native metadata commit waits for the transaction to settle before propagating cancellation; committed file and pointer agree.
6. Web upload without an existing character retains its intentional tolerant behavior.
7. An upload committed first can subsequently be removed through native asset deletion.
8. Existing Unicode-decomposed character keys are resolved without creating/renaming a duplicate host.
9. A failed replacement cannot remove a concurrent successful replacement.

The race wraps the real public load_project method to hold its precheck snapshot; native deletion uses an independent real manager on the same disposable root. Commit/failure tests intercept os.replace, a filesystem boundary, and delegate all non-selected operations to the real implementation. No private transaction hook or result was patched. Event handshakes control ordering; sleep(0) only yields scheduling, without time-based sleeps. The cancellation/deletion and transaction outcomes use real project persistence.

The prior R11 audit already reproduced the pre-fix false-success condition. The first new-test attempt here had a setup error: isolated_data_root configures isolation but does not return a path. The test was corrected to use get_project_manager, as existing fixtures do. A second pilot assertion assumed character_sheet was absent, while native creation initializes it empty; it was corrected to assert no generated sheet content. No production change was made to accommodate those fixture assumptions. [Initial setup output](evidence/stage-4-initial-test-setup.txt) and [initial focused output](evidence/stage-4-initial-focused.txt) are retained as intermediate results, not defect or passing evidence.

## Final validation

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/integration/server/test_reference_upload_transaction.py \
  tests/integration/server/test_workflow_access.py \
  tests/integration/server/routers/test_files_router.py \
  tests/integration/server/routers/test_files_router_asset_sheet_upload.py \
  tests/integration/lib/project/test_project_manager.py \
  tests/integration/lib/project/test_project_manager_concurrent_save.py \
  tests/integration/server/agent_toolset/test_host_consistency.py \
  tests/integration/server/test_remote_mcp.py
```

**1,367 passed**, one known SQLite expression-index reflection warning, 57.35 seconds. [Main output](evidence/stage-4-pytest.txt). This includes all 14 new cases and existing Web uploads, audio/style/sheet branches, ProjectManager/deletion/concurrent-save, shared-host and remote contracts, and earlier workflow-access regressions.

After documenting the guarantee in the public guide and native-MCP testing document, `tests/unit/test_public_contract.py` passed **12 cases**, same warning, 2.31 seconds. [Public-contract output](evidence/stage-4-public-contract.txt).

Total: **1,379 distinct passing cases**. Ruff check/format passed for the three changed Python files ([output](evidence/stage-4-lint.txt)). Targeted BasedPyright with the existing venv path returned **0 errors, 0 warnings** ([output](evidence/stage-4-types.txt)). `git diff --check` passed. No gate suppression or dependency installation was needed.

## Preservation and boundaries

[Baseline](evidence/stage-4-baseline.json) and [scope comparison](evidence/stage-4-scope-check.json) show **4,714 protected tracked files unchanged** from the start of stage 4. Changed paths are two native implementation files, one new regression file and two documentation files.

AST comparison of ProjectManager confirms the only changed existing method is update_character_reference_image, now delegating its unchanged in-memory field update to the shared setter. The existing transaction primitive, native asset deletion, audio installer and all other methods remain unchanged. Earlier stages, official skills, language/prompt policy, speech/timing, provider configuration/authentication, branding and unrelated tests remain protected.

No live configuration, credentials, login state, host connection, production project/media, private receipt, historical usage or active service was inspected/changed. No real model/provider/ASR/authentication call, live restart, commit, push, merge or deployment occurred. Tests use disposable roots/databases and existing external substitutes; internal file mutations are confined to test fixtures.

R12 authentication/route classification belongs to stage 5 and remains pending. R10e documentation/verification remains stage 6. This implementation does not certify every possible reader's cross-file snapshot behavior or permanent asset existence after later native operations. It establishes the specific owner/file commit and rollback guarantees exercised above. Stop before stage 5 for user review.
