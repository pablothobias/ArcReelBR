"""Chunked upload staging for client files too large for one inline ``content_base64`` argument.

A staged upload lives at ``<project>/.arcreel/mcp_uploads/<upload_id>/`` (128-bit random ID, symlink-guarded), is
scoped to its project and to the authenticated MCP client that began it, and expires after a TTL refreshed by each
appended chunk; expired uploads are swept opportunistically on begin, append and resolve. Each purpose is capped at the
native install limit for that media, and active uploads are limited per client and in total bytes per project. A
verified upload is immutable: further appends are refused. Staging only collects and verifies bytes: it never installs
media. Consumers call :func:`resolve_staged_upload` to obtain a verified open stream
and feed the native install transaction (for example ``stage_uploaded_video_stream`` /
``stage_uploaded_bytes`` in ``server/services/currency/upload_finalize.py``), which keeps its own size limits, then
call :func:`discard_staged_upload`."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from lib.bgm.library import BGM_MAX_BYTES
from lib.infra.async_thread import run_sync_transaction
from lib.infra.content_digest import digest_stream
from lib.project.project_manager import ProjectManager
from lib.speech.audio_utils import AUDIO_REFERENCE_MAX_BYTES
from server.services.currency.upload_finalize import UPLOAD_IMAGE_MAX_BYTES, UPLOAD_VIDEO_MAX_BYTES
from server.services.media_transport import private_store
from server.services.media_transport.errors import (
    UPLOAD_ALREADY_COMPLETE,
    UPLOAD_CHUNK_INVALID,
    UPLOAD_DIGEST_MISMATCH,
    UPLOAD_EXPIRED,
    UPLOAD_INCOMPLETE,
    UPLOAD_NOT_FOUND,
    UPLOAD_PURPOSE_MISMATCH,
    UPLOAD_QUOTA_EXCEEDED,
    UPLOAD_STAGING_REFUSED,
    UPLOAD_TOO_LARGE,
    MediaTransportError,
)

UPLOAD_AREA = "mcp_uploads"
DATA_FILE = "data.part"
#: Raw bytes per chunk; its base64 form (~5.4 MiB) stays far below the remote request-body limit.
UPLOAD_CHUNK_SIZE = 4 * 1024 * 1024
#: Per-purpose ceilings equal to the native install limits for that media; staging never accepts more than an
#: installer would. Consumers still apply native validation (type, duration, decoding) on install.
UPLOAD_PURPOSE_LIMITS: dict[str, int] = {
    "unit_video": UPLOAD_VIDEO_MAX_BYTES,
    "asset_image": UPLOAD_IMAGE_MAX_BYTES,
    "derivative_image": UPLOAD_IMAGE_MAX_BYTES,
    "product_reference_image": UPLOAD_IMAGE_MAX_BYTES,
    "storyboard_image": UPLOAD_IMAGE_MAX_BYTES,
    "end_frame": UPLOAD_IMAGE_MAX_BYTES,
    "grid_composite": UPLOAD_IMAGE_MAX_BYTES,
    "reference_audio": AUDIO_REFERENCE_MAX_BYTES,
    "bgm": BGM_MAX_BYTES,
}
UPLOAD_PURPOSES: tuple[str, ...] = tuple(UPLOAD_PURPOSE_LIMITS)
MAX_UPLOAD_BYTES = max(UPLOAD_PURPOSE_LIMITS.values())
#: Active (unexpired) uploads one client may hold in one project.
MAX_ACTIVE_UPLOADS_PER_CLIENT = 4
#: Declared bytes of all active uploads in one project.
MAX_STAGED_BYTES_PER_PROJECT = 2 * MAX_UPLOAD_BYTES
UPLOAD_TTL_SECONDS = 2 * 60 * 60
_FILENAME_MAX = 255
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _not_found(upload_id: str) -> MediaTransportError:
    return MediaTransportError(UPLOAD_NOT_FOUND, "staged upload not found", upload_id=upload_id)


@dataclass(frozen=True, slots=True)
class UploadStatus:
    upload_id: str
    filename: str
    purpose: str
    size_bytes: int
    sha256: str
    chunk_size: int
    chunk_count: int
    received_chunks: int
    missing_chunks: tuple[int, ...]
    complete: bool
    expires_at: float


@dataclass(slots=True)
class StagedUpload:
    """A complete, digest-verified staged upload with an open read stream positioned at byte 0. Close it after use."""

    upload_id: str
    filename: str
    purpose: str
    size_bytes: int
    sha256: str
    stream: BinaryIO = field(repr=False)

    def close(self) -> None:
        self.stream.close()

    def __enter__(self) -> StagedUpload:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _chunk_count(size: int) -> int:
    return max(1, -(-size // UPLOAD_CHUNK_SIZE))


def _status(meta: dict[str, Any]) -> UploadStatus:
    count = int(meta["chunk_count"])
    received = set(meta.get("received", []))
    missing = tuple(index for index in range(count) if index not in received)
    return UploadStatus(
        upload_id=meta["upload_id"],
        filename=meta["filename"],
        purpose=meta["purpose"],
        size_bytes=int(meta["size_bytes"]),
        sha256=meta["sha256"],
        chunk_size=int(meta["chunk_size"]),
        chunk_count=count,
        received_chunks=len(received),
        missing_chunks=missing,
        complete=bool(meta.get("verified")),
        expires_at=float(meta["expires_at"]),
    )


def validate_upload_request(filename: str, size_bytes: int, sha256: str, purpose: str) -> None:
    name = os.path.basename(filename.replace("\\", "/"))
    if (
        name != filename
        or not filename
        or filename in {".", ".."}
        or len(filename) > _FILENAME_MAX
        or "\x00" in filename
    ):
        raise MediaTransportError(UPLOAD_CHUNK_INVALID, "filename must be a bare file name without directories")
    if size_bytes <= 0:
        raise MediaTransportError(UPLOAD_CHUNK_INVALID, "size_bytes must be positive")
    limit = UPLOAD_PURPOSE_LIMITS.get(purpose)
    if limit is None:
        raise MediaTransportError(UPLOAD_CHUNK_INVALID, "unknown purpose", purposes=list(UPLOAD_PURPOSES))
    if size_bytes > limit:
        raise MediaTransportError(
            UPLOAD_TOO_LARGE, "upload exceeds the native limit for this purpose", purpose=purpose, max_bytes=limit
        )
    if _SHA256_RE.fullmatch(sha256) is None:
        raise MediaTransportError(UPLOAD_CHUNK_INVALID, "sha256 must be 64 lowercase hex characters")


async def begin_upload(
    projects: ProjectManager,
    project_name: str,
    *,
    filename: str,
    size_bytes: int,
    sha256: str,
    purpose: str,
    client_id: str | None,
) -> UploadStatus:
    validate_upload_request(filename, size_bytes, sha256, purpose)
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)
    created: list[Path] = []

    def _begin() -> UploadStatus:
        try:
            root = private_store.area_root(project_dir, UPLOAD_AREA, create=True)
        except private_store.PrivateStoreError:
            raise MediaTransportError(UPLOAD_STAGING_REFUSED, "upload staging area is unavailable") from None
        # The area lock serializes quota checks with record creation.
        with private_store.record_lock(root):
            private_store.sweep_expired(project_dir, UPLOAD_AREA)
            live = [
                meta for meta in private_store.live_records(project_dir, UPLOAD_AREA) if meta.get("kind") == "upload"
            ]
            if sum(1 for meta in live if meta.get("client_id") == client_id) >= MAX_ACTIVE_UPLOADS_PER_CLIENT:
                raise MediaTransportError(
                    UPLOAD_QUOTA_EXCEEDED,
                    "too many active staged uploads for this client; finish or let them expire",
                    max_active_uploads=MAX_ACTIVE_UPLOADS_PER_CLIENT,
                )
            staged = sum(int(meta.get("size_bytes") or 0) for meta in live)
            if staged + size_bytes > MAX_STAGED_BYTES_PER_PROJECT:
                raise MediaTransportError(
                    UPLOAD_QUOTA_EXCEEDED,
                    "staged bytes for this project would exceed the staging quota",
                    max_staged_bytes=MAX_STAGED_BYTES_PER_PROJECT,
                )
            try:
                upload_id = private_store.new_record_id()
                directory = private_store.record_dir(project_dir, UPLOAD_AREA, upload_id, create=True)
            except private_store.PrivateStoreError:
                raise MediaTransportError(UPLOAD_STAGING_REFUSED, "upload staging area is unavailable") from None
            created.append(directory)
            return _initialize(directory, upload_id)

    def _initialize(directory: Path, upload_id: str) -> UploadStatus:
        with open(directory / DATA_FILE, "wb") as handle:
            handle.truncate(size_bytes)
        meta = {
            "kind": "upload",
            "upload_id": upload_id,
            "project": project_name,
            "client_id": client_id,
            "filename": filename,
            "purpose": purpose,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "chunk_size": UPLOAD_CHUNK_SIZE,
            "chunk_count": _chunk_count(size_bytes),
            "received": [],
            "verified": False,
            "expires_at": private_store.clock() + UPLOAD_TTL_SECONDS,
        }
        private_store.write_meta(directory, meta)
        return _status(meta)

    try:
        return await run_sync_transaction(_begin)
    except BaseException:
        for directory in created:
            await asyncio.to_thread(private_store.remove_record, directory)
        raise


def _locate(project_dir: Path, upload_id: str, client_id: str | None) -> tuple[Path, dict[str, Any]]:
    try:
        directory = private_store.record_dir(project_dir, UPLOAD_AREA, upload_id)
    except private_store.PrivateStoreError:
        raise _not_found(upload_id) from None
    meta = private_store.read_meta(directory)
    # Another caller's upload is indistinguishable from an absent one.
    if meta is None or meta.get("kind") != "upload" or meta.get("client_id") != client_id:
        raise _not_found(upload_id)
    if private_store.expired(meta):
        private_store.remove_record(directory)
        raise MediaTransportError(UPLOAD_EXPIRED, "staged upload expired; begin a new upload", upload_id=upload_id)
    data = directory / DATA_FILE
    if data.is_symlink() or not data.is_file():
        raise _not_found(upload_id)
    return directory, meta


def _file_digest(path: Path) -> str:
    with open(path, "rb") as handle:
        return digest_stream(handle.read)[0]


async def append_upload_chunk(
    projects: ProjectManager,
    project_name: str,
    upload_id: str,
    *,
    index: int,
    content: bytes,
    client_id: str | None,
    chunk_sha256: str | None = None,
) -> UploadStatus:
    """Write chunk ``index`` (resending one overwrites it); when every chunk is present, verify the full sha256.

    A full-digest mismatch discards the staged upload and refuses with ``upload_digest_mismatch``."""
    if chunk_sha256 is not None and hashlib.sha256(content).hexdigest() != chunk_sha256:
        raise MediaTransportError(UPLOAD_CHUNK_INVALID, "chunk bytes do not match chunk_sha256; resend the chunk")
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)

    def _append() -> UploadStatus:
        # Locate first so an expired target reports upload_expired, then sweep the rest of the area.
        directory, _ = _locate(project_dir, upload_id, client_id)
        private_store.sweep_expired(project_dir, UPLOAD_AREA)
        with private_store.record_lock(directory):
            directory, meta = _locate(project_dir, upload_id, client_id)
            if meta.get("verified"):
                # A verified upload is immutable so a consumer never reads bytes that differ from the verified digest.
                raise MediaTransportError(
                    UPLOAD_ALREADY_COMPLETE, "staged upload is already complete and verified", upload_id=upload_id
                )
            count = int(meta["chunk_count"])
            size = int(meta["size_bytes"])
            if not 0 <= index < count:
                raise MediaTransportError(
                    UPLOAD_CHUNK_INVALID, f"chunk index must be within 0..{count - 1}", chunk_count=count
                )
            expected = min(UPLOAD_CHUNK_SIZE, size - index * UPLOAD_CHUNK_SIZE)
            if len(content) != expected:
                raise MediaTransportError(
                    UPLOAD_CHUNK_INVALID, f"chunk {index} must be exactly {expected} bytes", expected_length=expected
                )
            data_path = directory / DATA_FILE
            fd = os.open(data_path, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
            try:
                os.lseek(fd, index * UPLOAD_CHUNK_SIZE, os.SEEK_SET)
                view = memoryview(content)
                while view:
                    written = os.write(fd, view)
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            received = sorted({*meta.get("received", []), index})
            meta = {**meta, "received": received, "expires_at": private_store.clock() + UPLOAD_TTL_SECONDS}
            if len(received) == count:
                if _file_digest(data_path) != meta["sha256"]:
                    private_store.remove_record(directory)
                    raise MediaTransportError(
                        UPLOAD_DIGEST_MISMATCH,
                        "assembled bytes do not match the declared sha256; the staged upload was discarded",
                        upload_id=upload_id,
                    )
                meta["verified"] = True
            private_store.write_meta(directory, meta)
            return _status(meta)

    return await run_sync_transaction(_append)


async def upload_status(
    projects: ProjectManager, project_name: str, upload_id: str, *, client_id: str | None
) -> UploadStatus:
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)
    return await asyncio.to_thread(lambda: _status(_locate(project_dir, upload_id, client_id)[1]))


def current_client_id() -> str | None:
    """The authenticated remote MCP client, or ``None`` outside a remote request (embedded host, Web, tests)."""
    from mcp.server.auth.middleware.auth_context import get_access_token

    token = get_access_token()
    return token.client_id if token is not None else None


async def resolve_staged_upload(
    projects: ProjectManager,
    project_name: str,
    upload_id: str,
    *,
    client_id: str | None = None,
    use_request_client: bool = True,
    purposes: Collection[str] | None = None,
) -> StagedUpload:
    """Return a complete staged upload as an open stream after re-verifying size and sha256 from that stream.

    Scope: ``project_name`` and the caller that began it (by default the current remote MCP client). ``purposes``
    lists the purposes this consumer installs; an upload staged for another purpose (and therefore checked against
    another size ceiling) is refused with ``upload_purpose_mismatch``. Raises ``upload_not_found`` /
    ``upload_expired`` / ``upload_incomplete`` / ``upload_digest_mismatch`` / ``upload_purpose_mismatch``. Never
    installs media."""
    caller = current_client_id() if use_request_client and client_id is None else client_id
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)

    def _open() -> StagedUpload:
        directory, _ = _locate(project_dir, upload_id, caller)
        private_store.sweep_expired(project_dir, UPLOAD_AREA)
        with private_store.record_lock(directory):
            return _open_locked()

    def _open_locked() -> StagedUpload:
        directory, meta = _locate(project_dir, upload_id, caller)
        if purposes is not None and meta.get("purpose") not in purposes:
            raise MediaTransportError(
                UPLOAD_PURPOSE_MISMATCH,
                "staged upload was declared for a different purpose",
                upload_id=upload_id,
                purpose=meta.get("purpose"),
                accepted_purposes=sorted(purposes),
            )
        if not meta.get("verified"):
            status = _status(meta)
            raise MediaTransportError(
                UPLOAD_INCOMPLETE,
                "staged upload is incomplete",
                upload_id=upload_id,
                missing_chunks=list(status.missing_chunks[:50]),
            )
        fd = os.open(directory / DATA_FILE, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
        stream = os.fdopen(fd, "rb")
        try:
            digest, size, _ = digest_stream(stream.read)
            if size != meta["size_bytes"] or digest != meta["sha256"]:
                raise MediaTransportError(
                    UPLOAD_DIGEST_MISMATCH, "staged bytes changed after verification", upload_id=upload_id
                )
            stream.seek(0)
        except BaseException:
            stream.close()
            raise
        return StagedUpload(
            upload_id=upload_id,
            filename=meta["filename"],
            purpose=meta["purpose"],
            size_bytes=size,
            sha256=digest,
            stream=stream,
        )

    return await asyncio.to_thread(_open)


async def discard_staged_upload(
    projects: ProjectManager,
    project_name: str,
    upload_id: str,
    *,
    client_id: str | None = None,
    use_request_client: bool = True,
) -> None:
    """Remove a staged upload after its consumer installed (or abandoned) it; absent uploads are ignored."""
    caller = current_client_id() if use_request_client and client_id is None else client_id
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)

    def _discard() -> None:
        try:
            directory, _meta = _locate(project_dir, upload_id, caller)
        except MediaTransportError:
            return
        with private_store.record_lock(directory):
            private_store.remove_record(directory)

    await run_sync_transaction(_discard)


__all__ = [
    "MAX_ACTIVE_UPLOADS_PER_CLIENT",
    "MAX_STAGED_BYTES_PER_PROJECT",
    "MAX_UPLOAD_BYTES",
    "UPLOAD_CHUNK_SIZE",
    "UPLOAD_PURPOSES",
    "UPLOAD_PURPOSE_LIMITS",
    "UPLOAD_TTL_SECONDS",
    "StagedUpload",
    "UploadStatus",
    "append_upload_chunk",
    "begin_upload",
    "current_client_id",
    "discard_staged_upload",
    "resolve_staged_upload",
    "upload_status",
    "validate_upload_request",
]
