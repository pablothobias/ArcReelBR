"""Resolution values a declarative video endpoint can actually render, shared by configuration, preflight, and quotes.

A declarative definition that declares ``enum_maps.resolution`` fails rendering for any key outside that map
(``enum_map_value_missing``) — after the task already exists. Configuration writes, request facts (preview, quotes,
admission, execution) therefore validate against the same representation the renderer uses: the ArcReel-side
``enum_maps.resolution`` keys, compared exactly as :func:`.template_engine.enum_map_key`
does. Model facts (catalog ``resolutions`` / user overrides) narrow that set when they intersect it, matching what the
settings UI offers. No case-folding or alias is invented: a value is accepted only if the renderer accepts it verbatim.

Endpoints without a resolution enum map (Python backends, ComfyUI, unconstrained declarative definitions) return
``None``: their own runtime owns validation and this layer does not narrow it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def declarative_resolution_options(
    definition: Mapping[str, Any] | None, model_resolutions: Iterable[str] | None = None
) -> tuple[str, ...] | None:
    """Renderable resolution values in declaration order, or ``None`` when the endpoint does not constrain resolution."""
    if not isinstance(definition, Mapping):
        return None
    enum_maps = definition.get("enum_maps")
    if not isinstance(enum_maps, Mapping):
        return None
    resolution_map = enum_maps.get("resolution")
    if not isinstance(resolution_map, Mapping) or not resolution_map:
        return None
    renderable = tuple(str(key) for key in resolution_map)
    if model_resolutions is None:
        return renderable
    declared = {str(value) for value in model_resolutions}
    narrowed = tuple(value for value in renderable if value in declared)
    # Model facts that share no key with the renderer describe the provider side; the renderer stays authoritative.
    return narrowed or renderable


def resolution_suggestion(value: str, options: Iterable[str]) -> str | None:
    """A unique renderable value differing only by letter case, offered as a hint and never applied automatically."""
    matches = [option for option in options if option.lower() == value.lower() and option != value]
    return matches[0] if len(matches) == 1 else None


__all__ = ["declarative_resolution_options", "resolution_suggestion"]
