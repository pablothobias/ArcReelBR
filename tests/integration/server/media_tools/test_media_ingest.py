"""Client media ingest tools (MCP-011/012/013/016) through the shared declaration entry.

Every tool reuses the native upload transactions; tests assert byte integrity, ordering, provenance,
refusals without orphan files, and that no generation task is ever enqueued.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lib.artifacts.artifact_activation import ArtifactCurrencyResolver
from lib.artifacts.artifact_manifest import ArtifactKey, ArtifactStatus
from lib.artifacts.generation_input import project_input_observation, storyboard_image_input
from lib.artifacts.version_manager import MANUAL_UPLOAD_VERSION_SOURCE, VersionManager
from lib.db.base import DEFAULT_USER_ID
from lib.generation.generation_queue import GenerationQueue
from lib.project.asset_derivatives import derivative_sheet_relative_path
from lib.project.project_manager import ProjectManager
from lib.script.reference_video.request_projection import resolve_reference_assets
from server.agent_toolset.declaration import Blocked, ReadCheck
from server.agent_toolset.media_ingest import (
    ARRANGE_PRODUCT_REFERENCE_IMAGES,
    CLEAR_END_FRAME,
    INSTALL_FINISHED_MEDIA,
    LIST_PRODUCT_REFERENCE_IMAGES,
    MEDIA_INGEST_TOOLS,
    SET_END_FRAME,
    UPLOAD_BGM,
    UPLOAD_PRODUCT_REFERENCE_IMAGES,
)
from server.services.currency import upload_finalize
from server.services.media_transport import append_upload_chunk, begin_upload
from server.tool_runtime import CallerContext
from tests.factories import wav_bytes
from tests.fakes import bind_session_factory, use_project_manager
from tests.integration.server.agent_tool_support import ToolHarness, fake_caps_resolver, run_declared_tool
from tests.integration.server.derivative_sheet_support import seed_derivative_project, solid_png_bytes


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jpeg(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (24, 16), color).save(buffer, format="JPEG", quality=91)
    return buffer.getvalue()


def _segment(segment_id: str = "E1S01", **extra: Any) -> dict[str, Any]:
    return {
        "segment_id": segment_id,
        "novel_text": "t",
        "duration_seconds": 4,
        "characters_in_segment": [],
        "scenes": [],
        "props": [],
        "image_prompt": "a quiet room",
        "video_prompt": "slow push",
        "generated_assets": {
            "storyboard_image": None,
            "video_clip": None,
            "video_uri": None,
            "video_thumbnail": None,
            "grid_id": None,
            "grid_cell_index": None,
            "status": "pending",
        },
        **extra,
    }


async def _fake_thumbnail(_video: Path, thumbnail: Path):
    def _write() -> None:
        thumbnail.parent.mkdir(parents=True, exist_ok=True)
        thumbnail.write_bytes(b"jpg")

    await asyncio.to_thread(_write)
    return thumbnail


@pytest.fixture
def ingest(tmp_path: Path, session_factory, monkeypatch: pytest.MonkeyPatch):
    data_root = tmp_path / "projects"
    pm = ProjectManager(data_root)
    pm.create_project("demo")
    pm.create_project_metadata("demo", "Demo", "Anime", "narration")
    pm.add_product("demo", "Bottle", "steel bottle")
    pm.add_character("demo", "Alice", "silver hair")
    pm.save_script(
        "demo",
        {
            "episode": 1,
            "title": "E1",
            "content_mode": "narration",
            "segments": [_segment(), _segment("E1S02", products_in_shot=["Bottle"])],
        },
        "episode_1.json",
        validate=False,
    )
    use_project_manager(monkeypatch, pm)
    bind_session_factory(monkeypatch, session_factory)
    monkeypatch.setattr(upload_finalize, "extract_video_thumbnail", _fake_thumbnail)
    queue = GenerationQueue(session_factory=session_factory)
    return ToolHarness(
        "demo",
        data_root,
        pm,
        caller=CallerContext(user_id=DEFAULT_USER_ID, source="mcp"),
        queue=queue,
        config_resolver=fake_caps_resolver(last_frame=True),
    )


async def _assert_no_tasks(harness: ToolHarness) -> None:
    listed = await harness.queue.list_tasks(project_name="demo")
    assert listed["total"] == 0, listed


def _project(harness: ToolHarness) -> dict[str, Any]:
    return json.loads((harness.project_path / "project.json").read_text(encoding="utf-8"))


def test_declarations_block_writes_and_check_reads() -> None:
    names = [tool.name for tool in MEDIA_INGEST_TOOLS]
    assert len(names) == len(set(names))
    for tool in MEDIA_INGEST_TOOLS:
        expected = ReadCheck if tool is LIST_PRODUCT_REFERENCE_IMAGES else Blocked
        assert isinstance(tool.migration, expected), tool.name
        properties = json.dumps(tool.input_schema["properties"]) + json.dumps(tool.input_schema.get("$defs", {}))
        assert '"path"' not in properties, tool.name
        assert '"source_path"' not in properties, tool.name


# ---------------------------------------------------------------------------
# MCP-011 product originals
# ---------------------------------------------------------------------------


async def test_product_photos_append_in_order_with_original_bytes(ingest: ToolHarness) -> None:
    first, second = _jpeg((200, 10, 10)), _jpeg((10, 200, 10))

    out = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {
            "product": "Bottle",
            "images": [
                {"filename": "front.jpg", "content_base64": _b64(first)},
                {"filename": "back.jpg", "content_base64": _b64(second)},
            ],
        },
    )

    assert out.problem is None, out.problem
    value = out.value
    assert [item["ref_id"] for item in value["installed"]] == ["Bottle_1.jpg", "Bottle_2.jpg"]
    assert [item["sha256"] for item in value["installed"]] == [_sha(first), _sha(second)]
    assert all(item["bytes_preserved"] for item in value["installed"])
    refs = _project(ingest)["products"]["Bottle"]["reference_images"]
    assert refs == ["products/refs/Bottle_1.jpg", "products/refs/Bottle_2.jpg"]
    assert (ingest.project_path / refs[0]).read_bytes() == first
    assert (ingest.project_path / refs[1]).read_bytes() == second
    assert value["effective_consumption"]["route"] == "storyboard"
    assert value["effective_consumption"]["originals_sent"] == ["Bottle_1.jpg", "Bottle_2.jpg"]
    assert value["generation_submitted"] is False
    await _assert_no_tasks(ingest)

    listed = await run_declared_tool(LIST_PRODUCT_REFERENCE_IMAGES, ingest, {"product": "Bottle"})
    assert listed.problem is None
    assert [(item["index"], item["sha256"]) for item in listed.value["reference_images"]] == [
        (0, _sha(first)),
        (1, _sha(second)),
    ]
    assert listed.value["product_sheet"]["declared"] is False


async def test_bad_photo_in_batch_writes_nothing(ingest: ToolHarness) -> None:
    out = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {
            "product": "Bottle",
            "images": [
                {"filename": "ok.jpg", "content_base64": _b64(_jpeg((1, 2, 3)))},
                {"filename": "broken.jpg", "content_base64": _b64(b"not an image")},
            ],
        },
    )

    assert out.problem is not None
    assert out.problem.code == "invalid_image_file"
    assert not (ingest.project_path / "products" / "refs").exists() or not any(
        (ingest.project_path / "products" / "refs").iterdir()
    )
    assert _project(ingest)["products"]["Bottle"].get("reference_images", []) == []


async def test_missing_product_and_server_paths_are_refused(ingest: ToolHarness) -> None:
    missing = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Ghost", "images": [{"filename": "a.jpg", "content_base64": _b64(_jpeg((1, 1, 1)))}]},
    )
    assert missing.problem is not None
    assert missing.problem.code == "product_not_found"
    assert not (ingest.project_path / "products" / "refs").exists() or not any(
        (ingest.project_path / "products" / "refs").iterdir()
    )

    path_like = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Bottle", "images": [{"filename": "../../etc/a.jpg", "content_base64": _b64(b"x")}]},
    )
    assert path_like.problem is not None
    assert path_like.problem.code == "invalid_request"

    both = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Bottle", "images": [{"filename": "a.jpg", "content_base64": "eA==", "staged_upload_id": "u"}]},
    )
    assert both.problem is not None
    assert both.problem.code == "invalid_request"


async def test_foreign_project_scope_is_not_found(ingest: ToolHarness) -> None:
    foreign = ToolHarness(
        "other",
        ingest.data_root,
        ingest.pm,
        caller=ingest.caller,
        queue=ingest.queue,
        config_resolver=ingest.config_resolver,
    )
    out = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        foreign,
        {"product": "Bottle", "images": [{"filename": "a.jpg", "content_base64": _b64(_jpeg((5, 5, 5)))}]},
    )
    assert out.problem is not None
    assert out.problem.code in {"project_not_found", "not_found", "project_migration_failed"}
    assert str(ingest.data_root) not in out.problem.detail


async def test_arrange_reorders_and_detaches_without_deleting(ingest: ToolHarness) -> None:
    images = [{"filename": f"{n}.jpg", "content_base64": _b64(_jpeg((n * 40, 0, 0)))} for n in range(1, 4)]
    uploaded = await run_declared_tool(UPLOAD_PRODUCT_REFERENCE_IMAGES, ingest, {"product": "Bottle", "images": images})
    assert uploaded.problem is None
    expected = ["Bottle_1.jpg", "Bottle_2.jpg", "Bottle_3.jpg"]

    unconfirmed = await run_declared_tool(
        ARRANGE_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Bottle", "expected_order": expected, "order": ["Bottle_3.jpg", "Bottle_1.jpg"]},
    )
    assert unconfirmed.problem is not None
    assert unconfirmed.problem.code == "confirmation_required"
    assert unconfirmed.problem.params == {"would_detach": ["Bottle_2.jpg"]}
    assert len(_project(ingest)["products"]["Bottle"]["reference_images"]) == 3

    reordered = await run_declared_tool(
        ARRANGE_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Bottle", "expected_order": expected, "order": list(reversed(expected))},
    )
    assert reordered.problem is None, reordered.problem
    expected = list(reversed(expected))

    out = await run_declared_tool(
        ARRANGE_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {
            "product": "Bottle",
            "expected_order": expected,
            "order": ["Bottle_3.jpg", "Bottle_1.jpg"],
            "confirm_detach": True,
        },
    )

    assert out.problem is None, out.problem
    assert out.value["detached"] == ["Bottle_2.jpg"]
    assert _project(ingest)["products"]["Bottle"]["reference_images"] == [
        "products/refs/Bottle_3.jpg",
        "products/refs/Bottle_1.jpg",
    ]
    assert (ingest.project_path / "products" / "refs" / "Bottle_2.jpg").is_file()

    stale = await run_declared_tool(
        ARRANGE_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Bottle", "expected_order": expected, "order": expected},
    )
    assert stale.problem is not None
    assert stale.problem.code == "reference_images_changed"
    assert stale.problem.params == {"current_order": ["Bottle_3.jpg", "Bottle_1.jpg"]}
    await _assert_no_tasks(ingest)


async def test_reference_precedence_differs_by_route(ingest: ToolHarness) -> None:
    """Storyboard images send the sheet and every original; reference video lets a sheet replace originals."""
    photo = _jpeg((9, 9, 200))
    await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Bottle", "images": [{"filename": "p.jpg", "content_base64": _b64(photo)}]},
    )
    project_dir = ingest.project_path
    unit = {"unit_id": "E1U1", "text": "@Bottle on the table", "duration_seconds": 4}
    without_sheet = resolve_reference_assets(_project(ingest), project_dir, unit)
    assert [(asset.kind, asset.path.name) for asset in without_sheet] == [("original", "Bottle_1.jpg")]

    sheet = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "asset_sheet", "asset_type": "product", "name": "Bottle"},
            "file": {"filename": "sheet.png", "content_base64": _b64(solid_png_bytes((50, 60, 70)))},
        },
    )
    assert sheet.problem is None, sheet.problem

    project = _project(ingest)
    with_sheet = resolve_reference_assets(project, project_dir, unit)
    assert [asset.kind for asset in with_sheet] == ["sheet"]

    script = ingest.pm.load_script("demo", "episode_1.json")
    assembled = storyboard_image_input(
        project, script, episode=1, resource_id="E1S02", observation=project_input_observation(project_dir)
    )
    paths = [Path(ref.artifact_path).name for ref in assembled.references]
    assert paths[:2] == ["Bottle.png", "Bottle_1.jpg"]

    listed = await run_declared_tool(LIST_PRODUCT_REFERENCE_IMAGES, ingest, {"product": "Bottle"})
    consumption = listed.value["effective_consumption"]
    assert consumption["rule"] == "sheet_then_originals"
    assert consumption["image_count_before_clamp"] == 2
    assert consumption["max_reference_images"] == 3
    # Parity with the native storyboard consumer: sheet first, then exactly the listed originals.
    product_refs = [Path(ref.artifact_path).name for ref in assembled.references if "Bottle" in ref.artifact_path]
    assert product_refs == ["Bottle.png", *consumption["originals_sent"]]
    assert consumption["sends_product_sheet"] is True

    # Parity with the native reference-video consumer once the project is on that route.
    def _to_reference_route(project: dict) -> None:
        project["generation_mode"] = "reference_video"

    ingest.pm.update_project("demo", _to_reference_route)
    listed_rv = await run_declared_tool(LIST_PRODUCT_REFERENCE_IMAGES, ingest, {"product": "Bottle"})
    rv = listed_rv.value["effective_consumption"]
    native_rv = resolve_reference_assets(_project(ingest), project_dir, unit)
    assert rv["route"] == "reference_video"
    assert rv["rule"] == "sheet_replaces_originals"
    assert rv["originals_sent"] == [asset.path.name for asset in native_rv if asset.kind == "original"] == []
    assert rv["image_count_before_clamp"] == len(native_rv) == 1


# ---------------------------------------------------------------------------
# MCP-012 finished media
# ---------------------------------------------------------------------------


async def test_asset_sheet_install_is_a_selected_manual_version(ingest: ToolHarness) -> None:
    out = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "asset_sheet", "asset_type": "character", "name": "Alice"},
            "file": {"filename": "alice.png", "content_base64": _b64(solid_png_bytes((200, 10, 10)))},
        },
    )

    assert out.problem is None, out.problem
    assert out.value["path"] == "characters/Alice.png"
    assert out.value["version"] == 1
    project_dir = ingest.project_path
    versions = VersionManager(project_dir).get_versions("characters", "Alice")["versions"]
    assert versions[-1]["source"] == MANUAL_UPLOAD_VERSION_SOURCE
    assert versions[-1]["original_filename"] == "alice.png"
    status = (
        ArtifactCurrencyResolver(project_dir)
        .compare(ArtifactKey.asset_sheet("character", "Alice"), artifact_path="characters/Alice.png")
        .status
    )
    assert status is ArtifactStatus.CURRENT
    assert _project(ingest)["characters"]["Alice"]["character_sheet"] == "characters/Alice.png"
    await _assert_no_tasks(ingest)


async def test_asset_sheet_for_missing_asset_writes_nothing(ingest: ToolHarness) -> None:
    out = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "asset_sheet", "asset_type": "prop", "name": "Lamp"},
            "file": {"filename": "lamp.png", "content_base64": _b64(solid_png_bytes((1, 2, 3)))},
        },
    )
    assert out.problem is not None
    assert out.problem.code == "prop_not_found"
    assert not (ingest.project_path / "props" / "Lamp.png").exists()


async def test_derivative_sheet_install_keeps_description(tmp_path: Path, session_factory, monkeypatch) -> None:
    pm, project_dir = seed_derivative_project(tmp_path)
    use_project_manager(monkeypatch, pm)
    bind_session_factory(monkeypatch, session_factory)
    harness = ToolHarness("demo", tmp_path / "projects", pm, queue=GenerationQueue(session_factory=session_factory))

    out = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        harness,
        {
            "target": {"kind": "character_derivative", "character": "阿岚", "derivative": "战斗装"},
            "file": {"filename": "armor.png", "content_base64": _b64(solid_png_bytes((90, 90, 90)))},
        },
    )

    assert out.problem is None, out.problem
    assert out.value["path"] == derivative_sheet_relative_path("阿岚", "战斗装")
    project = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    derivative = project["characters"]["阿岚"]["derivatives"]["战斗装"]
    assert derivative["description"] == "换上黑色重甲"
    assert derivative["character_sheet"] == out.value["path"]
    listed = await harness.queue.list_tasks(project_name="demo")
    assert listed["total"] == 0


async def test_storyboard_image_and_video_install(ingest: ToolHarness) -> None:
    board = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_image", "script": "episode_1.json", "item_id": "E1S01"},
            "file": {"filename": "board.jpg", "content_base64": _b64(_jpeg((30, 30, 30)))},
        },
    )
    assert board.problem is None, board.problem
    assert board.value["path"] == "storyboards/scene_E1S01.png"

    clip = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 400
    video = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1S01"},
            "file": {"filename": "clip.mp4", "content_base64": _b64(clip)},
        },
    )
    assert video.problem is None, video.problem
    assert video.value["installed_sha256"] == _sha(clip)
    assert video.value["bytes_preserved"] is True
    assert video.value["installed_sha256_advisory"] is True
    assets = ingest.pm.load_script("demo", "episode_1.json")["segments"][0]["generated_assets"]
    assert assets["storyboard_image"] == "storyboards/scene_E1S01.png"
    assert assets["video_clip"] == "videos/scene_E1S01.mp4"
    assert assets["video_thumbnail"] == "thumbnails/scene_E1S01.jpg"

    bad = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1S01"},
            "file": {"filename": "clip.webm", "content_base64": _b64(clip)},
        },
    )
    assert bad.problem is not None
    assert bad.problem.code == "unsupported_video_type"
    missing = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_image", "script": "episode_1.json", "item_id": "E9S99"},
            "file": {"filename": "board.png", "content_base64": _b64(solid_png_bytes((1, 1, 1)))},
        },
    )
    assert missing.problem is not None
    assert missing.problem.code == "segment_not_found"
    await _assert_no_tasks(ingest)


async def test_concurrent_video_installs_keep_distinct_versions(ingest: ToolHarness) -> None:
    clips = [bytes([n]) * 300 for n in (1, 2)]
    outs = await asyncio.gather(
        *(
            run_declared_tool(
                INSTALL_FINISHED_MEDIA,
                ingest,
                {
                    "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1S01"},
                    "file": {"filename": f"c{n}.mp4", "content_base64": _b64(clip)},
                },
            )
            for n, clip in enumerate(clips)
        )
    )
    assert all(out.problem is None for out in outs), [out.problem for out in outs]
    assert sorted(out.value["version"] for out in outs) == [1, 2]
    history = VersionManager(ingest.project_path).get_versions("videos", "E1S01")["versions"]
    assert len(history) == 2
    assert all(entry["source"] == MANUAL_UPLOAD_VERSION_SOURCE for entry in history)
    current = (ingest.project_path / "videos" / "scene_E1S01.mp4").read_bytes()
    assert current in clips


async def test_reference_unit_video_install(tmp_path: Path, session_factory, monkeypatch) -> None:
    pm = ProjectManager(tmp_path / "projects")
    pm.create_project("demo")
    pm.create_project_metadata("demo", "Demo", "Anime", "narration")
    project = pm.load_project("demo")
    project["generation_mode"] = "reference_video"
    project["episodes"] = [{"episode": 1, "title": "E1", "script_file": "scripts/episode_1.json"}]
    pm.save_project("demo", project)
    pm.save_script(
        "demo",
        {
            "episode": 1,
            "title": "E1",
            "content_mode": "narration",
            "generation_mode": "reference_video",
            "video_units": [
                {
                    "unit_id": "E1U1",
                    "shots": [{"text": "t"}],
                    "references": [],
                    "duration_seconds": 4,
                    "generated_assets": {"video_clip": None, "video_uri": "https://stale", "status": "pending"},
                }
            ],
        },
        "episode_1.json",
        validate=False,
    )
    use_project_manager(monkeypatch, pm)
    bind_session_factory(monkeypatch, session_factory)
    monkeypatch.setattr(upload_finalize, "extract_video_thumbnail", _fake_thumbnail)
    harness = ToolHarness(
        "demo",
        tmp_path / "projects",
        pm,
        queue=GenerationQueue(session_factory=session_factory),
        config_resolver=fake_caps_resolver(last_frame=True),
    )
    clip = b"\x07" * 333

    out = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        harness,
        {
            "target": {"kind": "reference_unit_video", "episode": 1, "unit_id": "E1U1"},
            "file": {"filename": "unit.mov", "content_base64": _b64(clip)},
        },
    )

    assert out.problem is None, out.problem
    assert out.value["path"] == "reference_videos/E1U1.mp4"
    assert out.value["bytes_preserved"] is True
    unit = pm.load_script("demo", "episode_1.json")["video_units"][0]
    assert unit["generated_assets"].get("video_uri") is None
    assert unit["generated_assets"]["video_clip"] == "reference_videos/E1U1.mp4"

    # A larger clip arrives through a completed media-transport staging and becomes version 2.
    staged_clip = bytes(range(200)) * 50
    status = await begin_upload(
        pm,
        "demo",
        filename="unit2.mp4",
        size_bytes=len(staged_clip),
        sha256=_sha(staged_clip),
        purpose="unit_video",
        client_id=None,
    )
    await append_upload_chunk(pm, "demo", status.upload_id, index=0, content=staged_clip, client_id=None)
    staged = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        harness,
        {
            "target": {"kind": "reference_unit_video", "episode": 1, "unit_id": "E1U1"},
            "file": {"filename": "unit2.mp4", "staged_upload_id": status.upload_id},
        },
    )
    assert staged.problem is None, staged.problem
    assert staged.value["version"] == 2
    assert staged.value["installed_sha256"] == _sha(staged_clip)

    # The storyboard route is refused on reference-video projects, and so are end frames.
    storyboard = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        harness,
        {
            "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1U1"},
            "file": {"filename": "clip.mp4", "content_base64": _b64(clip)},
        },
    )
    assert storyboard.problem is not None
    assert storyboard.problem.code == "segment_not_found"
    end_frame = await run_declared_tool(
        SET_END_FRAME,
        harness,
        {
            "script": "episode_1.json",
            "item_id": "E1U1",
            "file": {"filename": "end.png", "content_base64": _b64(solid_png_bytes((3, 3, 3)))},
        },
    )
    assert end_frame.problem is not None
    assert end_frame.problem.code == "end_frame_reference_video_unsupported"
    assert (await harness.queue.list_tasks(project_name="demo"))["total"] == 0


async def test_staged_upload_feeds_the_native_video_install(ingest: ToolHarness) -> None:
    """A completed media-transport staging is read as a stream, installed, then released."""
    clip = bytes(range(256)) * 40
    status = await begin_upload(
        ingest.pm,
        "demo",
        filename="big.mp4",
        size_bytes=len(clip),
        sha256=_sha(clip),
        purpose="unit_video",
        client_id=None,
    )
    await append_upload_chunk(ingest.pm, "demo", status.upload_id, index=0, content=clip, client_id=None)

    out = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1S01"},
            "file": {"filename": "big.mp4", "staged_upload_id": status.upload_id},
        },
    )

    assert out.problem is None, out.problem
    assert out.value["input_sha256"] == _sha(clip)
    assert out.value["installed_sha256"] == _sha(clip)
    reused = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1S01"},
            "file": {"filename": "big.mp4", "staged_upload_id": status.upload_id},
        },
    )
    assert reused.problem is not None
    assert reused.problem.code == "upload_not_found"


async def test_staged_product_photo_keeps_its_bytes(ingest: ToolHarness) -> None:
    photo = _jpeg((12, 34, 56))
    status = await begin_upload(
        ingest.pm,
        "demo",
        filename="label.jpg",
        size_bytes=len(photo),
        sha256=_sha(photo),
        purpose="product_reference_image",
        client_id=None,
    )
    await append_upload_chunk(ingest.pm, "demo", status.upload_id, index=0, content=photo, client_id=None)

    out = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {
            "product": "Bottle",
            "images": [
                {"filename": "label.jpg", "staged_upload_id": status.upload_id},
                {"filename": "inline.jpg", "content_base64": _b64(_jpeg((1, 1, 1)))},
            ],
        },
    )

    assert out.problem is None, out.problem
    assert out.value["installed"][0]["sha256"] == _sha(photo)
    assert (ingest.project_path / "products" / "refs" / "Bottle_1.jpg").read_bytes() == photo
    await _assert_no_tasks(ingest)


async def test_staged_upload_for_another_purpose_is_refused_and_writes_nothing(ingest: ToolHarness) -> None:
    photo = _jpeg((77, 7, 7))
    status = await begin_upload(
        ingest.pm,
        "demo",
        filename="p.jpg",
        size_bytes=len(photo),
        sha256=_sha(photo),
        purpose="asset_image",
        client_id=None,
    )
    await append_upload_chunk(ingest.pm, "demo", status.upload_id, index=0, content=photo, client_id=None)

    photos = await run_declared_tool(
        UPLOAD_PRODUCT_REFERENCE_IMAGES,
        ingest,
        {"product": "Bottle", "images": [{"filename": "p.jpg", "staged_upload_id": status.upload_id}]},
    )
    assert photos.problem is not None
    assert photos.problem.code == "upload_purpose_mismatch"
    assert photos.problem.params is not None
    assert photos.problem.params["purpose"] == "asset_image"
    assert list(photos.problem.params["accepted_purposes"]) == ["product_reference_image"]
    assert _project(ingest)["products"]["Bottle"].get("reference_images", []) == []
    refs_dir = ingest.project_path / "products" / "refs"
    assert not refs_dir.exists() or not any(refs_dir.iterdir())

    video = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1S01"},
            "file": {"filename": "p.mp4", "staged_upload_id": status.upload_id},
        },
    )
    assert video.problem is not None
    assert video.problem.code == "upload_purpose_mismatch"
    assert not (ingest.project_path / "videos" / "scene_E1S01.mp4").exists()

    # The same staging still installs for its own purpose.
    sheet = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "asset_sheet", "asset_type": "product", "name": "Bottle"},
            "file": {"filename": "p.jpg", "staged_upload_id": status.upload_id},
        },
    )
    assert sheet.problem is None, sheet.problem
    await _assert_no_tasks(ingest)


async def test_incomplete_or_foreign_staged_upload_is_refused(ingest: ToolHarness) -> None:
    clip = b"\x01" * 64
    status = await begin_upload(
        ingest.pm,
        "demo",
        filename="c.mp4",
        size_bytes=len(clip),
        sha256=_sha(clip),
        purpose="unit_video",
        client_id=None,
    )
    incomplete = await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_video", "script": "episode_1.json", "item_id": "E1S01"},
            "file": {"filename": "c.mp4", "staged_upload_id": status.upload_id},
        },
    )
    assert incomplete.problem is not None
    assert incomplete.problem.code == "upload_incomplete"
    unknown = await run_declared_tool(UPLOAD_BGM, ingest, {"file": {"filename": "a.wav", "staged_upload_id": "0" * 32}})
    assert unknown.problem is not None
    assert unknown.problem.code == "upload_not_found"
    assert not (ingest.project_path / "videos" / "scene_E1S01.mp4").exists()


# ---------------------------------------------------------------------------
# MCP-013 end frames
# ---------------------------------------------------------------------------


async def test_end_frame_set_select_and_clear(ingest: ToolHarness) -> None:
    uploaded = await run_declared_tool(
        SET_END_FRAME,
        ingest,
        {
            "script": "episode_1.json",
            "item_id": "E1S01",
            "file": {"filename": "end.jpg", "content_base64": _b64(_jpeg((10, 120, 10)))},
        },
    )
    assert uploaded.problem is None, uploaded.problem
    assert uploaded.value["end_frame_image"] == "end_frames/scene_E1S01.png"
    assert uploaded.value["video_model"]["last_frame"] is True

    await run_declared_tool(
        INSTALL_FINISHED_MEDIA,
        ingest,
        {
            "target": {"kind": "storyboard_image", "script": "episode_1.json", "item_id": "E1S02"},
            "file": {"filename": "board.png", "content_base64": _b64(solid_png_bytes((200, 0, 200)))},
        },
    )
    selected = await run_declared_tool(
        SET_END_FRAME,
        ingest,
        {
            "script": "episode_1.json",
            "item_id": "E1S01",
            "source": {"kind": "storyboard_image", "script": "episode_1.json", "item_id": "E1S02"},
        },
    )
    assert selected.problem is None, selected.problem
    snapshot = ingest.project_path / "end_frames" / "scene_E1S01.png"
    source = ingest.project_path / "storyboards" / "scene_E1S02.png"
    assert snapshot.read_bytes() == source.read_bytes()
    source.write_bytes(solid_png_bytes((0, 0, 0)))  # later source change does not reach the snapshot
    assert _sha(snapshot.read_bytes()) == selected.value["snapshot_sha256"]

    cleared = await run_declared_tool(CLEAR_END_FRAME, ingest, {"script": "episode_1.json", "item_id": "E1S01"})
    assert cleared.problem is None, cleared.problem
    assert not snapshot.exists()
    segment = ingest.pm.load_script("demo", "episode_1.json")["segments"][0]
    assert not segment.get("end_frame_image")
    await _assert_no_tasks(ingest)


async def test_end_frame_refused_when_model_does_not_send_last_frames(ingest: ToolHarness) -> None:
    ingest.config_resolver = fake_caps_resolver(last_frame=False)
    out = await run_declared_tool(
        SET_END_FRAME,
        ingest,
        {
            "script": "episode_1.json",
            "item_id": "E1S01",
            "file": {"filename": "end.png", "content_base64": _b64(solid_png_bytes((1, 2, 3)))},
        },
    )
    assert out.problem is not None
    assert out.problem.code == "end_frame_unsupported_by_video_model"
    assert not (ingest.project_path / "end_frames").exists()

    ingest.config_resolver = fake_caps_resolver(error=RuntimeError("no provider"))
    unresolved = await run_declared_tool(
        SET_END_FRAME,
        ingest,
        {
            "script": "episode_1.json",
            "item_id": "E1S01",
            "source": {"kind": "asset_sheet", "asset_type": "character", "name": "Alice"},
        },
    )
    assert unresolved.problem is not None
    assert unresolved.problem.code == "video_capability_unavailable"


# ---------------------------------------------------------------------------
# MCP-016 BGM
# ---------------------------------------------------------------------------


async def test_bgm_upload_measures_loudness_and_is_not_inserted(ingest: ToolHarness) -> None:
    audio = wav_bytes(1.5, tone_hz=330)
    out = await run_declared_tool(UPLOAD_BGM, ingest, {"file": {"filename": "rain.wav", "content_base64": _b64(audio)}})

    assert out.problem is None, out.problem
    value = out.value
    assert value["id"].startswith("bgm-")
    assert value["duration_seconds"] == pytest.approx(1.5, abs=0.01)
    assert value["inserted_into_timeline"] is False
    assert value["input_sha256"] == _sha(audio)
    assert (ingest.project_path / "bgm" / f"{value['id']}.wav").read_bytes() == audio
    assert value["id"] in _project(ingest)["bgm"]
    await _assert_no_tasks(ingest)

    problems = []
    for _ in range(2):
        bad = await run_declared_tool(
            UPLOAD_BGM, ingest, {"file": {"filename": "noise.mp3", "content_base64": _b64(b"not audio")}}
        )
        assert bad.problem is not None
        problems.append(bad.problem)
    assert problems[0].code == "bgm_invalid_audio"
    assert problems[0].detail == problems[1].detail
    assert problems[0].detail.startswith("noise.mp3: ")
    assert ".upload" not in problems[0].detail
    assert not [path.name for path in (ingest.project_path / "bgm").iterdir() if path.name.startswith(".")]
