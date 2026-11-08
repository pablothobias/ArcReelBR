"""Validate saved review evidence offline; never generate media or grant audiovisual acceptance."""

from __future__ import annotations

import argparse
import array
import asyncio
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from lib.infra.ffmpeg import FfmpegUnavailableError, ffmpeg_executable, local_file_input
from lib.infra.media_probe import MediaProbeError, probe_media


class Speech(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker_label: str
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    end_seconds: float = Field(gt=0, allow_inf_nan=False)
    words_heard: str = Field(min_length=1)
    delivery_observation: str
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered(self) -> Speech:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Speech must end after it starts")
        return self


class AudioReview(BaseModel):
    """Audio-only responses have no visual or mouth-synchrony fields."""

    model_config = ConfigDict(extra="forbid")
    evidence_status: Literal["observed", "insufficient_evidence"]
    speech: list[Speech]
    actual_audio_description: str
    assessability_limits: list[str]


class Subtitle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    approximate_start_seconds: float = Field(ge=0, allow_inf_nan=False)
    approximate_end_seconds: float = Field(gt=0, allow_inf_nan=False)
    overlaps_heard_speech: Literal["yes", "no", "uncertain"]

    @model_validator(mode="after")
    def ordered(self) -> Subtitle:
        if self.approximate_end_seconds <= self.approximate_start_seconds:
            raise ValueError("Subtitle must end after it starts")
        return self


class Synchrony(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["apparently_aligned", "apparently_offset", "insufficient_evidence"]
    explanation: str
    estimated_offset_ms: float | None = Field(allow_inf_nan=False)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)


class VideoReview(AudioReview):
    actual_visual_description: str
    visible_words: list[str]
    subtitles: list[Subtitle]
    audiovisual_synchrony: Synchrony


class MediaEvidence(BaseModel):
    """Actual modality and decoded-signal evidence; unknown is never silent."""

    has_audio: bool | None = None
    has_video: bool | None = None
    duration_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pcm_state: Literal["zero", "nonzero", "unknown", "no_audio"] = "unknown"
    decoded_streams: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


def validate_review(raw: object, evidence: MediaEvidence) -> dict[str, Any]:
    """Check shape, known modality, zero PCM and time bounds; all prose still needs review."""
    findings: list[dict[str, str]] = []
    missing = []
    contract = VideoReview if evidence.has_video is True else AudioReview
    if evidence.has_video is None:
        missing.append("video_modality_unknown")
    if evidence.has_audio is False:
        missing.append("audio_stream_absent")
    if evidence.has_audio is None or evidence.pcm_state == "unknown":
        missing.append("audio_evidence_unknown")
    if any(stream.get("pcm_state") == "unknown" for stream in evidence.decoded_streams):
        missing.append("audio_decode_incomplete")
    if evidence.duration_seconds is None:
        missing.append("media_duration_unknown")
    parsed: AudioReview | None = None
    try:
        parsed = (
            TypeAdapter(AudioReview | VideoReview).validate_python(raw)
            if evidence.has_video is None
            else contract.model_validate(raw)
        )
    except ValidationError as exc:
        findings.extend(
            {"code": "response_contract_invalid", "path": ".".join(map(str, issue["loc"])), "detail": issue["type"]}
            for issue in exc.errors(include_input=False, include_url=False)
        )
    if parsed is not None:
        if parsed.evidence_status == "insufficient_evidence":
            missing.append("evaluator_reported_insufficient_evidence")
        if parsed.speech and (evidence.has_audio is False or evidence.pcm_state == "no_audio"):
            findings.append(
                {"code": "speech_without_audio_stream", "path": "speech", "detail": "No audio stream exists"}
            )
        if parsed.speech and evidence.pcm_state == "zero":
            findings.append(
                {"code": "speech_on_zero_pcm", "path": "speech", "detail": "All decoded audio samples are zero"}
            )
        intervals = [(f"speech.{index}", speech.end_seconds) for index, speech in enumerate(parsed.speech)]
        if isinstance(parsed, VideoReview):
            intervals.extend(
                (f"subtitles.{index}", cue.approximate_end_seconds) for index, cue in enumerate(parsed.subtitles)
            )
            sync = parsed.audiovisual_synchrony
            if sync.status != "insufficient_evidence" and (
                evidence.has_audio is False or evidence.pcm_state in {"zero", "no_audio"}
            ):
                findings.append(
                    {
                        "code": "synchrony_without_sound",
                        "path": "audiovisual_synchrony",
                        "detail": "No audible signal can support mouth/speech synchrony",
                    }
                )
        if evidence.duration_seconds is not None:
            for path, end in intervals:
                if end > evidence.duration_seconds:
                    findings.append(
                        {
                            "code": "timestamp_outside_media",
                            "path": path,
                            "detail": "Reported end exceeds actual media duration",
                        }
                    )
    return {
        "validation_status": "rejected"
        if findings
        else "insufficient_evidence"
        if missing
        else "consistent_requires_review",
        "response_contract": contract.__name__ if evidence.has_video is not None else "modality_unverified",
        "findings": findings,
        "missing_evidence": missing,
        "requires_reviewer": True,
        "automatic_quality_pass": False,
        "limitations": [
            "Only structured claims are checked; free prose, identity, acting and subjective quality remain unverified.",
            "Nonzero PCM is not proof of speech. Sampling and model confidence do not prove lip-sync.",
            "Rejection establishes an evidence/validation contradiction, not the cause of provider generation.",
        ],
    }


def float_pcm_evidence(path: Path) -> dict[str, Any]:
    """Read interleaved float64 samples without downmixing, resampling or integer quantization."""
    samples = 0
    nonzero = False
    finite = True
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 8192):
            digest.update(chunk)
            if len(chunk) % 8:
                raise ValueError("Incomplete float64 PCM sample")
            values = array.array("d")
            values.frombytes(chunk)
            if sys.byteorder != "little":
                values.byteswap()
            samples += len(values)
            nonzero |= any(value != 0 for value in values)
            finite &= all(math.isfinite(value) for value in values)
    return {
        "sample_count_all_channels": samples,
        "all_samples_finite": finite,
        "pcm_state": "unknown" if not samples or not finite else "nonzero" if nonzero else "zero",
        "decoded_sha256": digest.hexdigest(),
    }


def inspect_media(media: Path) -> MediaEvidence:
    """Probe and decode all audio streams at native rates/channels using bundled ffmpeg."""
    try:
        probe = asyncio.run(probe_media(media))
    except (OSError, MediaProbeError, FfmpegUnavailableError) as exc:
        return MediaEvidence(findings=[f"probe_failed:{type(exc).__name__}"])
    audio_streams = [stream for stream in probe.streams if stream.kind == "audio"]
    result = MediaEvidence(
        has_audio=bool(audio_streams),
        has_video=probe.first_stream("video") is not None,
        duration_seconds=probe.duration_seconds if probe.duration_seconds and probe.duration_seconds > 0 else None,
        pcm_state="unknown" if audio_streams else "no_audio",
    )
    with tempfile.TemporaryDirectory(prefix="arcreel-review-pcm-") as directory:
        for index, _stream in enumerate(audio_streams):
            decoded = Path(directory) / f"audio-{index}.f64le"
            try:
                subprocess.run(
                    [
                        ffmpeg_executable(),
                        "-nostdin",
                        "-v",
                        "error",
                        *local_file_input(media),
                        "-map",
                        f"0:a:{index}",
                        "-vn",
                        "-c:a",
                        "pcm_f64le",
                        "-f",
                        "f64le",
                        str(decoded),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
                result.decoded_streams.append({"audio_stream": index, **float_pcm_evidence(decoded)})
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                result.decoded_streams.append({"audio_stream": index, "pcm_state": "unknown"})
                result.findings.append(f"decode_failed:{type(exc).__name__}")
    states = [stream["pcm_state"] for stream in result.decoded_streams]
    if states:
        result.pcm_state = (
            "nonzero" if "nonzero" in states else "zero" if all(state == "zero" for state in states) else "unknown"
        )
    return result


def response_payload(saved: object) -> object:
    """Extract JSON text from a saved GenerateContent response, or accept a saved review object."""
    if isinstance(saved, dict) and "candidates" in saved:
        parts = saved["candidates"][0]["content"]["parts"]
        return json.loads("".join(part.get("text", "") for part in parts if not part.get("thought")))
    return saved


def validate_saved_review(media: Path, response: Path, output: Path, *, evidence_refs: list[str]) -> dict[str, Any]:
    media = media.resolve(strict=True)
    response = response.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=False)
    raw = response.read_bytes()
    (output / "raw-response.json").write_bytes(raw)
    snapshot = output / f"inspected-input{media.suffix}"
    with media.open("rb") as source, snapshot.open("xb") as frozen:
        shutil.copyfileobj(source, frozen)
    evidence = inspect_media(snapshot)
    try:
        result = validate_review(response_payload(json.loads(raw)), evidence)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        result = {
            "validation_status": "rejected",
            "findings": [{"code": "saved_response_unreadable", "detail": type(exc).__name__}],
            "requires_reviewer": True,
            "automatic_quality_pass": False,
        }
    with snapshot.open("rb") as handle:
        media_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        **result,
        "media": str(media),
        "inspected_media": str(snapshot.resolve()),
        "media_sha256": media_hash,
        "raw_response": str((output / "raw-response.json").resolve()),
        "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
        "evidence_refs": evidence_refs,
        "media_evidence": evidence.model_dump(mode="json"),
        "metered_service_calls": 0,
    }
    (output / "validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New private evidence directory")
    parser.add_argument("--evidence-ref", action="append", default=[])
    args = parser.parse_args()
    result = validate_saved_review(args.media, args.response, args.output, evidence_refs=args.evidence_ref)
    print(args.output / "validation.json")
    return 2 if result["validation_status"] == "rejected" else 0


if __name__ == "__main__":
    raise SystemExit(main())
