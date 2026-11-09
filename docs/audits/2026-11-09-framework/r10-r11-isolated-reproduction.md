# R10/R11 isolated reproductions

> Stage-7 closure (latest): [integrated results and disposition of all 17 entries](../../plans/native-framework-boundary/stage-7-results.md) records completed local stages, the complementary safe R12 MCP error correction, preserved customizations and 1,472 passing cases. Two pre-existing Web test failures reproduce on the base revision and remain recorded. Earlier pending-stage/recommendation statements below are historical. No commit; current host/configuration readiness remains separate.

> Stage-6 update (latest): [R10e contract and validation](../../plans/native-framework-boundary/stage-6-results.md) confirms inspection may materialize before ASR, including unavailable recognition; `apply_timing=false` skips new measurements and preserves still-valid prior timing. Native materialization is unchanged; 1,203 selected cases pass. Earlier pending-stage statements below are historical. Configuration readiness remains separate and stage 7 has not started.

> Stage-4 update: [R11 implementation results](../../plans/native-framework-boundary/stage-4-results.md) records transactional MCP character-image upload and passing regression coverage. Earlier race outcomes describe pre-fix source; R12/stage 5 remains pending.

> Stage-3 update: [implementation results](../../plans/native-framework-boundary/stage-3-results.md) records R10a+b/c/d corrections and tests. Earlier reproduction outcomes describe the pre-fix source. R10e materialization is preserved; R11/R12 are still pending.

Date: 2026-11-09. Product revision: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. This follows [the adapter assessment](mcp-adapter-assessment.md) and updates [the register](refactor-register.md). No product corrections were implemented. All mutations below occurred in disposable test projects/databases.

## Result

**13 cases passed**, with one existing SQLite expression-index reflection warning, in 2.79 seconds. The cases assert the problematic outcomes, not corrected behavior. This confirms the conditional effects in R10 and reproduces R11's false-success/orphan-reference outcome under controlled concurrent deletion. It does not establish an incident in an existing production project or an audiovisual quality regression.

| Subcase | Reproduction and observation | Classification and proposed disposition |
|---|---|---|
| R10a: cost-reader persistence | Invoke the real shared `get_project_costs` declaration against a bound legacy reference-video script. The call succeeds and persists removal of retired shot-duration/override fields. `project.json`, the 8-second unit duration and `Olá, Ana!` remain unchanged. Both real native cost computation and a computation stub give the same result. With an already adopted script, bytes remain unchanged. | Confirmed conditional filesystem side effect, not creative rewriting or evidence that native migrations are defective. Define the diagnostic contract and choose the appropriate native reader; retain compatibility migrations and pt-BR. |
| R10b: cancellation | Pause the real `_persist_script_json` before its write. Cancel `get_project_costs`. Its task raises `CancelledError` while the worker remains paused and the script still has its original bytes. Releasing the worker then persists the migration after the caller has finished. | Confirmed cancellation-boundary defect for the new cost reader when a legacy migration is needed. A control using existing `run_sync_transaction` over the same real reader remains pending until the write finishes and only then propagates cancellation. Proposed correction: use an appropriate read-only path or preserve native transaction semantics, depending on intended contract. No correction applied. |
| R10c: storyboard image-edit preview | Call the real `edit_images(preview=true)` handler against a bound legacy reference script and a missing storyboard target, with a local capability fake. The handler returns without a top-level problem after persisting the legacy migration. No batch is submitted. | Confirmed script-write effect before preview completion, even when the target cannot execute. The schema describes read-only target validation and no image writes; the observed write is a script migration, not an image edit. Clarify the intended persistence contract before choosing a narrow adjustment. |
| R10d: storyboard-quote qualification | A correctly configured `reference_video` project is rejected **before** loading/migrating its script; bytes remain unchanged. With the same reference skeleton but project mode `storyboard`, the call reads/migrates first and then rejects the incompatible skeleton. | Narrower than the earlier generic risk statement. Do not claim every valid storyboard quotation migrates scripts. The demonstrated quote write concerns an incompatible project/script combination. Whether a rejected quote should adopt a legacy script is a contract decision, not grounds to remove native migration support. |
| R10e: speech inspection | Use the real presentation materialization/persistence service with fake local media, a duration probe and local ASR stubs; call `review_speech(apply_timing=false)`. Both successful ASR and unavailable ASR cases create presentation and subtitle JSONs and update `.arcreel_artifacts.json`. The unavailable case returns `speech_review_unavailable` **after** those writes. | Confirmed native materialization before ASR, not measured-timing application. Script, audio and video bytes remain unchanged, no `speech_reviews` evidence is created, and the second identical call leaves content hashes stable. Do not remove this inherited materialization capability as a regression. Clarify the inspection contract; a strictly read-only design would need an explicit decision. |
| R11: reference-upload race | Start real shared `upload_reference(character_image)` with a valid image and existing Ana. Pause image normalization after the existing-host check, then call real `ProjectManager.delete_asset('demo', 'characters', 'Ana')` on another worker. After deletion completes, resume normalization/upload. MCP reports `success=true`, the reference file exists, and Ana is absent from project metadata. | Confirmed reproducible false success/orphan reference under the controlled race. Promote from unverified risk to confirmed adapter-contract defect. Proposed correction: make the retained existing-host guarantee valid through commit, with coherent refusal/cleanup, preserving intentional Web semantics, native deletion and supplied references. |
| R11 control | Same upload and scheduling barrier, with no concurrent deletion. | Success includes a persisted file **and** a character metadata reference. The race result is not caused by invalid image bytes or an initially missing character. |

## Isolation and evidence boundaries

The retained [reproduction source](reproduce_r10_r11.py) imports the existing `access` fixture. Root test fixtures pin process-local data/Claude directories and SQLite databases, and per-case fixtures provide disposable projects. Dotenv loading and bytecode writes were disabled. No existing production project was read or changed, and no live application endpoint, provider, real ASR or model was invoked.

Cost-read cases include real native computation with no configured provider, as well as the stubbed-computation controls. Cancellation cases stub cost computation after the read, but use actual `ProjectManager.load_script`, its script lock and its real JSON persistence; only the pre-write scheduling barrier is substituted. R11 uses a real image normalizer, metadata setter, file write and native deletion transaction. The synchronization wrapper pauses normalization without replacing its implementation. No `KeyError`, successful outcome or orphan file is fabricated by a test double.

Speech cases reuse the repository's existing provenance fixture and native reader; only duration measurement, settings lookup and ASR are local substitutes. This tests persistence ordering, not recognition quality, media decoding or Portuguese speech accuracy. The preview case uses a capability fake and a missing target; it does not establish a successful preview of editable current media. These limits do not weaken the observed script write but limit broader claims.

Controlled barriers establish a possible supported interleaving, not its production frequency. They do not simulate cancellation of an actual connected MCP client or assert that a specific client propagates disconnects into this handler. The R10b finding is specifically the handler-task cancellation boundary.

## Running again

The audit script is kept outside the normal test suite. A temporary copy under `tests/integration/server/` lets pytest load the repository's fixtures/plugins; that copy was removed after execution. No permanent application test or product file was modified.

From this worktree, the executed commands were:

```bash
cp docs/audits/2026-11-09-framework/reproduce_r10_r11.py tests/integration/server/test_audit_r10_r11_tmp.py
PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -s -p no:cacheprovider tests/integration/server/test_audit_r10_r11_tmp.py
rm tests/integration/server/test_audit_r10_r11_tmp.py
```

The first development run passed 11 cases. The final run expanded the cost-reader cases to cover real computation as well as the stub, yielding 13 passing cases. No source changes occurred between these runs. [Final captured output](r10-r11-pytest-output.txt) includes the observations and timing; the expected missing-provider/local frontend warnings are test-environment facts, not production failures.

## List update

- **R10:** verification complete for the reproduced cases. Separate confirmed native side effects (R10a/c/e), the confirmed handler cancellation defect (R10b), and the quote-route qualification (R10d). Keep correction proposals narrow; no wholesale migration, speech, Portuguese-content or presentation removal.
- **R11:** promote to a confirmed concurrency/contract defect, reproduced using native deletion. Retain the upload and deletion capabilities; adjust the adapter guarantee rather than replacing the framework.
- Production incident attribution, audiovisual acceptance and actual client-disconnect behavior remain untested. None is required to recognize the reproduced contract defects.
