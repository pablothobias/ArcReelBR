"""Credentialed requests may only reach the origin their URL template fixes, never one a rendered value chose.

A URL template such as ``https://api.example{{ prompt }}`` lets free text extend the authority: a prompt of
``@collector.example/x`` turns the request (with its Bearer key) into one for ``collector.example``.

Two rules, each implemented once and shared by every caller (the definition validator, configuration-time
credential checks and the send-time guard in the declarative/ComfyUI clients):

- the authority rule, :func:`arcreel_market_core.endpoint_definition.url_authority_is_fixed`, decides whether a
  template fixes its origin (a leading ``{{ base_url }}`` / ``{{ override_base_url }}``, or a literal authority);
- the origin parser, :func:`strict_origin`, yields (scheme, host, port) only when :func:`urllib.parse.urlsplit` and
  :class:`httpx.URL` agree on it, so parser differentials cannot smuggle a second host. Any disagreement or
  unparsable URL counts as a mismatch.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import urlsplit

import httpx

from arcreel_market_core.endpoint_definition.url_authority import ORIGIN_PLACEHOLDERS, url_authority_is_fixed

#: Stable failure code for a request whose rendered origin is not the template's fixed origin.
CREDENTIAL_HOST_MISMATCH = "credential_host_mismatch"

_LEADING_PLACEHOLDER = re.compile(r"{{\s*(.*?)\s*}}")
_DEFAULT_PORTS = {"http": 80, "https": 443}

Origin = tuple[str, str, int]


def strict_origin(url: str) -> Origin | None:
    """(scheme, host, port) when both URL parsers agree on it; ``None`` for disagreement or unparsable URLs."""
    try:
        parts = urlsplit(url)
        split_port = parts.port
        parsed = httpx.URL(url)
    except (ValueError, TypeError, httpx.InvalidURL):
        return None
    scheme = parts.scheme.lower()
    default = _DEFAULT_PORTS.get(scheme)
    if default is None or not parts.hostname:
        return None
    split_origin = (scheme, parts.hostname.lower(), split_port or default)
    httpx_origin = (parsed.scheme.lower(), parsed.host.lower(), parsed.port or default)
    return split_origin if split_origin == httpx_origin else None


def origin_text(url: str | None) -> str | None:
    """``scheme://host:port`` form of :func:`strict_origin` (surrounding whitespace ignored), for stored origins."""
    origin = strict_origin(url.strip()) if url else None
    return None if origin is None else f"{origin[0]}://{origin[1]}:{origin[2]}"


def template_origin(url_template: str, context: Mapping[str, object]) -> Origin | None:
    """Origin the URL template fixes before any free-text value is rendered; ``None`` when it fixes none."""
    if not url_authority_is_fixed(url_template):
        return None
    leading = _LEADING_PLACEHOLDER.match(url_template)
    if leading is not None and leading.group(1) in ORIGIN_PLACEHOLDERS:
        base = context.get(leading.group(1))
        return strict_origin(base) if isinstance(base, str) and base else None
    return strict_origin(url_template.split("{{", 1)[0])


def credential_origin_matches(url_template: str, rendered_url: str, context: Mapping[str, object]) -> bool:
    """Whether a rendered URL stays on the origin its template fixes (the only origin allowed to get credentials)."""
    expected = template_origin(url_template, context)
    return expected is not None and strict_origin(rendered_url) == expected


__all__ = [
    "CREDENTIAL_HOST_MISMATCH",
    "Origin",
    "credential_origin_matches",
    "origin_text",
    "strict_origin",
    "template_origin",
]
