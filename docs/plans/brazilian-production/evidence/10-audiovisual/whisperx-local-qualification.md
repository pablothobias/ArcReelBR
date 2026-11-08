# Bounded local WhisperX qualification

Date: 2026-11-08. Scope: four existing audio inputs, CPU recognition followed by Portuguese alignment of **recognized text only**. This is new local evidence for #10, not a complete audiovisual evaluator or production integration.

## Result

Both runs returned empty recognition for exact digital silence and the complete expected word sequences for wrong speech, good speech and the H3 native-audio sample. Good speech contained **pão**, correcting the earlier base-model observation of **pano** on this control. H3 recognition retained “O café está pronto”, which the closed Pro trial omitted. The raw ASR and aligned JSON files were byte-identical across both runs.

The first process saved all outputs and then exited **139**. The macOS crash report identifies SIGSEGV in an ONNX Runtime native event/telemetry thread. A subsequent no-inference JIT-VAD load/teardown probe and one repeated four-case run, with ONNX telemetry explicitly disabled and native networking denied, both exited **0**. Those two environment changes were combined; this does not isolate the crash cause or establish long-term process stability.

One strict timestamp-bound check found a **0.4375 ms** overrun: final word `fugiu.` ends at `4.566`, while PCM duration is `4.5655625` seconds. This is consistent with rounding to milliseconds, but the raw violation is retained. All other reported word boundaries were finite, nonnegative, ordered and within their PCM durations. No reference word-boundary annotations exist, so these checks do not establish timestamp accuracy.

No paid API, model substitution, media upload, production modification or global installation occurred. The original repository environment, dependency manifests and lockfiles were unchanged.

## Frozen inputs and criteria

Before inference, `frozen-observation-criteria.json` recorded silence contradictions, complete wrong/good/H3 word sequences for later comparison, the pão/pano distinction, duration/ordering checks and the absence of timing ground truth. Its SHA-256 is `7984108c1c8b658c258cae0d3d9932f9c26b274c53f252dc6a2cde0de05dea2c`.

The inference scripts never read the criteria, expected dialogue, prior transcript or project script. Language was fixed to `pt`; `initial_prompt`, `prefix` and `hotwords` were null, with `condition_on_previous_text=false`. Alignment received only the raw recognized segments. Comparison against the frozen words happened afterward.

| Case | Existing bytes reused | PCM duration, seconds | SHA-256 |
| --- | --- | ---: | --- |
| Silence | Existing `audio/missing.wav`; same control as the Pro trial | 4.5 | `00ea5c7415d6fd1232a2bb551c00c253f90023abb0775f9d9a3e54d47da9bc9d` |
| Wrong speech | Exact existing `audiovisual-research/case-1ea5cb52ec97/actual-audio.wav` submitted to the Pro trial | 4.5655625 | `2ad8bc1cad6d99ba85843d6902a70556a8a62b83ec50724aed77518d0723d59d` |
| Good speech | Existing `audio/good.wav` | 4.345 | `fb4f7de5eee89d4b84cfbe9aaebf5a0b19c36f234686a7e2e2aa43510b937ec8` |
| H3 native audio | Existing `media-preflight/native-audio-review/audio.wav` | 5.184 | `c705192fdaf6cb30338f41809cf0ca04c7ebd83bcb88c0326476edfd65f69c3e` |

All inputs are mono 16-bit PCM at 16 kHz. The H3 MP4 source hash was rechecked as `79f540ee9f2258d836d24eac62a9927881d0c8911d151fec87f54c12e2ff58eb`. Its existing extraction receipt reports MP4 duration 5.167 seconds and decoded PCM duration 5.184 seconds; the test uses the full existing PCM. This PCM hash was first recorded during this qualification, not retroactively asserted as a historical receipt. Existing source files were copied without changing bytes. The earlier [local evidence](../../audiovisual-review.md) supplies provenance and limitations.

## Isolated environment and rights reviewed

All environment, caches, downloads, scripts and raw results live under `/tmp/arcreel-goal-state/local-av-qualification/`. Host architecture was macOS arm64. The already installed Python 3.12.16 and uv 0.13.7 created a private virtual environment; package resolution selected 103 packages. No repository dependency was added, so repository-wide dependency gates were not run.

| Component | Pinned selection | Rights/source checked |
| --- | --- | --- |
| WhisperX | 3.8.6, stable PyPI release | [PyPI version metadata](https://pypi.org/pypi/whisperx/3.8.6/json), [BSD-2-Clause source](https://github.com/m-bain/whisperX/blob/v3.8.6/LICENSE) |
| ASR weights | `Systran/faster-whisper-small`, revision `536b0662742c02347bc0e980a01041f333bce120` | [Pinned model card](https://huggingface.co/Systran/faster-whisper-small/blob/536b0662742c02347bc0e980a01041f333bce120/README.md) declares MIT and lists Portuguese |
| Alignment weights | `jonatasgrosman/wav2vec2-large-xlsr-53-portuguese`, revision `634ac655299bcdc46c83bc01da9bab52d2987e4f` | [Pinned model card](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-portuguese/blob/634ac655299bcdc46c83bc01da9bab52d2987e4f/README.md) declares Apache-2.0, Portuguese training and 16 kHz input |
| VAD code and weights | `silero-vad==6.2.1`, packaged JIT model | [Official project](https://github.com/snakers4/silero-vad), installed distribution MIT notice; no gated model or token |
| Inference libraries | faster-whisper 1.2.1; CTranslate2 4.8.5; torch/torchaudio 2.8.0; transformers 4.57.3 | Exact installed metadata/lock retained privately; CPU `int8` capability confirmed by CTranslate2 |
| Imported ONNX runtime | 1.31.1 | Transitive dependency imported despite JIT VAD; explicit telemetry-disable API used in repeat |
| Sentence segmentation | NLTK 3.10.4 and official `punkt_tab` archive | Archive SHA-256 matched official NLTK index; Portuguese model identified as Brazilian CETENFolha in bundled README. Separate pretrained-tokenizer distribution terms were not established here; do not treat this experiment as a cleared production redistribution bundle |

WhisperX [explicitly maps Portuguese to this aligner](https://github.com/m-bain/whisperX/blob/v3.8.6/whisperx/alignment.py). CPU macOS execution is documented in the [official README](https://github.com/m-bain/whisperX). Actual local execution confirms this selected package combination can produce results; it does not validate Apple MPS acceleration.

Only the necessary ASR/aligner files were downloaded, without Flax weights or the optional language model. Public model downloads required no credentials. Their large-file hashes matched Hugging Face's revision metadata:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| ASR `model.bin` | 483,546,902 | `3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671` |
| Aligner `pytorch_model.bin` | 1,262,122,456 | `c244caf8395a0c333bdc877e7b62ce5efea12ad8cfec0851c0fe6efb844b834e` |
| Packaged Silero `silero_vad.jit` | 2,272,526 | `e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720` |

WhisperX's default Silero constructor fetches mutable torch.hub source. The private probe instead supplied a `Silero` subclass through WhisperX's existing `vad_model` argument. Its constructor loaded the pinned package's JIT weights; inherited speech detection, preprocessing and chunk merging were unchanged. This is an explicit experiment adapter, not an unmodified default CLI run. No pyannote diarization or gated weights were loaded.

TorchCodec warned that FFmpeg shared libraries were unavailable. No FFmpeg installation or library-path change was made. The test used existing PCM loaded by Python `wave` into memory, avoiding the unavailable decoder as the warning itself recommends.

## Actual observations

Punctuation/case are excluded only from the post-inference word comparison. Raw strings, scores, character alignments and exact JSON remain unchanged.

| Input | Raw ASR text, leading space omitted here | Aligned words | Initial ASR / alignment, seconds | Repeat ASR / alignment, seconds |
| --- | --- | ---: | ---: | ---: |
| Silence | Empty text and empty segments | 0 | 0.094 / <0.001 | 0.100 / <0.001 |
| Wrong speech | `Boa noite, Bruno. A porta ficou aberta e o cachorro fugiu.` | 11 | 0.936 / 0.448 | 1.236 / 0.531 |
| Good speech | `Bom dia, Ana. O pão acabou, mas o café está quentinho.` | 11 | 0.883 / 0.294 | 0.986 / 0.352 |
| H3 native audio | `Bom dia! O café está pronto!` | 6 | 0.710 / 0.196 | 0.856 / 0.243 |

Initial ASR/alignment model loading took 1.304 / 0.577 seconds; repeat loading took 1.057 / 0.682 seconds. Script wall times before process teardown were 16.124 and 14.375 seconds, including imports/loading. These are two warm-machine observations on short files, not a throughput benchmark.

The silent PCM contained exactly zero nonzero samples; no recognized speech was returned in either run. That negative-control result does not mean VAD can prove speech absence on nonzero audio. The wrong speech matches its deliberately different recorded phrase, not the approved good phrase. Good speech and H3 match their existing reference word sequences; this is not a measurement of voice quality or delivery.

Selected raw intervals illustrate the evidence and limits:

- Wrong speech: `Boa` 0.074–0.315; `Bruno.` 1.077–1.498; `fugiu.` 4.065–4.566 seconds. The final boundary exceeds PCM by 0.0004375 seconds and is flagged, without silently clamping it.
- Good speech: `pão` 1.558–1.758; `café` 2.961–3.322; `quentinho.` 3.703–4.345 seconds.
- H3: `Bom` 0.499–0.680; `dia!` 0.801–1.143; `O` 1.345–1.385; `café` 1.445–1.748; `está` 1.788–1.969; `pronto!` 2.070–2.654 seconds.

These intervals are model estimates with uncalibrated scores. No word/phoneme gold alignment or visible-mouth evidence was used. They cannot certify speech onset accuracy, lip-sync, acting, identity, subtitles or audiovisual acceptance.

## Process failure, repeat and network boundary

The first run returned all four case results and wrote its final summary before SIGSEGV. The OS crash summary names `onnxruntime_pybind11_state.so` with frames under `Microsoft::Applications::Events`, including `TransmissionPolicyManager::uploadAsync`. This supports investigating native telemetry/event teardown; it does not prove the exact root cause or demonstrate an actual upload.

The first script's Python audit hook denied Python socket/DNS operations and recorded zero attempts. **That hook cannot attest absence of native-library network traffic.** Hugging Face and pyannote telemetry were disabled, but ONNX telemetry had not yet been explicitly disabled. No script path sent media to a service. The stronger repeat used the same local-only input/model paths plus:

```text
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)'
onnxruntime.disable_telemetry_events() before WhisperX/Silero imports
```

A separate loopback socket negative control under that sandbox failed with `PermissionError: [Errno 1] Operation not permitted`. The no-inference VAD load/teardown probe exited 0. The repeated four-case process also exited 0 and again recorded zero Python network attempts. No model or inference-option change occurred. Both raw-ASR and aligned output bytes matched across runs for every case. One clean exit is insufficient to label the original native failure fixed.

## Commands and retained receipts

Private setup inputs were:

```text
whisperx==3.8.6
silero-vad==6.2.1
transformers==4.57.3
```

The package manager produced and installed the complete pinned dependency set:

```bash
UV_CACHE_DIR=/tmp/arcreel-goal-state/local-av-qualification/uv-cache \
  uv pip compile /tmp/arcreel-goal-state/local-av-qualification/requirements.in \
  --python 3.12 --output-file /tmp/arcreel-goal-state/local-av-qualification/requirements.txt
UV_CACHE_DIR=/tmp/arcreel-goal-state/local-av-qualification/uv-cache \
  uv venv /tmp/arcreel-goal-state/local-av-qualification/venv --python 3.12
UV_CACHE_DIR=/tmp/arcreel-goal-state/local-av-qualification/uv-cache \
  uv pip sync /tmp/arcreel-goal-state/local-av-qualification/requirements.txt \
  --python /tmp/arcreel-goal-state/local-av-qualification/venv/bin/python
```

`requirements.txt` SHA-256: `0104ee5091e9612184e3814a4cf94bab7010e747632275f2aa411b02914bb9a1`. Installed freeze SHA-256: `cea90e26bc0cfb031982a154617b5af03aa061fa839e8a706eea2de5a0fbc21a`.

Both scripts ran with an explicit minimal environment via `env -i`, private `HF_HOME`, `TORCH_HOME`, `NLTK_DATA` and `MPLCONFIGDIR`, offline Hugging Face/Transformers flags, disabled dotenv, and disabled Hugging Face/pyannote telemetry. Runtime parameters were CPU `int8`, four threads, batch size 1, Portuguese transcription, no expected-text priming and alignment of recognized segments only. The repeat added the OS network sandbox and ONNX telemetry disable described above.

Private evidence is retained under `/tmp/arcreel-goal-state/local-av-qualification/`:

- `input-manifest.json`, frozen criteria, `metadata/`, model download manifests and `source-artifact-hashes.json`.
- `requirements.in`, generated lock/freeze, resolve/install/import logs and exact inference scripts.
- `results/` and `results-repeat/`: raw ASR, complete aligned JSON, configuration, durations, PCM statistics, per-case wall times and post-inference comparisons.
- `crash-summary.json`, no-inference probe log, network sandbox control, `repeat-equality.json` and `qualification-receipt.json` with observed exits 139/0/0 and artifact hashes.

Initial inference script SHA-256: `cf39c48852470e602a548e4f2cbabec4bf16dcf69511d41a9dbdf94814b630bd`. Repeat script SHA-256: `e9a486a9f99b2957747e5a6295ca04720b226b58c7022e6accc586cd82b9af74`. No media/model binaries are committed.

## Decision supported by this exercise

WhisperX supplies useful new local recognition and word-alignment evidence on these four controls. It deserves further bounded qualification as a speech-evidence component. This experiment does not clear its dependency bundle for production redistribution, establish general PTBR accuracy or resolve native runtime stability. It does not evaluate real video, lip-sync, identity/continuity, performance, quality or visible subtitle timing. Keep #10 open and preserve the independent media-fact guards; do not promote these observations into an automatic quality pass.
