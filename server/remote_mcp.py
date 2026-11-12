"""Streamable-HTTP adapter for ArcReel's host-independent tools."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any

from fastapi.responses import PlainTextResponse
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from lib.project.project_manager import ProjectManager, get_project_manager
from lib.script.source_loader import SourceLoader
from server.agent_runtime.service import AssistantService
from server.agent_toolset.global_config import (
    GLOBAL_CONFIG_INSTRUCTIONS,
    GLOBAL_CONFIG_TOOL_IDS,
    GatedToolsFastMCP,
    authorized_key_names,
    build_global_config_tools,
    global_config_authorized,
)
from server.agent_toolset.media_transport import MEDIA_TRANSPORT_TOOLS, register_media_resources
from server.agent_toolset.remote import remote_tools
from server.agent_toolset.toolset import AGENT_TOOLSET
from server.auth import API_KEY_PREFIX
from server.auth import verify_api_key as default_verify_api_key
from server.services.configuration.custom_providers import ReloadLimits
from server.services.tasks.artifact_download_retry import ArtifactDownloadWorker
from server.session_mcp import default_session_service, session_tools
from server.tool_runtime import Services

logger = logging.getLogger(__name__)

#: Sent to every client at initialize (no secret, identical for every key).
REMOTE_MCP_INSTRUCTIONS = (
    "ArcReel tools for producing short videos through the existing ArcReel Agent and native project transactions. "
    + GLOBAL_CONFIG_INSTRUCTIONS
)

_UNPUBLISHED_ISSUER_URL = AnyHttpUrl("http://localhost/")

# One decoded control byte may occupy six JSON bytes (``\u00XX``); leave 1 MiB for the MCP envelope.
_MAX_REQUEST_BODY_BYTES = SourceLoader.DEFAULT_MAX_BYTES * 6 + 1024 * 1024


class ArcApiKeyVerifier(TokenVerifier):
    """Bridge MCP Bearer auth to ArcReel's existing API Key verifier."""

    def __init__(
        self, verify_api_key: Callable[[str], Awaitable[dict[str, Any] | None]] = default_verify_api_key
    ) -> None:
        self._verify_api_key = verify_api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token.startswith(API_KEY_PREFIX):
            return None
        payload = await self._verify_api_key(token)
        if payload is None:
            return None
        return AccessToken(token=token, client_id=payload["sub"], scopes=["arcreel"])


def build_remote_mcp_server(
    *,
    projects: ProjectManager | None = None,
    services: Services | None = None,
    token_verifier: TokenVerifier | None = None,
    session_service_factory: Callable[[], AssistantService] = default_session_service,
    reload_limits: ReloadLimits = None,
    global_config_key_names: Iterable[str] | None = None,
    artifact_download_worker: ArtifactDownloadWorker | None = None,
) -> FastMCP:
    """Build one restart-safe MCP server instance for the host lifespan.

    Remote-only surfaces join the shared toolset here: media transport (byte delivery/staging for external clients,
    which the embedded agent does not need) and global endpoint/provider configuration. Configuration tools are
    registered only for API-key names granted by the operator (``ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS`` or
    ``global_config_key_names``) and are hidden and refused for every other key; default is deny. ``reload_limits`` is
    the running generation worker's limit refresh, injected at app assembly; without it, provider configuration writes
    are refused rather than leaving worker limits stale. ``artifact_download_worker`` is the same worker's
    retrieval-resume surface for ``retry_artifact_download``; without it that tool refuses with a stable problem."""
    if services is not None:
        if projects is not None and projects.data_root.resolve() != services.projects.data_root.resolve():
            raise ValueError("projects and services.projects must belong to the same project root")
        projects = services.projects
        if artifact_download_worker is not None:
            services = replace(services, artifact_download_worker=artifact_download_worker)
    else:
        projects = projects or get_project_manager()
        services = Services.defaults(projects, artifact_download_worker=artifact_download_worker)

    names = None if global_config_key_names is None else frozenset(global_config_key_names)
    # Activation check for operators: count only, never the key names.
    granted = len(authorized_key_names() if names is None else names)
    logger.info("Remote MCP global configuration tools granted to %d API key name(s)", granted)
    server = GatedToolsFastMCP(
        "arcreel",
        instructions=REMOTE_MCP_INSTRUCTIONS,
        tools=[
            *remote_tools(AGENT_TOOLSET, projects=projects, services=services),
            *remote_tools(MEDIA_TRANSPORT_TOOLS, projects=projects, services=services),
            *session_tools(projects=projects, service_factory=session_service_factory),
            *build_global_config_tools(
                projects=projects, services=services, reload_limits=reload_limits, authorized_names=names
            ),
        ],
        gated_tool_names=GLOBAL_CONFIG_TOOL_IDS,
        is_authorized=lambda: global_config_authorized(names),
        token_verifier=token_verifier or ArcApiKeyVerifier(),
        # ArcReel accepts only static arc- API keys, with no OAuth authorization server (ADR 0065), and declares no RFC 9728
        # protected-resource metadata: MCP requires metadata to list at least one authorization server, so declaring it would direct discovering clients
        # into an OAuth flow that cannot succeed. Without resource_server_url, 401 returns only a plain Bearer challenge;
        # issuer_url is required by the SDK but exposed only when authorization routes or metadata are registered; neither occurs here.
        auth=AuthSettings(
            issuer_url=_UNPUBLISHED_ISSUER_URL,
            resource_server_url=None,
            required_scopes=["arcreel"],
        ),
        stateless_http=True,
        streamable_http_path="/",
        json_response=False,
        max_request_body_size=_MAX_REQUEST_BODY_BYTES,
        # Every endpoint request requires an arc- API key, never stored as a browser cookie / session;
        # requests rebound to this endpoint lack credentials and receive 401. A Host allowlist is not a security boundary here
        # and would only block legitimate deployments; reverse proxies and deployment topology govern Host ownership. Browser cross-origin protection comes solely from
        # application-level CORSMiddleware (CORS_ORIGINS, see server/cors_config.py).
        # Disabling this switch does not affect the SDK’s POST Content-Type validation.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    register_media_resources(server, projects, services=services)
    return server


class RemoteMCPHost:
    """Stable ASGI mount whose one-shot SDK manager is rebuilt per host lifespan."""

    def __init__(self, server_factory: Callable[..., FastMCP] = build_remote_mcp_server) -> None:
        self._server_factory = server_factory
        self._app: Any | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._app is None:
            await PlainTextResponse("MCP server is not running", status_code=503)(scope, receive, send)
            return
        await self._app(scope, receive, send)

    @asynccontextmanager
    async def run(
        self, *, reload_limits: ReloadLimits = None, artifact_download_worker: ArtifactDownloadWorker | None = None
    ) -> AsyncGenerator[None]:
        """Serve for one host lifespan; the app's generation-worker hooks (``reload_limits`` limit refresh and the
        ``artifact_download_worker`` retrieval resume) reach the factory only when given."""
        hooks: dict[str, Any] = {
            key: value
            for key, value in (("reload_limits", reload_limits), ("artifact_download_worker", artifact_download_worker))
            if value is not None
        }
        server = self._server_factory(**hooks)
        child_app = server.streamable_http_app()
        async with server.session_manager.run():
            self._app = child_app
            try:
                yield
            finally:
                self._app = None


remote_mcp_host = RemoteMCPHost()

REMOTE_MCP_PATH = "/mcp"


class _MountPrefixEndpoint:
    """Pass the mount prefix itself, without a trailing slash, to the same subapplication using Mount’s child scope instead of a 307 redirect.

    Match Starlette ``Mount``: retain the full ``path``, adding only the prefix to ``root_path``. The subapplication removes
    the prefix through ``get_route_path``; changing ``path`` to ``"/"`` would differ from ``Mount`` child scopes."""

    def __init__(self, prefix: str, app: ASGIApp) -> None:
        self._prefix = prefix
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        root_path = scope.get("root_path", "")
        child_scope = {
            **scope,
            "app_root_path": scope.get("app_root_path", root_path),
            "root_path": root_path + self._prefix,
            "path": scope["path"] + "/",
        }
        if "raw_path" in scope:
            child_scope["raw_path"] = scope["raw_path"] + b"/"
        await self._app(child_scope, receive, send)


def mount_remote_mcp(app: Starlette, mcp_app: ASGIApp) -> None:
    """Mount the remote MCP endpoint at ``/mcp``.

    The MCP specification uses ``/mcp`` without a trailing slash as the canonical endpoint. Handle it directly instead of
    returning 307: some clients do not follow POST redirects, and relative ``Location`` values escape reverse-proxy subpath
    prefixes. Retain ``/mcp/`` as a compatibility entry point."""
    app.router.routes.extend(
        [
            Route(REMOTE_MCP_PATH, _MountPrefixEndpoint(REMOTE_MCP_PATH, mcp_app), include_in_schema=False),
            Mount(REMOTE_MCP_PATH, mcp_app),
        ]
    )


__all__ = [
    "REMOTE_MCP_INSTRUCTIONS",
    "REMOTE_MCP_PATH",
    "ArcApiKeyVerifier",
    "RemoteMCPHost",
    "build_remote_mcp_server",
    "mount_remote_mcp",
    "remote_mcp_host",
]
