"""Routes for replacing character-derivative asset images by upload (``docs/adr/0072``).

Uploads are finished images: save to canonical ``characters/derivatives/{角色}/{衍生}.png`` as a selected manually uploaded
version in history. The manifest records image bytes (``docs/adr/0062``), independent of the base image or change description.
Uploads replace only the asset image, not the base for subsequent edit generation; the change description remains unchanged.

Separate from base-image uploads (``files.py`` ``UPLOAD_SPECS``): derivative coordinates have two components, base/derivative,
and persist with fixed ``.png`` extensions. Submission uses the formal activation callback shared with derivative generation and image editing."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from lib.infra.api_errors import ApiError
from lib.project.project_manager import get_project_manager
from server.i18n import Translator
from server.services.currency.manual_media_install import install_derivative_sheet
from server.services.currency.upload_finalize import (
    UploadTooLargeError,
    UploadValidationError,
    validate_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/projects/{project_name}/characters/{char_name}/derivatives/{derivative_name}/upload")
async def upload_derivative_sheet(
    project_name: str,
    char_name: str,
    derivative_name: str,
    _t: Translator,
    file: UploadFile = File(...),
):
    """Upload an image to replace a character derivative’s asset image as its current version.

    No base asset image is required: the upload is a finished image, not generated from the base image."""
    try:
        max_bytes = validate_upload(file.filename, file.size, kind="image")
        # Bound bytes read into memory to prevent OOM when Content-Length is absent or bypassed.
        content = await file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise UploadTooLargeError(max_bytes)
        installed = await install_derivative_sheet(
            manager=get_project_manager(),
            project_name=project_name,
            owner_name=char_name,
            derivative_name=derivative_name,
            filename=file.filename,
            content=content,
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
    except (HTTPException, ApiError):
        raise
    except Exception as e:
        # Never return str(e): unexpected errors may contain server paths or other internals; log the traceback only.
        logger.exception("请求处理失败")
        raise HTTPException(status_code=500, detail=_t("internal_server_error")) from e
