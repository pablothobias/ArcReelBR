# Image encoding and downstream MIME correction

Issue: [#16](https://github.com/pablothobias/ArcReelBR/issues/16). This correction concerns media encoding and request metadata. It does not fix or reverse the owner's rejection of the generated character's artificial appearance.

## Qualified mismatch

The preserved rejected fixture is JPEG data at the canonical `characters/Ana.png` path, 1376 × 768, 357,068 bytes, SHA-256 `798741b81a9b82fff30a40ac312be5cb659739ec217de1092955f06d74a1af25`. Its original version copy has the same bytes. The installed Google SDK image object's `save` writes its original bytes; choosing a `.png` filename did not encode PNG. The declarative downstream engine previously selected MIME from that suffix, allowing JPEG bytes to be labeled `image/png`.

No remote rejection was tested or inferred. Independent qualification reproduced the metadata mismatch locally. The historical artifact, version history, paid usage and owner rejection remain intact; this implementation does not rewrite or promote them.

## Current behavior

- Future Gemini image responses decode their inline bytes through existing `convert_image_bytes_to_png` and persist real PNG bytes. This shared normalizer retains alpha and handles orientation. Encoding/writing stays inside the existing noninterruptible postresponse thread boundary. A decode/save failure retains measured usage in `ImageResponseError` and does not authorize a retry.
- Declarative outbound image assets prefer actual image-header MIME, using the existing shared detector exposed as `image_mime_from_bytes`. The detector's formats and fallback behavior are unchanged. Images are read once; historical mismatched files are not rewritten.
- Audio, video and unknown non-image paths retain their previous extension-based MIME behavior. Existing unsupported-audio and unreadable-file errors remain covered. No provider-specific format list, image store, harness or billing policy was added.

## Deterministic boundary evidence

The focused suite ran the actual installed Google SDK with intercepted HTTP responses containing genuine JPEG and RGBA PNG images. Both produced canonical PNG artifacts; RGBA pixels retained their alpha. An invalid returned image retained billable usage without a saved artifact or retry. Existing cancellation and database-ledger save-failure coverage also passed.

The actual declarative H3 backend constructed serialized requests from JPEG-at-`.png` and ordinary PNG fixtures through intercepted submit/poll/download HTTP. Both first-frame and reference-image data URIs carried the actual MIME and byte-identical payloads. Source files stayed unchanged. Additional tests cover non-image MIME handling, shared historical JPEG/GIF/WEBP/HEIC/HEIF detection, extension fallback, unsupported audio and missing-image errors.

Commands:

```bash
uv run python -m pytest tests/unit/lib/backends/image_backends/test_gemini.py tests/unit/lib/backends/image_backends/test_gemini_billing.py tests/unit/lib/custom_provider/test_declarative_image_mime.py tests/unit/lib/backends/test_data_uri.py tests/unit/lib/custom_provider/test_builtin_declarative_video_parity.py tests/integration/lib/generation/test_gemini_image_billing.py -q
```

Result: **103 passed**, one existing SQLite expression-index reflection warning. Focused Ruff and formatting checks passed for all nine changed Python files. `basedpyright` passed on all four changed source files with zero errors/warnings. `audit_tests.py --check` passed with zero violations across the affected backend/custom-provider/generation test directories.

No paid generation, provider request, upload, settings mutation or application restart was used for this verification. HTTP in these tests was intercepted; it is not provider-access or generated-image quality evidence. Historical rejected bytes were rehashed unchanged after implementation. Runtime integration/restart and any separately approved future generation are coordinated independently.
