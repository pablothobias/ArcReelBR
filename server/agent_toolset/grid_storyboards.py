"""Storyboard-grid declarations: generate composite grids, then split with user agreement.

``generate_grid`` is a generation long task. A ``list_only`` preview is not a generation result and returns immediately under the tool name via grid-specific hooks; other values have the normal generation-tool shape. ``split_grids`` is an ordinary write tool."""

from __future__ import annotations

from server.agent_toolset.declaration import BLOCKED, READ_CHECK, ToolDeclaration
from server.agent_toolset.media_generation import generation_tool
from server.media_tools.grid import (
    GenerateGridRequest,
    SplitGridsRequest,
    generate_grid,
    grid_is_error,
    grid_structured,
    grid_summary,
    split_grids,
)
from server.media_tools.grid_review import (
    MAX_COMPOSITE_EDGE,
    InspectGridRequest,
    ListGridsRequest,
    ReplaceGridCompositeRequest,
    inspect_grid,
    inspect_grid_images,
    inspect_grid_projection,
    inspect_grid_summary,
    list_grids,
    list_grids_summary,
    replace_grid_composite,
    replace_grid_composite_summary,
)

GENERATE_GRID = generation_tool(
    name="generate_grid",
    description=(
        "Generate composite storyboard grids for storyboard projects with grid assembly enabled (generation_mode=storyboard and grid_storyboard=true; paid generation; groups follow segment_break and split across images when above the per-grid panel limit). Produces only composite images and writes no storyboard images: successful shots report their grid composite (artifact_path grids/<grid_id>.png), with status composite ready, not split. Unsplit grid_id values also appear in terminal grid_ids_awaiting_split. Batch handles and terminal batch queries lack that field: existing ready unsplit grids appear in skipped items’ artifact_path; newly generated ones appear in successful shots’ artifact_path. Ask the user to review composites in the grid panel, then call split_grids only after explicit agreement. list_only=true previews the plan without queueing, under the generate_grid key. Without scene_ids, stale but usable old images are reused and ready unsplit composites are not regenerated; in-flight tasks for the same group are reused without duplicate charges. Admission is all-or-nothing: any blocked shot (missing references, pending prompt, partial overlap with an in-flight grid, etc.) prevents tasks for the entire batch, with generation_batch_admission_withheld for otherwise healthy shots. Existing in-flight grids finish normally; their shots carry generation_active_task_conflict (action=wait_for_task). Terminal generation_result gives requested / succeeded / failed / blocked outcomes by shot ID."
    ),
    request_model=GenerateGridRequest,
    handler=generate_grid,
    summary=grid_summary,
    projection=grid_structured,
    is_error=grid_is_error,
)

SPLIT_GRIDS = ToolDeclaration(
    name="split_grids",
    description=(
        "Split one or more composite grids into storyboard images for all covered shots; old storyboard images remain in version history for rollback. Call only with explicit user agreement: after generate_grid, show the user the composite (inspect_grid, or the grid panel), let them regenerate, replace (replace_grid_composite) or roll back (select_media_version kind=grid_composite) if desired, then pass grid_id values after confirmation. Do not call automatically after generation, upload or restore. Pass reviewed_composites with each grid's inspect_grid split_guard (sha256, version) so only the composite the user saw is split; a changed composite is skipped with status composite_changed. Obtain grid_id from generate_grid grid_ids_awaiting_split, successful-shot artifact_path (grids/<grid_id>.png), list_grids, or list_only preview. Returns per-grid results: split grids list written shots; generating grids, grids without composites, changed composites, or absent grids are skipped with reasons. If none are split, returns a problem with per-grid reasons in params.results."
    ),
    request_model=SplitGridsRequest,
    migration=BLOCKED,
    domain_key="split_grids",
    handler=split_grids,
)

LIST_GRIDS = ToolDeclaration(
    name="list_grids",
    description=(
        "List the project's composite grid records with the grid capability. Read-only, free, triggers no generation. Returns capability (large_grid_allowed, max_cell_count from the project's image tier), writable/write_block (ad_grid_not_supported or grid_storyboard_not_enabled when grid writes are refused; existing records stay readable), and per grid: grid_id, episode, script_file, state (generating, failed, no_composite, awaiting_split, split), scene_ids, rows, cols, grid_size, split_at, current composite version, and in_flight (an active generation task owns it). Use inspect_grid to look at one composite before asking the user to approve a split."
    ),
    request_model=ListGridsRequest,
    migration=READ_CHECK,
    domain_key="list_grids",
    handler=list_grids,
    summary=list_grids_summary,
)

INSPECT_GRID = ToolDeclaration(
    name="inspect_grid",
    description=(
        f"Inspect one composite grid before splitting: attaches the composite as an image content block (JPEG, longest edge at most {MAX_COMPOSITE_EDGE} px) and returns the record: state, layout (rows, cols, grid_size, cell_count, video_aspect_ratio), cells (index, row, col, frame_type, scene_id each cell writes, split_image_path after a split), split_at, in_flight, and composite (version, current_version, available_versions, is_current, source, sha256 and size of the original composite bytes, width, height, status ok/missing/unreadable). Read-only, free, triggers no generation and never splits. version inspects a historical composite for comparison. For the current composite, split_guard {{grid_id, sha256, version}} is returned: show the image to the user and, only after explicit approval, pass it to split_grids reviewed_composites. Missing grids return grid_not_found; absent versions return version_not_found with params.available_versions."
    ),
    request_model=InspectGridRequest,
    migration=READ_CHECK,
    domain_key="inspect_grid",
    handler=inspect_grid,
    summary=inspect_grid_summary,
    projection=inspect_grid_projection,
    images=inspect_grid_images,
)

REPLACE_GRID_COMPOSITE = ToolDeclaration(
    name="replace_grid_composite",
    description=(
        "Replace a grid's composite with a user-supplied, user-approved image (filename with an image extension plus exactly one of content_base64 or staged_upload_id from begin_media_upload for larger files), through the same native transaction as the Web upload: size/image validation, PNG/EXIF normalization without resizing (rows x cols layout remains the user's responsibility), a new composite version (previous versions stay restorable), and the record reset to awaiting_split. Never splits and never changes storyboard cells; previous_split_at reports a split that the new composite no longer matches. No charges or generation. Refuses ad projects or projects without grid storyboards (ad_grid_not_supported, grid_storyboard_not_enabled), grids with an active generation task (grid_generation_in_progress), invalid images (invalid_image_file, image_pixels_too_large), version_conflict when expected_current_version differs or another commit changed the composite meanwhile, and staging refusals (upload_not_found, upload_expired, upload_incomplete, upload_digest_mismatch). Returns version, sha256, and split_guard; show the composite to the user (inspect_grid) and split only after explicit approval."
    ),
    request_model=ReplaceGridCompositeRequest,
    migration=BLOCKED,
    domain_key="replace_grid_composite",
    handler=replace_grid_composite,
    summary=replace_grid_composite_summary,
)

GRID_STORYBOARD_TOOLS = (GENERATE_GRID, SPLIT_GRIDS)
#: Composite review tools (MCP-014); registered separately so existing GRID_STORYBOARD_TOOLS consumers stay unchanged.
GRID_REVIEW_TOOLS = (LIST_GRIDS, INSPECT_GRID, REPLACE_GRID_COMPOSITE)

__all__ = [
    "GENERATE_GRID",
    "GRID_REVIEW_TOOLS",
    "GRID_STORYBOARD_TOOLS",
    "INSPECT_GRID",
    "LIST_GRIDS",
    "REPLACE_GRID_COMPOSITE",
    "SPLIT_GRIDS",
]
