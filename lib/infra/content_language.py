"""Project creative-language codes, independent of interface locales."""

from typing import Annotated, Literal, get_args

from pydantic import BeforeValidator

ContentLanguageCode = Literal["zh", "en", "vi", "ru", "pt-BR"]
CONTENT_LANGUAGE_CODES = get_args(ContentLanguageCode)


def normalize_content_language(value: object) -> str:
    """Normalize explicit supported codes; retain the Brazilian region distinction."""
    if not isinstance(value, str):
        raise ValueError("source_language must be a supported language code")
    code = value.strip().replace("_", "-").lower()
    normalized = "pt-BR" if code == "pt-br" else code
    if normalized not in CONTENT_LANGUAGE_CODES:
        raise ValueError(f"source_language must be one of {CONTENT_LANGUAGE_CODES}")
    return normalized


def is_brazilian_portuguese(value: object) -> bool:
    """Recognize supported Brazilian Portuguese spellings without inferring a language."""
    return isinstance(value, str) and value.strip().replace("_", "-").lower() == "pt-br"


ContentLanguage = Annotated[ContentLanguageCode, BeforeValidator(normalize_content_language)]
