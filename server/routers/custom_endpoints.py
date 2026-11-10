"""Custom call-endpoint management API.

CRUD for definitions and confirmation before saving. No envelope: request bodies and exports are the
verbatim definition JSON. Import uses ``POST``; export uses ``GET`` followed by client-side saving.
There are no separate import/export endpoints or outer envelopes.

``POST /validate`` is one-step, server-stateless confirmation: share the saving validator and additionally
return existing endpoints with matching author/name, echoed hints, and version levels, letting clients
choose a new copy, overwrite, or cancellation before creation.

Both import entry points (``validate`` and create) route by payload shape: ``kind`` means an endpoint
definition; otherwise accept as ComfyUI workflow. Users most commonly have workflows exported by
ComfyUI itself, not endpoint definitions."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from arcreel_market_core.endpoint_definition import (
    SchemaVersionLevel,
    current_schema_version,
    meets_min_app_version,
    parse_semver,
    schema_version_level,
)
from lib.custom_provider import make_endpoint_key
from lib.custom_provider.comfyui.import_shapes import ImportShape
from lib.db import get_async_session
from lib.db.base import dt_to_iso
from lib.db.models.custom_endpoint import CustomEndpoint
from lib.db.repositories.custom_endpoint_repo import CustomEndpointRepository
from lib.infra.api_errors import NotFoundError
from server.i18n import Translator
from server.routers import comfyui_inference, endpoint_tests
from server.routers._market_installations import (
    EndpointInstallationResponse,
    endpoint_installation,
    endpoint_installations,
)
from server.routers.system_config import get_app_version_reader
from server.services.configuration.endpoint_definitions import (
    DuplicateDescriptor,
    accepted,
    accepted_definition,
    create_custom_endpoint,
    delete_custom_endpoint,
    duplicates_of,
    hints_of,
    replace_custom_endpoint,
    routed_import,
    schema_version_of,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custom-endpoints", tags=["Custom Endpoints"])

# Register endpoint-test and node-binding-inference routes before this module's ``/{endpoint_id}``: FastAPI matches registration order;
# failed path-parameter parsing does not fall through. ``/custom-endpoints/trial-runs`` matching ``endpoint_id: int`` yields
# 422 directly.
router.include_router(endpoint_tests.router)
router.include_router(comfyui_inference.router)

#: Body is verbatim definition JSON. Deliberately avoid ``dict``: nonobjects (arrays, bare strings) must pass through shared validation
#: for field-located diagnostics instead of FastAPI's own 422 shape.
DefinitionBody = Annotated[Any, Body()]

#: For pasted raw workflows, importers specify image or video output; workflows themselves do not declare this.
ImportMediaType = Literal["image", "video"]


# ---------------------------------------------------------------------------
# Pydantic models.
# ---------------------------------------------------------------------------


class CustomEndpointResponse(BaseModel):
    """One custom call endpoint. ``definition`` is its export content; clients save it directly as a file."""

    id: int
    key: str  # ce-<id>, system-assigned and opaque.
    display_name: str
    kind: str
    schema_version: str
    media_type: str
    definition: dict[str, Any]
    created_at: str | None = None
    updated_at: str | None = None
    installation: EndpointInstallationResponse | None = None


class CustomEndpointListResponse(BaseModel):
    endpoints: list[CustomEndpointResponse]


class SchemaVersionInfo(BaseModel):
    """File/current-version comparison. ``level`` is only a hint; the schema validator remains the gate."""

    file: str | None
    current: str
    level: SchemaVersionLevel


class MinAppVersionInfo(BaseModel):
    """Compare ``meta.min_app_version`` with current application version. Noncompliance is advisory, not an import blocker."""

    required: str
    current: str
    satisfied: bool


class ValidateResponse(BaseModel):
    errors: list[dict[str, str]]
    warnings: list[dict[str, str]]
    duplicates: list[DuplicateDescriptor]
    # Echo meta.hints verbatim (base_url and suggested model); display only, without bundled provider creation.
    hints: dict[str, Any] | None = None
    schema_version: SchemaVersionInfo
    # null if undeclared/non-semver, or application version cannot be read.
    min_app_version: MinAppVersionInfo | None = None
    # Accepted payload shape: endpoint definition, ComfyUI API workflow, or unsubmittable UI format.
    import_shape: ImportShape
    # Wrapped raw API workflow; null for the other two shapes, where clients retain their own content.
    wrapped_definition: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def endpoint_response(
    row: CustomEndpoint, installation: EndpointInstallationResponse | None = None
) -> CustomEndpointResponse:
    return CustomEndpointResponse(
        installation=installation,
        id=row.id,
        key=make_endpoint_key(row.id),
        display_name=row.display_name,
        kind=row.kind,
        schema_version=row.schema_version,
        media_type=row.media_type,
        definition=row.definition,
        created_at=dt_to_iso(row.created_at),
        updated_at=dt_to_iso(row.updated_at),
    )


def _min_app_version_of(definition: object, read_app_version: Callable[[], str]) -> MinAppVersionInfo | None:
    if not isinstance(definition, Mapping):
        return None
    meta = definition.get("meta")
    required = meta.get("min_app_version") if isinstance(meta, Mapping) else None
    if not isinstance(required, str) or parse_semver(required) is None:
        return None
    try:
        current = read_app_version()
    except Exception:
        logger.exception("Failed to read app version")
        return None
    return MinAppVersionInfo(required=required, current=current, satisfied=meets_min_app_version(required, current))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_endpoint(
    body: DefinitionBody,
    _t: Translator,
    media_type: ImportMediaType = "video",
    session: AsyncSession = Depends(get_async_session),
) -> CustomEndpointResponse:
    """Create (import) a custom call endpoint. The body is verbatim definition JSON; keys are system-assigned.

    Bodies may also be raw ComfyUI API workflows; the server wraps them as ComfyUI endpoint definitions
    using ``media_type``. Wrapped node bindings are empty, so required prompt/output binding checks reject them."""
    _, routed, diagnostics = routed_import(body, media_type)
    row = await create_custom_endpoint(session, accepted(routed, diagnostics, _t))
    return endpoint_response(row, await endpoint_installation(session, row.id))


@router.get("")
async def list_endpoints(session: AsyncSession = Depends(get_async_session)) -> CustomEndpointListResponse:
    """List all custom call endpoints, including full definitions."""
    rows = await CustomEndpointRepository(session).list_all()
    installations = await endpoint_installations(session)
    return CustomEndpointListResponse(endpoints=[endpoint_response(row, installations.get(row.id)) for row in rows])


@router.post("/validate")
async def validate_endpoint_definition(
    body: DefinitionBody,
    _t: Translator,
    read_app_version: Annotated[Callable[[], str], Depends(get_app_version_reader)],
    exclude_id: int | None = None,
    media_type: ImportMediaType = "video",
    session: AsyncSession = Depends(get_async_session),
) -> ValidateResponse:
    """One-step presave confirmation: shape routing + validation diagnostics + matching author/name endpoints + echoed hints + version levels + minimum app version. The server retains no state.

    ``exclude_id`` excludes the edited endpoint itself; otherwise it always reports itself as a duplicate.
    For raw API workflow payloads, compute every returned item from the wrapped result, which the client then takes forward."""
    shape, definition, diagnostics = routed_import(body, media_type)
    payload = diagnostics.to_payload(_t)
    file_version = schema_version_of(definition)
    current_version = current_schema_version(definition)
    return ValidateResponse(
        errors=payload["errors"],
        warnings=payload["warnings"],
        duplicates=await duplicates_of(CustomEndpointRepository(session), definition, exclude_id),
        hints=hints_of(definition),
        schema_version=SchemaVersionInfo(
            file=file_version,
            current=current_version,
            level=schema_version_level(file_version, current_version),
        ),
        min_app_version=_min_app_version_of(definition, read_app_version),
        import_shape=shape,
        wrapped_definition=definition if shape is ImportShape.COMFYUI_API_WORKFLOW else None,
    )


@router.get("/{endpoint_id}")
async def get_endpoint(
    endpoint_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> CustomEndpointResponse:
    """Read one endpoint. Export means saving this response's ``definition`` to a file; the server does not handle downloads."""
    row = await CustomEndpointRepository(session).get(endpoint_id)
    if row is None:
        raise NotFoundError("custom_endpoint_not_found")
    return endpoint_response(row, await endpoint_installation(session, row.id))


@router.put("/{endpoint_id}")
async def update_endpoint(
    endpoint_id: int,
    body: DefinitionBody,
    _t: Translator,
    session: AsyncSession = Depends(get_async_session),
) -> CustomEndpointResponse:
    """Replace the entire definition in place: retain its key and model-row attachments; new tasks use the new definition immediately."""
    row = await replace_custom_endpoint(session, endpoint_id, accepted_definition(body, _t))
    return endpoint_response(row, await endpoint_installation(session, row.id))


@router.delete("/{endpoint_id}", status_code=204)
async def delete_endpoint(
    endpoint_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete an endpoint; reject referenced endpoints and return their reference list.

    Do not cascade-delete referencing model rows: they carry manual user configuration (pricing, capability
    overrides), and cascading loses that work. Do not leave dangling references either, delaying failure until generation."""
    await delete_custom_endpoint(session, endpoint_id)
