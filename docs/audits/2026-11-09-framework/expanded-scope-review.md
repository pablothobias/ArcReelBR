# Expanded review beyond the initial instruction/adapter list

> Stage-5 update: [R12 implementation results](../../plans/native-framework-boundary/stage-5-results.md) records native inherited-route validation and passing tests. Earlier zero-pricing observations describe pre-fix source; current configuration readiness and stage 6 remain separate/pending.

Date: 2026-11-09. Baseline `a779b5d51`, current revision `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. Trigger: the user challenged the completeness of the consolidated list. No source correction, production operation, provider call or host configuration change was authorized or performed.

## Why the prior conclusion was too narrow

The prior checklist mapped known W01-W08/R07-R11 findings and 16 profile clauses. That establishes completeness within those clauses, not discovery completeness across the fork. The added audit documents themselves are untracked and absent from the baseline diff. A pre-existing skill-disable modification is also outside the committed diff and remains untouched.

The broader pass starts from the actual changed-path inventory rather than searching only already-known findings. [The complete path inventory](expanded-change-inventory.json) contains 860 paths:

| Category | Paths | Coverage meaning |
|---|---:|---|
| Frontend visual snapshots | 490 | Snapshot assets; not 490 independent runtime changes. No fresh pixel review. |
| Documentation and retained evidence | 121 | Historical director proposals and active-entry references were distinguished; no blanket deletion. No revalidation of all historical live evidence. |
| Tests | 87 | Test-source changes, not runtime policy by themselves. Targeted cases executed below. |
| Backend libraries, tools and scripts | 85 | Executable-source changes screened by owning subsystem; findings and behavioral qualifications below. Includes reused unchanged source analysis of MCP and offline diagnostic tools. |
| Frontend sources, assets and configuration | 48 | Production-relevant transport/presentation/tool-label/speech-rate diffs inspected; branding/styling not freshly certified visually. |
| Production instructions/external package | 11 | Existing W01-W08 analysis reused; public official skill route rechecked. |
| Root assets/repository configuration | 13 | Manifest and optional speech dependency identified; repository/build assets do not establish another production director. No dependency installation. |
| Public documentation | 5 | Provider/deployment translation files, outside active production policy. |

This is an inventory plus a source-directed review, not a line-by-line proof that every changed path is defect-free.

## Owning seams checked and actual behavioral changes

| Area | Evidence and comparison | Consequence for the list |
|---|---|---|
| Native Agent lifecycle/context | New conversation-language module, session queue/replay changes, options assembly and language template. ADR 0122 explicitly adopts `snapshot=False` and documents refreshing user-memory context on reconnect, prompt-prefix/cache/token/fingerprint tradeoffs and pending live-model validation. Independent details: [runtime review](expanded-runtime-review.md). | Broader than changing UI labels or translating replies. Preserve the authorized product-language objective, but record actual runtime behavior and the limits of equivalence claims. It is not an independently proven external director or automatic removal target. |
| Internal text execution | New Claude subscription backend/factory/validator path; quota-pause error propagation in text generation, tool runtime and generation results. | It changes model execution and error/recovery semantics, not just auth labels. Preserve the native backend customization; do not misdescribe it as unchanged upstream behavior. Independent review distinguishes isolated no-tool SDK calls from another creative Agent. |
| Speech/presentation after application | `presentation_read_model.py:296-320` reloads persisted timing on ordinary reads when its source basis matches. `artifact_planner.py:1638-1650,1693-1705` reconstructs measured artifacts/current state. `speech_presentation.py:403-419,461-462` validates and records measured timing. | Removing W08 does not revert previously applied timing. Optional timing affects native timeline/read/render behavior after use, not only the new MCP handler. Preserve that product capability and its provenance/invalidation rules. Existing measured-timing read/render tests passed below. No new defect established in those cases. |
| Gemini generation/recovery | `gemini.py:180-225` limits application retries to known-unsent request failures; `gemini_shared.py:186-204` adds non-idempotent client behavior and disables SDK retries for that route. `media_generator.py:188-190` excludes ambiguous/received response errors from reference-reduction retry. | Existing preservation entry must explicitly include native retry/submission behavior, not merely MIME/accounting. No independent external policy layer was found here. Preserve protection against repeated potentially paid submissions. |
| Image request limits/catalog | `media_generator.py:742-749,791` passes catalog output bounds; `custom_provider/backends.py:142-146` injects bound facts; Gemini sends max_output_tokens at `:197-204`; catalog-core adds bound fields. | Real request-shape change. Preserve as an explicit native customization with model-bound support, not a claim that provider behavior is unchanged or every image backend implements the field. |
| Quotation/settlement | New image usage estimates and uncertainty, failure-response settlement, provider-response evidence and modality aggregation. Reviewed `ledger.py`, `metering.py`, `usage_repo.py`, cost estimator and relevant Gemini/custom-provider diffs. | These changes affect billable failure reporting and estimates. Existing W04/R08 removes an imposed quotation sequence, not this native accounting behavior. Targeted Gemini tests passed; no whole-provider correctness certification. |
| Native video admission | Diffs in `media_tools/videos.py` and `services/admission/video_quote.py` primarily translate guidance/errors while retaining admission/confirmation logic. | Do not mistake translated guidance about inherited confirmation and whole-batch submission for a newly inserted workflow. No additional removal target established here. |
| Content and prompt templates | pt-BR language normalization, reading units/speech rates, preservation of explicit Brazilian project language during overview generation, and output-language filter in script/visual templates. | These intentionally alter generation instructions for product localization. Preserve them; “Codex must not interfere” is not a reason to remove product-owned language policy. No claim of identical media output or measured creative quality. |
| Frontend consumers | HTTP/SSE Accept-Language normalization; added audio_measured type; new tool summaries; speech-rate language mapping; remaining inspected timeline/Settings changes are presentation/layout. | Access/display integration, not another production scheduler. Current configuration/authentication UI mismatch stays with the separate configuration investigation. |
| External director links | Root mission/resources are learning references. The old production README and delegation research explicitly identify the director proposal as historical. | Preserve history. Retire actual active package/protocol links as W01/W02 require; searching the word Codex in historical plans is insufficient evidence for more removal. |

## Verification in this expanded pass

53 selected existing cases passed, one existing SQLite expression-index reflection warning, 7.36 seconds. [Captured output](expanded-review-pytest-output.txt).

```text
python -m pytest -q -p no:cacheprovider
  tests/unit/lib/backends/image_backends/test_gemini_billing.py
  tests/unit/server/agent_runtime/test_options_assembler.py
  tests/integration/server/services/presentation/test_presentation_read_model.py::test_measured_timing_survives_reads_and_currency_reconstruction
  tests/integration/server/services/presentation/test_timeline_final_cut.py::test_measured_subtitles_render_only_inside_measured_interval
```

Executed using the existing main-checkout virtual environment with dotenv loading and bytecode writes disabled. Existing fixtures isolate roots/databases; provider boundaries are faked and render testing uses local fixtures. No real model/ASR/provider request. These tests supplement, not replace, the prior 69 adapter cases and 13 isolated reproductions, which were not repeated.

Independent runtime review is separately documented and any new defect must be distinguished from the intentional behavioral changes above. No additional removal target is inferred merely to increase the list. Conversely, preserving a product feature is not a guarantee that its implementation or fallback assumptions are correct.

## New actionable finding: R12

[XR05's isolated follow-up](expanded-runtime-review.md#xr05-follow-up-inherited-cloud-mode-plus-zero-multiplier-reproduced) confirms that the real no-stored-key configuration selects Agent pricing multiplier 0.0 while each synthetic cloud-route flag survives SDK environment assembly. Three cases reached an intercepted spawn boundary; no subprocess, provider, credential check or inference ran. Inheritance predates the local zero-price rule, but the new rule assumes a subscription route that this general launch path does not enforce. The env-i launcher protects only its entry.

Register R12 as a targeted route/pricing adjustment while preserving subscription operation. No actual cloud charge or ledger incident is established. Current launch-state verification is left to the parallel configuration audit. This is a new confirmed interaction that was missing from the initial list; XR01-XR04 and the broader speech/Gemini changes are explicitly described product customizations, not additional removals invented to inflate the findings.

Updated disposition counts: eight removal mechanisms, five confirmed adjustment items (R07, R09, R10b, R11, R12), and four persistence-contract decisions (R10a/c/d/e). Preserved product changes have the qualifications above. The framework's validated status is not an exemption from examining locally altered runtime behavior.
