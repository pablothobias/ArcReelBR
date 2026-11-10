"""Symlink-free, project-contained file access for media transport.

Media files are opened component by component without following symbolic links (``dir_fd`` + ``O_NOFOLLOW`` on POSIX;
per-component ``lstat`` plus ``fstat``/``lstat`` identity comparison elsewhere), so a path that escapes the project,
traverses a link or names a non-regular file is refused. Digests are computed from the same open descriptor and
cached by stat identity (``lib.infra.content_digest``), so repeated chunk reads do not rehash unchanged files."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from lib.infra.content_digest import (
    cached_file_digest,
    digest_stream,
    file_identity,
    remember_file_digest,
)
from server.services.media_transport.errors import (
    MEDIA_MISSING,
    MEDIA_PATH_REFUSED,
    MEDIA_VERSION_CHANGED,
    MediaTransportError,
)

_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
_BINARY = getattr(os, "O_BINARY", 0)


def _refused() -> MediaTransportError:
    return MediaTransportError(
        MEDIA_PATH_REFUSED, "media file is outside the project, behind a symbolic link, or not a regular file"
    )


def _missing() -> MediaTransportError:
    return MediaTransportError(MEDIA_MISSING, "media file is not present")


def relative_parts(relative: str) -> tuple[str, ...]:
    """Split a project-relative POSIX path; absolute paths, empty segments and dot segments are refused."""
    if not isinstance(relative, str) or not relative or "\x00" in relative or "\\" in relative:
        raise _refused()
    path = PurePosixPath(relative)
    if path.is_absolute():
        raise _refused()
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise _refused()
    return tuple(parts)


def _open_posix(project_dir: Path, parts: tuple[str, ...]) -> int:
    directory_fd = os.open(project_dir, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | _DIRECTORY | _NOFOLLOW, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = child
        return os.open(parts[-1], os.O_RDONLY | _NONBLOCK | _NOFOLLOW | _BINARY, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


def _open_portable(project_dir: Path, parts: tuple[str, ...]) -> int:
    lexical = project_dir
    for part in parts:
        lexical = lexical / part
        if lexical.is_symlink() or getattr(os.path, "isjunction", lambda _p: False)(lexical):
            raise _refused()
    real_root = os.path.realpath(project_dir)
    if os.path.commonpath([real_root, os.path.realpath(lexical)]) != real_root:
        raise _refused()
    fd = os.open(lexical, os.O_RDONLY | _BINARY)
    try:
        opened = os.fstat(fd)
        current = os.lstat(lexical)
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            raise _refused()
    except BaseException:
        os.close(fd)
        raise
    return fd


@contextmanager
def open_project_media(project_dir: Path, relative: str) -> Iterator[int]:
    """Open ``relative`` under ``project_dir`` read-only without following links; yield the descriptor of a regular file."""
    parts = relative_parts(relative)
    try:
        if os.open in os.supports_dir_fd and _NOFOLLOW:
            fd = _open_posix(project_dir, parts)
        else:
            fd = _open_portable(project_dir, parts)
    except MediaTransportError:
        raise
    except (FileNotFoundError, NotADirectoryError):
        raise _missing() from None
    except OSError:
        # ELOOP (final link) or ENOTDIR through a link: a symbolic link or special node sits on the path.
        raise _refused() from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise _refused()
        yield fd
    finally:
        os.close(fd)


def _pread_all(fd: int, offset: int, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    position = offset
    while remaining > 0:
        block = os.pread(fd, remaining, position) if hasattr(os, "pread") else _seek_read(fd, position, remaining)
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
        position += len(block)
    return b"".join(chunks)


def _seek_read(fd: int, position: int, length: int) -> bytes:
    os.lseek(fd, position, os.SEEK_SET)
    return os.read(fd, length)


def fd_digest(fd: int) -> tuple[str, int, os.stat_result]:
    """Content sha256 and size of an open file, from the stat-identity cache when unchanged; raise version-changed if it moves during hashing."""
    before = os.fstat(fd)
    cached = cached_file_digest(before)
    if cached is not None:
        return cached, before.st_size, before
    position = 0

    def read(size: int) -> bytes:
        nonlocal position
        block = _pread_all(fd, position, size)
        position += len(block)
        return block

    hexdigest, size, _ = digest_stream(read)
    after = os.fstat(fd)
    if (
        file_identity(before) != file_identity(after)
        or before.st_ctime_ns != after.st_ctime_ns
        or size != before.st_size
    ):
        raise MediaTransportError(MEDIA_VERSION_CHANGED, "media changed while it was being read; describe it again")
    remember_file_digest(before, hexdigest)
    return hexdigest, size, before


def read_verified_range(fd: int, *, expected_sha256: str, offset: int, length: int) -> tuple[bytes, int]:
    """Read ``length`` bytes at ``offset`` only if the file has ``expected_sha256`` and does not change during the read.

    ``length`` is clamped to the file size; returns the bytes and the total file size."""
    hexdigest, size, before = fd_digest(fd)
    if hexdigest != expected_sha256:
        raise MediaTransportError(MEDIA_VERSION_CHANGED, "media bytes no longer match this media_id; describe it again")
    data = _pread_all(fd, offset, max(0, min(length, size - offset)))
    after = os.fstat(fd)
    if file_identity(before) != file_identity(after) or before.st_ctime_ns != after.st_ctime_ns:
        raise MediaTransportError(MEDIA_VERSION_CHANGED, "media changed while it was being read; describe it again")
    return data, size


__all__ = ["fd_digest", "open_project_media", "read_verified_range", "relative_parts"]
