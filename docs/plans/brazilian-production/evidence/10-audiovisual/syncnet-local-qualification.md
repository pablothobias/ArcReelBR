# SyncNet local research qualification

Status: bounded local CPU research exercise completed, 2026-11-08. Both introduced shifts met the predeclared relative-sensitivity criterion. This is not a calibrated production lip-sync gate. No paid API, upload, generation, repository dependency or production configuration change.

## Rights and reproducibility boundary

The official [SyncNet source](https://github.com/joonson/syncnet_python) is pinned at `907c0b579c2e2d83f0eae1b2ac9e720cde4e5623`. Its [code license](https://github.com/joonson/syncnet_python/blob/907c0b579c2e2d83f0eae1b2ac9e720cde4e5623/LICENSE.md) is MIT. That does not establish checkpoint rights.

The separate [Oxford model page](https://www.robots.ox.ac.uk/~vgg/software/lipsync/) permits research use and links [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This exercise uses that explicit research permission, preserves attribution to Joon Son Chung and Andrew Zisserman, and cites their *Out of time: automated lip sync in the wild*, ACCV workshop, 2016. It establishes no commercial production clearance. The official downloader identifies `syncnet_v2.model`; only that checkpoint is requested. S3FD detector weights are excluded because their separate permission was not established.

Private evidence root: `/tmp/arcreel-goal-state/local-syncnet-qualification`. It contains the pinned source, original license-page snapshots and SHA-256 hashes, package-manager environment/lock, preparation script, predeclared plan and measurement adapter. The upstream source is unmodified. The isolated CPU environment uses Python 3.10.22, PyTorch 2.5.1, NumPy 2.2.6, SciPy 1.15.3, OpenCV 4.13.0.92 and python_speech_features 0.6. The [official CPU environment](https://github.com/joonson/syncnet_python/blob/907c0b579c2e2d83f0eae1b2ac9e720cde4e5623/environment-cpu.yml) specifies Python 3.10 and PyTorch 2.5.1; the [implementation](https://github.com/joonson/syncnet_python/blob/907c0b579c2e2d83f0eae1b2ac9e720cde4e5623/SyncNetInstance.py) explicitly supports CPU. Only dependencies needed for the manual-ROI path were installed using `uv`; the unused detector/scene pipeline was not installed. No global package or repository dependency is changed.

The complete official checkpoint is 54,573,114 bytes, SHA-256 `961e8696f888fce4f3f3a6c3d5b3267cf5b343100b238e79b2659bff2c605442`. An initial full transfer ended prematurely and was never loaded. Eight validated HTTP byte ranges from the same official endpoint produced the complete file. The adapter uses `weights_only=True` and strict state-dictionary loading; missing or unexpected model parameters would fail rather than retain random initialization.

## Authorized input and preparation

The existing five-second native-audio H3 source has SHA-256 `79f540ee9f2258d836d24eac62a9927881d0c8911d151fec87f54c12e2ff58eb`. Its original audiovisual alignment is unknown. Drawings from the earlier fixtures are not talking-face controls and are excluded.

Bundled FFmpeg derives the original interval 0–5 seconds at 25 FPS and 16 kHz mono PCM, with a fixed manual face ROI `(x=330, y=360, width=720, height=720)` resized to 224 × 224. Source bytes remain unchanged. Derived frame `n` targets source time `n/25`; original 24 FPS source selection introduces up to half a source frame of sampling quantization. Audio sample `k` maps to original `k/16000`. No synchronization correction is applied.

All 125 derived face frames were inspected through five consecutive contact sheets. The single face and mouth remain inside the ROI; transient steam crosses part of the face. This is manually reviewed spatial coverage, not an automated detector, face track, mouth-landmark measurement or identity validation. The standard automatic S3FD pipeline remains unqualified.

## Predeclared exploratory exercise

Before any model output, freeze these comparisons and retain the full distance curves:

- Video always uses original 0.4–4.4 seconds. Audio uses original 0–4, 0.4–4.4 and 0.8–4.8 seconds, introducing relative delays of +400, 0 and −400 ms without padding the waveform.
- Reuse the official network, MFCC preparation and distance function. Score only feature rows 15–79 over a ±15-frame search, so every compared audio feature is real rather than zero padding.
- The official reported offset is `vshift - argmin`. Thus delayed audio should produce a negative reported offset change, representing the correction direction.
- Exploratory success requires the expected direction and an estimated relative change within two 25 FPS frames, or 80 ms, of the injected shift. This is not a production acceptance threshold or a calibrated confidence rule.

Even successful relative-shift sensitivity would not establish that the original is synchronized, that speech matches the intended Portuguese, or that acting, identity and narrative quality are acceptable. A failed transfer, model load, crop or measurement remains missing evidence.

## Actual measurements

| Input condition | Reported offset, frames | Relative change from baseline | Expected change | Error | Uncalibrated confidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| Audio delayed 400 ms | −11 | −10 | −10 | 0 frames | 3.66594 |
| Original relative window | −1 | 0 | 0 | Not a ground-truth test | 2.78191 |
| Audio advanced 400 ms | 9 | 10 | 10 | 0 frames | 1.38926 |

The CPU measurement completed in 2.13 seconds after imports/checkpoint preparation, using two PyTorch CPU threads. Both introduced shifts met the predeclared direction and 80 ms error criterion with zero relative frame error. `measurement-results.json` retains all 31 values of each offset-distance curve, the exact scored rows, runtime and window mapping. `media-manifest.json` retains source/derivative hashes, and confirms the original source stayed unchanged. `qualification-summary.json` retains license, checkpoint, adapter and lock hashes.

The baseline's reported −1 frame is an uncalibrated model estimate on an unlabeled generated clip, not a verified −40 ms defect or a reason to edit it. The search spans ±15 frames, or ±600 ms, with 40 ms output quantization. It uses only one manually cropped, single-face clip and partly non-speaking footage. Source resampling, steam, crop geometry, generated mouth motion and limited speech duration constrain interpretation. No confidence threshold, false-acceptance rate, real synchronized reference, held-out PTBR set, occlusion/multiple-face control, voiceover control or automated face-track acceptance has been established.

Shifting the same underlying pair can translate an arbitrary stable distance minimum even when it does not represent correct mouth-to-speech correspondence. Thus this passing exercise primarily establishes indexing and relative-shift sensitivity. It does not validate lip matching. Held-out silence, unrelated-speech and static-face controls are needed before interpreting scores or selecting accuracy/confidence thresholds.

Result: local relative-offset measurement is technically feasible and sensitive to these introduced shifts. Qualification of a general automatic synchrony decision remains open. A next qualification needs authorized real-face material with independently annotated alignment and predeclared held-out controls; it must not label this H3 baseline as synchronized merely because relative shifts were detected.
