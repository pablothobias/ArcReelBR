# Nano Banana 2 fallback quote preflight

Status: [issue #14](https://github.com/pablothobias/ArcReelBR/issues/14) is integrated and closed. The selected image entry now has a reversible local user override with complete token rates and verified technical limits. The existing estimator produces a complete conservative bound. **No image generation has occurred, and no image allowance is approved.** The earlier unbounded quote and retry finding below are historical, superseded findings.

## Current selected model and configuration

Keep the existing `gemini-aistudio/gemini-3.1-flash-image` (Nano Banana 2), with no successor-model substitution. After the coordinator restarted the existing application with #14, the supported settings endpoint `PATCH /api/v1/providers/gemini-aistudio/models/gemini-3.1-flash-image` saved only two technical facts and the complete price table as a **local user copy**. This is not a newly synchronized official catalog snapshot.

[Official model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image) verifies 131,072 input tokens and 32,768 output tokens. [Official standard pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-image) charges USD 0.50 per million text/image input tokens, USD 3 per million text/thinking output tokens and USD 60 per million image output tokens. The three corresponding application meters are `uncached_input_tokens`, `output_tokens` and `image_output_tokens`.

Readback confirmed the new bounds/rates and preserved name, display name, model selection, other facts (including 14 reference images and existing resolution tiers), endpoint, enabled/default state and multipliers. The source is correctly `modified`; the official synchronized catalog hash is unchanged. Provider multiplier is 1.0 and model multiplier is 1.0. [Sanitized configuration evidence](evidence/06-image-price-configuration.json) records these checks, source URLs and the preview result. Private preimage, exact PATCH, complete entry backup and supported restore plan are under `/tmp/arcreel-goal-state/media-preflight/image-override-preparation/`.

There was no earlier user copy. The saved restore operation is `POST /api/v1/catalog/entries/restore-official` with the same maker/name/media-type identity, removing this copy and resuming official following. Check for intervening changes before restoration; the full preimage is retained. Restoring the old image-only price table would also restore incomplete quoting, so dependent submission must be reassessed.

## Complete conservative quote and its limit

The existing asynchronous `estimate_image_batch_cost` service, with normal synchronized-catalog and user-entry startup loading, returned:

- `estimated_cost: {"USD": 2.031616}`
- `unpriced_count: 0`
- `estimate_basis: "full_context_output_upper_bound"`

This read-only check used a single explicit in-memory text-to-image lane, not a persisted project or task. Its effective entry was checked against the saved user copy. The existing HTTP asset-batch preview also ran on the actual sample project, but that project has no assets, so its empty-target result is not evidence of a one-image quote. An initial standalone service invocation omitted normal catalog hydration and returned unpriced; that result was corrected by loading the same existing startup catalog services, without another settings mutation.

The bound is `(131072 × 0.50 + 32768 × 60) / 1,000,000 = USD 2.031616` at the actual combined multiplier 1.0. The estimator allocates the shared output maximum to the highest-cost output split rather than counting overlapping full image and text caps. This covers the full supported context and output ceilings. **It is a conservative per-request maximum, not expected one-image cost or a newly approved spending allowance.** No prompt-specific token estimate or free inference is assumed.

A documented 1K image consumes 1,120 image tokens, equal to USD 0.0672 at the image rate, rounded to USD 0.067 in Google's table. That remains an image-output component, with input and thinking additional. It must not replace the complete bound in an approval request. The backend's technical token limits are model constraints, not a new backend money cap.

#14 also changed image retry handling: only verified unsent failures may use the existing outer retries. Ambiguous acceptance pauses rather than silently resubmitting, and received usage remains accountable even if parsing or artifact saving fails. Do not multiply an image-output component by five and call that a full allowance. Any unresolved outcome retains its original reservation and blocks a new action.

## Candidate scope and remaining approval

The current fallback candidate is one newly generated **1K, 16:9 three-view character sheet**, text-only, with no reference images, grounding or alternative model. This supersedes the initial unapproved square-image preference: the existing formal asset-sheet path fixes its canvas to 16:9, so the fixture preserves that supported path. Use existing image-generation tasks and artifact registration/version selection. Verify actual dimensions satisfy H3's 256-pixel minimum after any separately approved generation. No provider request has been sent for this candidate; a construction-only check replaced the SDK boundary without a provider client or network.

This could exercise the project-provider fallback if separately approved. It cannot be described as an image produced by Codex's `image_gen` tool, and does not establish that specific #6 round trip. Available Codex image-tool metadata still supplies no tariff, currency, allowance or usage receipt; its unknown cost is not zero.

Earlier formal pilot preparation referenced five reusable assets plus three storyboard images. That historical eight-image target set is distinct from one fallback fixture; re-read the current formal set, model/lane selection and quotes before proposing any pilot allowance. No fixture approval would cover quality retries, H3 video, evaluation, pilot or continuity generation. Earlier H3 and evaluation allowances do not authorize images.

## Historical pre-fix finding

Before #14, the saved exact-model entry contained image-output prices only, and the backend omitted billed input/thinking quantities. Its USD 0.067 1K estimate was therefore not complete. A controlled fake SDK timeout caused five calls through the real retry wrapper, demonstrating ambiguous-resubmission risk without network or generation. There was no supported complete finite quote for that configuration.

[Historical qualification evidence](evidence/06-image-fallback-billing-gap.json) preserves that finding. USD 0.335 or USD 0.336 represented only multiplied output-image components and was never a full quote or approved reserve. The current complete local override, model technical bounds and integrated #14 behavior supersede that original blocker; they do not establish media quality or generation success.


## Concrete non-generating formal fixture

A separate production-app fixture, `image-handoff-fixture-6-20261108`, now contains exactly reusable character `Ana` and one formal episode-1 storyboard target `E1S01`. The existing embedded Agent created the character through `patch_project` and authored the script through the configured official-subscription `claude-opus-5-5` backend. Its implementation fixes internal effort to `medium`; selected-model usage is recorded in text ledger entry 16. Subscription telemetry has no invented paid-token charge. The main conversation harness remains unchanged under ADR 0124.

The storyboard has one five-second neutral shot, no dialogue/voiceover, references only Ana, and registers no scene, prop or product assets. No image/video/audio task exists. The sole authoring task completed. Its script SHA-256 is `2f7dc3d635105fd2f86131e0af3844f49dc2840ef874861c5bd30a179aea0e7b`.

The actual authenticated character-batch preview now has **one target `character/Ana`**, no skipped targets, USD 2.031616, `unpriced_count: 0`, and `full_context_output_upper_bound`. This replaces the earlier empty-project preview as evidence of a real target. Actual configuration resolution confirms exact `gemini-aistudio/gemini-3.1-flash-image`, `1K`, `16:9`, zero references. Construction through the existing backend, with only its SDK boundary replaced, confirms one candidate, `IMAGE` response mode and the shared 32,768 output-token cap. This construction check sent no provider request.

The existing prompt builder appends a white-background, three-view layout. Before approval, the embedded Agent corrected only Ana's description from light gray to white, aligning the final character prompt without changing the script or harness. Final rendered prompt SHA-256: `385dd99642c91e4ce889435b71c06db36305635b5bac8ff16a7ab85ca258f720`.

```text
Asset sheet for character “Ana”.

A fictional adult Brazilian woman named Ana, approximately thirty years old, with medium-brown skin, short curly dark hair, a plain teal T-shirt and dark trousers. Neutral relaxed standing pose, natural proportions, simple studio lighting, and a clean white background. No logos, text, extra people or reference images.

Landscape 16:9 three-view sheet on a pure white background: front / exact side (90° side view) / rear arranged horizontally.

The character must have exactly the same facial and head features, fur or hairstyle, clothing or body markings, body shape, and accessories in all three panels.

Avoid: watermarks, extra text, logos
```

The exact target/prompt/quote snapshot is `/tmp/arcreel-goal-state/image-fallback-fixture/frozen-target-quote.json`, with the nonempty HTTP preview, construction-only request, session transcript and `recovery.json` beside it. Stable client keys are `image6-formal-preparation-v1` and `image6-background-alignment-v1`; the existing session is completed. Recovery retains null image approval, no paid intentions and no reservation. No new directing-policy branch was added.

A new numeric approval would cover only that single initial character-sheet image at the quoted maximum, not another generated image, quality regeneration, video, pilot or evaluation. Actual source pixel dimensions must be probed after any authorized generation rather than inferred from `1K`. Later reuse of the same image through authenticated character/storyboard uploads and downstream identity/request inspection remains separate validation; the current storyboard image preview correctly reports missing Ana reference media. This preparation does not close #6 or imply that a fallback artifact came from Codex's image-generation tool.
