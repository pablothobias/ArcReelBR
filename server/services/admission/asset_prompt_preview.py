"""Asset-image draft prompt preview: substitute the draft description into generation input and use the runtime rendering path without submitting generation or saving the description.

Use the same generation input as the executor (``lib.artifacts.generation_input``). When generation would be rejected
(an empty description, unreadable original image, or unavailable base asset image for a derivative), the preview is unavailable
with a gap code. Otherwise, truncate references to the same image-backend limit as the executor before rendering.
When truncation occurs, include a warning with the same shape as runtime task results."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.artifacts.generation_input import (
    AssetSheetInput,
    AssetSheetSemantics,
    DerivativeSheetInput,
    asset_sheet_input,
    derivative_sheet_input,
    project_input_observation,
)
from lib.infra.api_errors import NotFoundError
from lib.project.asset_derivatives import resolve_derivative_target
from lib.project.asset_types import ASSET_SPECS, DERIVATIVES_FIELD, AssetSpec, resolve_asset_key
from server.services.admission.prompt_preview import UNAVAILABLE_INVALID, RenderedPrompt, reference_image_limit
from server.services.admission.reference_admission import input_refusal_error


def _with_draft_description(
    project: Mapping[str, Any],
    *,
    asset_type: str,
    asset_key: str,
    derivative_key: str | None,
    description: str,
) -> dict[str, Any]:
    """Copy the project payload with the target description replaced by the draft; copy only the path containing the draft."""

    bucket_key = ASSET_SPECS[asset_type].bucket_key
    draft = dict(project)
    bucket = draft[bucket_key] = dict(project[bucket_key])
    entry = bucket[asset_key] = dict(bucket[asset_key])
    if derivative_key is None:
        entry["description"] = description
    else:
        table = entry[DERIVATIVES_FIELD] = dict(entry[DERIVATIVES_FIELD])
        table[derivative_key] = {**table[derivative_key], "description": description}
    return draft


def resolve_asset_preview_target(
    project: Mapping[str, Any], spec: AssetSpec, entry_name: str, derivative_name: str | None
) -> tuple[str, str | None] | None:
    """Resolve requested names to persisted ``(asset_key, derivative_key)``; ``None`` when either is not registered.

    Shared by the Web preview routes and the Agent/MCP asset preview tool."""

    asset_key = resolve_asset_key(project.get(spec.bucket_key), entry_name)
    if asset_key is None:
        return None
    if derivative_name is None:
        return asset_key, None
    try:
        target = resolve_derivative_target(dict(project), entry_name, derivative_name)
    except (KeyError, NotFoundError):
        return None
    return target.owner_key, target.derivative_key


@dataclass(frozen=True)
class AssetPromptPreview:
    """Structured asset/derivative preview: ``rendered`` plus the shared generation input facts behind it.

    ``references`` lists every assembled reference in assembly order with ``sent`` marking those inside the
    provider limit; identities and digests come from the generation input, never from prompt text."""

    rendered: RenderedPrompt
    #: ``asset_sheet`` or ``derivative_sheet``.
    target_kind: str
    #: Style inputs the renderer used; derivatives render without style (the base sheet reference carries it).
    style: str | None = None
    style_description: str | None = None
    #: Description the renderer used (stored unless a draft was supplied).
    description: str | None = None
    canvas_ratio: str | None = None
    references: tuple[dict[str, Any], ...] = ()
    #: Image-backend reference limit applied before rendering; ``None`` means no truncation (or unresolved backend).
    max_reference_images: int | None = None
    image_model: str | None = None


def _semantic_fields(generation_input: AssetSheetInput | DerivativeSheetInput) -> dict[str, Any]:
    semantics = generation_input.semantics
    if isinstance(semantics, AssetSheetSemantics):
        return {
            "style": semantics.style,
            "style_description": semantics.style_description,
            "description": semantics.description,
        }
    return {"description": semantics.description}


async def preview_asset_prompt(
    project_name: str,
    project: Mapping[str, Any],
    project_path: Path,
    *,
    asset_type: str,
    asset_key: str,
    derivative_key: str | None,
    description: str | None = None,
) -> AssetPromptPreview:
    """Render asset/derivative prompts with execution rules; ``description=None`` uses the stored description.

    ``asset_key`` / ``derivative_key`` are the actual persisted names. Read-only: no write, task, or provider call."""

    target_kind = "asset_sheet" if derivative_key is None else "derivative_sheet"

    def _assemble() -> AssetSheetInput | DerivativeSheetInput:
        source = (
            project
            if description is None
            else _with_draft_description(
                project,
                asset_type=asset_type,
                asset_key=asset_key,
                derivative_key=derivative_key,
                description=description,
            )
        )
        observation = project_input_observation(project_path)
        if derivative_key is None:
            return asset_sheet_input(source, asset_type=asset_type, name=asset_key, observation=observation)
        return derivative_sheet_input(source, owner=asset_key, derivative=derivative_key, observation=observation)

    try:
        generation_input = await asyncio.to_thread(_assemble)
    except (ValueError, TypeError, KeyError):
        return AssetPromptPreview(
            rendered=RenderedPrompt(unavailable=UNAVAILABLE_INVALID, is_text_form=True), target_kind=target_kind
        )
    facts: dict[str, Any] = {"target_kind": target_kind, "canvas_ratio": generation_input.canvas_ratio}
    if (refused := generation_input.refusal) is not None:
        refusal = input_refusal_error(refused)
        return AssetPromptPreview(
            rendered=RenderedPrompt(
                unavailable=refusal.key, unavailable_params=dict(refusal.params), is_text_form=True
            ),
            **facts,
        )
    max_reference_images, model = (
        await reference_image_limit(project_name, dict(project), project_path)
        if generation_input.references
        else (None, "")
    )
    rendered = generation_input.render(max_reference_images=max_reference_images, model=model)
    references = tuple(
        {
            "index": index,
            "sent": index <= rendered.sent_count,
            "role": reference.visual.role,
            "logical_type": reference.visual.logical_type,
            "logical_id": reference.visual.logical_id,
            "kind": reference.visual.kind,
            "artifact_path": reference.artifact_path,
            "content_digest": reference.visual.content_digest,
        }
        for index, reference in enumerate(generation_input.references, start=1)
    )
    return AssetPromptPreview(
        rendered=RenderedPrompt(
            text=rendered.prompt,
            is_text_form=True,
            warnings=rendered.warnings,
            references=tuple(reference for reference in references if reference["sent"]),
        ),
        references=references,
        max_reference_images=max_reference_images,
        image_model=model or None,
        **facts,
        **_semantic_fields(generation_input),
    )


async def render_asset_prompt(
    project_name: str,
    project: Mapping[str, Any],
    project_path: Path,
    *,
    asset_type: str,
    asset_key: str,
    derivative_key: str | None,
    description: str,
) -> RenderedPrompt:
    """Render a draft description using asset execution rules: derivatives edit only the base appearance; the base image carries the style.

    ``asset_key`` / ``derivative_key`` are the actual persisted names in the asset and derivative tables."""

    preview = await preview_asset_prompt(
        project_name,
        project,
        project_path,
        asset_type=asset_type,
        asset_key=asset_key,
        derivative_key=derivative_key,
        description=description,
    )
    return preview.rendered
