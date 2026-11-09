"""Local blind speech recognition and conservative canonical-text timing admission."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import threading
import unicodedata
import wave
from pathlib import Path
from typing import Any

import numpy as np

from lib.infra.ffmpeg import ffmpeg_executable, local_file_input
from lib.speech.measured_timing import MeasuredSubtitleTiming
from lib.speech.speech_presentation import SpeechPresentation

_RECOGNITION_LOCK = threading.Lock()


class AudioReviewUnavailable(RuntimeError):
    """Local recognition needs explicit installation/configuration; never fall back to paid APIs."""


def tokens(text: str) -> list[str]:
    """Ignore punctuation/case only; preserve accents, words, numbers and negation."""
    return re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())


def transcribe_media(path: Path, *, language: str) -> dict[str, Any]:
    """Recognize actual audio only. Models must already exist locally; no network/downloads."""
    model_path = os.environ.get("ARCREEL_SPEECH_REVIEW_MODEL", "")
    if not model_path or not Path(model_path).is_dir():
        raise AudioReviewUnavailable("Set ARCREEL_SPEECH_REVIEW_MODEL to a local faster-whisper model directory.")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise AudioReviewUnavailable("Install the speech-review extra: uv sync --extra speech-review") from exc
    # Serialize CPU inference to bound local resource use. The disposable WAV never leaves this call.
    with _RECOGNITION_LOCK, tempfile.TemporaryDirectory(prefix="arcreel-speech-") as temporary:
        wav = Path(temporary) / "audio.wav"
        extraction = subprocess.run(
            [
                ffmpeg_executable(),
                "-nostdin",
                "-v",
                "error",
                *local_file_input(path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-t",
                "120",
                str(wav),
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if extraction.returncode:
            raise AudioReviewUnavailable("Audio stream could not be decoded; inspect the selected media.")
        model = WhisperModel(model_path, device="cpu", compute_type="int8", cpu_threads=4, local_files_only=True)
        with wave.open(str(wav), "rb") as source:
            samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        segments, info = model.transcribe(
            samples,
            language=language,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=None,
            temperature=0,
            beam_size=5,
        )
        words = [
            {"text": word.word, "start": word.start, "end": word.end, "probability": word.probability}
            for segment in segments
            for word in (segment.words or [])
        ]
        model_digest = hashlib.sha256()
        for name in ("model.bin", "config.json", "tokenizer.json"):
            with (Path(model_path) / name).open("rb") as handle:
                while block := handle.read(1024 * 1024):
                    model_digest.update(block)
        return {
            "engine": "faster-whisper",
            "model_digest": model_digest.hexdigest(),
            "language": info.language,
            "words": words,
            "prompt_supplied": False,
        }


def assess_speech(presentation: SpeechPresentation, transcript: dict[str, Any]) -> dict[str, Any]:
    """Return evidence and candidate intervals; exact words and reliable bounds are required."""
    expected = [token for cue in presentation.subtitles for token in tokens(cue.text)]
    observed: list[str] = []
    timed: list[tuple[int, int]] = []
    valid = True
    previous_end = 0
    track = presentation.narration_audio or presentation.video
    boundary = track.duration_microseconds
    for word in transcript["words"]:
        parts = tokens(word["text"])
        start, end, probability = word["start"], word["end"], word["probability"]
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in (start, end, probability)
        ):
            valid = False
            continue
        a, b = round(start * 1_000_000), round(end * 1_000_000)
        if not previous_end <= a < b <= boundary or probability < 0.7 or len(parts) != 1:
            valid = False
        observed.extend(parts)
        timed.extend([(a, b)] * len(parts))
        previous_end = b
    matches = expected == observed
    eligible = matches and valid and bool(expected)
    intervals: list[list[int]] = []
    offset = 0
    if eligible:
        for cue in presentation.subtitles:
            count = len(tokens(cue.text))
            if not count:
                eligible = False
                break
            intervals.append([timed[offset][0], timed[offset + count - 1][1]])
            offset += count
    # Muted native audio cannot be used to time a post-production voiceover.
    audible = presentation.narration_audio is not None or presentation.video.audio_enabled
    eligible = eligible and audible
    source_basis = (presentation.timing_policy or {}).get("source_basis", presentation.subtitle_basis.digest)
    report = {
        "schema_version": 1,
        "unit_id": presentation.unit_id,
        "source_basis": source_basis,
        "media_digest": track.media.evidence.content_digest,
        "expected_text": [cue.text for cue in presentation.subtitles],
        "transcript": transcript,
        "text_match": matches,
        "voice_review": "no_speech_detected" if not observed else ("text_matches" if matches else "text_mismatch"),
        "lip_sync": "not_assessed",
        "vocal_performance": "not_assessed",
        "timing_eligible": eligible,
        "intervals": intervals if eligible else [],
        "limitations": [
            "ASR word times are estimates, not phoneme-level lip-sync verification.",
            "Recognition does not establish acting quality or speaker identity.",
        ],
    }
    if not expected and not observed:
        report["timing_status"] = "not_applicable_no_speech"
    elif not audible:
        report["timing_blocker"] = "selected_presentation_mutes_native_audio"
    elif not matches:
        report["timing_blocker"] = "transcript_differs_from_canonical_speech"
    elif not eligible:
        report["timing_blocker"] = "missing_or_uncertain_word_boundaries"
    return report


def timing_from_report(report: dict[str, Any]) -> MeasuredSubtitleTiming:
    if report.get("timing_eligible") is not True:
        raise ValueError("speech evidence does not admit measured subtitles")
    digest = "sha256-v1:" + hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return MeasuredSubtitleTiming(report["source_basis"], tuple(tuple(p) for p in report["intervals"]), digest)
