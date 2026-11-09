# Stage 6: speech-inspection persistence contract

Date: 2026-11-09. Base revision `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`, retaining prior local stages. The user authorized stage 6/R10e and results before stage 7. Changes remain local and uncommitted; stage 7 has not started.

## Confirmed contract and changes

R10e is resolved by describing and testing the existing native contract, not by replacing materialization or making inspection read-only.

| Operation | Native contract |
| --- | --- |
| Inspection with `apply_timing=false` | Does not apply new measured timing. May materialize current subtitle, presentation and manifest artifacts before recognition. |
| Inspection when ASR is unavailable | Can return `speech_review_unavailable` after successful materialization. Failure does not promise zero writes. |
| Inspection with eligible previous measurements | Retains still-valid applied timing. Normal native invalidation for changed source/media remains in force. |
| Explicit application with `apply_timing=true` | Existing eligibility, identity and uncertainty checks continue to govern application. |

The shared tool description exposes this contract to both hosts; the parameter description, public installation guide, native MCP testing guide, speech testing guide and optional edit-video guidance now agree. The public guide also correctly lists `language` as required, matching the existing request schema. Earlier wording suggesting unavailable recognition always leaves the mechanical draft unchanged was narrowed to the actual guarantee: no new measured timing is applied.

The handler AST is unchanged. Request semantics are unchanged except the parameter description. Native materialization, recognition implementation, timing eligibility/invalidation, canonical text, source media and application evidence remain owned by the framework. No mandatory ASR gate, second materializer, new external orchestration or paid fallback was added.

## Isolated regression evidence

Four new parametrized cases exercise the real speech handler, presentation reader, TTS resolver and persistence with temporary local video/audio, across available/unavailable ASR and absent/present prior measured timing. The prior-measured branch first applies eligible timing through the real handler. Only the third-party recognizer is replaced with a synthetic local stub; no model download or provider query occurs. Local ffmpeg extraction and native media digests remain real.

Assertions cover materialization without prior presentation artifacts, retained eligible measurements, no new application evidence on inspection, canonical script/media stability and stable content on a repeated identical inspection. Stable hashes are content evidence, not proof of zero filesystem activity. Available-ASR output is synthetic and does not validate real transcription quality, Portuguese recognition, lip sync, emotion, speaker identity or editorial acceptance.

These tests confirm preserved behavior rather than demonstrate a runtime defect fixed in this stage. The four focused cases passed before the final description edits and are included in the final suite count below, not counted twice.

## Validation results

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHON_DOTENV_DISABLED=1 /Users/pablo.carminatti.br/Projects/ArcReelBR/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/integration/server/media_tools/test_speech_review.py \
  tests/integration/server/services/presentation/test_presentation_read_model.py \
  tests/integration/server/services/presentation/test_timeline_final_cut.py \
  tests/unit/lib/speech/test_audio_review.py \
  tests/unit/lib/speech/test_speech_presentation.py \
  tests/integration/server/agent_toolset/test_host_consistency.py \
  tests/unit/test_public_contract.py \
  tests/unit/scripts/test_agent_profile_lint.py \
  tests/unit/lib/prompts/test_brazilian_content.py \
  tests/unit/lib/agent/test_profile_manifest.py
```

- **1,203 passed in 41.90s**, including native measured read/render coverage and both-host contracts. One SQLAlchemy warning reports unsupported reflection of the expression-based `idx_tasks_dedupe_active` index; no test failed. [Full output](evidence/stage-6-pytest.txt).
- Ruff check and format check on the three changed Python files passed. [Output](evidence/stage-6-lint.txt).
- Basedpyright on those three files: **0 errors, 0 warnings, 0 notes**. [Output](evidence/stage-6-types.txt).
- Native Agent profile lint passed in a disposable data/database root. [Output](evidence/stage-6-profile-lint.txt).
- Scope comparison: **4,711 protected tracked files unchanged**, handler AST identical and request-schema behavior unchanged. [Scope evidence](evidence/stage-6-scope-check.json), [baseline](evidence/stage-6-baseline.json).
- `git diff --check` passed. No complete gate was requested or run.

## Preservation and remaining boundary

Product customizations, including pt-BR content and optional measured timing, remain intact. Configuration/authentication source and current settings were outside this stage; no credentials, installed skills, live process, production artifacts or historical evidence were altered. No real ASR/model, account-readiness check or paid generation was run. The separate configuration investigation remains separately owned. Stage 7 requires the user's next authorization.
