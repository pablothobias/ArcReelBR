"""Read a provider's own error code and message out of a persisted provider response body.

Failures recorded before an endpoint definition declared ``extract.error_code`` (or by backends that never lift the
provider's verdict into the task failure) persist only a generic task reason such as
``provider reported failure (status: failed)``, while the last provider response stored on the usage record still
carries the real verdict, e.g. MiniMax ``{"task": {"error": {"code": "2013", "message": …}}}``.

The usage record does not persist which endpoint-definition revision produced it, so the definition's declared
``extract.error``/``error_code`` paths cannot be resolved deterministically for a historical row. This module
therefore reads a bounded, ordered set of well-known structured shapes. It starts from the runtime definition shared
with :func:`lib.backends.backend_runtime.extract_provider_error_message` (``PROVIDER_ERROR_PATHS`` and
``PROVIDER_ERROR_MESSAGE_KEYS``) and extends it explicitly:

* error objects at ``$.error``, ``$.data.error`` (runtime) and ``$.task.error`` (extension), each either an object
  with a code (``code``/``error_code``) and a message (runtime keys plus ``msg``) or a non-empty string message;
* MiniMax ``$.base_resp`` (extension) with ``status_code``/``status_msg``.

An object whose code is a success code (``0``) is not a verdict. A code is only ever copied from the body (integers
stringified exactly as ``accept: scalar`` does); codes longer than :data:`MAX_PROVIDER_CODE_CHARS` are treated as
unknown, and nothing is inferred from message text. A body stored as a JSON string is parsed only if it is complete JSON. A response bounded at persistence
(``{"truncated": true, "body": "<json prefix>"}``, see ``usage_repo.bound_provider_response``) always holds a cut
prefix of oversized JSON, which is never complete, so nothing is extracted from it and the code stays unknown. Pure
function, no I/O.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from lib.backends.backend_runtime import PROVIDER_ERROR_MESSAGE_KEYS, PROVIDER_ERROR_PATHS

#: Ordered candidate locations of an error object or string: the runtime locations, then ``task.error``.
_ERROR_OBJECT_PATHS: tuple[tuple[str | int, ...], ...] = (*PROVIDER_ERROR_PATHS, ("task", "error"))
_CODE_KEYS = ("code", "error_code")
#: Runtime message keys, then ``msg``.
_MESSAGE_KEYS: tuple[str, ...] = (*PROVIDER_ERROR_MESSAGE_KEYS, "msg")
#: Codes meaning "no error" in providers that always return a status block.
_SUCCESS_CODES = frozenset({"0"})
#: Longest provider code accepted; anything longer is not a code and stays unknown.
MAX_PROVIDER_CODE_CHARS = 128

#: ``json``: the stored column value was already structured JSON. ``json_text``: it was a raw JSON string decoded
#: here; ``path`` is then relative to the decoded document.
SourceEncoding = Literal["json", "json_text"]


@dataclass(frozen=True, slots=True)
class PersistedProviderError:
    """A provider verdict found in a persisted response; ``code`` stays ``None`` when the body has none."""

    code: str | None
    message: str | None
    #: JSONPath of the error object relative to the persisted column value, e.g. ``$.task.error``. With
    #: ``json_text`` encoding it addresses the decoded document.
    path: str
    source_encoding: SourceEncoding


def is_truncation_wrapper(body: object) -> bool:
    """Whether persistence already cut the response (``usage_repo.bound_provider_response`` marker)."""
    return isinstance(body, Mapping) and body.get("truncated") is True and set(body) == {"truncated", "body"}


def _code_text(value: object) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text or len(text) > MAX_PROVIDER_CODE_CHARS:
        return None
    return text


def _message_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _dig(body: object, path: tuple[str | int, ...]) -> object:
    current = body
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _from_error_node(node: object) -> tuple[str | None, str | None] | None:
    if isinstance(node, str):
        message = _message_text(node)
        return (None, message) if message else None
    if not isinstance(node, Mapping):
        return None
    codes = [c for c in (_code_text(node.get(key)) for key in _CODE_KEYS) if c is not None]
    failure_codes = [c for c in codes if c not in _SUCCESS_CODES]
    if codes and not failure_codes:
        # Only success statuses: not a verdict, whatever its message says.
        return None
    code = failure_codes[0] if failure_codes else None
    message = next((m for m in (_message_text(node.get(key)) for key in _MESSAGE_KEYS) if m is not None), None)
    if code is None and message is None:
        return None
    return code, message


def _from_base_resp(node: object) -> tuple[str | None, str | None] | None:
    if not isinstance(node, Mapping):
        return None
    code = _code_text(node.get("status_code"))
    if code is None or code in _SUCCESS_CODES:
        return None
    return code, _message_text(node.get("status_msg"))


def _decode_text(text: str) -> object | None:
    try:
        return json.loads(text)
    except (ValueError, RecursionError):
        return None


def extract_persisted_provider_error(body: object) -> PersistedProviderError | None:
    """Return the first well-known provider error in a persisted response body, or ``None`` if there is none."""
    if is_truncation_wrapper(body):
        # Persistence keeps only a cut prefix of oversized JSON: never complete, so no verdict can be read from it.
        return None
    encoding: SourceEncoding = "json"
    if isinstance(body, str):
        body = _decode_text(body)
        encoding = "json_text"
    if not isinstance(body, Mapping):
        return None
    found: tuple[str | None, str | None] | None = None
    location: tuple[str | int, ...] = ()
    for path in _ERROR_OBJECT_PATHS:
        found = _from_error_node(_dig(body, path))
        if found is not None:
            location = path
            break
    if found is None:
        found = _from_base_resp(body.get("base_resp"))
        location = ("base_resp",)
    if found is None:
        return None
    return PersistedProviderError(
        code=found[0],
        message=found[1],
        path=".".join(("$", *(str(key) for key in location))),
        source_encoding=encoding,
    )


__all__ = [
    "MAX_PROVIDER_CODE_CHARS",
    "PersistedProviderError",
    "SourceEncoding",
    "extract_persisted_provider_error",
    "is_truncation_wrapper",
]
