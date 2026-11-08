# Ticket #5 validation

Baseline: `401488f40`. Scope: explicit Brazilian Portuguese project content, English technical prompts, existing UI locales preserved.

| Criterion | Evidence |
| --- | --- |
| Explicit normalized content language | REST and tool create/edit/read, ProjectOverview schema and overview-regeneration preservation in `test_projects_content_language.py`, `test_brazilian_content.py`, and ProjectManager integration tests |
| Portuguese reading units and configurable rates | Word-count and 2.5-word/s estimate tests, explicit project override; legacy unknown-language fallback retained |
| Technical and literal creative language separation | Shared output policy reaches drama, narration, reference-video, ad and overview templates; literal dialogue/source anchors/asset names preserved |
| Existing project/language compatibility | Regression suite: 540 passed across prompt, text metrics, speech rate, tool runtime, project routers and ProjectManager tests |
| Deterministic source-to-structured example | Portuguese source and structured drama/narration/reference fixtures retain intended speech; reference validator rejects translated dialogue |

Commands:

- `uv run python -m pytest tests/unit/lib/prompts tests/unit/lib/infra/test_text_metrics.py tests/unit/lib/speech/test_speech_rate.py tests/unit/server/test_tool_runtime.py tests/integration/server/routers/test_projects_content_language.py tests/integration/lib/project/test_project_manager.py -q --no-cov`: 540 passed.
- Independent reviewer ran `uv run python -m pytest tests/unit/lib/prompts/test_brazilian_content.py tests/integration/server/routers/test_projects_content_language.py tests/unit/lib/infra/test_text_metrics.py tests/unit/lib/speech/test_speech_rate.py -q`: 82 passed.
- `pnpm exec vitest run src/components/shared/SpeechRateField.test.tsx`: 11 passed, also repeated by independent reviewer. Coordinator reran under supported Node 24.22.2.
- `pnpm typecheck`: passed under Node 24.22.2.
- `npx react-doctor@latest --verbose --scope changed`: 100/100, no findings in two changed frontend files.
- Owned Python Ruff checks, test audit and whitespace checks passed.

Independent Codex reviewer: `implement_mcp`, separate from the backend implementer `implement_ptbr` and coordinator's frontend implementation. No actionable specification, correctness or standards findings. A stale script-generator comment found by coordinator was corrected without changing behavior.

These deterministic checks prove the language contract and literal preservation paths. They do not prove live model compliance, native speech quality or rendered subtitle timing. Those are acceptance criteria of later production/review tickets, not claimed here. No paid requests.
