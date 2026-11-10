"""Remote MCP media transport: typed media identity, verified chunked download, upload staging and retained Jianying packages.

Used only by the remote-only tools in ``server/agent_toolset/media_transport.py`` and by upload consumers through
:func:`resolve_staged_upload`. The embedded Agent reads project files natively and does not use this package."""

from server.services.media_transport.errors import MediaTransportError
from server.services.media_transport.jianying_packages import PreparedJianyingPackage, prepare_jianying_package
from server.services.media_transport.selectors import MEDIA_KINDS, parse_selector
from server.services.media_transport.transport import (
    DEFAULT_CHUNK_SIZE,
    MAX_CHUNK_SIZE,
    RESOURCE_URI_TEMPLATE,
    MediaChunk,
    MediaDescriptor,
    describe_media,
    read_media_chunk,
)
from server.services.media_transport.uploads import (
    StagedUpload,
    UploadStatus,
    append_upload_chunk,
    begin_upload,
    discard_staged_upload,
    resolve_staged_upload,
)

__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "MAX_CHUNK_SIZE",
    "MEDIA_KINDS",
    "RESOURCE_URI_TEMPLATE",
    "MediaChunk",
    "MediaDescriptor",
    "MediaTransportError",
    "PreparedJianyingPackage",
    "StagedUpload",
    "UploadStatus",
    "append_upload_chunk",
    "begin_upload",
    "describe_media",
    "discard_staged_upload",
    "parse_selector",
    "prepare_jianying_package",
    "read_media_chunk",
    "resolve_staged_upload",
]
