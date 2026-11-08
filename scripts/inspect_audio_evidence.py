"""Collect local speech evidence without generating or modifying production media.

Run with ``uv run python -m scripts.inspect_audio_evidence --help``. Whisper is
an optional external local executable. Its transcript is evidence to review,
never proof of correct speech, voice, lip-sync or subtitle alignment.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from lib.infra.ffmpeg import ffmpeg_executable, local_file_input
from lib.infra.media_probe import probe_media


class ExpectedSpeech(BaseModel):
    segment_id: str = Field(min_length=1)
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def ordered(self) -> ExpectedSpeech:
        if self.end <= self.start:
            raise ValueError("Speech interval must end after it starts")
        return self


def normalized_words(text: str) -> list[str]:
    """Ignore case and punctuation, retaining Portuguese accents and word order."""
    return re.findall(r"\w+", text.casefold())


def compare_evidence(
    expected: list[ExpectedSpeech], transcript: dict[str, Any], subtitle_cues: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Report discrepancies and missing evidence without assigning audiovisual passes.

    Whisper offsets are approximate segment timestamps. Cues use the existing
    SubtitleCue.to_dict shape, with global timeline microseconds. Timing checks
    compare the complete utterance envelope, not individual word alignment.
    """
    spans = transcript.get("transcription", [])
    results = []
    for item in expected:
        matches = [
            span
            for span in spans
            if span["offsets"]["from"] / 1000 < item.end and span["offsets"]["to"] / 1000 > item.start
        ]
        observed = " ".join(span["text"].strip() for span in matches)
        findings = []
        if not normalized_words(observed):
            findings.append("speech_evidence_missing")
        elif normalized_words(observed) != normalized_words(item.text):
            findings.append("transcript_mismatch_requires_listening")
        if subtitle_cues is None:
            findings.append("subtitle_timing_evidence_missing")
        else:
            # Compare matching text anywhere on the timeline so a shifted cue is not mistaken for absent evidence.
            cues = [cue for cue in subtitle_cues if normalized_words(str(cue["text"])) == normalized_words(item.text)]
            if len(cues) != 1 or not matches:
                findings.append("subtitle_alignment_evidence_ambiguous")
            else:
                cue_start = cues[0]["start_microseconds"] / 1_000_000
                cue_end = cue_start + cues[0]["duration_microseconds"] / 1_000_000
                speech_start = min(span["offsets"]["from"] for span in matches) / 1000
                speech_end = max(span["offsets"]["to"] for span in matches) / 1000
                if cue_end <= speech_start or cue_start >= speech_end:
                    findings.append("subtitle_has_no_overlap_with_transcribed_speech")
                elif abs(cue_start - speech_start) > 0.5 or abs(cue_end - speech_end) > 0.5:
                    findings.append("subtitle_boundary_discrepancy_requires_review")
        results.append(
            {
                **item.model_dump(),
                "observed_transcript": observed,
                "transcription_spans": matches,
                "findings": findings,
                "review_status": "requires_review",
                "correction_routes": [
                    "Re-read the approved script and artifact versions before any correction.",
                    "Use patch_episode_script only for an intended script correction; preserve approved speech.",
                    "Use read_timeline/edit_timeline for supported trim, placement or source-volume corrections.",
                    "Per-word subtitle retiming and lip-sync are not established correction capabilities.",
                ],
            }
        )
    return results


def pcm_evidence(path: Path) -> dict[str, Any]:
    """Measure decoded PCM, independently of ASR hallucinations on silence."""
    with wave.open(str(path), "rb") as audio:
        frames = audio.readframes(audio.getnframes())
        rate = audio.getframerate()
    values = [int.from_bytes(frames[i : i + 2], "little", signed=True) for i in range(0, len(frames), 2)]
    return {
        "sample_rate": rate,
        "duration_seconds": len(values) / rate,
        "peak_amplitude": max((abs(value) for value in values), default=0) / 32768,
        "rms_amplitude": math.sqrt(sum(value * value for value in values) / max(len(values), 1)) / 32768,
    }


def inspect_audio(
    media: Path,
    model: Path,
    output: Path,
    expected: list[ExpectedSpeech],
    *,
    subtitle_cues: list[dict[str, Any]] | None = None,
    whisper: str = "whisper-cli",
) -> dict[str, Any]:
    """Decode actual local media and run local Portuguese ASR without an expected-text prompt."""
    media = media.resolve(strict=True)
    model = model.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=False)
    probe = asyncio.run(probe_media(media))
    report: dict[str, Any] = {
        "media": str(media),
        "sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
        "has_video": probe.first_stream("video") is not None,
        "duration_seconds": probe.duration_seconds,
        "metered_service_calls": 0,
        "review_status": "requires_review",
        "limitations": [
            "ASR may hallucinate, mistranscribe or misplace timestamps; listen to discrepancies.",
            "No judgement of speaker identity, voice quality, emotion, continuity or lip-sync is automated.",
            "Subtitle cue metadata is not evidence of visible burned subtitles; inspect playback separately.",
        ],
    }
    if probe.first_stream("audio") is None:
        return {**report, "findings": ["audio_stream_missing"], "segments": []}
    audio_path = output / "audio.wav"
    subprocess.run(
        [
            ffmpeg_executable(),
            "-nostdin",
            "-v",
            "error",
            "-y",
            *local_file_input(media),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    prefix = output / "transcript"
    subprocess.run(
        [
            whisper,
            "-m",
            str(model),
            "-f",
            str(audio_path),
            "-l",
            "pt",
            "-ojf",
            "-of",
            str(prefix),
            "-ng",
            "-np",
        ],
        check=True,
        capture_output=True,
        timeout=600,
    )
    transcript_path = prefix.with_suffix(".json")
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    pcm = pcm_evidence(audio_path)
    return {
        **report,
        "audio": {"path": str(audio_path.resolve()), **pcm},
        "transcript": str(transcript_path.resolve()),
        "language": transcript.get("result", {}).get("language"),
        "findings": ["decoded_audio_is_silent"] if pcm["peak_amplitude"] == 0 else [],
        "segments": compare_evidence(expected, transcript, subtitle_cues),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument(
        "--expected", required=True, type=Path, help="JSON list of segment_id/start/end/text expectations"
    )
    parser.add_argument(
        "--subtitle-cues", type=Path, help="Optional JSON list of existing SubtitleCue.to_dict evidence"
    )
    parser.add_argument("--output", required=True, type=Path, help="Dedicated local evidence directory")
    parser.add_argument("--whisper", default="whisper-cli")
    args = parser.parse_args()
    expected = [ExpectedSpeech.model_validate(item) for item in json.loads(args.expected.read_text(encoding="utf-8"))]
    cues = json.loads(args.subtitle_cues.read_text(encoding="utf-8")) if args.subtitle_cues else None
    report = inspect_audio(args.media, args.model, args.output, expected, subtitle_cues=cues, whisper=args.whisper)
    report_path = args.output / "review.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
