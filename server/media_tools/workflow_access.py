"""MCP access to existing configuration, admission and cost services.

No production sequencing lives here: the native workflow remains the caller.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal, Self

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from lib.db.repositories.usage_repo import UsageRepository
from lib.i18n import _
from lib.infra.api_errors import ApiError
from lib.infra.content_digest import sha256_file
from server.media_tools.assets import GenerateAssetsRequest
from server.routers.projects import ProjectSettingsRequest, UpdateProjectRequest, update_project_settings
from server.services.admission.asset_sheet_batch import AssetSheetScope, load_asset_sheet_batch_plan
from server.services.admission.cost_estimation import CostEstimationService, estimate_image_batch_cost
from server.services.admission.storyboard_batch import load_storyboard_image_batch_plan
from server.services.project.model_settings_validation import (
    MODEL_SETTING_VALUE_UNSUPPORTED,
    find_unsupported_model_setting,
)
from server.services.tasks.formal_image_commit import get_aspect_ratio
from server.tool_runtime import (
    CallerContext,
    NoArguments,
    ProjectScope,
    Services,
    ToolOutcome,
    ToolProblem,
    ToolRequest,
)


class ConfigureProjectRequest(ProjectSettingsRequest):
    """Automated settings updates exclude user-only controls and reject unknown fields."""

    model_config = ConfigDict(extra="forbid")


class EpisodeQuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    episode_id: int = Field(ge=1, description="Episode ID whose missing storyboard images should be quoted")


async def configure_project(
    request: ToolRequest[ConfigureProjectRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    try:
        validated = ConfigureProjectRequest.model_validate(request.value.model_dump(exclude_unset=True))
        if "model_settings" in validated.model_fields_set and (
            unsupported := await find_unsupported_model_setting(
                validated.model_settings,
                services.capabilities,
                stored=(await asyncio.to_thread(services.projects.load_project, scope.project_name)).get(
                    "model_settings"
                ),
            )
        ):
            return ToolOutcome(
                problem=ToolProblem(
                    MODEL_SETTING_VALUE_UNSUPPORTED,
                    unsupported.detail(),
                    action="fix_input",
                    params=unsupported.params(),
                )
            )
        settings = UpdateProjectRequest.model_validate(validated.model_dump(exclude_unset=True))
        value = await update_project_settings(
            scope.project_name, settings, _, manager=services.projects, source="worker"
        )
        return ToolOutcome(value=value)
    except (HTTPException, ApiError, ValueError) as exc:
        return ToolOutcome(problem=ToolProblem("invalid_request", str(getattr(exc, "detail", exc))))


async def quote_assets(
    request: ToolRequest[GenerateAssetsRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    try:
        v = request.value
        project, plan = await load_asset_sheet_batch_plan(
            services.projects,
            services.queue,
            project_name=scope.project_name,
            scope=AssetSheetScope(
                asset_type=v.type, episode_id=v.episode_id, names=tuple(v.names) if v.names is not None else None
            ),
            user_id=caller.user_id,
        )
        ids = plan.new_task_ids
        quote = await estimate_image_batch_cost(
            project,
            ["i2i" if plan.units[i].image_to_image else "t2i" for i in ids],
            aspect_ratio=get_aspect_ratio(project, "characters"),
            resolver=services.capabilities,
            session_factory=services.sessions,
        )
        return ToolOutcome(
            value={
                "targets": [{"unit_id": i, "depends_on": plan.dependencies.get(i)} for i in ids],
                "generating": sorted(plan.generating),
                "problems": [
                    {"unit_id": i.unit_id, "problem": i.problem.model_dump(mode="json") if i.problem else None}
                    for i in plan.preflight.items
                ],
                **quote.to_payload(),
            }
        )
    except (LookupError, ValueError, FileNotFoundError) as exc:
        return ToolOutcome(problem=ToolProblem("quote_unavailable", str(exc)))


async def quote_storyboards(
    request: ToolRequest[EpisodeQuoteRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    try:
        loaded, plan = await load_storyboard_image_batch_plan(
            services.projects,
            services.queue,
            project_name=scope.project_name,
            episode_id=request.value.episode_id,
            user_id=caller.user_id,
            persist_legacy_migrations=False,
        )
        ids = plan.new_task_ids
        quote = await estimate_image_batch_cost(
            loaded.project,
            [plan.lanes[i] for i in ids],
            aspect_ratio=get_aspect_ratio(loaded.project, "storyboards"),
            resolver=services.capabilities,
            session_factory=services.sessions,
        )
        return ToolOutcome(
            value={
                "targets": [{"unit_id": i} for i in ids],
                "skipped": [{"unit_id": i.unit_id, "reason": i.reason.value} for i in plan.skips],
                **quote.to_payload(),
            }
        )
    except (LookupError, ValueError, FileNotFoundError) as exc:
        return ToolOutcome(problem=ToolProblem("quote_unavailable", str(exc)))


async def get_project_costs(
    request: ToolRequest[NoArguments], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    def read():
        project = services.projects.load_project(scope.project_name)
        scripts = {}
        for episode in project.get("episodes", []):
            filename = episode.get("script_file")
            if filename:
                try:
                    scripts[filename] = services.projects.load_script_readonly(scope.project_name, filename)
                except FileNotFoundError:
                    continue
        return project, scripts, services.projects.get_project_path(scope.project_name)

    project, scripts, path = await asyncio.to_thread(read)
    value = await CostEstimationService(services.capabilities, services.sessions, project_path=path).compute(
        project, scripts, project_name=scope.project_name
    )
    return ToolOutcome(value=value)


class UsageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    limit: int = Field(default=50, ge=1, le=200, description="Maximum usage records per page")
    cursor: str | None = Field(default=None, description="Opaque next_cursor from the previous usage page")


async def get_project_usage(
    request: ToolRequest[UsageRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    from lib.db.repositories.usage_repo import UsageCursor, UsageCursorError, UsageFilters

    try:
        cursor = UsageCursor.decode(request.value.cursor) if request.value.cursor else None
    except UsageCursorError:
        return ToolOutcome(problem=ToolProblem("invalid_request", "Invalid usage cursor"))
    async with services.sessions() as session:
        page = await UsageRepository(session).list_records(
            filters=UsageFilters(project_name=scope.project_name), limit=request.value.limit, cursor=cursor
        )
    # Provider diagnostics can contain request details; the financial reader exposes only accounting fields.
    fields = {
        "id",
        "task_id",
        "task_type",
        "media_type",
        "provider",
        "model",
        "status",
        "segment_id",
        "started_at",
        "finished_at",
        "cost_amount",
        "currency",
        "unpriced_reason",
        "session_id",
    }
    page["items"] = [{k: v for k, v in row.items() if k in fields} for row in page["items"]]
    return ToolOutcome(value=page)


async def get_effective_configuration(
    request: ToolRequest[NoArguments], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    import sys
    from importlib.resources import files

    from lib.backends.text_backends.base import TextTaskType
    from lib.backends.text_backends.claude_subscription import (
        SubscriptionAuthenticationError,
        verify_local_subscription,
    )
    from lib.speech.character_voice import character_voice_binding

    project = await asyncio.to_thread(services.projects.load_project, scope.project_name)
    result: dict[str, Any] = {"models": {}, "problems": {}, "character_voice_binding": character_voice_binding(project)}
    for lane in ("t2i", "i2i", "i2v", "r2v"):
        try:
            if lane == "t2i" or lane == "i2i":
                model = await services.capabilities.resolve_image_backend(project, None, generation_type=lane)
            else:
                model = await services.capabilities.resolve_video_backend(project, None, generation_type=lane)
            result["models"][lane] = model.pair_key
        except ValueError as exc:
            result["problems"][lane] = type(exc).__name__
    try:
        provider, model = await services.capabilities.text_backend_for_task(TextTaskType.SCRIPT, scope.project_name)
        result["models"]["script"] = f"{provider}/{model}"
        if provider == "claude-subscription":
            cli = await asyncio.to_thread(
                lambda: str(
                    files("claude_agent_sdk").joinpath(
                        "_bundled", "claude.exe" if sys.platform == "win32" else "claude"
                    )
                )
            )
            try:
                async with asyncio.timeout(15):
                    project_path = await asyncio.to_thread(services.projects.get_project_path, scope.project_name)
                    await verify_local_subscription(cli, str(project_path))
                result["subscription_login"] = "verified"
            except (SubscriptionAuthenticationError, OSError, TimeoutError):
                result["subscription_login"] = "unverified"
        else:
            result["subscription_login"] = "not_selected"
    except ValueError as exc:
        result["problems"]["script"] = type(exc).__name__
    return ToolOutcome(value=result)


class UploadReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["character_image", "character_audio", "style_image"] = Field(description="Reference type to upload")
    name: str | None = Field(default=None, description="Existing character name; required for character references")
    filename: str = Field(
        min_length=1, max_length=255, description="Original filename with a supported reference extension"
    )
    content_base64: str | None = Field(
        default=None,
        min_length=1,
        max_length=20 * 1024 * 1024,
        description=(
            "Base64 file bytes supplied by the client, never a server filesystem path; give exactly one of "
            "content_base64 or staged_upload_id"
        ),
    )
    staged_upload_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description=(
            "Complete staged upload from begin_media_upload/append_media_upload_chunk (remote MCP), staged with "
            "purpose asset_image for image references or reference_audio for character audio; give exactly one of "
            "content_base64 or staged_upload_id. The staging is discarded after a successful install"
        ),
    )
    confirm_style_analysis: bool = Field(
        default=False, description="Style uploads invoke the configured text model; explicit authorization is required"
    )

    @model_validator(mode="after")
    def _exactly_one_source(self) -> Self:
        if (self.content_base64 is None) == (self.staged_upload_id is None):
            raise ValueError("give exactly one of content_base64 or staged_upload_id")
        return self


#: Staging purposes each reference kind installs; the staging's size ceiling matches the native install limit.
_REFERENCE_STAGING_PURPOSES: dict[str, tuple[str, ...]] = {
    "character_image": ("asset_image",),
    "style_image": ("asset_image",),
    "character_audio": ("reference_audio",),
}


def _installed_digest(project_dir: Path, relative: object) -> str | None:
    """sha256 of the installed (normalized) bytes at a project-relative pointer, or ``None`` when unreadable."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        return None
    parts = relative.split("/")
    if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        return None
    path = project_dir.joinpath(*parts)
    if path.is_symlink() or not path.is_file():
        return None
    return sha256_file(path)


async def upload_reference(
    request: ToolRequest[UploadReferenceRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    """Install one reference through the native upload transaction; the result adds ``sha256`` of the installed bytes.

    Image references are normalized on install, so ``sha256`` names the stored file (readable back through
    ``describe_media``), not necessarily the bytes the client sent."""
    import base64
    import binascii
    from io import BytesIO

    from fastapi import UploadFile

    from server.routers.files import upload_project_file, upload_project_style_image
    from server.services.media_transport import MediaTransportError, discard_staged_upload, resolve_staged_upload

    value = request.value
    if "/" in value.filename or "\\" in value.filename or value.filename in {".", ".."}:
        return ToolOutcome(problem=ToolProblem("invalid_request", "filename must be a plain filename"))
    if value.kind != "style_image" and not value.name:
        return ToolOutcome(problem=ToolProblem("invalid_request", "A character name is required"))
    if value.kind == "style_image" and not value.confirm_style_analysis:
        return ToolOutcome(
            problem=ToolProblem("confirmation_required", "Style analysis invokes the configured text model")
        )
    staged = None
    if value.staged_upload_id is not None:
        try:
            staged = await resolve_staged_upload(
                services.projects,
                scope.project_name,
                value.staged_upload_id,
                purposes=_REFERENCE_STAGING_PURPOSES[value.kind],
            )
        except MediaTransportError as exc:
            return ToolOutcome(problem=ToolProblem(exc.code, exc.detail, params=exc.params or None))
        file = UploadFile(file=staged.stream, filename=value.filename, size=staged.size_bytes)
    else:
        try:
            content = await asyncio.to_thread(base64.b64decode, value.content_base64 or "", validate=True)
        except (binascii.Error, ValueError):
            return ToolOutcome(problem=ToolProblem("invalid_request", "Invalid base64 content"))
        file = UploadFile(file=BytesIO(content), filename=value.filename, size=len(content))
    try:
        if value.kind == "style_image":
            result = await upload_project_style_image(
                scope.project_name, _, file, manager=services.projects, change_source="worker"
            )
            installed = result.get("style_image")
        else:
            result = await upload_project_file(
                project_name=scope.project_name,
                require_reference_host=True,
                upload_type="character_ref" if value.kind == "character_image" else "character_audio_ref",
                _t=_,
                file=file,
                name=value.name,
                on_conflict="fail",
                role="whole_source",
                insert_at=None,
                source_kind=None,
                revision=None,
                manager=services.projects,
                change_source="worker",
            )
            installed = result.get("path")
    except (HTTPException, ApiError, ValueError) as exc:
        return ToolOutcome(problem=ToolProblem("reference_upload_failed", str(getattr(exc, "detail", exc))))
    finally:
        await file.close()
    if value.staged_upload_id is not None:
        with suppress(Exception):
            # Installed; a failed discard only leaves the staging to the TTL sweep.
            await discard_staged_upload(services.projects, scope.project_name, value.staged_upload_id)
    project_dir = await asyncio.to_thread(services.projects.get_project_path, scope.project_name)
    digest = await asyncio.to_thread(_installed_digest, project_dir, installed)
    return ToolOutcome(value={**result, "sha256": digest})
