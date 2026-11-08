"""Known modality, signal and temporal contradictions never become AV acceptance."""

import pytest

from scripts.validate_av_review import MediaEvidence, validate_review


def audio_review(*, speech=True, confidence=1.0):
    return {
        "evidence_status": "observed",
        "speech": [
            {
                "speaker_label": "speaker",
                "start_seconds": 0,
                "end_seconds": 1,
                "words_heard": "Olá",
                "delivery_observation": "Conversational",
                "confidence": confidence,
            }
        ]
        if speech
        else [],
        "actual_audio_description": "A short utterance" if speech else "No speech heard",
        "assessability_limits": [],
    }


def video_review():
    return {
        **audio_review(),
        "actual_visual_description": "A speaking person",
        "visible_words": [],
        "subtitles": [],
        "audiovisual_synchrony": {
            "status": "apparently_aligned",
            "explanation": "Apparent correspondence",
            "estimated_offset_ms": 0,
            "confidence": 1,
        },
    }


def test_audio_only_contract_rejects_visual_claims_even_at_maximum_confidence():
    result = validate_review(
        video_review(), MediaEvidence(has_audio=True, has_video=False, duration_seconds=2, pcm_state="nonzero")
    )
    assert result["validation_status"] == "rejected"
    assert {item["path"] for item in result["findings"]} >= {"actual_visual_description", "audiovisual_synchrony"}
    assert not result["automatic_quality_pass"]


def test_known_zero_pcm_rejects_structured_speech_without_relying_on_visual_fields():
    result = validate_review(
        audio_review(), MediaEvidence(has_audio=True, has_video=False, duration_seconds=2, pcm_state="zero")
    )
    assert result["validation_status"] == "rejected"
    assert result["findings"][0]["code"] == "speech_on_zero_pcm"


@pytest.mark.parametrize("state", ["unknown", "no_audio"])
def test_missing_or_unknown_audio_is_not_assumed_digital_silence(state):
    evidence = MediaEvidence(
        has_audio=None if state == "unknown" else False, has_video=False, duration_seconds=2, pcm_state=state
    )
    result = validate_review(audio_review(speech=False), evidence)
    assert result["validation_status"] == "insufficient_evidence"
    assert not any(item["code"] == "speech_on_zero_pcm" for item in result["findings"])
    assert result["requires_reviewer"]


def test_faithful_nonzero_response_is_consistent_evidence_but_never_an_automatic_pass():
    result = validate_review(
        audio_review(), MediaEvidence(has_audio=True, has_video=False, duration_seconds=2, pcm_state="nonzero")
    )
    assert result["validation_status"] == "consistent_requires_review"
    assert result["findings"] == []
    assert result["requires_reviewer"]
    assert not result["automatic_quality_pass"]


@pytest.mark.parametrize("end", [2, 2.001])
def test_timestamp_end_is_bounded_by_actual_duration(end):
    raw = audio_review()
    raw["speech"][0]["end_seconds"] = end
    result = validate_review(
        raw, MediaEvidence(has_audio=True, has_video=False, duration_seconds=2, pcm_state="nonzero")
    )
    assert result["validation_status"] == ("consistent_requires_review" if end == 2 else "rejected")


@pytest.mark.parametrize(("start", "end"), [(-1, 1), (1, 1), (2, 1), (0, float("nan")), (0, float("inf"))])
def test_invalid_time_intervals_are_rejected(start, end):
    raw = audio_review()
    raw["speech"][0].update(start_seconds=start, end_seconds=end)
    assert (
        validate_review(raw, MediaEvidence(has_audio=True, has_video=False, duration_seconds=2, pcm_state="nonzero"))[
            "validation_status"
        ]
        == "rejected"
    )


def test_video_subtitles_are_bounded_and_no_audio_cannot_support_synchrony():
    raw = video_review()
    raw["subtitles"] = [
        {"text": "Olá", "approximate_start_seconds": 1, "approximate_end_seconds": 3, "overlaps_heard_speech": "yes"}
    ]
    result = validate_review(
        raw, MediaEvidence(has_audio=False, has_video=True, duration_seconds=2, pcm_state="no_audio")
    )
    assert {item["code"] for item in result["findings"]} == {
        "speech_without_audio_stream",
        "synchrony_without_sound",
        "timestamp_outside_media",
    }


def test_unknown_duration_does_not_validate_temporal_claims_or_promote_confidence():
    result = validate_review(video_review(), MediaEvidence(has_audio=True, has_video=True, pcm_state="nonzero"))
    assert result["validation_status"] == "insufficient_evidence"
    assert "media_duration_unknown" in result["missing_evidence"]
    assert not result["automatic_quality_pass"]


def test_unexamined_audio_track_keeps_partial_evidence_incomplete():
    evidence = MediaEvidence(
        has_audio=True,
        has_video=False,
        duration_seconds=2,
        pcm_state="nonzero",
        decoded_streams=[{"pcm_state": "nonzero"}, {"pcm_state": "unknown"}],
    )
    result = validate_review(audio_review(), evidence)
    assert result["validation_status"] == "insufficient_evidence"
    assert "audio_decode_incomplete" in result["missing_evidence"]


def test_unknown_video_modality_does_not_reject_a_valid_video_response_as_audio_only():
    result = validate_review(video_review(), MediaEvidence(has_audio=True, duration_seconds=2, pcm_state="nonzero"))
    assert result["validation_status"] == "insufficient_evidence"
    assert result["response_contract"] == "modality_unverified"
    assert result["findings"] == []
    assert "video_modality_unknown" in result["missing_evidence"]


def test_evaluator_abstention_propagates_without_becoming_a_consistent_result():
    raw = audio_review(speech=False)
    raw["evidence_status"] = "insufficient_evidence"
    result = validate_review(
        raw, MediaEvidence(has_audio=True, has_video=False, duration_seconds=2, pcm_state="nonzero")
    )
    assert result["validation_status"] == "insufficient_evidence"
    assert "evaluator_reported_insufficient_evidence" in result["missing_evidence"]
    assert result["requires_reviewer"]
    assert not result["automatic_quality_pass"]
