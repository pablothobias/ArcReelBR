# International media preflight

Issue #9, checked 2026-11-08. Status: provider setup and nonbillable preflight complete; actual sample generation, rendering, playback and actual-cost verification remain pending. No paid generation or evaluation call was made during this preflight.

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

Pending intent reference: `sample-9-initial-E1U01-5s-2k-v1`. This is the separate capability sample for #9, not the #11 pilot or #12 continuity sample. It has not been submitted or reserved as approved work.

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

The coordinator presented the USD 1.95 per-video and round proposal to the owner; explicit numeric approval was still pending at this checkpoint. The recovery record must retain empty approval evidence and authorize no submission until the actual owner response arrives.

## Private receipts and remaining evidence

Sanitized private receipts are under `/tmp/arcreel-goal-state/media-preflight/`:

- `config-presence.json` and `effective-config.json`: credential presence and pre-change nonsecret configuration/catalog facts.
- `configuration-result.json`: existing-credential base-only update and free connectivity summaries.
- `price-override-result.json`: before/after price tables, preserved model facts, source and multiplier.
- `request-preflight.json`: standalone API preview scaffolding and read-only capability/model responses; distinguish it from the actual no-assets candidate.
- `candidate-quote.json`: no-assets request shape, existing calculator results, delivery profile and explicitly unapproved ceilings.

No file contains provider key values or authentication tokens. Local helper scripts authenticate in memory through the application's normal login endpoint; they retain no access token file. The preflight did not restart either server or modify source code.

Remaining #9 criteria: explicit numeric owner approval, current formal workflow preview for the eventual sample project, actual exact-H3 entitlement/balance validation through the approved bounded submission, original-job polling and reconciliation, actual recorded cost, native audio review, source-dimension probing, existing final-cut render at 1080 × 1920 and actual playback evidence. Google generation is conditional on a genuine image need; it is unnecessary for this initial text-only capability sample.
