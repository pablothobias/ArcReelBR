"""Speech review uses the native presentation transaction and records source-bound evidence."""

from pathlib import Path

import pytest

from lib.speech.audio_review import AudioReviewUnavailable
from server.media_tools import speech_review
from server.services.presentation.presentation_read_model import PresentationReadModelService
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolRequest
from tests.integration.server.services.presentation.test_presentation_read_model import (
    _SettingsResolver,
    _setup_narrator_project,
)


async def test_review_applies_timing_and_keeps_evidence_through_native_reader(tmp_path, monkeypatch):
    pm, path, settings = _setup_narrator_project(tmp_path)

    async def probe(_path: Path) -> float:
        return 6.25

    reader = PresentationReadModelService(
        pm,
        settings_resolver_factory=lambda _name, _path: _SettingsResolver(settings),
        duration_probe=probe,
    )
    monkeypatch.setattr(speech_review, "PresentationReadModelService", lambda _pm: reader)
    monkeypatch.setattr(
        speech_review,
        "transcribe_media",
        lambda _path, *, language: {
            "words": [
                {"text": "一", "start": 0.1, "end": 0.5, "probability": 0.99},
                {"text": "二二", "start": 0.6, "end": 1, "probability": 0.99},
            ],
        },
    )
    result = await speech_review.review_speech(
        ToolRequest(
            speech_review.ReviewSpeechRequest(unit_id="E1S01", language="zh", variant="use_tts", apply_timing=True)
        ),
        ProjectScope("demo", pm.data_root),
        CallerContext("test", "mcp"),
        Services(projects=pm, workflow_planner=None, capabilities=None, queue=None),
    )
    assert result.problem is None
    assert result.value["applied"] is True
    assert result.value["lip_sync"] == "not_assessed"
    assert len(list((path / "speech_reviews").glob("*.json"))) == 1
    reread = await reader.materialize_unit(
        project_name="demo",
        resource_type="videos",
        resource_id="E1S01",
        variant="use_tts",
    )
    assert reread.presentation.timing == "audio_measured"
    assert reread.presentation.subtitles[0].start_microseconds == 100_000


def test_missing_local_model_has_actionable_error_without_network(tmp_path, monkeypatch):
    monkeypatch.delenv("ARCREEL_SPEECH_REVIEW_MODEL", raising=False)
    with pytest.raises(AudioReviewUnavailable, match="ARCREEL_SPEECH_REVIEW_MODEL"):
        speech_review.transcribe_media(tmp_path / "missing.mp4", language="pt")
