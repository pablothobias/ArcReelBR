# Audiovisual evaluator diagnosis

Status: bounded offline investigation, 2026-11-08. No additional provider calls, production changes or replacement evaluator were authorized or executed. The original six model responses and submitted-input evidence remain unchanged. Human review and another evaluator are options, not selected replacements.

## Established failure

Two audio-only controls produced unsupported visual scenes and confident lip-sync claims. The digital-silence control also produced invented speech. Independent inspection verified that its submitted WAV bytes match the recorded hash and contain 72,000 mono 16-bit PCM frames at 16 kHz with zero nonzero sample bytes. Provider usage identifies audio and text, without video.

The original `Review.model_validate_json` call accepts both responses because its schema validates structure and field types, not whether an input contains video or audible speech. This is a demonstrated acceptance gap. It does not establish why the model generated those claims. The schema allows empty visual text and `insufficient_evidence`; it does not force fabricated observations. The instruction prompt also explicitly requests abstention on audio-only inputs.

The video cases supplied useful observations, including delayed subtitles and symbolic character/prop differences. Those successes neither erase the failed controls nor establish general unreliability of every video observation. Actual human identity, voice performance and phoneme-level lip-sync remain unvalidated.

## Tight offline replay

The private replay compiles the actual four Pydantic schema classes and checks that their JSON schema exactly equals the schema retained in each original request context. It then submits unchanged raw provider text to the original validator with verified modality/PCM facts. It imports no provider caller and makes no network request.

```text
uv run python /tmp/arcreel-goal-state/evaluation-diagnosis/replay_validation.py
FAIL wrong-speech-audio: original schema ACCEPTED unsupported_visual_claim,unsupported_lip_sync
FAIL missing-speech-audio: original schema ACCEPTED unsupported_visual_claim,unsupported_lip_sync,speech_claim_on_zero_pcm
2 failing cases; provider_calls=0
exit 1
```

Repeated runs gave the same result in a fraction of a second. `--minimal` remains red with the required schema scaffolding and one unsupported visual assertion, after removing the original transcript, detailed invented scene and lip-sync claim.

```text
uv run python /tmp/arcreel-goal-state/evaluation-diagnosis/replay_validation.py --guarded
PASS wrong-speech-audio: evidence guard REJECTED unsupported_visual_claim,unsupported_lip_sync
PASS missing-speech-audio: evidence guard REJECTED unsupported_visual_claim,unsupported_lip_sync,speech_claim_on_zero_pcm
0 failing cases; provider_calls=0
exit 0
```

The guarded replay adds strict modality and zero-PCM rejection after structural parsing. This demonstrates a local validation correction against the same failures. It neither regenerates the model response nor demonstrates a fix to the cause of model fabrication. The replay remains a private diagnostic artifact, not a production evaluator.

## Bounded payload and association audits

After the ranked hypotheses were shown to the owner, the official installed Google SDK 2.31.0 was exercised through an in-memory HTTP transport and a dummy key. Six requests were reconstructed from frozen contexts and local input bytes. No credentials were retrieved and no network request was sent.

- Decoding each reconstructed inline payload reproduced its captured submitted-input SHA-256.
- Audio-only inputs serialized as WAV; video inputs serialized as MP4. Each request contained one user turn, one media part and the exact retained instruction/schema text.
- No system instruction, cached-content reference, tools or previous conversation turns appeared in the reconstructed bodies.
- Six distinct provider response IDs matched their saved usage, recovery intention and artifact associations. Source hashes in dispatch records matched the corresponding contexts.

Private outputs: `/tmp/arcreel-goal-state/evaluation-diagnosis/wire-audit.json` and `association-audit.json`; rerunnable driver: `audit_sdk_payload.py` in that directory.

**No historical HTTP wire body was captured at dispatch.** These reconstructions weaken a gross local MIME, serialization or file-selection explanation. They cannot prove the exact historical request bytes or rule out remote routing, decoding or caching behavior. The correct transcription in the non-silent audio-only case further weakens a simple explanation that no usable audio arrived.

## Ranked hypotheses and current bounds

| Hypothesis | Falsifiable prediction | Current evidence |
|---|---|---|
| Crossmodal task/schema framing encourages completion instead of abstention | With the same input/model and only the schema block changed to an audio-specific contract, unsupported visual completion decreases | Plausible, untested causally; abstention was already representable, so schema necessity is not the explanation |
| The model/provider audio-only perception path fails under this configuration | Failures remain after verified request delivery, isolation and controlled format/schema changes, while video cases may behave differently | Consistent with observed controls; not isolated from prompt or remote-path effects |
| WAV/MIME/SDK serialization or historical API delivery differs from the intended input | A captured diagnostic wire body or equivalent supported encoding exposes a byte/part mismatch or changes the outcome | No mismatch in offline reconstruction; historical delivery and remote interpretation remain unknown |
| Local input, response or conversation contamination | Identity/history audit exposes reused or swapped cases; independently isolated requests remove the symptom | No local association mismatch, reused response ID or reconstructed history found; remote contamination was not tested |

No live causal probe or new model comparison has been performed. The observed failure is established; its generation cause remains unresolved.

## Options before further spending

| Option | Useful result | Limit and authorization boundary |
|---|---|---|
| Fix the known validation method, then test the same model | Reject impossible claims using actual modality and PCM; conduct a narrowly controlled comparison before attributing the failure to the model | Offline rejection is demonstrated. Any new inference requires a new concrete quote and explicit numeric approval; previous six-call approval is exhausted |
| Human review of existing media | A person can listen/watch the actual files, adjudicate voice and timing, and provide grounded acceptance decisions | Uses human attention; does not repair or establish automated evaluator reliability |
| Another evaluator | Compare a different system against the same known-good and defective controls | A model switch alone does not fix validation. Exact model, input support, pricing and a bounded comparative trial need verification and approval |

A controlled same-model follow-up should retain immutable inputs, capture a sanitized actual serialized request before submission, disable retries/history/tools, and change one variable at a time. An audio-specific schema comparison can isolate task framing; an equivalent encoding comparison can separately test the media path. Silence remains a negative control, and returned confidence is never its own ground truth. No new call count, price or allowance is implied here.
