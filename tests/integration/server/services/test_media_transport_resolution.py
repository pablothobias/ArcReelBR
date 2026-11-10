"""Media-transport selector resolution for kinds owned by other native services: voice references, asset sheets
without history, grid composites and Jianying package expiry."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import pytest

from lib.project.project_manager import ProjectManager
from server.services.media_transport import describe_media, parse_selector, private_store, read_media_chunk
from server.services.media_transport.errors import MediaTransportError
from tests.factories import wav_bytes


class _Queue:
    def __init__(self, tasks: dict[str, dict[str, Any]]) -> None:
        self._tasks = tasks

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._tasks.get(task_id)


@pytest.fixture
def projects(timeline_project: ProjectManager) -> ProjectManager:
    return timeline_project


async def _bytes(projects: ProjectManager, descriptor: Any, queue: Any) -> bytes:
    data = b""
    for index in range(descriptor.chunk_count):
        chunk = await read_media_chunk(projects, "demo", descriptor.media_id, index, queue=queue)
        data += chunk.data
    return data


async def test_voice_reference_and_sample_resolve_through_the_voice_reference_service(projects: ProjectManager) -> None:
    project_dir = projects.get_project_path("demo")
    reference = wav_bytes(2.5, tone_hz=330)
    sample = wav_bytes(3.0, tone_hz=550)
    (project_dir / "characters" / "refs_audio").mkdir(parents=True, exist_ok=True)
    (project_dir / "characters" / "refs_audio" / "林.wav").write_bytes(reference)
    (project_dir / "audio").mkdir(exist_ok=True)
    (project_dir / "audio" / "segment_voice_sample__林__t1.wav").write_bytes(sample)
    projects.update_project(
        "demo",
        lambda project: project.update(
            {
                "characters": {
                    "林": {"description": "", "reference_audio": "characters/refs_audio/林.wav"},
                    "无声": {"description": ""},
                }
            }
        ),
    )
    queue = _Queue(
        {
            "t1": {
                "task_id": "t1",
                "project_name": "demo",
                "task_type": "voice_sample",
                "status": "succeeded",
                "resource_id": "林",
                "result": {
                    "file_path": "audio/segment_voice_sample__林__t1.wav",
                    "sha256": hashlib.sha256(sample).hexdigest(),
                },
            },
            "t2": {"task_id": "t2", "project_name": "demo", "task_type": "voice_sample", "status": "running"},
            "t3": {"task_id": "t3", "project_name": "other", "task_type": "voice_sample", "status": "succeeded"},
        }
    )

    bound = await describe_media(
        projects, "demo", parse_selector({"kind": "character_voice_reference", "character": "林"}), queue=queue
    )
    previewed = await describe_media(
        projects, "demo", parse_selector({"kind": "voice_sample", "task_id": "t1"}), queue=queue
    )

    assert (bound.mime_type, bound.version, bound.sha256) == ("audio/wav", None, hashlib.sha256(reference).hexdigest())
    assert await _bytes(projects, bound, queue) == reference
    assert await _bytes(projects, previewed, queue) == sample
    for selector, code in (
        ({"kind": "character_voice_reference", "character": "无声"}, "media_missing"),
        ({"kind": "character_voice_reference", "character": "不存在"}, "character_not_found"),
        ({"kind": "voice_sample", "task_id": "t2"}, "voice_sample_not_ready"),
        ({"kind": "voice_sample", "task_id": "t3"}, "task_not_found"),
    ):
        with pytest.raises(MediaTransportError) as caught:
            await describe_media(projects, "demo", parse_selector(selector), queue=queue)
        assert caught.value.code == code


async def test_asset_sheet_without_history_and_grid_composite_use_registered_current_files(
    projects: ProjectManager,
) -> None:
    project_dir = projects.get_project_path("demo")
    (project_dir / "characters").mkdir(exist_ok=True)
    sheet = b"\x89PNG\r\n\x1a\nsheet"
    (project_dir / "characters" / "林.png").write_bytes(sheet)
    projects.update_project(
        "demo",
        lambda project: project.update(
            {"characters": {"林": {"description": "", "character_sheet": "characters/林.png"}}}
        ),
    )
    (project_dir / "grids").mkdir(exist_ok=True)
    (project_dir / "grids" / "grid_0123456789ab.json").write_text("{}", encoding="utf-8")
    (project_dir / "grids" / "grid_0123456789ab.png").write_bytes(b"\x89PNG\r\n\x1a\ngrid")
    queue = _Queue({})

    asset = await describe_media(
        projects, "demo", parse_selector({"kind": "asset_sheet", "asset_type": "character", "name": "林"}), queue=queue
    )
    grid = await describe_media(
        projects, "demo", parse_selector({"kind": "grid_composite", "grid_id": "grid_0123456789ab"}), queue=queue
    )

    assert (asset.version, asset.mime_type) == (None, "image/png")
    assert await _bytes(projects, asset, queue) == sheet
    assert await _bytes(projects, grid, queue) == b"\x89PNG\r\n\x1a\ngrid"
    with pytest.raises(MediaTransportError) as missing_grid:
        await describe_media(
            projects, "demo", parse_selector({"kind": "grid_composite", "grid_id": "grid_ffffffffffff"}), queue=queue
        )
    assert missing_grid.value.code == "media_not_found"


async def test_expired_jianying_package_is_refused_and_removed(
    projects: ProjectManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = projects.get_project_path("demo")
    package_id = private_store.new_record_id()
    directory = private_store.record_dir(project_dir, "mcp_packages", package_id, create=True)
    (directory / "package.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    private_store.write_meta(directory, {"kind": "jianying_package", "expires_at": private_store.clock() + 60})
    selector = parse_selector({"kind": "jianying_package", "package_id": package_id})
    queue = _Queue({})

    live = await describe_media(projects, "demo", selector, queue=queue)
    monkeypatch.setattr(private_store, "clock", lambda: 10**12)
    with pytest.raises(MediaTransportError) as expired:
        await read_media_chunk(projects, "demo", live.media_id, 0, queue=queue)

    assert live.mime_type == "application/zip"
    assert expired.value.code == "media_missing"
    assert not await asyncio.to_thread(Path(directory).exists)


@pytest.mark.parametrize(
    ("selector", "patch"),
    [
        (
            {"kind": "product_reference_image", "product": "杯子", "index": 0},
            {"products": {"杯子": {"description": "", "reference_images": ["project.json"]}}},
        ),
        (
            {"kind": "product_reference_image", "product": "杯子", "index": 0},
            {"products": {"杯子": {"description": "", "reference_images": ["products/refs/../../project.json"]}}},
        ),
        (
            {"kind": "asset_sheet", "asset_type": "character", "name": "林"},
            {"characters": {"林": {"description": "", "character_sheet": "scripts/episode_1.json"}}},
        ),
        (
            {"kind": "asset_sheet", "asset_type": "character", "name": "林"},
            {"characters": {"林": {"description": "", "character_sheet": "characters/refs_audio/林.wav"}}},
        ),
        (
            {"kind": "asset_sheet", "asset_type": "character", "name": "林"},
            {"characters": {"林": {"description": "", "character_sheet": "STAGED"}}},
        ),
        (
            {"kind": "character_voice_reference", "character": "林"},
            {"characters": {"林": {"description": "", "reference_audio": "project.json"}}},
        ),
    ],
)
async def test_metadata_pointers_outside_canonical_directories_are_refused(
    projects: ProjectManager, selector: dict[str, Any], patch: dict[str, Any]
) -> None:
    """A project.json string must not stream project metadata, scripts or another client's staged upload."""
    from server.services.media_transport import uploads

    project_dir = projects.get_project_path("demo")
    (project_dir / "characters" / "refs_audio").mkdir(parents=True, exist_ok=True)
    (project_dir / "characters" / "refs_audio" / "林.wav").write_bytes(wav_bytes(2.5))
    staged = await uploads.begin_upload(
        projects,
        "demo",
        filename="x.png",
        size_bytes=4,
        sha256=hashlib.sha256(b"\x00" * 4).hexdigest(),
        purpose="asset_image",
        client_id="apikey:victim",
    )
    staged_path = f".arcreel/mcp_uploads/{staged.upload_id}/data.part"
    if "characters" in patch and patch["characters"]["林"].get("character_sheet") == "STAGED":
        patch = {"characters": {"林": {"description": "", "character_sheet": staged_path}}}
    projects.update_project("demo", lambda project: project.update(patch))

    with pytest.raises(MediaTransportError) as refused:
        await describe_media(projects, "demo", parse_selector(selector), queue=_Queue({}))

    # The voice-reference service applies its own refs_audio check first and reports it under its own key.
    assert refused.value.code in {"media_path_refused", "voice_reference_path_invalid"}


async def test_final_cut_descriptor_reports_stale_renders(
    projects: ProjectManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lib.artifacts.artifact_manifest import ArtifactStatus
    from lib.final_cut.service import FinalCutService, FinalCutStatus

    project_dir = projects.get_project_path("demo")
    artifact = "renders/episode_1/tl-00000001/final_cut.without_narration.no_subtitles.mp4"
    (project_dir / artifact).parent.mkdir(parents=True)
    (project_dir / artifact).write_bytes(b"\x00\x00\x00\x18ftypmp42 final")

    async def stale_status(self, project_name, timeline_id, *, narration=None, subtitles=None) -> FinalCutStatus:
        return FinalCutStatus(
            episode=1,
            timeline_id=timeline_id,
            narration="without_narration",
            subtitles="no_subtitles",
            status=ArtifactStatus.STALE,
            artifact_path=artifact,
            version=2,
            rendered_at="2026-01-01T00:00:00Z",
        )

    monkeypatch.setattr(FinalCutService, "status", stale_status)
    descriptor = await describe_media(
        projects, "demo", parse_selector({"kind": "final_cut", "timeline": "tl-00000001"}), queue=_Queue({})
    )

    assert (descriptor.status, descriptor.version, descriptor.mime_type) == ("stale", 2, "video/mp4")
    assert descriptor.selector["subtitles"] == "no_subtitles"


async def test_reads_stay_available_on_a_migration_failed_project(projects: ProjectManager) -> None:
    from lib.project.project_migration_failure import record_migration_failure
    from lib.project.project_schema import CURRENT_PROJECT_SCHEMA_VERSION
    from server.agent_toolset.declaration import invoke_declaration
    from server.agent_toolset.media_transport import BEGIN_MEDIA_UPLOAD, DESCRIBE_MEDIA
    from server.tool_runtime import CallerContext, ProjectScope, Services

    project_dir = projects.get_project_path("demo")
    (project_dir / "bgm").mkdir(exist_ok=True)
    (project_dir / "bgm" / "bgm-0123abcd.wav").write_bytes(wav_bytes(0.2))
    projects.update_project(
        "demo",
        lambda project: project.update(
            {
                "bgm": {
                    "bgm-0123abcd": {
                        "name": "a",
                        "file": "bgm/bgm-0123abcd.wav",
                        "duration_us": 200000,
                        "integrated_lufs": -20.0,
                        "gain_db": 4.0,
                        "content_digest": "sha256-v1:" + "0" * 64,
                        "uploaded_at": "2026-01-01T00:00:00Z",
                    }
                }
            }
        ),
    )
    record_migration_failure(project_dir, RuntimeError("x"), schema_version=CURRENT_PROJECT_SCHEMA_VERSION)
    services = Services(projects=projects, workflow_planner=object(), capabilities=object(), queue=_Queue({}))
    scope = ProjectScope(project_name="demo", data_root=projects.data_root)
    caller = CallerContext(user_id="u", source="mcp")

    described = await invoke_declaration(
        DESCRIBE_MEDIA, {"selector": {"kind": "bgm", "bgm_id": "bgm-0123abcd"}}, scope, caller, services
    )
    blocked = await invoke_declaration(
        BEGIN_MEDIA_UPLOAD,
        {"filename": "a.mp4", "size_bytes": 1, "sha256": "0" * 64, "purpose": "unit_video"},
        scope,
        caller,
        services,
    )

    assert described.problem is None
    assert described.value is not None
    assert blocked.problem is not None
    assert blocked.problem.code == "project_migration_failed"
