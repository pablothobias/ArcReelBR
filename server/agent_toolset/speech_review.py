"""Shared speech-review declaration for embedded and remote MCP hosts."""

from server.agent_toolset.declaration import BLOCKED, ToolDeclaration
from server.media_tools.speech_review import ReviewSpeechRequest, review_speech

SPEECH_REVIEW_TOOLS = (
    ToolDeclaration(
        name="review_speech",
        description=(
            "Review actual selected media using local blind ASR, without supplying canonical dialogue to the recognizer. "
            "No paid API calls or model downloads. Requires speech-review extra and ARCREEL_SPEECH_REVIEW_MODEL. "
            "Current-presentation materialization precedes recognition and may persist subtitle/presentation/manifest artifacts, "
            "including when ASR is unavailable. apply_timing=false skips new measured-timing application, "
            "retains still-valid existing measurements and does not imply zero writes. "
            "Returns actual transcript, word times/confidence, canonical text comparison and timing blockers. "
            "Set apply_timing=true only to apply eligible measured subtitle intervals through the native presentation service; "
            "preserves canonical words/speakers, validates media/text identity, and feeds preview/export/final-cut consumers. "
            "Mismatch or uncertain words never apply. Historical versions must be selected before applying timing. "
            "Lip sync, emotion and speaker identity remain not_assessed: do not claim audiovisual acceptance from ASR. "
            "A muted native track cannot establish post-production voiceover timing."
        ),
        request_model=ReviewSpeechRequest,
        migration=BLOCKED,
        domain_key="speech_review",
        handler=review_speech,
    ),
)
