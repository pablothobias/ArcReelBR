"""Global ArcReel asset-library declarations: list/read library entries, save an approved project character/scene/prop
into the library, and apply library entries to the current project.

This is the local ArcReel library shared across projects (the Web Assets library), not a provider asset library
(``list_provider_library_assets`` / ``select_provider_library_asset``). Products are not library types. No tool here
generates media or calls a provider."""

from __future__ import annotations

from server.agent_toolset.declaration import BLOCKED, ToolDeclaration, UnscopedToolDeclaration
from server.media_tools.global_asset_library import (
    ApplyGlobalLibraryRequest,
    GetGlobalLibraryAssetRequest,
    ListGlobalLibraryRequest,
    SaveToGlobalLibraryRequest,
    apply_global_library_assets,
    apply_global_library_summary,
    get_global_library_asset,
    list_global_library_assets,
    save_asset_to_global_library,
)

_ENTRY_FIELDS = (
    "Each entry: id, type (character/scene/prop), name, description, voice_style, has_image, has_reference_audio, "
    "source_project, updated_at, derivatives (name, description, has_image). Storage paths are never returned."
)

LIST_GLOBAL_LIBRARY_ASSETS = UnscopedToolDeclaration(
    name="list_global_library_assets",
    description=(
        "List entries of the global ArcReel asset library shared across projects (not a provider asset library), most recently updated first, "
        "with offset pagination: items, total (matches for the type/query) and counts per type (matches for the query). "
        "Read-only, no side effects. " + _ENTRY_FIELDS
    ),
    request_model=ListGlobalLibraryRequest,
    domain_key="global_library_assets",
    handler=list_global_library_assets,
)

GET_GLOBAL_LIBRARY_ASSET = UnscopedToolDeclaration(
    name="get_global_library_asset",
    description=(
        "Read one global ArcReel asset-library entry with its derivatives. Read-only. Returns asset_not_found for an unknown id. "
        + _ENTRY_FIELDS
    ),
    request_model=GetGlobalLibraryAssetRequest,
    domain_key="global_library_asset",
    handler=get_global_library_asset,
)

SAVE_ASSET_TO_GLOBAL_LIBRARY = ToolDeclaration(
    name="save_asset_to_global_library",
    description=(
        "Save an approved character, scene or prop of this project into the global ArcReel asset library: description, voice_style, "
        "the currently selected sheet image, character derivatives (name, description, sheet image) and the bound character reference "
        "audio are copied, with source_project provenance and usable provider-asset links of the selected image versions. Missing "
        "images are saved as entries without images; nothing is generated. Products are not supported. An existing same-type entry "
        "with the target name returns asset_already_exists with params.existing unless overwrite=true. The library is shared by every "
        "project and an overwrite cannot be undone, so overwrite only with the user's explicit consent; overwriting an entry saved "
        "from another project additionally refuses with library_cross_project_overwrite_requires_confirmation (params.existing_source_project, "
        "params.existing_updated_at); after the user confirms replacing that project's entry, retry with cross_project_overwrite holding "
        "exactly those two values. A changed entry is refused again with current values. "
        "Returns the saved entry. " + _ENTRY_FIELDS
    ),
    request_model=SaveToGlobalLibraryRequest,
    migration=BLOCKED,
    domain_key="global_library_asset",
    handler=save_asset_to_global_library,
)

APPLY_GLOBAL_LIBRARY_ASSETS = ToolDeclaration(
    name="apply_global_library_assets",
    description=(
        "Apply global ArcReel asset-library entries to this project as finished assets: writes description, voice_style, derivatives "
        "and character reference audio (setting the voice), and commits library images as the selected manually uploaded versions "
        "(local or object storage per global settings, materializing remote library images first) with provider-asset links copied. "
        "No generation, no provider call. The library is shared across projects; applying reads it and never changes it. "
        "conflict_policy is required and explicit (skip / overwrite / rename); "
        "overwrite replaces the project's same-name asset description, voice and reference audio, which cannot be undone (earlier sheet "
        "images stay in version history; ask the user first); a different-type or "
        "case-variant name under overwrite refuses with project_asset_name_conflict and nothing is applied. Returns succeeded "
        "(id, name as applied), skipped (id, name) and failed (id, reason: not_found / invalid_name / image_missing / audio_missing / "
        "project_name_conflict)."
    ),
    request_model=ApplyGlobalLibraryRequest,
    migration=BLOCKED,
    domain_key="global_library_apply",
    handler=apply_global_library_assets,
    summary=apply_global_library_summary,
)

GLOBAL_ASSET_LIBRARY_TOOLS = (
    LIST_GLOBAL_LIBRARY_ASSETS,
    GET_GLOBAL_LIBRARY_ASSET,
    SAVE_ASSET_TO_GLOBAL_LIBRARY,
    APPLY_GLOBAL_LIBRARY_ASSETS,
)

__all__ = [
    "APPLY_GLOBAL_LIBRARY_ASSETS",
    "GET_GLOBAL_LIBRARY_ASSET",
    "GLOBAL_ASSET_LIBRARY_TOOLS",
    "LIST_GLOBAL_LIBRARY_ASSETS",
    "SAVE_ASSET_TO_GLOBAL_LIBRARY",
]
