"""Measured timing rejects wrong words, uncertain recognition and stale speech/media."""

from dataclasses import replace

import pytest

from lib.speech.audio_review import assess_speech, timing_from_report
from lib.speech.measured_timing import measured_policy
from lib.speech.speech_composition import SpeechMode
from lib.speech.speech_presentation import materialize_speech_presentation
from tests.unit.lib.speech.test_speech_presentation import _media, _speech


def presentation():
    return materialize_speech_presentation(
        _speech(SpeechMode.CHARACTER_SPEECH, ("Ana", "Resolvi não me estressar.")),
        variant="post_production",
        video=_media("video.mp4", kind="v", duration=5),
        provider_audio_enabled=True,
    )


def transcript():
    return {
        "words": [
            {"text": text, "start": 1 + i * 0.4, "end": 1.3 + i * 0.4, "probability": 0.95}
            for i, text in enumerate(["Resolvi", "não", "me", "estressar."])
        ]
    }


def test_measured_cues_follow_actual_words_not_whole_clip():
    original = presentation()
    report = assess_speech(original, transcript())
    timing = timing_from_report(report)
    assert measured_policy(timing.basis_identity) == timing
    actual = materialize_speech_presentation(
        _speech(SpeechMode.CHARACTER_SPEECH, ("Ana", "Resolvi não me estressar.")),
        variant="post_production",
        video=original.video.media,
        provider_audio_enabled=True,
        timing=timing,
    )
    assert actual.subtitles[0].start_microseconds == 1_000_000
    assert actual.subtitles[0].end_microseconds == 2_500_000
    assert actual.subtitles[0].text == original.subtitles[0].text
    assert actual.timing == "audio_measured"
    assert actual.subtitle_basis.digest != original.subtitle_basis.digest
    assert report["lip_sync"] == "not_assessed"
    with pytest.raises(ValueError, match="different speech or media"):
        materialize_speech_presentation(
            _speech(SpeechMode.CHARACTER_SPEECH, ("Ana", "Outra fala.")),
            variant="post_production",
            video=original.video.media,
            provider_audio_enabled=True,
            timing=timing,
        )
    with pytest.raises(ValueError, match="different speech or media"):
        materialize_speech_presentation(
            _speech(SpeechMode.CHARACTER_SPEECH, ("Ana", "Resolvi não me estressar.")),
            variant="post_production",
            video=replace(
                original.video.media,
                evidence=replace(original.video.media.evidence, content_digest="sha256-v1:" + "c" * 64),
            ),
            provider_audio_enabled=True,
            timing=timing,
        )


@pytest.mark.parametrize("change", ["silence", "negation", "extra", "confidence", "overlap", "outside", "nan"])
def test_uncertain_or_different_audio_cannot_change_subtitles(change):
    data = transcript()
    if change == "silence":
        data["words"] = []
    elif change == "negation":
        data["words"].pop(1)
    elif change == "extra":
        data["words"].append({"text": "sim", "start": 3, "end": 3.5, "probability": 0.99})
    elif change == "confidence":
        data["words"][1]["probability"] = 0.2
    elif change == "overlap":
        data["words"][1]["start"] = 0
    elif change == "outside":
        data["words"][-1]["end"] = 6
    else:
        data["words"][1]["start"] = float("nan")
    report = assess_speech(presentation(), data)
    assert report["timing_eligible"] is False
    with pytest.raises(ValueError, match="does not admit"):
        timing_from_report(report)
