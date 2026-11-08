# Bounded multimodal characterization

Status: six owner-approved real evaluation requests completed on 2026-11-08. **Issue #10 remains open: a reliable autonomous audiovisual acceptance gate was not demonstrated.** Useful observations coexist with confident hallucinations on known controls. No further requests are authorized by this completed trial.

This is separate from MiniMax H3 generation, the #9 capability sample, #11 pilot acceptance and #12 continuity acceptance. The evaluated H3 video is the synthetic five-second capability sample, not the pilot. No ElevenLabs, lip-sync implementation, second subtitle system or new Agent runtime was added.

## Approval and bounded execution

The owner explicitly approved USD 0.25 for exactly six evaluations. Approval provenance is retained under `questioncall_0a0a661fbada4fbe8dcb3a937eac2511`. Per-artifact ceilings were USD 0.04 for the H3 sample, USD 0.06 for each of three audiovisual controls, and USD 0.01 for each of two audio controls. There were no retries or replacement evaluations.

The exact model was `gemini-3.8-flash` through the official Developer API GenerateContent endpoint. Installed `google-genai` 2.31.0 used the existing configured Google credential in memory; no secret was printed, exported or copied into the isolated application. Each call followed a durable Codex directing reservation. The SDK used `HttpRetryOptions(attempts=1)`, meaning the original request only, with continuation and automatic function calling disabled and no tools.

Actual video bytes, including their native audio stream, were supplied inline. Video processing was static at 24 FPS with HIGH per-part media resolution. Audio-only controls supplied actual WAV bytes. This establishes actual multimodal input, not just sampled stills plus an ASR transcript. Frame sampling still does not establish continuous or phoneme-level perception. Official documentation describes direct audio/video input and configurable sampling. [Video input](https://ai.google.dev/gemini-api/docs/generate-content/video-understanding), [model capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).

Every request used LOW thinking and a hard output cap of 2,048 tokens, including thinking. The model does not support MINIMAL thinking. Exact free CountTokens preflights used the same media part, FPS, resolution and entire review/schema prompt; all counts passed the approved input caps. A local SDK configuration incompatibility was corrected before any inference: HIGH was carried per media part because Developer API CountTokens rejects `generation_config` in the installed SDK. [Output cutoff](https://ai.google.dev/gemini-api/docs/generate-content/thinking#token-limits), [thinking levels](https://ai.google.dev/gemini-api/docs/latest-model), [nonbillable counting clarification](https://discuss.ai.google.dev/t/direct-gemini-developer-api-counttokens-free-tier-billing-and-quota-clarification/190706).

## Actual usage and response identities

The table records provider-reported input/output usage and cost computed at official list rates, not a verified external invoice or tax-inclusive charge. Current rates through 2026-12-31 are USD 0.75 per million uncached input tokens and USD 3.75 per million output tokens including thinking. No cached input was reported. [Official pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash).

| Artifact | Free counted input / cap | Actual input | Actual output including thinking | Usage-derived USD | Provider response ID |
|---|---:|---:|---:|---:|---|
| Known-good audiovisual control, 9 s | 59,694 / 65,000 | 58,010 | 371 | 0.04489875 | `vJ_waoy8NYaqytMPhMan6Qs` |
| Wrong-speech audio control, 4.565533 s | 908 / 2,000 | 876 | 596 | 0.00289200 | `7p_waq_lFvTX0_gPj6me2Qw` |
| Silent audio control, 4.5 s | 905 / 2,000 | 874 | 233 | 0.00152925 | `Z6DwasvKOsehytMPkonlkA4` |
| Delayed-subtitle audiovisual control, 9 s | 59,694 / 65,000 | 58,010 | 498 | 0.04537500 | `haDwatnaH-vJ0_gPl9zS8Ak` |
| Symbolic identity/story control, 9 s | 59,694 / 65,000 | 58,010 | 324 | 0.04472250 | `1aDwavL8FK6xuMYPvpq-mA4` |
| Native H3 audiovisual sample, at most 5 s | 33,201 / 40,000 | 32,566 | 586 | 0.02662200 | `-qDwavq7EpKv5NoPzu_hgAo` |
| **Total, six requests** | | **208,346** | **2,608** | **0.16603950** | |

The conservative input-cap plus maximum-output quote was USD 0.22533, within the USD 0.25 approval. Actual token-derived cost was USD 0.16603950. All six reservations are reconciled as completed, with no unknown outcome or pending request. Raw response hashes, submitted/source hashes, reported modality details, caps and individual receipts are indexed in [10-multimodal-trial.json](10-multimodal-trial.json). Private raw evidence and the completed recovery record remain under `/tmp/arcreel-goal-state/audiovisual-research/`.

## Blind observations compared with known evidence

The model received no expected transcript, correctness label or descriptive filename. Raw JSON responses were preserved before comparison with the approved content and known fixture construction. Passing the response schema is not audiovisual acceptance.

| Input | Observed model result | Supported conclusion |
|---|---|---|
| Known-good audiovisual control | Correct Portuguese words, ANA/blue/white-mug drawing and overlapping subtitles around 0.125–4.292 s; lip-sync marked insufficient evidence for the static drawing. | Supports these narrow visual/transcript/timing observations. Subjective voice labels were inconsistent with other outputs and are not a reliable identity or quality result. |
| Wrong-speech audio-only WAV | Correctly recognized the different Portuguese speech, but invented an outdoor woman, clothing, surroundings and aligned mouth movements with confidence 0.95. | **Rejected evaluator output.** There was no visual input. Audio recognition does not validate its invented visual/performance claims. |
| Digitally silent audio-only WAV | Invented an English medical sentence, an indoor woman/office scene and aligned mouth movements with confidence 0.95. | **Rejected evaluator output.** Independent full PCM decoding found zero nonzero samples, hashes matched, and provider usage showed AUDIO plus TEXT only. No local substitution or encoding defect explained the output. |
| Delayed-subtitle audiovisual control | Located subtitles at 5.0–9.0 s after speech and reported no overlap; lip-sync remained unassessable. | Supports detection of the known subtitle-envelope defect on this fixture. It does not establish word-level subtitle alignment. |
| Symbolic identity/story control | Observed BRUNO/red/brown object rather than baseline ANA/blue/white mug; recognized the unchanged audio and subtitles. | Supports a symbolic label/costume/prop discrepancy. It does not test human facial identity or cross-episode character continuity. |
| Actual native H3 audiovisual sample | Heard the intended Portuguese word sequence, described the kitchen subject/actions, and reported warm delivery and apparently aligned mouths at confidence 0.85. | A real joint audio/video observation. It is not calibrated acting, voice-consistency or phoneme-level lip-sync acceptance, particularly given the failed controls. |

The audio-only hallucinations remain in the raw evidence. The operator-side modality guard rejects non-insufficient mouth-sync/visible-text claims on audio-only inputs and accepts no visual description from them. Known digital silence independently vetoes invented speech. These safeguards prevent accepting the demonstrated failures; they do not prove that subjective judgements on other footage are reliable. No used control was retried with a corrected prompt, and no silent model substitution occurred.

## Independent review and remaining boundary

Independent Codex review verified the exact model/settings, reservation-before-call ordering, single SDK attempt, free counts within caps, source/submitted hashes and the silent control's all-zero PCM. The local policy's 33 focused unit/CLI tests and typecheck passed while preserving the existing generation-round limits. Final receipt/footage assessment is retained with the coordinator's review evidence.

The original local inspection, silence measurement, ASR, contact-sheet, subtitle and timeline operations remain useful. This trial adds actual provider observations but does not justify wiring Gemini results into an autonomous pass/regenerate gate. The high-confidence impossible observations show why confidence and well-formed JSON are insufficient. Further evaluator/provider changes require an explicit decision and separately bounded approval; this allowance authorizes no seventh call. Native audio remains the first production path, with conditional follow-ups only for observed production shortcomings.
