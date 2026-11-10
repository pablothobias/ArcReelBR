"""Version-management API routes.

Handle version queries and restoration."""

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from lib.infra.api_errors import BadRequestError

logger = logging.getLogger(__name__)

from lib.artifacts.version_manager import VersionManager
from lib.project.asset_derivatives import derivative_artifact_id
from lib.project.project_manager import get_project_manager
from lib.project.resource_paths import CHARACTER_DERIVATIVE_RESOURCE_TYPE
from server.services.currency import media_version_selection
from server.services.currency.media_version_selection import (
    commit_non_typed_restore_claim,
    read_media_versions,
    resolve_restorable_resource_path,
    restore_media_version,
    sync_grid_record,
)

router = APIRouter()

# Policy lives in the shared selection service; kept here as the route-facing name.
_RESTORABLE_RESOURCE_TYPES = media_version_selection.RESTORABLE_RESOURCE_TYPES


def get_version_manager(project_name: str) -> VersionManager:
    """Get the project version manager."""
    project_path = get_project_manager().get_project_path(project_name)
    return VersionManager(project_path)


def _resolve_resource_path(
    resource_type: str,
    resource_id: str,
    project_path: Path,
) -> tuple[Path, str]:
    """Return (current_file_absolute, relative_file_path); raise domain exceptions for unrestorable types or out-of-bounds IDs."""
    return resolve_restorable_resource_path(resource_type, resource_id, project_path)


_sync_grid_record = sync_grid_record
_commit_non_typed_restore_claim = commit_non_typed_restore_claim


def _restore_non_typed_version(
    *,
    versions: VersionManager,
    resource_type: str,
    project_name: str,
    resource_id: str,
    version: int,
    current_file: Path,
    file_path: str,
    project_path: Path,
) -> dict[str, Any]:
    """Route-facing entry to the shared non-typed restore transaction (see ``media_version_selection``)."""
    return media_version_selection.restore_non_typed_version(
        project_manager=get_project_manager(),
        versions=versions,
        resource_type=resource_type,
        project_name=project_name,
        resource_id=resource_id,
        version=version,
        current_file=current_file,
        file_path=file_path,
        project_path=project_path,
    )


# ==================== Version queries ====================


@router.get("/projects/{project_name}/versions/{resource_type}/{resource_id}")
async def get_versions(
    project_name: str,
    resource_type: str,
    resource_id: str,
):
    """List all versions of a resource.

    Args:
        project_name: Project name.
        resource_type: Resource type (storyboards, videos, characters, scenes, props).
        resource_id: Resource ID."""
    return await read_resource_versions(project_name, resource_type, resource_id)


@router.get("/projects/{project_name}/versions/character-derivative/{owner_name}/{derivative_name}")
async def get_derivative_versions(
    project_name: str,
    owner_name: str,
    derivative_name: str,
):
    """List versions of a character-derivative image.

    Derivative IDs ``本体名/衍生名`` do not fit generic single-segment parameters, so use a separate two-segment path."""
    return await read_resource_versions(
        project_name,
        CHARACTER_DERIVATIVE_RESOURCE_TYPE,
        derivative_artifact_id(owner_name, derivative_name),
    )


@router.post("/projects/{project_name}/versions/character-derivative/{owner_name}/{derivative_name}/restore/{version}")
async def restore_derivative_version(
    project_name: str,
    owner_name: str,
    derivative_name: str,
    version: int,
):
    """Restore a character-derivative image to a specified historical version."""
    return await restore_resource_version(
        project_name,
        CHARACTER_DERIVATIVE_RESOURCE_TYPE,
        derivative_artifact_id(owner_name, derivative_name),
        version,
    )


async def read_resource_versions(project_name: str, resource_type: str, resource_id: str) -> dict[str, Any]:
    """Version-list reading shared by routes with hierarchical IDs, such as derivatives, that cannot use single-segment parameters."""
    try:
        versions = await asyncio.to_thread(get_version_manager, project_name)
    except ValueError as e:
        logger.warning("版本查询请求非法: %s", e)
        raise BadRequestError("request_invalid") from e
    return await read_media_versions(versions, resource_type, resource_id)


# ==================== Version restoration ====================


@router.post("/projects/{project_name}/versions/{resource_type}/{resource_id}/restore/{version}")
async def restore_version(
    project_name: str,
    resource_type: str,
    resource_id: str,
    version: int,
):
    """Switch to a specified version.

    Copy the selected version to the current path and select it as current.

    Args:
        project_name: Project name.
        resource_type: Resource type.
        resource_id: Resource ID.
        version: Version number to restore."""
    return await restore_resource_version(project_name, resource_type, resource_id, version)


async def restore_resource_version(
    project_name: str,
    resource_type: str,
    resource_id: str,
    version: int,
) -> dict[str, Any]:
    """Restoration shared by routes with hierarchical IDs, such as derivatives, that cannot use single-segment parameters."""
    try:
        versions = await asyncio.to_thread(get_version_manager, project_name)
    except ValueError as e:
        logger.warning("版本还原请求非法: %s", e)
        raise BadRequestError("request_invalid") from e
    return await restore_media_version(
        project_manager=get_project_manager(),
        versions=versions,
        project_name=project_name,
        resource_type=resource_type,
        resource_id=resource_id,
        version=version,
        change_source="webui",
    )
