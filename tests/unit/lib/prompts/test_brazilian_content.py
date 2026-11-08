"""Deterministic Brazilian source, structured-content and visual-prompt contracts.

The structured responses are fixtures, not evidence of live model compliance.
"""

import pytest
from pydantic import ValidationError

from lib.infra.content_language import normalize_content_language
from lib.infra.text_metrics import count_reading_units, find_reading_unit_offset, reading_unit_noun
from lib.project.project_manager import ProjectOverview
from lib.prompts.prompt_builders_reference import build_reference_video_prompt
from lib.prompts.prompt_builders_script import (
    build_drama_prompt,
    build_narration_prompt,
    build_overview_prompt,
    render_drama_content_for_prompt_authoring,
)
from lib.script.reference_video.draft_validation import DraftViolation, assert_dialogue_preserved
from lib.script.script_models import DramaNormalizedScript, NarrationScriptPlanDraft, ReferenceScriptPlanDraft
from lib.speech.speech_rate import estimate_spoken_seconds, project_speech_rate_override
from server.routers.projects import CreateProjectRequest, UpdateProjectRequest
from server.tool_runtime import CreateProjectToolRequest

_SOURCE = 'Ana olha a conta. Ana: "Não acredito! Você pagou o café?"'
_SPEECH = "Não acredito! Você pagou o café?"
_NARRATION = "Ana olhou a conta e descobriu que o café já estava pago."


@pytest.mark.parametrize("language", ["pt-BR", "pt-br", " PT_br "])
def test_content_language_normalizes_across_write_schemas(language):
    assert normalize_content_language(language) == "pt-BR"
    assert CreateProjectRequest(generation_mode="storyboard", source_language=language).source_language == "pt-BR"
    assert UpdateProjectRequest(source_language=language).source_language == "pt-BR"
    assert CreateProjectToolRequest(name="cafe", source_language=language).source_language == "pt-BR"
    overview = ProjectOverview(
        synopsis="Um café pago.", genre="Comédia", theme="Amizade", world_setting="São Paulo", language=language
    )
    assert overview.model_dump()["language"] == "pt-BR"


@pytest.mark.parametrize("language", ["zh", "en", "vi", "ru"])
def test_existing_language_codes_are_preserved(language):
    assert CreateProjectRequest(generation_mode="storyboard", source_language=language).source_language == language
    assert f"all string values must use {language};" in build_overview_prompt(_SOURCE, target_language=language)


def test_unknown_language_is_not_inferred_as_brazilian():
    with pytest.raises(ValidationError):
        UpdateProjectRequest(source_language="pt-PT")
    assert CreateProjectRequest(generation_mode="storyboard").source_language is None
    assert count_reading_units("你好", None) == 2


@pytest.mark.parametrize("language", ["pt-BR", "PT_br"])
def test_brazilian_word_units_and_configurable_estimated_pace(language):
    assert count_reading_units(_SPEECH, language) == 6
    assert reading_unit_noun(language) == "words"
    assert find_reading_unit_offset(_SPEECH, 2, language) == len("Não acredito")
    assert estimate_spoken_seconds(_SPEECH, language) == pytest.approx(2.4)
    override = project_speech_rate_override({"speech_rate_units_per_second": 3})
    assert estimate_spoken_seconds(_SPEECH, language, override) == 2


def _assert_separated_policy(prompt):
    assert "English for technical directions" in prompt
    assert "Brazilian Portuguese (pt-BR)" in prompt
    assert "never translate spoken quotations" in prompt


def test_source_to_structured_drama_fixture_retains_intended_speech():
    """Screenplay input and structured fixture retain speech through visual authoring context."""
    overview_prompt = build_overview_prompt(_SOURCE, source_kind="screenplay", target_language="pt-BR")
    assert _SOURCE in overview_prompt
    _assert_separated_policy(overview_prompt)
    structured = DramaNormalizedScript.model_validate(
        {
            "title": "O café",
            "scenes": [
                {
                    "scene_id": "E1S01",
                    "duration_seconds": 8,
                    "characters_in_scene": ["Ana"],
                    "scenes": [],
                    "props": [],
                    "scene_description": "Close-up of Ana looking at the bill.",
                    "utterances": [{"kind": "dialogue", "speaker": "Ana", "text": _SPEECH}],
                    "source_text": _SOURCE,
                }
            ],
        }
    ).model_dump()
    assert structured["scenes"][0]["utterances"][0]["text"] == _SPEECH
    prompt = build_drama_prompt(
        project_overview={},
        style="",
        style_description="",
        episode=1,
        target_language="pt-BR",
        scenes_content=render_drama_content_for_prompt_authoring(structured["scenes"]),
    )
    _assert_separated_policy(prompt)
    assert _SPEECH in prompt
    assert "Close-up of Ana looking at the bill." in prompt


def test_narration_structured_fixture_preserves_portuguese_source():
    structured = NarrationScriptPlanDraft.model_validate(
        {
            "segments": [
                {
                    "segment_id": "E1S01",
                    "novel_text": _NARRATION,
                    "duration_seconds": 8,
                    "characters_in_segment": [],
                    "scenes": [],
                    "props": [],
                }
            ]
        }
    ).model_dump()
    prompt = build_narration_prompt(
        project_overview={},
        style="",
        style_description="",
        characters={},
        scenes={},
        props={},
        script_plan_segments=structured["segments"],
        episode=1,
        target_language="pt-BR",
    )
    _assert_separated_policy(prompt)
    assert _NARRATION in prompt
    assert structured["segments"][0]["novel_text"] == _NARRATION


def test_reference_fixture_retains_literal_speech_and_rejects_translation():
    body = f"@[Ana] looks at the bill.\n@[Ana]{{{_SPEECH}}}"
    structured = ReferenceScriptPlanDraft.model_validate(
        {
            "units": [
                {
                    "unit_id": "E1U01",
                    "text": body,
                    "duration_seconds": 8,
                    "source_text": _SOURCE,
                }
            ]
        }
    ).model_dump()
    prompt = build_reference_video_prompt(
        project_overview={},
        style="",
        style_description="",
        characters={"Ana": {}},
        scenes={},
        props={},
        script_plan_units=structured["units"],
        max_refs=3,
        episode=1,
        target_language="pt-BR",
    )
    _assert_separated_policy(prompt)
    assert _SPEECH in prompt
    assert_dialogue_preserved("E1U01", body, body.replace("looks at the bill", "looks down at the bill"))
    with pytest.raises(DraftViolation, match="台词被改写"):
        assert_dialogue_preserved("E1U01", body, body.replace(_SPEECH, "I cannot believe it!"))
