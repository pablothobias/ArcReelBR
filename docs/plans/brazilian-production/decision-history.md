# Historical interview record

This records successive interview statements, including superseded choices. The consolidated README is also a historical snapshot. Current production ownership is defined in `AGENTS.md`; the later investigation state is recorded in `docs/handoffs/2026-11-09-investigations/README.md`.

# Brazilian end-to-end production

Status: discovery and decision interview; no implementation approved by this plan yet.
Baseline inspected: main, 401488f40 (2026-11-08).

## Confirmed requirements

- Run ArcReel locally without Docker, using the existing Claude Code subscription setup for the embedded Agent.
- Use Codex with MCP tools and skills to research, execute, inspect outputs, make production decisions, and start processes.
- Research foreign scripts, episodes, and reference videos online, validate sources, and develop content for Brazilian social-media audiences.
- Produce Brazilian Portuguese creative content while keeping technical instructions and prompts in English. Literal dialogue and narration must remain in the intended output language.
- Support series, meme videos, and self-contained short dramas.
- Select providers and models with the owner and distinguish configuration from necessary implementation changes.

## Decision tree

1. Control ownership: Codex delegates to the embedded Agent, calls production tools directly, or mixes both under explicit ownership rules.
   - Depends on this: MCP session-control contract, response tracking, concurrent writers, recovery.
2. Completion boundary: reviewed export or publication to social platforms.
   - Depends on this: delivery formats, publishing integrations, success evidence.
3. Autonomy policy: spending, retries, creative approvals, and exceptions.
   - Depends on this: service-enforced limits and automatic correction policy.
4. Reference-use policy: original works inspired by verified references versus close adaptation.
   - Depends on this: source dossier, adaptation checks, source material handling.
5. First acceptance scenario and subsequent coverage across all three content types.
   - Depends on this: model selection, duration, platform, visual style, acceptance metrics.

## Investigation areas

These are investigation areas, not a claim that each capability is absent:
- Existing MCP production tools versus embedded Agent session control.
- Persistent production state, questions, response cursors, completion, retry and restart semantics.
- Source provenance, actual reference-video access and evidence of observed content.
- Brazilian cultural adaptation and independent instruction/content language policies.
- Provider/model capabilities and configuration gaps.
- Visual, speech, subtitle, continuity and timing review, including automated correction limits.
- Rendering, editable delivery and end-to-end acceptance evidence.

## Evidence

- [Existing orchestration research](../../research/codex-arcreel-delegation.md): prior code assessment, not a live validation of the bridge.
- [Language policy](../../adr/0122-english-product-defaults-preserve-project-language.md).
- [Local subscription execution](../local-subscription-run.md).

No virality guarantee is implied. A measurable definition of publication readiness and later audience performance remains to be agreed.

## Round 1 decisions (2026-11-08)

Confirmed by the owner:
- Codex researches, directs and validates; the embedded Agent executes ArcReel production operations.
- Completion is a reviewed export with title, description and source information. Automatic publication is outside this first delivery.
- Develop original Brazilian-context stories inspired by verified foreign references.
- Every production starts from a reference. Codex should autonomously compare, decide and correct within the production objective. Spending and attempt ceilings remain unresolved.
- Use the owner's existing 30 ideas in `/Users/pablo.carminatti.br/Desktop/final-br-storyboards`, improving and adapting them to ArcReel. The previously suggested 30–60 second invented pilot is not the selected input.

## Initial input inventory

The directory contains 30 numbered Markdown requests plus an index and conversion notes. All 30 numbered files contain a reference URL and storyboard sections. The index lists target durations from 12 to 28 seconds. These are document facts, not verification of the linked videos. The first request explicitly includes dialogue, shot timing, subtitle timing, continuity and production instructions.

Legacy request fields refer to an external CLAUDE.md spending cap and include `falas intactas: sim`. The owner now requests improvement and adaptation; document these revisions explicitly while preserving the original inputs. Do not inherit an unspecified historical spending ceiling.

Next decisions: comparison criteria and inaccessible-reference behavior; provider/model choices; spend and retry units and ceilings; selecting acceptance samples after source-access and model-capability assessment. Series continuity requires additional coverage beyond this independent-video collection.

## Round 2 decisions (2026-11-08)

The owner accepted Q6, Q7 and Q9:
- Evaluate reference fidelity at the level of hook, narrative mechanism, progression, rhythm and payoff; independently evaluate Brazilian-language naturalness, clarity, continuity, visuals, audio and subtitle timing.
- Codex may revise dialogue and duration with recorded reasons, preserving original inputs. The adapted script supplies concrete production acceptance details.
- If a source cannot be inspected, autonomously seek and record a compatible verified replacement; if none is found, pause that request and continue others. Titles and descriptions are not evidence of video inspection.
- Use per-video and per-batch financial ceilings, counting discarded outputs, and at most two additional generations per rejected segment after its initial generation. Polling an existing task is not another generation. Monetary limits remain pending model selection and an example quote.
- Provider/model selection remains open. The owner requested an inventory of the model roles required before choosing names.

## Model and responsibility clarification (2026-11-08)

- Research, reference interpretation, Brazilian adaptation and structured-script preparation belong in Codex before ArcReel ingestion. Existing internal text-generation calls must be audited for bypass or adaptation; do not require a separate writing model merely to duplicate Codex's work.
- The owner selected MiniMax H3 for video. The initial ElevenLabs preference was superseded by the native-first decision below; it is an optional fallback, not a required stage. The exact H3 provider endpoint remains open.
- The owner asked whether images can be generated inside Codex. This conversation exposes image generation/editing, but automatic transfer, formal asset registration, reproducibility and unattended access remain integration work, not demonstrated capabilities.
- Separate voice production requires an explicit dialogue timing and lip-sync strategy for on-screen speakers. Replacing an audio track alone is not evidence of synchronization.


## Native-first constraint (2026-11-08)

The owner explicitly prioritizes preserving the existing ArcReel harness and production workflow. Test native production quality first. Use video-generated voices if they meet acceptance criteria; ElevenLabs is optional and justified only by observed shortcomings. Generate images within ArcReel if external-image ingestion would require unnecessary workflow changes. Do not promise integrations before verifying their actual paths.

Verified in source, not executed in this interview:
- `server/routers/files.py` accepts character, scene, prop and product image uploads and associates them with project assets.
- `server/routers/shot_uploads.py` accepts storyboard-image uploads for existing storyboard-route shots, registering versions and formal asset state. This is an existing API path, not proof of a working Codex-to-ArcReel transfer.
- `lib/script/reference_video/voice_settings.py` represents video-generated audio, optional reference audio and silent modes according to resolved capabilities. This does not establish H3 capabilities for the eventual selected provider or Portuguese voice quality.

Implementation priority: configure existing capabilities, test one representative input, identify actual failures, and propose only the smallest necessary changes. Monetary ceilings and provider selection still precede paid trials.

## Text execution through Agent SDK: feasibility (2026-11-08)

Accepted by the owner on 2026-11-08, not implemented: add a TextBackend implementation using the official Claude Agent SDK with the owner's existing local Claude Code authentication. Preserve TextGenerator, its callers, schema validation and accounting contract; register/select the new backend through existing resolution. Use isolated generation sessions without production tools to avoid recursive tool calls or contamination of the supervising conversation.

Source evidence: TextGenerator already delegates to TextBackend.generate; the installed SDK includes output_format JSON-schema options and structured_output results. Image inputs, output limits/truncation, usage accounting, concurrency, timeout and cancellation require adapter-specific validation. An isolated schema-producing trial plus one representative production call is needed before declaring equivalence. No paid or subscription-consuming trial was run in this assessment.

Official authentication evidence checked: https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan (October 7 update: signed-in Agent SDK use draws from subscription limits), and https://code.claude.com/docs/en/legal-and-compliance (end-user sign-in to unmodified Claude Code; do not collect or intermediate user credentials). This personal local design must use the official authentication flow, not extract OAuth tokens for direct Messages API requests.


## Accepted model choices (2026-11-08)

- Internal text generation: official Claude Agent SDK using the owner's local subscription login; Claude Opus 5.5 with medium effort. The catalog records `claude-opus-5-5`, and the installed SDK exposes `effort`; the exact execution combination remains to be tested. Preserve existing TextGenerator consumers and validation.
- Images: prefer images generated in the Codex conversation and ingested through existing formal upload paths if the integration trial succeeds. Otherwise use the owner's selected Nano Banana 2 through an ArcReel image provider. Verify the exact provider/API identifier; do not silently substitute Nano Banana 2.1 or another successor.
- Video: MiniMax H3, provider still unspecified.
- Separate voice service: ElevenLabs. Preserve the earlier native-first policy: test video-generated audio first and use separate voice when necessary; the latest model list does not explicitly revoke that policy.
- Remaining decisions: provider access for image/video, precise financial ceilings, recovery on quota exhaustion, output acceptance and initial test order, series continuity requirements.

## Provider and recovery decisions (2026-11-08)

- Q12 accepted: persist progress and pause new text requests when subscription limits are reached; resume when quota is available. Never silently switch to paid API authentication.
- Q13 accepted: select one of the existing 30 requests after source/capability checks, validate the full production and export path, then expand to the batch. Add a separate cross-episode continuity acceptance test for series.
- H3 provider selected: official MiniMax, https://www.minimax.io/, whose API platform is https://platform.minimax.io/.
- Existing integration evidence: bundled catalog binds MiniMax-H3 to minimax-h3; `lib/custom_provider/builtin_endpoints/minimax-h3.json` supplies its declarative video endpoint. This establishes an existing integration path, not account access or successful generation.

## Existing continuity audit requested (2026-11-08)

The owner accepted Q14/Q15: affirmed platform access and keeping the application interface in English. Credentials and actual API entitlements have not been inspected.

Q16 was not accepted as new functionality. The owner explicitly requires auditing existing continuity features and reusing solved behavior. A new persistent series bible is not approved. Existing project assets, episode ledger, overview, formal scripts and voice bindings must be evaluated before proposing any additional storage or workflow.

Initial verified source evidence: project-wide characters/scenes/props and overview are passed into script prompt authoring (`lib/script/script_generator.py`); the episode ledger stores ordered episode identities, outlines and source origins; character voice binding supports prompt descriptions or reference audio (`lib/speech/character_voice.py`). These are existing mechanisms, not guarantees that a model preserves every narrative fact or voice in generated output.

Audit conclusion: reuse the existing project representation; do not add a parallel series bible. Drama planning includes current/next episode outlines (see ADR 0032 and `lib/prompts/prompt_templates/templates/text/drama_script_plan.md`), with tests ensuring the next outline connects the ending without importing future plot. This establishes planning continuity, not automatic comprehensive recall of prior episodes. Prior-event consistency should first be checked using existing sources/formal scripts in Codex supervision; no new persistence is justified by this audit. Read-only source/test inspection only, no runtime production or new test run.
