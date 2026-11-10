"""Shared character voice-reference declarations for embedded and remote MCP hosts (TTS voices, samples, binding, inspection)."""

from server.agent_toolset.declaration import BLOCKED, READ_CHECK, ToolDeclaration
from server.agent_toolset.media_generation import generation_tool
from server.media_tools.voice_references import (
    ConfirmVoiceSampleRequest,
    GenerateVoiceSampleRequest,
    InspectVoiceReferenceRequest,
    ListTtsVoicesRequest,
    ListVoiceSamplesRequest,
    confirm_voice_sample,
    generate_voice_sample,
    inspect_voice_reference,
    list_tts_voices,
    list_voice_samples,
)

_MIGRATION_READ_NOTE = (
    " If project-data upgrade failed, returns project_migration_failed; repair according to its details and call "
    "retry_project_migration."
)

LIST_TTS_VOICES = ToolDeclaration(
    name="list_tts_voices",
    description=(
        "List the project's effective TTS backend (provider_id, model) and the voices that backend actually offers, "
        "for character voice-reference samples. Voices are discovered from the backend, not a fixed list; "
        "configured=false means no audio provider resolves for the project. Also returns the sample text limit and "
        "reference-audio limits (2-10 seconds, size cap). Read-only: no task, provider call or write."
        + _MIGRATION_READ_NOTE
    ),
    request_model=ListTtsVoicesRequest,
    migration=READ_CHECK,
    domain_key="tts_voices",
    handler=list_tts_voices,
)

GENERATE_VOICE_SAMPLE = generation_tool(
    name="generate_voice_sample",
    description=(
        "Generate a TTS preview sample of an explicit voice speaking explicit text for one character, as a candidate "
        "reference audio (paid generation through the native voice_sample task and audio lane). Requires character, "
        "voice (from list_tts_voices) and text; there is no narrator or project-voice fallback. Do not use "
        "generate_narration_audio for character dialogue samples. preview=true validates the same voice, backend and "
        "text and returns voice_sample_quote without any task or provider call: estimated_cost.amount is null with "
        "unpriced_reason when the price cannot be computed before synthesis (unknown, not free; never present it as "
        "zero or as a cap). preview=false submits one sample. The sample is NOT bound to the character: audition it "
        "(describe_media kind=voice_sample, inspect_voice_reference), then bind it with confirm_voice_sample. Every "
        "sample keeps its own file, so earlier unconfirmed samples are never overwritten. If the character already "
        "has an active sample task, returns voice_sample_in_progress with its task_id instead of submitting. "
        "Executed samples are validated (2-10 seconds, size cap); a validation failure fails the task, and its "
        "recorded provider cost still appears in list_voice_samples. If the connection drops, recover the sample "
        "with list_voice_samples; do not regenerate to recover it. Terminal generation_result reports the task_id "
        "under the character name."
    ),
    request_model=GenerateVoiceSampleRequest,
    handler=generate_voice_sample,
)

LIST_VOICE_SAMPLES = ToolDeclaration(
    name="list_voice_samples",
    description=(
        "List character voice samples recorded for this project from durable task records, newest first, optionally "
        "for one character: task_id, character (and whether it still exists), status, voice, text, provider/model, "
        "recorded duration, media state/format/MIME/size/sha256, recorded provider cost (null amounts are unpriced, "
        "and samples with no recorded call say so), creation time, failure code, whether the sample is the bytes "
        "currently bound as the character's reference, and whether it is confirmable. Survives reconnects and "
        "restarts. Read-only: no task, provider call or write." + _MIGRATION_READ_NOTE
    ),
    request_model=ListVoiceSamplesRequest,
    migration=READ_CHECK,
    domain_key="voice_samples",
    handler=list_voice_samples,
)

CONFIRM_VOICE_SAMPLE = ToolDeclaration(
    name="confirm_voice_sample",
    description=(
        "Bind a succeeded voice sample (by task_id) as the character's reference audio through the native "
        "confirmation transaction; the sample's bytes are installed unchanged, with no TTS call, no new task and no "
        "client upload. Refuses tasks of another project, character or task type (task_not_found), unfinished "
        "samples (voice_sample_not_ready), missing files (voice_sample_file_missing), altered files "
        "(voice_sample_content_changed) and renamed or removed characters (character_not_found). Pass "
        "expected_reference_sha256 (or expect_unbound=true) from the last inspection to refuse with "
        "voice_reference_revision_conflict if the binding changed meanwhile. Idempotent: confirming the sample already "
        "bound returns already_bound=true without writing. Use upload_reference(kind=character_audio) for user files."
    ),
    request_model=ConfirmVoiceSampleRequest,
    migration=BLOCKED,
    domain_key="voice_sample_confirmation",
    handler=confirm_voice_sample,
)

INSPECT_VOICE_REFERENCE = ToolDeclaration(
    name="inspect_voice_reference",
    description=(
        "Inspect isolated voice-reference audio: a character's currently bound reference (character) or a sample "
        "(task_id). Returns format, MIME type, size, sha256, measured container/codec/duration (or an explicit "
        "unavailable reason), whether it fits reference limits, provenance (task, voice, text, provider/model when "
        "recorded; unknown for uploads) and whether it is the bound reference. transcribe=true with language also "
        "runs local blind ASR without supplying the sample text to the recognizer; without the speech-review extra or "
        "a local model it returns an explicit limitation and never downloads models or calls paid APIs. A transcript "
        "proves neither voice identity, acting, emotion nor lip sync, and is not a human listening review. Read-only: "
        "no task, provider call or write. Bytes are retrieved with describe_media." + _MIGRATION_READ_NOTE
    ),
    request_model=InspectVoiceReferenceRequest,
    migration=READ_CHECK,
    domain_key="voice_reference_inspection",
    handler=inspect_voice_reference,
)

VOICE_REFERENCE_TOOLS = (
    LIST_TTS_VOICES,
    GENERATE_VOICE_SAMPLE,
    LIST_VOICE_SAMPLES,
    CONFIRM_VOICE_SAMPLE,
    INSPECT_VOICE_REFERENCE,
)

__all__ = ["VOICE_REFERENCE_TOOLS"]
