"""Host-neutral tools for character voice references: TTS voices, preview samples, sample records, binding and inspection.

All domain rules live in ``server.services.voice_references``; generation goes through the native ``voice_sample``
queue task. Only ``generate_voice_sample`` (preview=false) creates a task or reaches a provider. Listing, quoting,
confirming and inspecting never enqueue, never synthesize, and never download models.

Tool response text is Agent-facing, without i18n; register display names in ``ARCREEL_MCP_TOOL_IDS`` with all three translations.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from lib.catalog.errors import ModelNotInCatalogError
from lib.generation.generation_result import (
    GenerationResultBuilder,
    GenerationSelectionMode,
    problem_from_task_failure,
    record_batch_outcomes,
)
from lib.i18n import DEFAULT_LOCALE
from lib.i18n import _ as translate
from lib.infra.api_errors import ApiError
from lib.infra.ffmpeg import FfmpegUnavailableError
from lib.infra.media_probe import MediaProbeError, probe_media
from lib.infra.path_safety import safe_join
from lib.material.work_files import local_work_files
from lib.project.asset_types import resolve_asset_key, validate_asset_name
from lib.speech.audio_review import AudioReviewUnavailable, transcribe_media
from server.media_tools.context import (
    generation_batch_submission_outcome,
    generation_result_outcome,
    tool_error,
    tool_problem,
)
from server.services import voice_references as voices
from server.tool_runtime import (
    CallerContext,
    ProjectScope,
    Services,
    ToolOutcome,
    ToolProblem,
    ToolRequest,
    migration_gate,
    model_not_in_catalog_problem,
    submit_media_generation,
)

_GENERATE = "generate_voice_sample"

_SHA256 = r"^[0-9a-f]{64}$"

#: What a transcript cannot establish; repeated in every inspection that runs recognition.
_TRANSCRIPT_LIMITS = (
    "A transcript shows recognized words only. It proves neither voice identity, acting, emotion nor lip sync, "
    "and is not a human listening review."
)


def _api_problem(exc: ApiError) -> ToolOutcome[Any]:
    return tool_problem(translate(exc.key, DEFAULT_LOCALE, **exc.params), code=exc.key, params=exc.params or None)


def _suffix(relative_path: str) -> str:
    return PurePosixPath(relative_path).suffix.lstrip(".").lower()


# ==================== list_tts_voices ====================


class ListTtsVoicesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


async def list_tts_voices(
    request: ToolRequest[ListTtsVoicesRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    del request
    try:
        if (problem := await migration_gate(scope, services)) is not None:
            return ToolOutcome(problem=problem)
        project = await asyncio.to_thread(services.projects.load_project, scope.project_name)
        catalog = await voices.resolve_voice_catalog(scope.project_name, project, resolver=services.capabilities)
    except ModelNotInCatalogError as exc:
        return ToolOutcome(problem=model_not_in_catalog_problem(exc))
    except ApiError as exc:
        return _api_problem(exc)
    except Exception as exc:
        return tool_error("list_tts_voices", exc)
    value: dict[str, Any] = {
        "configured": catalog.configured,
        "provider_id": catalog.provider_id,
        "model": catalog.model,
        "backend": catalog.backend_name,
        "voices": [{"id": v.id, "label": translate(v.label, DEFAULT_LOCALE)} for v in catalog.voices],
        "sample_text_max_length": voices.VOICE_SAMPLE_TEXT_MAX_LENGTH,
        "reference_limits": voices.REFERENCE_LIMITS.to_payload(),
    }
    if not catalog.configured:
        value["note"] = "No audio provider resolves for this project; ask the user to configure one in settings."
    return ToolOutcome(value=value)


# ==================== generate_voice_sample ====================


class GenerateVoiceSampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    character: str = Field(min_length=1, description="Existing character name the sample is auditioned for")
    voice: str = Field(min_length=1, description="Voice ID from list_tts_voices; no default or narrator fallback")
    text: str = Field(
        min_length=1,
        description=(
            f"Exact text to synthesize, at most {voices.VOICE_SAMPLE_TEXT_MAX_LENGTH} characters; "
            "the result must last 2-10 seconds to be usable as reference audio"
        ),
    )
    preview: StrictBool = Field(
        default=False,
        description="true: validate and quote only, with no task or provider call; false: submit the paid sample",
    )


async def generate_voice_sample(
    request: ToolRequest[GenerateVoiceSampleRequest],
    scope: ProjectScope,
    caller: CallerContext,
    services: Services,
) -> ToolOutcome[Any]:
    value = request.value
    try:
        sample = await voices.prepare_voice_sample(
            scope.project_name,
            value.character,
            text=value.text,
            voice=value.voice,
            projects=services.projects,
            resolver=services.capabilities,
        )
        catalog = await voices.resolve_voice_catalog(scope.project_name, sample.project, resolver=services.capabilities)
        if catalog.voices and not catalog.has_voice(sample.voice):
            return tool_problem(
                f"Voice {sample.voice!r} is not offered by the project's audio backend {catalog.provider_id}/{catalog.model}.",
                code="voice_sample_voice_unknown",
                params={"voice": sample.voice, "available": [v.id for v in catalog.voices]},
            )
        quote = await voices.quote_voice_sample(
            provider_id=catalog.provider_id or sample.provider_id,
            model=catalog.model or "",
            text=sample.text,
            session_factory=services.sessions,
        )
        active_task_id = await _active_sample_task_id(services, scope, caller, sample.character)
        if value.preview:
            return ToolOutcome(value=_quote_value(sample, quote, active_task_id))
        if active_task_id is not None:
            # The queue keeps one active task per character; never attach a different request to it.
            return ToolOutcome(problem=_in_progress_problem(sample.character, active_task_id))

        spec = voices.voice_sample_task_spec(sample, source=caller.source)
        builder = GenerationResultBuilder(_GENERATE, GenerationSelectionMode.EXPLICIT)
        submitted = await submit_media_generation(
            scope=scope,
            caller=caller,
            services=services,
            operation=_GENERATE,
            preflight=builder.build(),
            pending_ids=[sample.character],
            specs=[spec],
        )
        not_queued = (
            any(member.unit_id == sample.character and member.task_id is None for member in submitted.batch.members)
            if submitted.failures is None
            else any(not failure.task_id for failure in submitted.failures)
        )
        if not_queued and (raced := await _active_sample_task_id(services, scope, caller, sample.character)):
            # A concurrent request with different text/voice won the per-character slot; the queue refused to attach.
            return ToolOutcome(problem=_in_progress_problem(sample.character, raced, batch_id=submitted.batch.batch_id))
        if submitted.successes is None or submitted.failures is None:
            return generation_batch_submission_outcome(submitted.batch)
        record_batch_outcomes(builder, successes=submitted.successes, failures=submitted.failures)
        return generation_result_outcome(
            builder.build(),
            batch_id=submitted.batch.batch_id,
            binds_reference=False,
            next_step="Audition with describe_media(kind=voice_sample) or inspect_voice_reference, then confirm_voice_sample.",
        )
    except ModelNotInCatalogError as exc:
        return ToolOutcome(problem=model_not_in_catalog_problem(exc))
    except ApiError as exc:
        return _api_problem(exc)
    except Exception as exc:
        return tool_error(_GENERATE, exc)


async def _active_sample_task_id(
    services: Services, scope: ProjectScope, caller: CallerContext, character: str
) -> str | None:
    active = await services.queue.get_active_tasks_for_resources(
        project_name=scope.project_name,
        task_type=voices.VOICE_SAMPLE_TASK_TYPE,
        resource_ids=[character],
        user_id=caller.user_id,
    )
    return str(active[0]["task_id"]) if active else None


def _in_progress_problem(character: str, task_id: str, *, batch_id: str | None = None) -> ToolProblem:
    params: dict[str, Any] = {"task_id": task_id}
    if batch_id is not None:
        params["batch_id"] = batch_id
    return ToolProblem(
        "voice_sample_in_progress",
        f"Character {character} already has an active voice sample task {task_id}; "
        "wait for it with list_voice_samples instead of submitting another.",
        action="wait_for_task",
        params=params,
    )


def _quote_value(
    sample: voices.PreparedVoiceSample, quote: voices.VoiceSampleQuote, active_task_id: str | None
) -> dict[str, Any]:
    cost = quote.to_payload()
    price = (
        f"{cost['amount']} {cost['currency']}"
        if cost["amount"] is not None
        else f"unpriced (reason: {cost['unpriced_reason']}); unknown, not free"
    )
    summary = (
        f"Voice sample quote for {sample.character}: voice {sample.voice} on {quote.provider_id}/{quote.model}, "
        f"{len(sample.text)} characters, {price}. No task was created."
    )
    if active_task_id:
        summary += f" An active sample task {active_task_id} already exists for this character."
    return {
        "voice_sample_quote": {
            "character": sample.character,
            "voice": sample.voice,
            "text": sample.text,
            "text_length": len(sample.text),
            "provider_id": quote.provider_id,
            "model": quote.model,
            "estimated_cost": cost,
            "active_task_id": active_task_id,
            "binds_reference": False,
            "reference_limits": voices.REFERENCE_LIMITS.to_payload(),
        },
        "summary": summary,
    }


# ==================== list_voice_samples ====================


class ListVoiceSamplesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    character: str | None = Field(default=None, description="Only samples for this character name; omit for all")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of samples, newest first")


def _cost_summary(calls: list[voices.SampleCost] | None) -> dict[str, Any]:
    if calls is None:
        return {"known": False, "reason": "usage_records_unavailable", "calls": []}
    totals: dict[str, float] = {}
    for call in calls:
        if call.amount is not None and call.currency is not None:
            totals[call.currency] = round(totals.get(call.currency, 0.0) + call.amount, 6)
    complete = all(call.amount is not None for call in calls)
    return {
        "known": bool(calls) and complete,
        "recorded_calls": len(calls),
        "totals": totals or None,
        "complete": complete,
        "calls": [call.to_payload() for call in calls],
        **({"reason": "no_provider_call_recorded"} if not calls else {}),
    }


def _sample_entry(
    task: Mapping[str, Any],
    facts: voices.SampleFileFacts,
    *,
    characters: Mapping[str, Any],
    bound: Mapping[str, str | None],
    costs: dict[str, list[voices.SampleCost]] | None,
) -> dict[str, Any]:
    payload = task.get("payload") or {}
    result = task.get("result") or {}
    character = str(task.get("resource_id") or "")
    key = resolve_asset_key(characters, character)
    bound_sha = bound.get(key) if key is not None else None
    status = task.get("status")
    entry: dict[str, Any] = {
        "task_id": task.get("task_id"),
        "character": character,
        "character_exists": key is not None,
        "status": status,
        "voice": payload.get("voice"),
        "text": payload.get("prompt"),
        "provider_id": result.get("provider_id") or task.get("provider_id"),
        "model": result.get("model"),
        "duration_seconds": result.get("duration_seconds"),
        "media": {
            "state": facts.state,
            "format": _suffix(result["file_path"]) if isinstance(result.get("file_path"), str) else None,
            "mime_type": facts.mime_type,
            "size_bytes": facts.size_bytes,
            "sha256": facts.sha256,
        },
        "cost": _cost_summary(None if costs is None else costs.get(str(task.get("task_id")), [])),
        "created_at": task.get("queued_at"),
        "finished_at": task.get("finished_at"),
        "bound": facts.sha256 is not None and facts.sha256 == bound_sha,
        "confirmable": status == "succeeded" and facts.state == "available" and key is not None,
    }
    if entry["model"] is None and costs:
        entry["model"] = next((c.model for c in costs.get(str(task.get("task_id")), [])), None)
    if status in {"failed", "cancelled"}:
        problem = problem_from_task_failure(task.get("error_message"), cancelled=status == "cancelled")
        entry["error"] = {"code": problem.code, "detail": problem.detail}
    return entry


async def list_voice_samples(
    request: ToolRequest[ListVoiceSamplesRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    del caller
    value = request.value
    try:
        if (problem := await migration_gate(scope, services)) is not None:
            return ToolOutcome(problem=problem)
        character = None
        if value.character is not None:
            try:
                character = validate_asset_name(value.character)
            except ValueError:
                return tool_problem(f"Invalid character name {value.character!r}", code="asset_invalid_name")
        tasks = await voices.list_voice_sample_tasks(
            scope.project_name, queue=services.queue, character=character, limit=value.limit
        )

        def _read() -> tuple[dict[str, Any], dict[str, str | None], list[voices.SampleFileFacts]]:
            project = services.projects.load_project(scope.project_name)
            project_dir = services.projects.get_project_path(scope.project_name)
            facts = [voices.sample_file_facts(project_dir, task) for task in tasks]
            return project, voices.bound_reference_digests(services.projects, scope.project_name), facts

        project, bound, facts = await asyncio.to_thread(_read)
        costs = await voices.load_sample_costs([str(t["task_id"]) for t in tasks], session_factory=services.sessions)
    except ApiError as exc:
        return _api_problem(exc)
    except Exception as exc:
        return tool_error("list_voice_samples", exc)
    raw_characters = project.get("characters")
    characters: Mapping[str, Any] = raw_characters if isinstance(raw_characters, dict) else {}
    samples = [
        _sample_entry(task, fact, characters=characters, bound=bound, costs=costs)
        for task, fact in zip(tasks, facts, strict=True)
    ]
    return ToolOutcome(
        value={
            "samples": samples,
            "characters_with_reference": sorted(name for name, digest in bound.items() if digest is not None),
        }
    )


# ==================== confirm_voice_sample ====================


class ConfirmVoiceSampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(min_length=1, description="task_id of a succeeded voice sample from list_voice_samples")
    character: str = Field(min_length=1, description="Character the sample was generated for")
    expected_reference_sha256: str | None = Field(
        default=None,
        pattern=_SHA256,
        description=(
            "sha256 of the reference currently bound, as last inspected; refuses if it changed meanwhile. "
            "Exactly one of this or expect_unbound is required"
        ),
    )
    expect_unbound: StrictBool = Field(
        default=False,
        description="true when the character had no reference when inspected; refuses if it gained one meanwhile",
    )

    @model_validator(mode="after")
    def _one_expectation(self) -> Self:
        # Default deny: binding must state what it replaces, so an approved reference is never overwritten blindly.
        if self.expect_unbound == (self.expected_reference_sha256 is not None):
            raise ValueError(
                "provide exactly one of expected_reference_sha256 (current bound reference, from inspect_voice_reference "
                "or list_voice_samples) or expect_unbound=true"
            )
        return self


async def confirm_voice_sample(
    request: ToolRequest[ConfirmVoiceSampleRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    del caller
    value = request.value
    try:
        saved = await voices.confirm_voice_sample(
            scope.project_name,
            value.character,
            value.task_id,
            projects=services.projects,
            queue=services.queue,
            source="worker",
            expected_reference_sha256=value.expected_reference_sha256,
            expect_unbound=value.expect_unbound,
            idempotent=True,
        )
    except ApiError as exc:
        return _api_problem(exc)
    except Exception as exc:
        return tool_error("confirm_voice_sample", exc)
    return ToolOutcome(
        value={
            "character": value.character,
            "task_id": value.task_id,
            "bound": True,
            "already_bound": saved.already_bound,
            "reference_sha256": saved.sha256,
            "format": _suffix(saved.path),
        }
    )


# ==================== inspect_voice_reference ====================


class InspectVoiceReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    character: str | None = Field(default=None, description="Inspect this character's currently bound reference audio")
    task_id: str | None = Field(default=None, description="Inspect this voice sample task's audio instead")
    transcribe: StrictBool = Field(
        default=False, description="Also run local blind ASR (no canonical text supplied; no downloads or paid APIs)"
    )
    language: str | None = Field(
        default=None, pattern=r"^[a-z]{2,3}$", description="Spoken language for ASR, e.g. pt; required with transcribe"
    )

    @model_validator(mode="after")
    def _one_subject(self) -> Self:
        if (self.character is None) == (self.task_id is None):
            raise ValueError("provide exactly one of character or task_id")
        if self.transcribe and self.language is None:
            raise ValueError("language is required when transcribe is true")
        return self


async def _measure(path: Path) -> dict[str, Any]:
    try:
        probe = await probe_media(path)
    except FfmpegUnavailableError:
        return {"available": False, "reason": "ffmpeg_unavailable"}
    except (MediaProbeError, OSError):
        return {"available": False, "reason": "media_unparseable"}
    audio = probe.first_stream("audio")
    return {
        "available": True,
        "container_formats": sorted(probe.container_formats),
        "audio_codec": audio.codec if audio is not None else None,
        "has_audio_stream": audio is not None,
        "has_video_stream": probe.first_stream("video") is not None,
        "duration_seconds": probe.duration_seconds,
    }


async def _transcribe(path: Path, language: str) -> dict[str, Any]:
    try:
        # Blind recognition: only the audio and the spoken language reach the recognizer, never the sample text.
        transcript = await asyncio.to_thread(transcribe_media, path, language=language)
    except AudioReviewUnavailable as exc:
        return {"available": False, "limitation": str(exc), "limits": _TRANSCRIPT_LIMITS}
    words = transcript.get("words") or []
    return {
        "available": True,
        "engine": transcript.get("engine"),
        "model_digest": transcript.get("model_digest"),
        "language": transcript.get("language"),
        "text": "".join(str(word.get("text", "")) for word in words).strip(),
        "words": words,
        "prompt_supplied": False,
        "limits": _TRANSCRIPT_LIMITS,
    }


def _within_limits(measurement: dict[str, Any], size_bytes: int) -> bool | None:
    duration = measurement.get("duration_seconds")
    if not measurement.get("available") or duration is None:
        return None
    limits = voices.REFERENCE_LIMITS
    return limits.min_seconds <= duration <= limits.max_seconds and size_bytes <= limits.max_bytes


async def inspect_voice_reference(
    request: ToolRequest[InspectVoiceReferenceRequest], scope: ProjectScope, caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    del caller
    value = request.value
    try:
        if (problem := await migration_gate(scope, services)) is not None:
            return ToolOutcome(problem=problem)
        task: dict[str, Any] | None = None
        if value.task_id is not None:
            task = voices.require_project_voice_sample_task(
                await services.queue.get_task(value.task_id), project_name=scope.project_name, task_id=value.task_id
            )
            relative = voices.sample_relative_path(task)
        else:
            assert value.character is not None
            pointer = await voices.character_reference_pointer(
                scope.project_name, value.character, projects=services.projects
            )
            if pointer is None:
                return ToolOutcome(value=_unbound(value.character))
            relative = pointer
        project_dir = await asyncio.to_thread(services.projects.get_project_path, scope.project_name)
        # Object-storage projects keep cleaned working files remotely: materialize (digest-verified) before reading.
        async with local_work_files(project_dir, [relative], session_factory=services.sessions):
            return await _inspect_local(value, scope, services, project_dir, task)
    except ApiError as exc:
        return _api_problem(exc)
    except Exception as exc:
        return tool_error("inspect_voice_reference", exc)


def _unbound(character: str) -> dict[str, Any]:
    return {
        "subject": "character_voice_reference",
        "character": character,
        "bound": False,
        "detail": "No reference audio is bound to this character, or its file is missing.",
    }


async def _inspect_local(
    value: InspectVoiceReferenceRequest,
    scope: ProjectScope,
    services: Services,
    project_dir: Path,
    task: dict[str, Any] | None,
) -> ToolOutcome[dict[str, Any]]:
    provenance: dict[str, Any]
    if task is not None:
        assert value.task_id is not None
        media = await voices.resolve_voice_sample_media(
            scope.project_name, value.task_id, projects=services.projects, queue=services.queue
        )
        provenance = _task_provenance(task)
        subject = "voice_sample"
    else:
        assert value.character is not None
        found = await voices.resolve_character_voice_reference_media(
            scope.project_name, value.character, projects=services.projects
        )
        if found is None:
            return ToolOutcome(value=_unbound(value.character))
        media = found
        provenance = await _reference_provenance(scope.project_name, media, services)
        subject = "character_voice_reference"
    bound_digests = await asyncio.to_thread(voices.bound_reference_digests, services.projects, scope.project_name)
    path = await asyncio.to_thread(safe_join, project_dir, media.relative_path)
    measurement = await _measure(path)
    bound_key = resolve_asset_key(bound_digests, media.character)
    result: dict[str, Any] = {
        "subject": subject,
        "character": media.character,
        "task_id": media.task_id,
        "media": {
            "format": _suffix(media.relative_path),
            "mime_type": media.mime_type,
            "size_bytes": media.size_bytes,
            "sha256": media.sha256,
            "version": media.version,
        },
        "measurement": measurement,
        "within_reference_limits": _within_limits(measurement, media.size_bytes),
        "reference_limits": voices.REFERENCE_LIMITS.to_payload(),
        "provenance": provenance,
        "bound": bound_key is not None and bound_digests.get(bound_key) == media.sha256,
    }
    if value.transcribe:
        assert value.language is not None
        result["transcript"] = await _transcribe(path, value.language)
    return ToolOutcome(value=result)


def _task_provenance(task: Mapping[str, Any]) -> dict[str, Any]:
    payload = task.get("payload") or {}
    result = task.get("result") or {}
    return {
        "source": "voice_sample_task",
        "task_id": task.get("task_id"),
        "voice": payload.get("voice"),
        "text": payload.get("prompt"),
        "provider_id": result.get("provider_id") or task.get("provider_id"),
        "model": result.get("model"),
        "recorded_duration_seconds": result.get("duration_seconds"),
        "created_at": task.get("queued_at"),
    }


async def _reference_provenance(project_name: str, media: voices.VoiceMedia, services: Services) -> dict[str, Any]:
    """Match the bound bytes to the sample task that produced them; uploads and unrecorded origins stay unknown."""
    tasks = await voices.list_voice_sample_tasks(project_name, queue=services.queue, character=media.character)
    for task in tasks:
        result = task.get("result") or {}
        if task.get("status") == "succeeded" and result.get("sha256") == media.sha256:
            return _task_provenance(task)
    return {"source": "unknown", "detail": "Not matched to a recorded voice sample (for example an uploaded file)."}
