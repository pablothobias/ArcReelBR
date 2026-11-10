"""Custom call-endpoint definition service shared by the Web router and global-configuration MCP tools.

Owns import routing, the shared definition gate, duplicate (lineage) detection, attachment-safety checks and
the create/replace transactions. ``server/routers/custom_endpoints.py`` adds HTTP binding; MCP tools add
revision preconditions on top of the same transactions, so validation and cache invalidation cannot diverge."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from arcreel_market_core.endpoint_definition import (
    DefinitionDiagnostics,
    VersionRelation,
    validate_definition,
    version_relation,
)
from lib.custom_provider import make_endpoint_key, make_provider_id
from lib.custom_provider.comfyui.import_shapes import ImportShape, route_import_payload, ui_workflow_refusal
from lib.custom_provider.discovery_formats import endpoint_attachment_holds
from lib.custom_provider.endpoint_resolution import derive_mirror_columns
from lib.db.models.custom_endpoint import CustomEndpoint
from lib.db.repositories.custom_endpoint_repo import CustomEndpointRepository, EndpointReference
from lib.infra.api_errors import ConflictError, NotFoundError, UnprocessableError
from lib.infra.content_digest import prefixed_canonical_json_digest

logger = logging.getLogger(__name__)


class DuplicateDescriptor(BaseModel):
    """Existing endpoint matching the import definition's author/name (``meta.author`` + ``meta.name``)."""

    id: int
    key: str
    display_name: str
    version: str
    # Existing definition age relative to the import file.
    relation: VersionRelation


class EndpointReferenceDescriptor(BaseModel):
    """Model row referencing the endpoint. Return with deletion-denied 409 responses to show users where to detach it."""

    provider_id: int
    provider_display_name: str
    model_id: str
    model_display_name: str


def definition_revision(definition: object) -> str:
    """Content revision of a stored definition: canonical-JSON digest, independent of key order and whitespace.

    Callers replacing a definition pass the revision they read; a different current revision means another
    writer changed it in between."""
    return prefixed_canonical_json_digest(definition)


def routed_import(body: object, media_type: str) -> tuple[ImportShape, Any, DefinitionDiagnostics]:
    """Route by payload shape, returning the definition to validate plus diagnostics.

    UI-format workflows bypass the validator: they lack ``class_type``, so definition-schema validation
    would flood the screen with field errors unrelated to choosing the wrong export menu item.
    One structured refusal instead explains the next action."""
    shape, definition = route_import_payload(body, media_type=media_type)
    if shape is ImportShape.COMFYUI_UI_WORKFLOW:
        return shape, definition, ui_workflow_refusal()
    return shape, definition, validate_definition(definition)


def accepted(definition: object, diagnostics: DefinitionDiagnostics, _t: Callable[..., str]) -> dict[str, Any]:
    """Errors yield 422 + structured diagnostics; only accepted definitions may be persisted.

    Saving and ``validate`` share :func:`validate_definition`, preventing divergent decisions. Eliminating
    “validate accepts, saving rejects” is precisely why the validator is shared. Warnings do not block saving."""
    if diagnostics.errors or not isinstance(definition, dict):
        raise UnprocessableError("custom_endpoint_definition_invalid").with_diagnostic(diagnostics.to_payload(_t))
    return definition


def accepted_definition(body: object, _t: Callable[..., str]) -> dict[str, Any]:
    """Full-replacement entry point: accept endpoint definitions only, without import routing.

    Overwriting an existing endpoint with raw workflow would erase confirmed node bindings too; this must not happen silently."""
    return accepted(body, validate_definition(body), _t)


def lineage(definition: object) -> tuple[str | None, str | None, str | None]:
    """Extract ``(author, name, version)`` from any input shape.

    Database rows are validated, but request bodies may not yet be. Duplicate detection must still work
    on erroneous definitions, or a single name typo would hide the fact that a copy was already imported."""
    if not isinstance(definition, Mapping):
        return None, None, None
    meta = definition.get("meta")
    if not isinstance(meta, Mapping):
        return None, None, None
    author, name, version = meta.get("author"), meta.get("name"), meta.get("version")
    return (
        author if isinstance(author, str) else None,
        name if isinstance(name, str) else None,
        version if isinstance(version, str) else None,
    )


async def duplicates_of(
    repo: CustomEndpointRepository, definition: object, exclude_id: int | None
) -> list[DuplicateDescriptor]:
    """Find existing endpoints by matching ``meta.author + meta.name``.

    Match only these: keys are system-assigned and absent from shared files; display names are not unique.
    Author/name is the only file information identifying the same definition across instances.
    Versions explain relative age only and do not participate in matching."""
    author, name, version = lineage(definition)
    if author is None or name is None:
        return []
    duplicates: list[DuplicateDescriptor] = []
    for row in await repo.list_all():
        if row.id == exclude_id:
            continue
        row_author, row_name, row_version = lineage(row.definition)
        if row_author != author or row_name != name:
            continue
        duplicates.append(
            DuplicateDescriptor(
                id=row.id,
                key=make_endpoint_key(row.id),
                display_name=row.display_name,
                version=row_version or "",
                relation=version_relation(row_version, version),
            )
        )
    return duplicates


def hints_of(definition: object) -> dict[str, Any] | None:
    if not isinstance(definition, Mapping):
        return None
    meta = definition.get("meta")
    if not isinstance(meta, Mapping):
        return None
    hints = meta.get("hints")
    return dict(hints) if isinstance(hints, Mapping) else None


def schema_version_of(definition: object) -> str | None:
    if not isinstance(definition, Mapping):
        return None
    value = definition.get("schema_version")
    return value if isinstance(value, str) else None


def reference_descriptors(references: list[EndpointReference]) -> list[dict[str, Any]]:
    return [EndpointReferenceDescriptor(**ref._asdict()).model_dump() for ref in references]


async def invalidate_backend_cache() -> None:
    """Apply in-place definition updates to new tasks immediately by clearing backend instances cached by provider/model.

    Polling tasks retain construction-time specs; changes affect only new tasks. This accepted behavior
    uses no in-flight version lock."""
    from server.services.tasks.generation_context import invalidate_backend_cache as invalidate

    invalidate()


async def check_kind_change_keeps_attachments(repo: CustomEndpointRepository, endpoint_id: int, new_kind: str) -> None:
    """Changing definition container kind must not break active attachments.

    Endpoint × provider-protocol bidirectional compatibility was previously checked only on provider-side
    writes (``docs/adr/0081``). Full replacement changes ``kind`` in place without changing keys/model-row
    references: ComfyUI can overwrite a declarative endpoint attached to an OpenAI-protocol provider,
    and vice versa, with neither side warning at save. Share the provider-side predicate to reject bad
    attachments on both write paths. Changing model-row attachments first, then replacing the definition,
    remains possible as two separate operations."""
    for attachment in await repo.list_attachments(make_endpoint_key(endpoint_id)):
        if endpoint_attachment_holds(endpoint_kind=new_kind, discovery_format=attachment.discovery_format):
            continue
        raise UnprocessableError(
            "custom_endpoint_kind_conflicts_with_attachment",
            model=attachment.model_id,
            provider=make_provider_id(attachment.provider_id),
        )


async def check_media_type_change_has_no_attachments(
    repo: CustomEndpointRepository, endpoint_id: int, new_media_type: str
) -> None:
    """Changing definition media type must not reclassify attached model rows in place.

    Model rows have no own media type; their endpoint determines it. Replacing an image-producing
    ComfyUI definition with video-producing content reclassifies every attached row as video. Providers
    with one image and one video default then have two video defaults; default lookup finds two rows and
    fails only during generation. Duration-tier normalization also follows media type and becomes misaligned.

    Unlike changing ``kind``, no still-valid case exists: this changes model-row membership, not pairing.
    Detach first, then replace the definition; both separate operations remain possible."""
    attachments = await repo.list_attachments(make_endpoint_key(endpoint_id))
    if attachments:
        raise UnprocessableError(
            "custom_endpoint_media_type_conflicts_with_attachment",
            media_type=new_media_type,
            model=attachments[0].model_id,
            provider=make_provider_id(attachments[0].provider_id),
        )


async def create_custom_endpoint(session: AsyncSession, definition: dict[str, Any]) -> CustomEndpoint:
    """Persist an already-accepted definition as a new ``ce-<id>`` endpoint, commit, and invalidate backend caches."""
    mirror = derive_mirror_columns(definition)
    row = await CustomEndpointRepository(session).create(
        definition=definition,
        kind=mirror.kind,
        schema_version=mirror.schema_version,
        media_type=mirror.media_type,
        display_name=mirror.display_name,
    )
    await session.commit()
    await invalidate_backend_cache()
    await session.refresh(row)
    return row


class RevisionConflict(Exception):
    """The stored definition changed since the caller read ``expected``; nothing was written."""

    def __init__(self, endpoint_id: int, expected: str, current: str) -> None:
        super().__init__(f"custom endpoint {endpoint_id} revision changed")
        self.endpoint_id = endpoint_id
        self.expected = expected
        self.current = current


async def replace_custom_endpoint(
    session: AsyncSession,
    endpoint_id: int,
    definition: dict[str, Any],
    *,
    expected_revision: str | None = None,
) -> CustomEndpoint:
    """Replace an already-accepted definition in place: keep the key and model-row attachments; new tasks use it immediately.

    ``expected_revision`` (from :func:`definition_revision` of the definition the caller read) makes the
    replacement conditional: a mismatch raises :class:`RevisionConflict` before any write. ``None`` keeps the
    unconditional Web behaviour."""
    mirror = derive_mirror_columns(definition)
    repo = CustomEndpointRepository(session)
    current = await repo.get(endpoint_id)
    if current is None:
        raise NotFoundError("custom_endpoint_not_found")
    # Not compare-and-swap: the revision is checked on the row read in this transaction and the replacement is a
    # separate unconditional UPDATE, with no row lock. A concurrent writer committing between the read and this
    # commit (e.g. a Web edit) is overwritten without a conflict. JSON equality is not portable across the supported
    # databases (PostgreSQL ``json`` has no ``=``), so a conditional UPDATE is not a cheap fix; the check catches
    # stale reads, not simultaneous commits.
    if expected_revision is not None:
        current_revision = definition_revision(current.definition)
        if current_revision != expected_revision:
            raise RevisionConflict(endpoint_id, expected_revision, current_revision)
    if mirror.kind != current.kind:
        await check_kind_change_keeps_attachments(repo, endpoint_id, mirror.kind)
    if mirror.media_type != current.media_type:
        await check_media_type_change_has_no_attachments(repo, endpoint_id, mirror.media_type)
    row = await repo.update(
        endpoint_id,
        definition=definition,
        kind=mirror.kind,
        schema_version=mirror.schema_version,
        media_type=mirror.media_type,
        display_name=mirror.display_name,
    )
    if row is None:
        raise NotFoundError("custom_endpoint_not_found")
    await session.commit()
    await invalidate_backend_cache()
    await session.refresh(row)
    return row


async def delete_custom_endpoint(session: AsyncSession, endpoint_id: int) -> None:
    """Delete an endpoint; reject referenced endpoints and return their reference list.

    Do not cascade-delete referencing model rows: they carry manual user configuration (pricing, capability
    overrides), and cascading loses that work. Do not leave dangling references either, delaying failure until generation."""
    repo = CustomEndpointRepository(session)
    row = await repo.get(endpoint_id)
    if row is None:
        raise NotFoundError("custom_endpoint_not_found")
    references = await repo.list_references(make_endpoint_key(endpoint_id))
    if references:
        raise ConflictError("custom_endpoint_referenced_by_models", count=len(references)).with_diagnostic(
            {"references": reference_descriptors(references)}
        )
    await repo.delete(endpoint_id)
    await session.commit()
    await invalidate_backend_cache()


__all__ = [
    "DuplicateDescriptor",
    "EndpointReferenceDescriptor",
    "RevisionConflict",
    "accepted",
    "accepted_definition",
    "check_kind_change_keeps_attachments",
    "check_media_type_change_has_no_attachments",
    "create_custom_endpoint",
    "definition_revision",
    "delete_custom_endpoint",
    "duplicates_of",
    "hints_of",
    "invalidate_backend_cache",
    "lineage",
    "reference_descriptors",
    "replace_custom_endpoint",
    "routed_import",
    "schema_version_of",
]
