# Gemini image accounting and bounded estimates

Issue #14 corrects the existing Gemini image path without changing its selected model, adding another generation harness or installing a backend monetary cap. Deterministic SDK/HTTP-boundary tests make no paid provider request. Factory catalog snapshots and their provenance remain unchanged. No effective settings or credentials were edited during implementation.

## Accounting and delivery

Gemini prompt tokens include reference-image input. The backend reports that input once, partitions reported candidate image tokens from the remaining response tokens, then adds thinking only to non-image output. Reported cache reads are separated from uncached input. An omitted thinking measurement remains unknown unless the consistent prompt/candidate/total measurements establish its residual for this tool-free request. Missing or inconsistent required measurements explicitly make settlement unpriced; missing values are not invented zeros.

The result retains aggregate input/output and available modality details. A received response that fails image parsing or persistence carries its measured result through the existing failed-call ledger path. It remains failed, with no artifact claim, while retaining reported reference cost. Ambiguous delivery carries unknown usage, remains failed/unpriced and does not imply a zero charge.

The image SDK uses explicit httpx clients, one SDK attempt, no automatic function continuation and no automatic redirects. The backend retries only definitely-unsent connection/acquisition failures. Read/write response loss, a generic timeout, provider errors and postresponse parsing/persistence errors never automatically submit another image. Existing video checkpoint/retrieval behavior is unchanged.

## Conservative quote contract

Optional catalog image facts `max_input_tokens` and `max_output_tokens` are positive integers. They are distinct from output-token estimation bases. Entry parse/write/edit round trips preserve them, and absent bounds remain absent. The existing model-information editor keeps the complete facts object when editing displayed fields; its generic facts type does not discard these additions.

For Gemini image estimates, both bounds and all applicable prices must be known. The estimator prices the full input limit and two **disjoint** combined-output allocations: all output tokens as images, or all as text/thinking. Both endpoints must be fully priced; their larger cost bounds any intermediate split under a linear price table, including nonnegative free allowances. Context-dependent tables remain unpriced because their rates need not increase with context. The preview exposes `estimate_basis: full_context_output_upper_bound`. This is a full-context/output upper bound, potentially much larger than expected usage, rather than an exact prompt quote.

The same effective entry supplies the output ceiling to the actual image request through `MediaGenerator`; bound custom-provider entries retain the same ceiling through their existing wrapper. Requests still use the selected model and one candidate. Unknown bounds/rates keep the existing preview incomplete. Applying a user entry correction is a separate supported configuration action; it does not grant spending approval.

## Reviewed data for the selected model

Official Google primary sources checked on 2026-11-08:

- [Gemini 3.1 Flash Image pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-image): USD 0.50 per million text/image input tokens, USD 3 per million text/thinking output tokens, USD 60 per million image output tokens. A 1K image uses 1,120 image tokens, yielding USD 0.0672 before input/thinking. The displayed USD 0.067 is rounded and is not a complete call quote.
- [Selected model limits](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image): input limit 131,072 and output limit 32,768 tokens.
- [GenerateContent usage metadata](https://ai.google.dev/api/generate-content#UsageMetadata): prompt, candidate, thinking, total and modality-detail measurements have distinct meanings.
- [Image generation thinking](https://ai.google.dev/gemini-api/docs/image-generation#thinking-process): thinking is billable; a thinking level is not a numeric token ceiling.

A reviewed user-entry correction for this exact model can therefore use those two bounds and three token meters: `uncached_input_tokens: 0.50`, `output_tokens: 3`, `image_output_tokens: 60`, each per million according to the existing meter vocabulary. It replaces rounded image-count pricing for that entry; it does not add a second image-output charge. At multiplier 1, the resulting full-context/output bound is USD 2.031616 per request: USD 0.065536 input plus USD 1.96608 combined output at the larger rate. Actual measured reference cost is settled separately and is not a provider invoice.

## Deterministic evidence

The focused tests cover real SDK serialization, exact nonoverlapping token arithmetic, rounded-image price correction, missing/inconsistent metadata, omitted-thinking evidence, both conservative output endpoints, missing bounds/rates, custom entry cap propagation, and transport certainty. Existing consumer integration drives the normal quote, image generation and ledger with mocked external HTTP: successful images, missing images and save failures retain reported usage; ambiguous loss makes exactly one request and stays unpriced. Catalog-core tests cover optional-bound round trips and invalid values. No protected scripts, media or provider credentials are included in this evidence.

Final validation: 1,965 broad consumer tests passed; one newly added custom-provider fixture initially used a read-only ORM property and was corrected to its mapped identifier. The complete new SDK/consumer suite then passed all 28 cases, independently repeated by the reviewer. All 109 catalog-core tests passed. Edited-file type checking, Ruff, touched-test auditing and whitespace checks passed. No unresolved failure remains; the full broad suite was not repeated after the fixture-only correction.

Independent review reproduced an outer reference-compression fallback that could mistake a postresponse save error containing “payload too large” for an unsent request. Typed received-response and ambiguous-delivery exceptions now terminate before that fallback. The regression uses a real reference PNG and asserts exactly one mocked provider request and preserved failed usage. This validation does not establish live image quality or authorize a paid call.
