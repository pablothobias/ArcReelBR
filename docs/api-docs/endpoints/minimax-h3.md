# minimax-h3

- Protocol: [Video generation V2](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-create.md)
- Pricing: [Pay-as-you-go pricing](https://platform.minimaxi.com/docs/guides/pricing-paygo.md)
- Code: `lib/custom_provider/builtin_endpoints/minimax-h3.json`, `lib/custom_provider/declarative_backend.py::DeclarativeVideoBackend`
- Request shape: multimodal `content[]` carries first frames, last frames, reference images and reference audio by role; it shares the v1 host but uses a different path prefix (`/v2`); query responses directly include an expiring download URL
- Reference audio: `data:audio/<format>;base64,` with lowercase `wav` / `mp3` (Protocol page); the definition's `ref_audio.container_mime` emits it from the detected container (`packages/arcreel-market-core/src/arcreel_market_core/endpoint_definition/template_engine.py::asset_container_mime`)
- Errors: create HTTP errors carry `error.message` (Protocol page); query failures carry `task.error.{code, message}` (official v2 query page). `extract.error_code` classifies `2013`, `1026`, `1027` as fix_input and `1004`, `1008` as configure, per the platform error-code reference; other codes stay unclassified (`lib/custom_provider/declarative_backend.py::ProviderJobRejectedError`)
