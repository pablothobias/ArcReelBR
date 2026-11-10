"""Project-private, TTL-bound record directories under ``<project>/.arcreel/<area>/<record_id>/``.

Shared by upload staging and retained Jianying packages. Record IDs are 128-bit random hex; every component from the
project directory down is checked against symbolic links and junctions before use (precedent:
``lib/script/reference_video/execution_checkpoint.py``). Each record holds a ``meta.json`` sentinel; sweeping deletes
only directories carrying an expired sentinel this module wrote."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import time
import weakref
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lib.infra.json_io import atomic_write_json

ARCREEL_DIR = ".arcreel"
META_FILE = "meta.json"
_RECORD_ID_RE = re.compile(r"[0-9a-f]{32}")

#: Wall clock in seconds; tests replace it to exercise expiry.
clock: Callable[[], float] = time.time


#: Weak values: an entry lives only while some caller holds its lock object, so the map never grows with record count.
_RECORD_LOCKS: weakref.WeakValueDictionary[str, threading.Lock] = weakref.WeakValueDictionary()
_RECORD_LOCKS_GUARD = threading.Lock()


def record_lock(directory: Path) -> threading.Lock:
    """Process-wide lock for one record; writers, readers and the sweeper serialize on it.

    Keep the returned object referenced for as long as it is held (``with record_lock(...)`` does)."""
    key = os.fspath(directory)
    with _RECORD_LOCKS_GUARD:
        lock = _RECORD_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _RECORD_LOCKS[key] = lock
        return lock


def record_lock_count() -> int:
    """Live lock entries (tests assert the map does not grow)."""
    with _RECORD_LOCKS_GUARD:
        return len(_RECORD_LOCKS)


class PrivateStoreError(ValueError):
    """The store path traverses a link or the record ID is malformed."""


def new_record_id() -> str:
    return secrets.token_hex(16)


def valid_record_id(record_id: object) -> bool:
    return isinstance(record_id, str) and _RECORD_ID_RE.fullmatch(record_id) is not None


def _is_link(path: Path) -> bool:
    isjunction = getattr(os.path, "isjunction", None)
    return path.is_symlink() or bool(isjunction is not None and isjunction(path))


def area_root(project_dir: Path, area: str, *, create: bool) -> Path:
    cursor = project_dir
    for part in (ARCREEL_DIR, area):
        cursor = cursor / part
        if _is_link(cursor):
            raise PrivateStoreError("private store cannot traverse a symbolic link or junction")
        if create:
            cursor.mkdir(exist_ok=True)
    return cursor


def record_dir(project_dir: Path, area: str, record_id: str, *, create: bool = False) -> Path:
    if not valid_record_id(record_id):
        raise PrivateStoreError("malformed record id")
    root = area_root(project_dir, area, create=create)
    directory = root / record_id
    if _is_link(directory):
        raise PrivateStoreError("private store cannot traverse a symbolic link or junction")
    if create:
        directory.mkdir()
    return directory


def read_meta(directory: Path) -> dict[str, Any] | None:
    meta_path = directory / META_FILE
    if _is_link(meta_path) or not meta_path.is_file():
        return None
    try:
        value = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def write_meta(directory: Path, meta: dict[str, Any]) -> None:
    atomic_write_json(directory / META_FILE, meta)


def expired(meta: dict[str, Any]) -> bool:
    expires_at = meta.get("expires_at")
    return not isinstance(expires_at, int | float) or expires_at <= clock()


def remove_record(directory: Path) -> None:
    # hard-delete: temp -- expired or consumed transport record this module created (meta.json sentinel checked by callers)
    shutil.rmtree(directory, ignore_errors=True)


def sweep_expired(project_dir: Path, area: str) -> int:
    """Remove expired records carrying this module's sentinel; return how many were removed."""
    try:
        root = area_root(project_dir, area, create=False)
    except PrivateStoreError:
        return 0
    if not root.is_dir():
        return 0
    removed = 0
    for entry in root.iterdir():
        if not valid_record_id(entry.name) or _is_link(entry) or not entry.is_dir():
            continue
        lock = record_lock(entry)
        # A record in use (being appended to or opened) is skipped rather than removed under its user.
        if not lock.acquire(blocking=False):
            continue
        try:
            meta = read_meta(entry)
            if meta is not None and expired(meta):
                remove_record(entry)
                removed += 1
        finally:
            lock.release()
    return removed


def live_records(project_dir: Path, area: str) -> list[dict[str, Any]]:
    """Metadata of unexpired records in ``area`` (for quotas)."""
    try:
        root = area_root(project_dir, area, create=False)
    except PrivateStoreError:
        return []
    if not root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for entry in root.iterdir():
        if not valid_record_id(entry.name) or _is_link(entry) or not entry.is_dir():
            continue
        meta = read_meta(entry)
        if meta is not None and not expired(meta):
            records.append(meta)
    return records


__all__ = [
    "ARCREEL_DIR",
    "META_FILE",
    "PrivateStoreError",
    "area_root",
    "clock",
    "expired",
    "live_records",
    "new_record_id",
    "read_meta",
    "record_dir",
    "record_lock",
    "record_lock_count",
    "remove_record",
    "sweep_expired",
    "valid_record_id",
    "write_meta",
]
