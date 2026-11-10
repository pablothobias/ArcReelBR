"""Opaque, deterministic ``media_id`` tokens.

A token is ``<payload>.<signature>``, both unpadded base64url (never ``/``). The payload is canonical JSON binding
project, kind, selector (with any resolved version pinned), version, content sha256 and chunk size; the signature is
HMAC-SHA256 under the server token secret (``server.auth.get_token_secret``). No timestamp or randomness enters the
token, so describing unchanged media twice yields the same ``media_id``. Tokens carry no filesystem path."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any

from lib.infra.content_digest import CONTENT_DIGEST_RE, canonical_json_bytes
from server.auth import get_token_secret
from server.services.media_transport.errors import MEDIA_ID_INVALID, MEDIA_PROJECT_MISMATCH, MediaTransportError

_TOKEN_VERSION = 1
_SIGNING_CONTEXT = b"arcreel-media-id-v1\x00"
#: Upper bound on accepted token length; real tokens are a few hundred characters.
MAX_MEDIA_ID_LENGTH = 4096


@dataclass(frozen=True, slots=True)
class MediaIdentity:
    project: str
    kind: str
    selector: dict[str, Any]
    version: int | None
    sha256: str
    chunk_size: int

    def payload(self) -> dict[str, Any]:
        return {
            "v": _TOKEN_VERSION,
            "p": self.project,
            "k": self.kind,
            "s": self.selector,
            "ver": self.version,
            "h": self.sha256,
            "c": self.chunk_size,
        }


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _signature(payload: bytes) -> bytes:
    return hmac.new(get_token_secret().encode("utf-8"), _SIGNING_CONTEXT + payload, hashlib.sha256).digest()


def encode_media_id(identity: MediaIdentity) -> str:
    payload = canonical_json_bytes(identity.payload(), allow_nan=False)
    return f"{_b64encode(payload)}.{_b64encode(_signature(payload))}"


def _invalid() -> MediaTransportError:
    return MediaTransportError(MEDIA_ID_INVALID, "media_id is malformed or its signature does not verify")


def decode_media_id(media_id: str, *, project: str) -> MediaIdentity:
    """Verify the signature, then that the token belongs to ``project``; never trust payload fields before verifying."""
    if not isinstance(media_id, str) or not media_id or len(media_id) > MAX_MEDIA_ID_LENGTH or media_id.count(".") != 1:
        raise _invalid()
    encoded_payload, encoded_signature = media_id.split(".")
    try:
        payload = _b64decode(encoded_payload)
        signature = _b64decode(encoded_signature)
    except (binascii.Error, ValueError):
        raise _invalid() from None
    if _b64encode(payload) != encoded_payload or not hmac.compare_digest(signature, _signature(payload)):
        raise _invalid()
    try:
        raw = json.loads(payload)
        identity = MediaIdentity(
            project=raw["p"],
            kind=raw["k"],
            selector=raw["s"],
            version=raw["ver"],
            sha256=raw["h"],
            chunk_size=raw["c"],
        )
        valid = (
            raw["v"] == _TOKEN_VERSION
            and isinstance(identity.project, str)
            and isinstance(identity.kind, str)
            and isinstance(identity.selector, dict)
            and identity.selector.get("kind") == identity.kind
            and (identity.version is None or type(identity.version) is int)
            and isinstance(identity.sha256, str)
            and CONTENT_DIGEST_RE.match(identity.sha256) is not None
            and type(identity.chunk_size) is int
        )
    except (ValueError, KeyError, TypeError):
        raise _invalid() from None
    if not valid:
        raise _invalid()
    if identity.project != project:
        raise MediaTransportError(MEDIA_PROJECT_MISMATCH, "media_id was issued for a different project")
    return identity


__all__ = ["MAX_MEDIA_ID_LENGTH", "MediaIdentity", "decode_media_id", "encode_media_id"]
