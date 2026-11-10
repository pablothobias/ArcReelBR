"""Shot-level manual storyboard-image/video upload routes.

Separate from generic asset uploads (files.py), outside UPLOAD_SPECS. The install transactions live in
``server.services.currency.manual_media_install`` and are shared with the Agent ``install_finished_media`` tool: locate entries by script_file + shot_id,
track versions with VersionManager, write metadata through finalize_shot_*, and return asset_fingerprints for immediate
uploader cache busting, with SSE covering other clients. UploadSpec subdir + naming paths and MetadataSetter signatures
do not cover this pipeline. Share extension/size validation through upload_finalize.validate_upload.

Split-grid cells use normal storyboard-to-video canonical paths, storyboards/scene_{id}.png. Uploading a shot overwrites
its cell without changing grid records; whole-composite uploads use separate grids.py endpoints."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile

from lib.infra.api_errors import ApiError, NotFoundError
from lib.project.project_manager import get_project_manager
from lib.script.script_editor import ScriptEditError
from server.error_handlers import script_edit_detail
from server.i18n import Translator
from server.services.currency.manual_media_install import install_shot_storyboard_image, install_shot_video
from server.services.currency.upload_finalize import (
    UploadTooLargeError,
    UploadValidationError,
    validate_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/projects/{project_name}/shots/{shot_id}/upload/{kind}")
async def upload_shot_media(
    project_name: str,
    shot_id: str,
    kind: Literal["storyboard", "video"],
    script_file: str,
    _t: Translator,
    file: UploadFile = File(...),
):
    """Upload a storyboard image or video, replacing the shot’s AI-generated asset.

    Match generation: staging → atomic formal selection/metadata commit with derived status → SSE batch notification."""
    try:
        max_bytes = validate_upload(file.filename, file.size, kind="image" if kind == "storyboard" else "video")
        manager = get_project_manager()
        if kind == "storyboard":
            # Bound bytes read into memory to prevent OOM when Content-Length is absent/bypassed.
            content = await file.read(max_bytes + 1)
            if len(content) > max_bytes:
                raise UploadTooLargeError(max_bytes)
            installed = await install_shot_storyboard_image(
                manager=manager,
                project_name=project_name,
                script_file=script_file,
                shot_id=shot_id,
                filename=file.filename,
                content=content,
                change_source="webui",
            )
        else:
            installed = await install_shot_video(
                manager=manager,
                project_name=project_name,
                script_file=script_file,
                shot_id=shot_id,
                filename=file.filename,
                stream=file.file,
                declared_size=file.size,
                change_source="webui",
            )

        return {
            "success": True,
            "path": installed.path,
            "version": installed.version,
            "asset_fingerprints": installed.asset_fingerprints,
        }

    except UploadValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=_t(e.key, **e.params)) from e
    except FileNotFoundError as exc:
        # Never return str(exc): load_script errors contain absolute server paths.
        raise NotFoundError("script_not_found", name=script_file) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=_t("segment_not_found", id=shot_id)) from exc
    except ScriptEditError as e:
        raise HTTPException(status_code=400, detail=script_edit_detail(e, _t)) from e
    except (HTTPException, ApiError):
        raise
    except Exception as e:
        # Never return str(e): unexpected errors may contain server paths or other internals; log the traceback only.
        logger.exception("请求处理失败")
        raise HTTPException(status_code=500, detail=_t("internal_server_error")) from e
