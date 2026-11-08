# Offline review validation

`scripts/validate_av_review.py` checks saved audiovisual-review responses against actual local media evidence. It performs no provider request, ASR, generation, editing or automatic quality acceptance. It addresses the demonstrated validation defect in #10; it does not establish why the evaluator generated its failed responses or close the remaining perception criteria.

## Use

Run against a saved review object or the original saved Google GenerateContent response. Choose a new **private** output directory because it retains the original response and an immutable copy of the inspected media:

```bash
uv run python -m scripts.validate_av_review \
  --media /private/actual-media.wav \
  --response /private/provider-response.json \
  --evidence-ref /private/usage-and-result.json \
  --output /private/new-review-validation
```

The command writes `validation.json`, the exact `raw-response.json` bytes and an `inspected-input` media snapshot. Hashes refer to those inspected bytes, even if an application replaces the original selected artifact during inspection. Supplied evidence references remain attached. Existing output directories are never overwritten.

Exit 2 means the response was rejected. Exit 0 means validation completed, which may still report missing evidence. Neither exit 0 nor a structurally consistent response is an audiovisual pass: every result requires a reviewer and has `automatic_quality_pass=false`.

## Checks and limits

- `AudioReview` has audio observations and structured speech only. Visual, subtitle and lip-synchrony fields are forbidden. `VideoReview` retains the separate visual response contract. Unknown video modality is not assumed to be audio-only; it remains insufficient evidence.
- Existing bundled ffmpeg and `probe_media` establish actual streams and duration. All audio streams are decoded to float64 PCM without downmixing, resampling or integer quantization. A zero-signal conclusion requires nonempty finite samples and zero values across every decoded stream/channel. Missing streams, failed probing/decoding, empty data and nonfinite samples are distinct from proven zero PCM. Opposite stereo channels and quiet nonzero float audio remain nonzero.
- Structured speech contradicting proven zero PCM or an absent audio stream is rejected. Positive synchrony claims without an audible signal are rejected. Ordered, finite speech and subtitle timestamps must fit the actual media duration. Missing duration and evaluator-reported insufficient evidence propagate as insufficient evidence.
- A consistent response still requires review. Nonzero PCM does not establish speech, confidence does not establish correctness, and frame sampling does not prove lip-sync. Arbitrary unsupported claims can remain in free-form prose; the helper does not pretend to solve that with word-matching heuristics. Acting, facial identity and subjective quality remain unverified.

## Verification

Focused checks: `tests/unit/scripts/test_validate_av_review.py` and `tests/integration/scripts/test_validate_av_review.py`. They exercise forbidden modality fields, zero PCM, absent/unknown evidence, exact/end-overflow temporal boundaries, abstention, confidence, real opposite-channel stereo, quiet float audio, missing audio, invalid media and source replacement during decoding. Production routes, caller allowance policy and the subtitle/rendering pipeline are unchanged.

The focused pytest run passed all 24 cases. Ruff and basedpyright passed for the helper and both test files. The repository test auditor passed for both test directories with zero violations.

Actual captured-response replays are retained privately under `/tmp/arcreel-goal-state/audiovisual-research/offline-validation-v1/`. The two failed audio-only controls were rejected; the known-good audiovisual control was structurally consistent but still required review. Separate actual CLI runs under `offline-cli-validation-v1/` returned exit 2 for the silent failed control and exit 0 with `consistent_requires_review` for the known-good control. No new inference or metered call was made, and protected media/response content was not copied into the repository.

The earlier six-call characterization, including rejected provider outputs and its USD 0.16603950 usage-derived cost, remains unchanged in [the trial evidence](evidence/10-multimodal-trial.md). Any future controlled retest needs its own explicit scope, quote and approval; this offline helper grants no additional calls.
