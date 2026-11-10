"""Handlers for the operator-gated global endpoint/provider configuration tools.

Each handler opens one session from ``Services.sessions``, delegates to
:mod:`server.services.configuration.global_config`, and maps refusals to stable tool problems. No handler performs a
connection test, provider call, generation or job submission, and no result carries a credential value."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException
from mcp.server.auth.middleware.auth_context import get_access_token
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from lib.custom_provider.comfyui.failures import ComfyuiError
from lib.custom_provider.endpoint_test import EndpointTestParameters
from lib.i18n import DEFAULT_LOCALE
from lib.i18n import _ as translate
from lib.infra.api_errors import ApiError
from server.services.configuration import global_config as config
from server.services.configuration.custom_providers import KeyedHTTPException, ModelInput, ReloadLimits
from server.services.configuration.endpoint_definitions import RevisionConflict
from server.tool_runtime import CallerContext, Services, ToolOutcome, ToolProblem, ToolRequest

logger = logging.getLogger(__name__)


def _t(key: str, **params: Any) -> str:
    return translate(key, locale=DEFAULT_LOCALE, **params)


def caller_identity() -> str | None:
    """Authenticated API-key subject (``apikey:<name>``) for the audit trail; ``None`` outside an MCP request."""
    token = get_access_token()
    return token.client_id if token is not None else None


def _problem(exc: Exception) -> ToolProblem:
    if isinstance(exc, config.GlobalConfigRefused):
        return ToolProblem(exc.code, exc.detail, action=exc.action, params=dict(exc.params) or None)
    if isinstance(exc, RevisionConflict):
        return ToolProblem(
            "revision_conflict",
            "The endpoint definition changed since it was read; re-read it and retry with its current revision",
            action="Call get_endpoint_definition, reapply your edit to the current definition, and pass its revision",
            params={"expected": exc.expected, "current": exc.current},
        )
    if isinstance(exc, ApiError):
        params: dict[str, Any] = {"status": exc.status_code}
        if exc.diagnostic is not None:
            params["diagnostic"] = exc.diagnostic
        return ToolProblem(exc.key, _t(exc.key, **exc.params), params=params)
    if isinstance(exc, KeyedHTTPException):
        return ToolProblem(exc.key, str(exc.detail), params={"status": exc.status_code})
    if isinstance(exc, HTTPException):
        return ToolProblem("provider_config_rejected", str(exc.detail), params={"status": exc.status_code})
    if isinstance(exc, ComfyuiError):
        return ToolProblem("endpoint_preview_failed", str(exc.code), params={"failure_code": exc.code})
    if isinstance(exc, ValidationError):
        return ToolProblem("invalid_request", str(exc.errors(include_url=False, include_input=False)))
    raise exc


async def _run(services: Services, operation: Callable[[AsyncSession], Awaitable[Any]]) -> ToolOutcome[Any]:
    try:
        async with services.sessions() as session:
            return ToolOutcome(value=await operation(session))
    except (
        config.GlobalConfigRefused,
        RevisionConflict,
        ApiError,
        HTTPException,
        ComfyuiError,
        ValidationError,
    ) as exc:
        return ToolOutcome(problem=_problem(exc))
    except Exception as exc:
        return ToolOutcome(problem=_internal_error(exc))


def _internal_error(exc: Exception) -> ToolProblem:
    """Generic problem for unexpected failures; log only the exception type, never its text or parameters."""
    logger.error("Global configuration tool failed: %s", type(exc).__name__)
    return ToolProblem(
        "internal_error",
        "Global configuration operation failed; inspect server diagnostics before retrying",
    )


async def list_global_providers(request: ToolRequest[Any], caller: CallerContext, services: Services) -> ToolOutcome:
    del request, caller
    return await _run(services, config.list_providers)


async def list_global_endpoints(request: ToolRequest[Any], caller: CallerContext, services: Services) -> ToolOutcome:
    del request, caller
    return await _run(services, config.list_endpoints)


async def get_endpoint_definition(request: ToolRequest[Any], caller: CallerContext, services: Services) -> ToolOutcome:
    del caller
    key = request.value.endpoint_key
    return await _run(services, lambda session: config.endpoint_definition(session, services.projects, key))


async def validate_endpoint_definition(
    request: ToolRequest[Any], caller: CallerContext, services: Services
) -> ToolOutcome:
    del caller
    value = request.value
    return await _run(
        services,
        lambda session: config.validate_definition(
            session, value.definition, _t, exclude_key=value.exclude_endpoint_key
        ),
    )


async def preview_endpoint_request(request: ToolRequest[Any], caller: CallerContext, services: Services) -> ToolOutcome:
    del caller, services
    value = request.value
    parameters = EndpointTestParameters(**value.parameters.model_dump())
    try:
        return ToolOutcome(value=config.preview_definition(value.definition, parameters, _t, base_url=value.base_url))
    except (config.GlobalConfigRefused, ApiError, ComfyuiError) as exc:
        return ToolOutcome(problem=_problem(exc))
    except Exception as exc:
        return ToolOutcome(problem=_internal_error(exc))


async def copy_builtin_endpoint(request: ToolRequest[Any], caller: CallerContext, services: Services) -> ToolOutcome:
    del caller
    value = request.value
    identity = caller_identity()
    return await _run(
        services,
        lambda session: config.copy_builtin_endpoint(
            session, value.endpoint_key, _t, allow_duplicate=value.allow_duplicate, identity=identity
        ),
    )


async def update_custom_endpoint(request: ToolRequest[Any], caller: CallerContext, services: Services) -> ToolOutcome:
    del caller
    value = request.value
    identity = caller_identity()
    return await _run(
        services,
        lambda session: config.update_custom_endpoint(
            session,
            services.projects,
            value.endpoint_key,
            value.definition,
            value.expected_revision,
            _t,
            apply=value.apply,
            identity=identity,
        ),
    )


def configure_custom_provider_handler(reload_limits: ReloadLimits):
    async def configure_custom_provider(
        request: ToolRequest[Any], caller: CallerContext, services: Services
    ) -> ToolOutcome:
        del caller
        value = request.value
        identity = caller_identity()
        try:
            models = (
                [ModelInput.model_validate(model.model_dump()) for model in value.models]
                if value.models is not None
                else None
            )
        except ValidationError as exc:
            return ToolOutcome(problem=_problem(exc))
        plan = config.ProviderPlan(
            provider_id=value.provider_id,
            display_name=value.display_name,
            discovery_format=value.discovery_format,
            base_url=value.base_url,
            credential_ref=value.credential_ref,
            models=models,
            expected_revision=value.expected_revision,
            image_max_workers=value.image_max_workers,
            video_max_workers=value.video_max_workers,
            audio_max_workers=value.audio_max_workers,
        )
        return await _run(
            services,
            lambda session: config.configure_custom_provider(
                session,
                services.projects,
                plan,
                _t,
                apply=value.apply,
                reload_limits=reload_limits,
                identity=identity,
            ),
        )

    return configure_custom_provider


__all__ = [
    "caller_identity",
    "configure_custom_provider_handler",
    "copy_builtin_endpoint",
    "get_endpoint_definition",
    "list_global_endpoints",
    "list_global_providers",
    "preview_endpoint_request",
    "update_custom_endpoint",
    "validate_endpoint_definition",
]
