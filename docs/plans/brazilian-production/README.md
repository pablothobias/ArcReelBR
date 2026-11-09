# Brazilian production: consolidated implementation plan

> Historical planning snapshot (2026-11-08), preserved for provenance. Production ownership was subsequently clarified: the native ArcReel Agent owns creative decisions; Codex connects and supervises through MCP. See `AGENTS.md` and [the investigation handoff](../../handoffs/2026-11-09-investigations/README.md) for the later state. The decisions below are not current production instructions.

Status: source/configuration audit complete; remaining owner decisions below. No production implementation or paid generation performed in this audit.
Baseline: `main` at `401488f40`, inspected 2026-11-08.

## Current decisions

- Preserve the existing ArcReel harness, domain state, generation queue and delivery pipelines. Configure and reuse before adding code.
- Codex researches verified foreign references, adapts original Brazilian stories, prepares scripts, directs production and reviews results. The embedded Agent executes production through existing application operations.
- Every production has an inspected reference. If inaccessible, Codex may find a verified compatible replacement; otherwise pause that item and continue others. A title or description is not video-inspection evidence.
- Start with the 30 requests at `/Users/pablo.carminatti.br/Desktop/final-br-storyboards`. Select one representative request after reference/capability checks, then expand. Add a two-episode continuity test using existing project data.
- Brazilian Portuguese creative content; English technical instructions/prompts with literal Portuguese dialogue preserved. Interface stays English.
- Internal text calls: official Agent SDK with the owner's local subscription login, Opus 5.5, medium effort, isolated generation sessions behind TextBackend. Preserve validation and usage records.
- Video: MiniMax H3 through official international MiniMax. Images: Codex generation plus existing uploads if practical; Nano Banana 2 (`gemini-3.1-flash-image`) through existing Google integration otherwise. Do not substitute a successor silently.
- Test native H3 audio first. ElevenLabs is the selected separate-voice alternative if needed, not an obligatory step for every video.
- Completion: reviewed rendered video plus title, description and source information. No automatic social publication in the initial scope.
- On subscription quota exhaustion: persist progress and pause new text calls. No automatic paid API fallback.
- **Budget and quality-attempt controls belong to Codex's execution context, not new ArcReel backend logic**, explicitly clarified by the owner during this audit. Use existing quotes and cost records. Per-video and per-round amounts remain undecided. Initial generation plus at most two additional quality regenerations per rejected segment; polling is not regeneration.

## Audit method and limits

Read source, related ADRs and existing tests. Checked the selected local database read-only for configuration presence and the Codex MCP configuration without exposing secrets. No tests, provider trials, media generation or server restart ran during this audit. Source support is not provider access or output-quality proof.

Observed local configuration: no ArcReel tools exposed to this conversation; no ArcReel-named MCP entry in the checked Codex config; no provider credentials/custom providers/provider-config rows in the selected application database; no explicit default text/image/video/audio settings in the queried keys; no populated legacy Anthropic key. Owner affirmed platform access, which is distinct from configuration in this application.

## Reuse without rebuilding

| Area | Existing mechanism and evidence | Required action |
| --- | --- | --- |
| Local execution | `scripts/run_local.sh` starts both servers with cleaned environment, optional setup and no-reload default | Verify configured runtime at trial; no new launcher |
| MCP server and production tools | `server/remote_mcp.py:65`; `server/agent_toolset/toolset.py:27` | Connect Codex with existing access-token authentication |
| Embedded Agent sessions | `server/routers/assistant.py:153` onwards; `server/agent_runtime/service.py` | Reuse send, accepted/queued state, idempotency keys, entries, SSE, questions and interrupt |
| H3 | `lib/custom_provider/builtin_endpoints/minimax-h3.json`; catalog binds `MiniMax-H3` | Configure credential and international base; select capabilities and trial |
| International MiniMax | `lib/backends/minimax_shared.py:25` defaults to mainland; `:26` defines international override | Configure `https://api.minimax.io/v1` through existing provider settings; validate resolved H3 `/v2` request |
| Nano Banana 2 | `lib/catalog/snapshot/catalog.json`, AI Studio/Vertex bindings for `gemini-3.1-flash-image` | Configure Google provider only as needed; trial exact model |
| Image ingestion | `server/routers/files.py:438`; `server/routers/shot_uploads.py:48` | Upload through formal API paths with version/asset registration, not file-copy-only ingestion |
| Source and script state | Markdown upload normalizes to source text (`files.py:724`); structured review/confirmation (`script_review.py:100,149`) | Map prepared material into existing schemas, preserving formal validation |
| Series continuity | Project overview, characters/scenes/props, derivatives, voices, episode ledger and current/next outlines | Reuse; no parallel series bible or duplicate narrative database |
| Review tools | `image_review.py:17`; `video_review.py:18` | Reuse image/contact-sheet inspection and local black/freeze/cut signals |
| Editing and delivery | `final_cuts.py:14`; `jianying_drafts.py:14`; `lib/final_cut/ffmpeg_render.py` | Use existing timelines, audio mixing, subtitle variants, render and optional editable export |
| Usage and quotes | `server/services/admission/video_quote.py`; `cost_estimation.py`; billing ledger | Consume from Codex; no new backend budget enforcement |
| Provider-job recovery | `lib/generation/restart_recovery.py:125`; task retry-download endpoint | Resume eligible existing jobs; preserve prohibition on blind paid resubmission |
| Approval/autonomy | ADR 0065 allows already-authorized autonomy using existing confirmation parameters | Encode owner policy in Codex skill; no new permission engine |

## Actual implementation and integration work

### P1. Expose embedded session control through existing MCP

Add thin tools over AssistantService for starting/sending, inspecting/polling state and entries, answering questions and interruption. Preserve project ownership, client_key idempotency and accepted-versus-queued semantics. Expose pending questions as well as history. A turn result is not proof that the session is idle or the production artifact is ready. Do not build another Agent runtime or MCP server.

Acceptance: one real local delegation reaches terminal state; Codex sees questions and failures; retries do not duplicate accepted instructions; reconnect retrieves correct state. Reuse existing generation batch polling for media jobs.

### P2. Add subscription-backed text execution

Implement a TextBackend using the installed official Claude Agent SDK. Register/select it through the existing resolver while preserving simple/complex tiers, response schemas, image inputs, output-limit/truncation handling and usage accounting. Select Opus 5.5 and medium explicitly for this backend. Keep sessions isolated without production tools. Do not silently use an API key or charge text tokens at API prices under subscription.

ADR 0124 is the accepted narrow extension to the existing separation described by ADRs 0017/0051; it does not merge Agent credential storage with media-provider credentials or make Agent conversation models inherit arbitrary text-tier selections.

Acceptance: structured response, image-input task, timeout/failure, quota exhaustion and one real script operation through the existing consumer contract.

### P3. Support Brazilian content language without translating the UI

Verified gap: `server/tool_runtime.py:2522` and `ProjectOverview` language enum accept only zh/en/vi/ru. `lib/speech/speech_rate.py:27` falls back to Chinese units for unknown languages. Add explicit Portuguese content-language handling and tested reading-unit/timing behavior.

Verified gap: `script_generator.py:912` and drama/reference prompt-authoring templates currently couple technical strings to source_language. Separate English technical directions from Portuguese dialogue/narration/subtitles. Preserve existing projects, references and formal-script contracts.

Acceptance: a PT-BR source is explicitly represented, technical prompts are English with verbatim intended Portuguese speech, and speech estimates do not use the Chinese fallback.

### P4. Build the Codex directing workflow and its recovery record

Create a dedicated Codex skill using existing project state and tools. It owns source verification, reference evidence, Brazilian adaptation, decisions, review and correction, final delivery packaging, and a small persistent record of outstanding intent and review results. Do not duplicate formal assets, episode scripts or the application workflow status.

Budget policy is **Codex-only**: retrieve quote/current usage, account for pending authorized work, authorize only within remaining allowance, persist per-video/per-round spending and quality-regeneration counters, and stop at agreed boundaries. Count discarded work and billable retries; avoid equating an unknown price with zero. Use sequential paid admission initially if needed for reliable accounting. Existing transport retries and provider-side charges must be included in estimates/margins; a Codex control is not an application-wide lock on manual or independently initiated spending.

Persist pause reason and resumption intent when quota is exhausted. Reuse existing session and provider-task recovery; do not regenerate merely because a wait timed out. Choose active-chat versus unattended continuation scope before promising background operation.

Acceptance: a deliberately interrupted directing round can recover from authoritative project state and recorded intent without duplicate paid work; spending/attempt boundaries stop further Codex-authorized submissions.

### P5. Validate the input handoff, reusing existing APIs

The 30 Markdown files are source material, not formal ArcReel JSON. Prepare a mapping to the current structured planning/editing contracts; use source upload plus existing normalization/review, or validated structured submission where appropriate. Keep original files and recorded editorial changes. Reconcile inherited `falas intactas`, old CLAUDE.md cap references and montage timings with current decisions.

Test Codex-produced image upload into one existing asset/shot through formal endpoints. Only add a narrow MCP wrapper if the existing authenticated transport cannot be used cleanly. No new source importer, asset store or image provider is assumed necessary.

### P6. Close the audiovisual evaluation boundary

Existing review samples image frames and returns local technical signals; `model_review` is always null. It does not establish actual speech content, audio quality, sentence-level subtitle synchronization or lip-sync. Verify accessible audio/video inspection tools and add only the missing inspection/alignment bridge needed for Codex review.

Existing subtitles are mechanical timed drafts (`lib/speech/speech_presentation.py:139–147,210`; ADR 0089), not observed speech alignment. Preserve their pipeline. If trial output fails accepted timing criteria, add alignment/correction within that pipeline rather than a second subtitle renderer.

Acceptance must include listening/observing actual output, reference comparison, Portuguese speech, cut/order/continuity, subtitle timing and rendered-file playback. No visual-only pass may claim full audiovisual approval.

### P7. Conditional voice integration

No built-in ElevenLabs backend/endpoint was found in the inspected provider registries and implementations. If native H3 audio fails, integrate the selected ElevenLabs model/voices through existing audio abstractions. Existing narration TTS does not automatically replace individual speakers in a native mixed audio track or synchronize their lips. Determine the necessary route from observed failure; do not preemptively rebuild dubbing.

### P8. Real acceptance trials

Use one of the owner's 30 requests first, then a two-episode continuity case. Validate exact provider/model capability, formal registration, resume behavior, full review and final export. Expand to the remaining requests only after this works. Run proportional implementation checks, then bounded real trials within approved costs; do not infer live performance from existing mocked tests.

## Delivery decisions and remaining setup

The owner selected 1080p delivery and approved active-chat automation with persisted recovery checkpoints, rather than a new unattended supervisor. The first financial round is one pilot, with unknown-cost submissions paused. Numeric budget amounts and currency remain unset: approval of the policy does not invent a spending allowance.

Deliver vertical 1080 × 1920 with Portuguese burned subtitles. Verify provider generation tiers before choosing a source resolution; 1080p delivery does not imply H3 supports native 1080p. Use the existing renderer for conversion where required, record the source resolution, and quote the selected path before paid work.

Quality criteria remain the approved reference comparison plus Brazilian speech, clarity, continuity, visuals, audio and subtitle timing. Conditional ElevenLabs model/voice selection and any lip-sync or subtitle-alignment changes follow observed failures, not speculative implementation.

The owner approved the breakdown. [Spec #2](https://github.com/pablothobias/ArcReelBR/issues/2) and ten child tickets were published with verified native blocking dependencies; see the [ticket index](tickets/README.md). No implementation has started.

## History and validation

[Interview history](decision-history.md) preserves prior rounds including superseded assumptions. ADRs 0123 and 0124 capture the accepted architectural boundaries. Only documentation changed in this audit; no source implementation, database mutation, account configuration, API-key creation or generation was performed.
