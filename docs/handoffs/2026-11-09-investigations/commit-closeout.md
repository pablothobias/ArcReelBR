# Commit closeout: 9 November 2026

## Authorization and boundaries

The user authorized fixing failing tests, completing documentation, validating again and creating separate local commits. No push, application configuration changes, service restart, authentication changes or media generation were requested or performed in this closeout. Tests use temporary isolated data roots and fixtures, not the production projects.

The original `local-changes.json`, runtime snapshot and before-status files remain historical evidence. Their old HEAD and dirty-state counts must not be treated as the current checkout state.

## Commits by scope

| Commit | Scope |
| --- | --- |
| `b88d14cd0` | Native MCP configuration/reference/cost access and session controls; shared schema descriptions and host-consistency coverage |
| `39487c317` | Local speech review, source-bound subtitle timing, dependency setup, public Chinese/English installation documentation and external Agent guidance |
| `e15b423b5` | Historical production plans, published ticket receipts, glossary and research; superseded production direction explicitly marked historical |
| `399248ebc` | Learning mission, resource index, overview and reference materials |

This closeout and the two investigation prompts are included in the following `docs(handoff)` commit; find its full ID with `git log -1 -- docs/handoffs/2026-11-09-investigations`.

## Corrections and validation

- Added sample arguments for all seven workflow-access tools to the dual-host consistency inventory.
- Added meaningful field descriptions to the shared Settings request schema and upload/usage schemas; existing value/default/validation semantics are preserved.
- Aligned the fixture's project root with the real configuration resolver using the existing isolated-data-root fixture.
- Declared the expected missing-character/missing-script sample outcomes and retained their error-envelope comparisons.
- Compared both Settings response bodies and text blocks while normalizing only `project.metadata.updated_at`, which is independently stamped on each host invocation. Other values remain compared exactly.
- Full host-consistency file: **1,011 passed**, with one existing SQLAlchemy SQLite expression-index reflection warning.
- Other selected backend files: **114 passed** in the preceding combined run; their code and inputs were unchanged by the final timestamp-path correction. Combined validated scope: **1,125 cases**, not the entire backend suite.
- Selected files cover local speech review, workflow access, session MCP, image editing, project routes, presentation and final cuts.
- Targeted `basedpyright --warnings`: **0 errors, 0 warnings** for the changed request/schema/test files.
- Targeted Ruff lint/format and `git diff --check`: passed.
- Frontend typecheck and **2,974 related tests in 218 files** passed in the preceding review. No frontend inputs changed during these corrections, so those results were reused. That run reported the shell's Node 22 version below the package's declared Node requirement; it passed but is not a claim of testing every supported Node version.
- Documentation consistency check and Chinese/English production builds passed with installed Node 24.22.2. Deployment instructions now cover optional dependencies, separate model provisioning, server path configuration, container requirements, inspection versus applying timing and quality limits. No documented setup commands were executed against the application.

The original host-consistency failures are resolved; they are no longer a current blocker. Full autonomous audiovisual assessment remains unresolved, as do the user's editorial and continuity concerns. Those are the subjects of the two read-only investigations, not defects claimed fixed by this closeout.

## Starting the investigations

Use the current committed checkout and existing data root. The running application was deliberately not restarted; it may retain pre-closeout modules/schema descriptions until restarted separately. Distinguish loaded runtime behavior from the committed source during inspection rather than silently restarting it.

The earlier observation that `frontend/vite.config.ts` changed during handoff preparation remains historical. It was not included in these commits because it no longer differed from HEAD at closeout. No author or cause is inferred.

Keep prior budget approvals closed. Both investigation prompts remain read-only and prohibit paid calls, production edits and configuration mutations.
