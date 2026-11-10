"""Host-neutral tools for the global ArcReel asset library (the Web ``/assets`` library), distinct from provider asset
libraries (``list_provider_library_assets``).

All operations reuse :mod:`server.services.asset_library.global_library`, shared with the Web routes: saving copies the
selected images, derivatives, reference audio and usable provider-asset links; applying commits finished images as
manual-upload versions in the target project with an explicit name-conflict policy. Nothing here generates media or
calls a provider. Results never expose storage paths: images and audio are reported as presence flags.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from pydantic.json_schema import SkipJsonSchema

from lib.i18n import DEFAULT_LOCALE
from lib.i18n import _ as translate_message
from lib.infra.api_errors import ApiError
from lib.project.asset_types import ProjectAssetNameConflictError, localize_asset_type
from lib.project.project_change_hints import project_change_source
from server.media_tools.context import tool_error
from server.services.asset_library.global_library import (
    CROSS_PROJECT_OVERWRITE,
    ApplyToProjectRequest,
    FromProjectRequest,
    GlobalLibraryError,
    LibraryContext,
    apply_library_assets,
    get_library_asset,
    global_library_error_text,
    list_library_assets,
    save_project_asset,
)
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolProblem, ToolRequest

LibraryAssetType = Literal["character", "scene", "prop"]


def _translate(key: str, **params: Any) -> str:
    return translate_message(key, DEFAULT_LOCALE, **params)


def _context(services: Services) -> LibraryContext:
    return LibraryContext(pm=services.projects, session_factory=services.sessions)


class ListGlobalLibraryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: LibraryAssetType | SkipJsonSchema[None] = Field(
        default=None, description="Filter by library type; omit for all types"
    )
    query: str | SkipJsonSchema[None] = Field(default=None, max_length=200, description="Search entry names")
    limit: Annotated[int, Field(ge=1, le=200)] = Field(default=50, description="Page size")
    offset: Annotated[int, Field(ge=0)] = Field(default=0, description="Page offset")


class GetGlobalLibraryAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_id: str = Field(min_length=1, description="Library entry id from list_global_library_assets")


class ObservedLibraryOwner(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    existing_source_project: str | None = Field(
        description="params.existing_source_project from the refusal (null when the entry has no source project)"
    )
    existing_updated_at: str | None = Field(description="params.existing_updated_at from the refusal")


class SaveToGlobalLibraryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_type: LibraryAssetType = Field(description="Project asset type to save; products are not supported")
    name: str = Field(min_length=1, description="Project asset name as registered in the project")
    library_name: str | SkipJsonSchema[None] = Field(
        default=None, description="Name to store under in the library; defaults to the project name"
    )
    overwrite: StrictBool = Field(
        default=False,
        description="Replace an existing same-type same-name library entry (its images, derivatives and audio). The library is shared by every project and the replaced content cannot be recovered: only with the user's explicit consent. Without it a conflict returns asset_already_exists with params.existing",
    )
    cross_project_overwrite: ObservedLibraryOwner | SkipJsonSchema[None] = Field(
        default=None,
        description="Consent to replace an entry saved from another project, bound to what the user saw: copy existing_source_project and existing_updated_at from the library_cross_project_overwrite_requires_confirmation refusal. If the entry changed since, the refusal is returned again with current values",
    )


class ApplyGlobalLibraryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_ids: list[Annotated[str, Field(min_length=1)]] = Field(
        min_length=1, max_length=100, description="Library entry ids to apply to this project"
    )
    conflict_policy: Literal["skip", "overwrite", "rename"] = Field(
        description=(
            "Required, explicit name-conflict policy. skip: leave existing project assets untouched; overwrite: replace the same-type "
            "same-name project asset, unrecoverably replacing its description, voice and reference audio; earlier sheets stay in version history (existing derivatives "
            "absent from the library entry are kept; a different-type or case-variant name refuses); rename: add as 'name (2)', 'name (3)'…"
        )
    )


def _public_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Library entry without storage paths: images/audio reported as presence flags."""
    return {
        "id": asset["id"],
        "type": asset["type"],
        "name": asset["name"],
        "description": asset["description"],
        "voice_style": asset["voice_style"],
        "has_image": bool(asset.get("image_path")),
        "has_reference_audio": bool(asset.get("audio_path")),
        "source_project": asset["source_project"],
        "updated_at": asset["updated_at"],
        "derivatives": [
            {"name": d["name"], "description": d["description"], "has_image": bool(d.get("image_path"))}
            for d in asset.get("derivatives") or ()
        ],
    }


def _problem(exc: Exception) -> ToolProblem | None:
    if isinstance(exc, GlobalLibraryError):
        params: dict[str, Any] = dict(exc.params)
        if exc.resource_type is not None:
            params["resource_type"] = exc.resource_type
        if exc.existing is not None:
            params["existing"] = _public_asset(exc.existing)
        if exc.key == CROSS_PROJECT_OVERWRITE:
            detail = (
                f"The global library entry '{params['name']}' was saved from project "
                f"'{params['existing_source_project']}'. The library is shared by every project and an overwrite cannot be "
                "undone; ask the user, then retry with cross_project_overwrite set to existing_source_project and "
                "existing_updated_at from this refusal."
            )
        else:
            detail = global_library_error_text(exc, _translate)
        return ToolProblem(exc.key, detail, params=params or None)
    if isinstance(exc, ProjectAssetNameConflictError):
        existing_type = exc.existing.asset_type
        return ToolProblem(
            "project_asset_name_conflict",
            _translate(
                "project_asset_name_conflict",
                name=exc.name,
                requested_type=localize_asset_type(exc.requested_asset_type or existing_type, _translate),
                existing_type=localize_asset_type(existing_type, _translate),
                existing_name=exc.existing.name,
            ),
            params={"name": exc.name, "existing_type": existing_type, "existing_name": exc.existing.name},
        )
    if isinstance(exc, ApiError):
        return ToolProblem(exc.key, _translate(exc.key, **(exc.params or {})), params=exc.params or None)
    return None


async def _run(operation: str, call: Any) -> ToolOutcome[Any]:
    try:
        return ToolOutcome(value=await call)
    except Exception as exc:
        problem = _problem(exc)
        return ToolOutcome(problem=problem) if problem is not None else tool_error(operation, exc)


async def list_global_library_assets(
    request: ToolRequest[ListGlobalLibraryRequest], _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value

    async def _list() -> dict[str, Any]:
        page = await list_library_assets(
            _context(services), type=req.type, q=req.query, limit=req.limit, offset=req.offset
        )
        return {**page, "items": [_public_asset(item) for item in page["items"]]}

    return await _run("list_global_library_assets", _list())


async def get_global_library_asset(
    request: ToolRequest[GetGlobalLibraryAssetRequest], _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    async def _get() -> dict[str, Any]:
        entry = await get_library_asset(_context(services), request.value.asset_id)
        return {"asset": _public_asset(entry["asset"])}

    return await _run("get_global_library_asset", _get())


async def save_asset_to_global_library(
    request: ToolRequest[SaveToGlobalLibraryRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value

    async def _save() -> dict[str, Any]:
        saved = await save_project_asset(
            _context(services),
            FromProjectRequest(
                project_name=scope.project_name,
                resource_type=req.resource_type,
                resource_id=req.name,
                override_name=req.library_name,
                overwrite=req.overwrite,
            ),
            overwrite_owner=scope.project_name,
            observed_owner=(
                None
                if req.cross_project_overwrite is None
                else (
                    req.cross_project_overwrite.existing_source_project,
                    req.cross_project_overwrite.existing_updated_at,
                )
            ),
        )
        return {"asset": _public_asset(saved["asset"])}

    return await _run("save_asset_to_global_library", _save())


async def apply_global_library_assets(
    request: ToolRequest[ApplyGlobalLibraryRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    req = request.value

    async def _apply() -> dict[str, Any]:
        with project_change_source("worker"):
            return await apply_library_assets(
                _context(services),
                ApplyToProjectRequest(
                    asset_ids=list(req.asset_ids),
                    target_project=scope.project_name,
                    conflict_policy=req.conflict_policy,
                ),
            )

    return await _run("apply_global_library_assets", _apply())


def apply_global_library_summary(value: dict[str, Any]) -> str:
    parts = [f"applied {len(value['succeeded'])}"]
    if value["skipped"]:
        parts.append(f"skipped {len(value['skipped'])}")
    if value["failed"]:
        parts.append(f"failed {len(value['failed'])}")
    return "Global library: " + ", ".join(parts)


__all__ = [
    "ApplyGlobalLibraryRequest",
    "GetGlobalLibraryAssetRequest",
    "ListGlobalLibraryRequest",
    "ObservedLibraryOwner",
    "SaveToGlobalLibraryRequest",
    "apply_global_library_assets",
    "apply_global_library_summary",
    "get_global_library_asset",
    "list_global_library_assets",
    "save_asset_to_global_library",
]
