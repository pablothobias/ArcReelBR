# Nano Banana 2 fallback quote preflight

Status: no complete bounded quote yet. No real image-generation request, tool invocation, settings change or price override occurred. The pricing/retry defect is tracked separately as [issue #14](https://github.com/pablothobias/ArcReelBR/issues/14).

## Proposed scope and existing path

The narrow fallback candidate is exactly one newly generated 1K image from existing `gemini-aistudio/gemini-3.1-flash-image`, text-only, 1:1, no reference images, search grounding or alternative model. A 1K square image is the intended size; verify its actual dimensions exceed H3's 256-pixel minimum after generation. Do not substitute the catalog's successor model.

The existing path is `generate_assets` or the applicable existing image-generation task, through `GeminiImageBackend`, followed by existing artifact registration/version selection. The provider model metadata declares `/v1beta/models/{model}:generateContent`. A construction-only preview from the same installed SDK types used by this backend produced `responseModalities: ["IMAGE"]`, `imageConfig: {aspectRatio: "1:1", imageSize: "1K"}`, with one text prompt and no image inputs. No SDK provider client sent a request.

This can validate the agreed provider fallback if separately approved and made safely quoteable. It cannot be described as an image produced by the Codex `image_gen` tool, and does not complete that specific #6 round trip. Codex image-generation tool metadata still supplies no tariff, currency, account allowance or usage report; its unknown cost is not zero.

## Saved catalog versus official billing

The actual saved/synced exact-model entry has a USD image-output-only table: 512PX 0.045, 1K 0.067, 2K 0.101, 4K 0.151. No local price override was added. Existing estimator and calculator return USD 0.067 for one 1K output.

[Official Google standard pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-image) additionally charges text/image input at USD 0.50 per million tokens and text/thinking output at USD 3 per million. Images cost USD 60 per million image tokens. The documented 1K image consumes 1,120 tokens: USD 0.0672, rounded to USD 0.067 in the public table.

The backend intentionally reports only one output image and its resolution. It does not report input or thinking usage, so the existing USD 0.067 quote is an output-image component, not a demonstrated all-in ceiling. `responseModalities: ["IMAGE"]` is not evidence that internal thinking or input tokens are free.

## Transport reservation and blocker

This image backend has **five** outer attempts, distinct from H3's three-attempt submit path. Controlled qualification replaced only the third-party SDK boundary: a `TimeoutError` representing response loss after acceptance caused the real wrapper to call the fake five times. No network or generation took place. The wrapper does not classify ambiguous image acceptance like the existing H3 guard.

Five 1K image-output components total USD 0.336 at the exact token rate, before input/thinking charges. This figure is not a full quote or proposed approved allowance. The current request config supplies neither an explicit total-output bound nor a thinking bound, and the path does not capture all billed attempts' usage. A minimum practical all-in numerical reserve has therefore not been established. Keep submission paused rather than reporting USD 0.335 or USD 0.336 as the round total.

[Sanitized qualification evidence](evidence/06-image-fallback-billing-gap.json) records SDK request config, current estimated usage/price, the five controlled calls and the missing axes. The qualified, deduplicated follow-up [#14](https://github.com/pablothobias/ArcReelBR/issues/14) asks for complete or explicitly unpriced estimates, real usage reporting and safe handling of ambiguous retries through existing contracts. It introduces no backend spending cap or new provider.

## One fixture versus the pilot

The current formal three-shot pilot references five reusable assets: one character, one scene and three props, plus three storyboard images. Preserving that registered/reference structure requires **eight initial images**, before any rejected-image retry. Their output-only 1K components would be USD 0.5376 once each, or USD 2.688 across five attempts each; input/reference/thinking costs remain additional and unbounded by the current quote. This is not an authorized pilot image budget.

One fixture image covers one fallback-path exercise only. It does not cover the eight-image pilot set, reference-image inputs to storyboard generation, quality retries, H3 video, evaluation, the pilot allowance or continuity sample. Reassess the actual current formal target set and exact quote after fixing/clarifying the billing boundary, then obtain explicit owner approval for that distinct round. No image-generation approval is inferred from the earlier H3 or audiovisual-evaluation allowances.
