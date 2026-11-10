"""One credential-host rule, every caller: the same hostile URLs are refused everywhere (security finding B1).

Callers: the definition validator, the configuration-time credential checks (``global_config``), the send-time
declarative guard and the ComfyUI client. Each row pairs a URL template with a URL a hostile value could render.
"""

from __future__ import annotations

import pytest

from arcreel_market_core.endpoint_definition import (
    DefinitionErrorCode,
    url_authority_is_fixed,
    validate_definition,
)
from lib.custom_provider.comfyui.comfyui_client import ComfyuiClient
from lib.custom_provider.comfyui.failures import ComfyuiError
from lib.custom_provider.credential_origin import CREDENTIAL_HOST_MISMATCH, credential_origin_matches, origin_text
from server.services.configuration import global_config

BASE = "https://api.minimax.io"
CONTEXT = {"base_url": BASE, "override_base_url": BASE}

HOSTILE = [
    ("at", "https://api.minimax.io{{ x }}", f"{BASE}@evil.example/x"),
    ("percent-40", "{{ base_url }}{{ x }}", f"{BASE}%40evil.example/x"),
    ("dot", "{{ base_url }}.evil.example/x", f"{BASE}.evil.example/x"),
    ("port", "{{ base_url }}:8443/x", f"{BASE}:8443/x"),
    ("backslash-at", "{{ base_url }}\\@evil.example/x", f"{BASE}\\@evil.example/x"),
    ("fullwidth-at", "{{ base_url }}＠evil.example/x", f"{BASE}＠evil.example/x"),
    ("tab", "{{ base_url }}\t@evil.example/x", f"{BASE}\t@evil.example/x"),
    ("idn", "https://{{ x }}.example/x", f"{BASE}@évil.example/x"),
    ("scheme-relative", "//{{ x }}/x", "//evil.example/x"),
    ("base-then-placeholder", "{{ base_url }}{{ x }}", f"{BASE}evil.example/x"),
]
BENIGN = [
    ("base-path", "{{ base_url }}/v2/{{ x }}", f"{BASE}/v2/@evil.example"),
    ("literal-query", "https://api.minimax.io/v1?id={{ x }}", f"{BASE}/v1?id=@evil.example"),
]


def _definition(url: str) -> dict:
    return {
        "kind": "declarative",
        "schema_version": "1.3.0",
        "meta": {"name": "x", "author": "x", "version": "1.0.0"},
        "auth": {"headers": {"Authorization": "Bearer {{ api_key }}"}},
        "submit": {
            "method": "POST",
            "url": url,
            "body": {"model": "{{ model }}", "prompt": "{{ prompt }}", "x": "{{ prompt }}"},
            "extract": {"task_id": ["$.id"]},
        },
        "poll": {
            "method": "GET",
            "url": "{{ base_url }}/tasks/{{ task_id }}",
            "extract": {"status": ["$.status"], "video_url": ["$.url"]},
        },
    }


def _authority_errors(url: str) -> list:
    return [
        issue
        for issue in validate_definition(_definition(url)).errors
        if issue.code is DefinitionErrorCode.URL_AUTHORITY_PLACEHOLDER
    ]


def _comfyui_path(rendered: str) -> str | None:
    return rendered[len(BASE) :] if rendered.startswith(BASE) else None


@pytest.mark.parametrize(("template", "rendered"), [row[1:] for row in HOSTILE], ids=[row[0] for row in HOSTILE])
def test_every_caller_refuses_the_same_hostile_urls(template: str, rendered: str) -> None:
    # Validator and configuration share one authority predicate.
    assert _authority_errors(template)
    assert not url_authority_is_fixed(template)
    assert not global_config.url_authority_is_fixed(template)
    # Configuration-time origin check (credential reuse).
    with pytest.raises(global_config.GlobalConfigRefused) as refused:
        global_config.ensure_same_origin(origin_text(BASE) or "", rendered, ref="minimax")
    assert refused.value.code in {"credential_host_mismatch", "base_url_invalid"}
    # Send-time guard: refused by the template rule, and by the origin parser even under a fixed template.
    assert not credential_origin_matches(template, rendered, CONTEXT)
    assert not credential_origin_matches("{{ base_url }}/x", rendered, CONTEXT)
    # ComfyUI appends paths to its configured base URL.
    if (path := _comfyui_path(rendered)) is not None:
        client = ComfyuiClient(base_url=BASE, api_key="k", definition={})
        with pytest.raises(ComfyuiError) as comfy:
            client._authed_url(path)
        assert comfy.value.code == CREDENTIAL_HOST_MISMATCH


@pytest.mark.parametrize(("template", "rendered"), [row[1:] for row in BENIGN], ids=[row[0] for row in BENIGN])
def test_every_caller_accepts_values_after_a_fixed_authority(template: str, rendered: str) -> None:
    assert not _authority_errors(template)
    assert global_config.url_authority_is_fixed(template)
    global_config.ensure_same_origin(origin_text(BASE) or "", rendered, ref="minimax")
    assert credential_origin_matches(template, rendered, CONTEXT)
    path = _comfyui_path(rendered)
    assert path is not None
    ComfyuiClient(base_url=BASE, api_key="k", definition={})._authed_url(path)
