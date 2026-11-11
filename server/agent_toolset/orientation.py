"""Orientation declarations: production plan, video capabilities, and prompt preview, read before deciding the next action."""

from __future__ import annotations

from lib.workflow.workflow_plan import WorkflowPlanRequest
from server.agent_toolset.declaration import READ_CHECK, Exempt, ToolDeclaration
from server.tool_runtime import (
    NoArguments,
    PromptPreviewRequest,
    get_prompt_preview,
    get_video_capabilities,
    get_workflow_plan,
)

GET_WORKFLOW_PLAN = ToolDeclaration(
    name="get_workflow_plan",
    description=(
        "Read the project’s authoritative production plan: current content, admission for each AI action in status.operations, ordered steps, blocking reasons, data issues, active-task observations, video admission, and suggested next_action. Read it before every action: execute a user-named operation when operations marks it admitted, relay its reason when refused; when the user says continue, follow next_action, and let the user choose among parallel options when next_alternatives is nonempty. confirmed_request_durations applies only to this plan and is not persisted. Read-only, no side effects. If project-data upgrade failed, the plan contains only project_migration_failed and the next action points to repair."
    ),
    request_model=WorkflowPlanRequest,
    migration=READ_CHECK,
    domain_key="workflow_plan",
    handler=get_workflow_plan,
)

GET_VIDEO_CAPABILITIES = ToolDeclaration(
    name="get_video_capabilities",
    description=(
        "Query the current project video model’s capabilities (at model level: provider, model, supported durations, etc.) and project preferences, including duration_constraints whose axes follow the project generation mode. This is project-wide and requires no episode. Reference-video projects also include reference_unit_durations (tiers with and without images, endpoint_fixed flags and causes for each bucket; a problem when no-image tiers cannot be resolved). Read-only; no provider request. Returns the corresponding problem if the video model is unconfigured or capabilities cannot be resolved."
    ),
    request_model=NoArguments,
    migration=Exempt(
        "Read-only model capabilities and project preferences; no artifact-manifest access or write credentials. Must remain available for repair planning after migration failure."
    ),
    domain_key="video_capabilities",
    handler=get_video_capabilities,
)

GET_PROMPT_PREVIEW = ToolDeclaration(
    name="get_prompt_preview",
    description=(
        "Read the final prompt text that a script entry would send to the image / video model if generated now, routed by the entry's generation route. "
        "Storyboard entries (segment / scene / shot IDs) use the storyboard execution renderer; storyboard_image.references lists the images actually sent in 图N order with logical identity and content digest. "
        "Reference-video units (unit_id such as E1U1) use the same request projector and unit renderer as the Web unit preview and execution: video holds the prompt, storyboard_image is prompt_preview_not_applicable, "
        "and reference_video lists images in @Image N send order (type, name, base_name, is_derivative, sha256), audio in @Audio N order bound to base-character speakers (with target_image_index for per-image backends), "
        "unavailable_references, projection problems, provider/model and request duration. Markers @Image N / @Audio N are functional prompt syntax and are returned verbatim. "
        "If either side's prompt is pending, empty or blocked, that side contains a stable unavailable reason code instead of text. "
        "preview_basis is always current_configuration: this is not the payload of a historical task. Pass task_id of a submitted video task for this entry to also receive captured_submission, the prompt and ordered media digests frozen in that task's execution checkpoint "
        "(task_not_found / task_target_mismatch / captured_submission_unavailable when it cannot be read). "
        "Read-only: no provider request, charges, task submission or file changes. Returns project_migration_failed if project-data upgrade failed."
    ),
    request_model=PromptPreviewRequest,
    migration=READ_CHECK,
    domain_key="prompt_preview",
    handler=get_prompt_preview,
)

ORIENTATION_TOOLS = (GET_WORKFLOW_PLAN, GET_VIDEO_CAPABILITIES, GET_PROMPT_PREVIEW)

__all__ = [
    "GET_PROMPT_PREVIEW",
    "GET_VIDEO_CAPABILITIES",
    "GET_WORKFLOW_PLAN",
    "ORIENTATION_TOOLS",
]
