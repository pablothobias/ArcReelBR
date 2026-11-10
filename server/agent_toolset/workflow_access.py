"""Native workflow access, shared by embedded and external MCP hosts."""

from server.agent_toolset.declaration import BLOCKED, Exempt, ToolDeclaration
from server.media_tools.assets import GenerateAssetsRequest
from server.media_tools.workflow_access import (
    ConfigureProjectRequest,
    EpisodeQuoteRequest,
    UploadReferenceRequest,
    UsageRequest,
    configure_project,
    get_effective_configuration,
    get_project_costs,
    get_project_usage,
    quote_assets,
    quote_storyboards,
    upload_reference,
)
from server.tool_runtime import NoArguments

WORKFLOW_ACCESS_TOOLS = (
    ToolDeclaration(
        name="upload_reference",
        description=(
            "Upload supplied character image/audio or style-reference bytes through the native upload validation. "
            "No server-local paths accepted. Character references require an existing named character. "
            "Image references guide image-to-image sheet generation; audio references require compatible voice binding/model/route. "
            "Uploading does not regenerate media. Style uploads require confirm_style_analysis and invoke the configured text model. "
            "Bytes arrive inline as content_base64 or, for larger files on remote MCP, as a complete staged_upload_id "
            "(purpose asset_image for images, reference_audio for audio; staging refusals such as upload_not_found or "
            "upload_purpose_mismatch are returned unchanged). The result includes sha256 of the installed file: images "
            "are normalized on install, so read them back with describe_media (kind character_reference_image or "
            "style_image) rather than comparing with the sent bytes."
        ),
        request_model=UploadReferenceRequest,
        migration=BLOCKED,
        domain_key="reference",
        handler=upload_reference,
    ),
    ToolDeclaration(
        name="configure_project",
        description=(
            "Update supported project Settings using the native validated transaction. Only supplied fields change. "
            "Grid toggles remain user-controlled in Web Settings. "
            "Use for explicit style, model, resolution, voice-binding and delivery requirements before generation. "
            "Modes remain creation-fixed. Do not change the user's requirements or treat a configuration change as regeneration."
        ),
        request_model=ConfigureProjectRequest,
        migration=BLOCKED,
        domain_key="project",
        handler=configure_project,
    ),
    ToolDeclaration(
        name="get_effective_configuration",
        description=(
            "Read effective project image/video/script models and verify the official local subscription login when selected. "
            "No secrets, provider generation or paid authentication test. Unverified login is not readiness. "
            "Use get_video_capabilities for the current route's actual audio/reference capabilities."
        ),
        request_model=NoArguments,
        migration=Exempt("Read-only configuration and authentication status; no artifact access."),
        domain_key="configuration",
        handler=get_effective_configuration,
    ),
    ToolDeclaration(
        name="quote_assets",
        description=(
            "Preview the same targets as generate_assets without submitting jobs. Supports explicit names for regeneration. "
            "Returns target IDs, dependencies, problems, currency, unpriced_count and estimate_basis. "
            "A full_context_output_upper_bound is conservative, not expected spend; null or partial cost is not free."
        ),
        request_model=GenerateAssetsRequest,
        migration=BLOCKED,
        domain_key="quote",
        handler=quote_assets,
    ),
    ToolDeclaration(
        name="quote_storyboards",
        description=(
            "Preview the episode's missing storyboard images using the Web batch planner; no provider calls or tasks. "
            "Skipped missing-reference units are not zero-cost generation. Preserve unpriced_count and estimate_basis."
        ),
        request_model=EpisodeQuoteRequest,
        migration=BLOCKED,
        domain_key="quote",
        handler=quote_storyboards,
    ),
    ToolDeclaration(
        name="get_project_costs",
        description=(
            "Read prospective per-shot costs and recorded actual project costs, using the application's cost estimator. "
            "Prospective estimates are not submission admission. "
            "Unknown prices are not zero; no generation is performed."
        ),
        request_model=NoArguments,
        migration=BLOCKED,
        domain_key="costs",
        handler=get_project_costs,
    ),
    ToolDeclaration(
        name="get_project_usage",
        description=(
            "Read paginated actual usage records for this project, including Agent and generation calls, without secrets. "
            "Keep unknown/subscription cost null distinct from zero. Follow next_cursor until null to reconcile the full ledger."
        ),
        request_model=UsageRequest,
        migration=Exempt("Read-only accounting records remain available during project migration failure."),
        domain_key="usage",
        handler=get_project_usage,
    ),
)
