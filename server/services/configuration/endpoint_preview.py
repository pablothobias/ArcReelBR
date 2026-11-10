"""Offline endpoint-definition request preview shared by the Web endpoint-test router and global-configuration MCP tools.

Rendering transmits no bytes and creates no jobs: it is the shared ``validate_definition`` gate followed by the
kind's ``preview`` renderer. Connection tests (trial runs) stay in ``server/routers/endpoint_tests.py``; nothing
here may submit a provider call."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from arcreel_market_core.endpoint_definition import DefinitionDiagnostics, validate_definition
from lib.custom_provider.endpoint_test import (
    EndpointTestAssets,
    EndpointTestCredentials,
    EndpointTestDefinitionError,
    EndpointTestMode,
    EndpointTestParameters,
    KindTestSupport,
    RequestPreview,
    support_for_kind,
    supports_test_mode,
)
from lib.infra.api_errors import BadRequestError, UnprocessableError


def invalid_definition(diagnostics: DefinitionDiagnostics, _t: Callable[..., str]) -> UnprocessableError:
    return UnprocessableError("custom_endpoint_definition_invalid").with_diagnostic(diagnostics.to_payload(_t))


def accepted_test_definition(definition: object, _t: Callable[..., str], *, mode: EndpointTestMode) -> dict[str, Any]:
    """Run shared validation, then check whether definition ``kind`` supports this mode.

    Validation shares saving's decisions/codes, with no additional definition threshold here. An unsupported
    mode for a kind is not an invalid definition; reject separately with 400, outside definition diagnostics."""
    diagnostics = validate_definition(definition)
    if diagnostics.errors or not isinstance(definition, dict):
        raise invalid_definition(diagnostics, _t)
    kind = str(definition["kind"])
    if not supports_test_mode(kind, mode):
        raise BadRequestError("endpoint_test_mode_unsupported_for_kind", kind=kind)
    return definition


def kind_support(definition: Mapping[str, Any]) -> KindTestSupport:
    """Endpoint-test implementation for this definition kind, already admitted by :func:`accepted_test_definition` mode checks."""
    return support_for_kind(str(definition["kind"]))


def preview_definition_request(
    definition: Mapping[str, Any],
    parameters: EndpointTestParameters,
    _t: Callable[..., str],
    *,
    credentials: EndpointTestCredentials | None,
    assets: EndpointTestAssets,
) -> RequestPreview:
    """Render submit/poll/result sections of an accepted definition without sending them.

    Credentials are masked by the renderer. Rendering failures attributable to the definition raise 422 with
    definition diagnostics; ComfyUI construction failures (``ComfyuiError``) propagate for the caller to word."""
    try:
        return kind_support(definition).preview(definition, parameters, credentials=credentials, assets=assets)
    except EndpointTestDefinitionError as exc:
        raise invalid_definition(exc.diagnostics, _t) from exc


__all__ = [
    "accepted_test_definition",
    "invalid_definition",
    "kind_support",
    "preview_definition_request",
]
