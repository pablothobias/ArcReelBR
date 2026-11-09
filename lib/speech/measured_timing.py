"""Source-bound subtitle timing, without changing canonical speech or ownership."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lib.speech.speech_artifact_provenance import SubtitleUtteranceEvidence
from lib.speech.speech_presentation import SubtitleCue


@dataclass(frozen=True, slots=True)
class MeasuredSubtitleTiming:
    """Intervals verified against a mechanical basis (text, ownership and actual media)."""

    source_basis: str
    intervals: tuple[tuple[int, int], ...]
    evidence_digest: str

    @property
    def basis_identity(self) -> dict[str, object]:
        return {
            "kind": "audio-measured",
            "version": 1,
            "source_basis": self.source_basis,
            "intervals": [list(pair) for pair in self.intervals],
            "evidence_digest": self.evidence_digest,
        }

    def distribute(
        self, utterances: tuple[SubtitleUtteranceEvidence, ...], *, boundary_microseconds: int
    ) -> tuple[SubtitleCue, ...]:
        if len(utterances) != len(self.intervals):
            raise ValueError("measured intervals must cover every canonical utterance")
        cues: list[SubtitleCue] = []
        previous_end = 0
        for utterance, (start, end) in zip(utterances, self.intervals, strict=True):
            if (
                type(start) is not int
                or type(end) is not int
                or not previous_end <= start < end <= boundary_microseconds
            ):
                raise ValueError("measured intervals must be ordered, non-overlapping and inside the media")
            cues.append(SubtitleCue(start, end - start, utterance.text, utterance.owner, utterance.speaker))
            previous_end = end
        return tuple(cues)


def measured_policy(raw: Any) -> MeasuredSubtitleTiming | None:
    """Parse persisted policy strictly; unknown/corrupt policies are never accepted."""
    if raw is None:
        return None
    if not isinstance(raw, dict) or raw.get("kind") != "audio-measured" or raw.get("version") != 1:
        raise ValueError("unsupported measured timing policy")
    from lib.infra.content_digest import PREFIXED_DIGEST_RE

    for key in ("source_basis", "evidence_digest"):
        if not isinstance(raw.get(key), str) or PREFIXED_DIGEST_RE.fullmatch(raw[key]) is None:
            raise ValueError("invalid timing evidence identity")
    pairs = raw.get("intervals")
    if not isinstance(pairs, list) or any(
        not isinstance(p, list) or len(p) != 2 or any(type(v) is not int for v in p) for p in pairs
    ):
        raise ValueError("invalid measured intervals")
    return MeasuredSubtitleTiming(raw["source_basis"], tuple(tuple(p) for p in pairs), raw["evidence_digest"])
