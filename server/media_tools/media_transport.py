"""Remote-only media transport handlers: describe and download media in verified chunks, stage large uploads, and prepare
Jianying download packages.

Thin adapters over ``server/services/media_transport``. Nothing here submits generation, renders, or calls a provider;
results never contain server filesystem paths, and chunk bytes travel as embedded blob resources, never inside JSON."""

from __future__ import annotations

import base64
import binascii
from dataclasses import asdict, dataclass
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StrictInt
from pydantic.json_schema import SkipJsonSchema

from lib.edit_timeline.errors import EditTimelineError
from lib.jianying_draft.basis import DraftNarration
from lib.jianying_draft.errors import JianyingDraftError
from server.agent_toolset.declaration import OPAQUE_BLOB_MIME_TYPE, ToolResource
from server.media_tools.context import tool_error, tool_problem
from server.services.media_transport.errors import MediaTransportError
from server.services.media_transport.jianying_packages import PreparedJianyingPackage, prepare_jianying_package
from server.services.media_transport.selectors import JianyingPackageSelector, MediaSelector
from server.services.media_transport.transport import (
    DEFAULT_CHUNK_SIZE,
    MAX_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
    MediaChunk,
    MediaDescriptor,
    describe_media,
    read_media_chunk,
    resource_uri,
)
from server.services.media_transport.uploads import (
    MAX_UPLOAD_BYTES,
    UPLOAD_CHUNK_SIZE,
    UPLOAD_PURPOSES,
    UploadStatus,
    append_upload_chunk,
    begin_upload,
    current_client_id,
)
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome, ToolProblem, ToolRequest

type UploadPurpose = Literal[
    "unit_video",
    "asset_image",
    "derivative_image",
    "product_reference_image",
    "storyboard_image",
    "end_frame",
    "grid_composite",
    "reference_audio",
    "bgm",
]
if get_args(UploadPurpose.__value__) != UPLOAD_PURPOSES:
    raise RuntimeError("UploadPurpose must match UPLOAD_PURPOSES")

_CHUNK_SIZE_DESCRIPTION = (
    f"Raw bytes per chunk, {MIN_CHUNK_SIZE}..{MAX_CHUNK_SIZE} (4 MiB); default {DEFAULT_CHUNK_SIZE} (256 KiB). "
    "The value is bound into media_id, so every chunk of one download uses it"
)


def _transport_problem(exc: MediaTransportError) -> ToolOutcome[Any]:
    return ToolOutcome(problem=ToolProblem(exc.code, exc.detail, params=exc.params or None))


class DescribeMediaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selector: MediaSelector = Field(
        description="Typed media selector; kind chooses the media family and its identity fields"
    )
    chunk_size: StrictInt = Field(
        default=DEFAULT_CHUNK_SIZE, ge=MIN_CHUNK_SIZE, le=MAX_CHUNK_SIZE, description=_CHUNK_SIZE_DESCRIPTION
    )


class ReadMediaChunkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    media_id: str = Field(min_length=1, max_length=4096, description="media_id from describe_media, unchanged")
    index: StrictInt = Field(ge=0, description="Zero-based chunk index, below the descriptor's chunk_count")


class BeginMediaUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str = Field(
        min_length=1, max_length=255, description="Bare file name including extension, no directories"
    )
    size_bytes: StrictInt = Field(ge=1, le=MAX_UPLOAD_BYTES, description="Exact total byte count of the file")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$", description="Lowercase hex sha256 of the complete file")
    purpose: UploadPurpose = Field(
        description=(
            "Intended consumer; caps size_bytes at that media's native install limit (unit_video 200 MiB, images 30 MiB, "
            "reference_audio and bgm per their native limits). Recorded only, never acted on"
        ),
    )


class AppendMediaUploadChunkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    upload_id: str = Field(pattern=r"^[0-9a-f]{32}$", description="upload_id from begin_media_upload")
    index: StrictInt = Field(ge=0, description="Zero-based chunk index")
    content_base64: str = Field(
        min_length=1,
        description=f"Standard base64 of exactly chunk_size ({UPLOAD_CHUNK_SIZE}) raw bytes; the last chunk carries the remainder",
    )
    chunk_sha256: str | SkipJsonSchema[None] = Field(
        default=None, pattern=r"^[0-9a-f]{64}$", description="Optional lowercase hex sha256 of this chunk's raw bytes"
    )


class PrepareJianyingPackageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    timeline: str = Field(min_length=1, description="Edit timeline ID whose exported Jianying draft to package")
    narration: DraftNarration | SkipJsonSchema[None] = Field(
        default=None, description="Narration variant exported by export_jianying_draft; omit to use the project default"
    )
    draft_path: str = Field(
        min_length=1,
        max_length=1024,
        description="The user's local Jianying draft directory on their own computer, as the user stated it; only written into the draft JSON",
    )
    jianying_version: Literal["5", "6"] = Field(description="Jianying version: 6 means 6 or later; 5 means 5.x")
    expected_draft_version: StrictInt | SkipJsonSchema[None] = Field(
        default=None,
        ge=1,
        description="Draft version reported by export_jianying_draft; when given, refuse if the registered draft has been re-exported since",
    )
    chunk_size: StrictInt = Field(
        default=DEFAULT_CHUNK_SIZE, ge=MIN_CHUNK_SIZE, le=MAX_CHUNK_SIZE, description=_CHUNK_SIZE_DESCRIPTION
    )


@dataclass(frozen=True, slots=True)
class ChunkReadout:
    project: str
    chunk: MediaChunk


@dataclass(frozen=True, slots=True)
class JianyingPackageReadout:
    package: PreparedJianyingPackage
    media: MediaDescriptor


async def describe_media_tool(
    request: ToolRequest[DescribeMediaRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[MediaDescriptor]:
    try:
        descriptor = await describe_media(
            services.projects,
            scope.project_name,
            request.value.selector,
            queue=services.queue,
            chunk_size=request.value.chunk_size,
        )
    except MediaTransportError as exc:
        return _transport_problem(exc)
    except Exception as exc:
        return tool_error("describe_media", exc)
    return ToolOutcome(value=descriptor)


async def read_media_chunk_tool(
    request: ToolRequest[ReadMediaChunkRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[ChunkReadout]:
    try:
        chunk = await read_media_chunk(
            services.projects, scope.project_name, request.value.media_id, request.value.index, queue=services.queue
        )
    except MediaTransportError as exc:
        return _transport_problem(exc)
    except Exception as exc:
        return tool_error("read_media_chunk", exc)
    return ToolOutcome(value=ChunkReadout(project=scope.project_name, chunk=chunk))


async def begin_media_upload_tool(
    request: ToolRequest[BeginMediaUploadRequest], scope: ProjectScope, _caller: CallerContext, services: Services
) -> ToolOutcome[UploadStatus]:
    value = request.value
    try:
        status = await begin_upload(
            services.projects,
            scope.project_name,
            filename=value.filename,
            size_bytes=value.size_bytes,
            sha256=value.sha256,
            purpose=value.purpose,
            client_id=current_client_id(),
        )
    except MediaTransportError as exc:
        return _transport_problem(exc)
    except Exception as exc:
        return tool_error("begin_media_upload", exc)
    return ToolOutcome(value=status)


async def append_media_upload_chunk_tool(
    request: ToolRequest[AppendMediaUploadChunkRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[UploadStatus]:
    value = request.value
    try:
        content = base64.b64decode(value.content_base64, validate=True)
    except (binascii.Error, ValueError):
        return tool_problem("content_base64 is not valid base64", code="upload_chunk_invalid")
    try:
        status = await append_upload_chunk(
            services.projects,
            scope.project_name,
            value.upload_id,
            index=value.index,
            content=content,
            client_id=current_client_id(),
            chunk_sha256=value.chunk_sha256,
        )
    except MediaTransportError as exc:
        return _transport_problem(exc)
    except Exception as exc:
        return tool_error("append_media_upload_chunk", exc)
    return ToolOutcome(value=status)


async def prepare_jianying_package_tool(
    request: ToolRequest[PrepareJianyingPackageRequest],
    scope: ProjectScope,
    _caller: CallerContext,
    services: Services,
) -> ToolOutcome[JianyingPackageReadout]:
    from server.services.presentation.timeline_jianying_draft import JianyingDraftRootError, validate_draft_root

    value = request.value
    try:
        draft_root = validate_draft_root(value.draft_path)
    except JianyingDraftRootError as exc:
        return tool_problem("draft_path is empty, too long or contains control characters", code=exc.key)
    try:
        package = await prepare_jianying_package(
            services.projects,
            scope.project_name,
            value.timeline,
            narration=value.narration,
            draft_root=draft_root,
            jianying_version=value.jianying_version,
            expected_draft_version=value.expected_draft_version,
        )
        descriptor = await describe_media(
            services.projects,
            scope.project_name,
            JianyingPackageSelector(kind="jianying_package", package_id=package.package_id),
            queue=services.queue,
            chunk_size=value.chunk_size,
        )
    except MediaTransportError as exc:
        return _transport_problem(exc)
    except (JianyingDraftError, EditTimelineError) as exc:
        return tool_problem(str(exc), code=exc.code, params=exc.params or None)
    except Exception as exc:
        return tool_error("prepare_jianying_package", exc)
    return ToolOutcome(value=JianyingPackageReadout(package=package, media=descriptor))


def _descriptor_json(descriptor: MediaDescriptor) -> dict[str, Any]:
    return asdict(descriptor)


def describe_media_projection(value: MediaDescriptor) -> dict[str, Any]:
    return {"media": _descriptor_json(value)}


def describe_media_summary(value: MediaDescriptor) -> str:
    return (
        f"Media {value.kind} ({value.mime_type}, {value.size_bytes} bytes, sha256 {value.sha256}) "
        f"in {value.chunk_count} chunk(s) of {value.chunk_size} bytes; read them with read_media_chunk."
    )


def read_media_chunk_projection(value: ChunkReadout) -> dict[str, Any]:
    chunk = value.chunk
    return {
        "media_chunk": {
            "media_id": chunk.media_id,
            "index": chunk.index,
            "offset": chunk.offset,
            "length": chunk.length,
            "chunk_sha256": chunk.chunk_sha256,
            "total_size": chunk.total_size,
            "sha256": chunk.sha256,
            "final": chunk.final,
            "mime_type": chunk.mime_type,
            "blob_mime_type": OPAQUE_BLOB_MIME_TYPE,
        }
    }


def read_media_chunk_resources(value: ChunkReadout) -> list[ToolResource]:
    chunk = value.chunk
    return [ToolResource(uri=resource_uri(value.project, chunk.media_id, chunk.index), data=chunk.data)]


def upload_status_projection(value: UploadStatus) -> dict[str, Any]:
    payload = asdict(value)
    payload["missing_chunks"] = list(value.missing_chunks[:100])
    payload["missing_chunks_truncated"] = len(value.missing_chunks) > 100
    return {"media_upload": payload}


def jianying_package_projection(value: JianyingPackageReadout) -> dict[str, Any]:
    return {"jianying_package": asdict(value.package), "media": _descriptor_json(value.media)}


def jianying_package_summary(value: JianyingPackageReadout) -> str:
    package = value.package
    return (
        f"Jianying package prepared for timeline {package.timeline_id} ({package.narration}, Jianying {package.jianying_version}, "
        f"folder {package.draft_folder}): {package.size_bytes} bytes in {value.media.chunk_count} chunk(s); "
        "download with read_media_chunk before it expires."
    )


__all__ = [
    "AppendMediaUploadChunkRequest",
    "BeginMediaUploadRequest",
    "ChunkReadout",
    "DescribeMediaRequest",
    "JianyingPackageReadout",
    "PrepareJianyingPackageRequest",
    "ReadMediaChunkRequest",
    "append_media_upload_chunk_tool",
    "begin_media_upload_tool",
    "describe_media_projection",
    "describe_media_summary",
    "describe_media_tool",
    "jianying_package_projection",
    "jianying_package_summary",
    "prepare_jianying_package_tool",
    "read_media_chunk_projection",
    "read_media_chunk_resources",
    "read_media_chunk_tool",
    "upload_status_projection",
]
