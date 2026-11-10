"""Global endpoint/provider configuration operations for external tools.

Composes the shared endpoint-definition and custom-provider services with the guarantees an external
configuration surface needs on top of the Web transactions:

- Sanitized readback: no credential value (not even a masked fragment) leaves this module; credentials are
  identified only by an opaque server-side reference (the owning provider id).
- Credential reuse by reference: a new or updated custom provider may reuse an existing credential only when the
  destination origin (scheme, host, port) equals the credential's original origin. A different host is refused,
  never implicit.
- Revisions and impact: replacements require the revision the caller read, and every write path can first be run
  with ``apply=False`` to reveal model rows, projects and global defaults that reference the target.
- Audit: each applied change logs the caller identity and the changed field names, never values.

Nothing here performs connection tests, provider calls or generation; previews render offline."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from arcreel_market_core.endpoint_definition import url_authority_is_fixed
from lib.catalog.builtin_models import BuiltinModelError, list_builtin_models
from lib.config.model_setting_keys import GLOBAL_MODEL_SETTING_KEYS, PROJECT_MODEL_SETTING_KEYS
from lib.config.registry import PROVIDER_REGISTRY
from lib.custom_provider import (
    is_custom_endpoint,
    is_custom_provider,
    make_endpoint_key,
    make_provider_id,
    parse_endpoint_key,
    parse_provider_id,
)
from lib.custom_provider.credential_origin import origin_text
from lib.custom_provider.declarative_backend import apply_path_overrides
from lib.custom_provider.endpoint_resolution import resolve_endpoint_spec
from lib.custom_provider.endpoint_test import (
    EndpointTestAssets,
    EndpointTestCredentials,
    EndpointTestMode,
    EndpointTestParameters,
)
from lib.custom_provider.endpoints import ENDPOINT_REGISTRY, endpoint_spec_to_dict
from lib.custom_provider.path_overrides import effective_path_overrides
from lib.db.models.custom_provider import CustomProvider
from lib.db.repositories.credential_repository import CredentialRepository
from lib.db.repositories.custom_endpoint_repo import CustomEndpointRepository
from lib.db.repositories.custom_provider_repo import CustomProviderRepository
from lib.infra.api_errors import NotFoundError
from lib.infra.content_digest import prefixed_canonical_json_digest
from lib.project.project_manager import ProjectManager
from server.services.configuration import endpoint_definitions as endpoints
from server.services.configuration.custom_providers import (
    CreateProviderRequest,
    FullUpdateProviderRequest,
    ModelInput,
    ReloadLimits,
    create_custom_provider,
    endpoint_catalog_specs,
    provider_response,
    replace_custom_provider,
    validate_provider_models,
)
from server.services.configuration.endpoint_preview import (
    accepted_test_definition,
    kind_support,
    preview_definition_request,
)

logger = logging.getLogger(__name__)

#: Dedicated audit channel: identity, operation, target and changed field names; never values.
audit_logger = logging.getLogger("arcreel.audit.global_config")

#: Placeholder rendered in previews where the credential would go. Fully opaque, unlike the Web preview's last-four mask.
PREVIEW_CREDENTIAL_MASK = "****"

type Translate = Callable[..., str]


# ---------------------------------------------------------------------------
# Errors with stable codes (mapped to tool problems by the MCP handlers).
# ---------------------------------------------------------------------------


class GlobalConfigRefused(Exception):
    """A configuration request refused before any write. ``code`` is stable; ``params`` carry no secret."""

    def __init__(self, code: str, detail: str, *, action: str | None = None, **params: object) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.action = action
        self.params = params


# ---------------------------------------------------------------------------
# Origins and credential references.
# ---------------------------------------------------------------------------

#: Normalized ``scheme://host:port`` of a URL, or ``None`` when it has no http(s) scheme/host or when the URL
#: parser and the HTTP client disagree on its origin (single shared implementation, also used at send time).
origin_of = origin_text


@dataclass(frozen=True, slots=True)
class ReusableCredential:
    """An existing API key resolved from an opaque reference. ``api_key`` never leaves the server."""

    ref: str
    origin: str
    api_key: str = field(repr=False)


async def resolve_credential_ref(session: AsyncSession, ref: str) -> ReusableCredential:
    """Resolve ``ref`` (a built-in provider id for its active credential, or a ``custom-<id>`` provider id).

    Only single-API-key credentials with a known original origin are reusable."""
    ref = ref.strip()
    if is_custom_provider(ref):
        try:
            row_id = parse_provider_id(ref)
        except ValueError:
            row_id = None
        provider = await CustomProviderRepository(session).get_provider(row_id) if row_id is not None else None
        if provider is None:
            raise GlobalConfigRefused("credential_ref_unknown", f"Unknown credential reference {ref!r}")
        origin = origin_of(provider.base_url)
        if not provider.api_key or origin is None:
            raise GlobalConfigRefused("credential_ref_unusable", f"Credential {ref!r} has no reusable API key/origin")
        return ReusableCredential(ref=ref, origin=origin, api_key=provider.api_key)
    meta = PROVIDER_REGISTRY.get(ref)
    if meta is None:
        raise GlobalConfigRefused("credential_ref_unknown", f"Unknown credential reference {ref!r}")
    if "api_key" not in meta.secret_keys:
        raise GlobalConfigRefused("credential_ref_unusable", f"Credential {ref!r} is not a single API key")
    credential = await CredentialRepository(session).get_active(ref)
    origin = origin_of((credential.base_url if credential else None) or meta.default_base_url)
    if credential is None or not credential.api_key or origin is None:
        raise GlobalConfigRefused("credential_ref_unusable", f"Credential {ref!r} has no active API key/origin")
    return ReusableCredential(ref=ref, origin=origin, api_key=credential.api_key)


def ensure_same_origin(credential_origin: str, destination_base_url: str, *, ref: str) -> None:
    """Refuse sending an existing credential to an origin other than the one it was configured for."""
    destination = origin_of(destination_base_url)
    if destination is None:
        raise GlobalConfigRefused(
            "base_url_invalid", "Destination base_url must be an absolute http(s) URL with a host"
        )
    if destination != credential_origin:
        raise GlobalConfigRefused(
            "credential_host_mismatch",
            "The referenced credential belongs to a different host; reuse across hosts is refused",
            action="Use a destination on the credential's original host, or have the operator configure a credential for the new host in Settings",
            credential_ref=ref,
            credential_origin=credential_origin,
            destination_origin=destination,
        )


@dataclass(frozen=True, slots=True)
class BoundModel:
    """A model row (planned or stored) whose endpoint requests would carry the provider credential."""

    model_id: str
    endpoint: str
    path_overrides: Mapping[str, str] | None = None


#: Request sections whose rendered URL receives the provider credential.
_CREDENTIALED_SECTIONS = ("submit", "poll", "result")
#: Adversarial values for caller-controlled variables: each tries to move the authority off the configured host
#: when a URL interpolates it unescaped (userinfo, host suffix, port, backslash-userinfo, fragment cut).
_HOSTILE_VALUES = ("@x.invalid/#", ".x.invalid", ":1", "\\@x.invalid/", "/../@x.invalid")


async def ensure_endpoint_requests_stay_on_origin(
    session: AsyncSession,
    bound: list[BoundModel],
    *,
    base_url: str,
    credential_origin: str,
    ref: str,
    replaced_definitions: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    """Refuse when any request a bound endpoint would send with the credential could leave ``credential_origin``.

    Declarative definitions may use absolute URLs, and URL placeholders render unescaped, so the runtime sends auth
    headers/queries to whatever submit/poll/result render to. Three checks, all against the effective definition
    (path overrides applied, ``replaced_definitions`` taking precedence over stored definitions):

    1. Structure: only the base URL may supply the scheme/authority (the shared
       :func:`arcreel_market_core.endpoint_definition.url_authority_is_fixed`).
    2. Benign render: the offline preview renderer, against ``base_url``, must land on ``credential_origin``.
    3. Hostile render: the same with adversarial prompt/model values must still land there.

    This is configuration-time policy; a send-time origin check in the declarative backends is the stronger guard."""
    repo = CustomEndpointRepository(session)
    credentials = EndpointTestCredentials(base_url=base_url, api_key=PREVIEW_CREDENTIAL_MASK)
    for model in bound:
        try:
            spec = await resolve_endpoint_spec(model.endpoint, repo.get)
        except ValueError:
            continue  # Unknown endpoints are refused by model validation itself.
        definition = (replaced_definitions or {}).get(model.endpoint, spec.definition)
        if definition is None:
            continue  # Python built-in endpoints address the configured base_url only.
        overrides = effective_path_overrides(model.path_overrides, spec.requests)

        def refuse(
            code: str, request: str, destination: str | None = None, model: BoundModel = model
        ) -> GlobalConfigRefused:
            return GlobalConfigRefused(
                code,
                "An endpoint bound to this provider could send the credential to a different host than the "
                "credential's; reuse across hosts is refused",
                action="Use only endpoints whose request URLs take their host from {{ base_url }} or a fixed "
                "literal on the credential's host, with placeholders only after the first '/', '?' or '#'",
                credential_ref=ref,
                credential_origin=credential_origin,
                destination_origin=destination,
                endpoint=model.endpoint,
                model_id=model.model_id,
                request=request,
            )

        effective = apply_path_overrides(definition, overrides)
        for section_name in _CREDENTIALED_SECTIONS:
            node = effective.get(section_name)
            url = node.get("url") if isinstance(node, Mapping) else None
            if url is not None and not (isinstance(url, str) and url_authority_is_fixed(url)):
                raise refuse("credential_host_unverifiable", section_name)

        renders = [EndpointTestParameters(model=model.model_id, prompt="")]
        renders += [EndpointTestParameters(model=value, prompt=value) for value in _HOSTILE_VALUES]
        for parameters in renders:
            try:
                preview = kind_support(definition).preview(
                    definition,
                    parameters,
                    credentials=credentials,
                    assets=EndpointTestAssets(),
                    path_overrides=overrides,
                )
            except Exception as exc:
                raise GlobalConfigRefused(
                    "credential_host_unverifiable",
                    "Could not render the endpoint's request URLs to verify where the credential would be sent",
                    endpoint=model.endpoint,
                    model_id=model.model_id,
                ) from exc
            for section_name in _CREDENTIALED_SECTIONS:
                section = getattr(preview, section_name)
                if section is None:
                    continue
                destination = origin_text(section.url)
                if destination != credential_origin:
                    raise refuse("credential_host_mismatch", section_name, destination)


def _bound(models: list[ModelInput] | list[Any]) -> list[BoundModel]:
    return [BoundModel(m.model_id, m.endpoint, m.path_overrides) for m in models]


# ---------------------------------------------------------------------------
# Impact.
# ---------------------------------------------------------------------------


def _project_references(projects: ProjectManager, refs: frozenset[str]) -> list[dict[str, Any]]:
    """Projects whose model settings or ``model_settings`` keys name any ``provider/model`` in ``refs`` (synchronous file reads)."""
    found: list[dict[str, Any]] = []
    for name in projects.list_projects():
        try:
            project = projects.load_project(name)
        except (OSError, ValueError):
            continue
        keys = [key for key in PROJECT_MODEL_SETTING_KEYS if project.get(key) in refs]
        model_settings = project.get("model_settings")
        if isinstance(model_settings, Mapping):
            keys.extend(f"model_settings.{ref}" for ref in model_settings if ref in refs)
        if keys:
            found.append({"project": name, "keys": keys})
    return found


async def _global_references(session: AsyncSession, refs: frozenset[str]) -> list[str]:
    from lib.config.service import ConfigService

    service = ConfigService(session)
    return [key for key in GLOBAL_MODEL_SETTING_KEYS if await service.get_setting(key, "") in refs]


async def provider_impact(
    session: AsyncSession, projects: ProjectManager, provider_id: int, model_ids: list[str]
) -> dict[str, Any]:
    refs = frozenset(f"{make_provider_id(provider_id)}/{model_id}" for model_id in model_ids)
    return {
        "projects": await asyncio.to_thread(_project_references, projects, refs),
        "global_settings": await _global_references(session, refs),
    }


async def endpoint_impact(session: AsyncSession, projects: ProjectManager, endpoint_id: int) -> dict[str, Any]:
    references = await CustomEndpointRepository(session).list_references(make_endpoint_key(endpoint_id))
    refs = frozenset(f"{make_provider_id(ref.provider_id)}/{ref.model_id}" for ref in references)
    return {
        "model_rows": [
            {"provider_id": make_provider_id(ref.provider_id), "model_id": ref.model_id} for ref in references
        ],
        "projects": await asyncio.to_thread(_project_references, projects, refs),
        "global_settings": await _global_references(session, refs),
    }


# ---------------------------------------------------------------------------
# Audit.
# ---------------------------------------------------------------------------


def changed_paths(before: object, after: object, prefix: str = "", *, limit: int = 64) -> list[str]:
    """Dotted paths whose values differ (names only), capped at ``limit``."""
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        paths: list[str] = []
        for key in sorted(set(before) | set(after), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                paths.append(path)
            else:
                paths.extend(changed_paths(before[key], after[key], path, limit=limit))
            if len(paths) >= limit:
                return paths[:limit]
        return paths
    return [] if before == after else [prefix or "<root>"]


def audit(identity: str | None, operation: str, target: str, fields: list[str]) -> None:
    audit_logger.info(
        "global configuration change: identity=%s operation=%s target=%s fields=%s",
        identity or "unknown",
        operation,
        target,
        ",".join(fields),
        extra={"identity": identity, "operation": operation, "target": target, "changed_fields": fields},
    )


# ---------------------------------------------------------------------------
# Sanitized readback.
# ---------------------------------------------------------------------------


def provider_revision(sanitized: Mapping[str, Any], updated_at: object) -> str:
    return prefixed_canonical_json_digest({"config": sanitized, "updated_at": str(updated_at)})


async def sanitized_custom_provider(session: AsyncSession, provider: CustomProvider) -> dict[str, Any]:
    payload = (await provider_response(session, provider)).model_dump(mode="json")
    payload.pop("api_key_masked", None)
    payload.pop("created_at", None)
    sanitized = {
        "provider_id": make_provider_id(provider.id),
        **payload,
        "credential": {
            "ref": make_provider_id(provider.id),
            "configured": bool(provider.api_key),
            "origin": origin_of(provider.base_url),
        },
    }
    sanitized["revision"] = provider_revision(sanitized, provider.updated_at)
    return sanitized


async def list_providers(session: AsyncSession) -> dict[str, Any]:
    """Built-in providers (credential status by reference, catalog models) and custom providers (sanitized)."""
    credentials = await CredentialRepository(session).get_active_credentials_bulk()
    builtin: list[dict[str, Any]] = []
    for provider_id, meta in PROVIDER_REGISTRY.items():
        credential = credentials.get(provider_id)
        try:
            models = [
                {
                    "model_id": item.view.model_id,
                    "media_type": item.view.model.media_type,
                    "enabled": item.enabled,
                    "default": item.is_default,
                }
                for item in await list_builtin_models(session, provider_id)
            ]
        except BuiltinModelError:
            models = []
        origin = origin_of((credential.base_url if credential else None) or meta.default_base_url)
        builtin.append(
            {
                "provider_id": provider_id,
                "display_name": meta.display_name,
                "credential": {
                    "ref": provider_id,
                    "configured": credential is not None,
                    "origin": origin,
                    "reusable": bool(
                        credential is not None
                        and credential.api_key
                        and "api_key" in meta.secret_keys
                        and origin is not None
                    ),
                },
                "models": models,
            }
        )
    custom_rows = await CustomProviderRepository(session).list_providers()
    custom = [await sanitized_custom_provider(session, row) for row in custom_rows]
    return {"builtin": builtin, "custom": custom}


async def list_endpoints(session: AsyncSession) -> list[dict[str, Any]]:
    """Endpoint catalog (built-in + custom) with definition availability and custom revisions."""
    rows = {make_endpoint_key(row.id): row for row in await CustomEndpointRepository(session).list_all()}
    result: list[dict[str, Any]] = []
    for spec in await endpoint_catalog_specs(session):
        descriptor = endpoint_spec_to_dict(spec)
        row = rows.get(spec.key)
        result.append(
            {
                "key": spec.key,
                "source": descriptor.get("source", "builtin"),
                "kind": spec.kind,
                "media_type": spec.media_type,
                "display_name": descriptor.get("display_name"),
                "display_name_key": descriptor.get("display_name_key"),
                "has_definition": spec.definition is not None,
                "revision": endpoints.definition_revision(row.definition) if row is not None else None,
            }
        )
    return result


async def endpoint_definition(session: AsyncSession, projects: ProjectManager, key: str) -> dict[str, Any]:
    """One endpoint's definition (definitions contain templates, never credential values)."""
    if is_custom_endpoint(key):
        row = await CustomEndpointRepository(session).get(parse_endpoint_key(key))
        if row is None:
            raise NotFoundError("custom_endpoint_not_found")
        return {
            "key": key,
            "source": "custom",
            "definition": row.definition,
            "revision": endpoints.definition_revision(row.definition),
            "impact": await endpoint_impact(session, projects, row.id),
        }
    spec = ENDPOINT_REGISTRY.get(key)
    if spec is None or spec.definition is None:
        raise GlobalConfigRefused(
            "endpoint_definition_not_found", f"Endpoint {key!r} has no declarative definition", endpoint=key
        )
    return {"key": key, "source": "builtin", "definition": dict(spec.definition), "revision": None, "impact": None}


# ---------------------------------------------------------------------------
# Offline validation and preview.
# ---------------------------------------------------------------------------


async def validate_definition(
    session: AsyncSession, definition: object, _t: Translate, *, exclude_key: str | None = None
) -> dict[str, Any]:
    """Shared validator diagnostics plus author/name duplicates; no writes, no network."""
    from arcreel_market_core.endpoint_definition import validate_definition as validate

    diagnostics = validate(definition).to_payload(_t)
    exclude_id = parse_endpoint_key(exclude_key) if exclude_key and is_custom_endpoint(exclude_key) else None
    duplicates = await endpoints.duplicates_of(CustomEndpointRepository(session), definition, exclude_id)
    return {
        "valid": not diagnostics["errors"] and isinstance(definition, dict),
        "errors": diagnostics["errors"],
        "warnings": diagnostics["warnings"],
        "duplicates": [duplicate.model_dump(mode="json") for duplicate in duplicates],
        "hints": endpoints.hints_of(definition),
    }


def preview_definition(
    definition: object,
    parameters: EndpointTestParameters,
    _t: Translate,
    *,
    base_url: str | None,
) -> dict[str, Any]:
    """Render the would-be request offline. The credential is always the opaque mask; no bytes are sent."""
    accepted = accepted_test_definition(definition, _t, mode=EndpointTestMode.PREVIEW_REQUEST)
    credentials = (
        EndpointTestCredentials(base_url=base_url, api_key=PREVIEW_CREDENTIAL_MASK) if base_url is not None else None
    )
    preview = preview_definition_request(accepted, parameters, _t, credentials=credentials, assets=EndpointTestAssets())

    def section(value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return {"method": value.method, "url": value.url, "headers": value.headers, "body": value.body}

    return {
        "submit": section(preview.submit),
        "poll": section(preview.poll),
        "result": section(preview.result),
        "conversions": dict(preview.conversions) if preview.conversions is not None else None,
    }


# ---------------------------------------------------------------------------
# Endpoint writes.
# ---------------------------------------------------------------------------


async def copy_builtin_endpoint(
    session: AsyncSession, key: str, _t: Translate, *, allow_duplicate: bool, identity: str | None
) -> dict[str, Any]:
    spec = ENDPOINT_REGISTRY.get(key)
    if spec is None or spec.definition is None:
        raise GlobalConfigRefused(
            "endpoint_definition_not_found", f"Built-in endpoint {key!r} has no declarative definition", endpoint=key
        )
    definition = dict(spec.definition)
    duplicates = await endpoints.duplicates_of(CustomEndpointRepository(session), definition, None)
    if duplicates and not allow_duplicate:
        raise GlobalConfigRefused(
            "endpoint_duplicate_exists",
            "A custom endpoint with the same meta.author/meta.name already exists",
            action="Update the existing endpoint with update_custom_endpoint, or pass allow_duplicate=true to create another copy",
            duplicates=[duplicate.model_dump(mode="json") for duplicate in duplicates],
        )
    row = await endpoints.create_custom_endpoint(session, endpoints.accepted_definition(definition, _t))
    new_key = make_endpoint_key(row.id)
    audit(identity, "copy_builtin_endpoint", new_key, [f"copied_from:{key}"])
    return {
        "key": new_key,
        "copied_from": key,
        "revision": endpoints.definition_revision(row.definition),
        "definition": row.definition,
        "duplicates": [duplicate.model_dump(mode="json") for duplicate in duplicates],
    }


async def update_custom_endpoint(
    session: AsyncSession,
    projects: ProjectManager,
    key: str,
    definition: object,
    expected_revision: str,
    _t: Translate,
    *,
    apply: bool,
    identity: str | None,
) -> dict[str, Any]:
    """Replace a custom endpoint definition conditionally on ``expected_revision``; ``apply=False`` only reports."""
    if not is_custom_endpoint(key):
        raise GlobalConfigRefused(
            "endpoint_not_custom",
            f"{key!r} is not a custom endpoint; copy a built-in endpoint first",
            action="Call copy_builtin_endpoint, then update the returned ce-<id> key",
        )
    endpoint_id = parse_endpoint_key(key)
    row = await CustomEndpointRepository(session).get(endpoint_id)
    if row is None:
        raise NotFoundError("custom_endpoint_not_found")
    current_revision = endpoints.definition_revision(row.definition)
    if current_revision != expected_revision:
        raise endpoints.RevisionConflict(endpoint_id, expected_revision, current_revision)
    accepted = endpoints.accepted_definition(definition, _t)
    fields = changed_paths(row.definition, accepted)
    impact = await endpoint_impact(session, projects, endpoint_id)
    duplicates = await endpoints.duplicates_of(CustomEndpointRepository(session), accepted, endpoint_id)
    await _ensure_attached_providers_stay_on_origin(session, key, accepted)
    report: dict[str, Any] = {
        "key": key,
        "applied": False,
        "current_revision": current_revision,
        "changed_fields": fields,
        "impact": impact,
        "duplicates": [duplicate.model_dump(mode="json") for duplicate in duplicates],
    }
    if not apply or not fields:
        return report
    updated = await endpoints.replace_custom_endpoint(
        session, endpoint_id, accepted, expected_revision=expected_revision
    )
    audit(identity, "update_custom_endpoint", key, fields)
    return {**report, "applied": True, "revision": endpoints.definition_revision(updated.definition)}


async def _ensure_attached_providers_stay_on_origin(
    session: AsyncSession, key: str, definition: Mapping[str, Any]
) -> None:
    """A replacement definition must keep every attached provider's credential on that provider's own origin."""
    references = await CustomEndpointRepository(session).list_references(key)
    repo = CustomProviderRepository(session)
    for provider_row_id in sorted({ref.provider_id for ref in references}):
        provider = await repo.get_provider(provider_row_id)
        if provider is None or not provider.api_key:
            continue
        provider_ref = make_provider_id(provider.id)
        origin = origin_of(provider.base_url)
        if origin is None:
            raise GlobalConfigRefused(
                "credential_host_unverifiable",
                "An attached provider has no determinable origin; its credential destination cannot be verified",
                provider_id=provider_ref,
            )
        attached = [m for m in await repo.list_models(provider.id) if m.endpoint == key]
        await ensure_endpoint_requests_stay_on_origin(
            session,
            _bound(attached),
            base_url=provider.base_url,
            credential_origin=origin,
            ref=provider_ref,
            replaced_definitions={key: definition},
        )


# ---------------------------------------------------------------------------
# Provider writes.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderPlan:
    """Normalized external provider configuration request (no secret values)."""

    provider_id: str | None
    display_name: str
    discovery_format: Literal["openai", "google", "comfyui"] | None
    base_url: str
    credential_ref: str | None
    models: list[ModelInput] | None
    expected_revision: str | None
    image_max_workers: int | None = None
    video_max_workers: int | None = None
    audio_max_workers: int | None = None


async def configure_custom_provider(
    session: AsyncSession,
    projects: ProjectManager,
    plan: ProviderPlan,
    _t: Translate,
    *,
    apply: bool,
    reload_limits: ReloadLimits,
    identity: str | None,
) -> dict[str, Any]:
    """Create (``provider_id`` None) or update a custom provider; credentials only by reference with same-origin reuse.

    Writes need ``reload_limits`` (the running worker's limit refresh): without it the applied change would leave
    generation concurrency limits stale, so ``apply=True`` is refused before any write."""
    if apply and reload_limits is None:
        raise GlobalConfigRefused(
            "reload_limits_unavailable",
            "This server was assembled without a generation-worker limit refresh; provider writes are refused",
            action="Restart the server through the normal application lifespan, or configure the provider in Settings",
        )
    if plan.provider_id is None:
        return await _create_provider(session, plan, _t, apply=apply, reload_limits=reload_limits, identity=identity)
    return await _update_provider(
        session, projects, plan, _t, apply=apply, reload_limits=reload_limits, identity=identity
    )


async def _create_provider(
    session: AsyncSession,
    plan: ProviderPlan,
    _t: Translate,
    *,
    apply: bool,
    reload_limits: ReloadLimits,
    identity: str | None,
) -> dict[str, Any]:
    if plan.credential_ref is None:
        raise GlobalConfigRefused(
            "credential_ref_required",
            "A new provider needs credential_ref naming an existing credential; raw keys are not accepted here",
        )
    if plan.discovery_format is None:
        raise GlobalConfigRefused("discovery_format_required", "A new provider needs discovery_format")
    credential = await resolve_credential_ref(session, plan.credential_ref)
    ensure_same_origin(credential.origin, plan.base_url, ref=credential.ref)
    models = list(plan.models or [])
    if models:
        await validate_provider_models(session, models, plan.discovery_format, _t)
    await ensure_endpoint_requests_stay_on_origin(
        session, _bound(models), base_url=plan.base_url, credential_origin=credential.origin, ref=credential.ref
    )
    fields = ["display_name", "discovery_format", "base_url", "credential", *(["models"] if models else [])]
    report: dict[str, Any] = {
        "applied": False,
        "operation": "create",
        "credential_ref": credential.ref,
        "changed_fields": fields,
        "impact": {"projects": [], "global_settings": []},
    }
    if not apply:
        return report
    created = await create_custom_provider(
        session,
        CreateProviderRequest(
            display_name=plan.display_name,
            discovery_format=plan.discovery_format,
            base_url=plan.base_url,
            api_key=credential.api_key,
            models=models,
            image_max_workers=plan.image_max_workers,
            video_max_workers=plan.video_max_workers,
            audio_max_workers=plan.audio_max_workers,
        ),
        _t,
        reload_limits=reload_limits,
    )
    row = await CustomProviderRepository(session).get_provider(created.id)
    assert row is not None
    target = make_provider_id(created.id)
    audit(identity, "create_custom_provider", target, fields)
    return {**report, "applied": True, "provider": await sanitized_custom_provider(session, row)}


async def _update_provider(
    session: AsyncSession,
    projects: ProjectManager,
    plan: ProviderPlan,
    _t: Translate,
    *,
    apply: bool,
    reload_limits: ReloadLimits,
    identity: str | None,
) -> dict[str, Any]:
    assert plan.provider_id is not None
    if not is_custom_provider(plan.provider_id):
        raise GlobalConfigRefused("provider_not_custom", f"{plan.provider_id!r} is not a custom provider")
    repo = CustomProviderRepository(session)
    try:
        row_id = parse_provider_id(plan.provider_id)
    except ValueError as exc:
        raise GlobalConfigRefused("provider_not_custom", f"{plan.provider_id!r} is not a custom provider") from exc
    provider = await repo.get_provider(row_id)
    if provider is None:
        raise NotFoundError("provider_not_found")
    before = await sanitized_custom_provider(session, provider)
    # Not compare-and-swap (see ``replace_custom_endpoint``): the revision check and the later replacement run in one
    # session without a row lock, so it detects stale reads, not a concurrent commit landing in between.
    if plan.expected_revision != before["revision"]:
        raise GlobalConfigRefused(
            "revision_conflict",
            "The provider changed since it was read; re-read it and retry with its current revision",
            expected=plan.expected_revision,
            current=before["revision"],
        )
    if plan.discovery_format is not None and plan.discovery_format != provider.discovery_format:
        raise GlobalConfigRefused("discovery_format_immutable", "A provider's discovery_format cannot change")
    api_key: str | None = None
    if plan.credential_ref is not None:
        credential = await resolve_credential_ref(session, plan.credential_ref)
        credential_origin, credential_ref = credential.origin, credential.ref
        api_key = credential.api_key
    else:
        # Keeping the stored key while moving the provider to another host would send it there implicitly.
        stored_origin = origin_of(provider.base_url)
        if stored_origin is None:
            raise GlobalConfigRefused(
                "credential_ref_unusable", "The stored credential has no determinable origin; pass credential_ref"
            )
        credential_origin, credential_ref = stored_origin, before["provider_id"]
    ensure_same_origin(credential_origin, plan.base_url, ref=credential_ref)
    stored_models = await repo.list_models(provider.id)
    if plan.models is not None:
        await validate_provider_models(
            session, list(plan.models), provider.discovery_format, _t, {m.model_id: m for m in stored_models}
        )
    await ensure_endpoint_requests_stay_on_origin(
        session,
        _bound(list(plan.models) if plan.models is not None else stored_models),
        base_url=plan.base_url,
        credential_origin=credential_origin,
        ref=credential_ref,
    )
    planned = {
        "display_name": plan.display_name,
        "base_url": plan.base_url,
        "image_max_workers": plan.image_max_workers or provider.image_max_workers,
        "video_max_workers": plan.video_max_workers or provider.video_max_workers,
        "audio_max_workers": plan.audio_max_workers or provider.audio_max_workers,
    }
    current = {key: before[key] for key in planned}
    fields = changed_paths(current, planned)
    if plan.models is not None:
        new_models = [m.model_dump(mode="json") for m in plan.models]
        old_models = [ModelInput.model_validate(m).model_dump(mode="json") for m in _model_inputs(before)]
        if new_models != old_models:
            fields.append("models")
    if api_key is not None and api_key != provider.api_key:
        fields.append("credential")
    impact = await provider_impact(session, projects, provider.id, [m.model_id for m in stored_models])
    kept = {m.model_id for m in (stored_models if plan.models is None else plan.models)}
    removed = sorted({m.model_id for m in stored_models} - kept)
    report: dict[str, Any] = {
        "applied": False,
        "operation": "update",
        "provider_id": before["provider_id"],
        "current_revision": before["revision"],
        "changed_fields": fields,
        "removed_models": removed,
        "impact": impact,
    }
    if not apply or not fields:
        return report
    await replace_custom_provider(
        session,
        provider.id,
        FullUpdateProviderRequest(
            display_name=plan.display_name,
            base_url=plan.base_url,
            api_key=api_key,
            models=list(plan.models) if plan.models is not None else None,
            image_max_workers=planned["image_max_workers"],
            video_max_workers=planned["video_max_workers"],
            audio_max_workers=planned["audio_max_workers"],
        ),
        _t,
        reload_limits=reload_limits,
        projects=projects,
    )
    await session.refresh(provider)
    audit(identity, "update_custom_provider", before["provider_id"], fields)
    return {**report, "applied": True, "provider": await sanitized_custom_provider(session, provider)}


def _model_inputs(sanitized: Mapping[str, Any]) -> list[dict[str, Any]]:
    keys = (
        "model_id",
        "display_name",
        "endpoint",
        "is_default",
        "is_enabled",
        "resolution",
        "capability_overrides",
        "path_overrides",
        "multiplier",
        "entry_binding",
    )
    return [{key: model.get(key) for key in keys} for model in sanitized.get("models", [])]


__all__ = [
    "PREVIEW_CREDENTIAL_MASK",
    "BoundModel",
    "GlobalConfigRefused",
    "ProviderPlan",
    "ReusableCredential",
    "audit",
    "changed_paths",
    "configure_custom_provider",
    "copy_builtin_endpoint",
    "endpoint_definition",
    "endpoint_impact",
    "ensure_endpoint_requests_stay_on_origin",
    "ensure_same_origin",
    "list_endpoints",
    "list_providers",
    "origin_of",
    "preview_definition",
    "provider_impact",
    "resolve_credential_ref",
    "update_custom_endpoint",
    "validate_definition",
]
