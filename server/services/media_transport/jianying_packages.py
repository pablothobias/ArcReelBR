"""Retained Jianying download packages for chunked delivery.

:meth:`TimelineJianyingDraftService.package_download` builds the same zip the Web download serves: the registered
draft with the user's local Jianying draft directory and Jianying version substituted, plus project materials. It
never renders and never writes to the user's computer. This module moves that temporary zip into a project-private,
TTL-bound record so a remote client can read it across several chunk calls, then addresses it as
``jianying_package`` media."""

from __future__ import annotations

import asyncio
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.infra.async_thread import run_noninterruptible_sync, run_sync_transaction
from lib.infra.content_digest import sha256_file_with_size
from lib.jianying_draft.archive import JianyingVersion
from lib.jianying_draft.basis import DraftNarration
from lib.jianying_draft.errors import JianyingDraftError
from lib.project.project_manager import ProjectManager
from server.services.media_transport import private_store
from server.services.media_transport.errors import MEDIA_MISSING, MEDIA_NOT_FOUND, MediaTransportError

PACKAGE_AREA = "mcp_packages"
PACKAGE_FILE = "package.zip"
#: Retention after preparation; long enough for a slow chunked download, short enough not to accumulate copies.
PACKAGE_TTL_SECONDS = 6 * 60 * 60


@dataclass(frozen=True, slots=True)
class PreparedJianyingPackage:
    package_id: str
    timeline_id: str
    narration: str
    draft_version: int | None
    jianying_version: str
    draft_folder: str
    size_bytes: int
    sha256: str
    expires_at: float


def _package_meta(package: PreparedJianyingPackage, draft_root: str) -> dict[str, Any]:
    return {
        "kind": "jianying_package",
        "package_id": package.package_id,
        "timeline_id": package.timeline_id,
        "narration": package.narration,
        "draft_version": package.draft_version,
        "jianying_version": package.jianying_version,
        "draft_root": draft_root,
        "draft_folder": package.draft_folder,
        "size_bytes": package.size_bytes,
        "sha256": package.sha256,
        "expires_at": package.expires_at,
    }


async def prepare_jianying_package(
    projects: ProjectManager,
    project_name: str,
    timeline_id: str,
    *,
    narration: DraftNarration | None,
    draft_root: str,
    jianying_version: JianyingVersion,
    expected_draft_version: int | None = None,
    translate: Callable[..., str] | None = None,
) -> PreparedJianyingPackage:
    """Package the registered draft for ``draft_root``/``jianying_version`` and retain it; raises the native draft errors.

    ``expected_draft_version`` (the ``version`` reported by ``export_jianying_draft``) refuses with
    ``jianying_draft_version_changed`` when the registered draft was re-exported since."""
    from server.services.presentation.timeline_jianying_draft import TimelineJianyingDraftService

    service = TimelineJianyingDraftService(projects)
    status = await service.status(project_name, timeline_id, narration=narration)
    # package_download re-reads the registered draft, so a re-export could commit between this check and packaging.
    # Render versions only increase and each commit replaces the formal file atomically, so the status is read again
    # after packaging: an unchanged version proves the packaged draft is the one checked here; otherwise the package
    # is discarded and the call refuses with jianying_draft_version_changed.
    if expected_draft_version is not None and status.version != expected_draft_version:
        raise JianyingDraftError(
            "jianying_draft_version_changed",
            "The registered Jianying draft is not the expected exported version; export or read its status again",
            expected_version=expected_draft_version,
            current_version=status.version,
        )
    kwargs: dict[str, Any] = {} if translate is None else {"translate": translate}
    package, name = await service.package_download(
        project_name,
        timeline_id,
        narration=status.narration,
        draft_root=draft_root,
        jianying_version=jianying_version,
        **kwargs,
    )
    try:
        after = await service.status(project_name, timeline_id, narration=status.narration)
    except BaseException:
        # hard-delete: temp -- temporary packaging directory created by package_download
        await run_noninterruptible_sync(shutil.rmtree, package.parent, ignore_errors=True)
        raise
    if after.version != status.version:
        # hard-delete: temp -- temporary packaging directory created by package_download
        await run_noninterruptible_sync(shutil.rmtree, package.parent, ignore_errors=True)
        raise JianyingDraftError(
            "jianying_draft_version_changed",
            "The Jianying draft was re-exported while it was being packaged; prepare the package again",
            expected_version=status.version,
            current_version=after.version,
        )
    project_dir = await asyncio.to_thread(projects.get_project_path, project_name)
    created: list[Path] = []

    def _retain() -> PreparedJianyingPackage:
        private_store.sweep_expired(project_dir, PACKAGE_AREA)
        package_id = private_store.new_record_id()
        directory = private_store.record_dir(project_dir, PACKAGE_AREA, package_id, create=True)
        created.append(directory)
        target = directory / PACKAGE_FILE
        shutil.move(os.fspath(package), os.fspath(target))
        sha256, size = sha256_file_with_size(target)
        prepared = PreparedJianyingPackage(
            package_id=package_id,
            timeline_id=status.timeline_id,
            narration=status.narration,
            draft_version=status.version,
            jianying_version=jianying_version,
            draft_folder=name,
            size_bytes=size,
            sha256=sha256,
            expires_at=private_store.clock() + PACKAGE_TTL_SECONDS,
        )
        private_store.write_meta(directory, _package_meta(prepared, draft_root))
        return prepared

    try:
        return await run_sync_transaction(_retain)
    except BaseException:
        for directory in created:
            await run_noninterruptible_sync(private_store.remove_record, directory)
        raise
    finally:
        # hard-delete: temp -- temporary packaging directory created by package_download
        await run_noninterruptible_sync(shutil.rmtree, package.parent, ignore_errors=True)


def jianying_package_relative_path(project_dir: Path, package_id: str) -> tuple[str, dict[str, Any]]:
    """Project-relative path and metadata of a retained, unexpired package; refuses missing or expired packages."""
    try:
        directory = private_store.record_dir(project_dir, PACKAGE_AREA, package_id)
    except private_store.PrivateStoreError:
        raise MediaTransportError(MEDIA_NOT_FOUND, "Jianying package not found", package_id=package_id) from None
    meta = private_store.read_meta(directory)
    if meta is None or meta.get("kind") != "jianying_package":
        raise MediaTransportError(MEDIA_NOT_FOUND, "Jianying package not found", package_id=package_id)
    if private_store.expired(meta):
        private_store.remove_record(directory)
        raise MediaTransportError(
            MEDIA_MISSING, "Jianying package expired; prepare it again", package_id=package_id, expired=True
        )
    return f"{private_store.ARCREEL_DIR}/{PACKAGE_AREA}/{package_id}/{PACKAGE_FILE}", meta


__all__ = [
    "PACKAGE_AREA",
    "PACKAGE_TTL_SECONDS",
    "PreparedJianyingPackage",
    "jianying_package_relative_path",
    "prepare_jianying_package",
]
