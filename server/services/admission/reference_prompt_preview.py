"""Final reference-to-video prompts using actual sent references/capabilities from the current request projection.

The Web draft preview (:func:`render_reference_prompt_preview`) and the Agent/MCP unit preview
(:func:`preview_reference_unit`) share one gate (:func:`reference_preview_gate`) and one rendering
(:func:`render_reference_unit`), both built on the execution projector and ``render_video_unit_prompt``.
Read-only: no provider requests, charges, task submissions, or manifest/script writes."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from lib.config.resolver import ConfigResolver
from lib.generation.batch_admission import DURATION_CONFIRMATION_CODE
from lib.i18n import render_message
from lib.i18n.display_names import DisplayNames
from lib.infra.async_thread import run_sync_transaction
from lib.infra.content_digest import sha256_file_with_size
from lib.project.project_manager import ProjectManager
from lib.references.reference_catalog import build_reference_catalog

# IMAGE_MARKER / AUDIO_MARKER: the renderer's own marker forms, reported verbatim so preview rows and the
# rendered prompt cannot drift.
from lib.script.reference_video.prompt_render import (
    AUDIO_MARKER,
    IMAGE_MARKER,
    RenderedUnitPrompt,
    render_video_unit_prompt,
    resolve_reference_audio_paths,
)
from lib.script.reference_video.request_projection import (
    ReferenceUnitRequestProjection,
    ResolvedReferenceAsset,
    project_reference_unit_request,
)
from lib.script.reference_video.voice_settings import VoiceRenderSettings

#: Unit body is blank: nothing to render.
UNAVAILABLE_REFERENCE_PROMPT_MISSING = "reference_prompt_preview_missing"
#: The projection resolved no request facts for the hydrated bucket.
UNAVAILABLE_REFERENCE_CAPABILITY = "reference_capability_unavailable"

#: Machine-readable statement that a preview reflects current project files and configuration, not a captured submission.
PREVIEW_BASIS_CURRENT = "current_configuration"


class ReferenceUnitNotFound(LookupError):
    """The unit ID does not exist in the reference-video script."""


def reference_preview_gate(
    projection: ReferenceUnitRequestProjection, unit: Mapping[str, Any]
) -> tuple[str, dict[str, object]] | None:
    """Shared read-only gate: ``(code, params)`` when the prompt cannot be rendered, ``None`` when it can.

    Pending duration confirmation does not block viewing text; other projection blockers make the preview unavailable."""

    blockers = [problem for problem in projection.blocking_problems if problem.code != DURATION_CONFIRMATION_CODE]
    if blockers:
        return blockers[0].code, blockers[0].parameters()
    if projection.request_facts is None:
        return UNAVAILABLE_REFERENCE_CAPABILITY, {"capability": projection.hydrated_generation_type}
    if not str(unit.get("text") or "").strip():
        return UNAVAILABLE_REFERENCE_PROMPT_MISSING, {}
    return None


@dataclass(frozen=True)
class ReferenceUnitRendering:
    """Execution-equivalent rendering of one admitted unit: prompt, voice settings and resolved audio paths."""

    rendered: RenderedUnitPrompt
    settings: VoiceRenderSettings
    audio_paths: dict[str, Path]


def render_reference_unit(
    *, project: dict, unit: dict, project_path: Path, projection: ReferenceUnitRequestProjection
) -> ReferenceUnitRendering:
    """Render exactly as execution does: request facts voice settings, available audio, projected request references.

    Callers must first pass :func:`reference_preview_gate`. Synchronous filesystem reads: run in a worker thread."""

    request_facts = projection.request_facts
    if request_facts is None:
        raise ValueError("reference projection has no request facts")
    audio_paths = resolve_reference_audio_paths(project, project_path)
    settings = VoiceRenderSettings.from_request_facts(request_facts, audio_ready=audio_paths)
    rendered = render_video_unit_prompt(
        unit,
        project,
        settings,
        request_references=[asset.reference for asset in projection.request_assets],
    )
    return ReferenceUnitRendering(rendered=rendered, settings=settings, audio_paths=audio_paths)


def render_reference_prompt_preview(
    *,
    project: dict,
    unit: dict,
    project_path: Path,
    projection: ReferenceUnitRequestProjection,
    translate: Callable[..., str],
    names: DisplayNames,
) -> dict[str, Any]:
    """Web draft preview: localized text over the shared gate and rendering.

    Match storyboard previews: exactly one of ``text`` and ``unavailable`` is non-``None``; ``warnings`` accompanies text only.
    """
    result: dict[str, Any] = {
        "text": None,
        "unavailable": None,
        "is_text_form": True,
        "references": [],
        "warnings": [],
    }
    if (gate := reference_preview_gate(projection, unit)) is not None:
        code, params = gate
        result["unavailable"] = render_message(code, params, translate, names)
        return result

    rendering = render_reference_unit(project=project, unit=unit, project_path=project_path, projection=projection)
    result["text"] = rendering.rendered.prompt
    result["references"] = [
        {
            "type": asset.reference.type,
            "name": asset.reference.name,
            "path": asset.path.relative_to(project_path).as_posix(),
        }
        for asset in projection.request_assets
    ]
    result["warnings"] = [
        *(render_message(problem.code, problem.parameters(), translate, names) for problem in projection.problems),
        *(
            render_message(warning["key"], warning["params"], translate, names)
            for warning in rendering.rendered.warnings
        ),
    ]
    return result


# ---------------------------------------------------------------------------
# Structured (machine-readable) unit preview for Agent / MCP callers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceImageInput:
    """One reference image in request order; ``index`` is the ``@Image N`` number (1-based)."""

    index: int
    marker: str
    type: str
    #: Reference name as written in the body; derivatives use ``本体名/衍生名``.
    name: str
    #: Owning asset-table entry: the base character for derivatives, otherwise ``name``.
    base_name: str
    is_derivative: bool
    #: ``sheet`` (generated asset image) or ``original`` (product source image fallback).
    kind: str
    artifact_path: str | None
    sha256: str | None
    size_bytes: int | None


@dataclass(frozen=True)
class ReferenceAudioInput:
    """One reference-audio segment in request order; ``index`` is the ``@Audio N`` number (1-based).

    Voice always binds to the base character (``speaker``), independent of the derivative appearance shown in images."""

    index: int
    marker: str
    speaker: str
    artifact_path: str | None
    sha256: str | None
    size_bytes: int | None
    #: ``@Image N`` number the backend attaches this audio to, for backends binding audio per image; otherwise ``None``.
    target_image_index: int | None


@dataclass(frozen=True)
class ReferenceVideoRequestPreview:
    """Current-configuration request projection for one reference-video unit."""

    unit_id: str
    declared_generation_type: str
    hydrated_generation_type: str
    provider_id: str | None
    model_id: str | None
    planned_duration: int
    request_duration_seconds: int | None
    #: ``native`` / ``soft`` / ``none`` voice tier; ``None`` when request facts are unavailable.
    voice_consistency: str | None
    #: True when the backend attaches each audio segment to a specific reference image.
    audio_per_image: bool
    images: tuple[ReferenceImageInput, ...] = ()
    audio: tuple[ReferenceAudioInput, ...] = ()
    #: Declared references not sent: ``{type, name, reason}``; reason ``unavailable`` (no usable file) or ``clamped``.
    unavailable_references: tuple[dict[str, object], ...] = ()
    #: Projection problems in the shared Web/Agent/quote envelope (stable codes).
    problems: tuple[dict[str, object], ...] = ()


def _file_identity(project_path: Path, path: Path) -> tuple[str | None, str | None, int | None]:
    """Project-relative path plus sha256/size, hashed exactly like task-local provider media staging."""

    try:
        relative = path.resolve().relative_to(project_path.resolve()).as_posix()
    except (OSError, ValueError):
        relative = None
    try:
        digest, size = sha256_file_with_size(path)
    except (FileNotFoundError, OSError):
        return relative, None, None
    return relative, digest, size


def _image_inputs(
    project: dict, project_path: Path, assets: tuple[ResolvedReferenceAsset, ...]
) -> tuple[ReferenceImageInput, ...]:
    catalog = build_reference_catalog(project)
    images: list[ReferenceImageInput] = []
    for index, asset in enumerate(assets, start=1):
        reference = asset.reference
        entry = catalog.lookup(reference.type, reference.name)
        base_name = entry.asset_name if entry is not None else str(reference.name)
        artifact_path, digest, size = _file_identity(project_path, asset.path)
        images.append(
            ReferenceImageInput(
                index=index,
                marker=IMAGE_MARKER.format(index=index),
                type=reference.type,
                name=str(reference.name),
                base_name=base_name,
                is_derivative=entry is not None and entry.name != entry.asset_name,
                kind=asset.kind,
                artifact_path=artifact_path,
                sha256=digest,
                size_bytes=size,
            )
        )
    return tuple(images)


def _audio_inputs(project_path: Path, rendering: ReferenceUnitRendering) -> tuple[ReferenceAudioInput, ...]:
    """Audio in ``@Audio N`` order, filtered like execution's request wiring for per-image backends."""

    rendered = rendering.rendered
    pairs = list(zip(rendered.audio_speakers, rendered.audio_speaker_reference_index, strict=True))
    if rendering.settings.requires_reference_image:
        # Execution (``_build_reference_audio_wiring``) keeps only speakers attached to a sent image.
        pairs = [(speaker, target) for speaker, target in pairs if target is not None]
    audio: list[ReferenceAudioInput] = []
    for index, (speaker, target) in enumerate(pairs, start=1):
        path = rendering.audio_paths.get(speaker)
        artifact_path, digest, size = (None, None, None) if path is None else _file_identity(project_path, path)
        audio.append(
            ReferenceAudioInput(
                index=index,
                marker=AUDIO_MARKER.format(index=index),
                speaker=speaker,
                artifact_path=artifact_path,
                sha256=digest,
                size_bytes=size,
                target_image_index=(target + 1)
                if target is not None and rendering.settings.requires_reference_image
                else None,
            )
        )
    return tuple(audio)


def _unavailable_references(projection: ReferenceUnitRequestProjection) -> tuple[dict[str, object], ...]:
    def key(reference: Any) -> tuple[str, str]:
        return reference.type, str(reference.name)

    available = {key(asset.reference) for asset in projection.available_assets}
    sent = {key(asset.reference) for asset in projection.request_assets}
    result: list[dict[str, object]] = []
    for reference in projection.declared_references:
        identity = key(reference)
        if identity not in available:
            result.append({"type": identity[0], "name": identity[1], "reason": "unavailable"})
        elif identity not in sent:
            result.append({"type": identity[0], "name": identity[1], "reason": "clamped"})
    return tuple(result)


@dataclass(frozen=True)
class ReferenceUnitPreview:
    """Structured result: ``text`` xor ``unavailable`` (stable code), plus the request projection."""

    text: str | None
    unavailable: str | None
    unavailable_params: dict[str, object] = field(default_factory=dict)
    warnings: tuple[dict[str, Any], ...] = ()
    request: ReferenceVideoRequestPreview | None = None


def build_reference_unit_preview(
    *, project: dict, unit: dict, project_path: Path, projection: ReferenceUnitRequestProjection
) -> ReferenceUnitPreview:
    """Structured preview over the shared gate/rendering. Synchronous file reads: run in a worker thread."""

    facts = projection.request_facts
    request = ReferenceVideoRequestPreview(
        unit_id=projection.unit_id,
        declared_generation_type=projection.declared_generation_type,
        hydrated_generation_type=projection.hydrated_generation_type,
        provider_id=projection.provider_id,
        model_id=projection.model_id,
        planned_duration=projection.planned_duration,
        request_duration_seconds=projection.request_duration.seconds if projection.request_duration else None,
        voice_consistency=facts.voice_consistency if facts is not None else None,
        audio_per_image=bool(facts.reference_audio_per_image) if facts is not None else False,
        unavailable_references=_unavailable_references(projection),
        problems=tuple(projection.problem_payloads()),
    )
    if (gate := reference_preview_gate(projection, unit)) is not None:
        code, params = gate
        return ReferenceUnitPreview(text=None, unavailable=code, unavailable_params=params, request=request)

    rendering = render_reference_unit(project=project, unit=unit, project_path=project_path, projection=projection)
    request = replace(
        request,
        images=_image_inputs(project, project_path, projection.request_assets),
        audio=_audio_inputs(project_path, rendering),
    )
    warnings = (
        *({"key": problem.code, "params": problem.parameters()} for problem in projection.problems),
        *rendering.rendered.warnings,
    )
    return ReferenceUnitPreview(
        text=rendering.rendered.prompt, unavailable=None, warnings=tuple(warnings), request=request
    )


async def preview_reference_unit(
    project_name: str,
    script_file: str,
    unit_id: str,
    *,
    projects: ProjectManager,
    resolver: ConfigResolver | None = None,
) -> ReferenceUnitPreview:
    """Project and render one saved reference-video unit with current configuration, as execution would.

    Read-only: loads project/script, builds the shared request projection, renders, and hashes the selected inputs."""

    def _load() -> tuple[dict[str, Any], Path, dict[str, Any], dict[str, Any]]:
        project = projects.load_project(project_name)
        project_path = projects.get_project_path(project_name)
        script = projects.load_script(project_name, script_file)
        for unit in script.get("video_units") or []:
            if isinstance(unit, dict) and unit.get("unit_id") == unit_id:
                return project, project_path, script, unit
        raise ReferenceUnitNotFound(unit_id)

    project, project_path, script, unit = await run_sync_transaction(_load)
    projection = await project_reference_unit_request(
        project=project,
        script=script,
        unit=unit,
        project_path=project_path,
        resolver=resolver,
    )
    return await asyncio.to_thread(
        build_reference_unit_preview, project=project, unit=unit, project_path=project_path, projection=projection
    )


__all__ = [
    "PREVIEW_BASIS_CURRENT",
    "UNAVAILABLE_REFERENCE_CAPABILITY",
    "UNAVAILABLE_REFERENCE_PROMPT_MISSING",
    "ReferenceAudioInput",
    "ReferenceImageInput",
    "ReferenceUnitNotFound",
    "ReferenceUnitPreview",
    "ReferenceUnitRendering",
    "ReferenceVideoRequestPreview",
    "build_reference_unit_preview",
    "preview_reference_unit",
    "reference_preview_gate",
    "render_reference_prompt_preview",
    "render_reference_unit",
]
