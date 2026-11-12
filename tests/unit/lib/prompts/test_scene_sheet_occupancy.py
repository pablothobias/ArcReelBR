"""Scene-sheet occupancy: an explicit scene field chooses an empty (default) or occupied environment sheet.

Occupancy is never inferred from description wording: the P04-like classroom description below asks for seated
adults, yet renders inside the empty-environment wrappers until the scene is explicitly marked ``occupied``.
Absent occupancy renders the empty-environment wrappers and keeps freshness digests byte for byte, so existing
scene sheets stay current.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lib.artifacts.artifact_manifest import InMemoryArtifactManifestAdapter
from lib.artifacts.generation_input import ManifestInputObservation, asset_sheet_input
from lib.artifacts.visual_artifact_provenance import build_asset_sheet_visual_basis
from lib.project.asset_types import ASSET_SPECS, build_asset_entry
from lib.project.data_validator import DataValidator
from lib.project.project_manager import ProjectManager
from lib.prompts.prompt_builders import build_scene_prompt

_STYLE_HEADER = "Style: Realista\nVisual style: Cinematic, natural light\n\n"
_CLASSROOM = (
    "Sala de aula de escola pública brasileira, carteiras de madeira enfileiradas dos dois lados do "
    "corredor central, ocupadas por adultos sentados assistindo em silêncio; luz da tarde entrando "
    "pelas janelas basculantes."
)


def _expected_prompt(guard: str, avoid: str) -> str:
    return (
        f"{_STYLE_HEADER}Asset sheet for scene “Sala de aula”.\n\n{_CLASSROOM}\n\n"
        f"A single panoramic environment establishing shot.\n\n{guard}\n\nAvoid:{avoid} watermarks, extra text, logos"
    )


_EMPTY_PROMPT = _expected_prompt(
    "This sheet is an empty environment reference: no people appear in the image.", " people appearing in the shot,"
)
_OCCUPIED_PROMPT = _expected_prompt(
    "This sheet is an occupied environment reference: show only the people the description asks for, as anonymous "
    "occupants of the place rather than story characters, with no distinctive faces or close-ups, keeping the space "
    "itself clearly readable.",
    " people beyond those described, close-ups of faces,",
)


def _project(**scene_fields: Any) -> dict[str, Any]:
    return {
        "style": "Realista",
        "style_description": "Cinematic, natural light",
        "scenes": {"Sala de aula": {"description": _CLASSROOM, **scene_fields}},
    }


def _sheet(tmp_path: Path, project: dict[str, Any]):
    observation = ManifestInputObservation(tmp_path, InMemoryArtifactManifestAdapter(artifacts=set()))
    return asset_sheet_input(project, asset_type="scene", name="Sala de aula", observation=observation)


def _render(sheet) -> str:
    return sheet.render(max_reference_images=None, model="").prompt


@pytest.mark.parametrize(
    ("occupancy", "expected"),
    [("empty", _EMPTY_PROMPT), ("occupied", _OCCUPIED_PROMPT)],
)
def test_scene_prompt_renders_the_explicit_occupancy(occupancy, expected):
    prompt = build_scene_prompt("Sala de aula", _CLASSROOM, "Realista", "Cinematic, natural light", occupancy=occupancy)

    assert prompt == expected


def test_scene_prompt_rejects_unknown_occupancy():
    with pytest.raises(ValueError, match="occupancy"):
        build_scene_prompt("Sala de aula", _CLASSROOM, occupancy="crowded")


def test_occupied_wording_in_description_alone_keeps_the_empty_sheet(tmp_path):
    sheet = _sheet(tmp_path, _project())

    assert sheet.semantics.occupancy == "empty"
    assert _render(sheet) == _EMPTY_PROMPT


def test_explicit_occupancy_reaches_the_generation_prompt(tmp_path):
    sheet = _sheet(tmp_path, _project(occupancy="occupied"))

    assert _render(sheet) == _OCCUPIED_PROMPT


@pytest.mark.parametrize("stored", [{}, {"occupancy": ""}, {"occupancy": "empty"}])
def test_empty_occupancy_keeps_the_existing_sheet_basis(tmp_path, stored):
    legacy = build_asset_sheet_visual_basis(
        asset_type="scene",
        asset_id="Sala de aula",
        description=_CLASSROOM,
        style="Realista",
        style_description="Cinematic, natural light",
        aspect_ratio="16:9",
    )

    assert _sheet(tmp_path, _project(**stored)).expected_basis().digest == legacy.digest


def test_switching_occupancy_marks_the_sheet_stale_and_switching_back_restores_it(tmp_path):
    empty = _sheet(tmp_path, _project()).expected_basis().digest
    occupied = _sheet(tmp_path, _project(occupancy="occupied")).expected_basis().digest

    assert occupied != empty
    assert _sheet(tmp_path, _project(occupancy="empty")).expected_basis().digest == empty


def test_invalid_stored_occupancy_is_rejected_by_generation_and_validation(tmp_path):
    project = _project(occupancy="crowded")

    with pytest.raises(ValueError, match="occupancy"):
        _sheet(tmp_path, project)
    errors = DataValidator(str(tmp_path)).validate_project_payload(project).errors
    assert any("occupancy" in str(error) and "crowded" in str(error) for error in errors)
    valid = DataValidator(str(tmp_path)).validate_project_payload(_project(occupancy="occupied")).errors
    assert not any("occupancy" in str(error) for error in valid)


def test_occupancy_is_a_scene_only_agent_field_that_defaults_by_absence():
    assert "occupancy" in ASSET_SPECS["scene"].agent_writable_fields
    assert all("occupancy" not in ASSET_SPECS[t].agent_writable_fields for t in ("character", "prop", "product"))
    assert "occupancy" not in build_asset_entry("scene", "x")
    assert build_asset_entry("scene", "x", {"occupancy": "occupied"})["occupancy"] == "occupied"


def test_agent_upsert_writes_occupancy_and_rejects_unknown_values(tmp_path):
    manager = ProjectManager(str(tmp_path))
    manager.create_project("demo")
    manager.create_project_metadata("demo", "Demo")

    manager.upsert_assets("demo", "scenes", {"Sala de aula": {"description": _CLASSROOM, "occupancy": "occupied"}})
    with pytest.raises(ValueError, match="occupancy"):
        manager.upsert_assets("demo", "scenes", {"Sala de aula": {"occupancy": "crowded"}})

    assert manager.load_project("demo")["scenes"]["Sala de aula"]["occupancy"] == "occupied"
