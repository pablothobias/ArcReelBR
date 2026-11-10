"""Media version declarations: list and select the current version of images, grid composites and narration audio."""

from __future__ import annotations

from server.agent_toolset.declaration import BLOCKED, READ_CHECK, ToolDeclaration
from server.media_tools.media_versions import (
    ListMediaVersionsRequest,
    SelectMediaVersionRequest,
    list_media_versions,
    list_media_versions_summary,
    select_media_version,
    select_media_version_summary,
)

LIST_MEDIA_VERSIONS = ToolDeclaration(
    name="list_media_versions",
    description=(
        "List recorded versions of one asset sheet (character, scene, prop, product), character derivative, storyboard image, grid composite, or per-unit narration audio, with provenance and restorability. Read-only, free, triggers no generation. Returns current_version, artifact_path, artifact_status (native currency: current, stale, missing, ...), dependents with their status (unit video for a storyboard; storyboards using an asset), and versions (version, is_current, created_at, source such as generated/manual_upload/grid_split, provider, model, grid_id, original_filename, sha256, prompt preview, restorable, provenance_verified, presentation_available for narration audio). To look at images use inspect_images or inspect_grid; video versions belong to select_video_version; character voice samples have their own tools. Missing targets return resource_not_found."
    ),
    request_model=ListMediaVersionsRequest,
    migration=READ_CHECK,
    domain_key="list_media_versions",
    handler=list_media_versions,
    summary=list_media_versions_summary,
)

SELECT_MEDIA_VERSION = ToolDeclaration(
    name="select_media_version",
    description=(
        "Make a recorded version the current one for an asset sheet, character derivative, storyboard image, grid composite, or per-unit narration audio, using the same native restore as the Web version history: owner metadata, version pointer and Artifact Manifest claim change together; no charges, no regeneration, no re-upload. current is project-wide: storyboard-to-video, timeline preview, render and export read the selected media, and dependents generated from another version may become stale (reported in dependents/stale_dependents). Selecting a version without verified provenance (provenance_verified=false) drops the currency claim. grid_composite selection resets the split state (awaiting_split) and never splits or changes storyboard cells; split only after the user approves the restored composite. Ask the user before changing current. Refuses active generation tasks for the target (active_task_conflict, audio_restore_conflicts_with_active_task), grid writes for ad or non-grid projects, version_not_found (params.available_versions), version_conflict when expected_current_version differs, and request_invalid for narration versions lacking complete provenance. Returns previous_version, current_version, changed, artifact_status, dependents and stale_dependents."
    ),
    request_model=SelectMediaVersionRequest,
    migration=BLOCKED,
    domain_key="select_media_version",
    handler=select_media_version,
    summary=select_media_version_summary,
)

MEDIA_VERSION_TOOLS = (LIST_MEDIA_VERSIONS, SELECT_MEDIA_VERSION)

__all__ = ["LIST_MEDIA_VERSIONS", "MEDIA_VERSION_TOOLS", "SELECT_MEDIA_VERSION"]
