"""Response JSONPath extraction and status mapping for declarative invocation endpoints."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from jsonpath_rfc9535 import JSONPathError, find

from arcreel_market_core.definition_diagnostics import DefinitionErrorCode, message_key
from arcreel_market_core.validation_messages import ValidationMessage, code_translator
from arcreel_market_core.video_backend_contract import ProviderJobStatus, normalize_provider_status

from .jsonpath_subset import parse_json_path

_DECLARATIVE_STATUSES = frozenset(
    {
        ProviderJobStatus.QUEUED,
        ProviderJobStatus.RUNNING,
        ProviderJobStatus.SUCCEEDED,
        ProviderJobStatus.FAILED,
    }
)


class JsonPathEvaluationError(ValueError):
    """The runtime JSONPath implementation cannot evaluate a path that passed the subset gate."""

    def __init__(self, path: str, cause: Exception) -> None:
        self.code = DefinitionErrorCode.JSONPATH_EVALUATION_FAILED
        self.message = ValidationMessage(message_key(self.code), {"path_expression": path})
        super().__init__(self.message.render(code_translator))


def extract_value(spec: object, response_body: object) -> object | None:
    """Return the first acceptable first match in priority order, or ``None`` if nothing matches."""
    paths, accept = normalize_extract_spec(spec)
    for item in paths:
        if isinstance(item, str):
            hit = _first_acceptable(item, response_body, accept)
        elif isinstance(item, Mapping):
            hit = _decode_then(item, response_body, accept)
        else:
            raise TypeError("Extraction path items must be strings or objects")
        if hit is not None:
            return hit
    return None


def map_status(raw: object, status_map: Mapping[str, str] | None = None) -> ProviderJobStatus:
    """Map provider states through an explicit dictionary into the four declarative categories; keep polling unknown values.

    If ``status_map`` misses, fall back to the built-in ``normalize_provider_status`` synonyms,
    which normalize common provider forms (``IN_PROGRESS`` / ``WAITING_GPU``, etc.) to shared states,
    classifying entirely unknown values as ``RUNNING`` to continue polling rather than falsely fail. ``EXPIRED`` is outside the four declarative categories and folds into ``FAILED``.
    """
    key = str(raw).strip().lower() if raw is not None else ""
    normalized_map = {str(source).strip().lower(): target for source, target in (status_map or {}).items()}
    if key in normalized_map:
        mapped = ProviderJobStatus(normalized_map[key])
        if mapped not in _DECLARATIVE_STATUSES:
            raise ValueError(f"Unsupported declarative status: {mapped.value}")
        return mapped
    fallback = normalize_provider_status(raw)
    return ProviderJobStatus.FAILED if fallback is ProviderJobStatus.EXPIRED else fallback


def normalize_extract_spec(spec: object) -> tuple[Sequence[object], str]:
    """Split extraction rules into a path-item sequence and acceptable type.

    Public rather than private: response validation reports each item's match status, so its per-item evaluation must share
    normalization with :func:`extract_value`. If each parses shorthand and object forms independently, drift in shorthand default ``accept`` would make reported
    matches differ from actual runtime extracted values.
    """
    if isinstance(spec, list):
        return spec, "string"
    if not isinstance(spec, Mapping):
        raise TypeError("Extraction rules must be a path array or an object")
    paths = spec.get("paths")
    if not isinstance(paths, list):
        raise TypeError("Extraction rules are missing the paths array")
    accept = spec.get("accept", "string")
    if accept not in {"string", "scalar"}:
        raise ValueError(f"Unknown accept: {accept}")
    return paths, accept


#: Declared classification of a provider error code; see :func:`classify_provider_error_code`.
ProviderErrorClass = Literal["fix_input", "configure", "unclassified"]


def classify_provider_error_code(spec: object, code: str) -> ProviderErrorClass:
    """Classify an extracted provider code by the ``error_code`` spec's declared code sets.

    ``fix_input_codes`` mean the request content or inputs must change; ``configure_codes`` mean credentials,
    balance or endpoint configuration must change. Anything else, including every code of the shorthand array form,
    is ``unclassified``: the code and message stay available, but no repair is implied. Codes compare as strings,
    exactly as ``accept: scalar`` stringifies them.
    """
    if isinstance(spec, Mapping):
        if code in {str(value) for value in spec.get("fix_input_codes") or ()}:
            return "fix_input"
        if code in {str(value) for value in spec.get("configure_codes") or ()}:
            return "configure"
    return "unclassified"


def _first_acceptable(path: str, target: Any, accept: str) -> object | None:
    parse_json_path(path)
    try:
        for node in find(path, target):
            if _acceptable(node.value, accept):
                return node.value
    except (ArithmeticError, JSONPathError) as exc:
        raise JsonPathEvaluationError(path, exc) from exc
    return None


def _decode_then(item: Mapping[str, object], response_body: object, accept: str) -> object | None:
    encoded = _first_acceptable(str(item["path"]), response_body, "string")
    if not isinstance(encoded, str):
        return None
    try:
        decoded = json.loads(encoded)
    except (TypeError, ValueError):
        return None
    then = item.get("then", ["$"])
    if not isinstance(then, list):
        return None
    for path in then:
        hit = _first_acceptable(str(path), decoded, accept)
        if hit is not None:
            return hit
    return None


def _acceptable(value: object, accept: str) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return accept == "scalar" and isinstance(value, (int, float, bool))
