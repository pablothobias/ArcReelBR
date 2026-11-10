"""Byte-identified reference-audio containers (``inputs.*.container_mime``) and provider ``error_code`` extraction."""

from __future__ import annotations

import base64
import hashlib

import pytest
from definition_factories import custom_endpoint_definition

from arcreel_market_core.endpoint_definition import (
    AssetData,
    DefinitionErrorCode,
    detect_audio_container,
    encode_inputs,
    extract_value,
    validate_definition,
)
from arcreel_market_core.endpoint_definition.template_engine import TemplateRenderError

WAV = (
    b"RIFF\x28\x00\x00\x00WAVE"
    b"fmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00"
    b"data\x04\x00\x00\x00\x01\x02\x03\x04"
)
# MPEG-1 Layer III, 128 kbit/s, 44.1 kHz: 417-byte frames.
_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413
MP3 = _FRAME * 2
MP3_WITH_ID3 = b"ID3\x04\x00\x00\x00\x00\x00\x05" + b"TAGXX" + MP3
CONTAINER_MIME = {"wav": "audio/wav", "mp3": "audio/mp3"}
AUDIO_DECL = {"voice": {"source": "reference_audio_files", "encoding": "data_uri", "container_mime": CONTAINER_MIME}}


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (WAV, "wav"),
        (MP3, "mp3"),
        (MP3_WITH_ID3, "mp3"),
        (_FRAME, "mp3"),
        (b"RIFF\x00\x00\x00\x00WAVEA", None),  # header only: no fmt/data chunks
        (b"RIFF\x28\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01", None),  # truncated fmt chunk
        (_FRAME[:100], None),  # truncated first frame
        (b"\xff\xfb\x90\x00" + b"\x00" * 413 + b"garbage!", None),  # second frame header is not a frame
        (b"ID3\x04\x00\x00\x00\x00\x00\x05TAGXXnot audio at all", None),
        (b"\x89PNG\r\n\x1a\n", None),
        (b"", None),
    ],
)
def test_container_detection_reads_structure_not_names(content: bytes, expected: str | None):
    assert detect_audio_container(content) == expected


@pytest.mark.parametrize(
    ("guessed_mime", "content", "expected_mime"),
    [
        ("audio/x-wav", WAV, "audio/wav"),
        ("audio/wave", WAV, "audio/wav"),
        ("audio/vnd.wave", WAV, "audio/wav"),
        ("audio/mpeg", MP3, "audio/mp3"),
        ("audio/mpeg3", MP3_WITH_ID3, "audio/mp3"),
        ("application/octet-stream", MP3, "audio/mp3"),
    ],
)
def test_declared_container_mime_replaces_any_host_guess_and_keeps_bytes(guessed_mime, content, expected_mime):
    encoded = encode_inputs(AUDIO_DECL, {"reference_audio_files": [AssetData(guessed_mime, content)]})
    [uri] = encoded["voice"]
    prefix, _, payload = uri.partition(",")
    assert prefix == f"data:{expected_mime};base64"
    assert hashlib.sha256(base64.b64decode(payload)).digest() == hashlib.sha256(content).digest()


def test_two_speakers_keep_their_order_and_own_container():
    encoded = encode_inputs(
        AUDIO_DECL,
        {"reference_audio_files": [AssetData("audio/x-wav", WAV, "a.wav"), AssetData("audio/mpeg", MP3, "b.mp3")]},
    )
    assert [uri.split(";")[0] for uri in encoded["voice"]] == ["data:audio/wav", "data:audio/mp3"]


@pytest.mark.parametrize(
    ("asset", "code"),
    [
        (AssetData("audio/mpeg", WAV, "speaker.mp3"), DefinitionErrorCode.ASSET_CONTAINER_EXTENSION_MISMATCH),
        (AssetData("audio/x-wav", MP3, "speaker.wav"), DefinitionErrorCode.ASSET_CONTAINER_EXTENSION_MISMATCH),
        (
            AssetData("audio/x-wav", b"RIFF\x00\x00\x00\x00WAVEA", "speaker.wav"),
            DefinitionErrorCode.ASSET_CONTAINER_UNRECOGNIZED,
        ),
        (AssetData("audio/ogg", b"OggS\x00\x02", "speaker.ogg"), DefinitionErrorCode.ASSET_CONTAINER_UNRECOGNIZED),
    ],
)
def test_misleading_extension_or_corrupt_bytes_fail_before_any_request(asset, code):
    with pytest.raises(TemplateRenderError) as raised:
        encode_inputs(AUDIO_DECL, {"reference_audio_files": [asset]})
    assert raised.value.code is code
    assert raised.value.message.params["input"] == "voice"


def test_container_missing_from_the_map_is_refused_never_relabelled():
    """An MP3 must never be sent as WAV: a WAV-only map refuses MP3 bytes."""
    declaration = {"voice": {**AUDIO_DECL["voice"], "container_mime": {"wav": "audio/wav"}}}
    with pytest.raises(TemplateRenderError) as raised:
        encode_inputs(declaration, {"reference_audio_files": [AssetData("audio/mpeg", MP3, "b.mp3")]})
    assert raised.value.code is DefinitionErrorCode.ASSET_CONTAINER_UNSUPPORTED
    assert raised.value.message.params["detected"] == "mp3"


def test_inputs_without_the_declaration_keep_the_callers_mime():
    encoded = encode_inputs(
        {"voice": {"source": "reference_audio_files", "encoding": "data_uri"}},
        {"reference_audio_files": [AssetData("audio/x-wav", b"anything", "a.wav")]},
    )
    assert encoded["voice"] == ["data:audio/x-wav;base64," + base64.b64encode(b"anything").decode()]


def test_validator_accepts_error_code_and_rejects_container_mime_on_images():
    definition = custom_endpoint_definition()
    definition["poll"]["extract"]["error_code"] = {"paths": ["$.error.code"], "accept": "scalar"}
    definition["submit"]["extract"]["error_code"] = ["$.error.code"]
    assert validate_definition(definition).errors == ()

    definition["inputs"]["first_frame"]["container_mime"] = {"wav": "audio/wav"}
    codes = [issue.code for issue in validate_definition(definition).errors]
    assert codes == [DefinitionErrorCode.CONTAINER_MIME_SOURCE_NOT_AUDIO]


def test_schema_rejects_containers_without_a_detector():
    definition = custom_endpoint_definition()
    definition["inputs"]["first_frame"]["container_mime"] = {"ogg": "audio/ogg"}
    assert validate_definition(definition).errors


def test_object_error_is_skipped_by_string_extraction_while_code_is_a_scalar():
    """MiniMax H3 reports ``task.error`` as an object: read its message and code, never ``str(dict)``."""
    body = {"task": {"status": "failed", "error": {"code": 2013, "message": 'audio format ".mpeg" not allowed'}}}
    assert extract_value(["$.task.error"], body) is None
    assert extract_value(["$.task.error.message", "$.task.error"], body) == 'audio format ".mpeg" not allowed'
    assert extract_value({"paths": ["$.task.error.code"], "accept": "scalar"}, body) == 2013
