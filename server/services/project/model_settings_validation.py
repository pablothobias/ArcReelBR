"""Reject ``model_settings`` values the executing endpoint cannot render, before any project write.

One check serves the MCP ``configure_project`` tool and the Web create/PATCH routes, so a value refused in one is
refused in all. It validates against :meth:`ConfigResolver.video_resolution_options`, the same representation that
request facts and the declarative renderer use. Values are compared verbatim after trimming; no alias or case-folding
is applied, only suggested. Valid maps are still written whole, preserving replacement semantics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from arcreel_market_core.endpoint_definition import resolution_suggestion
from lib.infra.api_errors import UnprocessableError

#: Stable code and i18n key for an unrenderable model setting value.
MODEL_SETTING_VALUE_UNSUPPORTED = "model_setting_value_unsupported"


class ResolutionOptionsSource(Protocol):
    async def video_resolution_options(
        self, provider_id: str, model_id: str, *, builtin_endpoint: str | None = None
    ) -> tuple[str, ...] | None: ...


@dataclass(frozen=True)
class UnsupportedModelSetting:
    """One rejected ``model_settings[<provider>/<model>].<field>`` value with the values the endpoint accepts."""

    model_key: str
    provider_id: str
    model_id: str
    field: str
    value: str
    allowed_values: tuple[str, ...]
    suggestion: str | None

    def params(self) -> dict[str, Any]:
        """Structured repair data shared by the MCP problem and the Web diagnostic."""
        params: dict[str, Any] = {
            "model_key": self.model_key,
            "field": self.field,
            "value": self.value,
            "allowed_values": list(self.allowed_values),
        }
        if self.suggestion is not None:
            params["suggestion"] = self.suggestion
        return params

    def detail(self) -> str:
        return (
            f"model_settings[{self.model_key}].{self.field}={self.value!r} is not accepted by the selected endpoint; "
            f"valid values: {', '.join(self.allowed_values)}. Nothing was saved."
        )

    def api_error(self) -> UnprocessableError:
        """HTTP 422 with an i18n key; the structured params ride along as the diagnostic."""
        return UnprocessableError(
            MODEL_SETTING_VALUE_UNSUPPORTED,
            provider=self.provider_id,
            model=self.model_id,
            value=self.value,
            allowed_values=", ".join(self.allowed_values),
        ).with_diagnostic(self.params())


async def find_unsupported_model_setting(
    model_settings: Mapping[str, Mapping[str, Any] | None] | None,
    resolver: ResolutionOptionsSource,
    *,
    stored: Mapping[str, Any] | None = None,
) -> UnsupportedModelSetting | None:
    """First changed ``model_settings`` value the endpoint cannot render, or ``None`` when every value is accepted.

    Callers submit the whole map, so ``stored`` (the project's current map) exempts values that are unchanged: a
    legacy or since-narrowed entry for another model must not block saving an unrelated edit. Execution-time request
    facts still refuse such a stale value before any task exists. Endpoints that do not constrain resolution (``None``
    options) are left to their own runtime validation.
    """
    for key, settings in (model_settings or {}).items():
        raw = (settings or {}).get("resolution")
        value = raw.strip() if isinstance(raw, str) else None
        if not value or value == _stored_resolution(stored, key):
            continue
        provider_id, _, model_id = key.partition("/")
        options = await resolver.video_resolution_options(provider_id, model_id)
        if options is None or value in options:
            continue
        return UnsupportedModelSetting(
            model_key=key,
            provider_id=provider_id,
            model_id=model_id,
            field="resolution",
            value=value,
            allowed_values=tuple(options),
            suggestion=resolution_suggestion(value, options),
        )
    return None


def _stored_resolution(stored: Mapping[str, Any] | None, key: str) -> str | None:
    entry = (stored or {}).get(key)
    raw = entry.get("resolution") if isinstance(entry, Mapping) else None
    return raw.strip() if isinstance(raw, str) else None


async def raise_for_unsupported_model_settings(
    model_settings: Mapping[str, Mapping[str, Any] | None] | None,
    resolver: ResolutionOptionsSource,
    *,
    stored: Mapping[str, Any] | None = None,
) -> None:
    """Web entry point: raise HTTP 422 (``model_setting_value_unsupported``) before anything is written."""
    if unsupported := await find_unsupported_model_setting(model_settings, resolver, stored=stored):
        raise unsupported.api_error()
