"""Gemini image requests preserve billable axes and avoid ambiguous paid resubmission."""

from __future__ import annotations

import base64
import io
import json
from dataclasses import replace

import httpx
import pytest
from google.genai import errors
from PIL import Image

from arcreel_catalog_core import CatalogEntry, ImageFacts, Meter, PriceRow, PriceTable
from lib.backends.gemini_shared import RateLimiter
from lib.backends.http_status_errors import AmbiguousSubmitError
from lib.backends.image_backends.base import ImageGenerationRequest, ImageRequestFacts, ImageResponseError
from lib.backends.image_backends.gemini import GeminiImageBackend
from lib.billing.metering import Priced, Unpriced, UnpricedReason, price_usage
from lib.catalog import query as catalog
from lib.catalog.user_entries import edited_entry
from lib.custom_provider.factory import create_custom_backend
from lib.custom_provider.metering import with_image_counts
from lib.db.models.custom_provider import CustomProvider
from lib.infra.retry import bind_clock
from tests.catalog_support import install_catalog, with_entry_changes


def _payload():
    image = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(image, format="PNG")
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(image.getvalue()).decode()}}
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 100,
            "cachedContentTokenCount": 0,
            "candidatesTokenCount": 1130,
            "thoughtsTokenCount": 20,
            "totalTokenCount": 1250,
            "promptTokensDetails": [{"modality": "TEXT", "tokenCount": 20}, {"modality": "IMAGE", "tokenCount": 80}],
            "candidatesTokensDetails": [
                {"modality": "TEXT", "tokenCount": 10},
                {"modality": "IMAGE", "tokenCount": 1120},
            ],
        },
    }


def _table():
    return PriceTable(
        currency="USD",
        meters=tuple(
            Meter(meter=meter, dims=(), rows=(PriceRow(when={}, price=price),))
            for meter, price in (("uncached_input_tokens", 0.5), ("output_tokens", 3), ("image_output_tokens", 60))
        ),
    )


@pytest.fixture
def backend():
    return GeminiImageBackend(api_key="not-a-real-key", rate_limiter=RateLimiter({}))


async def test_actual_sdk_response_records_disjoint_usage_and_unrounded_image_cost(backend, respx_mock, tmp_path):
    route = respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=_payload())
    result = await backend.generate(
        ImageGenerationRequest(
            prompt="red square", output_path=tmp_path / "out.png", image_size="1K", max_output_tokens=2048
        )
    )
    assert result.usage.quantities == {"uncached_input_tokens": 100, "output_tokens": 30, "image_output_tokens": 1120}
    assert not result.usage.missing_quantities
    assert (result.input_tokens, result.output_tokens, result.usage_tokens) == (100, 1150, 1250)
    assert (result.image_input_tokens, result.text_input_tokens) == (80, 20)
    cost = price_usage(_table(), result.usage, multiplier=1)
    assert isinstance(cost, Priced)
    assert cost.amount == pytest.approx(0.06734)
    assert Image.open(result.image_path).size == (4, 4)
    wire = json.loads(route.calls[0].request.content)
    assert wire["generationConfig"]["maxOutputTokens"] == 2048
    assert wire["generationConfig"]["candidateCount"] == 1
    assert route.call_count == 1


@pytest.mark.parametrize(("source_format", "mode"), [("JPEG", "RGB"), ("PNG", "RGBA")])
async def test_actual_sdk_image_bytes_become_png_without_losing_alpha(
    backend, respx_mock, tmp_path, source_format, mode
):
    content = io.BytesIO()
    color = (20, 90, 160, 79) if mode == "RGBA" else (20, 90, 160)
    Image.new(mode, (4, 4), color).save(content, format=source_format)
    payload = _payload()
    payload["candidates"][0]["content"]["parts"] = [
        {
            "inlineData": {
                "mimeType": Image.MIME[source_format],
                "data": base64.b64encode(content.getvalue()).decode(),
            }
        }
    ]
    route = respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=payload)
    output = tmp_path / "formal.png"

    result = await backend.generate(ImageGenerationRequest(prompt="casting sheet", output_path=output))

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as image:
        assert image.format == "PNG"
        assert image.size == (4, 4)
        assert image.mode == mode
        if mode == "RGBA":
            assert image.getpixel((0, 0)) == color
    assert result.usage.quantities["image_output_tokens"] == 1120
    assert route.call_count == 1


async def test_invalid_returned_image_retains_usage_without_retry(backend, respx_mock, tmp_path):
    payload = _payload()
    payload["candidates"][0]["content"]["parts"][0]["inlineData"]["data"] = base64.b64encode(
        b"not a decodable image"
    ).decode()
    route = respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=payload)
    output = tmp_path / "invalid.png"

    with pytest.raises(ImageResponseError, match="Invalid image") as caught:
        await backend.generate(ImageGenerationRequest(prompt="casting sheet", output_path=output))

    assert caught.value.result.usage.quantities["image_output_tokens"] == 1120
    assert route.call_count == 1
    assert not output.exists()


@pytest.mark.parametrize(
    "change",
    ["absent", "thoughts_and_total_absent", "image_details_absent", "cache_exceeds_prompt", "details_exceed_total"],
)
async def test_missing_or_inconsistent_metadata_never_prices_partial_usage(backend, respx_mock, tmp_path, change):
    payload = _payload()
    usage = payload["usageMetadata"]
    if change == "absent":
        payload.pop("usageMetadata")
    elif change == "thoughts_and_total_absent":
        usage.pop("thoughtsTokenCount")
        usage.pop("totalTokenCount")
    elif change == "image_details_absent":
        usage.pop("candidatesTokensDetails")
    elif change == "cache_exceeds_prompt":
        usage["cachedContentTokenCount"] = 101
    else:
        usage["candidatesTokensDetails"][0]["tokenCount"] = 50
    respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=payload)
    result = await backend.generate(ImageGenerationRequest(prompt="square", output_path=tmp_path / "out.png"))
    assert result.usage.missing_quantities
    assert price_usage(_table(), result.usage, multiplier=1) == Unpriced(UnpricedReason.MISSING_RATE)


async def test_consistent_totals_can_prove_omitted_thinking_and_preserve_aggregate_input(backend, respx_mock, tmp_path):
    payload = _payload()
    payload["usageMetadata"].pop("thoughtsTokenCount")
    payload["usageMetadata"].pop("promptTokensDetails")
    respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=payload)
    result = await backend.generate(ImageGenerationRequest(prompt="square", output_path=tmp_path / "out.png"))
    assert result.input_tokens == 100
    assert result.image_input_tokens is None
    assert result.text_input_tokens is None
    assert result.usage.quantities["output_tokens"] == 30
    assert not result.usage.missing_quantities


async def test_discarded_response_keeps_measured_usage_without_an_artifact_or_retry(backend, respx_mock, tmp_path):
    payload = _payload()
    payload["candidates"][0]["content"]["parts"] = [{"text": "No image"}]
    route = respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=payload)
    output = tmp_path / "absent.png"
    with pytest.raises(ImageResponseError) as caught:
        await backend.generate(ImageGenerationRequest(prompt="square", output_path=output))
    assert caught.value.result.usage.quantities["image_output_tokens"] == 1120
    assert route.call_count == 1
    assert not output.exists()


@pytest.mark.parametrize(
    "failure", [TimeoutError("lost response"), httpx.ReadTimeout("lost response"), httpx.WriteError("partially sent")]
)
async def test_ambiguous_transport_never_resends_inside_sdk_or_backend(backend, respx_mock, tmp_path, failure):
    route = respx_mock.post(url__regex=r".*:generateContent$").mock(side_effect=failure)
    with pytest.raises(AmbiguousSubmitError):
        await backend.generate(ImageGenerationRequest(prompt="square", output_path=tmp_path / "out.png"))
    assert route.call_count == 1


async def test_server_error_does_not_activate_sdk_automatic_retry(backend, respx_mock, tmp_path):
    route = respx_mock.post(url__regex=r".*:generateContent$").respond(
        503, json={"error": {"code": 503, "message": "busy"}}
    )
    with pytest.raises(errors.ServerError):
        await backend.generate(ImageGenerationRequest(prompt="square", output_path=tmp_path / "out.png"))
    assert route.call_count == 1


async def test_definitely_unsent_connection_failure_can_retry_without_repeating_accepted_work(
    backend, respx_mock, tmp_path
):
    class Clock:
        def monotonic(self):
            return 0.0

        async def sleep(self, delay):
            pass

    route = respx_mock.post(url__regex=r".*:generateContent$").mock(
        side_effect=[httpx.ConnectTimeout("not connected"), httpx.Response(200, json=_payload())]
    )
    with bind_clock(Clock()):
        result = await backend.generate(ImageGenerationRequest(prompt="square", output_path=tmp_path / "out.png"))
    assert route.call_count == 2
    assert result.image_path.exists()


def test_request_facts_without_billing_bounds_remain_incomplete_even_with_old_image_only_price():
    usage = GeminiImageBackend.estimate_usage(ImageRequestFacts(model="gemini-3.1-flash-image", aspect_ratio="9:16"))
    old = PriceTable(
        currency="USD", meters=(Meter(meter="output_images", dims=(), rows=(PriceRow(when={}, price=0.067),)),)
    )
    assert price_usage(old, usage, multiplier=1, estimate=True) == Unpriced(UnpricedReason.NO_USAGE_ESTIMATE)


def _bounded_entry(table=None):
    return CatalogEntry(
        maker="google",
        name="gemini-3.1-flash-image",
        media_type="image",
        display_name="Nano Banana 2",
        price=table or _table(),
        facts=ImageFacts(text_to_image=True, image_to_image=True, max_input_tokens=131072, max_output_tokens=32768),
    )


@pytest.mark.parametrize("higher", ["image_output_tokens", "output_tokens"])
def test_quote_uses_larger_fully_priced_disjoint_output_envelope(higher):
    table = _table()
    if higher == "output_tokens":
        table = replace(
            table,
            meters=tuple(
                replace(meter, rows=(PriceRow(when={}, price=100),)) if meter.meter == "output_tokens" else meter
                for meter in table.meters
            ),
        )
    usage = GeminiImageBackend.estimate_usage(
        ImageRequestFacts(model="gemini-3.1-flash-image", aspect_ratio="9:16", entry=_bounded_entry(table))
    )
    assert usage.quantities["image_output_tokens"] + usage.quantities["output_tokens"] == 32768
    assert usage.quantities[higher] == 32768
    assert usage.quantities["uncached_input_tokens"] == 131072
    assert usage.estimate_basis == "full_context_output_upper_bound"
    cost = price_usage(table, usage, multiplier=1, estimate=True)
    assert isinstance(cost, Priced)
    assert cost.amount == pytest.approx(0.065536 + 32768 * (60 if higher == "image_output_tokens" else 100) / 1_000_000)


@pytest.mark.parametrize(
    "missing",
    ["max_input_tokens", "max_output_tokens", "uncached_input_tokens", "output_tokens", "image_output_tokens"],
)
def test_quote_requires_both_bounds_and_every_positive_rate(missing):
    entry = _bounded_entry()
    if missing.startswith("max_"):
        entry = replace(entry, facts=replace(entry.facts, **{missing: None}))
    else:
        entry = replace(
            entry, price=replace(entry.price, meters=tuple(m for m in entry.price.meters if m.meter != missing))
        )
    usage = GeminiImageBackend.estimate_usage(ImageRequestFacts(model=entry.name, aspect_ratio="9:16", entry=entry))
    assert usage.missing_quantities
    assert price_usage(entry.price, usage, multiplier=1, estimate=True) == Unpriced(UnpricedReason.NO_USAGE_ESTIMATE)


def test_user_fact_edits_and_custom_count_supplement_preserve_billing_bounds_and_missing_state():
    entry = edited_entry(_bounded_entry(), display_name="Local display", facts={"resolutions": ["1K"]})
    assert (entry.facts.max_input_tokens, entry.facts.max_output_tokens) == (131072, 32768)
    usage = GeminiImageBackend.estimate_usage(ImageRequestFacts(model=entry.name, aspect_ratio="9:16"))
    supplemented = with_image_counts(usage, 2)
    assert supplemented.missing_quantities == usage.missing_quantities
    assert supplemented.quantities["input_images"] == 2


async def test_custom_bound_entry_uses_identical_catalog_output_cap_in_actual_sdk_request(
    monkeypatch, respx_mock, tmp_path
):
    entry = _bounded_entry()
    install_catalog(
        monkeypatch,
        with_entry_changes(
            catalog.factory_snapshot(), "gemini-aistudio", entry.name, facts=entry.facts, price=entry.price
        ),
    )
    provider = CustomProvider(
        id=1,
        api_key="not-a-real-key",
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    backend = create_custom_backend(
        provider=provider,
        model_id="relay-image",
        endpoint="gemini-image",
        entry_binding="google/gemini-3.1-flash-image",
    )
    route = respx_mock.post(url__regex=r".*:generateContent$").respond(200, json=_payload())
    result = await backend.generate(ImageGenerationRequest(prompt="square", output_path=tmp_path / "out.png"))
    wire = json.loads(route.calls[0].request.content)
    assert wire["generationConfig"]["maxOutputTokens"] == entry.facts.max_output_tokens
    assert result.image_path.exists()
    assert route.call_count == 1
