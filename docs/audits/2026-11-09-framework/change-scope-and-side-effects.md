# Recommended change scope and side-effect controls

> Stage-7 closure (latest): [integrated results and disposition of all 17 entries](../../plans/native-framework-boundary/stage-7-results.md) records completed local stages, the complementary safe R12 MCP error correction, preserved customizations and 1,472 passing cases. Two pre-existing Web test failures reproduce on the base revision and remain recorded. Earlier pending-stage/recommendation statements below are historical. No commit; current host/configuration readiness remains separate.

Date: 2026-11-09. Reviewed source: `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e`. Analysis and recommendations only. No source changes, new tests, provider requests, production or configuration changes were performed for this review.

This refines [the consolidated dispositions](consolidated-dispositions.md) using [the isolated R10/R11 results](r10-r11-isolated-reproduction.md) and [the expanded runtime review](expanded-runtime-review.md). It recommends concrete choices for the four previously open persistence contracts. Recommendations are not implementation approval or a claim of zero regression risk.

## Governing boundary

Codex is an external client using only the official ArcReel skill and MCP for production. It forwards original requirements/inputs/authorized feedback, carries the user's permission and follows official plan/tool contracts. The framework, including the official skill's supported direct-tool route, owns production semantics. Do not invent an embedded-session-only rule, a replacement external director, direct file/DB production repairs, external acceptance gates or another budget/recovery authority.

Development source inspection here is separately authorized investigation, not permission for Codex to use filesystem/DB operations during production. The application may internally persist its own native artifacts and perform native migrations; external-only Codex access does not imply that all MCP handlers must be filesystem-pure.

## Eight removal mechanisms

### W01: retire the external creative-director package

**Recommendation:** remove `.agents/skills/direct-brazilian-production/` from active skill discovery as a package, not just its title or one role sentence. Its body contains adaptation, exact-candidate and experiment instructions. Do not create a replacement custom production skill. Git history and existing historical documents preserve source provenance; keep private receipts/permission records intact in their existing locations, without importing them into the public repository.

**Side effects to control:** `disable-model-invocation: true` is already present from concurrent work; it alone is not proof that every host entry is retired. Check active repository references and, in the separately owned host setup work, any installed copy. Do not edit unrelated user skills or treat historical mentions as active authority. Preserve official `skills/video-workflow` and `skills/setup-arcreel-skills`.

**Acceptance:** active discovery no longer offers the custom director; the official route remains available. No session, project, media or ledger deletion.

### W02: retire the mandatory custom policy/recovery dependency

**Recommendation:** retire the package's operational `policy.py`/recovery protocol with W01; do not migrate its state machine into MCP, native profiles or another Codex helper. Preserve outstanding job IDs, real permission limits and financial evidence as historical/client context. Old round-specific approvals must not become authorization for a new round.

**Side effects to control:** the two test files `tests/unit/skills/test_direct_brazilian_policy.py` and `tests/integration/skills/test_direct_brazilian_policy_cli.py` load the package by path. Removing the script while leaving these active tests would break collection/execution. Retire only those obsolete policy tests alongside the removed mechanism, and reconcile active references. Do not delete native queue/recovery tests or historical validation receipts.

**Acceptance:** no remaining active command/import depends on the retired helper; native client-key idempotency, batch inspection and provider recovery remain authoritative. Removing a reservation record must never be used to infer an existing paid submission is safe to repeat.

### W03: remove the universal extra pre-generation pair

**Recommendation:** remove only the mandatory `get_project` plus `get_effective_configuration` pre-generation sequence from all three Delegated production sections. Preserve official project identification, `get_workflow_plan` routing, capability admission and application of explicitly supplied settings.

**Side effects to control:** preserve the tools and truthful configuration reporting; do not delete necessary official checks or reinstall the same sequence in the external Codex skill. Config/state inspection remains available when relevant, rather than mandatory for every generation.

**Acceptance:** official next-action routing and supplied settings continue to work without the new compulsory pair. No model/default/language changes.

### W04: remove blanket additional image quotation

**Recommendation:** edit all three surfaces together: generate-assets, all three profiles, and the shared get_project_costs description. Remove the blanket quote-before-paid-action directive, not the quote implementations. The profile sentence mixes added image quotation with inherited native video preview; preserve the latter and actual paid-action confirmation rules.

**Side effects to control:** do not interpret removal as permission to spend unknown amounts, exceed user limits or bypass official confirmation/admission. Preserve quote selection, estimates, unpriced_count and estimate_basis. W04 and R08 are one mechanism in multiple instruction surfaces.

**Acceptance:** both MCP hosts no longer publish the added blanket directive; native video-preview/consent and accounting uncertainty remain intact. No response or pricing changes.

### W05: remove compulsory accounting-call choreography

**Recommendation:** remove the universal pair get_project_usage/get_project_costs from profile prose. Keep requested/necessary reconciliation with the same native ledger, rather than creating another accounting store.

**Side effects to control:** actual permission must still cover the requested operation. The tool's instruction to paginate **for full reconciliation** remains useful and is not another compulsory production stage. Preserve ability to report costs and distinguish unknown from zero.

**Acceptance:** profile removal does not alter ledger data, pagination, estimates or the user's spending scope. Read-cost implementation fixes are separate below.

### W06: remove broad optional-reference policy

**Recommendation:** delete the broad “a reference is optional unless the request requires it” clause; defer to existing native mode/capability/input admission. Do not replace it with a new universal reference requirement.

**Side effects to control:** optional supplied photos/voice samples must not become mandatory, while genuinely required sheets/first frames remain required. Preserve supported upload paths and the no-regeneration meaning of upload.

**Acceptance:** existing mode-specific admission tests for present/missing references remain valid; no creative defaults, asset formats or pt-BR content changes.

### W07: remove external-controller financial authority

**Recommendation:** remove “the controller owns the financial ceiling.” Retain/integrate the meaning that the user's supplied limits and exclusions must be respected, and retain the existing ask-before-excluded-paid-action guard. Do not move policy.py into Codex under another name.

**Side effects to control:** removing a controller role must not erase native responsibility for communicated authorization, introduce repeated confirmation for already authorized actions, or imply a backend-enforced hard total cap exists.

**Acceptance:** no independent director authority remains; the user remains the permission authority and original native safeguards remain.

### W08: remove mandatory ASR acceptance stage

**Recommendation:** remove compulsory per-unit recognition and reviewer handoff from generic editing, then replace the dangling “speech-evidence step above” reference with purpose-scoped guidance for explicitly requested supported timing correction. Preserve evidence limitations, canonical script editing, keeping speech inside trims, and necessary reread/rerender mechanics after an applied correction.

**Side effects to control:** do not remove native first-round visual review, optional review_speech/measured timing, or already applied timing artifacts. A render/contact sheet/ASR result still does not prove acting, lip sync or editorial acceptance. No paid fallback is introduced when local recognition is unavailable.

**Acceptance:** ordinary editing can follow the inherited workflow without mandatory ASR; an explicit timing request can still use the supported native feature. Existing measured-timing read/render/provenance behavior remains intact.

## Five confirmed adjustments

### R07: restrict Settings fields at the tool boundary

**Recommended initial design:** preserve the Web Settings request/transaction. Use an explicit supported field contract for agent-callable configure_project, excluding grid_storyboard from both embedded and external automation until a distinct native user-authorized MCP permission is defined. An external MCP credential identifies a client, not proof that an arbitrary setting mutation came directly from a human. Do not grant external callers an exception based only on source='mcp'.

Reject an explicitly supplied forbidden field, including false/null, before applying any other fields. Do not silently ignore it, partially apply the rest, or broaden the profile's user-only rule to justify the wrapper. Other currently supported fields must retain types, omitted-vs-null semantics and native validation; do not reimplement their transaction. Existing user-only Settings remains the current path for grid changes. A future requirement for user-authorized grid updates over MCP is a separate product contract, not an implicit part of this cleanup.

**Risk/check:** this intentionally closes an exposed tool capability; check both host schemas and direct handler invocation defenses. Test rejected grid requests leave all settings unchanged; normal pt-BR/model/voice settings and Web grid toggling remain supported. Preserve project creation's separate inherited contract and do not reset existing grid flags.

### R09: correct preview versus submitted-batch guidance

**Recommendation:** correct model-facing remote guidance to say polling applies when a generation_batch handle is actually returned, and preview returns immediately without a batch. Keep long_task/waiting semantics for real submitted generation and preserve existing result envelopes. No fake batch handle, preview task or new queue.

**Risk/check:** setting long_task=False globally would break real-generation host behavior. Verify remote preview returns quote/no batch, real remote submission returns a handle, embedded real generation still waits, and structured/text result consumers remain compatible. Review shared-note effects on the older grid preview too, without changing its inherited execution contract.

### R10b: eliminate the cost reader's writing worker

**Preferred recommendation:** resolve this jointly with R10a below: use the native load_script_readonly in the diagnostic cost reader, retaining in-memory compatibility adoption. This removes the reproduced migration write after caller cancellation without adding a new cancellation/resume engine.

**Risk/check:** cancelled read-only threads can still finish computation; this recommendation does not claim they are forcibly stopped. They must not persist scripts or produce late financial/generation effects. Compare returned costs and script content on legacy/current fixtures and retain concurrent-read behavior. If some indispensable dependency still writes, contain that specific write with existing run_sync_transaction; do not blindly wrap every read or claim disconnect behavior was tested.

### R11: make character-image bytes and metadata one native commit

**Recommendation:** follow the existing native install_character_reference_audio/_update_project_with_files pattern for the MCP character-image path: under the same project transaction used by deletion, recheck the character, stage/install bytes and update its pointer with rollback. Reuse native validation/normalization and names. Keep any different intentional Web missing-host semantics separate rather than changing them silently.

**Risk/check:** merely adding host_bucket cleanup after the fact is insufficient: a stable filename may already have overwritten an older valid reference, and blind unlink may delete another concurrent upload's file. A check under a newly added outer lock plus a setter reacquiring the same lock can deadlock; use the existing transaction primitive correctly rather than nesting it around the old setter. Preserve prior bytes/pointer on failed commit, avoid recreating deleted characters, and retain native deletion/trash behavior.

**Acceptance:** controlled deletion-first/upload-first interleavings, initially missing host, normal replacement, failure rollback and concurrent same-target uploads each have coherent outcomes. No reported success with an unregistered owner; no lost prior reference on refused upload. No changes to character-audio/style uploads without independent evidence.

### R12: reject ambiguous route classification at the native boundary

**Preferred bounded recommendation:** in the new no-stored-key/zero-Agent-price branch, explicitly reject incompatible enabled cloud-routing overrides before an inference runtime is started. Reuse a shared native definition of incompatible subscription routes, consistent with the subscription text backend, rather than adding scattered variable lists. Preserve the clean subscription route and existing configured API-credential behavior. Do not silently strip an explicitly selected cloud mode and switch authentication routes, or label an unknown route zero-cost.

This recommendation does not add Bedrock/Vertex/Foundry support; if such support is intended, route-aware configuration and metering require a separate design. It also does not require invoking auth-status per generation, building a Codex preflight or changing current credentials. Configuration/runtime errors belong to the native service and can be relayed through MCP.

**Risk/check:** verify the three synthetic inherited-mode reproductions now refuse the conflicting no-key route before spawn; clean subscription and configured API paths retain correct pricing. Cover launcher and non-launcher entry construction, without actual inference or secrets. Use the SDK's real enabled-mode semantics when resolving flags rather than assuming every nonempty string means enabled. Do not rewrite historical costs from these tests: actual underbilling was not demonstrated. Coordinate with the separate configuration worktree to avoid competing edits.

## Four contract decisions: recommended resolutions

### R10a: costs should adopt compatibility in memory only

**Recommendation:** make the diagnostic cost path non-writing for scripts by using load_script_readonly. This method already applies the same duration compatibility conversion in memory, so estimates need not lose legacy support. Preserve normal native migrations in production/formal loading paths.

**Side-effect control:** no project metadata update, new migration flag or eager migration before costing. Compare legacy/current outputs, Portuguese dialogue, duration and byte-level files. Do not promise zero writes across unrelated application startup or all artifact APIs. Combined implementation/validation unit with R10b, not a second independent fix.

### R10c: preview should not persist script adoption

**Recommendation:** use the native read-only reader specifically for preview=true input loading; keep the existing writing/transaction behavior for actual editing. Preserve the shared target/capability/episode checks and the existing builder/result semantics. Do not clone the editor or introduce another planner in Codex.

**Side-effect control:** legacy/current target validation should yield equivalent outcomes; preview produces no script/image writes or submissions. Real edits must still submit and commit through native paths. This recommendation concerns the observed script-migration seam, not an unverified guarantee that every dependency is globally side-effect-free.

### R10d: quotation should not migrate a script, including before refusal

**Recommendation:** add a narrowly scoped read-only-script loading option to the existing native storyboard planner/loader for the quote caller, preserving its current default for generation/Web callers. Use the same in-memory script and route validation for planning; do not duplicate planning logic or globally replace load_script.

**Side-effect control:** the mismatch case should return its native refusal without script changes; valid reference_video should remain rejected before reading. Valid storyboard quotes retain targets/skips/dependencies/pricing; actual generation still follows its normal compatibility and admission behavior. A quote is a snapshot, not a reservation or guarantee that later generation is admitted.

### R10e: retain native speech materialization and document its semantics

**Recommendation:** keep review_speech's native materialization. Clarify that apply_timing=false prevents applying new measured timing, but does not promise zero presentation/subtitle/manifest writes. An ASR-unavailable error can follow successful native materialization. Do not create a parallel materializer or a new strictly read-only speech API solely for this cleanup.

**Side-effect control:** preserve existing valid measured policies and source-bound invalidation. Neither an unavailable review nor instruction cleanup may reset already applied measured timing, change canonical speech or mark editorial approval. Reuse the successful/ASR-unavailable/content-stability controls and verify existing measured read/render behavior. No promise of no timestamps/filesystem activity from second-call hash stability.

## Dependency order and validation boundaries

1. Keep this as analysis until implementation is requested. Coordinate ownership of R12/configuration source with the other worktree before edits.
2. Implement instruction/package retirement as one coherent change set: W01/W02 plus obsolete imports/tests and active references; W03-W08 plus all affected mixed clauses/descriptions. Do not revert entire commits or reset product customizations. Avoid changing active production sessions mid-round or restarting the user's process as an implied part of cleanup.
3. Fix native contracts in small reviewable units: R07 permission boundary, R09 guidance, R10a+b cost read, R10c preview, R10d quote loader, R11 transaction, R12 route classification. R10e is initially contract documentation, not a forced pipeline rewrite. Units can share owning files; coordinate rather than producing conflicting parallel edits.
4. Match verification to actual changes: instruction/profile materialization and references; both MCP host schema/contract checks; legacy/current read parity and cancellation; upload interleavings/rollback; no-key/API/subscription environment/pricing. Add focused regression coverage for the reproduced defects rather than deleting their reproductions or relying on host-schema equality alone.
5. Preserve pt-BR text, approved durations, saved settings, histories, receipts, media, selected versions, prior timing, branding, subscription backend and native Gemini safeguards throughout. A shared toolset serves both hosts, so inspect both even though Codex stays external.

Existing evidence remains: 69 adapter tests, 13 R10/R11 reproductions, 53 broader cases and 3 R12 pre-spawn reproductions passed in their recorded runs. No tests were rerun for this documentation-only review. These establish the current cases, not future fix success or live audiovisual equivalence. Later implementation must record actual checks and unresolved failures; no paid test, fresh authentication, model benchmark, mass migration or production edit is implied.
