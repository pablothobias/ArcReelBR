# Implementation evidence matrix

Updated: 2026-11-08. Baseline: `401488f40` on `main`. Spec #2 remains open.

GitHub bodies, comments, assignees, native dependencies and sub-issues were read directly before this checkpoint. Initial state: all ten tickets were open. Current closures and evidence appear below. No paid media/API calls at the latest pre-submission checkpoint. The owner subsequently approved USD1.95 for the separate #9 capability sample, reserved in private Codex recovery state. Existing uncommitted teaching/planning material is preserved.

This is a coordination checkpoint, not production state. ArcReel remains authoritative for projects, scripts, assets and jobs.

| Ticket | Open dependencies | Area | Owner | State | Verification |
| --- | --- | --- | --- | --- | --- |
| [#3](https://github.com/pablothobias/ArcReelBR/issues/3) | None | Remote MCP and existing session service | implement_mcp; independent review implement_text | Closed, remote commit `5e6626de5` | See criterion evidence below |
| [#4](https://github.com/pablothobias/ArcReelBR/issues/4) | None | Text backends, resolution, subscription accounting | implement_text; independent review implement_ptbr | Closed, remote commit `ecd6ead43` | See criterion evidence below |
| [#5](https://github.com/pablothobias/ArcReelBR/issues/5) | None | Content language, speech rates, prompt authoring | implement_ptbr; independent review implement_mcp | Closed, remote commit `7b012052e` | See criterion evidence below |
| [#6](https://github.com/pablothobias/ArcReelBR/issues/6) | None | Authenticated image uploads and generation preview | Coordinator | Partial local evidence; AI-generated image pending | See criterion evidence below |
| [#7](https://github.com/pablothobias/ArcReelBR/issues/7) | None | Reference dossier and formal episode handoff | implement_text; independent review implement_ptbr | Closed, remote commit `79e7b798b` | See criterion evidence below |
| [#8](https://github.com/pablothobias/ArcReelBR/issues/8) | None | Codex directing skill and recovery record | implement_ptbr; independent review implement_mcp | Closed, remote commit `7f704b670` | See criterion evidence below |
| [#9](https://github.com/pablothobias/ArcReelBR/issues/9) | None | Provider configuration and bounded media sample | implement_mcp; independent review implement_ptbr | Closed, remote commit `fa36d7264` | See criterion evidence below |
| [#10](https://github.com/pablothobias/ArcReelBR/issues/10) | None | Audiovisual evidence and correction handoff | implement_mcp; independent review implement_ptbr | Partial local evidence; full AV judgement missing | See criterion evidence below |
| [#11](https://github.com/pablothobias/ArcReelBR/issues/11) | #6, #10 | Real pilot and delivery | Coordinator, pending scheduling | Pending | See criterion evidence below |
| [#12](https://github.com/pablothobias/ArcReelBR/issues/12) | #11 | Two-episode sample and collection readiness | Coordinator, pending scheduling | Pending | See criterion evidence below |

## Ticket #3

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Configure the existing authenticated MCP connection without exposing access tokens or adding credential-management tools. | Completed required contract and live checks as specified | [Session validation](evidence/03-session-validation.md): deterministic tests and real authenticated MCP delegation/reconnect, independent review, remote commit `5e6626de5` |
| Expose existing session service operations for send/create, state and cursor-based entries, pending questions, answers and interrupt. | Completed required contract and live checks as specified | [Session validation](evidence/03-session-validation.md): deterministic tests and real authenticated MCP delegation/reconnect, independent review, remote commit `5e6626de5` |
| Preserve ownership checks, accepted versus queued messages and client-key idempotency; a turn result alone never means the session or production is complete. | Completed required contract and live checks as specified | [Session validation](evidence/03-session-validation.md): deterministic tests and real authenticated MCP delegation/reconnect, independent review, remote commit `5e6626de5` |
| Demonstrate a no-media local delegation, question/answer flow and reconnect; repeated send does not duplicate accepted work. | Completed required contract and live checks as specified | [Session validation](evidence/03-session-validation.md): deterministic tests and real authenticated MCP delegation/reconnect, independent review, remote commit `5e6626de5` |
| Reuse existing production tools, confirmation parameters and media-batch polling; keep the current harness. | Completed required contract and live checks as specified | [Session validation](evidence/03-session-validation.md): deterministic tests and real authenticated MCP delegation/reconnect, independent review, remote commit `5e6626de5` |

## Ticket #4

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Add a selectable TextBackend through existing resolution and preserve simple/complex tiers and current callers. | Completed required deterministic and actual subscription checks | [Text validation](evidence/04-text-validation.md): real structured/image/consumer calls, independent review, remote commit `ecd6ead43` |
| Use isolated sessions without production tools; preserve structured-schema validation, image inputs, truncation handling and usage accounting. | Completed required deterministic and actual subscription checks | [Text validation](evidence/04-text-validation.md): real structured/image/consumer calls, independent review, remote commit `ecd6ead43` |
| Use official local authentication; never extract OAuth tokens or silently fall back to a paid API key. | Completed required deterministic and actual subscription checks | [Text validation](evidence/04-text-validation.md): real structured/image/consumer calls, independent review, remote commit `ecd6ead43` |
| Record subscription token usage without fabricating per-token API charges; surface quota exhaustion as a resumable pause condition to the director. | Completed required deterministic and actual subscription checks | [Text validation](evidence/04-text-validation.md): real structured/image/consumer calls, independent review, remote commit `ecd6ead43` |
| Verify structured text and an image-input operation, timeout/failure handling and one real existing text consumer; retain existing provider behavior. | Completed required deterministic and actual subscription checks | [Text validation](evidence/04-text-validation.md): real structured/image/consumer calls, independent review, remote commit `ecd6ead43` |
| Honor ADR 0124 while preserving credential separation and the original Agent conversation-model boundary. | Completed required deterministic and actual subscription checks | [Text validation](evidence/04-text-validation.md): real structured/image/consumer calls, independent review, remote commit `ecd6ead43` |

## Ticket #5

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Accept and consistently normalize an explicit Brazilian Portuguese content language through relevant project/tool/schema paths. | Completed required contract and live checks as specified | [Language validation](evidence/05-language-validation.md): deterministic contract fixtures, compatibility regressions, independent review, remote commit `7b012052e` |
| Use suitable Portuguese reading units and configurable speech-rate behavior rather than the Chinese unknown-language fallback. | Completed required contract and live checks as specified | [Language validation](evidence/05-language-validation.md): deterministic contract fixtures, compatibility regressions, independent review, remote commit `7b012052e` |
| Separate technical prompt prose from literal spoken content in the existing supported generation routes. | Completed required contract and live checks as specified | [Language validation](evidence/05-language-validation.md): deterministic contract fixtures, compatibility regressions, independent review, remote commit `7b012052e` |
| Verify create/edit/read and representative drama, narration and reference-video prompt paths; existing languages and projects retain compatibility. | Completed required contract and live checks as specified | [Language validation](evidence/05-language-validation.md): deterministic contract fixtures, compatibility regressions, independent review, remote commit `7b012052e` |
| Demonstrate a source-to-structured-content example with English instructions and unchanged intended Portuguese speech using deterministic fixtures. | Completed required contract and live checks as specified | [Language validation](evidence/05-language-validation.md): deterministic contract fixtures, compatibility regressions, independent review, remote commit `7b012052e` |

## Ticket #6

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Exercise existing authenticated uploads for one reusable asset and one storyboard; preserve formal registration, version history and currency. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Partial: real authenticated synthetic PNG asset/storyboard uploads, versions and currentness verified; actual AI-generated input remains pending. [Evidence](image-handoff.md) |
| Confirm downstream request preview resolves the selected image and correct asset identity; copying files alone does not satisfy ingestion. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Partial: shared generation-input assembler and prompt preview resolve Ana reference; exact provider request preview pending. |
| Use existing transport where possible; add only a narrow wrapper if required for a reproducible Codex handoff. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Existing authenticated multipart routes exercised successfully; no new wrapper or store needed. |
| Record whether the local image handoff is practical; preserve the agreed Nano Banana 2 fallback without a new asset store. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Local file transport practical; AI generation availability not yet verified. Exact Nano Banana 2 fallback preserved in runbook. |
| Any image-generation call uses the applicable approved usage policy; no paid provider request without an explicit allowance. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | No image-generation/provider call made; no numerical allowance available. |

## Ticket #7

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Read actual reference content and record source identity, access date and observed events; titles/descriptions alone are insufficient. | Actual source, embedded session and independent project/ledger verification | Passed; [reference handoff](reference-handoff.md), remote `79e7b798b` |
| Find a verified compatible replacement when needed; if none is accessible pause that item rather than invent reference details. | Actual source, embedded session and independent project/ledger verification | Passed; [reference handoff](reference-handoff.md), remote `79e7b798b` |
| Preserve the original request and record changes to dialogue, duration and narrative decisions under the approved autonomy. | Actual source, embedded session and independent project/ledger verification | Passed; [reference handoff](reference-handoff.md), remote `79e7b798b` |
| Map source text and montage intentions to existing structured planning/review contracts; register assets and confirm the formal script through supported operations. | Actual source, embedded session and independent project/ledger verification | Passed; [reference handoff](reference-handoff.md), remote `79e7b798b` |
| Remove dependence on inherited unspecified budgets; distinguish montage timing from model generation durations. | Actual source, embedded session and independent project/ledger verification | Passed; [reference handoff](reference-handoff.md), remote `79e7b798b` |
| Demonstrate a formal episode with Portuguese content, English technical prompts and reusable existing project assets, without paid media generation. | Actual source, embedded session and independent project/ledger verification | Passed; [reference handoff](reference-handoff.md), remote `79e7b798b` |

## Ticket #8

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Keep budget and quality-attempt enforcement entirely in Codex context and its recovery record; do not add backend spend caps or duplicate billing. | Codex policy tests, CLI re-entry and independent review | Passed; [budget/recovery validation](budget-recovery-validation.md), remote `7f704b670` |
| Require explicit per-video/per-round numeric amounts and currency before paid submissions; sample, pilot and continuity require separate approval and unknown prices pause. | Codex policy tests, CLI re-entry and independent review | Passed; [budget/recovery validation](budget-recovery-validation.md), remote `7f704b670` |
| Include pending authorized spend, discarded work and billable transport retries; distinguish polling from new generation and apply initial generation plus at most two quality regenerations per rejected segment. | Codex policy tests, CLI re-entry and independent review | Passed; [budget/recovery validation](budget-recovery-validation.md), remote `7f704b670` |
| Use existing confirmation parameters for authorized autonomy and existing workflow state as the production authority. | Codex policy tests, CLI re-entry and independent review | Passed; [budget/recovery validation](budget-recovery-validation.md), remote `7f704b670` |
| Persist pending intent, review decisions, budget allowance and attempt counts without duplicating assets/scripts; reconcile completed jobs before resubmission. | Codex policy tests, CLI re-entry and independent review | Passed; [budget/recovery validation](budget-recovery-validation.md), remote `7f704b670` |
| Pause on subscription quota exhaustion without paid fallback; demonstrate budget-stop and interruption/re-entry scenarios with controlled fixtures. | Codex policy tests, CLI re-entry and independent review | Passed; [budget/recovery validation](budget-recovery-validation.md), remote `7f704b670` |
| Do not promise continued supervision after the Codex execution ends; provide explicit resumable state. | Codex policy tests, CLI re-entry and independent review | Passed; [budget/recovery validation](budget-recovery-validation.md), remote `7f704b670` |

## Ticket #9

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Configure credentials through existing settings without exposing secrets; use the international MiniMax endpoint and exact H3 selection. | Actual provider/settings/quote/job/render checks and independent review | Passed; exact H3 sample succeeded. Google discovery verified; image generation conditional and unperformed. |
| Configure the existing Google provider for gemini-3.1-flash-image when native image generation is needed; do not substitute a successor silently. | Actual provider/settings/quote/job/render checks and independent review | Passed; exact H3 sample succeeded. Google discovery verified; image generation conditional and unperformed. |
| Check actual duration/resolution/audio/reference capabilities and preview requests before spending; do not send unsupported native 1080p parameters. | Actual provider/settings/quote/job/render checks and independent review | Passed for the bounded capability sample; [actual media evidence](media-preflight.md), remote `fa36d7264` |
| Provide a concrete sample quote including required image generation, source video tier and delivery conversion; obtain numeric owner-approved ceilings before the real sample. | Actual provider/settings/quote/job/render checks and independent review | Passed for the bounded capability sample; [actual media evidence](media-preflight.md), remote `fa36d7264` |
| Generate a bounded sample through existing tools and poll the original job; preserve formal artifacts and report actual recorded cost. | Actual provider/settings/quote/job/render checks and independent review | Passed for the bounded capability sample; [actual media evidence](media-preflight.md), remote `fa36d7264` |
| Render vertical 1080 × 1920 using existing delivery machinery; record source resolution and any scaling, duration and playback evidence. | Actual provider/settings/quote/job/render checks and independent review | Passed for the bounded capability sample; [actual media evidence](media-preflight.md), remote `fa36d7264` |
| Test native audio first; record observed shortcomings for the review ticket without preemptively integrating ElevenLabs. | Actual provider/settings/quote/job/render checks and independent review | Passed for the bounded capability sample; [actual media evidence](media-preflight.md), remote `fa36d7264` |


## Ticket #10

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Reuse existing image/contact-sheet and local technical-signal tools; demonstrate access to actual audio and video beyond sampled still images. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Partial: reused contact sheets/signals and actual audio decoding/transcription on rendered fixtures; full playback/listening unavailable. |
| Verify audio/transcription or equivalent inspection capabilities rather than assuming an evaluator exists; use only necessary thin integration. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Local whisper-cli actual inference verified. False word mismatch and silent-audio hallucination observed, documented and independently reproduced. |
| Compare spoken content and timing to the intended script and reference goals; distinguish missing evidence from passing results. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Partial: transcript, PCM and cue envelopes compared with intended synthetic content; real reference quality judgement pending. |
| Exercise known-good and intentionally defective fixtures covering wrong/missing speech, identity/story errors and visibly mistimed subtitles. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Partial: actual wrong/silent speech, delayed subtitles and symbolic identity/story fixtures inspected. Subjective good-audio baseline remains unapproved. |
| Emit evidence-linked corrections using existing script/timeline operations where supported; identify any unsupported required correction precisely. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Existing correction routes documented with evidence; individual subtitle-only retiming not established. |
| Preserve the existing subtitle/rendering pipeline; do not build a speculative second system or claim frame sampling proves lip-sync. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Existing ASS/rendering pipeline reused unchanged; no frame-only lip-sync claim. Reviewed implementation in remote commit `e98612c83`. |
| New metered evaluation services require a concrete quote and authorized allowance before use. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | No metered evaluation service invoked; no numerical allowance supplied. |

## Ticket #11

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Use the prepared reference dossier and formal episode; reuse assets, generation, editing and export operations. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Apply Codex-only spending and quality-attempt controls throughout and preserve recoverable state. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Observe actual native audio before deciding whether a separate voice path is required; if ElevenLabs or alignment work is necessary, report the exact failure and open a separately scoped follow-up rather than falsely passing the pilot. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Confirm reference intent, Brazilian naturalness, dialogue completeness, continuity, subtitles and final playback, with evidence and material limitations. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Deliver vertical 1080 × 1920 with burned Portuguese subtitles, title, description, source information and recorded spending; do not publish to social platforms. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Complete only when the final output passes review; a blocked voice/alignment issue is not success and no unbounded generation is allowed. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |

## Ticket #12

| Acceptance criterion | Planned verification | Evidence and status |
| --- | --- | --- |
| Reuse shared characters, scene/prop assets, voice settings, overview, episode ledger and current/next outlines; no parallel series bible. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Choose a source-supported two-episode case and verify narrative and identity continuity against existing source and formal-script facts. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Obtain a quote and numeric allowance for this new round; the pilot allowance does not authorize all 30 requests. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Prepare a status inventory of the remaining requests with verified/blocked references, adaptation readiness and supported production path. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Demonstrate stopping and resuming between items without duplicate submissions and without exceeding Codex-approved bounds. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |
| Document actual limitations and file narrowly scoped issues only for evidenced gaps; do not automatically generate the entire collection. | Exercise through existing contracts; deterministic tests plus live evidence wherever the criterion requires it | Pending; not demonstrated |

## Integration and review log

- `7b012052e` (#5) and `5e6626de5` (#3) are committed, pushed, independently reviewed and closed with evidence on GitHub.
- No ticket closes until all criteria pass and the relevant commit is available remotely.
- Real provider samples, pilot and continuity round require separate concrete quotes and explicit numeric approval.
- No releases, workflows or social publishing are authorized.

## Current local readiness

- Production application runs on localhost:5173/API1241. Isolated authenticated validation server runs on1242 with separate data and no media credentials.
- Exact Opus5.5 medium subscription calls passed structured, image and existing-consumer checks. Production default/simple/complex text settings use `claude-subscription/claude-opus-5-5`.
- Owner supplied MiniMax and Gemini AIStudio credentials through Settings. Both free connectivity/model-list checks succeeded. Google lists exact `gemini-3.1-flash-image`; MiniMax model-list does not establish H3 entitlement.
- Existing MiniMax credential now uses the international endpoint with its key preserved. Synced H3 CNY pricing differed from official international USD pricing. Existing settings now use the verified USD override; five-second2K quote is USD0.65, per-video/round ceiling USD1.95 explicitly approved and reserved. See [media preflight](media-preflight.md).
- #6: authenticated synthetic-image upload/version/currentness and prompt preview succeeded, with52 regression tests passing. Actual AI-generated-image round trip and exact downstream request preview remain pending.
- #7: original reference inspected, silence independently decoded, all30 original hashes preserved. Actual embedded formal handoff has3shots and5registered assets; independent final review passed. Evidence integrated as `79e7b798b`; issue closed.
- #8: Codex-only policy/recovery integrated as `7f704b670`, independently reviewed,20tests passed, issue closed. The separate #9 sample allowance is now approved; later rounds remain unapproved.
- #10: advisory helper/fixtures integrated as `e98612c83`. Local Whisper exposed wrong/missing speech and its own false transcription. Full audiovisual subjective review, playback and lip-sync evidence remain missing. No preventive ElevenLabs integration.
- Subscription usage is accounted as tokens without invented API charges. No paid media or metered evaluation calls occurred. Sample, pilot and continuity each require separate concrete quotes and explicit numeric allowances.
- Private runtime/reference evidence remains under `/tmp/arcreel-goal-state/`, outside Git. No native desktop MCP registration, social publishing or unattended supervision claimed.

## Approved sample and evaluation checkpoint

- #9 actual H3 source succeeded: one provider submission, five billed seconds, USD0.65. Existing final-cut rendering produced1080x1920 at30fps. Independent full decode and all-attempt cost reconciliation passed; USD1.30 contingency released and further generation explicitly paused. Subjective audiovisual review remains pending. See [media preflight and execution](media-preflight.md).
- Owner separately approved six exact Gemini3.8Flash evaluation requests, total USD0.25, with per-artifact ceilings and no retries. Codex-only policy extension passed33tests and independent review, integrated as `973a50c18`. Inference results and actual costs remain to be recorded.
- Owner reported an incorrect Agent Settings warning while subscription execution worked. Code confirms the UI tests only API-key presence while the runtime supports local Claude login. Separate [issue #13](https://github.com/pablothobias/ArcReelBR/issues/13) records the reproduced readiness defect; no paid Agent API credential is required as a workaround.

## Evaluator findings and current diagnosis

- Six approved real evaluations completed with no retries or pending requests; usage-derived list cost USD0.16603950. Combined with H3 application-recorded USD0.65, recorded/estimated total is USD0.81603950, not an external invoice. Evidence is committed as `607549ecc`.
- #10 stays open: audio-only controls produced fabricated visuals and the digital-silence control produced invented speech. Some video/transcript/subtitle observations were correct. Raw outputs remain preserved; no automatic quality acceptance.
- Owner requested diagnosis before choosing human review or another evaluator. No alternative has been approved. Offline replay, prompt/schema/request analysis proceeds without new paid calls.
- #6 remains open. Image transport/encoding/identity was exercised with a tiny synthetic image; actual valid-size AI image is pending. Codex image tool exposes no price/allowance metadata. Nano Banana fallback has missing billable usage and ambiguous retry gaps, recorded in [#14](https://github.com/pablothobias/ArcReelBR/issues/14). No image call authorized or performed.
- #11 and #12 remain unstarted; Spec #2 stays open. Preexisting local teaching/planning/GLOSSARY changes remain untouched.

## Offline validation and controlled retest preparation

- Integrated offline saved-review validation as `62ec64a23`: separate audio/video contracts, actual modality/duration and all-channel/native-rate float64 PCM evidence, rejected contradictions and immutable raw/input snapshots. No automatic quality pass.
- 24 focused unit/integration tests, Ruff, basedpyright and test audit passed. Independent replay rejected both failed audio controls while retaining the good fixture and H3 sample as consistent but requiring review. No new inference occurred.
- The four-case deletion-only same-model diagnostic proposal was independently checked against frozen schema, media, full prompts and reconstructed requests. Proposed ceilings are USD0.01 per case and USD0.04 total; a fresh owner approval is pending. Previous six-call round remains closed. See [controlled retest proposal](evaluation-retest-proposal.md).
- #10 remains open: this fixes an evidence-validation defect but does not establish reliable perception or explain the provider's generation cause. #6, #11 and #12 remain incomplete; Spec #2 remains open.

## Completed controlled diagnostic

- Owner approved the separate four-case USD0.04 round. Codex-only policy support integrated as `8f16092aa`; 48 focused policy tests and independent review passed.
- Four actual captured requests matched frozen bodies and source hashes, ran once each, and settled at total USD0.00741600. No pending calls, retries or remaining authorization. Combined H3 plus both evaluation rounds: USD0.82345550 in app-recorded/provider-usage-derived costs, not independently verified invoices.
- The narrower schema did not prevent invented English speech on identical zero PCM or visual action in free audio prose. Offline validation rejected that actual new failure. The positive wrong-speech transcription is narrow evidence, not subjective quality acceptance.
- No human-review downgrade or alternate evaluator was selected. #10 remains open pending a sufficiently grounded review workflow; pilot and continuity acceptance remain unproven. A concrete alternative is being researched read-only for comparison.
