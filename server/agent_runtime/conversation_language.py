"""Per-message conversational context, separate from user-authored transcript content."""

from typing import Any

from lib.i18n import LOCALE_LANGUAGE_MAP, SUPPORTED_LOCALES, normalize_locale


def conversation_language_block(locale: str, message_uuid: str) -> dict[str, str]:
    """Bind application context to its CLI delivery identity for lossless history backfill."""
    language = LOCALE_LANGUAGE_MAP[normalize_locale(locale)]
    return {
        "type": "text",
        "text": (
            f'<arcreel-conversation-language message-id="{message_uuid}">\n'
            f"Reply language: {language}. This selects conversational replies only; preserve project/source "
            "creative language and existing content.\n"
            "</arcreel-conversation-language>"
        ),
    }


def user_content_without_language_context(
    blocks: list[dict[str, Any]], message_uuid: str | None
) -> list[dict[str, Any]]:
    """Remove only an exact application prefix bound to this message, retaining quoted lookalikes."""
    if (
        blocks
        and message_uuid
        and any(blocks[0] == conversation_language_block(locale, message_uuid) for locale in SUPPORTED_LOCALES)
    ):
        return blocks[1:]
    return blocks
