"""Review selected native presentation audio and optionally apply source-bound subtitle timing."""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from lib.infra.async_thread import run_sync_transaction
from lib.infra.json_io import atomic_write_json
from lib.infra.path_safety import safe_join
from lib.project.project_manager import is_reference_video_project
from lib.speech.audio_review import AudioReviewUnavailable, assess_speech, timing_from_report, transcribe_media
from lib.speech.speech_artifact_provenance import media_content_digest
from lib.speech.speech_presentation import SpeechPresentation
from server.media_tools.context import tool_error, tool_problem
from server.services.presentation.presentation_read_model import (
    PresentationReadModelService,
    PresentationUnavailableError,
)
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolRequest


class ReviewSpeechRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    unit_id: str = Field(min_length=1, description="Video-unit ID to review")
    version: StrictInt | None = Field(default=None, ge=1, description="Video version; omit for current selection")
    variant: Literal["post_production", "use_tts"] = Field(
        default="post_production", description="Native video or selected narration presentation"
    )
    language: str = Field(
        pattern=r"^[a-z]{2,3}$", description="Actual spoken language, e.g. pt; never a transcript prompt"
    )
    apply_timing: StrictBool = Field(
        default=False,
        description=(
            "Commit new eligible measured timing to the current native presentation when true. "
            "False preserves still-valid measured timing but does not make inspection read-only."
        ),
    )


async def review_speech(
    request: ToolRequest[ReviewSpeechRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[dict[str, Any]]:
    value = request.value
    try:
        project = await asyncio.to_thread(services.projects.load_project, scope.project_name)
        project_path = await asyncio.to_thread(services.projects.get_project_path, scope.project_name)
        resource_type = "reference_videos" if is_reference_video_project(project) else "videos"
        reader = PresentationReadModelService(services.projects)
        materialized = await reader.materialize_unit(
            project_name=scope.project_name,
            resource_type=resource_type,
            resource_id=value.unit_id,
            variant=value.variant,
            video_version=value.version,
        )
        presentation = materialized.presentation
        if not isinstance(presentation, SpeechPresentation):
            return tool_problem(
                "Speech provenance is unavailable for this media.", code="speech_provenance_unavailable"
            )
        track = presentation.narration_audio or presentation.video
        if track.duration_microseconds > 120_000_000:
            return tool_problem(
                "Review supports individual units up to 120 seconds.", code="speech_review_duration_limit"
            )
        media_path = await asyncio.to_thread(safe_join, project_path, track.media.artifact_path)
        transcript = await asyncio.to_thread(transcribe_media, media_path, language=value.language)
        digest = await asyncio.to_thread(media_content_digest, media_path)
        if digest != track.media.evidence.content_digest:
            return tool_problem("Selected media changed during recognition; retry review.", code="speech_review_stale")
        report = assess_speech(presentation, transcript)
        report["applied"] = False
        if value.apply_timing and report["timing_eligible"]:
            if presentation.selection != "current":
                return tool_problem(
                    "Select this version before applying measured timing.", code="speech_review_historical"
                )
            policy = timing_from_report(report)

            # Preserve evidence before committing canonical presentation files. It is immutable by digest.
            def save_evidence() -> None:
                evidence_path = safe_join(project_path, f"speech_reviews/{policy.evidence_digest.split(':')[-1]}.json")
                evidence_path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_json(evidence_path, report)

            await run_sync_transaction(save_evidence)
            updated = await reader.materialize_unit(
                project_name=scope.project_name,
                resource_type=resource_type,
                resource_id=value.unit_id,
                variant=value.variant,
                measured_timing=policy,
            )
            report["applied"] = True
            report["presentation"] = updated.to_dict()
        return ToolOutcome(value=report)
    except AudioReviewUnavailable as exc:
        return tool_problem(str(exc), code="speech_review_unavailable")
    except PresentationUnavailableError as exc:
        return tool_problem(str(exc), code="speech_review_unavailable")
    except Exception as exc:
        return tool_error("review_speech", exc)
