"""Identify reference-audio containers from bytes for ``inputs.*.container_mime`` declarations.

Endpoints that declare ``container_mime`` opt in to byte-based identification: the emitted data-URI MIME follows the real
container and the declared token, never the file extension or the host's ``mimetypes`` registry (which reports
``audio/mpeg`` / ``audio/x-wav`` / ``audio/wave`` depending on the environment). Only header and frame structure are
checked; bytes are never transcoded or rewritten, so the decoded payload keeps the original digest.

Recognition is conservative: a WAV needs a RIFF/WAVE header with both ``fmt `` and ``data`` chunks, an MP3 needs a
valid MPEG audio Layer III frame header (after an optional ID3v2 tag) and, when more bytes follow, a second valid frame
at the computed offset. Anything else is unrecognized, so a corrupt or mislabeled file fails before submission.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

AudioContainer = Literal["wav", "mp3"]

#: Containers this module can identify; ``container_mime`` keys are restricted to this set by the schema.
SUPPORTED_AUDIO_CONTAINERS: tuple[AudioContainer, ...] = ("wav", "mp3")

#: File suffixes that unambiguously claim one container; a different detected container means a misleading extension.
_SUFFIX_CONTAINERS: Mapping[str, AudioContainer] = {".wav": "wav", ".wave": "wav", ".mp3": "mp3"}

# MPEG audio Layer III bitrate tables (kbit/s) indexed by the 4-bit bitrate index; 0 (free) and 15 (bad) are invalid.
_MPEG1_L3_KBPS = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0)
_MPEG2_L3_KBPS = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0)
# Sample rates (Hz) by version bits: 3 = MPEG1, 2 = MPEG2, 0 = MPEG2.5; index 3 is reserved.
_SAMPLE_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}


def detect_audio_container(content: bytes) -> AudioContainer | None:
    """Return the container these bytes actually hold, or ``None`` when unrecognized or structurally corrupt."""
    if _is_wav(content):
        return "wav"
    if _is_mp3(content):
        return "mp3"
    return None


def suffix_container(name: str | None) -> AudioContainer | None:
    """Container claimed by a file name's suffix, or ``None`` when the name carries no recognized audio suffix."""
    if not name:
        return None
    dot = name.rfind(".")
    if dot < 0:
        return None
    return _SUFFIX_CONTAINERS.get(name[dot:].lower())


def _is_wav(content: bytes) -> bool:
    if len(content) < 12 or content[:4] != b"RIFF" or content[8:12] != b"WAVE":
        return False
    offset = 12
    seen_fmt = False
    while offset + 8 <= len(content):
        chunk_id = content[offset : offset + 4]
        size = int.from_bytes(content[offset + 4 : offset + 8], "little")
        if chunk_id == b"fmt ":
            if size < 16 or offset + 8 + size > len(content):
                return False
            seen_fmt = True
        elif chunk_id == b"data":
            # Streaming writers may leave the data size unset; the chunk itself must still follow a format chunk.
            return seen_fmt
        offset += 8 + size + (size & 1)
    return False


def _id3v2_length(content: bytes) -> int:
    """Total ID3v2 tag length (header, body and optional footer), or 0 when there is no tag."""
    if len(content) < 10 or content[:3] != b"ID3":
        return 0
    size_bytes = content[6:10]
    if any(byte & 0x80 for byte in size_bytes):
        return -1
    size = 0
    for byte in size_bytes:
        size = (size << 7) | byte
    footer = 10 if content[5] & 0x10 else 0
    return 10 + size + footer


def _frame_length(content: bytes, offset: int) -> int | None:
    """Byte length of a valid MPEG audio Layer III frame starting at ``offset``, or ``None`` if the header is invalid."""
    if offset + 4 > len(content):
        return None
    b0, b1, b2 = content[offset], content[offset + 1], content[offset + 2]
    if b0 != 0xFF or (b1 & 0xE0) != 0xE0:
        return None
    version = (b1 >> 3) & 0x03
    layer = (b1 >> 1) & 0x03
    if version == 1 or layer != 1:
        return None
    bitrate_index = (b2 >> 4) & 0x0F
    rate_index = (b2 >> 2) & 0x03
    if rate_index == 3:
        return None
    kbps = (_MPEG1_L3_KBPS if version == 3 else _MPEG2_L3_KBPS)[bitrate_index]
    if kbps == 0:
        return None
    sample_rate = _SAMPLE_RATES[version][rate_index]
    padding = (b2 >> 1) & 0x01
    coefficient = 144 if version == 3 else 72
    return coefficient * kbps * 1000 // sample_rate + padding


def _is_mp3(content: bytes) -> bool:
    start = _id3v2_length(content)
    if start < 0:
        return False
    length = _frame_length(content, start)
    if length is None or length <= 4:
        return False
    following = start + length
    if following + 4 <= len(content):
        return _frame_length(content, following) is not None
    # A truncated first frame is corrupt; a single complete frame is the shortest valid stream.
    return following <= len(content)


__all__ = [
    "SUPPORTED_AUDIO_CONTAINERS",
    "AudioContainer",
    "detect_audio_container",
    "suffix_container",
]
