# Nano Banana 2 fallback quote preflight

Status: [issue #14](https://github.com/pablothobias/ArcReelBR/issues/14) is integrated and closed. The selected image entry now has a reversible local user override with complete token rates and verified technical limits. The existing estimator produces a complete conservative bound. **The first fixture image was rejected and preserved. One separately approved photographic quality retry is now complete and settled; its result awaits owner review and has not been promoted. Neither closed allowance authorizes further generation.** The earlier unbounded quote and retry finding below are historical, superseded findings.

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

The separately approved fallback specimen was one **1K, 16:9 three-view character sheet**, text-only, with no reference images, grounding or alternative model. This supersedes the initial unapproved square-image preference: the existing formal asset-sheet path fixes its canvas to 16:9, so the fixture preserves that supported path. Use existing image-generation tasks and artifact registration/version selection. Verify actual dimensions satisfy H3's 256-pixel minimum after any separately approved generation. A construction-only check preceded the separately approved sole provider call described below. No new generation is authorized after the owner rejected its result.

This could exercise the project-provider fallback if separately approved. It cannot be described as an image produced by Codex's `image_gen` tool, and does not establish that specific #6 round trip. Available Codex image-tool metadata still supplies no tariff, currency, allowance or usage receipt; its unknown cost is not zero.

Earlier formal pilot preparation referenced five reusable assets plus three storyboard images. That historical eight-image target set is distinct from one fallback fixture; re-read the current formal set, model/lane selection and quotes before proposing any pilot allowance. No fixture approval would cover quality retries, H3 video, evaluation, pilot or continuity generation. Earlier H3 and evaluation allowances do not authorize images.

## Historical pre-fix finding

Before #14, the saved exact-model entry contained image-output prices only, and the backend omitted billed input/thinking quantities. Its USD 0.067 1K estimate was therefore not complete. A controlled fake SDK timeout caused five calls through the real retry wrapper, demonstrating ambiguous-resubmission risk without network or generation. There was no supported complete finite quote for that configuration.

[Historical qualification evidence](evidence/06-image-fallback-billing-gap.json) preserves that finding. USD 0.335 or USD 0.336 represented only multiplied output-image components and was never a full quote or approved reserve. The current complete local override, model technical bounds and integrated #14 behavior supersede that original blocker; they do not establish media quality or generation success.


## Concrete non-generating formal fixture

A separate production-app fixture, `image-handoff-fixture-6-20261108`, now contains exactly reusable character `Ana` and one formal episode-1 storyboard target `E1S01`. The existing embedded Agent created the character through `patch_project` and authored the script through the configured official-subscription `claude-opus-5-5` backend. Its implementation fixes internal effort to `medium`; selected-model usage is recorded in text ledger entry 16. Subscription telemetry has no invented paid-token charge. The main conversation harness remains unchanged under ADR 0124.

The storyboard has one five-second neutral shot, no dialogue/voiceover, references only Ana, and registers no scene, prop or product assets. At this preparation checkpoint, no image/video/audio task existed; the sole authoring task had completed. The later approved image outcome is recorded below. Its script SHA-256 is `2f7dc3d635105fd2f86131e0af3844f49dc2840ef874861c5bd30a179aea0e7b`.

The actual authenticated character-batch preview now has **one target `character/Ana`**, no skipped targets, USD 2.031616, `unpriced_count: 0`, and `full_context_output_upper_bound`. This replaces the earlier empty-project preview as evidence of a real target. Actual configuration resolution confirms exact `gemini-aistudio/gemini-3.1-flash-image`, `1K`, `16:9`, zero references. Construction through the existing backend, with only its SDK boundary replaced, confirms one candidate, `IMAGE` response mode and the shared 32,768 output-token cap. This construction check sent no provider request.

The existing prompt builder appends a white-background, three-view layout. Before approval, the embedded Agent corrected only Ana's description from light gray to white, aligning the final character prompt without changing the script or harness. Final rendered prompt SHA-256: `385dd99642c91e4ce889435b71c06db36305635b5bac8ff16a7ab85ca258f720`.

```text
Asset sheet for character “Ana”.

A fictional adult Brazilian woman named Ana, approximately thirty years old, with medium-brown skin, short curly dark hair, a plain teal T-shirt and dark trousers. Neutral relaxed standing pose, natural proportions, simple studio lighting, and a clean white background. No logos, text, extra people or reference images.

Landscape 16:9 three-view sheet on a pure white background: front / exact side (90° side view) / rear arranged horizontally.

The character must have exactly the same facial and head features, fur or hairstyle, clothing or body markings, body shape, and accessories in all three panels.

Avoid: watermarks, extra text, logos
```

The exact target/prompt/quote snapshot is `/tmp/arcreel-goal-state/image-fallback-fixture/frozen-target-quote.json`, with the nonempty HTTP preview, construction-only request, session transcript and `recovery.json` beside it. Stable client keys are `image6-formal-preparation-v1` and `image6-background-alignment-v1`; the existing session is completed. The original preparation record retained null approval and no reservation. The subsequent owner approval used a fresh `image-fixture-6` record and narrow policy scope, now closed with the rejected result and settled cost.

A new numeric approval would cover only that single initial character-sheet image at the quoted maximum, not another generated image, quality regeneration, video, pilot or evaluation. Actual source pixel dimensions must be probed after any authorized generation rather than inferred from `1K`. Later reuse of the same image through authenticated character/storyboard uploads and downstream identity/request inspection remains separate validation; the current storyboard image preview correctly reports missing Ana reference media. This preparation does not close #6 or imply that a fallback artifact came from Codex's image-generation tool.


## Actual approved image, owner rejection and closed spending

The owner approved “Sim, aprovo US$ 2,04 para esta amostra” in question `call_8270214e39304501a7f6d1f5d53d60a2`. After fresh target/prompt/configuration checks and independent policy clearance, Codex reserved the actual USD 2.031616 maximum before sending one stable-key instruction to the existing embedded Agent. It called `generate_assets` exactly once for `character/Ana`. Task `0ddb715b6b1b4e20bbbb03b5276a660f` and batch `c2999e34f58644318dde87de5be08023` completed successfully, registering historical version 1.

The returned file is **1376 × 768, 357,068 bytes, actual JPEG data despite its existing `characters/Ana.png` filename**. Its SHA-256 is `798741b81a9b82fff30a40ac312be5cb659739ec217de1092955f06d74a1af25`; current-path and original version-copy bytes match. The filename and bytes were preserved. Do not describe it as PNG merely from the suffix.

The owner explicitly rejected its 3D/artificial, non-realistic appearance. This is a rejected, discarded result, not an accepted creative reference or completed #6 handoff. No character/storyboard upload, version selection, downstream promotion, additional generation or quality repair occurred. The earlier observation of three views/white background was only a technical description; it did not establish realism, identity quality or owner acceptance. The center view also did not meet a strict 90-degree profile.

Independent all-attempt billing review verified one selected-model official POST returning HTTP 200, one task and ledger entry 20, and no execution-window retry. Returned usage was 147 input tokens, 1,120 image-output tokens and 237 non-image output tokens including thinking, totaling 1,504 tokens. Cost is `(147 × 0.50 + 1120 × 60 + 237 × 3) / 1,000,000 = USD 0.0679845`. The ledger's floating representation is `0.06798449999999999`. No full actual serialized wire capture was made; evidence comprises supported settings, construction, application logs, provider metadata, ledger and formal artifact records.

The directing record settled **USD 0.0679845 once** and released **USD 1.9636315** of the original reservation. Its intent remains `review: rejected`, `discarded: true`, paused with `owner_rejected_image_no_further_action_authorized`. Unused owner allowance is not authority for another call. [Sanitized actual-outcome evidence](evidence/06-image-fixture-outcome.json) preserves these facts. No work remains in flight.

## Photographic proposal preparation

Inspection found that this fixture's project style was empty and the approved rendered prompt did not explicitly request photographic realism. This does not establish the model's internal failure cause. Other existing projects were not changed, and no global default or harness fix was introduced.

At the coordinator's explicit instruction, only this fixture's supported project `style` field was changed through the authenticated owning REST PATCH, after immediate preimage checks. The Agent `patch_project` allowlist cannot change style; the REST request supports `style` but not arbitrary `style_description`, so the latter was not sent. The new style asks for live-action human casting photography with a real camera, skin pores, fine hair, natural asymmetry, realistic anatomy/cloth texture and soft studio lighting, and excludes 3D/CGI/dolls/plastic skin/illustration. Ana's identity, description, clothes, formal script, historical version metadata and image bytes were preserved.

Actual compiled prompt preview now contains that style and the existing white-background three-view layout. Its new SHA-256 is `6a4b69786bc1306f18ee1d5b24043e663cd4e839d9df1f63238ff60cac835425`. Before/after snapshots, exact new prompt and reversible style payload are kept separately in `/tmp/arcreel-goal-state/image-fallback-fixture/realism-proposal/`. The old frozen approved request and allowance were not repurposed.

At this preparation checkpoint, version 1 remained selected but its artifact currency became **stale** because its style basis changed. It is also independently rejected by the owner. At that checkpoint the new prompt was an ungenerated proposal without a new allowance. The later separate approval and sole quality retry are recorded below; the original allowance was not reused. Prompt changes alone do not prove a realistic result or satisfy #6.


## Separately approved photographic quality attempt 2

The owner then approved “Sim, aprovo US$ 2,04 para essa única nova tentativa” in question `call_60f4c93791e340348124a57eac6d7938`. A fresh `image-quality-6` record retained the rejected, settled initial attempt as immutable history and computed **quality attempt 2**. Following independent policy review, integration and an idle-verified restart activating #16's MIME correction, immediate checks confirmed the same Ana identity, current photographic prompt, exact model, 1K/16:9 shape, zero references, unchanged script and no pending job. The explicit named service preview quoted one regeneration at USD 2.031616; the missing-only HTTP preview remained empty because the stale old sheet was still present.

Codex reserved the full quote before one stable-key embedded-Agent instruction. The Agent made one named `generate_assets` call. Task `b11de379e3bf45d6997934927d207bb0`, batch `69166bb3947a41c99f7eb9898e0715b9` and ledger entry 22 completed successfully. Normal formal activation registered version 2; no manual version selection or upload occurred.

Version 2 is **genuine PNG**, 1376 × 768, 1,062,470 bytes, SHA-256 `1c3ed5bfce25a3ee8499a7fe4e2182086be897281070c704493ca868d18bf90a`, with current artifact currency and exact photographic prompt hash `6a4b69786bc1306f18ee1d5b24043e663cd4e839d9df1f63238ff60cac835425`. The rejected historical JPEG version 1 and original closed spending record hashes remain unchanged.

Independent all-attempt review verified exactly one new selected-model HTTP 200 response and measured usage: 259 input tokens, 1,120 image-output tokens and 320 non-image output tokens including thinking. Settled cost is **USD 0.0682895**, recorded once; **USD 1.9633265** of the reservation was released. The two image rounds together cost USD 0.136274, including rejected work. No full actual serialized wire capture is claimed. The new round is closed, has no pending job and grants no replacement or additional call. [Sanitized attempt-2 evidence](evidence/06-image-quality-attempt2.json) retains provenance, billing and history checks.

Root and independent reviewer observe more photographic skin, hair and cloth texture and a true side profile. **The framing ends around the thighs, with no knees or feet; this is not a complete full-body sheet. Owner acceptance remains pending.** There is no automatic quality pass. No storyboard upload, downstream promotion, video, evaluation, pilot or further image was produced. The result remains held for owner review; #6's accepted creative handoff is not established by generation alone.
