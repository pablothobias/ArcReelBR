"""Authoring and preview declarations: start an episode from a blank formal script, preview asset/derivative sheet
prompts before generation, and optionally generate the project overview with the text model."""

from __future__ import annotations

from server.agent_toolset.declaration import BLOCKED, READ_CHECK, TEXT_OUTPUT_TRUNCATED_NOTE, ToolDeclaration
from server.media_tools.authoring_previews import (
    AssetPromptPreviewRequest,
    GenerateProjectOverviewRequest,
    StartBlankScriptRequest,
    generate_project_overview,
    generate_project_overview_summary,
    get_asset_prompt_preview,
    start_blank_script,
    start_blank_script_summary,
)

START_BLANK_SCRIPT = ToolDeclaration(
    name="start_blank_script",
    description=(
        "Start an episode from blank: create an empty formal script for episode_id (the internal episode ID from the production plan, not a position) so the creator can write entries manually, the same transaction as the Web “Start from blank” action. "
        "Use it when get_workflow_plan offers next_action or next_alternatives of type start_blank_script and the user chose manual authoring. No model is called and no generation task is submitted. "
        "Side effect: unconfirmed planning for that episode is discarded — the unconfirmed script_plan and creator-owned script-plan / prompt-authoring drafts move to project trash (recoverable with restore_trash_record), and a previous script_plan confirmation is cleared, so any later plan needs fresh confirmation. "
        "Refusals leave everything unchanged: formal_script_exists when the episode already has a formal script (including a repeated call), episode_not_found for an unknown episode_id, draft_agent_owned while the Agent is editing that episode's draft. "
        "Success returns episode_id, script_file, and what was discarded (discarded_script_plan, discarded_drafts, cleared_script_plan_confirmation). Then add entries with the script editing tools."
    ),
    request_model=StartBlankScriptRequest,
    migration=BLOCKED,
    domain_key="start_blank_script",
    handler=start_blank_script,
    summary=start_blank_script_summary,
)

GET_ASSET_PROMPT_PREVIEW = ToolDeclaration(
    name="get_asset_prompt_preview",
    description=(
        "Preview the final prompt a character / scene / prop / product sheet, or a character derivative sheet, would send to the image model if generated now, using the executor's generation input (the same as the Web asset prompt preview). "
        "Optional description renders an unsaved draft description instead of the stored one; it is never saved. "
        "Returns text (or a stable unavailable code with unavailable_params when generation would be refused, e.g. empty description or unavailable base sheet for a derivative), style and style_description used (derivatives carry style through the base sheet reference), "
        "references in assembly order with sent flags, logical identity, artifact_path and content_digest from the shared projection, limits (max_reference_images, image_model, sent_reference_count) and truncation warnings. "
        "preview_basis is current_configuration. It does not prove the generated image will match the description. Read-only: no provider request, charge, task or file change. Returns asset_not_found for unregistered names and project_migration_failed if project-data upgrade failed."
    ),
    request_model=AssetPromptPreviewRequest,
    migration=READ_CHECK,
    domain_key="asset_prompt_preview",
    handler=get_asset_prompt_preview,
)

GENERATE_PROJECT_OVERVIEW = ToolDeclaration(
    name="generate_project_overview",
    description=(
        "Optional and paid: generate the project overview (synopsis, genre, theme, world_setting) from the project's text sources with the configured text model, the same operation as the Web “generate overview” action, and save it. "
        "It is never required: an approved script does not need it, and patch_project(overview=...) edits the overview manually without any model call. "
        "Requires confirm_text_model_call=true after the user authorizes the model call; otherwise returns confirmation_required with params.sources (files, characters used, truncation) and calls nothing. "
        "Success returns the native overview for review, previous_overview, source_language before/after, the sources sent, and stale_impacts: changed fields and the script inputs whose recorded basis they feed (reported stale by get_workflow_plan; nothing is regenerated). "
        "Problems: source_empty, source_decode_failed, text_provider_not_configured, overview_ai_response_invalid, model-catalog problems. "
        + TEXT_OUTPUT_TRUNCATED_NOTE
    ),
    request_model=GenerateProjectOverviewRequest,
    migration=BLOCKED,
    domain_key="project_overview",
    handler=generate_project_overview,
    summary=generate_project_overview_summary,
)

AUTHORING_PREVIEW_TOOLS = (START_BLANK_SCRIPT, GET_ASSET_PROMPT_PREVIEW, GENERATE_PROJECT_OVERVIEW)

__all__ = [
    "AUTHORING_PREVIEW_TOOLS",
    "GENERATE_PROJECT_OVERVIEW",
    "GET_ASSET_PROMPT_PREVIEW",
    "START_BLANK_SCRIPT",
]
