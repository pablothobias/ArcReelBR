"""Remote MCP media transport through a real MCP client: chunked download, resource template, upload staging,
and Jianying packaging, with zero queued tasks."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import McpError
from mcp.types import BlobResourceContents, EmbeddedResource
from pydantic import AnyHttpUrl

from lib.artifacts.version_manager import VersionManager
from lib.edit_timeline import EditTimelineService, RevisionAuthor
from lib.generation.generation_queue import GenerationQueue
from lib.project.project_manager import ProjectManager
from server.agent_toolset.media_transport import MEDIA_TRANSPORT_TOOLS, register_media_resources
from server.agent_toolset.remote import remote_tools
from server.remote_mcp import ArcApiKeyVerifier, mount_remote_mcp
from server.services.media_transport import private_store, uploads
from server.services.media_transport.errors import MediaTransportError
from server.services.media_transport.uploads import resolve_staged_upload
from server.services.presentation.timeline_jianying_draft import TimelineJianyingDraftService
from server.tool_runtime import Services
from tests.factories import install_uploaded_video, wav_bytes

SCRIPT = "episode_1.json"


@pytest.fixture
def media_env(timeline_project: ProjectManager, db_factory, tmp_path: Path):
    timeline_project.create_project("other")
    timeline_project.create_project_metadata("other", "Other", "Anime", "narration")
    queue = GenerationQueue(session_factory=db_factory, project_manager=timeline_project)
    services = Services(projects=timeline_project, workflow_planner=object(), capabilities=object(), queue=queue)

    async def verify_api_key(token: str):
        subjects = {"arc-valid": "apikey:test", "arc-other": "apikey:other"}
        return {"sub": subjects[token], "via": "apikey"} if token in subjects else None

    server = FastMCP(
        "arcreel",
        tools=remote_tools(MEDIA_TRANSPORT_TOOLS, projects=timeline_project, services=services),
        token_verifier=ArcApiKeyVerifier(verify_api_key),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl("http://localhost/"), resource_server_url=None, required_scopes=["arcreel"]
        ),
        stateless_http=True,
        streamable_http_path="/",
        json_response=False,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    register_media_resources(server, timeline_project, services=services)
    return server, timeline_project, queue


@asynccontextmanager
async def _session(server: FastMCP, token: str = "arc-valid", *, nested: bool = False) -> AsyncIterator[ClientSession]:
    """A client session; ``nested`` reuses the session manager already running for an enclosing session."""
    app = FastAPI()
    mount_remote_mcp(app, server.streamable_http_app())
    async with (
        contextlib.nullcontext() if nested else server.session_manager.run(),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=True,
            timeout=60,
        ) as client,
        streamable_http_client("http://localhost/mcp", http_client=client) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session


def _structured(result: Any) -> dict[str, Any]:
    assert result.structuredContent is not None
    return result.structuredContent


def _problem(result: Any) -> dict[str, Any]:
    assert result.isError
    return _structured(result)["problem"]


async def _describe(session: ClientSession, selector: dict[str, Any], chunk_size: int = 4096, project: str = "demo"):
    return await session.call_tool(
        "describe_media", {"project": project, "selector": selector, "chunk_size": chunk_size}
    )


async def _download(session: ClientSession, media: dict[str, Any], project: str = "demo") -> bytes:
    received = bytearray()
    for index in range(media["chunk_count"]):
        result = await session.call_tool(
            "read_media_chunk", {"project": project, "media_id": media["media_id"], "index": index}
        )
        assert not result.isError, result.content
        meta = _structured(result)["media_chunk"]
        (block,) = [block for block in result.content if isinstance(block, EmbeddedResource)]
        assert isinstance(block.resource, BlobResourceContents)
        assert block.resource.mimeType == "application/octet-stream"
        data = base64.b64decode(block.resource.blob)
        # Bytes travel only in the blob, never in the JSON text block.
        assert block.resource.blob not in result.content[0].text
        assert (meta["index"], meta["offset"], meta["length"]) == (index, len(received), len(data))
        assert meta["chunk_sha256"] == hashlib.sha256(data).hexdigest()
        assert meta["final"] is (index == media["chunk_count"] - 1)
        assert meta["sha256"] == media["sha256"]
        received.extend(data)
    return bytes(received)


async def _task_total(queue: GenerationQueue) -> int:
    return (await queue.list_tasks())["total"]


def _install_narration(projects: ProjectManager, tmp_path: Path, unit_id: str, seconds: float) -> Path:
    source = tmp_path / f"{unit_id}-{seconds}.wav"
    source.write_bytes(wav_bytes(seconds, tone_hz=440))
    project_dir = projects.get_project_path("demo")
    versions = VersionManager(project_dir)
    version = versions.add_version("audio", unit_id, "narration", source_file=source)
    record = next(r for r in versions.get_versions("audio", unit_id)["versions"] if r["version"] == version)
    return project_dir / record["file"]


def _no_paths(payload: Any, project_dir: Path) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    assert str(project_dir) not in text
    assert os.path.realpath(project_dir) not in text


async def test_wav_and_mp4_download_chunk_by_chunk_matches_source(media_env, tmp_path: Path) -> None:
    server, projects, queue = media_env
    project_dir = projects.get_project_path("demo")
    install_uploaded_video(project_dir, "reference_videos", "E1U1", seconds=0.5)
    video_record = VersionManager(project_dir).get_versions("reference_videos", "E1U1")["versions"][0]
    video_source = (project_dir / video_record["file"]).read_bytes()
    wav_snapshot = _install_narration(projects, tmp_path, "E1U1", 1.0)

    async with _session(server) as session:
        video = await _describe(session, {"kind": "unit_video", "script": SCRIPT, "unit_id": "E1U1"})
        audio = await _describe(session, {"kind": "narration_audio", "unit_id": "E1U1"})
        again = await _describe(session, {"kind": "narration_audio", "unit_id": "E1U1"})
        video_media = _structured(video)["media"]
        audio_media = _structured(audio)["media"]
        video_bytes = await _download(session, video_media)
        audio_bytes = await _download(session, audio_media)
        uri = f"arcreel://media/demo/{audio_media['media_id']}/1"
        via_resource = await session.read_resource(uri)
        foreign_uri = await _expect_resource_error(session, f"arcreel://media/other/{audio_media['media_id']}/0")
        out_of_range = await session.call_tool(
            "read_media_chunk",
            {"project": "demo", "media_id": audio_media["media_id"], "index": audio_media["chunk_count"]},
        )

    assert video_media["kind"] == "unit_video"
    assert (video_media["mime_type"], video_media["version"]) == ("video/mp4", 1)
    assert video_media["selector"]["version"] == 1
    assert video_bytes == video_source
    assert hashlib.sha256(video_bytes).hexdigest() == video_media["sha256"]
    assert audio_media["mime_type"] == "audio/wav"
    assert audio_media["chunk_count"] > 1
    assert audio_bytes == wav_snapshot.read_bytes()
    assert hashlib.sha256(audio_bytes).hexdigest() == audio_media["sha256"]
    # Deterministic identity: describing unchanged media twice yields the same media_id.
    assert _structured(again)["media"]["media_id"] == audio_media["media_id"]
    (contents,) = via_resource.contents
    assert isinstance(contents, BlobResourceContents)
    assert contents.mimeType == "application/octet-stream"
    assert base64.b64decode(contents.blob) == audio_bytes[4096:8192]
    assert "media_project_mismatch" in foreign_uri
    assert _problem(out_of_range)["code"] == "chunk_out_of_range"
    _no_paths(video_media, project_dir)
    _no_paths(audio_media, project_dir)
    assert await _task_total(queue) == 0


async def _expect_resource_error(session: ClientSession, uri: str) -> str:
    with pytest.raises(McpError) as caught:
        await session.read_resource(uri)
    return str(caught.value)


async def test_pinned_version_survives_new_version_but_changed_bytes_refuse(media_env, tmp_path: Path) -> None:
    server, projects, _queue = media_env
    snapshot = _install_narration(projects, tmp_path, "E1U2", 1.0)

    async with _session(server) as session:
        media = _structured(await _describe(session, {"kind": "narration_audio", "unit_id": "E1U2"}))["media"]
        first = await session.call_tool(
            "read_media_chunk", {"project": "demo", "media_id": media["media_id"], "index": 0}
        )
        # A newer version becomes current; the pinned v1 media_id still reads v1.
        _install_narration(projects, tmp_path, "E1U2", 1.5)
        after_new_version = await session.call_tool(
            "read_media_chunk", {"project": "demo", "media_id": media["media_id"], "index": 1}
        )
        current = _structured(await _describe(session, {"kind": "narration_audio", "unit_id": "E1U2"}))["media"]
        # The v1 bytes themselves change: no mixing, the download must restart.
        data = bytearray(snapshot.read_bytes())
        data[-1] ^= 0xFF
        snapshot.write_bytes(bytes(data))
        changed = await session.call_tool(
            "read_media_chunk", {"project": "demo", "media_id": media["media_id"], "index": 2}
        )
        changed_resource = await _expect_resource_error(session, f"arcreel://media/demo/{media['media_id']}/2")

    assert not first.isError
    assert not after_new_version.isError
    assert media["version"] == 1
    assert current["version"] == 2
    assert current["media_id"] != media["media_id"]
    problem = _problem(changed)
    assert problem["code"] == "media_version_changed"
    assert not [block for block in changed.content if isinstance(block, EmbeddedResource)]
    assert "media_version_changed" in changed_resource


async def test_missing_symlink_traversal_tampered_and_foreign_media_are_refused(media_env, tmp_path: Path) -> None:
    server, projects, _queue = media_env
    project_dir = projects.get_project_path("demo")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"\x89PNG secret")
    snapshot = _install_narration(projects, tmp_path, "E1U1", 1.0)
    linked = _install_narration(projects, tmp_path, "E1U2", 1.0)
    projects.update_project(
        "demo",
        lambda project: project.update(
            {
                "products": {
                    "杯子": {"description": "", "reference_images": ["../../outside.png", "products/refs/absent.png"]}
                }
            }
        ),
    )

    async with _session(server) as session:
        media = _structured(await _describe(session, {"kind": "narration_audio", "unit_id": "E1U1"}))["media"]
        payload, signature = media["media_id"].split(".")
        tampered_payload = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        tampered_payload["s"]["unit_id"] = "E1U2"
        forged = (
            base64.urlsafe_b64encode(json.dumps(tampered_payload, separators=(",", ":")).encode()).rstrip(b"=").decode()
            + "."
            + signature
        )
        tampered = await session.call_tool("read_media_chunk", {"project": "demo", "media_id": forged, "index": 0})
        garbage = await session.call_tool(
            "read_media_chunk", {"project": "demo", "media_id": "not-a-token", "index": 0}
        )
        foreign = await session.call_tool(
            "read_media_chunk", {"project": "other", "media_id": media["media_id"], "index": 0}
        )
        snapshot.unlink()
        missing_read = await session.call_tool(
            "read_media_chunk", {"project": "demo", "media_id": media["media_id"], "index": 0}
        )
        missing_describe = await _describe(session, {"kind": "narration_audio", "unit_id": "E1U1"})
        linked.unlink()
        linked.symlink_to(outside)
        symlink = await _describe(session, {"kind": "narration_audio", "unit_id": "E1U2"})
        traversal = await _describe(session, {"kind": "product_reference_image", "product": "杯子", "index": 0})
        absent_file = await _describe(session, {"kind": "product_reference_image", "product": "杯子", "index": 1})
        absent_index = await _describe(session, {"kind": "product_reference_image", "product": "杯子", "index": 5})
        unknown_unit = await _describe(session, {"kind": "unit_video", "script": SCRIPT, "unit_id": "E9U9"})
        bad_version = await _describe(
            session, {"kind": "unit_video", "script": SCRIPT, "unit_id": "E1U1", "version": 3}
        )

    assert _problem(tampered)["code"] == "media_id_invalid"
    assert _problem(garbage)["code"] == "media_id_invalid"
    assert _problem(foreign)["code"] == "media_project_mismatch"
    assert _problem(missing_read)["code"] == "media_missing"
    assert _problem(missing_describe)["code"] == "media_missing"
    assert _problem(symlink)["code"] == "media_path_refused"
    assert _problem(traversal)["code"] == "media_path_refused"
    assert _problem(absent_file)["code"] == "media_missing"
    assert _problem(absent_index)["code"] == "media_not_found"
    assert _problem(unknown_unit)["code"] == "media_not_found"
    assert _problem(bad_version)["code"] == "version_not_found"
    for result in (symlink, traversal, missing_describe):
        _no_paths(_structured(result), project_dir)
        assert str(tmp_path) not in json.dumps(_structured(result), ensure_ascii=False)


async def test_bgm_describes_and_downloads(media_env, tmp_path: Path) -> None:
    server, projects, _queue = media_env
    project_dir = projects.get_project_path("demo")
    (project_dir / "bgm").mkdir(exist_ok=True)
    content = wav_bytes(0.5, tone_hz=220)
    (project_dir / "bgm" / "bgm-0123abcd.wav").write_bytes(content)
    projects.update_project(
        "demo",
        lambda project: project.update(
            {
                "bgm": {
                    "bgm-0123abcd": {
                        "name": "主题",
                        "file": "bgm/bgm-0123abcd.wav",
                        "duration_us": 500000,
                        "integrated_lufs": -20.0,
                        "gain_db": 4.0,
                        "content_digest": "sha256-v1:" + hashlib.sha256(content).hexdigest(),
                        "uploaded_at": "2026-01-01T00:00:00Z",
                    }
                }
            }
        ),
    )

    async with _session(server) as session:
        media = _structured(await _describe(session, {"kind": "bgm", "bgm_id": "bgm-0123abcd"}))["media"]
        downloaded = await _download(session, media)
        unknown = await _describe(session, {"kind": "bgm", "bgm_id": "bgm-ffffffff"})

    assert downloaded == content
    assert _problem(unknown)["code"] == "media_not_found"


@pytest.fixture
def small_upload_chunks(monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(uploads, "UPLOAD_CHUNK_SIZE", 4096)
    return 4096


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


async def test_upload_staging_round_trip_and_refusals(
    media_env, small_upload_chunks: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    server, projects, queue = media_env
    content = os.urandom(small_upload_chunks * 2 + 123)
    digest = hashlib.sha256(content).hexdigest()
    chunks = [content[i : i + small_upload_chunks] for i in range(0, len(content), small_upload_chunks)]
    begin_args = {
        "project": "demo",
        "filename": "clip.mp4",
        "size_bytes": len(content),
        "sha256": digest,
        "purpose": "unit_video",
    }

    async with _session(server) as session:
        began = _structured(await session.call_tool("begin_media_upload", begin_args))["media_upload"]
        upload_id = began["upload_id"]
        # Out of order, with one resend.
        for index in (2, 0, 0):
            step = await session.call_tool(
                "append_media_upload_chunk",
                {"project": "demo", "upload_id": upload_id, "index": index, "content_base64": _b64(chunks[index])},
            )
            assert not step.isError, step.content
        partial = _structured(step)["media_upload"]
        wrong_length = await session.call_tool(
            "append_media_upload_chunk",
            {"project": "demo", "upload_id": upload_id, "index": 1, "content_base64": _b64(b"short")},
        )
        bad_chunk_digest = await session.call_tool(
            "append_media_upload_chunk",
            {
                "project": "demo",
                "upload_id": upload_id,
                "index": 1,
                "content_base64": _b64(chunks[1]),
                "chunk_sha256": "0" * 64,
            },
        )
        foreign_project = await session.call_tool(
            "append_media_upload_chunk",
            {"project": "other", "upload_id": upload_id, "index": 1, "content_base64": _b64(chunks[1])},
        )
        incomplete_error = None
        try:
            await resolve_staged_upload(projects, "demo", upload_id, client_id="apikey:test", use_request_client=False)
        except MediaTransportError as exc:
            incomplete_error = exc
        done = _structured(
            await session.call_tool(
                "append_media_upload_chunk",
                {"project": "demo", "upload_id": upload_id, "index": 1, "content_base64": _b64(chunks[1])},
            )
        )["media_upload"]

        bad = _structured(await session.call_tool("begin_media_upload", {**begin_args, "sha256": "f" * 64}))[
            "media_upload"
        ]
        for index, chunk in enumerate(chunks):
            mismatch = await session.call_tool(
                "append_media_upload_chunk",
                {"project": "demo", "upload_id": bad["upload_id"], "index": index, "content_base64": _b64(chunk)},
            )
        after_mismatch = await session.call_tool(
            "append_media_upload_chunk",
            {"project": "demo", "upload_id": bad["upload_id"], "index": 0, "content_base64": _b64(chunks[0])},
        )

        stale = _structured(await session.call_tool("begin_media_upload", begin_args))["media_upload"]
        monkeypatch.setattr(private_store, "clock", lambda: stale["expires_at"] + 1)
        expired = await session.call_tool(
            "append_media_upload_chunk",
            {"project": "demo", "upload_id": stale["upload_id"], "index": 0, "content_base64": _b64(chunks[0])},
        )
        monkeypatch.undo()
        monkeypatch.setattr(uploads, "UPLOAD_CHUNK_SIZE", small_upload_chunks)
        too_large = await session.call_tool("begin_media_upload", {**begin_args, "size_bytes": 10 * 1024**3})
        async with _session(server, token="arc-other", nested=True) as other:
            other_client = await other.call_tool(
                "append_media_upload_chunk",
                {"project": "demo", "upload_id": upload_id, "index": 1, "content_base64": _b64(chunks[1])},
            )

    assert (began["chunk_size"], began["chunk_count"], began["complete"]) == (small_upload_chunks, 3, False)
    assert (partial["received_chunks"], partial["missing_chunks"], partial["complete"]) == (2, [1], False)
    assert _problem(wrong_length)["code"] == "upload_chunk_invalid"
    assert _problem(bad_chunk_digest)["code"] == "upload_chunk_invalid"
    assert _problem(foreign_project)["code"] == "upload_not_found"
    assert getattr(incomplete_error, "code", None) == "upload_incomplete"
    assert done["complete"] is True
    assert done["missing_chunks"] == []
    assert _problem(mismatch)["code"] == "upload_digest_mismatch"
    assert _problem(after_mismatch)["code"] == "upload_not_found"
    assert _problem(expired)["code"] == "upload_expired"
    assert too_large.isError
    assert _problem(other_client)["code"] == "upload_not_found"

    with await resolve_staged_upload(
        projects, "demo", upload_id, client_id="apikey:test", use_request_client=False
    ) as staged:
        assert (staged.filename, staged.size_bytes, staged.sha256, staged.purpose) == (
            "clip.mp4",
            len(content),
            digest,
            "unit_video",
        )
        assert staged.stream.read() == content
    with pytest.raises(MediaTransportError) as other_caller:
        await resolve_staged_upload(projects, "demo", upload_id, client_id="apikey:other", use_request_client=False)
    assert getattr(other_caller.value, "code", None) == "upload_not_found"
    # Staging never installs media and never queues work.
    project_dir = projects.get_project_path("demo")
    assert not (project_dir / "reference_videos").exists() or not any((project_dir / "reference_videos").iterdir())
    assert await _task_total(queue) == 0


async def _timeline(projects: ProjectManager) -> str:
    readout = await EditTimelineService(projects).create_from_script(
        "demo", episode=1, name="完整版", author=RevisionAuthor(kind="arcreel_agent")
    )
    return readout.timeline.id


async def test_jianying_package_substitutes_draft_path_and_version_without_rendering(media_env) -> None:
    server, projects, queue = media_env
    project_dir = projects.get_project_path("demo")
    for unit in ("E1U1", "E1U2"):
        install_uploaded_video(project_dir, "reference_videos", unit, seconds=0.5)
    timeline_id = await _timeline(projects)
    base = {"project": "demo", "timeline": timeline_id, "narration": "without_narration", "chunk_size": 1024 * 1024}

    async with _session(server) as session:
        not_exported = await session.call_tool(
            "prepare_jianying_package", {**base, "draft_path": "/Users/me/Drafts", "jianying_version": "6"}
        )
        rendered = await TimelineJianyingDraftService(projects).render(
            "demo", timeline_id, narration="without_narration"
        )
        artifact = project_dir / rendered.artifact_path
        artifact_before = artifact.read_bytes()
        tasks_before = await _task_total(queue)
        v6 = await session.call_tool(
            "prepare_jianying_package",
            {
                **base,
                "draft_path": "/Users/me/JianyingPro Drafts",
                "jianying_version": "6",
                "expected_draft_version": 1,
            },
        )
        v5 = await session.call_tool(
            "prepare_jianying_package", {**base, "draft_path": "D:\\Jianying\\Drafts", "jianying_version": "5"}
        )
        stale_version = await session.call_tool(
            "prepare_jianying_package",
            {**base, "draft_path": "/Users/me/Drafts", "jianying_version": "6", "expected_draft_version": 7},
        )
        bad_path = await session.call_tool(
            "prepare_jianying_package", {**base, "draft_path": "/Users/me/\x07Drafts", "jianying_version": "6"}
        )
        v6_payload = _structured(v6)
        v6_zip = await _download(session, v6_payload["media"])
        v5_zip = await _download(session, _structured(v5)["media"])
        redescribed = await _describe(
            session,
            {"kind": "jianying_package", "package_id": v6_payload["jianying_package"]["package_id"]},
            chunk_size=1024 * 1024,
        )

    assert _problem(not_exported)["code"] == "jianying_draft_not_exported"
    package = v6_payload["jianying_package"]
    media = v6_payload["media"]
    assert media["kind"] == "jianying_package"
    assert media["mime_type"] == "application/zip"
    assert package["sha256"] == media["sha256"] == hashlib.sha256(v6_zip).hexdigest()
    assert (package["jianying_version"], package["draft_version"]) == ("6", 1)
    assert _structured(redescribed)["media"]["media_id"] == media["media_id"]
    folder = package["draft_folder"]
    with zipfile.ZipFile(io.BytesIO(v6_zip)) as archive:
        names = archive.namelist()
        content = archive.read(f"{folder}/draft_info.json").decode("utf-8")
    assert f"{folder}/draft_content.json" not in names
    assert f"/Users/me/JianyingPro Drafts/{folder}/assets/" in content
    assert "{{ARCREEL_JIANYING_ASSETS}}" not in content
    with zipfile.ZipFile(io.BytesIO(v5_zip)) as archive:
        v5_content = archive.read(f"{folder}/draft_content.json").decode("utf-8")
    assert "D:\\\\Jianying\\\\Drafts" in v5_content or "D:\\Jianying\\Drafts" in v5_content
    assert _problem(stale_version)["code"] == "jianying_draft_version_changed"
    assert _problem(bad_path)["code"] == "jianying_path_illegal"
    # No re-render, no queued work, and the registered draft is untouched.
    assert artifact.read_bytes() == artifact_before
    assert await _task_total(queue) == tasks_before == 0
    _no_paths(v6_payload, project_dir)
