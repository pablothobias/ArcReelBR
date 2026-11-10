"""Describe media and read verified chunks.

``describe`` resolves a selector, materializes object-storage working files like ``serve_project_file``
(``ensure_work_file`` under ``hold_work_file``), opens the file without following links, and returns a descriptor whose
``media_id`` binds project, kind, pinned selector, version, sha256 and chunk size. ``read_chunk`` verifies the token,
re-resolves its pinned selector on every call, and serves a chunk only while the file still has the bound version
and sha256; otherwise it refuses with ``media_version_changed`` so a client never mixes bytes of two versions."""

from __future__ import annotations

import asyncio
import hashlib
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from lib.material.work_files import (
    MaterialConnectionUnavailableError,
    MaterialFetchFailedError,
    ensure_work_file,
    hold_work_file,
)
from lib.project.project_manager import ProjectManager
from server.services.media_transport.errors import (
    MEDIA_CHUNK_OUT_OF_RANGE,
    MEDIA_ID_INVALID,
    MEDIA_UNAVAILABLE,
    MEDIA_VERSION_CHANGED,
    MediaTransportError,
)
from server.services.media_transport.files import fd_digest, open_project_media, read_verified_range
from server.services.media_transport.identity import MediaIdentity, decode_media_id, encode_media_id
from server.services.media_transport.resolution import ResolvedMedia, resolve_media
from server.services.media_transport.selectors import parse_selector

DEFAULT_CHUNK_SIZE = 256 * 1024
MAX_CHUNK_SIZE = 4 * 1024 * 1024
MIN_CHUNK_SIZE = 4 * 1024
RESOURCE_URI_TEMPLATE = "arcreel://media/{project}/{media_id}/{index}"


def chunk_count(size: int, chunk_size: int) -> int:
    return max(1, -(-size // chunk_size))


def resource_uri(project: str, media_id: str, index: int) -> str:
    return f"arcreel://media/{project}/{media_id}/{index}"


@dataclass(frozen=True, slots=True)
class MediaDescriptor:
    media_id: str
    kind: str
    selector: dict[str, Any]
    version: int | None
    mime_type: str
    size_bytes: int
    sha256: str
    chunk_size: int
    chunk_count: int
    resource_uri_template: str
    #: final_cut only: ``current`` or ``stale`` (rendered from an older timeline revision or inputs; still downloadable).
    status: str | None = None


@dataclass(frozen=True, slots=True)
class MediaChunk:
    media_id: str
    index: int
    offset: int
    length: int
    chunk_sha256: str
    total_size: int
    sha256: str
    final: bool
    mime_type: str
    data: bytes


async def _materialize(project_dir: Path, resolved: ResolvedMedia, holds: ExitStack) -> None:
    holds.enter_context(hold_work_file(project_dir / resolved.relative_path))
    try:
        await ensure_work_file(project_dir, resolved.relative_path)
    except (MaterialConnectionUnavailableError, MaterialFetchFailedError):
        raise MediaTransportError(MEDIA_UNAVAILABLE, "object storage could not provide this media file") from None


def _digest(project_dir: Path, relative: str) -> tuple[str, int]:
    with open_project_media(project_dir, relative) as fd:
        sha256, size, _stat = fd_digest(fd)
    return sha256, size


async def describe_media(
    projects: ProjectManager,
    project_name: str,
    selector: Any,
    *,
    queue: Any,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> MediaDescriptor:
    resolved = await resolve_media(projects, project_name, selector, queue=queue)
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)
    with ExitStack() as holds:
        await _materialize(project_dir, resolved, holds)
        sha256, size = await asyncio.to_thread(_digest, project_dir, resolved.relative_path)
    identity = MediaIdentity(
        project=project_name,
        kind=resolved.kind,
        selector=resolved.selector,
        version=resolved.version,
        sha256=sha256,
        chunk_size=chunk_size,
    )
    return MediaDescriptor(
        media_id=encode_media_id(identity),
        kind=resolved.kind,
        selector=resolved.selector,
        version=resolved.version,
        mime_type=resolved.mime_type,
        size_bytes=size,
        sha256=sha256,
        chunk_size=chunk_size,
        chunk_count=chunk_count(size, chunk_size),
        resource_uri_template=RESOURCE_URI_TEMPLATE,
        status=resolved.status,
    )


async def _reresolve(projects: ProjectManager, identity: MediaIdentity, *, queue: Any) -> ResolvedMedia:
    try:
        selector = parse_selector(identity.selector)
    except ValidationError:
        raise MediaTransportError(MEDIA_ID_INVALID, "media_id selector is not understood by this server") from None
    resolved = await resolve_media(projects, identity.project, selector, queue=queue)
    if resolved.version != identity.version:
        raise MediaTransportError(
            MEDIA_VERSION_CHANGED, "media version changed since this media_id was issued; describe it again"
        )
    return resolved


async def read_media_chunk(
    projects: ProjectManager,
    project_name: str,
    media_id: str,
    index: int,
    *,
    queue: Any,
    chunk_size: int | None = None,
) -> MediaChunk:
    """Read chunk ``index``; ``chunk_size`` defaults to the size bound in ``media_id`` and is capped at 4 MiB."""
    identity = decode_media_id(media_id, project=project_name)
    size_per_chunk = chunk_size or identity.chunk_size
    if not MIN_CHUNK_SIZE <= size_per_chunk <= MAX_CHUNK_SIZE:
        raise MediaTransportError(MEDIA_ID_INVALID, "chunk size is out of range")
    if index < 0:
        raise MediaTransportError(MEDIA_CHUNK_OUT_OF_RANGE, "chunk index must not be negative")
    resolved = await _reresolve(projects, identity, queue=queue)
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)

    def _read() -> tuple[bytes, int, int]:
        offset = index * size_per_chunk
        with open_project_media(project_dir, resolved.relative_path) as fd:
            data, total = read_verified_range(fd, expected_sha256=identity.sha256, offset=offset, length=size_per_chunk)
        count = chunk_count(total, size_per_chunk)
        if index < 0 or index >= count:
            raise MediaTransportError(
                MEDIA_CHUNK_OUT_OF_RANGE, f"chunk index must be within 0..{count - 1}", chunk_count=count
            )
        return data, offset, total

    with ExitStack() as holds:
        await _materialize(project_dir, resolved, holds)
        data, offset, total = await asyncio.to_thread(_read)
    return MediaChunk(
        media_id=media_id,
        index=index,
        offset=offset,
        length=len(data),
        chunk_sha256=hashlib.sha256(data).hexdigest(),
        total_size=total,
        sha256=identity.sha256,
        final=offset + len(data) >= total,
        mime_type=resolved.mime_type,
        data=data,
    )


__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "MAX_CHUNK_SIZE",
    "MIN_CHUNK_SIZE",
    "RESOURCE_URI_TEMPLATE",
    "MediaChunk",
    "MediaDescriptor",
    "chunk_count",
    "describe_media",
    "read_media_chunk",
    "resource_uri",
]
