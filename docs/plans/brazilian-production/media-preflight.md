# International media preflight

Issue #9, checked 2026-11-08. Status: provider setup and preflight complete. The owner subsequently approved USD 1.95 and the single initial H3 sample and formal 1080 × 1920 render succeeded. Independent subjective playback/evaluation remains pending; all-attempt financial reconciliation is complete. The preflight itself made no paid call.

## Application settings and free connectivity

The owner's original application is at `http://localhost:5173`, with API `http://localhost:1241`. Its existing active MiniMax and Google AI Studio credentials were found using read-only presence queries. No provider secret was printed, copied to another deployment, or included in this document. The isolated API at port 1242 still has no media credentials and its ongoing project was not changed.

MiniMax's blank credential base previously inherited mainland `https://api.minimaxi.com/v1`. Through the existing authenticated settings API, `PATCH /api/v1/providers/minimax/credentials/{existing-id}` changed only `base_url` to `https://api.minimax.io/v1/`. Readback confirmed the same active credential ID and unchanged masked-key field. No credential was recreated. The existing declarative normalizer removes `/v1` before appending the H3 `/v2` paths.

The application's existing `POST /api/v1/providers/{provider}/test` checks use provider model listing rather than generation. Both succeeded. Google AI Studio returned the exact `gemini-3.1-flash-image` model, confirming that the stored key works for that discovery request on the intended Google provider. Actual image-generation access, quota and image quality are not established by this free check. MiniMax returned nine models, without exact H3 in its text-oriented listing. This establishes authenticated international connectivity, not H3 video entitlement or available balance. A successful H3 submission remains untested.

## Effective international pricing

The effective official catalog sync was `2026-11-05T14:50:25Z`. It priced exact `MiniMax-H3` in CNY: 0.80 per output second at 2K, 0.50 at 768P, and 0.20 per input image after five free images. No matching local entry override existed initially. That table did not describe the international account's USD tariff.

The [official international pricing table](https://platform.minimax.io/docs/pricing/overview) lists exact H3 output at USD 0.13 per second for 2K and USD 0.08 for 768P, with five free input images and USD 0.04 for subsequent images; audio input is free. No image, video or audio reference is requested for this sample.

Using existing `PATCH /api/v1/providers/minimax/models/MiniMax-H3`, an authorized reversible local entry-price override now uses those USD rates. The current output-seconds resolution dimensions, default tier, input-image meter, five-image allowance and all unrelated model facts were retained. Readback reports `source: modified`, exact H3 enabled/default and provider multiplier 1.0. This is a whole-entry local copy, so it stops following later official entry changes until the existing restore-official-data action is used. Restoring the current official copy would reintroduce the CNY table and needs review before international submissions. Historical usage was not rewritten.

The existing `quote_video_request_from_price` calculator produced CNY 4.00 for the five-second candidate before the override. After loading the actual saved user entry, it produced USD 0.65 with `unpriced_reason: null`. The same existing price-table calculator independently returned USD 0.65 from the verified international rates. This reconciles the application's future quote currency with the selected international account; no exchange-rate conversion or new billing layer was introduced.

## Bounded sample candidate

Pending intent reference: `sample-9-initial-E1U01-5s-2k-v1`. This is the separate capability sample for #9, not the #11 pilot or #12 continuity sample. The approved initial action is now reserved and submitted under that same intent; no second quality action is authorized.

The existing [H3 API contract](https://platform.minimax.io/docs/api-reference/video-generation-v2-create) supports the exact model at 4–15 seconds and 768P/2K, with a concrete ratio for text-only input. A five-second text-only vertical sample is useful for checking native Portuguese speech, delivery conversion and retrieval, without generating a storyboard or asset image. No Highspeed, Lite, Max, successor image model or native `1080p` tier is substituted.

The local existing request-preview renderer, with `placeholder_missing_assets=False`, produced:

```json
{
  "method": "POST",
  "url": "https://api.minimax.io/v2/video_generation",
  "body": {
    "model": "MiniMax-H3",
    "content": [{
      "type": "text",
      "text": "Vertical medium shot in a simple Brazilian kitchen. An adult woman smiles at camera and says in Brazilian Portuguese: \"Bom dia! O café está pronto.\" Keep the quoted speech unchanged. Native room ambience and clear spoken audio."
    }],
    "resolution": "2K",
    "duration": 5,
    "ratio": "9:16"
  }
}
```

This preview uses a synthetic credential placeholder and transmits no provider request. The public standalone preview API instead fills placeholders for every declared missing image/audio source and can show `adaptive`; that scaffolding is not the no-assets execution shape. The explicit no-assets preview above contains only text. H3's existing declaration has an always-on native audio track, rather than a separate voice-provider call. Portuguese intelligibility and exact spoken words still require actual inspection.

The existing reference-video projector supports imageless units when the effective model supports text-to-video; a unit without references takes its `i2v` configuration bucket while the H3 provider request itself is text-only. Use a separate formal sample project/unit through the embedded Agent after approval, explicitly selecting `minimax/MiniMax-H3`, resolution `2k` and 9:16. Preserve its formal script, jobs, provider checkpoint and selected version. Do not mutate the ongoing isolated adaptation project or copy provider secrets into that deployment. Production execution must use the application's existing service/harness with the configured media credentials and required subscription text settings.

The existing final-cut output profile resolves 9:16 to 1080 × 1920 at 30 fps. After generation, probe the actual source video's pixel dimensions, duration and audio before rendering; the API's `2K` tier alone does not establish exact returned dimensions. Use the existing renderer for any scaling and burned Portuguese subtitles. The current checks establish the configured delivery path, not a completed render or playback result.

## Quote and reservation proposed to the owner

| Item | Amount | Scope |
|---|---:|---|
| Exact H3, 5 seconds, 2K, text-only | USD 0.65 | One successful provider generation |
| Generated images, reference inputs and separate voice generation | USD 0.00 | These operations are absent from this candidate |
| Local existing render/conversion | No provider generation fee | Existing local renderer; no paid rendering service requested |
| Proposed per-video ceiling | USD 1.95 | One initial quality-generation action, including conservative transport contingency |
| Proposed round ceiling | USD 1.95 | This one capability-sample video only |

The backend's existing submit retry wrapper permits at most three attempts. Connection-establishment/acquisition/proxy failures are definitely unsent and do not represent billed generations. Read/write/protocol ambiguity becomes `AmbiguousSubmitError` and stops automatic resubmission. Retryable explicit HTTP failures can be retried; their billing cannot be assumed zero without authoritative evidence. USD 1.95 therefore reserves three times USD 0.65 as a conservative maximum for this initial action's possible submitted attempts, not a claim that every retry is billed.

Polling and downloading the original job do not create a generation or increment the quality counter. After interruption, reconcile the original task, batch, provider checkpoint and usage before any replacement. Unknown delivery retains the reservation and pauses. On settlement, replace the reservation with actual referenced usage rather than adding another local charge.

No quality regeneration is included in the pending approval request. A rejected segment remains limited to at most two additional quality generations, each requiring a current quote and sufficient separately approved allowance. The initial-plus-two-quality ceiling combined with three potentially billed submit attempts per action would be USD 5.85, but that is not requested or authorized here. No pilot, continuity sample, collection generation, image call, separate voice integration or new metered evaluator is covered.

The owner explicitly approved “Sim, aprovo teto de US$ 1,95 para esta amostra e rodada” in response to question `c31f4d137dd9464a9dc0cb96e71fbdde`. The private recovery record stores this exact response and reference. The policy helper durably reserved the full USD 1.95 before any embedded-Agent dispatch.

## Private receipts and remaining evidence

Sanitized private receipts are under `/tmp/arcreel-goal-state/media-preflight/`:

- `config-presence.json` and `effective-config.json`: credential presence and pre-change nonsecret configuration/catalog facts.
- `configuration-result.json`: existing-credential base-only update and free connectivity summaries.
- `price-override-result.json`: before/after price tables, preserved model facts, source and multiplier.
- `request-preflight.json`: standalone API preview scaffolding and read-only capability/model responses; distinguish it from the actual no-assets candidate.
- `candidate-quote.json`: no-assets request shape, existing calculator results, delivery profile and explicitly unapproved ceilings.

No file contains provider key values or authentication tokens. Local helper scripts authenticate in memory through the application's normal login endpoint; they retain no access token file. The preflight did not restart either server or modify source code.

Remaining #9 criteria: successful terminal retrieval and reconciliation, actual recorded cost, native audio review, source-dimension probing, existing final-cut render at 1080 × 1920 and actual playback evidence. Google generation is conditional on a genuine image need; it is unnecessary for this initial text-only capability sample.


## Approved execution checkpoint

The separate formal project is `br-capability-sample-9-20261108`. The embedded Agent authored exactly one five-second unit, `E1U1`, in `scripts/episode_1.json` through the existing subscription text backend. Independent comparison verified that its full prompt matches the approved candidate character for character. The canonical directing segment ID `E1U01` maps to this actual unit; its existing intent and attempt count were retained.

The current formal `generate_videos` preview returned `submittable: true`, USD 0.65, zero unpriced items, no problems and `confirmed_request_durations: {}`. The same embedded session then invoked `generate_videos` once for that exact unit. Original task `765eece61cf24e1394829581a6f90e14`, batch `d9db0e69b2fb4f06ba7dff1d18fdd64e`, provider job `461209688465698` succeeded. A persisted execution checkpoint confirms international MiniMax, exact H3, 2K and five seconds. Ledger call 14 is now successful and records USD 0.65, retry count zero and no unpriced reason. The provider final response reports five output seconds, zero input seconds and zero input images. Independent review reconciled the complete create-response log, the unique original job and usage row, retry count zero and the transport ambiguity rules. Exactly one H3 create request completed with HTTP 200; any unlogged connection-establishment retry would be definitely unsent and unbilled. The policy record now settles USD 0.65 and releases USD 1.30 of contingency based on that combined evidence, not the final charge row alone.

The approved plain quotation syntax yields no canonical subtitle utterances in the current reference-video parser. Do not change the prompt, regenerate or invent timestamps to conceal that limitation. The coordinator clarified that burned Portuguese subtitles are mandatory for the #11 pilot; #9 can verify native audio and the existing 1080 × 1920 delivery path using the supported no-subtitles final-cut variant. The original artifact/job stays unchanged, and this precise subtitle gap is carried into #10/#11 preparation.


The original selected artifact is `reference_videos/E1U1.mp4`, version 1, current. Existing timeline `tl-0dd0f11d`, revision 1, has one source-volume-1 clip. Existing render task `49ba5e8857da42d88ebb695ef862dcd6` and batch `5119e2806a2e460c952fad6807133d87` succeeded; its artifact is `renders/episode_1/tl-0dd0f11d/final_cut.without_narration.no_subtitles.mp4`, version 1. No alternative rendering pipeline was used.

Independent bundled-ffmpeg probing confirms source H.264 1440 × 2560 at 24 fps with AAC 32 kHz stereo, approximately 5.167 seconds. The existing renderer downscaled it to H.264 1080 × 1920 at 30 fps with AAC 48 kHz stereo, approximately 5.167 seconds. Its duration acceptance check passed without warnings. Existing whole-video technical signals found no black span, freeze or cut. Contact sheets show a woman, kitchen, coffee pot and cup; they do not prove correct voice or lip-sync.

Actual local, unprimed Portuguese Whisper inference returned “Bom dia, o café está pronto.” at approximately 0–2.480 seconds, matching the intended words after punctuation normalization. Decoded PCM RMS was approximately 0.150, so this track is not digitally silent. This supplies real speech/transcription evidence but does not replace listening or a full audiovisual review. Native audio was tested first; no separate voice integration was invoked.

Additional private receipts: `formal-script-verification.json`, `formal-quote-entry.json`, `sample-jobs.json`, `actual-media-and-usage.json`, `actual-dimensions-bundled.json`, `native-final-provider-usage.json`, `submit-log-evidence.json`, `actual-source-sheet-0.jpg`, and `native-audio-review/review.json`. The directing record is `pending-sample-intent.json`; its completed media intent is settled at USD 0.65 with the independent financial audit linked. A persisted `sample_scope_complete_no_further_generation_authorized` pause prevents unused allowance from authorizing another action. No subsequent quality regeneration or new generation has been authorized.

Independent reviewer `implement_ptbr` also decoded the complete source and final video without errors. This confirms actual playable media structure/decoding, while subjective voice, naturalness and lip-sync assessment remains with the separately authorized audiovisual evaluation. The exact financial review summary is retained privately as `independent-financial-audit.json`.
