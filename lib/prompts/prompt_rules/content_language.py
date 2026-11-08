"""Output-language policy for explicit Brazilian content projects."""

from lib.infra.content_language import is_brazilian_portuguese


def prompt_output_language(value: str) -> str:
    """Split technical prose from literal speech only for Brazilian projects."""
    if not is_brazilian_portuguese(value):
        return value
    return (
        "English for technical directions (camera, staging, lighting, visual descriptions, "
        "image/video prompts and voice-performance instructions), and Brazilian Portuguese (pt-BR) "
        "for creative story content, dialogue, narration, subtitles and visible story text. "
        "Copy intended Portuguese speech and subtitle text verbatim from the approved source or script, "
        "including accents, punctuation and speaker attribution; never translate spoken quotations. Preserve source anchors and asset-reference names verbatim. "
        "In mixed video-prompt bodies, write technical prose in English and keep quoted speech in Portuguese"
    )
