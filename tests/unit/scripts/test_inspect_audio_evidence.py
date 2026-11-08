"""Advisory speech discrepancies never become audiovisual passes."""

import pytest

from scripts.inspect_audio_evidence import ExpectedSpeech, compare_evidence


@pytest.mark.parametrize(
    ("observed", "expected_finding"),
    [("Olá, Ana!", None), ("Olá, Bruno!", "transcript_mismatch_requires_listening"), ("", "speech_evidence_missing")],
)
def test_speech_comparison_distinguishes_matching_wrong_and_missing_evidence(observed, expected_finding):
    result = compare_evidence(
        [ExpectedSpeech(segment_id="E1U01", start=0, end=4, text="Olá, Ana!")],
        {"transcription": [{"text": observed, "offsets": {"from": 100, "to": 3500}}]},
    )[0]
    assert result["review_status"] == "requires_review"
    assert result["observed_transcript"] == observed
    assert "subtitle_timing_evidence_missing" in result["findings"]
    if expected_finding:
        assert expected_finding in result["findings"]
    else:
        assert result["findings"] == ["subtitle_timing_evidence_missing"]


@pytest.mark.parametrize(
    ("start", "finding"),
    [
        (100_000, None),
        (2_000_000, "subtitle_boundary_discrepancy_requires_review"),
        (5_000_000, "subtitle_has_no_overlap_with_transcribed_speech"),
    ],
)
def test_subtitle_envelopes_report_mistiming_without_claiming_word_alignment(start, finding):
    result = compare_evidence(
        [ExpectedSpeech(segment_id="E1U01", start=0, end=4, text="Olá, Ana!")],
        {"transcription": [{"text": "Olá, Ana!", "offsets": {"from": 100, "to": 3500}}]},
        [{"start_microseconds": start, "duration_microseconds": 3_400_000, "text": "Olá, Ana!"}],
    )[0]
    assert result["findings"] == ([finding] if finding else [])
    assert result["review_status"] == "requires_review"
    assert result["correction_routes"]


def test_repeated_lines_have_ambiguous_alignment_instead_of_a_pass():
    cue = {"start_microseconds": 0, "duration_microseconds": 2_000_000, "text": "Sim."}
    result = compare_evidence(
        [ExpectedSpeech(segment_id="E1U01", start=0, end=4, text="Sim.")],
        {"transcription": [{"text": "Sim.", "offsets": {"from": 0, "to": 2000}}]},
        [cue, cue],
    )[0]
    assert result["findings"] == ["subtitle_alignment_evidence_ambiguous"]
