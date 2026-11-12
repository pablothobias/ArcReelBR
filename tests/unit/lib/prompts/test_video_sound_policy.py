"""Video sound policy: score stays on the edit timeline, clips carry only diegetic sound.

Both generation paths (reference video and storyboard video) keep the shared default exclusion, including
``BGM``, with their path-specific additions; every storyboard-mode authoring prompt separates the four sound
layers (ambience, action effects, speech, score). Full request goldens live with each renderer's own tests.
"""

from __future__ import annotations

import pytest

from lib.prompts.prompt_builders_ad import build_ad_prompt, build_ad_shot_prompt_authoring_prompt
from lib.prompts.prompt_builders_script import build_drama_prompt, build_narration_prompt
from lib.prompts.prompt_utils import normalize_video_prompt, video_prompt_to_yaml
from lib.script.reference_video.prompt_render import render_unit_prompt
from lib.script.reference_video.voice_settings import VoiceRenderSettings
from lib.script.script_models import ReferenceResource

DEFAULT_AVOID = "Avoid: BGM, text subtitles, watermarks, logos"
DOUBLES_CLAUSE = ", doubles or twins with identical appearance and clothing"

_PROJECT = {
    "style": "Cinematic realism",
    "characters": {"Mara": {}, "Theo": {}},
    "scenes": {"Harbor": {}},
    "products": {"Lumen Flask": {}},
}


def _refs(*pairs: tuple[str, str]) -> list[ReferenceResource]:
    return [ReferenceResource(type=kind, name=name) for kind, name in pairs]


def _avoid_lines(prompt: str) -> list[str]:
    return [line for line in prompt.splitlines() if line.startswith("Avoid:")]


def test_reference_video_single_character_keeps_default_exclusion():
    rendered = render_unit_prompt(
        "@[Mara] waits at @[Harbor].", _PROJECT, _refs(("character", "Mara")), VoiceRenderSettings()
    )

    assert _avoid_lines(rendered.prompt) == [DEFAULT_AVOID]


def test_reference_video_adds_doubles_clause_and_keeps_product_fidelity():
    rendered = render_unit_prompt(
        "@[Mara] and @[Theo] walk along @[Harbor] holding @[Lumen Flask].\n@[Mara]: {We made it.}",
        _PROJECT,
        _refs(("character", "Mara"), ("character", "Theo"), ("scene", "Harbor"), ("product", "Lumen Flask")),
        VoiceRenderSettings(),
    )

    assert _avoid_lines(rendered.prompt) == [DEFAULT_AVOID + DOUBLES_CLAUSE]
    assert "High-fidelity product reproduction (highest priority, overriding the text / logo prohibitions above)" in (
        rendered.prompt
    )


def test_storyboard_video_structured_request_keeps_default_exclusion():
    prompt = video_prompt_to_yaml(
        {
            "action": "Mara walks to the pier edge.",
            "camera_motion": "Static",
            "ambiance_audio": "Waves lap the pilings throughout; her boots knock on the planks as she walks.",
            "dialogue": [{"speaker": "Mara", "line": "We made it."}],
        }
    )

    assert _avoid_lines(prompt) == [DEFAULT_AVOID]


def test_storyboard_video_plain_text_request_replaces_written_avoid_with_default():
    prompt = normalize_video_prompt("Mara walks to the pier edge.\nAvoid: music")

    assert _avoid_lines(prompt) == [DEFAULT_AVOID]


_OVERVIEW = {"synopsis": "S", "genre": "G", "theme": "T", "world_setting": "W"}


def _drama() -> str:
    return build_drama_prompt(
        project_overview=_OVERVIEW,
        style="Realism",
        style_description="cinematic",
        scenes_content="### E1S01 (8 seconds)\nVisual adaptation: rooftop chase",
        episode=1,
        aspect_ratio="9:16",
    )


def _narration() -> str:
    return build_narration_prompt(
        project_overview=_OVERVIEW,
        style="Realism",
        style_description="cinematic",
        characters={"Mara": {}},
        scenes={"Harbor": {}},
        props={},
        script_plan_segments=[
            {
                "segment_id": "E1S01",
                "novel_text": "She reached the harbor.",
                "duration_seconds": 6,
                "segment_break": True,
                "characters_in_segment": ["Mara"],
                "scenes": ["Harbor"],
                "props": [],
            }
        ],
        episode=1,
    )


def _ad_script() -> str:
    return build_ad_prompt(
        project_overview=_OVERVIEW,
        style="Realism",
        style_description="cinematic",
        characters={"Mara": {}},
        scenes={},
        props={},
        products={},
        brief="Brief",
        target_duration=30,
        generation_mode="image",
        supported_durations=[4, 6, 8],
    )


def _ad_shot_authoring() -> str:
    return build_ad_shot_prompt_authoring_prompt(
        project_overview=_OVERVIEW,
        style="Realism",
        style_description="cinematic",
        characters={"Mara": {}},
        scenes={},
        props={},
        products={},
        brief="Brief",
        shots=[{"shot_id": "E1S01", "duration_seconds": 4, "voiceover_text": ""}],
        target_ids=["E1S01"],
    )


@pytest.mark.parametrize("build", [_drama, _narration, _ad_script, _ad_shot_authoring])
def test_storyboard_authoring_separates_four_sound_layers(build):
    prompt = build()
    ambiance = next(line for line in prompt.splitlines() if line.startswith("- **video_prompt.ambiance_audio**"))

    assert "Continuous ambience" in ambiance
    assert "Action effects" in ambiance
    assert "Spoken words never go here" in ambiance
    assert "score is placed on the edit timeline" in ambiance
