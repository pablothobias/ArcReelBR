# Reproducing local audiovisual evidence

These are sanitized results of actual local fixture inference and rendered-frame inspection, not a passing production review. `actual-review-results.json` retains observed Portuguese text, approximate timestamps, PCM measurements, findings and gaps. `fixture-manifest.json` identifies the original media and model by SHA-256. Actual original files remain local at `/tmp/arcreel-goal-state/audio/` and are not committed.

## Build fixtures

Supply local recordings with known content. The good recording must say “Bom dia, Ana! O pão acabou, mas o café está quentinho.” The deliberately wrong recording used here says “Boa noite, Bruno! A porta ficou aberta e o cachorro fugiu.” Neither is supplied as an ASR prompt.

On macOS with the existing Luciana voice, the original synthetic speech can be recreated without a paid provider:

```bash
say -v Luciana -o /tmp/good.aiff 'Bom dia, Ana! O pão acabou, mas o café está quentinho.'
say -v Luciana -o /tmp/wrong.aiff 'Boa noite, Bruno! A porta ficou aberta e o cachorro fugiu.'
```

On other platforms use recordings of those phrases from an available authorized local source. From the repository root, choose a new output directory and run:

```bash
uv run python -m scripts.build_av_review_fixtures \
  --good-audio /tmp/good.aiff --wrong-audio /tmp/wrong.aiff \
  --output /tmp/av-fixtures
```

The builder has no macOS dependency. It uses the bundled font for visual labels and subtitles, supplied local audio, the existing ASS subtitle generator, bundled ffmpeg, contact-sheet builder and technical-signal detector. It creates three actual 540 × 960 MP4s, silence, cue metadata, expectations, contact sheets and signal JSON. It refuses an existing output directory. It changes no project or production artifact.

The original run used Arial for the symbolic figure labels, whereas the portable builder uses the bundled subtitle font. Media hashes therefore identify the historical original files rather than requiring byte equality across reproductions. TTS/encoder/platform versions can also change bytes. Judge the observable fixture behavior and record the new hashes.

## Run actual local inference

Install `whisper-cli` separately and provide the downloaded multilingual model. The original model hash and size are in the manifest; this repository does not download it automatically. With `/path/to/ggml-base.bin` replaced by that existing model path:

```bash
uv run python -m scripts.inspect_audio_evidence \
  --media /tmp/av-fixtures/good-av.mp4 --model /path/to/ggml-base.bin \
  --expected /tmp/av-fixtures/expected.json \
  --subtitle-cues /tmp/av-fixtures/good-av-cues.json --output /tmp/av-good-review

uv run python -m scripts.inspect_audio_evidence \
  --media /tmp/av-fixtures/subtitle-delayed.mp4 --model /path/to/ggml-base.bin \
  --expected /tmp/av-fixtures/expected.json \
  --subtitle-cues /tmp/av-fixtures/subtitle-delayed-cues.json --output /tmp/av-delayed-review

uv run python -m scripts.inspect_audio_evidence \
  --media /tmp/av-fixtures/wrong.wav --model /path/to/ggml-base.bin \
  --expected /tmp/av-fixtures/expected.json --output /tmp/av-wrong-review

uv run python -m scripts.inspect_audio_evidence \
  --media /tmp/av-fixtures/missing.wav --model /path/to/ggml-base.bin \
  --expected /tmp/av-fixtures/expected.json --output /tmp/av-missing-review
```

Inspect the MP4s and contact sheets against `reference.png`, actual PCM, raw transcript JSON and cue metadata. The delayed fixture should expose captions only after speech. The defective symbolic figure should show BRUNO/red/box instead of ANA/blue/mug. Those simple contrasts do not establish real-face continuity, listening quality, acting, lip-sync or full playback evaluation. Whisper can produce a false mismatch on correct speech and hallucinate content on zero PCM. Keep these limitations and all remaining criteria from [the review record](../../audiovisual-review.md).

Validation of the portable builder: executed against the original good/wrong recordings with a fresh local output directory; all three MP4s, contact sheets, signals, silence and metadata were produced. No model or media binary is included in this evidence directory.
