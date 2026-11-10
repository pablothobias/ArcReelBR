"""Declared Agent tools, with tool-name and migration-blocked sets derived from declarations."""

from __future__ import annotations

from server.agent_toolset.artifact_download import ARTIFACT_DOWNLOAD_TOOLS
from server.agent_toolset.asset_library import ASSET_LIBRARY_TOOLS
from server.agent_toolset.authoring_previews import AUTHORING_PREVIEW_TOOLS
from server.agent_toolset.content_read import CONTENT_READ_TOOLS
from server.agent_toolset.declaration import AgentToolDeclaration, Blocked, ToolDeclaration
from server.agent_toolset.edit_timelines import EDIT_TIMELINE_TOOLS
from server.agent_toolset.episode_management import EPISODE_MANAGEMENT_TOOLS
from server.agent_toolset.episode_planning import EPISODE_PLANNING_TOOLS, EPISODE_REPLAN_TOOLS
from server.agent_toolset.final_cuts import FINAL_CUT_TOOLS
from server.agent_toolset.generation_batches import GENERATION_BATCH_TOOLS
from server.agent_toolset.generation_diagnostics import GENERATION_DIAGNOSTICS_TOOLS
from server.agent_toolset.global_asset_library import GLOBAL_ASSET_LIBRARY_TOOLS
from server.agent_toolset.grid_storyboards import GRID_REVIEW_TOOLS, GRID_STORYBOARD_TOOLS
from server.agent_toolset.image_review import IMAGE_REVIEW_TOOLS
from server.agent_toolset.jianying_drafts import JIANYING_DRAFT_TOOLS
from server.agent_toolset.media_generation import MEDIA_GENERATION_TOOLS
from server.agent_toolset.media_ingest import MEDIA_INGEST_TOOLS
from server.agent_toolset.media_versions import MEDIA_VERSION_TOOLS
from server.agent_toolset.orientation import ORIENTATION_TOOLS
from server.agent_toolset.project_entry import PROJECT_ENTRY_TOOLS
from server.agent_toolset.project_trash import PROJECT_TRASH_TOOLS
from server.agent_toolset.repair_channel import REPAIR_CHANNEL_TOOLS
from server.agent_toolset.script_authoring import SCRIPT_AUTHORING_TOOLS
from server.agent_toolset.script_editing import SCRIPT_EDITING_TOOLS
from server.agent_toolset.speech_review import SPEECH_REVIEW_TOOLS
from server.agent_toolset.video_review import VIDEO_REVIEW_TOOLS
from server.agent_toolset.video_versions import VIDEO_VERSION_TOOLS
from server.agent_toolset.voice_references import VOICE_REFERENCE_TOOLS
from server.agent_toolset.workflow_access import WORKFLOW_ACCESS_TOOLS
from server.agent_toolset.workflow_completion import WORKFLOW_COMPLETION_TOOLS

AGENT_TOOLSET: tuple[AgentToolDeclaration, ...] = (
    *PROJECT_ENTRY_TOOLS,
    *WORKFLOW_ACCESS_TOOLS,
    *ORIENTATION_TOOLS,
    *GENERATION_BATCH_TOOLS,
    *GENERATION_DIAGNOSTICS_TOOLS,
    *ARTIFACT_DOWNLOAD_TOOLS,
    *CONTENT_READ_TOOLS,
    *MEDIA_GENERATION_TOOLS,
    *VOICE_REFERENCE_TOOLS,
    *MEDIA_INGEST_TOOLS,
    *GRID_STORYBOARD_TOOLS,
    *GRID_REVIEW_TOOLS,
    *MEDIA_VERSION_TOOLS,
    *IMAGE_REVIEW_TOOLS,
    *ASSET_LIBRARY_TOOLS,
    *GLOBAL_ASSET_LIBRARY_TOOLS,
    *VIDEO_VERSION_TOOLS,
    *VIDEO_REVIEW_TOOLS,
    *SPEECH_REVIEW_TOOLS,
    *EDIT_TIMELINE_TOOLS,
    *FINAL_CUT_TOOLS,
    *JIANYING_DRAFT_TOOLS,
    *SCRIPT_AUTHORING_TOOLS,
    *AUTHORING_PREVIEW_TOOLS,
    *REPAIR_CHANNEL_TOOLS,
    *SCRIPT_EDITING_TOOLS,
    *EPISODE_PLANNING_TOOLS,
    *EPISODE_MANAGEMENT_TOOLS,
    *EPISODE_REPLAN_TOOLS,
    *WORKFLOW_COMPLETION_TOOLS,
    *PROJECT_TRASH_TOOLS,
)

# Tool IDs are short names (SDK registration adds ``mcp__arcreel__``). Frontend display names are in ``frontend/src/i18n/{zh,en,vi}/dashboard.ts``
# under ``tool_name_<id>``; workflow-row summary formats are registered in ``frontend/src/components/copilot/chat/arcreel-tool-summaries.ts``.
# ``tests/unit/test_frontend_mcp_tool_i18n.py`` checks translations in every language and summary-format registration for each ID.
ARCREEL_MCP_TOOL_IDS: tuple[str, ...] = tuple(declaration.name for declaration in AGENT_TOOLSET)

# Tools rejected by the shared declaration entry after project migration failure, derived from each declaration’s policy.
MIGRATION_BLOCKED_TOOL_IDS: frozenset[str] = frozenset(
    declaration.name
    for declaration in AGENT_TOOLSET
    if isinstance(declaration, ToolDeclaration) and isinstance(declaration.migration, Blocked)
)

if len(set(ARCREEL_MCP_TOOL_IDS)) != len(ARCREEL_MCP_TOOL_IDS):
    raise RuntimeError("Duplicate declarations in the Agent toolset")

__all__ = ["AGENT_TOOLSET", "ARCREEL_MCP_TOOL_IDS", "MIGRATION_BLOCKED_TOOL_IDS"]
