"""Credentialed declarative/ComfyUI requests never leave the origin their URL template fixes (security finding B1).

No network: respx intercepts every request, and undeclared routes raise.
"""

from __future__ import annotations

import copy
from pathlib import Path

import httpx
import pytest

from arcreel_market_core.video_backend_contract import VideoGenerationRequest
from lib.custom_provider.comfyui.comfyui_client import ComfyuiClient
from lib.custom_provider.comfyui.failures import ComfyuiError
from lib.custom_provider.credential_origin import (
    CREDENTIAL_HOST_MISMATCH,
    credential_origin_matches,
    strict_origin,
    template_origin,
)
from lib.custom_provider.declarative_backend import DeclarativeRuntimeError, DeclarativeVideoBackend
from lib.custom_provider.endpoints import ENDPOINT_REGISTRY
from lib.generation.generation_result import GenerationAction, problem_from_task_failure
from lib.generation.task_failure_encoding import encode_task_failure_message
from tests.fakes import bounded_poll_clock
from tests.http_capture import capture_http

BASE = "https://api.minimax.io"
CONTEXT = {"base_url": BASE, "override_base_url": BASE}


@pytest.mark.parametrize(
    ("template", "rendered", "allowed"),
    [
        ("{{ base_url }}/v2/video_generation", f"{BASE}/v2/video_generation", True),
        ("{{ base_url }}/v2/query/{{ task_id }}", f"{BASE}/v2/query/@x.invalid", True),
        ("https://api.minimax.io/v1/files?id={{ result_id }}", f"{BASE}/v1/files?id=abc", True),
        ("https://api.minimax.io{{ prompt }}", "https://api.minimax.io@collector.example/steal", False),
        ("{{ base_url }}{{ task_id }}", "https://api.minimax.io@x.invalid", False),
        ("{{ base_url }}{{ task_id }}", "https://api.minimax.io.x.invalid/q", False),
        ("{{ base_url }}{{ task_id }}", "https://api.minimax.io:8443/q", False),
        ("https://{{ region }}.minimax.io/v2", "https://api.minimax.io/v2", False),
        ("{{ prompt }}/v2", "https://api.minimax.io/v2", False),
        ("{{ base_url }}/q", "https://api.minimax.io\\@collector.example/q", False),
    ],
    ids=[
        "base-url",
        "task-id-in-path",
        "literal-authority",
        "prompt-userinfo",
        "task-id-userinfo",
        "task-id-subdomain",
        "task-id-port",
        "placeholder-in-host",
        "free-text-origin",
        "backslash-userinfo",
    ],
)
def test_rendered_origin_must_equal_the_template_origin(template, rendered, allowed):
    assert credential_origin_matches(template, rendered, CONTEXT) is allowed


def test_origins_need_both_parsers_to_agree():
    assert strict_origin("https://API.minimax.io:443/x") == ("https", "api.minimax.io", 443)
    assert strict_origin("ftp://api.minimax.io/") is None
    assert template_origin("{{ base_url }}/x", {"base_url": ""}) is None


def _backend(definition: dict) -> DeclarativeVideoBackend:
    return DeclarativeVideoBackend(
        api_key="sk-test-secret-key-123456",
        base_url=BASE,
        model="MiniMax-H3",
        definition=definition,
        provider="minimax",
    )


def _h3(**urls: str) -> dict:
    definition = copy.deepcopy(dict(ENDPOINT_REGISTRY["minimax-h3"].definition or {}))
    for section, url in urls.items():
        definition[section]["url"] = url
    return definition


def _request(tmp_path: Path, prompt: str) -> VideoGenerationRequest:
    return VideoGenerationRequest(
        prompt=prompt, output_path=tmp_path / "out.mp4", duration_seconds=10, aspect_ratio="9:16", resolution="768p"
    )


async def test_prompt_rendered_into_the_host_is_refused_before_any_request(tmp_path):
    backend = _backend(_h3(submit="https://api.minimax.io{{ prompt }}"))
    with capture_http() as router, bounded_poll_clock():
        with pytest.raises(DeclarativeRuntimeError) as raised:
            await backend.generate(_request(tmp_path, "@collector.example/steal"))
        assert router.calls.call_count == 0
    assert raised.value.code == CREDENTIAL_HOST_MISMATCH
    assert "collector" not in str(raised.value)
    problem = problem_from_task_failure(encode_task_failure_message(raised.value))
    assert problem.code == CREDENTIAL_HOST_MISMATCH
    assert problem.action is GenerationAction.CONFIGURE_PROVIDER


async def test_provider_task_id_cannot_move_the_poll_host(tmp_path):
    backend = _backend(_h3(poll="{{ base_url }}{{ task_id }}"))
    with capture_http() as router, bounded_poll_clock():
        submit = router.post(f"{BASE}/v2/video_generation").mock(
            return_value=httpx.Response(200, json={"task_id": "@x.invalid", "base_resp": {"status_code": 0}})
        )
        with pytest.raises(DeclarativeRuntimeError) as raised:
            await backend.generate(_request(tmp_path, "hello"))
        assert submit.call_count == 1
        assert router.calls.call_count == 1  # nothing reached x.invalid
    assert raised.value.code == CREDENTIAL_HOST_MISMATCH


async def test_task_id_in_the_path_and_literal_hosts_still_work(tmp_path):
    backend = _backend(_h3(submit="https://api.minimax.io/v2/video_generation"))
    done = {"task": {"status": "succeeded", "content": {"url": "https://cdn.test/h3.mp4"}}}
    with capture_http() as router, bounded_poll_clock():
        router.post(f"{BASE}/v2/video_generation").mock(
            return_value=httpx.Response(200, json={"task_id": "@x.invalid", "base_resp": {"status_code": 0}})
        )
        poll = router.get(url__regex=rf"^{BASE}/v2/query/video_generation/.+").mock(
            return_value=httpx.Response(200, json=done)
        )
        router.get(url__regex=r"^https://cdn\.test/").mock(return_value=httpx.Response(200, content=b"mp4"))
        result = await backend.generate(_request(tmp_path, "hello"))
        assert poll.call_count == 1
        assert {call.request.url.host for call in router.calls} == {"api.minimax.io", "cdn.test"}
    assert result.task_id == "@x.invalid"


def test_comfyui_credentials_stay_on_the_configured_origin():
    client = ComfyuiClient(
        base_url="https://comfy.example",
        api_key="k",
        definition={"auth": {"headers": {"Authorization": "Bearer {{ api_key }}"}}},
    )
    assert httpx.URL(client._authed_url("/history/@x.invalid")).host == "comfy.example"
    with pytest.raises(ComfyuiError) as raised:
        client._authed_url("@x.invalid/history")
    assert raised.value.code == CREDENTIAL_HOST_MISMATCH
