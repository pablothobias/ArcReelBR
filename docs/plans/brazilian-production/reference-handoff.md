# Verified reference handoff

Status: local acceptance evidence for ticket #7 passed, including independent Codex review. The embedded Agent created and confirmed one formal episode through supported operations. Paid media generation and evaluation remain paused for later tickets and explicit spending approval.

## Private checkpoint and preserved inputs

Request ordinal 24 was selected from the owner's 30-item collection. All 30 original files still match the private SHA-256/size manifest. The selected original hash is `5b65c3d6863d3e0902e0634989b6ac47bffcbca090b2d4a0f07b5ce336b767d6`.

Private checkpoint: `/tmp/arcreel-goal-state/reference-preparation/`. It contains `original-collection-manifest.json`, the preserved original, `adapted-screenplay24.md`, `editorial-decisions24.json`, `reference24-dossier.json`, actual reference media/frames/audio measurements, durable send intents, authoritative session receipts, `formal-handoff-validation.json`, `workflow-final.json` and `ledger-summary.json`. These temporary local artifacts must be preserved or moved to private durable storage before deleting that directory. This repository contains no owner screenplay, dialogue, protected reference frames, access token or raw transcript.

The private editorial record identifies every narrative/material change and timing correction. Original intended spoken words and the 16-second montage target are preserved. A timing relaxation in the prepared source was explicitly corrected back to the original tighter endpoint in the formal directions. New synthetic Brazilian characters replace the reference identity. The inherited unspecified `CLAUDE.md` ceiling was removed; no media spending ceiling is assumed.

## Actual reference inspection

- Original source: https://x.com/sama/status/1758219575882301608
- Publisher: Sam Altman; original upload date 2024-02-15; accessed 2026-11-08.
- Media ID: `1758219437684224000`. Downloaded-media SHA-256: `93498d79b11197f85c09770dc95be0f07c47092dda88bba6ff5219ce82464dc0`.
- Decoded source video: 1280 × 720, 30 fps, 9.966 seconds. Container duration: 10.027 seconds. These reference dimensions do not describe H3 generation tiers or 1080 × 1920 delivery.
- Ten actual decoded frames at one-second intervals establish a rustic-kitchen presentation: an older woman smiles and waves, then mixes and lifts a glass bowl. Sampling supports observed events, not frame-exact event boundaries. The Brazilian narrative introduces its own mechanism; it is not reported as an event in the foreign source.
- The AAC stereo 48 kHz track decodes to digital silence across 481280 stereo sample frames. Full-track peak and RMS are negative infinity. Independent PCM decoding found zero nonzero bytes in 1,925,120 bytes. No spoken source words exist to transcribe, so ASR is inapplicable rather than fabricated.
- The original source was accessible; no replacement was necessary. Source identity and protected footage were not registered as production assets.

Actual retrieval and inspection used `yt-dlp --skip-download --dump-single-json`, `yt-dlp -f 'best[ext=mp4]/best'`, `ffprobe -show_format -show_streams -of json`, `ffmpeg -vf 'fps=1,scale=640:-1'`, and full-track `ffmpeg -af astats=metadata=1:reset=0`. Exact outputs and filenames remain in the private checkpoint.

## Supported handoff and correction history

Project: `br-reference-pilot-24`; episode 1, own source, `source_kind=screenplay`, `source_language=pt-BR`, vertical 9:16. The isolated application was reached through authenticated MCP at port 1242. The production instance was not used as a fixture.

Embedded session: `123122d0-78c5-47b6-bc48-3357d1d76f36`. Each send had a durable private intent and unique client key before submission. The director reconciled actual session entries and queued acceptance; queued messages were never treated as executed work or automatically resubmitted.

| Input or result | Existing operation actually used | Verified result |
|---|---|---|
| Dedicated project | External authenticated MCP `create_project` | One isolated project |
| Episode source | Embedded `upload_source`, `role=episode`, `source_kind=screenplay` | `source/episode_1.txt`; bytes match prepared source |
| Project model/style settings | Existing authenticated project REST PATCH | HTTP 200 and embedded readback; exact H3 and Nano Banana 2 selections |
| Structured content | Embedded `generate_script_plan` | Three shots totaling 16 seconds |
| Director corrections | Embedded `open_draft`, `patch_draft`, `promote_draft` | Corrections validated without regenerating content |
| Formal confirmation and asset registration | Embedded `confirm_script_review` | Confirmed formal script; five reusable assets |
| English visual directions | Embedded `generate_episode_script` | All three pending shots authored through subscription text |
| Metadata and canonical-speech corrections | Embedded `patch_episode_meta`, `patch_episode_script` | Mirrored title and one compiled occurrence of intended speech |

The first embedded turn correctly stopped when the narrow `patch_project` tool rejected provider/style settings and video capabilities were unavailable. The director used the existing project REST settings boundary, then the same session checked actual settings, capabilities and absence of prior work before planning. No application code change or credential change was needed.

Independent review identified a spoken quotation duplicated in a visual action field. The embedded Agent removed only that duplicate using `patch_episode_script`; the canonical Portuguese utterance remained unchanged. The existing drama prompt compiler now emits the intended speech exactly once. A metadata-only correction mirrored the approved title into the formal script and episode ledger. Neither correction regenerated text or media.

## Final readback and validation

Authoritative local project root: `/tmp/arcreel-goal-state/runtime/data/projects/br-reference-pilot-24/`.

- Formal artifact: `scripts/episode_1.json`; SHA-256 `2e10b80e097ca58a9fde27a20da7ed88c346d890f12414b58a81120d836428a3`.
- Project metadata SHA-256: `485688b92703f9a0f59f6cb24053ffe7dcfa95566187cb4dfec667bd83dada15`.
- `DramaEpisodeScript.model_validate` passes. Formal IDs are `E1S04`, `E1S05`, `E1S06`; montage durations are 8, 4 and 4 seconds.
- Exactly one canonical Portuguese utterance matches the original intended words. `render_storyboard_video_prompt` emits its literal once across the episode. Image/video direction fields are English, retaining Portuguese asset-name references.
- The existing review service reports `confirmed`. Authenticated workflow-status GET returned HTTP 200: formal content current, no pending prompt authoring, no unregistered references.
- Project assets: one character, one scene and three props. Character identity is reused in two shots, the scene in all three, and every asset reference resolves to the existing project tables. No duplicate per-shot asset store was created.
- Actual session state is completed, with no queued messages or pending questions. Read-only database inspection found two succeeded text tasks and zero media-generation tasks or calls.
- Independent Codex review rechecked original hashes, source identity, contact-sheet observations, full silent PCM, schema, active source bytes, canonical speech compilation, asset references, confirmation/workflow state and database records. No finding remains.

The 8 + 4 + 4 montage happens to fit the locally registered H3 whole-second range. This is not proof of provider access, native output resolution, audio quality or actual duration delivery. The final renderer's delivery conversion remains a separate requirement.

## Recorded subscription usage

The isolated project's eight successful text records contain 1,982,252 input tokens and 19,084 output tokens. Input includes 1,881,031 cache-read tokens and 97,865 one-hour cache-write tokens. These are recorded token measurements, not a monetary quote.

| Existing accounting path | Model | Records | Input tokens | Output tokens | App cost representation |
|---|---|---:|---:|---:|---|
| Embedded Agent | Opus 5.5 | 5 | 1,964,364 | 14,149 | Zero under existing subscription accounting |
| Existing session-title helper | Haiku 5.5 | 1 | 3,282 | 444 | Zero under existing subscription accounting |
| Internal text backend | Opus 5.5, medium effort | 2 | 14,606 | 4,491 | Unpriced; no fabricated API charge |

No paid image/video/audio generation or evaluation occurred. Neither zero app records nor SDK theoretical dollar estimates establish the subscription's actual external fee. The existing session-title helper remains separate from the internal text-backend model boundary.

## Resumption and next steps

Ticket #7's formal handoff is prepared. Media sheets, storyboard images, native H3 audio/video trials, numeric quotes and owner approvals, final rendering and audiovisual acceptance belong to later tickets. The observed next step is asset-sheet preparation, with all media still missing. Resume from the authoritative formal script and project assets, reconcile jobs before any submission, and obtain the separate approved spending round before generating media. Native audio must be inspected before considering separate voice or lip-sync work.
