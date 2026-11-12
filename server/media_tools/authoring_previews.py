"""Host-neutral authoring and preview tools over native services.

- ``start_blank_script``: the Web “Start from blank” transaction (:mod:`lib.script.blank_script`).
- ``get_asset_prompt_preview``: the Web asset/derivative pre-generation prompt preview
  (:mod:`server.services.admission.asset_prompt_preview`), read-only.
- ``generate_project_overview``: the Web “generate overview” text-model call
  (:meth:`lib.project.project_manager.ProjectManager.generate_overview`), only with explicit authorization.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from pydantic import ValidationError as PydanticValidationError
from pydantic.json_schema import SkipJsonSchema

from lib.backends.text_backends.base import SubscriptionQuotaPaused, TextOutputTruncatedError
from lib.catalog.errors import ModelNotInCatalogError
from lib.infra.async_thread import run_sync_transaction
from lib.project.asset_types import ASSET_SPECS
from lib.project.project_change_hints import project_change_source
from lib.project.project_manager import EmptySourceError
from lib.script.blank_script import BlankScriptError, start_blank_script_detailed
from lib.script.source_loader.errors import SourceDecodeError
from server.draft_workflow import EPISODE_ID_DESCRIPTION, PositiveEpisode
from server.media_tools.context import tool_error, tool_problem
from server.services.admission.asset_prompt_preview import preview_asset_prompt, resolve_asset_preview_target
from server.services.admission.reference_prompt_preview import PREVIEW_BASIS_CURRENT
from server.tool_runtime import (
    CallerContext,
    ProjectScope,
    Services,
    ToolOutcome,
    ToolProblem,
    ToolRequest,
    migration_gate,
    model_not_in_catalog_problem,
    truncation_problem,
)

# ---------------------------------------------------------------------------
# MCP-001: start_blank_script
# ---------------------------------------------------------------------------


class StartBlankScriptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    episode_id: PositiveEpisode = Field(description=EPISODE_ID_DESCRIPTION)


async def start_blank_script(
    request: ToolRequest[StartBlankScriptRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    """Run the native blank-start transaction; never calls a model and never overwrites a formal script."""

    episode = request.value.episode_id

    def run() -> Any:
        with project_change_source("worker"):
            return start_blank_script_detailed(services.projects, scope.project_name, episode)

    try:
        result = await run_sync_transaction(run)
    except BlankScriptError as exc:
        return tool_problem(str(exc), code=exc.code, params={"episode_id": episode})
    except FileNotFoundError as exc:
        return tool_problem(str(exc), code="project_not_found")
    except Exception as exc:
        return tool_error("start_blank_script", exc)
    return ToolOutcome(
        value={
            "episode_id": result.episode,
            "script_file": result.script_file,
            "created": True,
            "discarded_script_plan": result.discarded_script_plan,
            "discarded_drafts": list(result.discarded_drafts),
            "cleared_script_plan_confirmation": result.cleared_review,
        }
    )


def start_blank_script_summary(value: dict[str, Any]) -> str:
    discarded = []
    if value.get("discarded_script_plan"):
        discarded.append("unconfirmed script_plan")
    discarded.extend(f"draft {kind}" for kind in value.get("discarded_drafts") or [])
    tail = f"; moved to project trash: {', '.join(discarded)}" if discarded else ""
    return f"Blank formal script created: scripts/{value['script_file']} (episode_id={value['episode_id']}){tail}"


# ---------------------------------------------------------------------------
# MCP-019: get_asset_prompt_preview
# ---------------------------------------------------------------------------


class AssetPromptPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_type: Literal["character", "scene", "prop", "product"] = Field(description="Asset table of the entry")
    name: str = Field(min_length=1, description="Registered asset name (base character name for derivatives)")
    derivative: str | SkipJsonSchema[None] = Field(
        default=None,
        min_length=1,
        description="Derivative name under the character to preview its derivative sheet instead of the base sheet",
    )
    description: str | SkipJsonSchema[None] = Field(
        default=None,
        description="Optional unsaved draft description to render instead of the stored one; never persisted",
    )


async def get_asset_prompt_preview(
    request: ToolRequest[AssetPromptPreviewRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    """Render the asset/derivative sheet prompt with the executor's generation input; zero writes or generation."""

    value = request.value
    spec = ASSET_SPECS[value.asset_type]
    if value.derivative is not None and not spec.supports_derivatives:
        return tool_problem(f"{value.asset_type} assets have no derivatives", code="derivatives_not_supported")
    try:
        if problem := await migration_gate(scope, services):
            return ToolOutcome(problem=problem)

        def load() -> tuple[dict[str, Any], Any, tuple[str, str | None] | None]:
            project = services.projects.load_project(scope.project_name)
            target = resolve_asset_preview_target(project, spec, value.name, value.derivative)
            return project, services.projects.get_project_path(scope.project_name), target

        project, project_path, target = await asyncio.to_thread(load)
        if target is None:
            return tool_problem(
                "Asset or derivative is not registered",
                code="asset_not_found",
                params={"asset_type": value.asset_type, "name": value.name, "derivative": value.derivative},
            )
        asset_key, derivative_key = target
        preview = await preview_asset_prompt(
            scope.project_name,
            project,
            project_path,
            asset_type=value.asset_type,
            asset_key=asset_key,
            derivative_key=derivative_key,
            description=value.description,
        )
    except FileNotFoundError as exc:
        return tool_problem(str(exc), code="project_not_found")
    except Exception as exc:
        return tool_error("get_asset_prompt_preview", exc)
    rendered = preview.rendered
    return ToolOutcome(
        value={
            "asset_type": value.asset_type,
            "name": asset_key,
            "derivative": derivative_key,
            "target_kind": preview.target_kind,
            "preview_basis": PREVIEW_BASIS_CURRENT,
            "draft_description": value.description is not None,
            "text": rendered.text,
            "unavailable": rendered.unavailable,
            "unavailable_params": rendered.unavailable_params,
            "warnings": list(rendered.warnings),
            "description": preview.description,
            "style": preview.style,
            "style_description": preview.style_description,
            "occupancy": preview.occupancy,
            "canvas_ratio": preview.canvas_ratio,
            "references": list(preview.references),
            "limits": {
                "max_reference_images": preview.max_reference_images,
                "image_model": preview.image_model,
                "sent_reference_count": sum(1 for reference in preview.references if reference["sent"]),
            },
        }
    )


# ---------------------------------------------------------------------------
# MCP-020: generate_project_overview
# ---------------------------------------------------------------------------

#: Overview fields that enter recorded script-plan / prompt-authoring / ad-script bases (see artifact_provenance).
_OVERVIEW_BASIS_FIELDS = ("synopsis", "genre", "theme", "world_setting")


class GenerateProjectOverviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    confirm_text_model_call: StrictBool = Field(
        default=False,
        description=(
            "Overview generation calls the configured text model (consumes model quota / may be billed); "
            "explicit authorization is required. Without it, returns confirmation_required with the source scope"
        ),
    )


def _overview_impacts(
    before: dict[str, Any], after: dict[str, Any], language_before: object, language_after: object
) -> dict[str, Any]:
    changed = [field for field in _OVERVIEW_BASIS_FIELDS if before.get(field) != after.get(field)]
    language_changed = language_before != language_after
    basis_changed = bool(changed) or language_changed
    return {
        "changed_fields": changed,
        "source_language_changed": language_changed,
        "basis_changed": basis_changed,
        "affected_inputs": (
            [
                "script_plan prompt inputs (project_overview, target_language)",
                "prompt-authoring inputs (overview, target_language)",
                "ad episode script inputs (overview, target_language)",
            ]
            if basis_changed
            else []
        ),
        "note": (
            "Same passive effect as patch_project(overview=...): existing script plans and scripts whose recorded "
            "basis includes these fields are reported stale by get_workflow_plan; nothing is regenerated."
        ),
    }


async def generate_project_overview(
    request: ToolRequest[GenerateProjectOverviewRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[dict[str, Any]]:
    """Run the native overview generation (one text-model call) after explicit authorization."""

    projects = services.projects
    try:
        sources = await asyncio.to_thread(projects.describe_overview_sources, scope.project_name)
        before_project = await asyncio.to_thread(projects.load_project, scope.project_name)
    except SourceDecodeError as exc:
        return tool_problem(str(exc), code="source_decode_failed", params={"filename": exc.filename})
    except FileNotFoundError as exc:
        return tool_problem(str(exc), code="project_not_found")
    except Exception as exc:
        return tool_error("generate_project_overview", exc)
    if not sources:
        return tool_problem("The project has no text source to summarize", code="source_empty")
    if not request.value.confirm_text_model_call:
        return tool_problem(
            "Overview generation calls the configured text model; retry with confirm_text_model_call=true after the "
            "user authorizes it. patch_project(overview=...) edits the overview manually without a model call.",
            code="confirmation_required",
            params={"operation": "generate_project_overview", "sources": sources},
        )
    try:
        with project_change_source("worker"):
            overview = await projects.generate_overview(scope.project_name)
        after_project = await asyncio.to_thread(projects.load_project, scope.project_name)
    except EmptySourceError as exc:
        return tool_problem(str(exc), code="source_empty")
    except SourceDecodeError as exc:
        return tool_problem(str(exc), code="source_decode_failed", params={"filename": exc.filename})
    except TextOutputTruncatedError as exc:
        return ToolOutcome(problem=truncation_problem(exc))
    except ModelNotInCatalogError as exc:
        return ToolOutcome(problem=model_not_in_catalog_problem(exc))
    except PydanticValidationError:
        # Raw model output fragments stay out of the result, matching the Web route.
        return tool_problem("The text model returned an invalid overview", code="overview_ai_response_invalid")
    except SubscriptionQuotaPaused as exc:
        return ToolOutcome(problem=ToolProblem(exc.code, str(exc), params={"resumable": True}))
    except ValueError as exc:
        return tool_problem(str(exc), code="text_provider_not_configured")
    except Exception as exc:
        return tool_error("generate_project_overview", exc)
    previous = before_project.get("overview")
    previous = previous if isinstance(previous, dict) else {}
    language_before = before_project.get("source_language")
    language_after = after_project.get("source_language")
    return ToolOutcome(
        value={
            "overview": overview,
            "previous_overview": previous or None,
            "source_language": {"before": language_before, "after": language_after},
            "sources": sources,
            "stale_impacts": _overview_impacts(previous, overview, language_before, language_after),
        }
    )


def generate_project_overview_summary(value: dict[str, Any]) -> str:
    changed = value["stale_impacts"]["changed_fields"]
    return f"Project overview generated with the text model; changed fields: {', '.join(changed) or 'none'}"


__all__ = [
    "AssetPromptPreviewRequest",
    "GenerateProjectOverviewRequest",
    "StartBlankScriptRequest",
    "generate_project_overview",
    "generate_project_overview_summary",
    "get_asset_prompt_preview",
    "start_blank_script",
    "start_blank_script_summary",
]
