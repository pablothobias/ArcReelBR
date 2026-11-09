# Stage 2: MCP Settings authority and preview guidance

Date: 2026-11-09. Base revision: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`, retaining the previously validated stage-1 working-tree edits. User authorization covers stage 2, R07/R09 only. Changes are local and uncommitted. Stage 3 has not started.

## Implemented contracts

### R07: user-only grid control excluded from automated updates

- Extracted common typed fields into ProjectSettingsRequest in `server/routers/projects.py`; Web UpdateProjectRequest retains grid_storyboard. Field annotations/defaults were compared against the original AST and remain unchanged for Web updates.
- ConfigureProjectRequest now inherits only common settings and retains extra='forbid'. Both MCP hosts omit grid_storyboard from their schemas and reject its presence, including true/false/null, before applying other supplied fields.
- The configure_project handler revalidates its serialized input against the restricted contract before building the Web settings request. Explicit field presence is preserved with exclude_unset=True so omitted values are not cleared. Even a broader Web request passed directly to the handler cannot mutate grid or partially apply its other fields.
- The native Settings transaction, Web grid controls, creation contract, existing grid values, supported model/voice/language fields and omitted/null/empty semantics remain available. No user authorization bypass based on source='mcp' was added.

### R09: polling only for actual batch responses

The shared remote long-task note now instructs polling **when the response contains a generation_batch handle**, and explicitly distinguishes immediate preview-only responses without a batch. long_task metadata, handlers, envelopes, submission/waiting/queue behavior are unchanged. Existing real remote submission/embedded waiting and grid list-only preview cases remain covered. A real image-edit preview is exercised through both host adapters and returns equivalent quote JSON, creates no image-edit task/batch and preserves source-image bytes.

### Documentation reconciliation

Updated `docs/testing/native-mcp-production.md` and `public/agent-installation-guide.md` to document supported automated fields and conditional polling. The public guide contained a missed W04 blanket quote-before-generation instruction. It was replaced by capability descriptions plus the original native video-preview/confirmation rules. The connection/install/token steps were not changed or executed. Native MCP testing prose now describes both official direct-tool routing and session delegation rather than implying delegation is the only path.

This corrects the stage-1 completeness claim for that missed public-guide occurrence; the prior stage-1 test results remain valid for their actual scope.

## Reproduction and verification

Before the fix, seven focused cases failed as expected: six direct shared-invocation grid cases (two caller contexts times true/false/null) and schema exposure. [Captured pre-fix output](evidence/stage-2-before-fix.txt). Final coverage uses actual host adapters for rejection, plus separate direct-handler defense and supported-setting semantics; the pre-fix cases were not simply removed to hide the defect.

The main suite command was:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/integration/server/test_workflow_access.py \
  tests/integration/server/agent_toolset/test_host_consistency.py \
  tests/integration/server/test_remote_mcp.py \
  tests/integration/server/media_tools/test_image_edits.py \
  tests/integration/server/routers/test_projects_update_fields.py \
  tests/integration/server/routers/test_projects_creation_fields.py \
  tests/integration/server/routers/test_projects_ad_creation.py \
  tests/integration/server/routers/test_projects_content_language.py
```

**1,135 passed**, one existing SQLite expression-index reflection warning, 45.49 seconds. [Main output](evidence/stage-2-pytest.txt).

After adding three direct-handler defense cases, reran the whole workflow-access file: **15 passed**, same warning, 3.40 seconds. Twelve cases overlap the main suite; this adds three distinct cases. [Handler recheck](evidence/stage-2-handler-recheck.txt).

After updating public documentation, ran `tests/unit/test_public_contract.py`: **12 passed**, same warning, 2.38 seconds. [Public-contract output](evidence/stage-2-public-contract.txt).

Total final coverage: **1,150 distinct passing cases**, not the sum of overlapping runs. The earlier focused post-fix run of 17 cases is also retained as [intermediate evidence](evidence/stage-2-focused.txt), not added to the total.

Ruff check and format check passed for the six changed Python files. [Lint output](evidence/stage-2-lint.txt). Targeted BasedPyright passed with **0 errors, 0 warnings** using `--venvpath /Users/pablo.carminatti.br/Projects/ArcReelBR`. [Type output](evidence/stage-2-types.txt). The initial invocation could not resolve installed dependencies because pyproject points to the absent worktree .venv; supplying the existing environment directory resolved that invocation problem without changing repository/tool configuration or installing dependencies. `git diff --check` passed.

## Preservation, boundaries and remaining work

[Baseline](evidence/stage-2-baseline.json) and [scope comparison](evidence/stage-2-scope-check.json) record the stage-2 source paths and the two explicitly reconciled documentation paths. SHA-256 comparison found **4,709 protected tracked files unchanged** from the start of stage 2, including stage-1 profiles/retirement state, official public skills, localization, native speech/presentation, providers/auth configuration and unrelated tests. The stage-3 cost script reader remains unchanged.

No active user settings, grid values, credentials, environment, login state, host MCP connection or installed skill was changed. No real provider, model, ASR, authentication process, production project or live service was used. Existing tests isolate roots/databases and replace external boundaries. Public instructions were edited as documentation, not executed.

Acceptance achieved locally: both automated hosts reject grid fields without partial writes; supported settings/pt-BR and Web/create grid behavior remain; preview has no false batch handle; real generation/waiting contracts and existing grid previews pass. Model-facing description review confirms conditional guidance but does not prove real-model compliance or audiovisual acceptance.

Remaining R10/R11/R12 corrections, live configuration readiness, installed copies and any stage-3+ work remain pending. No commit, push, merge, deployment or restart occurred. Implementation stops before stage 3 for the user to review these results.
