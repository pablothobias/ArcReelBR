"""Provider error code classification declared on ``extract.error_code`` and the shared resolution options."""

from __future__ import annotations

import copy

import pytest

from arcreel_market_core.endpoint_definition import (
    DefinitionErrorCode,
    classify_provider_error_code,
    declarative_resolution_options,
    resolution_suggestion,
    validate_definition,
)

SPEC = {
    "paths": ["$.task.error.code"],
    "accept": "scalar",
    "fix_input_codes": ["2013", "1026"],
    "configure_codes": ["1004"],
}


@pytest.mark.parametrize(
    ("spec", "code", "expected"),
    [
        (SPEC, "2013", "fix_input"),
        (SPEC, "1004", "configure"),
        (SPEC, "1002", "unclassified"),
        ({"paths": ["$.code"], "accept": "scalar"}, "2013", "unclassified"),
        (["$.code"], "2013", "unclassified"),
        (None, "2013", "unclassified"),
    ],
    ids=["fix-input", "configure", "undeclared", "no-sets", "shorthand", "absent"],
)
def test_classification_follows_declared_sets_only(spec, code, expected):
    assert classify_provider_error_code(spec, code) == expected


def _definition(error_code: object) -> dict:
    return {
        "kind": "declarative",
        "schema_version": "1.2.0",
        "meta": {"name": "x", "author": "x", "version": "1.0.0"},
        "auth": {"headers": {"Authorization": "Bearer {{ api_key }}"}},
        "submit": {
            "method": "POST",
            "url": "{{ base_url }}/submit",
            "body": {"model": "{{ model }}", "prompt": "{{ prompt }}"},
            "extract": {"task_id": ["$.id"]},
        },
        "poll": {
            "method": "GET",
            "url": "{{ base_url }}/tasks/{{ task_id }}",
            "extract": {
                "status": ["$.status"],
                "video_url": ["$.url"],
                "error": ["$.error.message"],
                "error_code": error_code,
            },
        },
    }


def test_schema_and_validator_accept_disjoint_code_sets():
    diagnostics = validate_definition(_definition(copy.deepcopy(SPEC)))
    assert diagnostics.errors == ()


def test_overlapping_code_sets_are_rejected():
    spec = dict(SPEC, configure_codes=["1004", "2013"])
    diagnostics = validate_definition(_definition(spec))
    assert [(issue.path, issue.code, issue.params) for issue in diagnostics.errors] == [
        ("poll.extract.error_code", DefinitionErrorCode.ERROR_CODE_SETS_OVERLAP, {"codes": "2013"})
    ]


@pytest.mark.parametrize("bad", [[], ["has space"], [2013]], ids=["empty", "pattern", "not-string"])
def test_malformed_code_sets_fail_the_schema(bad):
    diagnostics = validate_definition(_definition(dict(SPEC, fix_input_codes=bad)))
    assert diagnostics.errors


def test_resolution_options_are_the_renderer_keys_narrowed_by_model_facts():
    definition = {"enum_maps": {"resolution": {"768p": "768P", "2k": "2K"}}}
    assert declarative_resolution_options(definition) == ("768p", "2k")
    assert declarative_resolution_options(definition, ["768p"]) == ("768p",)
    # Provider-side spellings in model facts never replace the renderer's keys.
    assert declarative_resolution_options(definition, ["768P", "2K"]) == ("768p", "2k")
    assert declarative_resolution_options({"enum_maps": {}}) is None
    assert resolution_suggestion("2K", ("768p", "2k")) == "2k"
    assert resolution_suggestion("4k", ("768p", "2k")) is None


@pytest.mark.parametrize(
    ("url", "offending"),
    [
        ("{{ base_url }}/v2/query/{{ task_id }}", None),
        ("{{ override_base_url }}/v2", None),
        ("https://api.example.com/v1/{{ task_id }}", None),
        ("https://api.example.com?id={{ task_id }}", None),
        ("https://api.example.com{{ prompt }}", "prompt"),
        ("https://{{ region }}.example.com/v1", "region"),
        # Text right after the origin placeholder extends the host: only /, ? or # may follow it.
        ("{{ base_url }}{{ task_id }}", "task_id"),
        ("{{ base_url }}.evil.example/x", "base_url"),
        ("{{ base_url }}?id={{ task_id }}", None),
        ("{{ base_url }}", None),
        ("{{ prompt }}/v1", "prompt"),
    ],
)
def test_url_authority_placeholders_are_found(url, offending):
    from arcreel_market_core.endpoint_definition import url_authority_violation

    assert url_authority_violation(url) == offending


def test_validator_rejects_a_placeholder_inside_the_url_authority():
    definition = _definition(copy.deepcopy(SPEC))
    definition["submit"]["url"] = "https://api.example.com{{ prompt }}"
    diagnostics = validate_definition(definition)
    assert [(issue.path, issue.code) for issue in diagnostics.errors] == [
        ("submit.url", DefinitionErrorCode.URL_AUTHORITY_PLACEHOLDER)
    ]
