# Optional Pegasus semantic trial preflight

Checked: 2026-11-08, using official TwelveLabs documentation and pricing only. No account inspection, signup, credential lookup, media preparation/upload, inference or MCP installation occurred. This is an unselected future option if pilot review exposes a need. It is not a new requirement for #10 capability acceptance or permission to spend. Actual pilot quality remains a separate #11 concern.

## Exact documented route

`POST https://api.twelvelabs.io/v1.3/analyze`, with explicit `model_name: "pegasus1.6"`, `x-api-key` authentication, `stream: false`, `temperature: 0`, `max_tokens: 2048` and JSON-schema output. The endpoint's default is still Pegasus 1.5, so omitting the model would change the proposed comparison. Its accepted top-level media are **video or images, not standalone audio**. This is documented API availability, not verified account access. [Sync analysis reference](https://docs.twelvelabs.io/api-reference/analyze-videos/analyze).

The synchronous route accepts video from 1 second to 1 hour, resolution 360×360 through 5184×2160, and aspect ratios including 9:16. Output limits are 512–98,304 tokens. It supports structured JSON; custom video segmentation instead uses `POST /v1.3/analyze/tasks`. A JSON array containing requested intervals from general analysis remains model interpretation, not calibrated temporal measurement. [Sync reference](https://docs.twelvelabs.io/api-reference/analyze-videos/analyze), [async reference](https://docs.twelvelabs.io/api-reference/analyze-videos/create-async-analysis-task).

Pegasus 1.6 has a combined 261,120-token context and lists Portuguese as **partial support**. Its documented context includes video and audio transcription; this does not establish preservation of speech acoustics for judging voice performance or phoneme-level synchrony. [Model specification](https://docs.twelvelabs.io/docs/concepts/models/pegasus/pegasus-1-6).

Inline base64 avoids separately creating a reusable Asset/index, but still transfers the media to TwelveLabs. Its documented pre-encoding size limit is 36 MB, or 48 MB encoded. Inline content is described as non-reusable, without a deletion-time guarantee. [Upload and processing methods](https://docs.twelvelabs.io/docs/concepts/upload-methods).

## Smallest useful prospective comparison

Four calls, one per case, zero transport retries or automatic continuation, maximum 2,048 output tokens each. No reference images, indexing, embeddings, Jockey calls or external tools. Reuse the existing frozen controls identified in [local WhisperX evidence](evidence/10-audiovisual/whisperx-local-qualification.md):

| Case | Existing source | Required prospective input |
| --- | --- | --- |
| Good speech | `good.wav`, 4.345 s | Neutral video carrier, no visible words or people |
| Wrong speech | Exact prior comparison WAV, 4.5655625 s | Identical neutral carrier specification |
| Digital silence | Exact zero-PCM WAV, 4.5 s | Identical neutral carrier specification |
| H3 | Existing native-audio MP4, 5.167 s container duration | Original audiovisual bytes |

The first three need video carriers because Analyze does not document a standalone-audio request. This changes modality and cannot reproduce the previous audio-only abstention test. Carriers must preserve the complete source PCM and record any explicit padding/encoding changes, contain no transcript cues, and be decoded/hash-checked before use. They have not been created here. Require each final video to be at most **6 seconds**, within supported resolution/aspect limits and the inline byte limit. The 224×224 SyncNet crops are below this API's documented minimum and are unsuitable as-is. The original H3 file is 1440×2560; whether the published maximum is orientation-sensitive must be confirmed before claiming that the original bytes qualify. If resizing is required, it becomes a separately identified, decoded and hashed evaluation input rather than the original-byte case.

Ask for observed spoken words, approximate intervals, directly visible actions and evidence limitations before comparing to hidden expected words. Reject invented speech/music on silence, invented people on neutral carriers, omitted utterance endings, impossible file-duration claims and unsupported exact sync assertions. H3 can probe visual-performance descriptions, but this four-case set supplies no acting or lip-sync ground truth. Request `insufficient_evidence` where appropriate and preserve incomplete responses without another call.

The API can produce scene descriptions and structured findings suitable for a **semantic capability probe**. Public documentation does not establish reliable subjective acting assessment or raw-acoustic/phoneme alignment. Therefore it is not an evidence-backed replacement for the local speech and synchronization components. [Analysis guide](https://docs.twelvelabs.io/docs/guides/analyze-videos-and-images/videos), [modality distinctions](https://docs.twelvelabs.io/docs/concepts/modalities).

## Conditional numeric workload bound, not an all-in quote

Current published new-billing Pro overage rates are **USD 1.75/hour** of Pegasus video input and **USD 7.50/million output tokens**. Storage is separately listed at USD 0.065/GB/month. [List pricing](https://www.twelvelabs.io/list-price).

The new billing rounds video duration upward to whole seconds per event and Pegasus tokens upward to 1,000 on the billing-period total. Plans are migrating in phases; legacy accounts retain their earlier billing until migration. No account's regime or allowance was inspected. [Billing units and migration boundary](https://docs.twelvelabs.io/docs/get-started/plans-and-billing/plans-allowances-and-overage).

| Conditional component | Conservative bound | USD |
| --- | ---: | ---: |
| Four video inputs, each ≤6 s | 24 s × 1.75 / 3,600 | 0.011666667 |
| Four outputs, each ≤2,048 tokens | At most 9,000 marginal rounded tokens × 7.50 / 1,000,000 | 0.067500000 |
| **Published workload component** | Four requests, zero retries | **0.079166667** |

USD **0.08** covers that conditional workload component at those rates, not the complete cost of starting/using an account. The public monthly plans are Free USD 0, Plus USD 29 and Pro USD 99; public overage applies only to Pro. Allowance availability, legacy pricing, storage treatment for inline requests, retention-related storage charges, taxes and any subscription change remain unresolved. Do not present free-plan access as zero-cost certainty or assume the user already has Pro. [Current plans](https://www.twelvelabs.io/pricing).

**No supportable all-in trial ceiling is available from public documents alone.** Final media metadata and the intended account's billing regime/allowance must be verified before a concrete spending decision. No signup, plan change, overage setting change or inference is selected by this preflight.

## Data-transfer and privacy boundary

The current [privacy policy](https://www.twelvelabs.io/legal/privacy-policy), updated January 12, 2026, describes U.S. hosting and possible transfers to other countries, retention according to service/legal/business needs rather than a fixed short deletion period, and service-improvement use of customer data/output. It also distinguishes customer-contract processor arrangements. It does not establish the intended account's exact processing region, training exclusion, inline-media TTL, deletion of backups or zero-data retention. Those remain unknown. The [security page](https://www.twelvelabs.io/security) describes encryption and AWS infrastructure, which does not resolve those contractual questions.

The next useful action, only if a pilot-specific need arises, is to resolve account access, complete billing and retention terms and freeze the actual four media/request bodies. Any paid trial and external transfer require their own explicit scope and allowance. No existing image, H3 or evaluator approval funds this option.
