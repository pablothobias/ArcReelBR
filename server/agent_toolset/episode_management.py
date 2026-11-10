"""Episode-management declarations: read the episode layout, create an empty episode, reorder or delete episodes,
edit whole-source episode boundaries manually, and reorder registered whole-source files.

None of these tools calls a model. Destructive changes follow the native two-step protocol: the first call returns
``status=confirmation_required`` with server-written ``impact.text`` and writes nothing; show that text to the user and
resubmit with the returned token only after explicit consent."""

from __future__ import annotations

from server.agent_toolset.declaration import BLOCKED, READ_CHECK, ToolDeclaration
from server.media_tools.episode_management import (
    CreateEpisodeRequest,
    DeleteEpisodeRequest,
    EditEpisodeBoundariesRequest,
    EpisodeLayoutRequest,
    MoveEpisodeRequest,
    MoveSourceFileRequest,
    create_empty_episode,
    delete_episode_tool,
    edit_episode_boundaries,
    get_episode_layout,
    move_episode_tool,
    move_source_file,
)

_IDS_NOTE = (
    " Episode IDs are internal identifiers allocated above the project's historical maximum; they are not playback order. "
    "Refer to episodes by title and playback position when talking to the user."
)

GET_EPISODE_LAYOUT = ToolDeclaration(
    name="get_episode_layout",
    description=(
        "Read the series episode layout, the same projection as the Web Episodes view. Read-only, no model call. Returns: files "
        "(registered whole-source files in order, each with normalized length, reading units, source_kind for drama, changed_outside, "
        "and segments: episode or unsplit spans with start/end offsets in normalized source-text coordinates, gap=true for unsplit text "
        "between extracted episodes); episodes in playback order (episode ID, position, title, hook, origin whole_source/own/none, "
        "placed, start/end file, reading units, spoken_seconds, first/last sentence); unregistered source/ files; replan (pending replan "
        "candidate summary or null); replan_generating; external_changes (files edited outside ArcReel with the impact of accepting them). "
        "Use segment offsets for edit_episode_boundaries positions." + _IDS_NOTE
    ),
    request_model=EpisodeLayoutRequest,
    migration=READ_CHECK,
    domain_key="episode_layout",
    handler=get_episode_layout,
)

CREATE_EPISODE = ToolDeclaration(
    name="create_episode",
    description=(
        "Create an empty episode (no source text) with optional title and hook, inserted after after_episode_id in playback order "
        "or appended at the end. Allocates a new episode ID and returns episode_id and position. No model call. Ad / short-film "
        "projects have exactly one episode and refuse (episode_manage_ad_episode_locked). To create an episode with its own source "
        "text use upload_source(role=episode) instead; do not create an empty episode and then reupload." + _IDS_NOTE
    ),
    request_model=CreateEpisodeRequest,
    migration=BLOCKED,
    domain_key="episode",
    handler=create_empty_episode,
)

MOVE_EPISODE = ToolDeclaration(
    name="move_episode",
    description=(
        "Reorder playback: move episode_id right after after_episode_id (null moves it to the beginning). Own-source and empty "
        "episodes can move anywhere, including between extracted episodes; extracted episodes always keep whole-source order, and "
        "moves that would swap them refuse with episode_manage_cut_order_locked. Only playback order changes: IDs, source ranges, "
        "scripts and media are untouched. No model call. Returns the new position and playback_order (episode IDs)."
        + _IDS_NOTE
    ),
    request_model=MoveEpisodeRequest,
    migration=BLOCKED,
    domain_key="episode_move",
    handler=move_episode_tool,
)

DELETE_EPISODE = ToolDeclaration(
    name="delete_episode",
    description=(
        "Move one episode (ledger entry, source, scripts, drafts, media, grids, versions) into project trash, recoverable for 30 days "
        "through restore_trash_record. Two steps: call without revision to receive status=confirmation_required with impact.text "
        "(the server-written loss list) and impact.revision; show impact.text to the user and only after explicit consent call again "
        "with that revision. If anything changed in between, a new confirmation is returned instead of deleting. A confirmed call "
        "refuses with episode_manage_tasks_active while the episode has queued/running generation tasks. Ad / short-film projects "
        "refuse. Never delete to simulate a reorder or boundary edit." + _IDS_NOTE
    ),
    request_model=DeleteEpisodeRequest,
    migration=BLOCKED,
    domain_key="episode_delete",
    handler=delete_episode_tool,
)

EDIT_EPISODE_BOUNDARIES = ToolDeclaration(
    name="edit_episode_boundaries",
    description=(
        "Manually edit whole-source episode boundaries without a model call (the Web Episodes view manual split): cut, split, "
        "move_boundary, merge_next, clear_after. Positions are file + offset in normalized source-text coordinates from "
        "get_episode_layout. Applies only to extracted (whole-source) episodes: own-source and empty episodes are never re-cut, a "
        "range may cross files in whole-source order but must not newly cross source-kind boundaries, and files changed outside "
        "ArcReel refuse until accepted. split keeps the ID on the first part and allocates a new ID for the second; move_boundary and "
        "merge_next keep the first episode's ID. Episodes whose range changes and that already have outputs become stale; replaced "
        "episodes with outputs become source-less and move to the end of playback order (outputs kept); those without outputs are "
        "removed. Two steps: dry_run=true (or any call needing confirmation) returns status=confirmation_required with impact "
        "(restaled, retired, removed, merged_units) and server-written impact.text; show it to the user, then resubmit with "
        "confirm_episodes = restaled + retired IDs (and confirm_merged_units for merge_next). If the locked recheck finds a different "
        "impact, confirmation is requested again. A confirmed change refuses with manual_split_tasks_active while a retired or removed "
        "episode has queued/running tasks. dry_run writes nothing. This is not patch_episode_script.split (which splits a shot/unit "
        "inside a script); never use reset_episode_planning or reupload as a substitute for a boundary edit."
    ),
    request_model=EditEpisodeBoundariesRequest,
    migration=BLOCKED,
    domain_key="episode_boundaries",
    handler=edit_episode_boundaries,
)

MOVE_SOURCE_FILE = ToolDeclaration(
    name="move_source_file",
    description=(
        "Move a registered whole-source file one position up or down in the whole-source file order; its extracted episodes move "
        "with it as playback blocks without being marked stale, and ranges spanning into a neighbour keep only their still-connected "
        "portion. No model call. When no episode is affected it applies directly (status=applied); otherwise it returns "
        "status=confirmation_required with impact.text and revision: show the text to the user and resubmit with revision after "
        "consent. Refuses with source_file_change_move_out_of_range at either end, source_file_change_tasks_active while a retired "
        "or removed episode has queued/running tasks, and while the file was changed outside ArcReel."
    ),
    request_model=MoveSourceFileRequest,
    migration=BLOCKED,
    domain_key="source_file_move",
    handler=move_source_file,
)

EPISODE_MANAGEMENT_TOOLS = (
    GET_EPISODE_LAYOUT,
    CREATE_EPISODE,
    MOVE_EPISODE,
    DELETE_EPISODE,
    EDIT_EPISODE_BOUNDARIES,
    MOVE_SOURCE_FILE,
)

__all__ = [
    "CREATE_EPISODE",
    "DELETE_EPISODE",
    "EDIT_EPISODE_BOUNDARIES",
    "EPISODE_MANAGEMENT_TOOLS",
    "GET_EPISODE_LAYOUT",
    "MOVE_EPISODE",
    "MOVE_SOURCE_FILE",
]
