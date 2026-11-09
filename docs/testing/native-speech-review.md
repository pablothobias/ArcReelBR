# Native speech review and measured subtitles

## Implemented boundary

`review_speech` is exposed through the existing shared toolset, both embedded and remote MCP. It analyzes one selected video unit or its selected TTS narration, compares blind recognition with canonical speech and optionally applies measured intervals. It does not synthesize, replace or retime audio/video, rewrite speech, or implement an external production harness.

Setup: install `uv sync --extra speech-review`, preinstall a faster-whisper model, and set `ARCREEL_SPEECH_REVIEW_MODEL` to its local directory. The local launcher includes this extra. Restart the application to load code/configuration. The tested model is `Systran/faster-whisper-small` at revision `536b0662742c02347bc0e980a01041f333bce120`; its pinned model card declares MIT. Review performs no model download and accepts no script prompt. Units are limited to 120 seconds and CPU inference is serialized.

Call with `unit_id`, `language` (e.g. `pt`), optional `version` and `variant`, and `apply_timing=false` for inspection. Set `apply_timing=true` for correction. External MCP also requires `project`. Application is conditional on full word agreement, confidence/bounds checks, audible presentation track and current selection. Failure leaves canonical text and timing unchanged. Changed media/text rejects an in-flight application; later reads fall back to mechanical timing when old measurements no longer match.

Evidence JSON is retained under project `speech_reviews/` by digest before a successful application. Timings persist in the canonical subtitle artifact, with its source basis. The existing presentation transaction owns registration and rollback. The main Agent's edit-video skill consumes the tool; its read-only visual reviewer remains read-only.

## Actual local production exercise

Project `br-framework-problema-resolvido`, native Agent session `699d2985-0cc3-480b-a746-97f9a1d8949b`. The application was restarted. Codex sent the requirement through session MCP; the embedded Agent reviewed retained units, applied eligible timing and rendered through the existing framework. No media-generation/TTS/evaluator API spend was authorized or made in this exercise.

- E1S04 question: detected 2.80–4.38 seconds in its source clip.
- E1S05 answer: detected 2.03–3.61 seconds in its source clip.
- Canonical words were preserved. The second clip starts at timeline time 5.167 seconds, placing its subtitle at approximately 7.197–8.777 seconds in the final cut.
- Timeline `tl-909fe8de`, revision 3; burned-subtitle final cut version 2; duration 15.333 seconds. Native render acceptance reports matching video/audio duration and no render warnings.
- Actual transcript and MCP receipts remain in the private editorial evidence directory for this project. Applied review evidence lives inside the project.

These are model-estimated word boundaries, not independent ground-truth measurements. The render test verifies that measured intervals are burned at the correct timeline positions, including a 0.5-second source trim; it does not establish the ASR's physical onset accuracy.

## Verification and remaining work

48 speech/presentation tests passed, including wrong/missing/extra words, uncertain bounds, stale media/text, persistence and currency reconstruction. Fifteen host-consistency cases for `review_speech` passed. Twenty-six timeline/final-cut/Jianying/placement cases passed, including actual frame decoding before/during/after a measured subtitle. Two handler/setup cases also passed, including the native application transaction under the event-loop blocking guard (91 focused tests in total). Targeted Python/frontend type checks, profile lint and dependency hygiene passed.

The broader host-consistency failures previously exposed incomplete sample inventory/schema descriptions for seven workflow-access tools. On 2026-11-09, the samples, shared field descriptions, isolated project root and per-call metadata timestamp comparison were corrected. The full host-consistency file then passed all 1,011 cases. The other 114 cases in the selected speech, workflow-access, session, image-edit, project-router and presentation/final-cut files passed in the preceding combined run and were unchanged by the final timestamp-path correction. This validates 1,125 selected backend cases, not the complete backend suite. Targeted basedpyright and Ruff checks passed. The frontend typecheck and 2,974 related tests passed before these backend/documentation-only fixes; their inputs were unchanged. Both documentation locales built successfully.

Voice performance, identity and lip synchronization remain unassessed. Existing [SyncNet qualification](../plans/brazilian-production/evidence/10-audiovisual/syncnet-local-qualification.md) and [negative controls](../plans/brazilian-production/evidence/10-audiovisual/syncnet-negative-controls.md) establish only exploratory measurements. They do not justify a production pass/fail threshold or commercial checkpoint clearance. Do not turn a transcript match into audiovisual approval. This implementation closes the native subtitle-timing path and actual-speech evidence path, not the complete autonomous audiovisual-review requirement.
