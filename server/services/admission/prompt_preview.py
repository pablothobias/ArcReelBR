"""Preview rendering of final entry prompts.

Show the exact image/video-model prompt if this entry were generated now. Use the same rendering functions as execution:
``lib.prompts.prompt_builders.render_storyboard_image_prompt`` /
``lib.prompts.prompt_utils.render_storyboard_video_prompt``. Storyboard images share execution’s generation input
(``lib.artifacts.generation_input``): rejected generation makes that side unavailable with gap codes; otherwise truncate
references using the same backend limit and render matching ``图N`` numbering. Truncation includes warnings shaped like
runtime results so users know before generation that some references will not be sent. Video previews resolve content mode
and voice bindings using execution rules.

Read-only: no provider requests, costs or manifest writes. Reference-video units are rendered by
``server.services.admission.reference_prompt_preview``; :func:`preview_entry_prompts` routes an entry to its route's
preview."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.artifacts.artifact_input_claims import resolve_usable_episode_script_input
from lib.artifacts.generation_input import (
    AssembledReference,
    StoryboardImageInput,
    project_input_observation,
    storyboard_image_input,
)
from lib.config.resolver import ConfigResolver
from lib.infra.async_thread import run_sync_transaction
from lib.project.project_manager import ProjectManager, get_project_manager
from lib.prompts.prompt_utils import render_storyboard_video_prompt
from lib.script.script_models import resolve_content_mode
from lib.script.storyboard_sequence import find_storyboard_item, get_storyboard_items
from server.services.admission.reference_admission import input_refusal_error
from server.services.admission.reference_prompt_preview import (
    PREVIEW_BASIS_CURRENT,
    ReferenceUnitNotFound,
    ReferenceVideoRequestPreview,
    preview_reference_unit,
)
from server.services.admission.video_batch_admission import resolve_voice_context
from server.services.tasks.generation_context import ImageLaneRequest, resolve_generation_context

logger = logging.getLogger(__name__)

#: Unavailability for pending prompts, ``None`` or absent fields, not yet authored after mechanical conversion.
UNAVAILABLE_PENDING = "prompt_preview_pending"
#: Unavailability for present but empty prompt fields, empty strings/objects.
UNAVAILABLE_MISSING = "prompt_preview_missing"
#: Unavailability for present malformed prompts rejected by rendering.
UNAVAILABLE_INVALID = "prompt_preview_invalid"
#: The side does not exist on this route (reference-video units have no storyboard image).
UNAVAILABLE_NOT_APPLICABLE = "prompt_preview_not_applicable"


class ScriptItemNotFound(LookupError):
    """The item ID does not exist in the script."""


@dataclass(frozen=True)
class RenderedPrompt:
    """Rendering result for one prompt side: exactly one of ``text`` and ``unavailable`` is non-``None``.

    ``warnings`` contains nonblocking rendering hints such as backend-limit reference truncation, shaped like task
    ``result.warnings`` ``{key, params}`` entries and present only when ``text`` renders successfully."""

    text: str | None = None
    unavailable: str | None = None
    #: Message parameters for unavailability; rejected generation input includes all gaps, shaped like runtime error details.
    unavailable_params: dict[str, object] = field(default_factory=dict)
    is_text_form: bool = False
    warnings: tuple[dict[str, Any], ...] = ()
    #: Reference images actually sent with this side, in request order (``图N`` numbering); only filled where the
    #: shared generation input exposes them (storyboard images). Each entry carries logical identity and digest.
    references: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ItemPromptPreview:
    item_id: str
    content_mode: str
    storyboard_image: RenderedPrompt
    video: RenderedPrompt
    #: Project generation route that owns the entry: ``storyboard`` or ``reference_video``.
    generation_mode: str = "storyboard"
    #: Always ``current_configuration``: rendered from current files and configuration, never a historical task payload.
    preview_basis: str = PREVIEW_BASIS_CURRENT
    #: Reference-video request projection (images/audio in send order, bindings, unavailable inputs); ``None`` for storyboards.
    reference_video: ReferenceVideoRequestPreview | None = None
    #: Inputs captured by a submitted task's execution checkpoint, only when a ``task_id`` was requested.
    captured_submission: dict[str, Any] | None = None


def _unavailable_before_rendering(prompt: object) -> str | None:
    """Unavailability detectable before rendering: pending or empty; ``None`` means the prompt should be rendered."""
    if prompt is None:
        return UNAVAILABLE_PENDING
    if (isinstance(prompt, str) and not prompt.strip()) or prompt == {}:
        return UNAVAILABLE_MISSING
    return None


def _render(prompt: object, render: Any) -> RenderedPrompt:
    is_text_form = isinstance(prompt, str)
    if (reason := _unavailable_before_rendering(prompt)) is not None:
        return RenderedPrompt(unavailable=reason, is_text_form=is_text_form)
    try:
        return RenderedPrompt(text=render(prompt), is_text_form=is_text_form)
    except (ValueError, TypeError, KeyError):
        return RenderedPrompt(unavailable=UNAVAILABLE_INVALID, is_text_form=is_text_form)


async def reference_image_limit(
    project_name: str,
    project: dict[str, Any],
    project_path: Path,
) -> tuple[int | None, str]:
    """Image-lane reference limit and model name, sharing execution truncation rules; ``None`` means no truncation.

    Resolution constructs a backend requiring credentials. Missing credentials/providers must not prevent read-only prompt
    inspection: resolution failure disables truncation and logs info. Such projects cannot generate anyway, preserving
    preview/execution text consistency. Preview resolves current project configuration without task payloads; a queued
    payload pinning another provider with different limits may have different numbering, a known limitation because
    preview does not know that payload."""
    try:
        ctx = await resolve_generation_context(
            project_name,
            None,
            project=project,
            project_path=project_path,
            image=ImageLaneRequest(generation_type="i2i"),
        )
    except Exception as exc:
        logger.info("预览无法解析 image lane，参考图不按后端上限裁剪：%s", exc)
        return None, ""
    return ctx.image.max_reference_images, ctx.image.backend_model


def _sent_references(references: Sequence[AssembledReference]) -> tuple[dict[str, Any], ...]:
    """Machine-readable identity of the images actually sent, from the shared generation input (never inferred from text)."""
    return tuple(
        {
            "index": index,
            "role": reference.visual.role,
            "logical_type": reference.visual.logical_type,
            "logical_id": reference.visual.logical_id,
            "kind": reference.visual.kind,
            "artifact_path": reference.artifact_path,
            "content_digest": reference.visual.content_digest,
        }
        for index, reference in enumerate(references, start=1)
    )


async def preview_item_prompts(
    project_name: str,
    script_file: str,
    item_id: str,
    *,
    projects: ProjectManager | None = None,
) -> ItemPromptPreview:
    """Render final storyboard-image and video prompts for one storyboard entry.

    ``projects`` lets tool runtimes inject an already resolved ProjectManager; REST routes use the process default."""

    def _load() -> tuple[dict[str, Any], Path, dict[str, Any], dict[str, Any], str]:
        manager = projects if projects is not None else get_project_manager()
        project = manager.load_project(project_name)
        project_path = manager.get_project_path(project_name)
        script = manager.load_script(project_name, script_file)
        items, id_field, *_ = get_storyboard_items(script)
        resolved = find_storyboard_item(items, id_field, item_id)
        if resolved is None:
            raise ScriptItemNotFound(item_id)
        return project, project_path, script, resolved[0], resolve_content_mode(script, project)

    project, project_path, script, item, content_mode = await run_sync_transaction(_load)
    # Resolve voice bindings from current project video capabilities, None for nondrama/silent paths, matching execution.
    voice_characters = await resolve_voice_context(project, content_mode)

    def _assemble() -> StoryboardImageInput:
        # Share execution input, including previous-storyboard availability, so ``图N`` numbering matches exactly;
        # unregistered/changed script content raises ValueError as an unrenderable prompt, while Manifest failures
        # (ArtifactManifestError) remain fail-loud.
        script_input = resolve_usable_episode_script_input(
            project_path=project_path,
            project=project,
            script=script,
            script_filename=script_file,
        )
        return storyboard_image_input(
            project,
            script,
            episode=script_input.episode,
            resource_id=item_id,
            observation=project_input_observation(project_path),
        )

    image: RenderedPrompt | None = None
    generation_input: StoryboardImageInput | None = None
    image_prompt = item.get("image_prompt")
    is_text_form = isinstance(image_prompt, str)
    # Empty prompts cannot render; generation input handles pending prompts to report them with all reference gaps.
    if image_prompt is not None and (reason := _unavailable_before_rendering(image_prompt)) is not None:
        image = RenderedPrompt(unavailable=reason, is_text_form=is_text_form)
    else:
        try:
            assembled = await asyncio.to_thread(_assemble)
        except (ValueError, TypeError, KeyError):
            image = RenderedPrompt(unavailable=UNAVAILABLE_INVALID, is_text_form=is_text_form)
        else:
            if (refused := assembled.refusal) is not None:
                refusal = input_refusal_error(refused)
                image = RenderedPrompt(
                    unavailable=refusal.key,
                    unavailable_params=dict(refusal.params),
                    is_text_form=is_text_form,
                )
            else:
                generation_input = assembled
    limit = (
        await reference_image_limit(project_name, project, project_path)
        if generation_input is not None and generation_input.references
        else (None, "")
    )

    def _render_both() -> ItemPromptPreview:
        storyboard_image = image
        if storyboard_image is None:
            assert generation_input is not None
            max_reference_images, model = limit
            try:
                rendered = generation_input.render(max_reference_images=max_reference_images, model=model)
            except (ValueError, TypeError, KeyError):
                storyboard_image = RenderedPrompt(unavailable=UNAVAILABLE_INVALID, is_text_form=is_text_form)
            else:
                storyboard_image = RenderedPrompt(
                    text=rendered.prompt,
                    is_text_form=is_text_form,
                    warnings=rendered.warnings,
                    references=_sent_references(generation_input.references[: rendered.sent_count]),
                )
        video = _render(
            item.get("video_prompt"),
            lambda prompt: render_storyboard_video_prompt(
                prompt,
                item,
                content_mode=content_mode,
                voice_characters=voice_characters,
            ),
        )
        return ItemPromptPreview(
            item_id=item_id,
            content_mode=content_mode,
            storyboard_image=storyboard_image,
            video=video,
        )

    return await asyncio.to_thread(_render_both)


async def preview_entry_prompts(
    project_name: str,
    script_file: str,
    item_id: str,
    *,
    projects: ProjectManager,
    resolver: ConfigResolver | None = None,
) -> ItemPromptPreview:
    """Route one script entry to its generation route's native preview (Agent/MCP entry).

    ``video_units`` entries use the reference-video request projector and renderer shared with the Web unit preview and
    execution; every other entry uses :func:`preview_item_prompts`. Read-only on both routes."""

    def _is_reference_unit() -> bool:
        script = projects.load_script(project_name, script_file)
        units = script.get("video_units")
        return isinstance(units, list) and any(
            isinstance(unit, dict) and unit.get("unit_id") == item_id for unit in units
        )

    if not await run_sync_transaction(_is_reference_unit):
        return await preview_item_prompts(project_name, script_file, item_id, projects=projects)

    def _content_mode() -> str:
        return resolve_content_mode(
            projects.load_script(project_name, script_file), projects.load_project(project_name)
        )

    try:
        unit_preview = await preview_reference_unit(
            project_name, script_file, item_id, projects=projects, resolver=resolver
        )
    except ReferenceUnitNotFound as exc:
        raise ScriptItemNotFound(item_id) from exc
    content_mode = await run_sync_transaction(_content_mode)
    return ItemPromptPreview(
        item_id=item_id,
        content_mode=content_mode,
        storyboard_image=RenderedPrompt(unavailable=UNAVAILABLE_NOT_APPLICABLE, is_text_form=True),
        video=RenderedPrompt(
            text=unit_preview.text,
            unavailable=unit_preview.unavailable,
            unavailable_params=unit_preview.unavailable_params,
            is_text_form=True,
            warnings=unit_preview.warnings,
        ),
        generation_mode="reference_video",
        reference_video=unit_preview.request,
    )


__all__ = [
    "UNAVAILABLE_INVALID",
    "UNAVAILABLE_MISSING",
    "UNAVAILABLE_NOT_APPLICABLE",
    "UNAVAILABLE_PENDING",
    "ItemPromptPreview",
    "RenderedPrompt",
    "ScriptItemNotFound",
    "preview_entry_prompts",
    "preview_item_prompts",
]
