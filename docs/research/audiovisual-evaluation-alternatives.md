# Audiovisual evaluation alternatives for Brazilian production

Research date: 2026-11-08. Decision support for issue #10, not an implementation or evaluator qualification. Only public documentation, public source and existing repository evidence were read. No installation, model inference, media upload, paid request, credential lookup or configuration change was performed.

## Finding and recommendation

No investigated tool establishes the complete requested automatic quality decision for ArcReel's Brazilian Portuguese, native-audio H3 videos. Several supply missing measurements. The smallest credible route is a composite inside the existing harness: retain deterministic media checks and local ASR, qualify Portuguese word alignment and a real audiovisual synchrony model, then trial one semantic video-understanding service against the same negative controls. Keep each result tied to its segment and actual input bytes. This is a research recommendation, not evidence that the composite works.

**First shortlist:** WhisperX for word alignment, the current official SyncNet implementation for local audiovisual offset measurements, and TwelveLabs Pegasus Models API for a separately bounded semantic comparison. **Second-line research:** Synchformer for event synchrony; selected VBench dimensions for temporal visual defects; Qwen3-Omni or video-SALMONN 2 Pro if suitable GPU infrastructure is available. MCPs and skills can simplify access but do not independently validate perception.

Do not mark #10 complete, silently substitute another generic model, or replace the requested automatic capability with human final approval. Independent annotations during qualification provide test ground truth; they do not change the production acceptance policy.

## Existing evidence and exact gap

[Local audiovisual review](../plans/brazilian-production/audiovisual-review.md) establishes actual PCM extraction, Portuguese whisper.cpp inference, rendered subtitle inspection, contact sheets and technical signals. The drawings exercise symbolic label/costume/prop changes, not real-face identity or mouth motion. [The diagnosis](../plans/brazilian-production/evaluation-diagnosis.md) and [closed Pro comparison](../plans/brazilian-production/evaluator-options.md#separately-approved-pro-comparison-result) document invented perception on zero PCM, incorrect duration, incomplete H3 transcription and uncalibrated zero-offset claims. No inference allowance remains open through those records.

The objective requires separate evidence for actual spoken words, word timing, visible subtitle timing, speaker-mouth synchrony, visual identity/continuity, audio quality, and narrative/reference adherence. Container duration can refute 0.04 seconds for a 4.56-second file; ASR can still mishear words. A synchrony score cannot establish the intended words, and a good transcript cannot establish a synchronized mouth. A contact sheet cannot measure audiovisual timing.

## Integrate, adapt, or reject

“Integrate” means qualify an existing interface and add a thin evidence adapter if it passes. “Adapt” means selectively reuse licensed code with its preprocessing and model terms checked. Neither means importing another orchestration runtime.

| Candidate | Actual input and useful evidence | Decision for this workflow | Important limit |
| --- | --- | --- | --- |
| WhisperX | Actual audio; ASR, VAD and word alignment | **Integrate first**, initially as an isolated CLI/library probe | No visual input or lip-sync evidence; alignment does not verify supplied words |
| Official SyncNet | Audio and consecutive face-video frames; offset, confidence and distances | **Adapt thinly / qualify first** | Visible talking face needed; confidence is not calibrated quality acceptance |
| Synchformer | Actual audio/video temporal features; offset classes and synchronizability | **Reserve alternative** for visible sound events | Coarse offset classes and dataset/domain limits; not exact phoneme timing |
| LatentSync evaluator | Face video plus audio; SyncNet confidence | **Defer selective reuse**, reject whole generator as evaluator | Required preprocessing includes AV adjustment; can invalidate a raw-offset test |
| TwelveLabs Pegasus Models API | Uploaded video, audio/transcription context, reference images, structured segment analysis | **First external semantic trial**, conditional on explicit trial approval | Portuguese is partial support; no documented calibrated phoneme-sync guarantee |
| TwelveLabs plugin / Jockey MCP | Agent-facing access to cloud video understanding and clip citations | **Optional access integration**, prefer Models API for a fixed clip test | Wrapper adds no reliability; Jockey is a separate cloud agent/service |
| VideoDB skills / MCP / SDK | Cloud speech/scene indexing, timestamped retrieval and editing | **Defer**, useful if hosted retrieval becomes necessary | Overlaps existing media plumbing; no demonstrated quality acceptance or lip-sync scoring |
| Qwen3-Omni | Joint actual audio/video, Portuguese speech input | **GPU-side semantic alternative**, not an immediate Mac default | Large BF16 footprint; generic understanding benchmarks do not qualify this task |
| video-SALMONN 2 Pro | Joint audio/video captioning and QA; 4B/8B/32B variants | **Secondary open-model probe** | PTBR task accuracy and Mac execution unverified |
| Selected VBench / VBench++ metrics | Decoded video frames/features; subject/background consistency, flicker and related dimensions | **Adapt selected metrics later** | Visual proxies cannot hear speech or certify script, real identity or acting |
| DNSMOS | Actual audio waveform; speech/noise/overall quality proxies | **Optional diagnostic only** | Noise-suppression MOS proxy, not acting, accent, semantic correctness or music mix approval |
| PaddleOCR | Rendered subtitle-region frames | **Optional local supplement** for burned subtitle verification | Text observation alone supplies neither speech timing nor synchrony |
| AV-HuBERT | Actual audiovisual speech representation | **Reject for production integration** | Archived; custom license restricts use to noncommercial research and prohibits production |
| EvalCrafter | Visual generation benchmark metrics | **Reject code copying for now** | No repository license found in inspected source; redundant visual scope |
| AVE-Agent / AVE-Compass | Editing agent plus mixed MLLM/objective evaluation | **Reject wholesale adoption**; study methodology only | Official evaluator uses Gemini; no top-level code license found; different editing benchmark |

The candidate-specific sources and qualifications below support this table. No benchmark number is treated as an ArcReel acceptance threshold.

## Speech and subtitle evidence

### WhisperX

The [official README](https://github.com/m-bain/whisperX) documents VAD, word-level alignment, CPU execution on macOS using `--device cpu --compute_type int8`, and a BSD-2-Clause code license. Its warnings include alignment problems for unsupported dictionary characters and overlapping speech. This is a plausible local addition, with CPU latency and dependency compatibility still to measure. It needs PyTorch, audio/model libraries and downloaded checkpoints; no metered API is required. MPS acceleration is not established by these instructions.

The [alignment source](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py) explicitly maps `pt` to `jonatasgrosman/wav2vec2-large-xlsr-53-portuguese`. The [checkpoint card](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-portuguese) declares Apache-2.0, Portuguese Common Voice fine-tuning and 16 kHz input. This establishes Portuguese support, not Brazilian accent/acting accuracy. Optional diarization introduces separate models and terms; it is unnecessary for a first single-speaker test.

Keep recognition blind to expected dialogue. Align recognized words first, compare against the approved script, and report missing/ambiguous words. Force-aligning the expected script into wrong speech can create plausible-looking timestamps for words never spoken. Test pão/pano, names, numbers, overlap, pauses and clipped endings. Never let alignment override exact zero-PCM evidence.

### Burned subtitles and OCR

[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) has Apache-2.0 code; its [official multilingual recognition documentation](https://paddlepaddle.github.io/PaddleOCR/v3.1.0/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html) lists Portuguese. OCR of timestamped subtitle-region frames can corroborate what the rendered MP4 actually displays, supplementing existing cue metadata. Exact checkpoint terms, Paddle runtime support on this Mac and OCR accuracy on the existing font/background need checking before selection. Use existing rendered-cue evidence first to avoid a premature dependency.

Derive subtitle observations from the actual burned image sequence, compare first/last visible frames against audio word intervals, and retain frame-rate uncertainty. Do not build a parallel subtitle generator or modify approved text to match an erroneous recording.

## Real audiovisual synchrony

### Official SyncNet: first local qualification target

[The authors' repository](https://github.com/joonson/syncnet_python) supports audio-video synchronization and active-speaker use. The current [implementation](https://github.com/joonson/syncnet_python/blob/master/SyncNetInstance.py) uses actual video frames and audio MFCCs, assumes 25 FPS / 16 kHz, and selects CUDA when available or CPU otherwise. It returns offset, confidence and distances. This current source matters: older CUDA-only descriptions are no longer accurate. No working Apple MPS path or local speed was established here.

[Code terms are MIT](https://github.com/joonson/syncnet_python/blob/master/LICENSE.md). The repository downloads a pretrained model separately; no distinct weight license/model card was established during this investigation. Resolve that scope before redistributing weights. Local processing can avoid media transfer; checkpoint acquisition still requires a download. There is no metered evaluator fee, but compute and maintenance cost remain.

Use isolated face tracks and preserve the mapping from derived 25 FPS crops to original MP4 timestamps. Keep the original untouched. Side profiles, occlusion, small mouths, multiple speakers, voiceover, cuts, music and silence must produce bounded uncertainty rather than a zero-offset pass. The score is a learned matching signal, not a probability that a Portuguese phoneme is correct. The synthetic drawing fixtures cannot qualify it.

### Synchformer and LatentSync

[Synchformer](https://github.com/v-iashin/Synchformer) predicts offset from actual temporal audio/video features and includes synchronizability models. Its documented environment was tested on Linux NVIDIA CUDA and AMD ROCm, not Apple Silicon. Checkpoints cover LRS3 and general sound-event datasets. [Code is MIT](https://github.com/v-iashin/Synchformer/blob/main/LICENSE); separate checkpoint rights should be resolved before redistribution. [Example preprocessing](https://github.com/v-iashin/Synchformer/blob/main/example.py) explicitly accommodates vertical video. It predicts a class grid, so report class spacing and range instead of invented millisecond precision. Defer until SyncNet's speaking-face test indicates a need for event-based coverage.

[LatentSync's evaluation instructions](https://github.com/bytedance/LatentSync#-evaluation) provide sync confidence and accuracy scripts, but require its own affine/AV-adjustment preprocessing. Measuring after an alignment step could conceal the original defect. [Code is Apache-2.0](https://github.com/bytedance/LatentSync/blob/main/LICENSE), while the [1.6 weight repository declares OpenRAIL++](https://huggingface.co/ByteDance/LatentSync-1.6). These are different licenses. PTBR qualification and Apple support are unverified. Selectively inspect the evaluation route later; do not install its diffusion generator simply to obtain a score.

## Semantic video understanding and existing agent integrations

### TwelveLabs: strongest ready-made access candidate, still unqualified

[Pegasus 1.6 specifications](https://docs.twelvelabs.io/docs/concepts/models/pegasus/pegasus-1-6) list Portuguese as **partial** support, accept 9:16 video within a resolution range that includes 1080×1920, and support reference images and timestamped segment events. [The analysis guide](https://docs.twelvelabs.io/docs/guides/analyze-videos-and-images/videos) explicitly describes checking AI-generated clips against prompts and identifying visual defects. These are documented product capabilities, not evidence of reliable H3 acceptance or accurate word timing.

[The modality documentation](https://docs.twelvelabs.io/docs/concepts/modalities) distinguishes visual/OCR, non-speech audio and transcription for Models; Agents combines speech into audio. A test must enable and record the correct route. Uploading video is actual media access, but timestamped prose or retrieval does not establish high-frequency mouth/audio measurement.

Use the Models API through an isolated adapter for a frozen clip and reference, structured findings and bounded output. [Current public pricing](https://www.twelvelabs.io/pricing) shows Free 3 GB cumulative storage, Plus USD 29/month and Pro USD 99/month. [Published Pro overage](https://www.twelvelabs.io/overage) lists Pegasus 1.6 video analysis input at USD 1.75/hour and output at USD 7.50/million tokens, plus storage and other workload charges. The account's actual allowance and billing regime are unknown. These rates are not a complete trial quote or authorization; do not infer that a new account or request is free.

Media and derived data leave the Mac for TwelveLabs storage/processing. [Jockey's current product FAQ](https://www.twelvelabs.io/jockey/) describes deleting originals, indexes and metadata through library/account deletion. This does not establish contract retention periods, regional processing, training exclusion or zero-data retention for Models. Verify those if a real production upload is considered. Service/model access is proprietary, with no right to copy Pegasus weights inferred from SDK licensing.

Existing integration surfaces are concrete:

- [Official Claude Code plugin](https://github.com/twelvelabs-io/twelve-labs-claude-code-plugin): source includes commands, skills, hooks and MCP configuration, local-file asset upload, reference-image prompting and structured analysis. Its inspected README still defaults to Pegasus 1.5 or 1.2 in some paths. A plugin installation is not an exact-model trial. Its MIT code can inform a thin adapter subject to notices; inspect hooks and defaults before any reuse.
- [Official Jockey MCP](https://docs.twelvelabs.io/docs/advanced/model-context-protocol): remote HTTP/OAuth, knowledge-store management, cross-video questions and clip citations. Existing single-video tools moved to `mcp-alpic.twelvelabs.io`, while Jockey uses `https://mcp.twelvelabs.io/jockey/mcp`. Select the intended product explicitly. MCP transport support does not prove compatibility with ArcReel's configured external-tool permissions.
- [Current Jockey explanation](https://www.twelvelabs.io/blog/introducing-jockey) says it was rebuilt as a first-party service rather than the historical open-source LangGraph project. Do not clone that old orchestrator as the production evaluator. An extra library agent is unnecessary for a fixed short-clip comparison.

### VideoDB skills and MCP

[Official skills](https://github.com/video-db/skills) cover SDK-driven ingestion, understanding, search and editing and declare MIT code. They explicitly support coding agents including Codex; local file uploads use the SDK. The [official hosted MCP](https://mcp.videodb.io/) accepts public URLs, transcribes/indexes speech and scenes, returns moment timestamps and performs edits; media and indexes remain in the VideoDB account until deletion. This is real cloud media processing, not an offline model.

This could reduce hosted retrieval plumbing, but that is not the current missing capability. No documented calibrated PTBR lip-sync or automatic creative acceptance was established. The skills advertise introductory credits, but exact current per-workload prices were not verified; the [public pricing route](https://videodb.io/pricing) redirected to contact. Treat costs, downstream analyzer choice, PTBR coverage, retention and model terms as unresolved. Defer integration; do not copy a large skill bundle that can install dependencies, save keys and invoke unrelated generation tools merely to inspect a short clip.

### Open audiovisual models

[Qwen3-Omni's official model card](https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct) declares Apache-2.0, lists Portuguese speech input and demonstrates video with `use_audio_in_video=True`. Its BF16 table reports 78.85 GB for a 15-second Instruct video; disabling the talker saves about 10 GB. Its serving caveat requires separately passing audio/video where `use_audio_in_video` is unavailable. These details make a casual Mac replacement unjustified. GPU server integration is possible in principle; local Apple execution, quantized accuracy, hosted endpoint availability and cost were not verified. Self-hosting can keep media under owner control; third-party hosting changes that boundary.

[video-SALMONN 2 Pro 4B's card](https://huggingface.co/tsinghua-ee/video-SALMONN-2-Pro-4B) declares Apache-2.0 and joint audio/video QA/captioning; the [official repository](https://github.com/bytedance/video-SALMONN-2) includes 4B/8B/32B releases and vLLM support. This smaller option merits a later feasibility probe, but Portuguese accuracy, Apple acceleration, required memory, a maintained hosted API and rental price are unresolved. Inspect backbone/audio-encoder notices in addition to repository terms. Caption/QA benchmark results do not establish silence abstention, timing accuracy or H3 facial synchrony.

## Visual continuity and speech-quality proxies

[VBench's official implementation](https://github.com/Vchitect/VBench) supports custom videos and decomposed video-generation metrics; VBench++ includes image-to-video and long-video variants. [Its code license is Apache-2.0](https://github.com/Vchitect/VBench/blob/master/LICENSE), not the MIT license of an unrelated namesake. Adapt a few dimensions only after checking each encoder/weight license and GPU dependency. Subject consistency can miss an actor swap or reward an unchanged frame; temporal consistency can penalize intentional cuts. Compare known identity/prop/costume swaps and freeze controls before using any score. PTBR is irrelevant to purely visual features, but text-conditioned metrics need separate language validation. No Mac runtime or API price was established.

[DNSMOS](https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS) is a no-reference speech-quality proxy designed for noise suppressors. [Local source](https://github.com/microsoft/DNS-Challenge/blob/master/DNSMOS/dnsmos_local.py) uses ONNX Runtime, 16 kHz input and 9.01-second windows, repeating shorter recordings to fill a window. That matters for the short H3 sample. [Code terms are MIT](https://github.com/microsoft/DNS-Challenge/blob/master/LICENSE-CODE); model/data terms require separate inspection. It may diagnose noisy/processed speech, but does not judge Brazilian delivery, intended text or a good music mix. CPU feasibility is plausible from the ONNX interface, not locally verified. No metered service is needed for local inference.

## Rejections and unresolved rights

- [AV-HuBERT](https://github.com/facebookresearch/av_hubert) was archived on 2024-09-01. Its [custom license](https://github.com/facebookresearch/av_hubert/blob/main/LICENSE) permits noncommercial research and explicitly excludes production. Reject as a production component despite genuine audiovisual input.
- [EvalCrafter](https://github.com/EvalCrafter/EvalCrafter) is a visual generation benchmark. No top-level license was present in the inspected repository, and the public repository metadata returned no detected license. Public visibility is insufficient permission to copy. Prefer licensed alternatives for this overlapping scope.
- [AVE-Compass / AVE-Agent](https://github.com/NJU-LINK/AVE-Compass) is an editing benchmark/agent with MLLM and objective metrics. Its README routes MLLM evaluation through Gemini and reports checklist/realism metrics rather than this project's qualification. No top-level code license was found in the inspected tree. Study the decomposition of instruction execution and preservation, but do not copy source or import its orchestrator. Another Gemini-based wrapper does not resolve the observed controls.
- Generic frame-only “video review” prompts and transcript summarization skills do not measure real audiovisual synchronization. Tool or skill packaging cannot supply a modality the underlying evaluator never receives.

## Maintenance snapshot

Public GitHub repository and latest-commit API metadata were read on 2026-11-08. Dates below describe inspected default-branch source, not a promise of support or a qualified release. Full SHA links identify the inspected revision; licensing and API pricing should be rechecked before implementation.

| Source | Latest inspected commit date (UTC) | Revision |
| --- | --- | --- |
| WhisperX | 2026-10-22 | [5d3678b](https://github.com/m-bain/whisperX/commit/5d3678b8535698a2826a5db9eb3e4105aef85dd9) |
| SyncNet | 2026-04-17 | [907c0b5](https://github.com/joonson/syncnet_python/commit/907c0b579c2e2d83f0eae1b2ac9e720cde4e5623) |
| Synchformer | 2025-09-15 | [b66668a](https://github.com/v-iashin/Synchformer/commit/b66668a1521d7567cc760e5544b2b5b53179b687) |
| LatentSync | 2025-06-20 | [a229c39](https://github.com/bytedance/LatentSync/commit/a229c3948406bc2cf6eaf4873e662e70c6a04746) |
| VBench | 2026-08-21 | [fd18b3d](https://github.com/Vchitect/VBench/commit/fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490) |
| Qwen3-Omni | 2026-04-23 | [e423585](https://github.com/QwenLM/Qwen3-Omni/commit/e4235853125589c789f06a2dd83e9f4126df5e9d) |
| video-SALMONN 2 | 2026-09-02 | [2d28e84](https://github.com/bytedance/video-SALMONN-2/commit/2d28e841c8378885d2f30982be801d0c44f7a5bb) |
| TwelveLabs plugin | 2026-05-14 | [c9d4936](https://github.com/twelvelabs-io/twelve-labs-claude-code-plugin/commit/c9d4936dbee87ecfd4fb8c54f7369d9b83439f14) |
| VideoDB skills | 2026-11-05 | [f985577](https://github.com/video-db/skills/commit/f985577fba97705ed937cc707c3a67e35f23faf5) |
| DNS-Challenge | 2024-03-29 | [591184a](https://github.com/microsoft/DNS-Challenge/commit/591184a9fcb2cbdec02520fed81a32bbbf9d73ff) |
| EvalCrafter | 2024-10-03 | [1275bda](https://github.com/evalcrafter/EvalCrafter/commit/1275bda05e74f295ad2585e3ebde8e95a81a15af) |
| AVE-Compass | 2026-07-29 | [2b11dd0](https://github.com/NJU-LINK/AVE-Compass/commit/2b11dd047345a9e509649e9570e0f4efadd25307) |

## Smallest integration seam

This is a proposed design, not an implemented interface. Retain Codex directing the embedded Agent and ArcReel's existing MCP toolset. Existing owning paths are `server/agent_toolset/video_review.py`, `server/media_tools/video_review.py`, `lib/video_review/` and `scripts/inspect_audio_evidence.py`. Embedded instructions in `agent_runtime_profile/CLAUDE.drama.md` already require project edits and generation through `mcp__arcreel__*`; keep that boundary.

An evaluator adapter should consume a manifest-resolved version, approved-script/timeline context and a production reference, returning evidence without modifying formal content. Use temporary derivations for PCM, crops and downsampled measurement video; preserve source hashes, derivation settings and original timestamps. The evaluation record should contain:

- Exact source/version/hash, reference identity, evaluator code/model/checkpoint revision and input modalities.
- Per-segment observed words/intervals, subtitle observations, face-track coverage and raw synchrony outputs, each with method and uncertainty.
- Separate observable visual/semantic findings with source timestamps, supporting frames/audio intervals and a constrained correction proposal.
- Explicit `unsupported`, `insufficient_evidence`, `contradiction` and `error` outcomes. Missing models, invisible mouths or failed downloads never become passing zero scores.

Do not average incompatible metrics into one confidence number. Deterministic contradictions block unsupported claims. The embedded Agent can use evidence to select an existing good version, propose supported timeline corrections or request bounded regeneration through existing tools and spending policy. Evidence collection must not itself dispatch regeneration or rewrite the intended script. No second workflow engine, series bible, subtitle system or independent production ledger is needed.

## Qualification plan and next decision

No steps below were executed by this research task. Local qualification should follow repository dependency guidance and verified code/weight terms in an isolated environment. Paid services still require a concrete quote and explicit numerical approval.

1. **Offline preparation, no model/API request:** freeze the existing silence, wrong-speech, good speech, delayed-subtitle, symbolic-identity and H3 bytes with hashes; verify durations from actual media. Record which fixtures have ground truth for which criterion. Existing drawings have none for mouth synchrony. Create a test manifest and expected outcomes without exposing labels/expected words to recognition. Review exact selected code/weight terms and dependency compatibility before installing anything.
2. **Bounded local candidate exercise:** after dependency and license review in an isolated environment, run WhisperX against the frozen audio on CPU, retaining raw output, timings and runtime. Run current SyncNet on authorized visible-speaking-face material with known alignment, plus digitally shifted copies at positive and negative offsets. Use only existing authorized media; do not generate a paid actor sample. If no such material exists, report synchrony qualification blocked rather than using drawings or unlabelled H3 as ground truth.
3. **Controls that every semantic candidate must face:** digital silence; different spoken words; audio-only with no visuals; no-audio video; subtitle/text/audio disagreement; the known delayed subtitle; labelled prop/costume mismatch; known real-identity changes when suitable authorized material exists; native H3 with independently established transcript. Silence must not elicit music or speech. File duration must agree with decoding. Retain complete utterances, not only “Bom dia.”.
4. **Synchrony controls:** preserve the visual stream while shifting audio; test silence, voiceover/offscreen speaker, occluded mouth, multiple faces, cuts, a static face and unrelated matching-duration speech. Report score curves, sign convention, frame quantization, supported offset range, face coverage and abstentions. Detect an introduced shift without correcting it before measurement. Do not declare 0 ms from a categorical/class-based output.
5. **Generalization:** separate calibration examples from held-out PTBR clips; include names, accents, expressive delivery, music and 1080×1920 footage. Measure false acceptance of known defects, false rejection of known-good media, localization error and reproducibility. Choose tolerances before examining held-out results. A few successful demonstrations are not a reliability estimate. Human test annotation is required ground truth here, not a proposed production approval downgrade.
6. **Only if needed, separately approve a cloud trial:** first confirm an exact Pegasus version, account allowance, all upload/processing/storage/output charges, retention/deletion route, input constraints and a numeric call/spend cap with zero implicit retries. Capture actual submitted media identity and sanitized request/response/usage. Trial a fixed clip directly through Models API, not a multi-agent library workflow. No paid quote is finalized by this research.

The immediate decision supported by current evidence is to prepare local WhisperX/SyncNet qualification and a concrete Pegasus trial option while keeping #10 open. If these components fail their controls, reject that component for that criterion. No candidate should acquire authority merely because another provider failed or because its output is timestamped JSON.
