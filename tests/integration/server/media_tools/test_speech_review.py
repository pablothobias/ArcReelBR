"""Speech review uses the native presentation transaction and records source-bound evidence."""

import hashlib
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from lib.speech.audio_review import AudioReviewUnavailable
from server.media_tools import speech_review
from server.services.presentation.presentation_read_model import PresentationReadModelService
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolRequest
from tests.factories import make_test_video, wav_bytes
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


@pytest.mark.parametrize("previously_measured", [False, True])
@pytest.mark.parametrize("asr_available", [False, True])
async def test_inspection_materializes_and_preserves_eligible_timing(
    tmp_path, monkeypatch, previously_measured, asr_available
):
    video = tmp_path / "fixture.mp4"
    make_test_video(video, duration_sec=3)
    pm, path, settings = _setup_narrator_project(tmp_path, video_bytes=video.read_bytes(), audio_bytes=wav_bytes(4.5))
    pm.update_project(
        "demo",
        lambda p: p.update(
            {
                "audio_backend": f"{settings.provider_id}/{settings.model_id}",
                "narration_voice": settings.voice,
                "narration_speed": settings.speed,
            }
        ),
    )
    model = tmp_path / "synthetic-whisper-model"
    model.mkdir()
    for filename in ("model.bin", "config.json", "tokenizer.json"):
        (model / filename).write_bytes(b"synthetic-test-model")

    class Whisper:
        def __init__(self, model_path, **options):
            assert Path(model_path) == model
            assert options["local_files_only"] is True

        def transcribe(self, samples, **options):
            assert options["language"] == "zh"
            assert options["initial_prompt"] is None
            words = [
                SimpleNamespace(word="一", start=0.1, end=0.5, probability=0.99),
                SimpleNamespace(word="二二", start=0.6, end=1.0, probability=0.99),
            ]
            return [SimpleNamespace(words=words)], SimpleNamespace(language="zh")

    whisper_module = ModuleType("faster_whisper")
    whisper_module.WhisperModel = Whisper
    monkeypatch.setitem(sys.modules, "faster_whisper", whisper_module)
    monkeypatch.setenv("ARCREEL_SPEECH_REVIEW_MODEL", str(model))
    scope = ProjectScope("demo", pm.data_root)
    caller = CallerContext("test", "mcp")
    services = Services.defaults(pm)

    async def review(apply_timing):
        return await speech_review.review_speech(
            ToolRequest(
                speech_review.ReviewSpeechRequest(
                    unit_id="E1S01", language="zh", variant="use_tts", apply_timing=apply_timing
                )
            ),
            scope,
            caller,
            services,
        )

    if previously_measured:
        applied = await review(True)
        assert applied.problem is None
        assert applied.value["applied"] is True
    if not asr_available:
        monkeypatch.delenv("ARCREEL_SPEECH_REVIEW_MODEL", raising=False)

    def snapshot():
        return {
            str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*")
            if p.is_file() and p.suffix in {".json", ".mp4", ".wav"}
        }

    before = snapshot()
    evidence_before = set((path / "speech_reviews").glob("*.json"))
    result = await review(False)
    after = snapshot()
    if asr_available:
        assert result.problem is None
        assert result.value["applied"] is False
    else:
        assert result.problem.code == "speech_review_unavailable"
    assert list((path / "presentations").rglob("*.json"))
    subtitle_files = list((path / "subtitles").rglob("*.json"))
    assert len(subtitle_files) == 1
    subtitle = json.loads(subtitle_files[0].read_text())
    assert subtitle["timing"] == ("audio_measured" if previously_measured else "mechanical")
    if previously_measured:
        assert before == after
    else:
        assert any(p.startswith("presentations/") for p in after.keys() - before.keys())
        assert any(p.startswith("subtitles/") for p in after.keys() - before.keys())
        assert after[".arcreel_artifacts.json"] != before[".arcreel_artifacts.json"]
    for name in before:
        if name.startswith(("scripts/", "videos/", "audio/", "speech_reviews/")) or name == "project.json":
            assert after[name] == before[name]
    assert set((path / "speech_reviews").glob("*.json")) == evidence_before
    await review(False)
    assert snapshot() == after
