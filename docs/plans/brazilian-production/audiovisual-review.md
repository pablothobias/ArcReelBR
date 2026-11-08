# Local audiovisual review evidence

Status: partial capability validation for issue #10, 2026-11-08. No pilot or continuity sample was generated. No metered evaluation service was invoked. The synthetic fixtures below are capability probes, not evidence that generated production video meets the specification.

## Available evidence path

The existing `inspect_video_units` MCP tool supplies image contact sheets and local black/freeze/cut signals. Its `model_review` remains null. The implementation here preserves those tools and the existing subtitle/rendering pipeline.

`scripts/inspect_audio_evidence.py` is an optional local CLI. It uses the repository's bundled ffmpeg and media probe, extracts actual mono PCM, runs an explicitly supplied local `whisper-cli` model in Portuguese without an expected-text prompt, and retains the raw JSON transcript and timestamps. It measures decoded PCM silence independently of recognition. It never declares an audiovisual pass or edits a project. Output must be a new directory; existing evidence is not overwritten.

Expected speech is a JSON list of `{segment_id, start, end, text}`, with seconds on the actual media timeline. Derive this small review context from the approved script and current timeline rather than maintaining a second formal script. Optional subtitle evidence uses the existing `SubtitleCue.to_dict()` shape (`start_microseconds`, `duration_microseconds`, `text`, and optional ownership/speaker fields). Cues must be placed on that same global timeline. The helper compares complete utterance envelopes, not per-word alignment. Repeated identical lines are reported as ambiguous.

Example:

```bash
uv run python -m scripts.inspect_audio_evidence \
  --media /tmp/arcreel-goal-state/audio/subtitle-delayed.mp4 \
  --model /tmp/arcreel-goal-state/audio/ggml-base.bin \
  --expected /tmp/arcreel-goal-state/audio/expected.json \
  --subtitle-cues /tmp/arcreel-goal-state/audio/subtitle-delayed-cues.json \
  --output /tmp/arcreel-goal-state/audio/new-review
```

Local dependency verified: whisper.cpp `whisper-cli` 1.9.5 with multilingual `ggml-base.bin`, downloaded from the model URL used by the official whisper.cpp project: `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin`. The model is external and is not committed or automatically downloaded by the helper. Initial and subsequent inference used CPU, Portuguese language selection and no speech-text priming. No paid fallback exists.

Sanitized historical results, media/model fingerprints and portable reproduction commands are committed under [evidence/10-audiovisual](evidence/10-audiovisual/README.md). The portable fixture builder is `scripts/build_av_review_fixtures.py`.

## Actual fixture exercise

Local evidence directory: `/tmp/arcreel-goal-state/audio/`. The exact fixture construction is retained there as `create_av_fixtures.py`; `fixture-manifest.json` records media/model sizes and SHA-256 fingerprints. Audio originated from the installed macOS Luciana voice. Intended speech: “Bom dia, Ana! O pão acabou, mas o café está quentinho.”

The visual reference is deliberately symbolic: a figure labelled ANA, wearing blue and holding a white mug. Its defective counterpart is labelled BRUNO, wears red and holds a brown box. This exercises observable character-label, costume and prop mismatches; it does not test real facial identity preservation. The three MP4 fixtures are 540 × 960, 25 fps, nine seconds long. They are local inspection fixtures, not the required 1080 × 1920 pilot.

Subtitles were burned with existing `lib.final_cut.subtitles.ass_document`, `BurnedSubtitle`, the bundled subtitle font and bundled ffmpeg. Contact sheets and technical signals came from existing `build_contact_sheets` and `detect_signals`. Signal detection decodes actual video; audio extraction reads actual AAC/PCM, rather than supplying a mocked transcript.

| Fixture and evidence | Observed result | Review implication |
|---|---|---|
| `good.wav`, `good-transcript.json` | Intended synthetic speech is 4.32 seconds. ASR returned “o pano acabou” instead of “O pão acabou”. | A known-good source can produce a transcript discrepancy. Listen before deciding that speech is wrong. |
| `wrong.aiff`, `wrong-review/review.json` | Actual different speech was recognized as “Boa noite, Bruno, a porta ficou aberta e o cachorro fugiu.” PCM RMS approximately 0.176. | Correctly exposes a large script/transcript discrepancy requiring review; not a subjective voice judgement. |
| `missing.wav`, `missing-review/review.json` | Decoded peak and RMS are exactly zero. ASR nevertheless hallucinated `[MÚSICA DE FUNDO]`. | PCM establishes silence here. ASR alone is not evidence of speech or background music. |
| `good-av.mp4`, `good-av-review/review.json`, `good-av-sheet-0.jpg` | Actual AAC extraction retained speech and the same pão/pano recognition error. Burned subtitles visible from 0.12 through 4.28 seconds in inspected frames; absent at 4.32 seconds. Cue metadata is 0.10–4.32 seconds. | Coarse subtitle envelope has supporting evidence. Voice quality, exact words and lip-sync remain unapproved. |
| `subtitle-delayed.mp4`, `subtitle-delayed-review/review.json`, `subtitle-delayed-sheet-0.jpg` | Same audio; subtitles absent during the speech and appear at 5.00 seconds through the end. Metadata is 5.00–9.00 seconds; helper reports no overlap with transcribed speech. | Visible subtitle timing defect, with cue metadata and actual rendered-frame corroboration. |
| `identity-story-error.mp4`, `identity-story-error-sheet-0.jpg` | Inspected frames show BRUNO/red/box, whereas reference frames show ANA/blue/mug. Speech and subtitles still address Ana and coffee. | Actionable symbolic character/prop/story mismatch. Requires visual correction while preserving approved speech. |

Existing `*-signals.json` outputs mark the intentionally static drawings as frozen. That advisory signal is expected for these fixtures and does not by itself establish a defect. No speech, facial motion or acting exists in their drawings.

## Evidence-linked correction routes

- For the wrong-speech fixture, retain the approved speech and reject the generated version after confirming by listening. Read the current version and authoritative job/batch state before requesting another generation through the embedded Agent. Generation requires the approved quote and attempt allowance. Do not rewrite the approved script merely to match erroneous output.
- For the symbolic identity/story defect, the reference and defective contact sheets identify the exact character label, costume and prop differences. Use existing version selection when a correct candidate exists; otherwise request a bounded visual regeneration through existing production tools. `patch_episode_script` is appropriate only if an editorial correction to the intended script is actually approved.
- For a supported placement/trim/source-volume correction, use `read_timeline` then `edit_timeline` with its current revision and affected clip IDs. Inspect the resulting export again. Moving the whole clip is not a correction for subtitle-only delay.
- Precise individual subtitle-cue retiming is not established by the existing timeline operations. The observed synthetic subtitle-only delay identifies that limitation; this work does not add a second subtitle system. A production defect of the same kind must be reported precisely for the conditional subtitle-alignment follow-up.

## Validation and remaining criteria

`uv run python -m pytest tests/unit/scripts/test_inspect_audio_evidence.py tests/integration/scripts/test_inspect_audio_evidence.py -q`: 9 passed. The integration cases create and inspect actual silent PCM and an actual video without an audio stream. Unit cases cover matching/wrong/missing speech, subtitle delay and repeated-line ambiguity. Targeted Ruff and basedpyright passed.

The real local inference and rendered fixture inspection above are separate from those automated tests. All findings remain `requires_review`. Missing evidence is never a passing result.

Independent Codex review found no concrete code defect, reran the nine tests, inspected all three contact sheets and separately ran local Whisper on `subtitle-delayed.mp4`. Its evidence is retained as `independent-subtitle-delayed-review/review.json`; it reproduced the nonzero PCM, pão/pano mismatch and subtitle no-overlap finding.

Subsequent work demonstrated actual audio/video provider input on controls and the native H3 technical sample, alongside full-file local decoding. See [the six-call characterization](evidence/10-multimodal-trial.md), [captured four-case diagnostic](evaluation-retest-proposal.md) and [offline validation](offline-review-validation.md). The controls exposed unsupported visual claims and hallucinations on digital silence; a narrower schema alone did not eliminate them. Offline checks reject demonstrated structural/signal contradictions, while free prose still requires semantic review. No human-review downgrade or alternate evaluator has been selected. The reference-led pilot, real human identity/continuity and intended voice/performance acceptance remain unproven. Segment timestamps, frames and confidence values do not certify phoneme-level lip-sync. #10 remains open while the sufficient-evidence workflow is being resolved; the successful H3 capability sample does not constitute #11 pilot acceptance.
