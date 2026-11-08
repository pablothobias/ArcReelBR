"""Outbound declarative image MIME follows persisted bytes without rewriting source files."""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from arcreel_market_core.video_backend_contract import VideoGenerationRequest
from lib.custom_provider.declarative_backend import (
    DeclarativeJobEngine,
    DeclarativeRuntimeError,
    DeclarativeVideoBackend,
    extract_provider_state,
)
from lib.custom_provider.endpoints import ENDPOINT_REGISTRY
from tests.fakes import bounded_poll_clock
from tests.http_capture import capture_http, request_json


@pytest.mark.parametrize(("source_format", "mime"), [("JPEG", "image/jpeg"), ("PNG", "image/png")])
async def test_h3_serialized_request_uses_actual_image_mime_and_preserves_historical_bytes(
    tmp_path, source_format, mime
):
    content = io.BytesIO()
    Image.new("RGB", (16, 12), "teal").save(content, format=source_format)
    original = content.getvalue()
    image = tmp_path / "historical.png"
    image.write_bytes(original)
    backend = DeclarativeVideoBackend(
        api_key="test-key",
        base_url="https://api.minimax.io/v1/",
        model="MiniMax-H3",
        definition=ENDPOINT_REGISTRY["minimax-h3"].definition,
        provider="minimax",
    )
    with capture_http() as router, bounded_poll_clock():
        submit = router.post("https://api.minimax.io/v2/video_generation").respond(200, json={"task_id": "job-one"})
        router.get("https://api.minimax.io/v2/query/video_generation/job-one").respond(
            200, json={"task": {"status": "succeeded", "content": {"url": "https://cdn.test/video.mp4"}}}
        )
        router.get("https://cdn.test/video.mp4").respond(200, content=b"downloaded-video")
        result = await backend.generate(
            VideoGenerationRequest(
                prompt="neutral fixture",
                output_path=tmp_path / "result.mp4",
                duration_seconds=5,
                resolution="2k",
                start_image=image,
                reference_images=[image],
            )
        )

    body = request_json(submit.calls.last.request)
    assert body["model"] == "MiniMax-H3"
    for entry, role in zip(body["content"][1:], ["first_frame", "reference_image"], strict=True):
        assert entry["role"] == role
        prefix, encoded = entry["image_url"]["url"].split(",", 1)
        assert prefix == f"data:{mime};base64"
        assert base64.b64decode(encoded) == original
    assert image.read_bytes() == original
    assert result.video_path.read_bytes() == b"downloaded-video"


@pytest.mark.parametrize(
    ("name", "content", "mime"),
    [
        ("voice.wav", b"\xff\xd8\xffaudio", "audio/x-wav"),
        ("clip.mp4", b"\x89PNG\r\n\x1a\nvideo", "video/mp4"),
        ("unknown.bin", b"\x89PNG\r\n\x1a\nunknown", "application/octet-stream"),
    ],
)
def test_non_image_asset_mime_keeps_existing_extension_semantics(tmp_path, name, content, mime):
    path = tmp_path / name
    path.write_bytes(content)
    engine = DeclarativeJobEngine(
        api_key="test-key",
        base_url="https://api.minimax.io/v1/",
        model="MiniMax-H3",
        definition=ENDPOINT_REGISTRY["minimax-h3"].definition,
        provider="minimax",
        read_state=extract_provider_state,
        log_label="test",
    )

    context = engine.request_context({}, {"start_image": path})

    uri = context["inputs"]["first_frame"]
    assert uri == f"data:{mime};base64,{base64.b64encode(content).decode()}"
    assert path.read_bytes() == content


def test_missing_image_keeps_declarative_template_error(tmp_path):
    engine = DeclarativeJobEngine(
        api_key="test-key",
        base_url="https://api.minimax.io/v1/",
        model="MiniMax-H3",
        definition=ENDPOINT_REGISTRY["minimax-h3"].definition,
        provider="minimax",
        read_state=extract_provider_state,
        log_label="test",
    )

    with pytest.raises(DeclarativeRuntimeError) as caught:
        engine.request_context({}, {"start_image": tmp_path / "missing.png"})

    assert caught.value.code == "declarative_template_render_failed"
