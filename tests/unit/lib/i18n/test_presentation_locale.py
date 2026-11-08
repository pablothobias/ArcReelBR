"""Presentation fallback is independent of project/source creative-language defaults."""

import pytest
from starlette.requests import Request

from lib.i18n import DEFAULT_LOCALE, _, normalize_locale
from server.i18n import get_locale


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("", "en"),
        ("pt-BR", "en"),
        ("xx", "en"),
        ("en-US", "en"),
        ("ZH-cn", "zh"),
        ("zh_CN", "zh"),
        ("vi-VN", "vi"),
        ("ru-RU", "ru"),
    ],
)
def test_request_runtime_and_catalog_agree(tag, expected):
    request = Request({"type": "http", "headers": [(b"accept-language", tag.encode())]})
    assert DEFAULT_LOCALE == "en"
    assert normalize_locale(tag) == expected
    assert get_locale(request) == expected
    assert _("deleted_provider_display_name", locale=tag) == _("deleted_provider_display_name", locale=expected)


def test_missing_translation_falls_back_to_english(monkeypatch):
    from lib.i18n import MESSAGES

    monkeypatch.delitem(MESSAGES["zh"], "deleted_provider_display_name")
    assert _("deleted_provider_display_name", locale="zh") == MESSAGES["en"]["deleted_provider_display_name"]
