"""Offline reproduction of the observed MiniMax H3 failures (MCP-006 / MCP-008) through the built-in definition.

Fixtures replay the historical provider responses: ``task.error={code: 2013, message: ".mpeg"/".x-wav" not allowed}``.
No network: respx intercepts every request.

Declared H3 code sets (``extract.error_code``) and their sources:

- ``2013`` invalid parameters → fix_input: the observed ``.mpeg`` / ``.x-wav`` production failures replayed here, and
  the MiniMax error-code reference.
- ``1026`` input content flagged as sensitive, ``1027`` output content flagged as sensitive → fix_input: MiniMax
  error-code reference (change the prompt or references).
- ``1004`` authentication failed, ``1008`` insufficient balance → configure: MiniMax error-code reference.
- Anything else (e.g. ``1002`` rate limited, ``1000`` unknown) stays unclassified: the code and message are kept, the
  action is a user-authorized retry, never an automatic one.

The create endpoint's HTTP error body is ``{type: "error", error: {type, message, http_code}, request_id}`` (official
v2 create page); the query endpoint's ``task.error.{code, message}`` is documented on the official query page.
"""

from __future__ import annotations

import base64
import hashlib
import mimetypes
from pathlib import Path

import httpx
import pytest

from arcreel_market_core.video_backend_contract import VideoCapabilityError, VideoGenerationRequest
from lib.backends.http_status_errors import ProviderRejectedError
from lib.custom_provider.declarative_backend import (
    PROVIDER_ERROR_MESSAGE_MAX_CHARS,
    DeclarativeVideoBackend,
    ProviderJobRejectedError,
)
from lib.custom_provider.endpoints import ENDPOINT_REGISTRY
from lib.generation.generation_result import GenerationAction, problem_from_task_failure
from lib.generation.task_failure_encoding import encode_task_failure_message
from tests.fakes import bounded_poll_clock
from tests.http_capture import capture_http, request_json

WAV = (
    b"RIFF\x28\x00\x00\x00WAVE"
    b"fmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00"
    b"data\x04\x00\x00\x00\x01\x02\x03\x04"
)
MP3 = (b"\xff\xfb\x90\x00" + b"\x00" * 413) * 2
PNGS = [b"\x89PNG\r\n\x1a\nREF" + bytes([i]) for i in range(4)]
BASE = "https://api.minimax.io"
MPEG_FAILURE = {
    "task": {
        "status": "failed",
        "error": {"code": 2013, "message": 'content[6].audio_url: invalid param: audio format ".mpeg" not allowed'},
    },
    "base_resp": {"status_code": 0, "status_msg": "success"},
}
XWAV_FAILURE = {
    "task": {
        "status": "failed",
        "error": {"code": 2013, "message": 'content[5].audio_url: invalid param: audio format ".x-wav" not allowed'},
    },
    "base_resp": {"status_code": 0, "status_msg": "success"},
}


def _backend() -> DeclarativeVideoBackend:
    definition = ENDPOINT_REGISTRY["minimax-h3"].definition
    assert definition is not None
    return DeclarativeVideoBackend(
        api_key="sk-test-secret-key-123456",
        base_url=BASE,
        model="MiniMax-H3",
        definition=definition,
        provider="minimax",
    )


def _request(tmp_path: Path, audio: list[tuple[str, bytes]], **overrides) -> VideoGenerationRequest:
    images = []
    for index, content in enumerate(PNGS):
        path = tmp_path / f"ref{index}.png"
        path.write_bytes(content)
        images.append(path)
    audio_paths = []
    for name, content in audio:
        path = tmp_path / name
        path.write_bytes(content)
        audio_paths.append(path)
    values = {
        "prompt": "@图片1 talks to @图片2 [@音频1] [@音频2]",
        "output_path": tmp_path / "out.mp4",
        "duration_seconds": 10,
        "aspect_ratio": "9:16",
        "resolution": "2k",
        "reference_images": images,
        "reference_audio_files": audio_paths or None,
    }
    values.update(overrides)
    return VideoGenerationRequest(**values)


def _routes(router, poll_responses):
    submit = router.post(f"{BASE}/v2/video_generation").mock(
        return_value=httpx.Response(200, json={"task_id": "461931189367168", "base_resp": {"status_code": 0}})
    )
    poll = router.get(url__regex=rf"^{BASE}/v2/query/video_generation/.+").mock(side_effect=poll_responses)
    router.get(url__regex=r"^https://cdn\.test/").mock(return_value=httpx.Response(200, content=b"mp4"))
    return submit, poll


@pytest.mark.parametrize("response", [MPEG_FAILURE, XWAV_FAILURE], ids=["2013-mpeg", "2013-x-wav"])
async def test_coded_job_failure_carries_code_and_message_and_is_not_retryable(tmp_path, response):
    backend = _backend()
    with capture_http() as router, bounded_poll_clock():
        submit, poll = _routes(router, [httpx.Response(200, json=response)])
        with pytest.raises(ProviderJobRejectedError) as raised:
            await backend.generate(_request(tmp_path, [("a.wav", WAV), ("b.mp3", MP3)]))
    assert submit.call_count == 1
    assert poll.call_count == 1  # a provider verdict is terminal: no further polling or resubmission
    error = raised.value
    assert error.params["provider_error_code"] == "2013"
    assert error.params["stage"] == "poll"
    assert error.params["provider_status"] == "failed"
    assert response["task"]["error"]["message"] == error.params["provider_error_message"]
    assert "{" not in error.params["provider_error_message"]  # never str(dict)

    stored = encode_task_failure_message(error)
    problem = problem_from_task_failure(stored)
    assert problem.code == "provider_job_rejected"
    assert problem.action is GenerationAction.FIX_INPUT
    assert problem.params["provider_error_code"] == "2013"


@pytest.mark.parametrize(
    ("code", "expected_code", "expected_action"),
    [
        (1026, "provider_job_rejected", GenerationAction.FIX_INPUT),
        (1027, "provider_job_rejected", GenerationAction.FIX_INPUT),
        (1004, "provider_job_configuration_rejected", GenerationAction.CONFIGURE_PROVIDER),
        (1008, "provider_job_configuration_rejected", GenerationAction.CONFIGURE_PROVIDER),
        (1002, "provider_job_failed_coded", GenerationAction.RETRY),
        (1000, "provider_job_failed_coded", GenerationAction.RETRY),
    ],
    ids=["1026-input", "1027-output", "1004-auth", "1008-balance", "1002-rate-limit", "1000-unknown"],
)
async def test_declared_code_sets_choose_the_action_and_nothing_is_retried(
    tmp_path, code, expected_code, expected_action
):
    """Only declared input codes ask for an input fix; undeclared codes keep code and message without claiming a repair."""
    response = {"task": {"status": "failed", "error": {"code": code, "message": f"provider says {code}"}}}
    with capture_http() as router, bounded_poll_clock():
        submit, poll = _routes(router, [httpx.Response(200, json=response)])
        with pytest.raises(ProviderJobRejectedError) as raised:
            await _backend().generate(_request(tmp_path, [("a.wav", WAV)]))
    assert submit.call_count == 1
    assert poll.call_count == 1
    assert raised.value.code == expected_code
    problem = problem_from_task_failure(encode_task_failure_message(raised.value))
    assert problem.code == expected_code
    assert problem.action is expected_action
    assert problem.params["provider_error_code"] == str(code)
    assert problem.params["provider_error_message"] == f"provider says {code}"


CREATE_ERROR_BODY = {
    "type": "error",
    "error": {
        "type": "invalid_request_error",
        "message": "invalid params, resolution not supported (2013)",
        "http_code": 400,
    },
    "request_id": "req-1",
}


async def test_create_http_error_body_surfaces_the_documented_message_once(tmp_path):
    """A 4xx create response is a deterministic refusal: one POST, reason read from ``error.message``."""
    with capture_http() as router, bounded_poll_clock():
        submit = router.post(f"{BASE}/v2/video_generation").mock(
            return_value=httpx.Response(400, json=CREATE_ERROR_BODY)
        )
        with pytest.raises(ProviderRejectedError) as raised:
            await _backend().generate(_request(tmp_path, []))
    assert submit.call_count == 1
    problem = problem_from_task_failure(encode_task_failure_message(raised.value))
    assert problem.code == "provider_rejected"
    assert problem.action is GenerationAction.FIX_INPUT
    assert "invalid params, resolution not supported (2013)" in problem.params["provider_reason"]


async def test_create_error_body_with_success_status_reads_error_message(tmp_path):
    """The same body behind a 2xx status has no task id: the submit ``error`` extract reads ``$.error.message``."""
    with capture_http() as router, bounded_poll_clock():
        submit = router.post(f"{BASE}/v2/video_generation").mock(
            return_value=httpx.Response(200, json=CREATE_ERROR_BODY)
        )
        with pytest.raises(RuntimeError, match=r"invalid params, resolution not supported \(2013\)") as raised:
            await _backend().generate(_request(tmp_path, []))
    assert submit.call_count == 1
    assert not isinstance(raised.value, ProviderJobRejectedError)


async def test_job_failure_message_is_redacted_and_bounded(tmp_path):
    secret_message = (
        "upstream echoed Bearer abcdefghijklmnop and failed to fetch https://cdn.test/a.wav?X-Amz-Signature=deadbeef&x=1 "
        + "x" * (PROVIDER_ERROR_MESSAGE_MAX_CHARS * 2)
    )
    response = {"task": {"status": "failed", "error": {"code": 1000, "message": secret_message}}}
    with capture_http() as router, bounded_poll_clock():
        _routes(router, [httpx.Response(200, json=response)])
        with pytest.raises(ProviderJobRejectedError) as raised:
            await _backend().generate(_request(tmp_path, [("a.wav", WAV)]))
    message = raised.value.params["provider_error_message"]
    assert "abcdefghijklmnop" not in message
    assert "deadbeef" not in message
    assert len(message) <= PROVIDER_ERROR_MESSAGE_MAX_CHARS
    assert message.endswith("…[truncated]")


async def test_uncoded_failure_keeps_the_legacy_text_path(tmp_path):
    """Without a provider code the stable generic failure (and its existing action) is unchanged."""
    response = {"task": {"status": "failed", "error": "quota exhausted"}}
    with capture_http() as router, bounded_poll_clock():
        _routes(router, [httpx.Response(200, json=response)])
        with pytest.raises(RuntimeError, match="quota exhausted") as raised:
            await _backend().generate(_request(tmp_path, []))
    assert not isinstance(raised.value, ProviderJobRejectedError)


async def test_submit_refusal_with_base_resp_code_is_structured(tmp_path):
    with capture_http() as router, bounded_poll_clock():
        submit = router.post(f"{BASE}/v2/video_generation").mock(
            return_value=httpx.Response(
                200, json={"base_resp": {"status_code": 2013, "status_msg": "invalid params, resolution"}}
            )
        )
        with pytest.raises(ProviderJobRejectedError) as raised:
            await _backend().generate(_request(tmp_path, []))
    assert submit.call_count == 1
    assert raised.value.params == {
        "provider_error_code": "2013",
        "provider_error_message": "invalid params, resolution",
        "stage": "submit",
    }


async def test_in_progress_and_network_failure_keep_the_same_job_without_resubmission(tmp_path):
    running = {"task": {"status": "running"}, "base_resp": {"status_code": 0, "status_msg": "success"}}
    done = {"task": {"status": "succeeded", "content": {"url": "https://cdn.test/h3.mp4"}}}
    with capture_http() as router, bounded_poll_clock():
        submit, poll = _routes(
            router,
            [
                httpx.Response(200, json=running),
                httpx.ConnectError("network down"),
                httpx.Response(200, json=running),
                httpx.Response(200, json=done),
            ],
        )
        result = await _backend().generate(_request(tmp_path, [("a.wav", WAV)]))
    assert submit.call_count == 1
    assert poll.call_count == 4
    assert {call.request.url.path for call in poll.calls} == {"/v2/query/video_generation/461931189367168"}
    assert result.task_id == "461931189367168"


async def test_wav_and_mp3_go_out_with_documented_mime_whatever_the_host_registry_says(tmp_path, monkeypatch):
    """Official H3 contract: ``data:audio/<format>;base64,...`` with lowercase wav / mp3."""
    aliases = {".wav": "audio/x-wav", ".mp3": "audio/mpeg"}
    real_guess = mimetypes.guess_type
    monkeypatch.setattr(
        mimetypes,
        "guess_type",
        lambda name, strict=True: (
            (aliases[Path(str(name)).suffix], None) if Path(str(name)).suffix in aliases else real_guess(name, strict)
        ),
    )
    done = {"task": {"status": "succeeded", "content": {"url": "https://cdn.test/h3.mp4"}}}
    with capture_http() as router, bounded_poll_clock():
        submit, _ = _routes(router, [httpx.Response(200, json=done)])
        await _backend().generate(_request(tmp_path, [("marcia.wav", WAV), ("jessica.mp3", MP3)]))
    body = request_json(submit.calls.last.request)
    content = body["content"]
    assert content[0] == {"type": "text", "text": "@图片1 talks to @图片2 [@音频1] [@音频2]"}
    images = [item["image_url"]["url"] for item in content if item["type"] == "image_url"]
    assert [base64.b64decode(url.partition(",")[2]) for url in images] == PNGS
    audio = [item["audio_url"]["url"] for item in content if item["type"] == "audio_url"]
    assert [url.partition(",")[0] for url in audio] == ["data:audio/wav;base64", "data:audio/mp3;base64"]
    # Speaker order and bytes preserved: decoded payloads keep the original sha256.
    assert [hashlib.sha256(base64.b64decode(url.partition(",")[2])).hexdigest() for url in audio] == [
        hashlib.sha256(WAV).hexdigest(),
        hashlib.sha256(MP3).hexdigest(),
    ]
    assert body["resolution"] == "2K"
    assert body["duration"] == 10
    assert body["ratio"] == "9:16"


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("jessica.mp3", WAV),
        ("marcia.wav", MP3),
        ("broken.wav", b"RIFF\x00\x00\x00\x00WAVEA"),
        ("noise.mp3", b"\x00" * 64),
    ],
    ids=["wav-bytes-named-mp3", "mp3-bytes-named-wav", "corrupt-wav", "corrupt-mp3"],
)
async def test_misleading_or_corrupt_audio_fails_before_any_request(tmp_path, name, content):
    with capture_http() as router, bounded_poll_clock():
        submit, poll = _routes(router, [])
        with pytest.raises(VideoCapabilityError) as raised:
            await _backend().generate(_request(tmp_path, [(name, content)]))
    assert raised.value.code == "video_reference_audio_format_unsupported"
    assert raised.value.params["name"] == name
    assert submit.call_count == 0
    assert poll.call_count == 0
    problem = problem_from_task_failure(encode_task_failure_message(raised.value))
    assert problem.action is GenerationAction.FIX_INPUT


def test_other_endpoints_do_not_opt_in():
    """Only H3 declares container_mime: other providers keep their existing MIME behaviour."""
    opted = [
        key
        for key, spec in ENDPOINT_REGISTRY.items()
        if spec.definition is not None
        and any("container_mime" in decl for decl in (spec.definition.get("inputs") or {}).values())
    ]
    assert opted == ["minimax-h3"]
