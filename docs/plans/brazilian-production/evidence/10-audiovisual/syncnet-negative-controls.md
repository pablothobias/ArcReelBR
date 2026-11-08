# SyncNet silence, unrelated-speech and static-face controls

Status: bounded local research completed, 2026-11-08. These three negative controls extend the [relative-shift exercise](syncnet-local-qualification.md). They provide evidence about discrimination on one generated H3 clip, not a production synchronization gate or resolution of #10.

## Finding

All three negatives had lower confidence and higher minimum distance than the unlabelled H3 baseline. Thus the predeclared scalar-order contradictions were **not observed in this small set**. This is useful relative separation, but the baseline has no verified synchronization ground truth, and these observations cannot establish an acceptance threshold.

Two results demonstrate why an offset or nonzero confidence cannot itself certify lip matching:

- **Exact silence:** all 31 distances were identical and confidence was zero, yet the algorithm returned **+600 ms**. This is its first-argmin tie behavior, not a measured synchronization error.
- **Static face:** one identical frame repeated throughout the video still yielded confidence **2.105045**, about 75.7% of the baseline's 2.781912, and a **−600 ms** minimum at the search boundary. There is no speech-related mouth motion in this control. A pronounced distance minimum can arise from the changing audio against a fixed visual embedding.

The unrelated Portuguese speech also produced a specific −320 ms estimate despite belonging to a different utterance. Its lower confidence/higher distance distinguish this instance relatively, but the offset does not establish correspondence between its phonemes and the visible mouth.

## Predeclared comparison

Before inference, `frozen-plan-and-media.json` fixed the inputs, hashes and interpretation criteria. Its SHA-256 is `028a8a8069055825e01cd6c286479108c7c5b17432f637ab513ccc39db358c17`.

The current [official algorithm](https://github.com/joonson/syncnet_python/blob/907c0b579c2e2d83f0eae1b2ac9e720cde4e5623/SyncNetInstance.py) takes the minimum mean embedding distance, reports `offset = vshift - argmin`, and defines confidence as `median(mean_distance) - minimum`. Lower minimum distance denotes closer learned embeddings; higher confidence denotes a more prominent minimum. Neither output is a calibrated probability of correct synchronization.

The frozen comparisons were:

1. Recompute the baseline using the exact former crop/window/features. Require its full curve to equal the previous baseline before interpreting any relative difference.
2. Retain all 31 distances, minimum/median/maximum, curve range, offset and confidence.
3. If a negative's confidence is at least the baseline's, the higher-confidence direction fails to separate that negative. If a negative's minimum distance is at most the baseline's, the lower-distance direction fails to separate it.
4. Even when these ordering contradictions are absent, do not invent a threshold or treat the baseline as synchronized. Silence has no speech signal and a repeated frame has no mouth motion, regardless of a returned offset or score.

These criteria probe obvious false-acceptance risks. They are not a demand for universal reliability and do not convert one unlabelled comparison into a positive ground-truth set.

## Fixed method and actual controls

The existing isolated installation, unchanged upstream code and complete checkpoint from the earlier research exercise were reused. Checkpoint SHA-256 remains `961e8696f888fce4f3f3a6c3d5b3267cf5b343100b238e79b2659bff2c605442`; source revision remains `907c0b579c2e2d83f0eae1b2ac9e720cde4e5623`. The prior document records MIT source terms, separate Oxford research-use permission and attribution to Joon Son Chung and Andrew Zisserman. No new weights, dependency or production-use clearance was introduced.

Each control is an actual lossless audiovisual MKV with 100 decoded 224 × 224 frames at 25 FPS and exactly 64,000 mono 16-bit PCM samples at 16 kHz: **4 seconds**. The same fixed manual ROI from the existing H3 source was retained. Derived files were decoded again and compared byte-for-byte to intended frame arrays and PCM before measurement.

| Condition | Video | Audio | Distinct decoded frames |
| --- | --- | --- | ---: |
| Unlabelled baseline | Existing H3 face, original 0.4–4.4 s | Existing H3 audio, original 0.4–4.4 s | 96 |
| Digital silence | Exactly the same moving frames as baseline | First 4 s of the existing zero-PCM control; all 64,000 samples zero | 96 |
| Unrelated speech | Exactly the same moving frames as baseline | Existing wrong-speech WAV, original 0.4–4.4 s; no padding | 96 |
| Static face | Original H3 face frame at 1.0 s, repeated 100 times | Exactly the same PCM as baseline | 1 |

The frozen frame was visually inspected; the face and mouth are inside the existing ROI. Repetition and the single unique decoded frame establish this fixture's lack of motion. No automated face tracking or mouth-landmark detector was added.

The network, MFCC calculation, batch size, distance function and aggregation match the earlier adapter. Every case produces 95 feature rows; mean distance uses rows 15–79 over ±15 offsets, so no zero-padded audio features enter the scored mean. Search resolution is 40 ms with limits ±600 ms. CPU execution used Python 3.10.22, PyTorch 2.5.1 and two Torch threads.

## Measurements

| Condition | Minimum distance | Median distance | Curve range | Confidence, uncalibrated | Offset frames / ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unlabelled baseline | 9.927547 | 12.709458 | 5.980814 | 2.781912 | −1 / −40 |
| Digital silence | 11.111341 | 11.111341 | 0 | 0 | +15 / +600 |
| Unrelated speech | 14.734548 | 16.610601 | 3.045793 | 1.876054 | −8 / −320 |
| Static face | 11.843157 | 13.948202 | 4.206181 | 2.105045 | −15 / −600 |

The baseline curve was **exactly equal, value for value**, to the earlier `unaltered-relative-window` curve. Therefore the relative comparison uses the same measured baseline rather than a changed crop or feature convention. The silence curve has exactly one repeated value across all offsets; a tiny nonzero float32 standard-deviation diagnostic is numerical residue, not temporal evidence.

The measurement completed in **6.292 seconds** after imports/checkpoint preparation and exited **0**, with its actual exit status persisted by the launching shell. There were no repeats of this four-case measurement and no further inference after results were inspected. The recomputed baseline was the sole repeated existing condition needed for comparability.

## Evidence and preservation

Private root: `/tmp/arcreel-goal-state/local-syncnet-qualification/negative-controls/`.

- `frozen-plan-and-media.json`: preregistered interpretation, source/checkpoint/previous-evidence hashes, derivation commands, media hashes and exact PCM/frame equivalence checks.
- `media/`: separately labelled baseline and three controls, WAVs and extracted frozen frame. Original production media were not changed.
- `measure.py`, `measurement-results.json`, `measurement.log`, `measurement-exit-code.txt` and `execution-receipt.json`: full curves, timing, exact command/environment and persisted exit provenance.

The measurement ran inside `/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)'`, with a minimal environment and an additional Python socket audit guard. No Python network attempt was recorded. No cloud request, upload, dependency installation, download, application-code change or harness change occurred.

| Derived audiovisual file | SHA-256 |
| --- | --- |
| `baseline-unlabelled.mkv` | `7c86ef2dd6467ef81e75d7836cb567294b3ba1837d5cb54a427ec3aa80223286` |
| `moving-face-digital-silence.mkv` | `2f176a137a26a168a3fc33ddb94fd30c93fadfa4226e3e66be0a2a7e277137ac` |
| `moving-face-unrelated-speech.mkv` | `263b1651ecb7d8e09f61d0838dd1b7be539761574e1ead974bcdf4bce2a48c7d` |
| `static-face-original-audio.mkv` | `25b780a683b4a0aa41674aeeaab8e635b8744d84eaaf9ae03fef133e5a302fd2` |

Measurement script SHA-256: `2194b3cebf6bef8fa6e89128e50c85bc6b8c62c913318b70362359e44c80c177`. Results SHA-256: `d67512d21ca774433eaa8371268e686aba4502f4bfb33de2ec13dc601097a89e`.

After measurement, hashes confirmed unchanged H3 original (`79f540ee9f2258d836d24eac62a9927881d0c8911d151fec87f54c12e2ff58eb`), wrong-speech source (`2ad8bc1cad6d99ba85843d6902a70556a8a62b83ec50724aed77518d0723d59d`), silence source (`00ea5c7415d6fd1232a2bb551c00c253f90023abb0775f9d9a3e54d47da9bc9d`), checkpoint, upstream source and all previous experiment evidence covered by the frozen hash snapshot. No media binary is committed.

## Consequence for the proposed evaluator

This exercise supports keeping SyncNet as **research evidence**, with explicit abstention conditions, rather than treating its raw offset/confidence as a pass:

- Exact zero PCM supplies no spoken synchronization evidence; a flat curve's tie-selected offset is meaningless.
- A known static mouth supplies no phoneme-motion evidence. A high score cannot override that input fact. General motion visibility/coverage detection is still unimplemented and unqualified.
- A minimum at the search boundary is unresolved within this search window. It cannot justify a precise correction or quality acceptance.
- Other cases remain unqualified; absence of these abstention conditions is not a passing rule. Expected speech still requires separate recognition, and matching utterance text does not establish matching mouth motion.

These are interpretation recommendations, not application changes. The three negatives are useful additions to qualification, but they leave false-acceptance rates, independent positive synchronization labels, held-out PTBR material, multiple faces/occlusion, identity, acting and creative acceptance unresolved. #10 remains open.

## Independent read-only review

A separate reviewer decoded all four videos and WAVs, verified their frozen hashes, 100-frame/64,000-sample sizes and static/silence properties, checked exact equality with the previous baseline curve, verified the shell-recorded exit 0, and inspected the score/window/index math. The reviewer found no blocking inconsistency and agreed that the observed relative ordering adds evidence beyond shift sensitivity without qualifying a lip-matching threshold. No model inference or provider call was performed by the reviewer.
