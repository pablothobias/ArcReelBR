"""Custom-provider management API.

Endpoints for CRUD, model management/discovery, and connectivity checks. Provider validation and write
transactions live in :mod:`server.services.configuration.custom_providers`; these routes add HTTP binding only."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lib.backends.artifact_download_guard import artifact_http_client
from lib.backends.http_status_errors import raise_for_status_redacted
from lib.catalog.model_id import has_dot_segment
from lib.custom_provider.discovery_formats import is_comfyui_protocol
from lib.db import get_async_session
from lib.db.repositories.custom_provider_repo import CustomProviderRepository
from lib.infra.api_errors import BadRequestError
from server.i18n import Translator

# Compatibility re-exports for existing test importers; the service module owns them.
from server.services.configuration.custom_providers import (
    CAPABILITY_OVERRIDE_ALLOWLIST as CAPABILITY_OVERRIDE_ALLOWLIST,
)
from server.services.configuration.custom_providers import (
    CreateProviderRequest,
    EndpointCatalogResponse,
    FullUpdateProviderRequest,
    ReloadLimits,
    UpdateProviderRequest,
    builtin_endpoint_definition,
    create_custom_provider,
    delete_custom_provider,
    endpoint_catalog,
    get_provider_response,
    invalidate_provider_caches_with,
    list_provider_responses,
    patch_custom_provider,
    replace_custom_provider,
)
from server.services.configuration.custom_providers import ModelInput as ModelInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custom-providers", tags=["Custom Providers"])

_CONNECTIVITY_CHECK_TIMEOUT = 15  # Seconds.

#: ComfyUI connectivity probe path, anonymously accessible on unauthenticated servers, also verifying correct addresses.
_COMFYUI_SYSTEM_STATS_PATH = "/system_stats"


class ConnectivityCheckRequest(BaseModel):
    # Connectivity deliberately accepts arbitrary strings; _run_connectivity_check soft-fails with 200 + success=False.
    discovery_format: str
    base_url: str
    api_key: str


class ConnectivityCheckResponse(BaseModel):
    success: bool
    message: str
    model_count: int = 0


class DiscoverResponse(BaseModel):
    models: list[dict] = []
    # Protocol has no enumerable models. ComfyUI models are workflow node choices, without a list matching rows;
    # empty lists would mean none discovered and misleadingly prompt credential checks.
    # Frontend replaces discovery buttons with explanatory text using this flag.
    not_applicable: bool = False
    reason: str | None = None


class DiscoverAnthropicRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None


def request_reload_limits(request: Request) -> ReloadLimits:
    """The running app's generation-worker rate-limit refresh, or ``None`` without a worker."""
    worker = getattr(request.app.state, "generation_worker", None)
    return worker.reload_limits if worker else None


async def invalidate_provider_caches(request: Request) -> None:
    """Clear backend-instance caches and refresh worker rate-limit configuration."""
    await invalidate_provider_caches_with(request_reload_limits(request))


# ---------------------------------------------------------------------------
# Provider CRUD
# ---------------------------------------------------------------------------


@router.get("")
async def list_providers(
    session: AsyncSession = Depends(get_async_session),
):
    """List all custom providers including model lists."""
    return {"providers": await list_provider_responses(session)}


# Register /endpoints before /{provider_id}, or FastAPI interprets "endpoints" as provider_id.
@router.get("/endpoints", response_model=EndpointCatalogResponse)
async def list_endpoint_catalog(
    session: AsyncSession = Depends(get_async_session),
) -> EndpointCatalogResponse:
    """Expose both endpoint namespaces as frontend source of truth for dropdowns, paths, and grouping.

    Built-ins use ENDPOINT_REGISTRY; custom definitions resolve from custom_endpoint rows on demand,
    without startup-wide loading, so in-place edits appear next fetch."""
    return await endpoint_catalog(session)


@router.get("/endpoints/{endpoint_key}/definition")
async def get_endpoint_definition(endpoint_key: str, _t: Translator) -> dict[str, Any]:
    """Get built-in declarative definition JSON for verbatim POST as a ce-<id> personal copy.

    Python built-ins have no definition and return 404 like unknown keys. Return raw definitions without
    envelopes, identical to import/export file formats."""
    definition = builtin_endpoint_definition(endpoint_key)
    if definition is None:
        raise HTTPException(status_code=404, detail=_t("endpoint_definition_not_found", endpoint=endpoint_key))
    return definition


@router.post("", status_code=201)
async def create_provider(
    body: CreateProviderRequest,
    request: Request,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a custom provider, optionally with models."""
    return await create_custom_provider(session, body, _t, reload_limits=request_reload_limits(request))


@router.get("/{provider_id}")
async def get_provider(
    provider_id: int,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
):
    """Get one custom provider's details."""
    return await get_provider_response(session, provider_id, _t)


@router.patch("/{provider_id}")
async def update_provider(
    provider_id: int,
    body: UpdateProviderRequest,
    request: Request,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
):
    """Update custom-provider configuration."""
    return await patch_custom_provider(session, provider_id, body, _t, reload_limits=request_reload_limits(request))


@router.put("/{provider_id}")
async def full_update_provider(
    provider_id: int,
    body: FullUpdateProviderRequest,
    request: Request,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
):
    """Atomically update provider metadata/model list in one transaction and clear global defaults referencing removed models.

    Omitted ``models`` updates only metadata/concurrency, leaving models unchanged."""
    return await replace_custom_provider(session, provider_id, body, _t, reload_limits=request_reload_limits(request))


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: int,
    request: Request,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a custom provider, cascading model deletion and clearing dangling defaults."""
    await delete_custom_provider(session, provider_id, _t, reload_limits=request_reload_limits(request))


# ---------------------------------------------------------------------------
# Stateless operations.
# ---------------------------------------------------------------------------


@router.post("/discover")
async def discover_models_endpoint(
    body: ConnectivityCheckRequest,
    _t: Translator,
):
    """Discover models using discovery_format + base_url + api_key."""
    return await _run_discover(body.discovery_format, body.base_url, body.api_key, _t)


@router.post("/discover-anthropic", response_model=DiscoverResponse)
async def discover_anthropic_models_endpoint(
    body: DiscoverAnthropicRequest,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
):
    """Anthropic model discovery for Agent configuration.

    Missing credentials fall back to active credentials (AgentCredentialRepository)."""
    body_key = (body.api_key or "").strip()
    needs_key = not body_key
    needs_url = body.base_url is None

    cred = None
    if needs_key or needs_url:
        from lib.db.repositories.agent_credential_repo import AgentCredentialRepository

        cred = await AgentCredentialRepository(session).get_active()

    api_key = body_key if not needs_key else (cred.api_key if cred else "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail=_t("anthropic_discovery_no_key"))

    base_url = body.base_url if not needs_url else (_credential_discovery_base(cred) if cred else None)
    if base_url:
        from lib.config.url_utils import InvalidAnthropicBaseUrlError, validate_anthropic_base_url

        try:
            base_url = validate_anthropic_base_url(base_url)
        except InvalidAnthropicBaseUrlError as exc:
            # Fixed wording, never echo inputs: URLs may contain mistakenly entered api_key.
            raise HTTPException(status_code=422, detail=_t("agent_base_url_invalid")) from exc

    return await _run_discover("anthropic", base_url, api_key, _t)


@router.post("/{provider_id}/discover")
async def discover_models_by_id(
    provider_id: int,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
):
    """Discover a provider's available models using stored credentials."""
    return await discover_custom_provider_models(session, provider_id, _t)


async def discover_custom_provider_models(
    session: AsyncSession, provider_id: int, _t: Callable[..., str]
) -> DiscoverResponse:
    """Discover custom-provider models with stored credentials, including matched entries/default endpoints for each."""
    provider = await CustomProviderRepository(session).get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail=_t("provider_not_found"))
    return await _run_discover(provider.discovery_format, provider.base_url, provider.api_key, _t)


@router.post("/test")
async def check_connectivity(
    body: ConnectivityCheckRequest,
    _t: Translator,
):
    """Check discovery_format + base_url + api_key reachability. Free probe, proving no model generation capability."""
    return await _run_connectivity_check(body.discovery_format, body.base_url, body.api_key, _t)


@router.post("/{provider_id}/test")
async def check_connectivity_by_id(
    provider_id: int, _t: Translator, session: AsyncSession = Depends(get_async_session)
):
    """Check a provider's connectivity using stored credentials."""
    repo = CustomProviderRepository(session)
    provider = await repo.get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail=_t("provider_not_found"))
    return await _run_connectivity_check(provider.discovery_format, provider.base_url, provider.api_key, _t)


def _credential_discovery_base(cred: Any) -> str | None:
    """Active-credential root for model discovery.

    If preset credentials did not override base_url (stored value still equals preset ``messages_url``),
    use preset ``discovery_url`` (DeepSeek model lists are outside the messages root). Custom/overridden
    credentials use stored values. Matches frontend rules that prefills do not count as overrides."""
    from lib.agent.agent_provider_catalog import get_preset

    preset = get_preset(cred.preset_id) if cred.preset_id else None
    if preset is not None and cred.base_url == preset.messages_url:
        return preset.discovery_url or preset.messages_url
    return cred.base_url


async def _run_discover(
    discovery_format: str,
    base_url: str | None,
    api_key: str,
    _t: Callable[..., str],
    *,
    discover_models_fn: Callable[..., Awaitable[list[dict]]] | None = None,
) -> DiscoverResponse:
    """Shared discovery logic for plaintext/stored credential entry points."""
    from lib.config.url_utils import InvalidAnthropicBaseUrlError
    from lib.custom_provider.discovery import UnsupportedDiscoveryFormatError, discover_models

    if is_comfyui_protocol(discovery_format):
        # Structured not-applicable, not 422: the protocol lacks discovery, rather than discovery failing.
        return DiscoverResponse(not_applicable=True, reason=_t("discovery_not_applicable_comfyui"))
    try:
        discover = discover_models_fn or discover_models
        models = await discover(
            discovery_format=discovery_format,
            base_url=base_url or None,
            api_key=api_key,
        )
        # IDs with dot segments are rejected on add, so exclude from addable lists.
        return DiscoverResponse(models=[m for m in models if not has_dot_segment(str(m.get("model_id", "")))])
    except UnsupportedDiscoveryFormatError as exc:
        raise BadRequestError("invalid_discovery_format", discovery_format=discovery_format) from exc
    except InvalidAnthropicBaseUrlError as exc:
        # Boundary-rejected addresses are not upstream failures: return 422 like /discover-anthropic, without echoing inputs.
        raise HTTPException(status_code=422, detail=_t("agent_base_url_invalid")) from exc
    except Exception as exc:
        err_msg = str(exc)
        if len(err_msg) > 200:
            err_msg = err_msg[:200] + "..."
        logger.warning("模型发现失败: %s", err_msg)
        raise HTTPException(status_code=502, detail=_t("discovery_failed", err_msg=err_msg)) from exc


async def _run_connectivity_check(
    discovery_format: str,
    base_url: str,
    api_key: str,
    _t: Callable[..., str],
    *,
    openai_probe: Callable[[str, str, Callable[..., str]], ConnectivityCheckResponse] | None = None,
    google_probe: Callable[[str, str, Callable[..., str]], ConnectivityCheckResponse] | None = None,
) -> ConnectivityCheckResponse:
    """Shared connectivity checks for plaintext/stored credential entry points."""
    try:
        if discovery_format == "openai":
            result = await asyncio.wait_for(
                asyncio.to_thread(openai_probe or _check_openai, base_url, api_key, _t),
                timeout=_CONNECTIVITY_CHECK_TIMEOUT,
            )
        elif discovery_format == "google":
            result = await asyncio.wait_for(
                asyncio.to_thread(google_probe or _check_google, base_url, api_key, _t),
                timeout=_CONNECTIVITY_CHECK_TIMEOUT,
            )
        elif is_comfyui_protocol(discovery_format):
            # No to_thread: ComfyUI probes use async httpx directly; other checks use synchronous SDKs.
            result = await asyncio.wait_for(
                _check_comfyui(base_url, api_key, _t),
                timeout=_CONNECTIVITY_CHECK_TIMEOUT,
            )
        else:
            return ConnectivityCheckResponse(
                success=False,
                message=_t("connectivity_check_unsupported_format", discovery_format=discovery_format),
            )
        return result
    except TimeoutError:
        return ConnectivityCheckResponse(
            success=False,
            message=_t("connectivity_check_timeout"),
        )
    except Exception as exc:
        err_msg = str(exc)
        if len(err_msg) > 200:
            err_msg = err_msg[:200] + "..."
        logger.warning("连通性检查失败 [%s]: %s", discovery_format, err_msg)
        return ConnectivityCheckResponse(
            success=False,
            message=_t("connectivity_check_failed", err_msg=err_msg),
        )


def _check_openai(
    base_url: str,
    api_key: str,
    _t: Callable[..., str],
    *,
    client_factory: Callable[..., Any] | None = None,
) -> ConnectivityCheckResponse:
    """Check OpenAI-compatible APIs using models.list()."""
    from openai import OpenAI

    from lib.config.url_utils import ensure_openai_base_url

    client = (client_factory or OpenAI)(api_key=api_key, base_url=ensure_openai_base_url(base_url))
    models = client.models.list()
    count = sum(1 for _ in models)
    return ConnectivityCheckResponse(
        success=True,
        message=_t("connectivity_check_ok"),
        model_count=count,
    )


def _check_google(
    base_url: str,
    api_key: str,
    _t: Callable[..., str],
    *,
    client_factory: Callable[..., Any] | None = None,
) -> ConnectivityCheckResponse:
    """Check Google genai APIs using models.list()."""
    from google import genai

    from lib.config.url_utils import ensure_google_base_url

    effective_url = ensure_google_base_url(base_url)
    http_options: genai.types.HttpOptionsDict | None = {"base_url": effective_url} if effective_url else None
    client = (client_factory or genai.Client)(api_key=api_key, http_options=http_options)
    pager = client.models.list()
    count = sum(1 for _ in pager)
    return ConnectivityCheckResponse(
        success=True,
        message=_t("connectivity_check_ok"),
        model_count=count,
    )


def _comfyui_probe_headers(api_key: str) -> dict[str, str]:
    """ComfyUI probe headers: send ``api_key`` directly as Bearer, or no credentials when empty.

    Do not render definition ``auth`` here (``docs/adr/0081``): endpoint-specific templates are unavailable
    to provider-level probes, which must not guess for one endpoint. Custom-header reverse-proxy auth
    may therefore fail probing; frontend directs users to connection-test results as authoritative."""
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


async def _check_comfyui(
    base_url: str,
    api_key: str,
    _t: Callable[..., str],
) -> ConnectivityCheckResponse:
    """Check ComfyUI reachability with ``GET {base_url}/system_stats`` and echo ``comfyui_version``.

    Omit ``model_count``: ComfyUI has no enumerable list, and 0 would imply no models.

    Validate destinations through ``artifact_http_client``, sharing submission/polling/download gates:
    reject link-local/cloud-metadata addresses, allow loopback/private networks for legitimate self-hosted
    ComfyUI. Rejections follow ``_run_connectivity_check`` failure responses, shaped like upstream unreachability."""
    url = base_url.strip().rstrip("/") + _COMFYUI_SYSTEM_STATS_PATH
    async with artifact_http_client(timeout=_CONNECTIVITY_CHECK_TIMEOUT) as client:
        resp = await client.get(url, headers=_comfyui_probe_headers(api_key))
    raise_for_status_redacted(resp)
    payload = resp.json()
    system = payload.get("system") if isinstance(payload, dict) else None
    version = system.get("comfyui_version") if isinstance(system, dict) else None
    # Missing versions still mean reachable: old versions/proxies omit the field, and rejection would block usable deployments.
    message = (
        _t("connectivity_check_comfyui_ok", version=str(version))
        if version
        else _t("connectivity_check_comfyui_ok_unknown_version")
    )
    return ConnectivityCheckResponse(success=True, message=message)
