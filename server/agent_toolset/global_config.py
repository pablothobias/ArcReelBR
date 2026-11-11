"""Operator-gated global endpoint/provider configuration tools (remote MCP only).

These tools change instance-wide configuration, a different surface from project production. They are never part
of ``AGENT_TOOLSET``: the embedded Agent and project sessions cannot see them. The remote host registers them only
when ``ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS`` names at least one API key (default deny), lists them only to those keys,
and rechecks the caller on every call; other callers neither see nor can call them.

Policy, not a security boundary: any ``arc-`` API key already authenticates the REST admin API, which offers the same
endpoint/provider writes (including raw credential entry). This gate narrows the MCP tool surface; it does not
restrict what a key holder could do over REST.

Credentials are referenced only by opaque ids (the owning provider id); values are never accepted from or returned
to the caller. Validation and preview render offline: no connection test, provider call, generation or job."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from typing import Any, Literal

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.tools import Tool as FastMCPTool
from mcp.types import Tool as MCPTool
from pydantic import BaseModel, ConfigDict, Field

from lib.project.project_manager import ProjectManager
from server.agent_toolset.declaration import UnscopedHandler, UnscopedToolDeclaration
from server.agent_toolset.remote import remote_tool
from server.media_tools import global_config as handlers
from server.services.configuration.custom_providers import ReloadLimits
from server.tool_runtime import CallerContext, Services, ToolOutcome, ToolProblem, ToolRequest

#: Operator setting: comma-separated API-key names (``ArcReel API key`` names, not key values) granted these tools.
GLOBAL_CONFIG_API_KEYS_ENV = "ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS"

_APPLY_DESCRIPTION = (
    "false (default) only validates and reports changed field names, impact and revision without writing; "
    "true writes after the same checks"
)


def authorized_key_names(environ: Mapping[str, str] | None = None) -> frozenset[str]:
    """API-key names granted global configuration tools; empty means none (default deny)."""
    raw = (os.environ if environ is None else environ).get(GLOBAL_CONFIG_API_KEYS_ENV, "")
    return frozenset(name.strip() for name in raw.split(",") if name.strip())


def global_config_authorized(names: Iterable[str] | None = None) -> bool:
    """Whether the current MCP request's API-key subject (``apikey:<name>``) is granted; False without a request token."""
    token = get_access_token()
    if token is None:
        return False
    granted = authorized_key_names() if names is None else frozenset(names)
    return any(token.client_id == f"apikey:{name}" for name in granted)


# ---------------------------------------------------------------------------
# Request models.
# ---------------------------------------------------------------------------


class _Empty(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EndpointKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint_key: str = Field(min_length=1, description="Endpoint key from list_global_endpoints (built-in or ce-<id>)")


class ValidateDefinitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    definition: Any = Field(description="Endpoint definition JSON object to validate")
    exclude_endpoint_key: str | None = Field(
        default=None, description="ce-<id> being edited, excluded from duplicate detection"
    )


class PreviewParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(min_length=1, description="Model name sent to the provider")
    prompt: str = Field(default="", description="Prompt text")
    duration_seconds: int = Field(default=5, ge=1, description="Video duration in seconds")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio such as 9:16")
    resolution: str | None = Field(default=None, description="Resolution token such as 768p or 2k")
    generate_audio: bool = Field(default=True, description="Whether to request generated audio")


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    definition: Any = Field(description="Endpoint definition JSON object to render")
    parameters: PreviewParameters = Field(description="Call parameters used for rendering")
    base_url: str | None = Field(
        default=None, description="Optional provider base URL to render; omitted keeps the {{ base_url }} placeholder"
    )


class CopyBuiltinEndpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint_key: str = Field(min_length=1, description="Built-in declarative endpoint key, such as minimax-h3")
    allow_duplicate: bool = Field(
        default=False, description="Create another copy even when one with the same meta.author/meta.name exists"
    )


class UpdateCustomEndpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint_key: str = Field(min_length=1, description="Custom endpoint key ce-<id>")
    definition: Any = Field(description="Complete replacement definition JSON object")
    expected_revision: str = Field(min_length=1, description="revision returned by get_endpoint_definition")
    apply: bool = Field(default=False, description=_APPLY_DESCRIPTION)


class ProviderModelArgument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=1, description="Provider API model name, such as MiniMax-H3")
    display_name: str = Field(min_length=1, description="Display name")
    endpoint: str = Field(min_length=1, description="Endpoint key (built-in or ce-<id>)")
    is_default: bool = Field(default=False, description="Default model for its media type in this provider")
    is_enabled: bool = Field(default=True, description="Whether the model is enabled")
    resolution: str | None = Field(default=None, description="Default resolution token")
    capability_overrides: dict[str, Any] | None = Field(default=None, description="Sparse capability overrides")
    path_overrides: dict[str, str] | None = Field(default=None, description="Request-name to path overrides")
    multiplier: float = Field(default=1.0, ge=0, description="Provider-model price multiplier")
    entry_binding: str | None = Field(default=None, description="Catalog entry binding maker/name")


class ConfigureProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str | None = Field(
        default=None, description="custom-<id> to update; omit to create a new custom provider"
    )
    display_name: str = Field(min_length=1, description="Provider display name")
    discovery_format: Literal["openai", "google", "comfyui"] | None = Field(
        default=None, description="Protocol; required to create, immutable on update"
    )
    base_url: str = Field(min_length=1, description="Provider base URL")
    credential_ref: str | None = Field(
        default=None,
        description=(
            "Opaque reference of an existing credential to reuse: a built-in provider id (its active credential) or "
            "custom-<id>. Required to create; on update omit to keep the stored credential. Its original host must "
            "equal base_url's host"
        ),
    )
    models: list[ProviderModelArgument] | None = Field(
        default=None, description="Complete model list (replaces all); omit on update to keep models unchanged"
    )
    expected_revision: str | None = Field(
        default=None, description="Required on update: revision from list_global_providers"
    )
    image_max_workers: int | None = Field(default=None, ge=1, description="Image concurrency cap; omit to keep")
    video_max_workers: int | None = Field(default=None, ge=1, description="Video concurrency cap; omit to keep")
    audio_max_workers: int | None = Field(default=None, ge=1, description="Audio concurrency cap; omit to keep")
    apply: bool = Field(default=False, description=_APPLY_DESCRIPTION)


# ---------------------------------------------------------------------------
# Declarations.
# ---------------------------------------------------------------------------


def _gated_handler(handler: UnscopedHandler[Any, Any], authorized: Callable[[], bool]) -> UnscopedHandler[Any, Any]:
    """Second enforcement layer inside the handler itself, independent of the remote tool wrapper."""

    async def gated(request: ToolRequest[Any], caller: CallerContext, services: Services) -> ToolOutcome[Any]:
        if not authorized():
            return ToolOutcome(
                problem=ToolProblem(
                    "global_config_forbidden", "Global configuration tools are not granted to this API key"
                )
            )
        return await handler(request, caller, services)

    return gated


def global_config_declarations(
    reload_limits: ReloadLimits,
    *,
    authorized: Callable[[], bool] = global_config_authorized,
) -> tuple[UnscopedToolDeclaration[Any, Any], ...]:
    """Declarations whose handlers re-check ``authorized`` per call.

    ``reload_limits`` is the running generation worker's limit refresh, injected by the app; ``None`` makes provider
    configuration writes refuse with ``reload_limits_unavailable`` instead of leaving worker limits stale."""
    declarations = _declarations(reload_limits)
    return tuple(replace(d, handler=_gated_handler(d.handler, authorized)) for d in declarations)


def _declarations(reload_limits: ReloadLimits) -> tuple[UnscopedToolDeclaration[Any, Any], ...]:
    return (
        UnscopedToolDeclaration(
            name="list_global_providers",
            description=(
                "List built-in providers (credential status by opaque ref, catalog models) and custom providers "
                "(sanitized config, models, credential ref, revision). Never returns credential values. Read-only."
            ),
            request_model=_Empty,
            domain_key="providers",
            handler=handlers.list_global_providers,
        ),
        UnscopedToolDeclaration(
            name="list_global_endpoints",
            description=(
                "List built-in and custom call endpoints with kind, media type, definition availability and custom "
                "revisions. Read-only."
            ),
            request_model=_Empty,
            domain_key="endpoints",
            handler=handlers.list_global_endpoints,
        ),
        UnscopedToolDeclaration(
            name="get_endpoint_definition",
            description=(
                "Read one endpoint definition. Custom endpoints also return revision and impact (model rows, "
                "projects and global defaults referencing it). Read-only."
            ),
            request_model=EndpointKeyRequest,
            domain_key="endpoint",
            handler=handlers.get_endpoint_definition,
        ),
        UnscopedToolDeclaration(
            name="validate_endpoint_definition",
            description=(
                "Validate an endpoint definition with the shared saving validator and report author/name duplicates. "
                "Offline: no network, no job, no write."
            ),
            request_model=ValidateDefinitionRequest,
            domain_key="validation",
            handler=handlers.validate_endpoint_definition,
        ),
        UnscopedToolDeclaration(
            name="preview_endpoint_request",
            description=(
                "Render the submit/poll/result requests an endpoint definition would send, with the credential "
                "fully masked and asset placeholders. Offline: sends nothing; this is not Test connection."
            ),
            request_model=PreviewRequest,
            domain_key="preview",
            handler=handlers.preview_endpoint_request,
        ),
        UnscopedToolDeclaration(
            name="copy_builtin_endpoint",
            description=(
                "Copy a built-in declarative endpoint into a new editable custom endpoint (ce-<id>). Refuses when a "
                "copy with the same meta.author/meta.name exists unless allow_duplicate is true."
            ),
            request_model=CopyBuiltinEndpointRequest,
            domain_key="endpoint",
            handler=handlers.copy_builtin_endpoint,
        ),
        UnscopedToolDeclaration(
            name="update_custom_endpoint",
            description=(
                "Replace a custom endpoint definition conditionally on expected_revision. apply=false reports changed "
                "fields, duplicates and impact without writing; a changed revision returns revision_conflict."
            ),
            request_model=UpdateCustomEndpointRequest,
            domain_key="endpoint_update",
            handler=handlers.update_custom_endpoint,
        ),
        UnscopedToolDeclaration(
            name="configure_custom_provider",
            description=(
                "Create or update a custom provider and its model list, reusing an existing credential only by opaque "
                "credential_ref on the same host (different host refused). apply=false reports changed fields and "
                "impact without writing. Never tests connectivity, never sets project or global defaults; select "
                "routes per project with configure_project."
            ),
            request_model=ConfigureProviderRequest,
            domain_key="provider_configuration",
            handler=handlers.configure_custom_provider_handler(reload_limits),
        ),
    )


#: Catalog/schema view (no reload callback, so provider writes refuse). Remote-only: never add these to ``AGENT_TOOLSET``;
#: the remote host registers :func:`build_global_config_tools` with the app's callback instead.
GLOBAL_CONFIG_TOOLS = global_config_declarations(None)

GLOBAL_CONFIG_TOOL_IDS = frozenset(declaration.name for declaration in GLOBAL_CONFIG_TOOLS)

#: Non-secret discoverability note for the remote server's ``instructions`` (sent to every client at initialize), so an
#: ungranted client can tell "not granted" from "not implemented". It names the setting, never the granted key names.
GLOBAL_CONFIG_INSTRUCTIONS = (
    "Global provider/endpoint configuration: operator-granted tools ("
    + ", ".join(declaration.name for declaration in GLOBAL_CONFIG_TOOLS)
    + f") exist on this server but are listed and callable only for API keys whose names the operator lists in "
    f"{GLOBAL_CONFIG_API_KEYS_ENV} (comma-separated key names, never key values); the default grants none. "
    "Granting takes effect only after a server restart. If tools/list omits them, or a call answers 'Unknown tool', "
    "this API key is not granted. Ask for a grant only when the user requested a configuration change, and never "
    "reconfigure through other surfaces instead."
)


# ---------------------------------------------------------------------------
# Remote registration.
# ---------------------------------------------------------------------------


class _GatedTool(FastMCPTool):
    """Delegate to the declared remote tool only for authorized callers; others get the same error as an unknown tool."""

    delegate: FastMCPTool = Field(exclude=True)
    authorized: Callable[[], bool] = Field(exclude=True)

    async def run(self, arguments: dict[str, Any], context: Any = None, convert_result: bool = False) -> Any:
        if not self.authorized():
            raise ToolError(f"Unknown tool: {self.name}")
        return await self.delegate.run(arguments, context=context, convert_result=convert_result)


def build_global_config_tools(
    *,
    projects: ProjectManager,
    services: Services,
    reload_limits: ReloadLimits,
    authorized_names: Iterable[str] | None = None,
) -> list[FastMCPTool]:
    """Remote tools for granted API keys, or an empty list when none is granted (then nothing is registered).

    ``authorized_names`` defaults to ``ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS`` read at build time for registration; each
    call re-reads the setting unless explicit names were given."""
    fixed = None if authorized_names is None else frozenset(authorized_names)
    if not (fixed if fixed is not None else authorized_key_names()):
        return []

    def authorized() -> bool:
        return global_config_authorized(fixed)

    tools: list[FastMCPTool] = []
    for declaration in global_config_declarations(reload_limits, authorized=authorized):
        delegate = remote_tool(declaration, projects=projects, services=services)
        tools.append(
            _GatedTool(
                fn=delegate.fn,
                name=delegate.name,
                title=delegate.title,
                description=delegate.description,
                parameters=delegate.parameters,
                fn_metadata=delegate.fn_metadata,
                is_async=True,
                context_kwarg=None,
                annotations=None,
                delegate=delegate,
                authorized=authorized,
            )
        )
    return tools


class GatedToolsFastMCP(FastMCP):
    """FastMCP whose tool listing hides gated tools from callers that fail ``is_authorized``.

    Use in place of ``FastMCP`` when registering :func:`build_global_config_tools`; the gated tools also refuse calls
    themselves, so listing is a convenience, not the enforcement point."""

    def __init__(
        self,
        *args: Any,
        gated_tool_names: frozenset[str] = frozenset(),
        is_authorized: Callable[[], bool] = global_config_authorized,
        **kwargs: Any,
    ) -> None:
        self._gated_tool_names = gated_tool_names
        self._is_authorized = is_authorized
        super().__init__(*args, **kwargs)

    async def list_tools(self) -> list[MCPTool]:
        tools = await super().list_tools()
        if not self._gated_tool_names or self._is_authorized():
            return tools
        return [tool for tool in tools if tool.name not in self._gated_tool_names]


__all__ = [
    "GLOBAL_CONFIG_API_KEYS_ENV",
    "GLOBAL_CONFIG_INSTRUCTIONS",
    "GLOBAL_CONFIG_TOOLS",
    "GLOBAL_CONFIG_TOOL_IDS",
    "GatedToolsFastMCP",
    "authorized_key_names",
    "build_global_config_tools",
    "global_config_authorized",
    "global_config_declarations",
]
