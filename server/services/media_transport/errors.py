"""Stable refusal codes for media transport.

Every refusal carries a stable ``code`` and a detail that never names a server filesystem path, so tool problems and
resource-template errors can relay it unchanged."""

from __future__ import annotations

from typing import Any

#: The ``media_id`` is malformed or its signature does not verify (tampered, truncated or issued by another server).
MEDIA_ID_INVALID = "media_id_invalid"
#: The ``media_id`` is valid but was issued for another project than the one addressed.
MEDIA_PROJECT_MISMATCH = "media_project_mismatch"
#: The selector names an object (asset, item, unit, timeline, BGM, task, package) that does not exist in the project.
MEDIA_NOT_FOUND = "media_not_found"
#: The named object exists but the requested version does not; ``params.available_versions`` lists existing versions.
MEDIA_VERSION_NOT_FOUND = "version_not_found"
#: The object exists but has no readable media file (never generated, file removed, or expired package).
MEDIA_MISSING = "media_missing"
#: The media file resolves outside the project, through a symbolic link, or to a non-regular file.
MEDIA_PATH_REFUSED = "media_path_refused"
#: The bytes behind the ``media_id`` changed since it was issued; describe the media again and restart the download.
MEDIA_VERSION_CHANGED = "media_version_changed"
#: The chunk index is outside ``0 .. chunk_count - 1``.
MEDIA_CHUNK_OUT_OF_RANGE = "chunk_out_of_range"
#: Object storage could not materialize the file locally.
MEDIA_UNAVAILABLE = "media_unavailable"

UPLOAD_NOT_FOUND = "upload_not_found"
UPLOAD_ALREADY_COMPLETE = "upload_already_complete"
UPLOAD_QUOTA_EXCEEDED = "upload_quota_exceeded"
#: The consumer does not accept the purpose the upload was staged for.
UPLOAD_PURPOSE_MISMATCH = "upload_purpose_mismatch"
UPLOAD_EXPIRED = "upload_expired"
UPLOAD_INCOMPLETE = "upload_incomplete"
UPLOAD_DIGEST_MISMATCH = "upload_digest_mismatch"
UPLOAD_CHUNK_INVALID = "upload_chunk_invalid"
UPLOAD_TOO_LARGE = "upload_too_large"
UPLOAD_STAGING_REFUSED = "upload_staging_refused"


class MediaTransportError(Exception):
    """A refusal with a stable code; ``detail`` and ``params`` never contain filesystem paths."""

    def __init__(self, code: str, detail: str, **params: Any) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.params = params

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


__all__ = [
    "MEDIA_CHUNK_OUT_OF_RANGE",
    "MEDIA_ID_INVALID",
    "MEDIA_MISSING",
    "MEDIA_NOT_FOUND",
    "MEDIA_PATH_REFUSED",
    "MEDIA_PROJECT_MISMATCH",
    "MEDIA_UNAVAILABLE",
    "MEDIA_VERSION_CHANGED",
    "MEDIA_VERSION_NOT_FOUND",
    "UPLOAD_ALREADY_COMPLETE",
    "UPLOAD_CHUNK_INVALID",
    "UPLOAD_DIGEST_MISMATCH",
    "UPLOAD_EXPIRED",
    "UPLOAD_INCOMPLETE",
    "UPLOAD_NOT_FOUND",
    "UPLOAD_PURPOSE_MISMATCH",
    "UPLOAD_QUOTA_EXCEEDED",
    "UPLOAD_STAGING_REFUSED",
    "UPLOAD_TOO_LARGE",
    "MediaTransportError",
]
