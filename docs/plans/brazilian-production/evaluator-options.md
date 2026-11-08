# Evaluator option after the failed audio controls

Status: research only. The four-case Flash diagnostic is closed; no alternative-model inference, model-default change or new allowance is authorized. Issue #10 remains open. The owner has not accepted an alternative evaluator or human-assisted final review as the production quality workflow.

## Concrete Google-account candidate

The configured official Google AI Studio account successfully listed **`gemini-3.1-pro-preview`**, version `3.1-pro-preview-01-2026`, with `generateContent` and `countTokens` support. This is an exact discovered identifier, not `gemini-pro-latest`, an image-generation Pro variant, or a guessed newer name. Discovery establishes visibility, not successful paid inference, available quota or audiovisual accuracy. The sanitized private receipt is `/tmp/arcreel-goal-state/evaluation-diagnosis/pro-model-discovery.json`.

Google's [model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview) explicitly supports text, image, **video and audio input**, text output, structured output and thinking. Its documented limits, also returned by discovery, are 1,048,576 input tokens and 65,536 output tokens. It is a Pro-family alternative; those labels do not establish that it outperforms the tested Flash model on these errors.

The [video documentation](https://ai.google.dev/gemini-api/docs/video-understanding#technical-details-video) describes static processing as the default, with audio and sampled frames. Its default 1 FPS can miss rapid motion; custom frame sampling exists. The newer agentic-video mode's listed models do not include this Pro identifier, so this proposal assumes ordinary static processing, not agentic navigation. [Audio documentation](https://ai.google.dev/gemini-api/docs/audio) supports audio descriptions and transcription. These are actual media inputs, but still model interpretations rather than reliable ground truth, phoneme-level lip-sync measurement or proof of acting quality.

## Smallest useful comparative trial proposal

Three fresh calls would test this model against the already observed failures and one real generated clip. Reuse the exact frozen silence WAV and original submitted wrong-speech WAV, plus the existing native-audio H3 source. For a model-only contrast, reuse the exact narrowed prompts and files from diagnostic B/D, plus the frozen original H3 audiovisual prompt/request. Keep identical generation settings, including `LOW` thinking, which the [official support table](https://ai.google.dev/gemini-api/docs/thinking#thinking-levels) explicitly supports for this model. Keep the same raw semantic readouts: speech on zero PCM, actual words, unsupported visual claims in audio-only prose, and cautious observable video/audio findings on H3. Do not supply expected words, silence labels or earlier model claims to the model. Human scoring uses those independent controls after the response.

The audio request bodies are byte-identical to captured Flash B/D bodies; only the model identifier in the endpoint changes. H3 reuses its historical prompt, bytes, generation configuration, per-part `MEDIA_RESOLUTION_HIGH`, and video metadata `fps=24`, start `0s`, end `5s`. Ordinary static processing remains the default; no agentic mode or new tools are requested. The [media-resolution documentation](https://ai.google.dev/gemini-api/docs/media-resolution) explains that resolution determines frame detail independently of processing mode. The exact Pro free-count endpoint accepted these fields and returned 33,201 tokens for H3; that confirms count admission, not that a future generation will honor every sampling detail or assess lip-sync accurately. This is a model-only request contrast, not an isolated internal cause test. Historical H3 transport was not captured, so delivery-path differences remain a comparison limitation. One call per input provides no reliability estimate. The H3 case has no exact human lip-sync ground truth and cannot establish reliable acceptance by itself. An inconclusive or truncated response remains the sole paid outcome, without a retry.

Current [official standard pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-pro-preview), checked November 8, 2026: **USD 2 per million input tokens and USD 12 per million output tokens including thinking**, for prompts at or below 200,000 input tokens. No free inference, cache discount, batch discount, grounding or tool usage is assumed.

| Proposed input, one call each | Entire input counted | Input admission cap | Combined thinking/output cap | Worst-case token cost, USD | Suggested explicit ceiling, USD |
|---|---:|---:|---:|---:|---:|
| Frozen silence WAV | 804 | 2,000 | 2,048 | 0.028576 | 0.03 |
| Frozen wrong-speech WAV | 807 | 2,000 | 2,048 | 0.028576 | 0.03 |
| Existing H3 native-audio video | 33,201 | 40,000 | 2,048 | 0.104576 | 0.11 |
| Round | 34,812 | 44,000 | 6,144 | 0.161728 | **0.17** |

Formula: `(input cap × 2 + combined output cap × 12) / 1,000,000`. These ceilings include one dispatch per input and **zero transport retries**. They authorize no new media generation, fourth inference, evaluator fallback or extra output attempt. A timeout or ambiguous response would retain that case's full reservation and stop the round. The unused prior allowances cannot fund it.

Three documented-free `countTokens` requests have now completed against this exact model/account for the complete frozen inputs. All fit their caps; no inference request was sent. Private canonical plan: `/tmp/arcreel-goal-state/evaluation-diagnosis/pro-options/pro-counts-and-request-plan.json`, with one expected SDK wire body per case. The count-only caller enforced an exact `:countTokens` URL; its only `generateContent` invocations used a dummy key and offline mock transport to reconstruct future bodies. Proposed order: wrong speech, silence, then H3. Any future execution requires separate explicit approval of USD 0.03/0.03/0.11 and USD 0.17 total, its own fresh directing record, and independent caller clearance. Preserve actual-wire capture and the reviewed single-forward guard. No prior round is reopened. A 2,048-token combined cap can truncate a Pro response; that possibility is part of this minimal comparison, not permission to raise the cap afterward.

## What each option can establish

| Option | Useful evidence | Limits and required owner choice |
|---|---|---|
| A separately approved Pro trial | Whether these exact controls and the H3 clip produce different observed claims under a concrete alternative model | May repeat hallucinations; success on three examples does not validate a general automatic evaluator. No switch is authorized. |
| Direct human listening and video playback with explicit review criteria | A person can check actual intelligibility, voice/delivery, visible acting and apparent synchrony rather than rely on sampled frames or generated prose | Requires time and explicit acceptance of a human-assisted workflow. It is not an approved downgrade or replacement for the requested independent capability. |
| Continue diagnosis without paid inference | Existing captured requests, zero-PCM contradiction, raw response inspection and deterministic guards can reject known unsupported claims | Cannot establish subjective audiovisual quality or prove another model's capability. |

The observed result already supports one narrow conclusion: removing visual root fields alone did not prevent false perception. It does not prove that all Google models fail, identify the provider's internal cause, or justify silently switching models. The next route belongs to the owner's explicit decision after reviewing the options and a frozen quote.
