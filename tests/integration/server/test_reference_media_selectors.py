"""describe_media selector kinds for uploaded reference images: character reference image and project style image."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.project.project_manager import ProjectManager
from server.services.media_transport.errors import (
    MEDIA_MISSING,
    MEDIA_NOT_FOUND,
    MEDIA_PATH_REFUSED,
    MediaTransportError,
)
from server.services.media_transport.resolution import resolve_media
from server.services.media_transport.selectors import parse_selector

CHARACTER = "小雨"


@pytest.fixture
def projects(tmp_path: Path) -> ProjectManager:
    manager = ProjectManager(tmp_path / "projects")
    manager.create_project("demo")
    manager.create_project_metadata("demo", "Demo", "Anime", "drama")

    def _add(project: dict) -> None:
        project.setdefault("characters", {})[CHARACTER] = {"description": "red raincoat"}

    manager.update_project("demo", _add)
    return manager


def _point(projects: ProjectManager, *, reference: str | None = None, style: str | None = None) -> None:
    def _mutate(project: dict) -> None:
        if reference is not None:
            project["characters"][CHARACTER]["reference_image"] = reference
        if style is not None:
            project["style_image"] = style

    projects.update_project("demo", _mutate)


def _write(projects: ProjectManager, relative: str, data: bytes = b"\x89PNG-bytes") -> None:
    path = projects.get_project_path("demo") / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def _resolve(projects: ProjectManager, selector: dict):
    return await resolve_media(projects, "demo", parse_selector(selector), queue=None)


async def test_character_reference_image_resolves_its_canonical_file(projects: ProjectManager) -> None:
    _write(projects, "characters/refs/xiaoyu.png")
    _point(projects, reference="characters/refs/xiaoyu.png")

    resolved = await _resolve(projects, {"kind": "character_reference_image", "character": CHARACTER})

    assert resolved.relative_path == "characters/refs/xiaoyu.png"
    assert resolved.mime_type == "image/png"
    assert resolved.version is None


async def test_style_image_resolves_the_root_style_reference(projects: ProjectManager) -> None:
    _write(projects, "style_reference.jpg")
    _point(projects, style="style_reference.jpg")

    resolved = await _resolve(projects, {"kind": "style_image"})

    assert resolved.relative_path == "style_reference.jpg"
    assert resolved.mime_type == "image/jpeg"


async def test_missing_and_unknown_targets_have_stable_codes(projects: ProjectManager) -> None:
    for selector, code in (
        ({"kind": "character_reference_image", "character": "Nobody"}, MEDIA_NOT_FOUND),
        ({"kind": "character_reference_image", "character": CHARACTER}, MEDIA_MISSING),
        ({"kind": "style_image"}, MEDIA_MISSING),
    ):
        with pytest.raises(MediaTransportError) as raised:
            await _resolve(projects, selector)
        assert raised.value.code == code


@pytest.mark.parametrize(
    "pointer",
    [
        "project.json",
        "characters/xiaoyu.png",
        "characters/refs_audio/voice.png",
        "characters/refs/nested/xiaoyu.png",
        "characters/refs/../../project.json",
        "characters/refs/.hidden.png",
        ".arcreel/mcp_uploads/x/data.part",
        "scripts/episode_1.json",
    ],
)
async def test_edited_character_pointer_outside_refs_is_refused(projects: ProjectManager, pointer: str) -> None:
    _point(projects, reference=pointer)

    with pytest.raises(MediaTransportError) as raised:
        await _resolve(projects, {"kind": "character_reference_image", "character": CHARACTER})

    assert raised.value.code == MEDIA_PATH_REFUSED


@pytest.mark.parametrize(
    "pointer", ["project.json", "style_reference.json", "source/style_reference.png", "style_reference.png/x"]
)
async def test_edited_style_pointer_outside_root_style_file_is_refused(projects: ProjectManager, pointer: str) -> None:
    _point(projects, style=pointer)

    with pytest.raises(MediaTransportError) as raised:
        await _resolve(projects, {"kind": "style_image"})

    assert raised.value.code == MEDIA_PATH_REFUSED
