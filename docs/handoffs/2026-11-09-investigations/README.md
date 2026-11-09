# Investigation handoff: 9 November 2026

**Later closeout:** the uncommitted baseline below is preserved as historical evidence. The authorized test/schema corrections and missing public documentation were subsequently completed and committed by scope. Read [commit-closeout.md](commit-closeout.md) before starting: it records validation results and supersedes the outstanding test-failure/uncommitted-work status below. The application was subsequently restarted with user authorization; see [restart verification](restart-verification.md) for the loaded-schema checks and their limits.

## Start here

The user authorized this handoff and read-only investigation preparation, not configuration changes or another production run. Two independent investigations can start from the current local application:

1. [Native workflow, inputs and editorial diagnosis](prompt-01-framework-investigation.md).
2. [Current configuration audit](prompt-02-configuration-audit.md).

Each prompt is self-contained. Paste one into each new session, or ask that session to read its absolute file path. Both sessions should read this handoff first. Preserve the current checkout and project data while investigating. Use separate output directories for the two reports; do not have both sessions edit this baseline.

These are file-based handoff materials, not newly created chats or dispatched agents. Prompts preserve the Portuguese user-facing instructions from the conversation, with the handoff paths and evidence requirements consolidated. Repository maintenance notes are in English.

## Verified baseline

See [runtime-snapshot.json](runtime-snapshot.json) for the exact capture timestamp in America/Sao_Paulo, native MCP responses summarized without credentials, and final-file hashes/probes.

- Checkout: `/Users/pablo.carminatti.br/Projects/ArcReelBR`.
- Branch: `main`; HEAD: `b848b3db0abaf4312b01fc006efeaa7b8d815c83`.
- Data root used by the retained artifacts: `/Users/pablo.carminatti.br/ArcReelData`.
- Frontend: `http://127.0.0.1:5173`, HTTP 200 at capture.
- Backend: `http://127.0.0.1:1241`, health status `ok` at capture. Its health response has `commit: null`, so this response alone does not identify loaded code.
- Native MCP: `http://127.0.0.1:1241/mcp`, authenticated read calls succeeded.
- Both test Agent sessions are completed, with zero queued messages and zero pending questions.
- Both project workflow plans have no active tasks and report episode complete. This is a workflow state, not editorial approval or audiovisual quality certification.
- No application configuration, production artifact, service or authentication state was changed while preparing this handoff. No generation or inference was requested.

HTTP availability is not a comprehensive UI test. These runtime observations cover the two named projects, not a system-wide job inventory. Recheck availability when beginning the investigations. The local launcher used in this session is `bash scripts/run_local.sh --no-reload`; do not start a duplicate process or restart a running service as part of the read-only audits.

## Test projects and retained evidence

| Project | Native Agent session | Final timeline | Recorded media spend |
| --- | --- | --- | --- |
| `br-viral-reuniao-impossivel` | `7409a38e-b7b2-4177-9064-bbaae6585c9a` | `tl-99ec13b6` | USD 4.8463545 |
| `br-framework-problema-resolvido` | `699d2985-0cc3-480b-a746-97f9a1d8949b` | `tl-909fe8de` | USD 2.5669145 |

Usage pagination was exhausted for both projects at capture; no unpriced media records were returned. Subscription text records may be zero or unpriced and do not measure subscription credit consumption. These totals are application ledger evidence, not independently reconciled provider invoices. Previous budget approvals do not authorize spending in either investigation.

Latest test final:

`/Users/pablo.carminatti.br/ArcReelData/projects/br-viral-reuniao-impossivel/renders/episode_1/tl-99ec13b6/final_cut.without_narration.burned_subtitles.mp4`

Previous test final:

`/Users/pablo.carminatti.br/ArcReelData/projects/br-framework-problema-resolvido/renders/episode_1/tl-909fe8de/final_cut.without_narration.burned_subtitles.mp4`

Both final files were found and probed in this handoff. The latest is 41.4 seconds, H.264/AAC, 1080×1920. The native Agent reported source clips at 768×1344 enlarged on export; inspect source files before relying on this as current evidence.

For the latest project, preserve and inspect:

- `project.json`, `scripts/episode_1.json`, `source/the-expert-reference.txt`.
- `characters/`, `storyboards/`, `videos/`, `speech_reviews/`, `subtitles/`, `renders/`, and native version/timeline/session history where present.
- `.arcreel/memory/viral-reference-the-expert.md`, a production note, not independent quality evidence.
- Private reference material in `/Users/pablo.carminatti.br/ArcReelData/editorial/viral-reference-the-expert`.

Original reference: [The Expert by Lauris Beinerts](https://www.youtube.com/watch?v=BKorP55Aqvg). The native Agent reports adapting publisher-caption passage 00:36.044–01:04.187, not the full sketch. Source popularity does not validate the selected excerpt or its adaptation. Published captions and contact sheets do not prove uninterrupted audiovisual review.

## User feedback and acceptance state

The user rejected the latest result editorially despite successful rendering:

- Júlio appears to change position during the scene. The user suspects keyframes; the first point of failure remains to be investigated.
- The user did not receive the English version of the script for audience-comprehension review.
- The user did not understand the context, did not find it funny, and considered the generated video generic and without value.
- The user suspects the source material, context, story or briefing supplied to the framework is a major bottleneck. This is a hypothesis, not a confirmed cause.

Do not overwrite or regenerate these artifacts before investigation. The contrast between native reviewer acceptance and user rejection is important evidence. A native reviewer had reported a seating inconsistency in the Marcos shot and accepted it; investigate whether that explains the user-observed defect rather than assuming it does.

## Known limitations and outstanding work

1. **Editorial and spatial diagnosis:** pending investigation 1. Trace source selection, excerpt, briefing, script, references, keyframes, generated clips and edit. Establish the earliest observable defect.
2. **Configuration audit:** pending investigation 2. Empty fields may inherit defaults or be inapplicable. Reconstruct actual effective values and consumption, not just visible UI fields.
3. **Speech/subtitles:** the latest native Agent reported measured timing applied only to Marcos's shot. Other shots used mechanical timing because of a word mismatch or uncertain boundaries. This report is a starting point; inspect retained evidence. Local ASR does not establish voice identity, acting or lip sync.
4. **Audiovisual review:** not conclusively validated. Native visual reviewers worked from sampled frames. Do not relabel visual approval or transcript agreement as audio/performance approval.
5. **Validation debt:** [native-speech-review.md](../../testing/native-speech-review.md) records 91 focused tests passing and broader host-consistency failures involving fixtures/schema descriptions for seven workflow-access tools. Those tests were not rerun during this handoff, and their results do not certify every current dirty file. Diagnose current relevance before proposing repairs.
6. **Uncommitted implementation:** the running local work is not represented by HEAD alone. Review and publication are separate future tasks, not prerequisites to read-only investigation of this checkout. Do not commit all dirty files indiscriminately.
7. **Authentication history:** earlier in this conversation, native SDK calls failed with expired/revoked OAuth errors; the official Claude CLI succeeded, and restarting the application allowed the same native session to proceed. Root cause was not conclusively isolated. No credentials are included here; no fresh inference authentication test was made for this handoff.
8. **Staleness and unused assets:** the native workflow snapshot retains storyboard stale flags and unused asset definitions. Investigate their actual effect; do not delete or regenerate merely to make a status screen clean.

Existing implementation evidence: [native-mcp-production.md](../../testing/native-mcp-production.md) and [native-speech-review.md](../../testing/native-speech-review.md). Their historical results must remain distinct from current checks.

## Local-change record

- [local-changes.json](local-changes.json): branch, full HEAD, timestamp, existence, size and SHA-256 for 83 changed/new non-ignored files present before this handoff: 39 tracked modifications and 44 untracked files.
- [git-status-before.txt](git-status-before.txt): status before handoff files were written; directory entries aggregate some untracked files.
- [git-diff-stat-before.txt](git-diff-stat-before.txt): tracked diff statistics against HEAD; excludes untracked file contents.
- [handoff-validation.json](handoff-validation.json): final comparison of baseline hashes, file/link checks and handoff inventory.

The manifest records file identities, not authorship. It includes work from different origins and must not be interpreted as changes all made by this session. The tracked changes touch native Agent instructions, MCP/tool exposure, speech/presentation, image edits, routes, local launcher/dependencies, UI summaries/localization and tests, alongside other existing changes. Untracked files include implementation, tests, research, plans and user material.

No raw patch, database copy, `.env`, access key or media archive is included. Ignored files and files outside the checkout are not comprehensively inventoried. Final videos have separate hashes in the runtime snapshot. This package is not a backup and does not reproduce the complete environment in a fresh clone. Use the existing checkout/data root for the audits; preserve them until conclusions are recorded.

## Session boundaries for the investigators

- Read the applicable AGENTS.md and the assigned prompt; use native MCP read interfaces where available.
- Keep production ownership in the ArcReel framework. No external harness or replacement workflow.
- Audit 1 owns workflow/editorial causality. Audit 2 owns configuration/effective-value causality. Cross-reference findings without editing each other's report.
- Write outputs under separate new audit directories. Record start/end timestamps and recheck relevant hashes if concurrent changes are suspected.
- Report exact verified facts, hypotheses and inaccessible evidence separately.
- Do not reuse the prior USD 22 or USD 20.10 scopes. No paid activity is authorized by this handoff.
- No Git publication, configuration mutation, authentication changes or service restart is required to begin the read-only investigations.
