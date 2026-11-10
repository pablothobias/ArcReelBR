"""Whether a request URL template fixes its scheme and authority, so no rendered value can choose the host.

The single implementation of this rule: the definition validator, configuration-time credential checks and the
send-time credential guard all call it. URL placeholders render unescaped, so any value rendered into or directly
after the authority could append ``@host``, ``.host`` or ``:port`` and move the request, with its credentials,
elsewhere. Allowed shapes:

- ``{{ base_url }}`` / ``{{ override_base_url }}`` as the very first token, followed by nothing or by ``/``, ``?`` or
  ``#`` (the configured base URL supplies the whole origin);
- a literal ``http://`` / ``https://`` whose authority (up to the first ``/``, ``?`` or ``#``) is non-empty and holds
  no placeholder.
"""

from __future__ import annotations

import re

#: Placeholders allowed to supply a URL's whole origin, and only as the template's very first token.
ORIGIN_PLACEHOLDERS = frozenset({"base_url", "override_base_url"})

_PLACEHOLDER = re.compile(r"{{\s*(.*?)\s*}}")
_LITERAL_SCHEME = re.compile(r"https?://", re.IGNORECASE)
_AUTHORITY_END = "/?#"


def url_authority_violation(template: str) -> str | None:
    """The fragment that lets a rendered value choose the URL's origin, or ``None`` when the origin is fixed.

    The fragment is a placeholder name when one sits in (or directly after) the authority, otherwise the literal
    text that breaks the allowed shapes, so diagnostics can point at it.
    """
    leading = _PLACEHOLDER.match(template)
    if leading is not None:
        if leading.group(1) not in ORIGIN_PLACEHOLDERS:
            return leading.group(1)
        rest = template[leading.end() :]
        if rest == "" or rest[0] in _AUTHORITY_END:
            return None
        # Text right after the origin placeholder extends its host: report the placeholder being extended unless
        # another placeholder does the extending.
        following = _PLACEHOLDER.match(rest)
        return following.group(1) if following is not None else leading.group(1)
    scheme = _LITERAL_SCHEME.match(template)
    if scheme is None:
        first = _PLACEHOLDER.search(template)
        return first.group(1) if first is not None else template.split("/", 3)[0] or template[:16]
    authority_end = len(template)
    for delimiter in _AUTHORITY_END:
        found = template.find(delimiter, scheme.end())
        if found != -1:
            authority_end = min(authority_end, found)
    authority = template[scheme.end() : authority_end]
    if not authority:
        return template[:authority_end] or template[:16]
    inside = _PLACEHOLDER.search(authority)
    if inside is not None:
        return inside.group(1)
    if "{{" in authority:
        return authority
    return None


def url_authority_is_fixed(template: str) -> bool:
    """Whether only the definition or the configured base URL can decide where requests to this template go."""
    return url_authority_violation(template) is None


__all__ = ["ORIGIN_PLACEHOLDERS", "url_authority_is_fixed", "url_authority_violation"]
