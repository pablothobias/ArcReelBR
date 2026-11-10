"""Resolution values must be ones the executing declarative endpoint renders (MCP-005).

Historical failure: ``2K`` was saved, quoted, admitted, and only failed at render time with
``enum_maps.resolution has no entry for 2K`` after the task existed.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from lib.config.resolver import ConfigResolver
from lib.custom_provider import make_provider_id
from lib.db.models.custom_endpoint import CustomEndpoint
from lib.db.models.custom_provider import CustomProvider, CustomProviderModel
from lib.generation.video_request_facts import (
    CONFIGURED_VIDEO_IDENTITY,
    ResolutionOverride,
    VideoRequestFacts,
    VideoRequestFactsFailure,
    evaluate_video_request_facts,
)

H3 = "minimax/MiniMax-H3"


def _project(resolution: str | None, pair: str = H3) -> dict:
    project: dict = {"generation_mode": "reference_video", "video_provider_r2v": pair}
    if resolution is not None:
        project["model_settings"] = {pair: {"resolution": resolution}}
    return project


async def _read(resolver, project, override=None):
    return await evaluate_video_request_facts(
        project,
        route="reference_video",
        generation_type="r2v",
        identity=CONFIGURED_VIDEO_IDENTITY,
        resolver=resolver,
        resolution_override=override,
    )


async def test_builtin_h3_options_follow_the_renderer_and_model_facts(db_factory):
    resolver = ConfigResolver(db_factory)
    assert await resolver.video_resolution_options("minimax", "MiniMax-H3") == ("768p", "2k")
    # Python endpoints validate themselves; this layer does not narrow them.
    assert await resolver.video_resolution_options("gemini-aistudio", "veo-3.1-generate-preview") is None


@pytest.mark.parametrize("override", [None, ResolutionOverride("2K")], ids=["saved", "preview-override"])
async def test_provider_side_spelling_is_refused_with_valid_values(db_factory, override):
    resolver = ConfigResolver(db_factory)
    project = _project("2K" if override is None else None)
    result = await _read(resolver, project, override)
    assert isinstance(result, VideoRequestFactsFailure)
    assert result.code == "video_resolution_not_supported"
    params = result.parameters()
    assert params["resolution"] == "2K"
    assert params["allowed_values"] == ["768p", "2k"]
    assert params["supported"] == "768p, 2k"


async def test_renderable_value_passes(db_factory):
    result = await _read(ConfigResolver(db_factory), _project("2k"))
    assert isinstance(result, VideoRequestFacts)
    assert result.resolution == "2k"


async def test_custom_provider_uses_its_endpoint_definition(db_factory):
    """A copied H3 endpoint (ce-N) is validated against its own enum map, like the built-in."""
    from lib.custom_provider.endpoints import ENDPOINT_REGISTRY

    definition = dict(ENDPOINT_REGISTRY["minimax-h3"].definition or {})
    async with db_factory() as session:
        endpoint = CustomEndpoint(
            kind="declarative",
            schema_version="1.2.0",
            media_type="video",
            display_name="H3 copy",
            definition=definition,
        )
        session.add(endpoint)
        provider = CustomProvider(
            display_name="Prov", discovery_format="openai", base_url="https://api.minimax.io", api_key="k"
        )
        session.add(provider)
        await session.flush()
        session.add(
            CustomProviderModel(
                provider_id=provider.id,
                model_id="MiniMax-H3",
                display_name="MiniMax-H3",
                endpoint=f"ce-{endpoint.id}",
            )
        )
        await session.commit()
        provider_id = make_provider_id(provider.id)
        assert (await session.execute(select(func.count()).select_from(CustomProviderModel))).scalar_one() == 1
    resolver = ConfigResolver(db_factory)
    options = await resolver.video_resolution_options(provider_id, "MiniMax-H3")
    assert options is not None
    assert "2k" in options
    assert "2K" not in options
