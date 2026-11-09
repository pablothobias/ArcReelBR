# Stages 0 and 1: implementation and validation results

Date: 2026-11-09. Base revision: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`; changes are local and uncommitted. User authorization covers only stages 0 and 1. Stage 2 and all later stages have not started.

## Stage 0: baseline and scope

Recorded [baseline](evidence/stage-0-baseline.json) before implementation. The existing unstaged `disable-model-invocation: true` edit was independently present. Its exact patch was retained as [pre-existing edit evidence](evidence/preexisting-skill-disable.patch) before the user-authorized retirement of that package. Earlier audit documents and this plan were already untracked; none was discarded.

Allowed runtime/instruction paths were restricted to the three profiles, the two native skills, one tool description, the obsolete director package and its two exclusive test files. The editor in this worktree changed only those paths. Shared-file scope in `server/agent_toolset/workflow_access.py` was limited to the cost-tool description; request models, handlers, auth, validation and Settings contracts were unchanged. No integration with another worktree or claim of coordination with its operator was made. Future overlapping configuration/route work still requires ownership coordination before stages 2-7.

SHA-256 comparison of **4,712 protected tracked files** found no changes or removals. This covers all tracked paths outside the 11 explicitly allowed paths, including native implementation, official public skills, language handling, providers/configuration, media/presentation code and unrelated tests. [Scope/preservation evidence](evidence/stage-1-scope-check.json).

## Stage 1: completed changes

| Mechanism | Implemented scope | Preserved behavior |
|---|---|---|
| W01 | Removed the custom director skill/package from active repository discovery. | Official public skills, existing histories and private evidence locations. Git retains the tracked package history. No installed host copy was inspected or modified. |
| W02 | Removed policy.py and recovery-format source with the package; retired the two tests whose sole purpose was to load/execute it. No other active runtime import/reference was found outside historical documents. | Native queue/recovery/idempotency implementations and their tests; permission/receipt/history records. No replacement helper. |
| W03 | Removed the mandatory project/configuration preflight pair from all three Delegated production sections. | Actual tools, supplied-settings handling, official plan routing. |
| W04 / R08 | Removed blanket image quotation from generate-assets, all three profiles and shared get_project_costs description. | Quote tools/handlers and factual unknown-cost semantics; native video preview and paid-action confirmations. |
| W05 | Removed the compulsory usage/cost-call pair from profiles. | Usage/cost API contracts, pagination and records. |
| W06 | Removed broad optional-reference policy. | Capability constraints, optional upload access, native required-input admission. |
| W07 | Replaced controller ceiling attribution with respect for the user's supplied ceiling/scope and retained outside-authorization permission guard. | User permission authority; production state remains native. |
| W08 | Limited speech/timing-tool guidance to requested measured timing correction; removed blanket per-unit acceptance prerequisite and compulsory reviewer handoff; repaired dependent prose. | First-round native visual review, keeping speech inside trims, optional recognition/timing, eligible application plus reread/rerender, canonical speech workflow and evidence limits. |

The three Delegated production sections remain identical. No schemas, tool names, handler bodies, batch/waiting semantics, Settings permissions, migration readers, upload transactions or pricing/authentication rules were changed. Remaining R07/R09/R10/R11/R12 findings remain pending their planned stages.

## Tests actually executed

Profile lint, in a temporary isolated data root/database with dotenv loading disabled:

```text
python scripts/lint_agent_runtime_profile.py
```

Result: **passed**, exit 0. [Captured output](evidence/stage-1-profile-lint.txt).

Selected suite, using the existing main-checkout virtual environment against this worktree, with bytecode and dotenv writes/reads disabled as applicable:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/unit/lib/agent/test_profile_manifest.py \
  tests/unit/lib/agent/test_profile_translation_lifecycle.py \
  tests/unit/scripts/test_agent_profile_lint.py \
  tests/integration/server/routers/test_projects_agent_profile.py \
  tests/integration/server/agent_toolset/test_host_consistency.py \
  tests/integration/server/test_workflow_access.py \
  tests/integration/server/test_remote_mcp.py \
  tests/unit/lib/prompts/test_brazilian_content.py \
  tests/integration/server/media_tools/test_speech_review.py
```

Result: **1,178 passed, one warning, 29.72 seconds**, exit 0. The warning is the previously observed SQLAlchemy SQLite expression-index reflection limitation for `idx_tasks_dedupe_active`. [Full test output](evidence/stage-1-pytest.txt).

Coverage includes profile materialization/lifecycle, both shared MCP hosts' schemas/descriptions/envelopes, native Settings/reference/quote/usage functionality, pt-BR prompt behavior and native speech review/measured timing. Existing fixtures isolate data roots/databases and fake provider/SDK boundaries. No real provider/model/ASR request, running application restart, credential lookup or host setup was performed. Tests do not certify real-model adherence or editorial outcomes.

Additional verification: all four removed profile clauses absent across the three matching sections; source review accounts for all 16 original additions; active-reference search excludes explicitly historical docs; `git diff --check` passed; no changed tracked path outside the allowed list. No new prose-mirroring tests were added. Existing obsolete helper tests were retired because their implementation was retired, not to conceal an unresolved defect.

## Acceptance and stop boundary

- Stage 0 repository baseline/scope and Stage 1 repository cleanup accepted by the checks above.
- Protected tracked files remain byte-identical; no production project or private recovery/receipt file was touched.
- Only the shared cost-tool description changed executable-source metadata. No Stage 2 contract correction was attempted.
- Current external skill installation/MCP connection/auth readiness remains a separate investigation. Repository retirement is not proof that a preinstalled copy disappeared from another host or an already-open chat context.
- No commit, push, merge, deployment or process restart was performed. No work beyond stage 1 is authorized by this completion record.

Implementation stops here for the user to review these results before any stage 2 action.
