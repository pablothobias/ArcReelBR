"""Real local float PCM decoding and immutable review evidence, without any provider calls."""

import array
import hashlib
import json
import subprocess
import wave

import pytest

from lib.infra.ffmpeg import ffmpeg_executable
from scripts.validate_av_review import float_pcm_evidence, inspect_media, validate_saved_review


def test_silent_wav_is_proven_zero_but_preserved_opposite_stereo_channels_are_not(tmp_path):
    for name, samples, expected in [("zero", [0, 0] * 100, "zero"), ("opposite", [10000, -10000] * 100, "nonzero")]:
        path = tmp_path / f"{name}.wav"
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(2)
            handle.setsampwidth(2)
            handle.setframerate(44100)
            handle.writeframes(array.array("h", samples).tobytes())
        evidence = inspect_media(path)
        assert evidence.pcm_state == expected
        assert evidence.has_audio
        assert not evidence.has_video
        assert evidence.decoded_streams[0]["sample_count_all_channels"] == 200


def test_quiet_float_audio_is_not_erased_by_integer_quantization(tmp_path):
    raw = tmp_path / "quiet.f64le"
    raw.write_bytes(array.array("d", [1e-12, -1e-12] * 100).tobytes())
    media = tmp_path / "quiet.wav"
    subprocess.run(
        [
            ffmpeg_executable(),
            "-v",
            "error",
            "-f",
            "f64le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-i",
            str(raw),
            "-c:a",
            "pcm_f64le",
            str(media),
        ],
        check=True,
    )
    result = inspect_media(media)
    assert result.pcm_state == "nonzero"
    assert result.decoded_streams[0]["sample_count_all_channels"] == 200


@pytest.mark.parametrize("values", [[], [float("nan")]])
def test_empty_or_nonfinite_pcm_is_unknown_not_zero(tmp_path, values):
    path = tmp_path / "samples.f64le"
    path.write_bytes(array.array("d", values).tobytes())
    assert float_pcm_evidence(path)["pcm_state"] == "unknown"


def test_saved_review_retains_raw_response_bytes_hash_and_original_source(tmp_path):
    media = tmp_path / "silence.wav"
    with wave.open(str(media), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 16000)
    response = tmp_path / "response.json"
    response.write_text(
        json.dumps(
            {
                "evidence_status": "observed",
                "speech": [
                    {
                        "speaker_label": "invented",
                        "start_seconds": 0,
                        "end_seconds": 0.5,
                        "words_heard": "invented speech",
                        "delivery_observation": "clear",
                        "confidence": 1,
                    }
                ],
                "actual_audio_description": "voice",
                "assessability_limits": [],
            }
        )
    )
    before = response.read_bytes()
    result = validate_saved_review(media, response, tmp_path / "evidence", evidence_refs=["provider-response:test"])
    assert result["validation_status"] == "rejected"
    assert result["findings"][0]["code"] == "speech_on_zero_pcm"
    assert result["raw_response_sha256"] == hashlib.sha256(before).hexdigest()
    assert (tmp_path / "evidence/raw-response.json").read_bytes() == before == response.read_bytes()
    assert result["evidence_refs"] == ["provider-response:test"]
    assert result["metered_service_calls"] == 0
    assert result["requires_reviewer"]


def test_video_without_audio_stays_no_audio_and_unreadable_input_stays_unknown(tmp_path):
    media = tmp_path / "silent-video.mp4"
    subprocess.run(
        [
            ffmpeg_executable(),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=32x32:r=10",
            "-t",
            "0.2",
            "-an",
            "-c:v",
            "libx264",
            str(media),
        ],
        check=True,
    )
    evidence = inspect_media(media)
    assert evidence.has_video
    assert evidence.has_audio is False
    assert evidence.pcm_state == "no_audio"
    assert evidence.decoded_streams == []
    invalid = tmp_path / "unreadable.bin"
    invalid.write_bytes(b"not a media file")
    failed = inspect_media(invalid)
    assert failed.has_audio is None
    assert failed.has_video is None
    assert failed.pcm_state == "unknown"


def test_formal_file_replacement_during_decode_cannot_relabel_frozen_evidence(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    replacement = tmp_path / "replacement.wav"
    for path, sample in [(source, 0), (replacement, 1000)]:
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(array.array("h", [sample] * 16000).tobytes())
    before = source.read_bytes()
    response = tmp_path / "response.json"
    response.write_text(
        json.dumps(
            {
                "evidence_status": "observed",
                "speech": [],
                "actual_audio_description": "No audible signal",
                "assessability_limits": [],
            }
        )
    )
    real_run = subprocess.run

    def replace_then_decode(*args, **kwargs):
        if replacement.exists():
            replacement.replace(source)
        return real_run(*args, **kwargs)

    monkeypatch.setattr("scripts.validate_av_review.subprocess.run", replace_then_decode)
    report = validate_saved_review(source, response, tmp_path / "evidence", evidence_refs=[])
    assert report["media_evidence"]["pcm_state"] == "zero"
    assert report["media_sha256"] == hashlib.sha256(before).hexdigest()
    assert (tmp_path / "evidence/inspected-input.wav").read_bytes() == before
    assert source.read_bytes() != before
    assert report["requires_reviewer"]
