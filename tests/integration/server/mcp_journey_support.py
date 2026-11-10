"""Isolated ArcReel host for the MCP-only production journey.

An external agent reaches ArcReel only through the official remote MCP (``build_remote_mcp_server``) over streamable
HTTP with an API-key Bearer. Everything else here is simulation: a temporary projects root, a per-test database, a fake
API-key verifier and fake image/audio backends installed at the backend-assembly seam, so resolution, MediaGenerator,
version history, ledger and queue all stay real while no provider, network or real credential is ever reached.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import httpx
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP
from mcp.types import BlobResourceContents, EmbeddedResource
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lib.backends.audio_backends.base import AudioCapability, AudioSynthesisResult, VoiceOption
from lib.backends.image_backends.base import ImageCapability, ImageGenerationResult
from lib.db.repositories.task_repo import TaskRepository
from lib.db.repositories.usage_repo import SettlementInput, UsageRepository
from lib.generation.generation_queue import GenerationQueue
from lib.generation.task_failure import encode_failure
from lib.generation.task_failure_encoding import encode_task_failure_message
from lib.project.project_manager import ProjectManager
from server.remote_mcp import mount_remote_mcp
from server.services.tasks.generation_tasks import execute_generation_task
from tests.factories import wav_bytes
from tests.fakes import write_backend_output

API_KEY = "arc-journey-key-0f9e8d7c"
OTHER_API_KEY = "arc-journey-other-1a2b3c4d"
# A credential-shaped secret the fake provider leaks into its failure text; it must never surface through MCP.
PROVIDER_SECRET = "sk-live-journey-5e6f7a8b9c0d1e2f"
SIGNED_URL = "https://cdn.provider.example/out/job-77.png?X-Amz-Signature=deadbeefcafe&X-Amz-Credential=AKIAJOURNEY"

IMAGE_PROVIDER = ("openai", "gpt-image-2")
AUDIO_PROVIDER = ("dashscope", "qwen3-tts-flash")
VOICES = (VoiceOption(id="Cherry", label="Cherry"), VoiceOption(id="Ethan", label="Ethan"))


def png_bytes(color: tuple[int, int, int], size: tuple[int, int] = (64, 96)) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes(color: tuple[int, int, int], size: tuple[int, int] = (80, 80)) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


@dataclass
class FakeImageBackend:
    """Image backend substitute: writes a distinct PNG per call, or raises ``fail_with`` without writing anything."""

    name: str = IMAGE_PROVIDER[0]
    model: str = IMAGE_PROVIDER[1]
    capabilities: ClassVar[set[ImageCapability]] = {ImageCapability.TEXT_TO_IMAGE, ImageCapability.IMAGE_TO_IMAGE}
    calls: list[Any] = field(default_factory=list)
    fail_with: BaseException | None = None

    async def reference_image_limit(self) -> int | None:
        return None

    async def generate(self, request):
        self.calls.append(request)
        if self.fail_with is not None:
            raise self.fail_with
        shade = (40 * len(self.calls)) % 256
        await write_backend_output(request.output_path, png_bytes((shade, 120, 200)))
        return ImageGenerationResult(image_path=request.output_path, provider=self.name, model=self.model)


@dataclass
class FakeAudioBackend:
    """TTS substitute: offers ``VOICES`` and writes a real 3-second WAV whose tone depends on the voice."""

    name: str = AUDIO_PROVIDER[0]
    model: str = AUDIO_PROVIDER[1]
    capabilities: ClassVar[set[AudioCapability]] = {AudioCapability.TEXT_TO_SPEECH}
    calls: list[Any] = field(default_factory=list)

    def list_voices(self) -> list[VoiceOption]:
        return list(VOICES)

    async def synthesize(self, request):
        self.calls.append(request)
        tone = 300 + 100 * [voice.id for voice in VOICES].index(request.voice)
        await write_backend_output(request.output_path, wav_bytes(3.0, tone_hz=tone))
        return AudioSynthesisResult(
            provider=self.name, model=self.model, text=request.text, output_path=request.output_path
        )


@dataclass
class FakeRetrievalWorker:
    """Generation-worker substitute for retrieval resume: records the reopened task instead of polling a provider."""

    resumed: list[dict[str, Any]] = field(default_factory=list)

    async def read_video_poll_timeout_seconds(self) -> int:
        return 600

    async def retry_artifact_download(self, task: dict[str, Any], *, poll_timeout_seconds: int) -> None:
        self.resumed.append({**task, "poll_timeout_seconds": poll_timeout_seconds})


@dataclass
class Journey:
    server: FastMCP
    projects: ProjectManager
    queue: GenerationQueue
    image: FakeImageBackend
    audio: FakeAudioBackend
    root: Path
    #: Retrieval resume target the MCP host was given (the app injects the running generation worker).
    retrieval: FakeRetrievalWorker
    sessions: async_sessionmaker[AsyncSession]
    #: Builds a fresh server over the same projects root, database and queue (a host restart).
    server_factory: Callable[[], FastMCP]
    #: Every tool result text a client saw during the test, for leak checks.
    seen: list[str] = field(default_factory=list)

    def restart_host(self) -> None:
        """Replace the MCP server with a new instance: nothing survives but durable state (files, database)."""
        self.server = self.server_factory()

    @asynccontextmanager
    async def host(self) -> AsyncIterator[None]:
        """Run the server's session manager so several client sessions (``nested=True``) can share one host run."""
        self.server.streamable_http_app()
        async with self.server.session_manager.run():
            yield

    async def call(self, session: ClientSession, tool: str, project: str | None, **arguments: Any) -> Any:
        if project is not None:
            arguments = {"project": project, **arguments}
        result = await session.call_tool(tool, arguments)
        self.seen.append(result_text(result))
        return result

    @asynccontextmanager
    async def session(self, token: str = API_KEY, *, nested: bool = False) -> AsyncIterator[ClientSession]:
        """One MCP client connection; a second (non-nested) session simulates a reconnect after the first closed."""
        app = FastAPI()
        mount_remote_mcp(app, self.server.streamable_http_app())
        async with (
            contextlib.nullcontext() if nested else self.server.session_manager.run(),
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

    async def task_total(self) -> int:
        return int((await self.queue.list_tasks(project_name=None, page_size=500))["total"])

    async def run_one(self, media_type: str) -> dict[str, Any]:
        """Claim and execute one queued task the way the generation worker does, then settle it.

        Execution goes through the production dispatcher ``execute_generation_task``; failures are recorded with the
        worker's own ``encode_task_failure_message`` and are never retried here (the worker does not retry either)."""
        task = await self.queue.claim_next_task(media_type)
        assert task is not None, f"no queued {media_type} task"
        try:
            result = await execute_generation_task(task, claimed_provider_id=task.get("provider_id"))
        except Exception as exc:
            await self.queue.mark_task_failed(task["task_id"], encode_task_failure_message(exc))
        else:
            await self.queue.mark_task_succeeded(task["task_id"], result)
        stored = await self.queue.get_task(task["task_id"])
        assert stored is not None
        return stored

    async def seed_download_failed(self, project: str, resource_id: str) -> str:
        """Simulate the worker side of a paid generation whose provider output could not be downloaded.

        The task was claimed, the provider job ID was persisted, the usage call was settled as failed, and the task
        failed with ``artifact_download_failed``: the state the worker leaves behind. No provider is involved."""
        async with self.sessions() as session:
            repo, usage = TaskRepository(session), UsageRepository(session)
            task = await repo.enqueue(
                project_name=project,
                task_type="image",
                media_type="image",
                resource_id=resource_id,
                payload={},
                provider_id="custom-journey",
            )
            call_id = await usage.start_call(
                project_name=project,
                call_type="image",
                model=IMAGE_PROVIDER[1],
                provider=IMAGE_PROVIDER[0],
                task_id=task["task_id"],
            )
            await usage.finish_call(
                call_id, status="failed", settlement=SettlementInput(cost_amount=0), error_message="download failed"
            )
            await repo.claim_next("image")
            await repo.persist_provider_job_id(task["task_id"], f"job-{resource_id}", endpoint="ce-journey")
            await repo.mark_failed(task["task_id"], encode_failure("artifact_download_failed", detail="403"))
        return str(task["task_id"])


def structured(result: Any) -> dict[str, Any]:
    assert not result.isError, result.content
    assert result.structuredContent is not None
    return result.structuredContent


def problem(result: Any) -> dict[str, Any]:
    assert result.isError, result.structuredContent
    assert result.structuredContent is not None, result.content
    return result.structuredContent["problem"]


def result_text(result: Any) -> str:
    """Everything a client can see in one tool result: text blocks plus structured content."""
    parts = [getattr(block, "text", "") for block in result.content]
    parts.append(json.dumps(result.structuredContent, ensure_ascii=False, default=str))
    return "\n".join(parts)


async def stage_upload(
    journey: Journey, session: ClientSession, project: str, filename: str, content: bytes, purpose: str, chunk: int
) -> str:
    """Stage ``content`` through begin_media_upload/append_media_upload_chunk and return the completed upload_id."""
    began = structured(
        await journey.call(
            session,
            "begin_media_upload",
            project,
            filename=filename,
            size_bytes=len(content),
            sha256=sha256(content),
            purpose=purpose,
        )
    )["media_upload"]
    assert began["chunk_size"] == chunk
    upload_id = began["upload_id"]
    pieces = [content[i : i + chunk] for i in range(0, len(content), chunk)]
    appended: dict[str, Any] = {}
    for index, piece in enumerate(pieces):
        appended = structured(
            await journey.call(
                session,
                "append_media_upload_chunk",
                project,
                upload_id=upload_id,
                index=index,
                content_base64=b64(piece),
                chunk_sha256=sha256(piece),
            )
        )["media_upload"]
    assert appended["complete"] is True
    assert appended["missing_chunks"] == []
    return upload_id


async def describe(
    journey: Journey, session: ClientSession, project: str, selector: dict[str, Any], chunk_size: int = 4096
) -> dict:
    return structured(await journey.call(session, "describe_media", project, selector=selector, chunk_size=chunk_size))[
        "media"
    ]


async def download(journey: Journey, session: ClientSession, project: str, media: dict[str, Any]) -> bytes:
    """Read every chunk as an EmbeddedResource blob (never base64 inside JSON) and verify each chunk digest."""
    received = bytearray()
    for index in range(media["chunk_count"]):
        result = await journey.call(session, "read_media_chunk", project, media_id=media["media_id"], index=index)
        meta = structured(result)["media_chunk"]
        (block,) = [block for block in result.content if isinstance(block, EmbeddedResource)]
        assert isinstance(block.resource, BlobResourceContents)
        assert block.resource.mimeType == "application/octet-stream"
        data = base64.b64decode(block.resource.blob)
        # Bytes travel only in the blob, never inside the structured JSON / text block.
        assert block.resource.blob not in json.dumps(result.structuredContent)
        assert meta["offset"] == len(received)
        assert meta["chunk_sha256"] == sha256(data)
        assert meta["sha256"] == media["sha256"]
        assert meta["final"] is (index == media["chunk_count"] - 1)
        received.extend(data)
    assert sha256(bytes(received)) == media["sha256"]
    return bytes(received)


def assert_no_leaks(texts: list[str], forbidden: list[str]) -> None:
    for text in texts:
        for secret in forbidden:
            assert secret not in text, f"{secret!r} leaked in an MCP result"


def plan_tool_names(value: Any) -> set[str]:
    """Collect every tool name a workflow plan advertises (``tool`` / ``next_tools`` / ``*_tool`` keys, recursively)."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"tool", "tool_name"} or key.endswith("_tool"):
                if isinstance(item, str):
                    found.add(item)
            elif (key in {"tools", "next_tools"} or key.endswith("_tools")) and isinstance(item, list):
                found.update(entry for entry in item if isinstance(entry, str))
            found |= plan_tool_names(item)
    elif isinstance(value, list):
        for item in value:
            found |= plan_tool_names(item)
    return found
