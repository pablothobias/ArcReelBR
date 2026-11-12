"""Reference-video direction contract across script_plan, prompt_authoring, and request projection.

Covers camera vocabulary, source-backed direction, sound guidance, and per-request direction language
(``instructions``) on the real builders, then projects an authored unit through the execution request
projector and unit renderer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lib.prompts.prompt_builders_reference import build_reference_units_split_prompt, build_reference_video_prompt
from lib.script.reference_video.draft_validation import (
    assert_dialogue_preserved,
    validate_dialogue_load,
    validate_unit_text,
)
from lib.script.reference_video.prompt_render import render_video_unit_prompt
from lib.script.reference_video.request_projection import (
    ReferenceRequestOptions,
    ReferenceUnitRequestProjector,
    ResolvedReferenceAsset,
)
from lib.script.reference_video.script_preview import derive_utterances
from lib.script.reference_video.voice_settings import VoiceRenderSettings
from lib.script.script_models import ReferenceResource
from tests.factories import make_video_request_facts

_SCENE = "Rua Danificada"
_WOMAN = "Mulher"
_MAN = "Homem"
_LINE_ONE = "Por favor, por favor!"
_LINE_TWO = "Faz a gente feliz. Só uma vez."

#: PT-BR source passage: two characters walking toward camera in one street, one speaker.
_SOURCE = (
    "Na rua destruída, a mulher caminha na frente e o homem calado vem atrás.\n"
    f"— {_LINE_ONE}\n"
    "Ela espera um instante.\n"
    f"— {_LINE_TWO}"
)

#: script_plan body carrying contradictory source direction: a held vanishing point while footsteps close the distance.
_PLAN_BODY = (
    "Open with both people distant and visible at full length in the damaged street. "
    "Stagger them in depth, woman ahead and silent man offset behind. "
    "Hold the vanishing point and building edges as their footsteps bring them closer.\n"
    f"@[{_WOMAN}] walks ahead through @[{_SCENE}] while @[{_MAN}] follows in silence. @[{_WOMAN}]{{{_LINE_ONE}}}\n"
    f"She pauses, then steps closer. @[{_WOMAN}]{{{_LINE_TWO}}}"
)

#: Representative prompt_authoring output: English direction, locked camera resolving the held vanishing point,
#: verbatim PT-BR dialogue, ambience bed plus action effects, no music.
_AUTHORED_BODY = (
    f"Shot size: wide shot at eye level. Composition: @[{_SCENE}] recedes to a central vanishing point; "
    f"@[{_WOMAN}] walks ahead at full length, @[{_MAN}] offset behind her in depth.\n"
    "Camera movement: locked camera; the vanishing point and building edges hold still while both people walk closer "
    "and grow larger in frame.\n"
    f"Visual content: @[{_WOMAN}] stops, clasps her hands, and lifts her chin toward the lens. @[{_WOMAN}]{{{_LINE_ONE}}}\n"
    f"She lets a beat pass, then takes one step closer. @[{_WOMAN}]{{{_LINE_TWO}}}\n"
    f"@[{_MAN}] keeps walking behind her without speaking.\n"
    "Sound: a light outdoor air bed continues through the pause between requests; shoes scuff grit and fabric "
    "rustles with each step."
)

_ENGLISH_DIRECTION = (
    "Write all visual direction in English. Keep every dialogue and off-screen speech line inside braces "
    "verbatim in Brazilian Portuguese (pt-BR); never translate it."
)

_EXCEPTION = "Direction-language exception: if the additional instructions at the end explicitly name a language"
_OLD_CAMERA_EXAMPLE = "fixed position, slowly pushing in"
_OLD_CAMERA_VOCABULARY = "(fixed / following / pushing in / pulling out / panning)"


def _project() -> dict:
    return {
        "generation_mode": "reference_video",
        "source_language": "pt-BR",
        "style": "Realistic cinematic",
        "characters": {
            _WOMAN: {"description": "woman in her thirties", "voice_style": "pleading female voice"},
            _MAN: {"description": "silent man"},
        },
        "scenes": {_SCENE: {"description": "damaged city street"}},
        "props": {},
    }


def _plan_prompt(*, instructions: str | None, target_language: str = "pt-BR") -> str:
    project = _project()
    return build_reference_units_split_prompt(
        novel_text=_SOURCE,
        project_overview={"synopsis": "s", "genre": "g", "theme": "t", "world_setting": "w"},
        characters=project["characters"],
        scenes=project["scenes"],
        props=project["props"],
        supported_durations=[8, 16],
        max_duration=16,
        max_reference_images=4,
        default_duration=8,
        episode=1,
        target_language=target_language,
        source_language="pt-BR",
        instructions=instructions,
    )


def _authoring_prompt(*, instructions: str | None, target_language: str = "pt-BR") -> str:
    project = _project()
    return build_reference_video_prompt(
        project_overview={"synopsis": "s", "genre": "g", "theme": "t", "world_setting": "w"},
        style=project["style"],
        style_description="",
        characters=project["characters"],
        scenes=project["scenes"],
        props=project["props"],
        script_plan_units=[{"unit_id": "E1U1", "text": _PLAN_BODY, "duration_seconds": 8}],
        max_refs=4,
        episode=1,
        target_language=target_language,
        instructions=instructions,
    )


def _speech_rate_clause(prompt: str) -> str:
    match = re.search(r"approximately [\d.]+ \w+/second", prompt)
    assert match is not None
    return match.group(0)


def _output_language_rule(prompt: str) -> str:
    return next(line for line in prompt.splitlines() if line.startswith("**Output language**"))


@pytest.mark.parametrize("build", [_plan_prompt, _authoring_prompt])
def test_explicit_direction_language_instruction_adds_scoped_exception(build) -> None:
    prompt = build(instructions=_ENGLISH_DIRECTION)

    assert _EXCEPTION in prompt
    assert "dialogue and off-screen speech inside braces `{}` stay verbatim in their approved language" in prompt
    assert "never infer a direction language from locale, source language, or project name" in prompt
    assert f"# Additional instructions\n{_ENGLISH_DIRECTION}" in prompt
    # The exception outranks the body-writing syntax note that otherwise ties visual prose to the output language.
    assert "This overrides the output-language rule, including the body-writing syntax note on language" in prompt


@pytest.mark.parametrize("target_language", ["pt-BR", "English", "Español"])
@pytest.mark.parametrize("build", [_plan_prompt, _authoring_prompt])
def test_default_path_has_no_instructions_section_or_exception(build, target_language: str) -> None:
    default = build(instructions=None, target_language=target_language)
    instructed = build(instructions=_ENGLISH_DIRECTION, target_language=target_language)

    assert "# Additional instructions" not in default
    assert "Direction-language exception" not in default
    assert _output_language_rule(default) == _output_language_rule(instructed)


def test_direction_language_instruction_does_not_change_speech_rate() -> None:
    default = _plan_prompt(instructions=None)
    instructed = _plan_prompt(instructions=_ENGLISH_DIRECTION)

    assert _speech_rate_clause(default) == _speech_rate_clause(instructed)
    assert "words/second" in _speech_rate_clause(default)


def test_authoring_prompt_replaces_ambiguous_camera_example_with_three_behaviors() -> None:
    prompt = _authoring_prompt(instructions=None)

    assert _OLD_CAMERA_EXAMPLE not in prompt
    assert _OLD_CAMERA_VOCABULARY not in prompt
    assert (
        "Camera movement: locked camera; the camera does not move, only the character moves within the frame." in prompt
    )
    assert "Good (camera travel)" in prompt
    assert "the two shifting against each other" in prompt
    assert "Good (optical zoom)" in prompt
    assert "keep their relative positions, with no parallax" in prompt
    assert (
        "Do not pin the horizon, vanishing point, or building edges in place while also asking for camera travel"
        in prompt
    )
    assert "favoring whichever the unit’s source-backed direction states" in prompt


def test_authoring_prompt_guides_ambience_bed_and_action_effects_without_music() -> None:
    prompt = _authoring_prompt(instructions=None)

    assert "continuous ambience bed for the location" in prompt
    assert "keeps playing through pauses between lines" in prompt
    assert "place action effects (footsteps, cloth movement, props) alongside the actions that produce them" in prompt
    assert "do not write score, background music, or songs" in prompt
    assert "Music is added on the edit timeline" in prompt


def test_source_backed_direction_is_carried_by_plan_and_kept_by_authoring() -> None:
    plan = _plan_prompt(instructions=None)
    authoring = _authoring_prompt(instructions=None)

    assert "Do not write shot size / composition / camera movement at this stage" not in plan
    assert "write it into the unit body as plain visual description" in plan
    assert "A cut in the source starts a new unit when both resulting units still satisfy the duration" in plan
    assert "keep the shots in one unit and write the later framing as a continuous camera move" in plan
    assert "only where the source shows it or the additional instructions approve it" in plan
    # The plan body reaches prompt_authoring unchanged; authoring keeps staging already in a body, including on rewrite.
    assert _PLAN_BODY in authoring
    assert "do not replace them with your own choices" in authoring
    assert "expand only what they leave unspecified" in authoring
    assert "an earlier authored body was already confirmed" in authoring
    assert "unless the additional instructions ask for that change" in authoring


def test_screenplay_plan_keeps_author_camera_direction() -> None:
    project = _project()
    prompt = build_reference_units_split_prompt(
        novel_text=_SOURCE,
        project_overview={},
        characters=project["characters"],
        scenes=project["scenes"],
        props={},
        supported_durations=[8],
        max_duration=8,
        max_reference_images=None,
        default_duration=None,
        episode=1,
        source_kind="screenplay",
    )

    assert "The author’s explicit framing, camera movement, and blocking are source-backed direction" in prompt


class _AllAssetsAvailable:
    def is_available(self, asset: ResolvedReferenceAsset) -> bool:
        del asset
        return True


@pytest.mark.asyncio
async def test_authored_english_direction_projects_with_verbatim_ptbr_dialogue() -> None:
    project = _project()
    unit = {"unit_id": "E1U1", "text": _AUTHORED_BODY, "duration_seconds": 8}

    # The script_plan body carrying source direction passes unit validation, and prompt_authoring
    # validators accept the authored body: dialogue matches script_plan exactly and fits the duration.
    plan_refs = validate_unit_text("E1U1", _PLAN_BODY, project, max_refs=4)
    assert [ref.name for ref in plan_refs] == [_WOMAN, _SCENE, _MAN]
    assert_dialogue_preserved("E1U1", _PLAN_BODY, _AUTHORED_BODY)
    validate_dialogue_load("E1U1", _AUTHORED_BODY, 8, project["source_language"])
    validated = validate_unit_text("E1U1", _AUTHORED_BODY, project, max_refs=4)
    assert [(ref.type, ref.name) for ref in validated] == [
        ("scene", _SCENE),
        ("character", _WOMAN),
        ("character", _MAN),
    ]

    facts = make_video_request_facts(
        route="reference_video",
        generation_type="r2v",
        provider_id="reference-provider",
        model_id="reference-model",
        supported_durations=(8, 16),
        allowed_durations=(8, 16),
        max_reference_images=4,
    )

    async def request_facts(generation_type: str):
        del generation_type
        return facts

    assets = [
        ResolvedReferenceAsset(
            reference=ReferenceResource(type=ref.type, name=ref.name), path=Path(f"/fake/{ref.name}.png")
        )
        for ref in validated
    ]
    projection = await ReferenceUnitRequestProjector(request_facts, _AllAssetsAvailable()).project_current(
        project=project,
        script={"video_units": [unit]},
        unit=unit,
        resolved_assets=assets,
        options=ReferenceRequestOptions(),
    )

    assert [(ref.type, ref.name) for ref in projection.declared_references] == [
        ("scene", _SCENE),
        ("character", _WOMAN),
        ("character", _MAN),
    ]
    assert [asset.path.name for asset in projection.request_assets] == [
        f"{_SCENE}.png",
        f"{_WOMAN}.png",
        f"{_MAN}.png",
    ]
    assert projection.planned_duration == 8
    assert projection.request_duration is not None
    assert projection.request_duration.seconds == 8
    assert not projection.blocking_problems

    rendered = render_video_unit_prompt(
        unit,
        project,
        VoiceRenderSettings.from_request_facts(facts),
        request_references=[asset.reference for asset in projection.request_assets],
    )
    utterances, warnings = derive_utterances(_AUTHORED_BODY)

    assert warnings == []
    assert [(u.kind, u.speaker, u.text) for u in utterances] == [
        ("dialogue", _WOMAN, _LINE_ONE),
        ("dialogue", _WOMAN, _LINE_TWO),
    ]
    assert f"<{_WOMAN}> says {{{_LINE_ONE}}}" in rendered.prompt
    assert f"<{_WOMAN}> says {{{_LINE_TWO}}}" in rendered.prompt
    assert f"<{_SCENE}>@Image 1, <{_WOMAN}>@Image 2, <{_MAN}>@Image 3." in rendered.prompt
    assert "Camera movement: locked camera" in rendered.prompt
    assert "BGM" in rendered.prompt.splitlines()[-1]
    assert rendered.warnings == []
