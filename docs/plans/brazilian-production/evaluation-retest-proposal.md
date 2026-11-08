# Controlled same-model audio diagnostic proposal

Status: the separately approved four-case diagnostic completed on 2026-11-08; its outcomes appear below the frozen proposal. No further inference is authorized. The earlier six-call evaluation allowance remains closed. This is a small falsifiable follow-up to [the established failures and offline diagnosis](evaluation-diagnosis.md), not a replacement evaluator or a reliability study.

## Question and controlled variable

Does replacing the appended crossmodal output-contract block with an audio-only output contract change the observed audio errors on the same two frozen WAVs, under otherwise unchanged request contents and model settings?

Keep the original instruction prefix byte-for-byte, including its existing abstention instruction. Replace only the final JSON-schema text block: original `Review` versus a modality-only derivative of that frozen original schema. Keep `gemini-3.8-flash`, the same configured official Google AI Studio credential, WAV bytes/MIME, one fresh user turn, media-first/text-second order, `thinking_level=LOW`, `max_output_tokens=2048`, JSON MIME, disabled automatic function calling and disabled continuation. Do not introduce expected words, silence labels, a correctness hint, extra history, tools or cache references into either model request.

The treatment removes only four root properties, `actual_visual_description`, `visible_words`, `subtitles`, `audiovisual_synchrony`, and their entries in `required`. Derivation fails if any expected property or required entry is missing. Every common property, description, original speech constraint, schema title and definition is unchanged. This deliberately does not use the production helper’s stricter `AudioReview` contract. Unused visual definitions remain, as does visual vocabulary in the unchanged instruction prefix, which could still influence the model. This is therefore a limited diagnostic contrast. Missing removed fields is mechanically expected and is not evidence of better perception.

## Four fixed cells, one request each

| Order | Frozen input | Appended contract | Entire input tokens counted | Proposed input cap | Combined thinking/output cap | Proposed case ceiling |
|---|---|---|---:|---:|---:|---:|
| A | Original submitted silence WAV | Original `Review` | 905 | 2,000 | 2,048 | USD 0.01 |
| B | Original submitted wrong-speech WAV | Modality-only derivative | 807 | 2,000 | 2,048 | USD 0.01 |
| C | Same wrong-speech WAV | Original `Review` | 908 | 2,000 | 2,048 | USD 0.01 |
| D | Same silence WAV | Modality-only derivative | 804 | 2,000 | 2,048 | USD 0.01 |

This fixed balanced order is predeclared; it is not a randomized or statistically powered study. Each cell permits at most one actual inference request. No failure, timeout, empty result, output cutoff, schema failure or unexpected observation authorizes a retry. No alternative encoding, reasoning level, model or additional case is included.

The two WAV SHA-256 fingerprints are unchanged from the failed cases: silence `00ea5c7415d6fd1232a2bb551c00c253f90023abb0775f9d9a3e54d47da9bc9d`; wrong speech `2ad8bc1cad6d99ba85843d6902a70556a8a62b83ec50724aed77518d0723d59d`. The wrong-speech file is the original submitted converted WAV, not a new conversion from AIFF.

## Price and permission boundary

Current [official standard pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash), applicable through December 31, 2026, is USD 0.75 per million input tokens and USD 3.75 per million output tokens including thinking. Count the entire media-plus-text input, including the schema embedded as ordinary text. No free inference entitlement or cache discount is assumed.

The existing selected credential completed documented-free `countTokens` requests; no inference was called. The final four request counts are above. The original-condition counts were reused only after verifying byte-identical files and complete prompts. Eight documented-free count RPCs occurred during preparation: six from earlier preparation, including a superseded stricter-schema proposal, plus two counts for the final modality-only treatment. An earlier URL-safe-base64 verifier correction concerned the local verifier, not changed media or a discovered provider payload mismatch. [Google's billing FAQ](https://ai.google.dev/gemini-api/docs/billing#is-gettokens-billed) identifies token counting as unbilled; [its official clarification](https://discuss.ai.google.dev/t/direct-gemini-developer-api-counttokens-free-tier-billing-and-quota-clarification/190706) maps this to `models.countTokens`.

Conservative bound per request: `(2000 × 0.75 + 2048 × 3.75) / 1,000,000 = USD 0.00918`. The four bounds total USD 0.03672. Proposed explicit allowance: **USD 0.01 per named case, USD 0.04 for the four-call round**. These figures are a proposal, not approval. The [output limit includes thinking and visible output](https://ai.google.dev/gemini-api/docs/generate-content/thinking#token-limits); a truncated result remains a paid diagnostic outcome.

Do not add a policy round or authorize a reservation until the owner approves this exact scope and numerical ceilings. The private draft record has empty owner evidence, null approved limits and no intents. Before any future dispatch, the directing policy must represent the approved four named cases without silently reusing the closed six-artifact allowance. Actual settlement must include unsuccessful/truncated responses and preserve the full reservation on unknown outcomes.

## Actual wire evidence before any future dispatch

Private proposal directory: `/tmp/arcreel-goal-state/evaluation-diagnosis/retest-proposal/`. Its canonical artifacts are listed in `canonical-artifacts.json`: `modality-only-schema.json`, `exact-schema-diff.json`, `original-prompt.txt`, `audio-contract-prompt.txt`, `counts-and-request-plan.json`, and one expected serialized body per case. The superseded stricter-contract proposal is retained only under `superseded-audio-contract-bundle/` and is not part of the proposed dispatch. Those bodies were reconstructed through the installed official SDK using a dummy key and an in-memory HTTP transport; they are **not historical or actual network dispatch captures**.

For a separately approved execution, capture the actual SDK-serialized body before the first network forward. Verify its model URL, body hash, decoded inline WAV hash using URL-safe base64, MIME, prompt/schema hashes, generation config and one-turn/two-part shape against the approved proposal. Persist a dispatch-started sentinel and sanitized metadata before forwarding; retain the raw body only privately without headers or credentials. A mismatch pauses before transmission.

Use an explicitly supplied `httpx.AsyncClient` with transport retries zero and redirects disabled, plus SDK `HttpRetryOptions(attempts=1)`, so an optional SDK aiohttp path cannot add an invisible resend. This preserves generation configuration while controlling transport. The explicit-httpx transport is identical across all four new cells, but it was not captured and was not necessarily identical in the historical six-call run. A failure that does not reproduce in the new original-schema cells therefore cannot distinguish stochastic variation from transport/configuration-path effects. The deletion-only contrast is controlled within the four new cells; it does not hold every historical delivery factor constant. Keep a one-forward guard per case. After any delivery ambiguity, retain the pending reservation and prohibit replay. Re-entry reconciles the sentinel/response/usage before considering any later case.

## Predeclared readouts and interpretation

1. On digital silence, inspect whether the model claims speech or non-silent audible events. Zero PCM is independent ground truth; confidence is not evidence.
2. On wrong speech, compare the heard words to the frozen fixture's independently known actual utterance. Do not show that utterance or the prior ASR output to the model. Preserve raw punctuation and report any normalization separately.
3. Inspect free-text audio descriptions and limits for unsupported visual assertions in both conditions. The mere absence of the removed visual fields is not a perception result.
4. Record structural validity, evidence-guard rejection, finish reason, returned model version, actual thought tokens, visible-output tokens and usage separately. Apply the same modality/zero-PCM guard to both conditions after scoring raw observations; guard rejection is a validation result, not improved model perception. An empty legacy visual field is not a hallucination; a positive unsupported visual assertion is.

`LOW` and the combined token cap remain fixed, but actual reasoning-token allocation can vary with schema size and required output. Changed contract field requirements, prompt length, residual visual vocabulary, stochastic output and unobservable provider state/model-alias drift remain confounds. A cutoff is inconclusive rather than a reason to increase output limits during this round.

If the original condition no longer reproduces the failure, report non-reproduction. If only the audio-contract condition improves an auditory readout, report a hypothesis-consistent diagnostic observation, not an isolated cause. If failures persist, report that persistence without claiming to have ruled out all framing or media-path explanations. One run per cell supports no statistical reliability estimate, no general video/lip-sync capability conclusion and no automatic acceptance gate. Any further causal probe needs its own design and authorization.

Final treatment schema SHA-256: `11bcf9eb646ef50bd9de62c3cad42509429e0c909f36bc334fa18a367ee0f91f`. Its exact deletion-only diff is recorded privately as `exact-schema-diff.json`; common speech definitions are byte-equivalent after canonical JSON serialization.

## Approved execution and observed results

The owner approved exactly “Sim, aprovo US$ 0,04 para os quatro casos” in question `call_8dbd2f9d4fcf4ac18808e025c157549e`, after this proposal was frozen in `b8a96ad1d`. A fresh `diagnostic-10` recovery record reserved USD 0.01 before each request. Independent Codex review cleared the policy and private bounded caller before dispatch. The historical six-call record remained closed and unchanged.

All four calls ran once in the specified order, using the same configured account and exact model. Actual serialized bodies were captured before forwarding and matched every frozen body hash. Four durable single-forward sentinels exist, all responses ended `STOP`, and all usage was settled. No retries, fifth call or media generation occurred. The record is closed with no pending request. Private wire/response/usage/recovery evidence is under `/tmp/arcreel-goal-state/evaluation-diagnosis/retest-proposal/`; [sanitized results](evidence/10-audiovisual/four-case-diagnostic-results.json) preserve response IDs, usage, hashes and raw semantic observations.

| Case | Raw semantic observation before guards | Recorded usage cost, USD |
|---|---|---:|
| A, silence/original | No speech claimed this time, but invented hum/click and a lab-coat/examination-room scene | 0.001548 |
| B, wrong speech/modality-only | Correct words after punctuation/case normalization; no visual assertion in audio/limits text; labels the synthetic Luciana voice male | 0.00147375 |
| C, wrong speech/original | Correct words, but invented a visible man, subtitles/timings and an off-camera spatial claim | 0.00336075 |
| D, silence/modality-only | Invented English speech, “so this is what it looks like on my hand”, plus skincare-product hand actions in the audio description | 0.0010335 |

Total recorded list-price cost from returned usage: **USD 0.007416**. The unused USD 0.032584 authorizes no additional call. No thoughts-token count was reported; input plus candidate counts equaled each response's total count. This is usage-based accounting, not independent invoice verification.

Both silence requests used the identical 4.5-second WAV with 72,000 mono 16-bit samples, all zero, independently rechecked after execution. Therefore D's confident speech claim contradicts the actual signal. Positive visual claims reproduced in the original contract, and visual action leaked into a retained free-text field in the modality-only contract. **Removing those root schema fields alone is insufficient to prevent unsupported semantic claims.** Their mechanical absence is not a successful perception result. A's earlier false-speech failure did not reproduce in this one new call, while false sound and visual claims did.

The same existing offline validator was then applied to all saved outcomes without any provider call: A/C rejected for forbidden audio-only fields; B was `consistent_requires_review`; D rejected for `speech_on_zero_pcm`. A/C's structural rejection is separate from the raw positive unsupported claims above. B's status is not quality acceptance, and free-text claims still require review.

This one run per cell does not establish reliability or a definitive cause. Retained visual vocabulary, stochastic output, unobserved reasoning allocation and provider serving state remain confounds. Explicit HTTPx delivery is controlled across these four calls but was not captured or necessarily identical in the historical six-call run. No general video, identity, acting or lip-sync capability conclusion follows from this diagnostic.
