"""Actual decoded PCM and missing-audio evidence, without a transcription-model dependency."""

import subprocess
import wave

import pytest

from lib.infra.ffmpeg import ffmpeg_executable
from scripts.inspect_audio_evidence import inspect_audio, pcm_evidence


def test_actual_silent_pcm_is_distinguishable_from_missing_transcript(tmp_path):
    audio = tmp_path / "silence.wav"
    with wave.open(str(audio), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(b"\x00\x00" * 16000)
    evidence = pcm_evidence(audio)
    assert evidence == {"sample_rate": 16000, "duration_seconds": 1, "peak_amplitude": 0, "rms_amplitude": 0}


def test_actual_video_without_audio_reports_missing_evidence_before_asr(tmp_path):
    video = tmp_path / "silent.mp4"
    subprocess.run(
        [
            ffmpeg_executable(),
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=32x32:d=0.2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
        capture_output=True,
    )
    model = tmp_path / "unused-model.bin"
    model.write_bytes(b"not loaded when no audio exists")
    evidence = inspect_audio(video, model, tmp_path / "evidence", [], whisper="unavailable-whisper")
    assert evidence["has_video"] is True
    assert evidence["findings"] == ["audio_stream_missing"]
    assert evidence["segments"] == []
    assert evidence["review_status"] == "requires_review"
    with pytest.raises(FileExistsError):
        inspect_audio(video, model, tmp_path / "evidence", [])
