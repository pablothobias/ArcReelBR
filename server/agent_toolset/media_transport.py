"""Remote-only media transport declarations and the media resource template.

These tools exist for external agents that cannot read the server's project directory: the embedded Agent reads
project files natively, so ``MEDIA_TRANSPORT_TOOLS`` is not part of ``AGENT_TOOLSET`` and is registered only on the
remote MCP host (adapted with ``remote_tools``), like the session tools in ``server/session_mcp.py``.

Every binary block uses ``application/octet-stream``; the real media type is only in structured metadata. Client
support for embedded blob resources varies by host and is not verified for every client."""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from lib.project.project_manager import ProjectManager
from server.agent_toolset.declaration import BLOCKED, OPAQUE_BLOB_MIME_TYPE, Exempt, ToolDeclaration
from server.agent_toolset.remote import authenticated_caller, resolve_project_scope
from server.media_tools.media_transport import (
    AppendMediaUploadChunkRequest,
    BeginMediaUploadRequest,
    DescribeMediaRequest,
    PrepareJianyingPackageRequest,
    ReadMediaChunkRequest,
    append_media_upload_chunk_tool,
    begin_media_upload_tool,
    describe_media_projection,
    describe_media_summary,
    describe_media_tool,
    jianying_package_projection,
    jianying_package_summary,
    prepare_jianying_package_tool,
    read_media_chunk_projection,
    read_media_chunk_resources,
    read_media_chunk_tool,
    upload_status_projection,
)
from server.services.media_transport.errors import MediaTransportError
from server.services.media_transport.transport import RESOURCE_URI_TEMPLATE, read_media_chunk
from server.tool_runtime import Services

#: Reads stay available on a migration-failed project so already rendered or generated media can still be retrieved;
#: the ``media_chunk`` resource template follows the same policy (it has no migration gate either).
READ_MIGRATION_POLICY = Exempt(
    "byte delivery of already-identified media; reads no project metadata that a migration rewrites"
)

DESCRIBE_MEDIA = ToolDeclaration(
    name="describe_media",
    description=(
        "Identify one project media file for download by a typed selector and return its descriptor: media_id (opaque "
        "token binding project, kind, selector, version and sha256), kind, selector (with the resolved version pinned), "
        "version, mime_type, size_bytes, sha256, chunk_size, chunk_count and resource_uri_template. Read-only and free: no "
        "generation, rendering or provider call. Kinds: asset_sheet (asset_type + name), character_derivative "
        "(base/derivative), product_reference_image (product + zero-based index), character_reference_image (uploaded "
        "reference image of a character), style_image (project style reference), character_voice_reference (bound "
        "reference audio of a character), voice_sample (task_id of a succeeded voice_sample task), storyboard_image and "
        "end_frame (script + item_id), grid_composite (grid_id), narration_audio (unit_id), unit_video (script + unit_id; "
        "storyboard or reference video), final_cut (timeline + variant), jianying_package (package_id from "
        "prepare_jianying_package) and bgm (bgm_id). Versioned kinds default to the current version and pin it, so later "
        "regeneration does not change what this media_id reads. Refusals: media_not_found, version_not_found "
        "(params.available_versions), media_missing, media_path_refused (outside the project, symbolic link or "
        "non-regular file), media_unavailable (object storage). Results never contain filesystem paths."
    ),
    request_model=DescribeMediaRequest,
    migration=READ_MIGRATION_POLICY,
    domain_key="media",
    handler=describe_media_tool,
    summary=describe_media_summary,
    projection=describe_media_projection,
)

READ_MEDIA_CHUNK = ToolDeclaration(
    name="read_media_chunk",
    description=(
        "Read one chunk of media identified by describe_media. The bytes arrive as an embedded resource block "
        "(BlobResourceContents, mimeType application/octet-stream; the real type is media_chunk.mime_type), never as "
        "base64 in the JSON. media_chunk carries media_id, index, offset, length, chunk_sha256 (of this chunk), "
        "total_size, sha256 (of the whole file) and final (true on the last chunk). Read indices 0..chunk_count-1, verify "
        "each chunk_sha256, concatenate in order, and check the total against sha256. Every call re-resolves the media and "
        "verifies its bytes still match the media_id; if the file changed, it returns media_version_changed and no bytes, "
        "so restart from describe_media instead of mixing versions. Other refusals: media_id_invalid (tampered or "
        "malformed), media_project_mismatch (issued for another project), chunk_out_of_range, media_missing. Read-only."
    ),
    request_model=ReadMediaChunkRequest,
    migration=READ_MIGRATION_POLICY,
    domain_key="media_chunk",
    handler=read_media_chunk_tool,
    projection=read_media_chunk_projection,
    resources=read_media_chunk_resources,
)

BEGIN_MEDIA_UPLOAD = ToolDeclaration(
    name="begin_media_upload",
    description=(
        "Start staging a client file too large for one inline content_base64 argument. Declare filename, exact "
        "size_bytes, sha256 of the whole file and purpose; returns upload_id, chunk_size, chunk_count, missing_chunks and "
        "expires_at. Staging is private to this project and this API key, expires after inactivity, and never installs "
        "media: pass the completed upload_id to a tool that accepts staged_upload_id, which applies its own native "
        "validation and size limits. Refuses upload_too_large above the purpose's native limit and upload_quota_exceeded when this API key already holds too many active uploads or the project's staged bytes would exceed the quota."
    ),
    request_model=BeginMediaUploadRequest,
    migration=BLOCKED,
    domain_key="media_upload",
    handler=begin_media_upload_tool,
    projection=upload_status_projection,
)

APPEND_MEDIA_UPLOAD_CHUNK = ToolDeclaration(
    name="append_media_upload_chunk",
    description=(
        "Append one chunk to a staged upload: content_base64 holds exactly chunk_size raw bytes (the last chunk the "
        "remainder); chunks may arrive in any order and resending an index overwrites it until the upload completes; a verified upload is immutable and further appends return upload_already_complete. Returns received_chunks, "
        "missing_chunks and complete. When the last missing chunk arrives the whole file is checked against the declared "
        "sha256; a mismatch discards the upload and returns upload_digest_mismatch. Other refusals: upload_not_found "
        "(unknown, another project or another API key), upload_expired, upload_chunk_invalid (bad index, length, base64 or "
        "chunk_sha256). Never installs media."
    ),
    request_model=AppendMediaUploadChunkRequest,
    migration=BLOCKED,
    domain_key="media_upload",
    handler=append_media_upload_chunk_tool,
    projection=upload_status_projection,
)

PREPARE_JIANYING_PACKAGE = ToolDeclaration(
    name="prepare_jianying_package",
    description=(
        "Prepare the Jianying download package of a draft already exported by export_jianying_draft, exactly as the Web "
        "download does: the user's local Jianying draft directory (draft_path, as the user stated it) and Jianying version "
        "(5 or 6, where 6 means 6 or later) are substituted into the draft, and project materials are bundled into a zip. "
        "Nothing is rendered, queued or charged, and nothing is written to the user's computer; the user extracts the zip "
        "into that directory themselves. Stale drafts remain packageable. The package is retained server-side for a "
        "limited time and returned as jianying_package plus a media descriptor (kind jianying_package) for "
        "read_media_chunk. Refusals: jianying_draft_not_exported, jianying_draft_version_changed (expected_draft_version "
        "differs), jianying_draft_invalid, timeline_not_found, jianying_path_invalid / jianying_path_too_long / "
        "jianying_path_illegal. Jianying compatibility is not CapCut compatibility."
    ),
    request_model=PrepareJianyingPackageRequest,
    migration=BLOCKED,
    domain_key="jianying_package",
    handler=prepare_jianying_package_tool,
    summary=jianying_package_summary,
    projection=jianying_package_projection,
)

MEDIA_TRANSPORT_TOOLS = (
    DESCRIBE_MEDIA,
    READ_MEDIA_CHUNK,
    BEGIN_MEDIA_UPLOAD,
    APPEND_MEDIA_UPLOAD_CHUNK,
    PREPARE_JIANYING_PACKAGE,
)

MEDIA_TRANSPORT_TOOL_IDS = frozenset(declaration.name for declaration in MEDIA_TRANSPORT_TOOLS)


class MediaResourceError(ValueError):
    """Sanitized resource-template refusal: ``<code>: <detail>`` without filesystem paths."""


def register_media_resources(server: FastMCP, projects: ProjectManager, *, services: Services | None = None) -> None:
    """Register ``arcreel://media/{project}/{media_id}/{index}`` serving the same verified chunk as read_media_chunk.

    ``{project}`` must equal the project bound in ``media_id``; chunk size is the one bound in ``media_id``. Errors carry
    only a stable code and a path-free detail."""

    def _queue() -> Any:
        if services is not None:
            return services.queue
        from lib.generation.generation_queue import get_generation_queue

        return get_generation_queue()

    @server.resource(
        RESOURCE_URI_TEMPLATE,
        name="arcreel_media_chunk",
        description=(
            "One verified chunk of ArcReel media identified by describe_media; same bytes and checks as read_media_chunk. "
            "Blob mimeType is application/octet-stream."
        ),
        mime_type=OPAQUE_BLOB_MIME_TYPE,
    )
    async def media_chunk(project: str, media_id: str, index: str) -> bytes:
        authenticated_caller()
        try:
            chunk_index = int(index)
        except ValueError:
            raise MediaResourceError("chunk_out_of_range: index must be an integer") from None
        try:
            scope = await asyncio.to_thread(resolve_project_scope, project, projects)
        except (FileNotFoundError, ValueError):
            raise MediaResourceError("invalid_project: project is invalid or unavailable") from None
        try:
            chunk = await read_media_chunk(projects, scope.project_name, media_id, chunk_index, queue=_queue())
        except MediaTransportError as exc:
            raise MediaResourceError(f"{exc.code}: {exc.detail}") from None
        except Exception:
            raise MediaResourceError("internal_error: media chunk could not be read") from None
        return chunk.data


__all__ = [
    "APPEND_MEDIA_UPLOAD_CHUNK",
    "BEGIN_MEDIA_UPLOAD",
    "DESCRIBE_MEDIA",
    "MEDIA_TRANSPORT_TOOLS",
    "MEDIA_TRANSPORT_TOOL_IDS",
    "PREPARE_JIANYING_PACKAGE",
    "READ_MEDIA_CHUNK",
    "register_media_resources",
]
