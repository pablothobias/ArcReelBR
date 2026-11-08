"""Actual image quote/execution/accounting contracts use one effective catalog bound."""

import base64
import io
import json
from dataclasses import replace

import httpx
import pytest
from PIL import Image
from sqlalchemy import select

from arcreel_catalog_core import Meter, PriceRow, PriceTable
from lib.backends.gemini_shared import RateLimiter
from lib.backends.image_backends.base import ImageResponseError, ImageSubmissionAmbiguousError
from lib.backends.image_backends.gemini import GeminiImageBackend
from lib.billing.ledger import Ledger
from lib.catalog import query as catalog
from lib.config.resolver import ConfigResolver
from lib.db.models.api_call import ApiCall
from lib.generation.media_generator import MediaGenerator
from server.services.admission.cost_estimation import estimate_image_batch_cost
from tests.catalog_support import install_catalog, with_entry_changes
from tests.fakes import FakeConfigResolver, write_generation_targets


@pytest.mark.parametrize("outcome", ["success", "no_image", "save_failure", "ambiguous"])
async def test_existing_image_consumer_uses_quoted_cap_and_settles_discarded_usage(
    tmp_path, db_factory, monkeypatch, respx_mock, outcome
):
    table = PriceTable(
        currency="USD",
        meters=tuple(
            Meter(meter=meter, dims=(), rows=(PriceRow(when={}, price=price),))
            for meter, price in (("uncached_input_tokens", 0.5), ("output_tokens", 3), ("image_output_tokens", 60))
        ),
    )
    entry = catalog.provider_model_entry("gemini-aistudio", "gemini-3.1-flash-image", "image")
    facts = replace(entry.facts, max_input_tokens=131072, max_output_tokens=32768)
    install_catalog(
        monkeypatch,
        with_entry_changes(catalog.factory_snapshot(), "gemini-aistudio", entry.name, facts=facts, price=table),
    )
    project = {
        "title": "T",
        "content_mode": "narration",
        "image_provider_t2i": "gemini-aistudio/gemini-3.1-flash-image",
    }
    quote = await estimate_image_batch_cost(
        project, ["t2i"], aspect_ratio="1:1", resolver=ConfigResolver(db_factory), session_factory=db_factory
    )
    assert quote.unpriced_count == 0
    assert quote.total == {"USD": pytest.approx(2.031616)}
    assert quote.to_payload()["estimate_basis"] == "full_context_output_upper_bound"

    image = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(image, format="PNG")
    part = {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(image.getvalue()).decode()}}
    payload = {
        "candidates": [{"content": {"parts": [part] if outcome != "no_image" else [{"text": "No image"}]}}],
        "usageMetadata": {
            "promptTokenCount": 100,
            "candidatesTokenCount": 1120,
            "thoughtsTokenCount": 20,
            "totalTokenCount": 1240,
            "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}],
        },
    }
    route = respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=payload)
    if outcome == "ambiguous":
        route.mock(side_effect=httpx.ReadTimeout("possibly accepted; lost response"))
    backend = GeminiImageBackend(api_key="not-a-real-key", rate_limiter=RateLimiter({}))
    project_path = tmp_path / "project"
    project_path.mkdir()
    write_generation_targets(project_path, segments=("E1S01",))
    generator = MediaGenerator(
        project_path, image_backend=backend, image_provider_id="gemini-aistudio", config_resolver=FakeConfigResolver()
    )
    generator.ledger = Ledger(session_factory=db_factory)
    if outcome == "save_failure":
        save_image = Image.Image.save

        def failed_save(*args, **kwargs):
            if kwargs.get("format") == "PNG":
                raise OSError("controlled output persistence failure: payload too large")
            return save_image(*args, **kwargs)

        monkeypatch.setattr(Image.Image, "save", failed_save)
    references = []
    if outcome == "save_failure":
        reference = project_path / "reference.png"
        reference.write_bytes(image.getvalue())
        references = [reference]
    if outcome == "success":
        output, version = await generator.generate_image_async(
            prompt="square", resource_type="storyboards", resource_id="E1S01"
        )
        assert output.exists()
        assert version == 1
    else:
        with pytest.raises(ImageSubmissionAmbiguousError if outcome == "ambiguous" else ImageResponseError):
            await generator.generate_image_async(
                prompt="square", resource_type="storyboards", resource_id="E1S01", reference_images=references
            )
        assert not (project_path / "storyboards" / "scene_E1S01.png").exists()
    assert route.call_count == 1
    wire = json.loads(route.calls[0].request.content)
    assert wire["generationConfig"]["maxOutputTokens"] == facts.max_output_tokens
    async with db_factory() as session:
        row = (await session.execute(select(ApiCall))).scalars().one()
        assert row.status == ("success" if outcome == "success" else "failed")
        if outcome == "ambiguous":
            assert row.cost_amount is None
            assert row.unpriced_reason == "missing_rate"
            assert row.input_tokens is None
            assert row.output_tokens is None
        else:
            assert row.cost_amount == pytest.approx(0.06731)
            assert row.input_tokens == 100
            assert row.output_tokens == 1140
            assert row.image_output_tokens == 1120
            assert row.text_output_tokens == 20
            assert row.last_provider_response["usage_metadata"]["thoughts_token_count"] == 20
        assert row.output_path is not None if outcome == "success" else row.output_path is None


async def test_existing_batch_preview_marks_factory_gemini_pricing_incomplete(db_factory):
    project = {"title": "T", "image_provider_t2i": "gemini-aistudio/gemini-3.1-flash-image"}
    quote = await estimate_image_batch_cost(
        project, ["t2i"], aspect_ratio="1:1", resolver=ConfigResolver(db_factory), session_factory=db_factory
    )
    assert quote.to_payload() == {"estimated_cost": None, "unpriced_count": 1}
