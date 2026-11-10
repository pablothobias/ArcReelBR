"""Character voice references: TTS voice discovery, preview-sample submission, sample records and confirmation.

One domain service shared by the Web routes in ``server/routers/generate.py`` and the Agent tools in
``server/media_tools/voice_references.py``. Generation stays on the native ``voice_sample`` queue task
(``execute_character_voice_sample_task``); this module never synthesizes audio itself and never calls a
provider. Samples are previews: only :func:`confirm_voice_sample` binds one to a character, through the
native ``install_character_reference_audio`` transaction.

Errors are :class:`lib.infra.api_errors.ApiError` subclasses carrying stable i18n keys. Routes translate them
through the app handler; tools relay ``key`` as the problem code.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lib.backends.audio_backends.base import VoiceOption
from lib.billing.catalog_pricing import price_builtin_call
from lib.billing.metering import Priced, Usage
from lib.billing.multipliers import get_provider_multiplier
from lib.catalog.errors import ModelNotInCatalogError
from lib.config.resolver import ConfigResolver
from lib.custom_provider.metering import load_custom_price_source
from lib.db.models.api_call import ApiCall
from lib.generation.generation_queue_client import TaskSpec
from lib.infra.api_errors import BadRequestError, ConflictError, NotFoundError
from lib.infra.async_thread import run_sync_transaction
from lib.infra.path_safety import safe_exists, safe_join
from lib.project.asset_types import resolve_asset_key, validate_asset_name
from lib.project.project_change_hints import (
    ProjectChangeSource,
    build_change_label,
    emit_project_change_batch,
    project_change_source,
)
from lib.project.project_manager import ProjectManager
from lib.speech.audio_utils import (
    AUDIO_REFERENCE_MAX_BYTES,
    AUDIO_REFERENCE_MAX_SECONDS,
    AUDIO_REFERENCE_MIN_SECONDS,
    resolve_audio_ref_path,
)
from server.services.tasks.generation_context import AudioLaneRequest, resolve_generation_context

logger = logging.getLogger(__name__)

VOICE_SAMPLE_TASK_TYPE = "voice_sample"

# Coarse preview-text length guard (same as frontend VOICE_SAMPLE_TEXT_MAX_LENGTH). Reference audio must be 2-10 seconds,
# but text-length-to-duration varies by language/voice and cannot be predicted precisely before submission. Block only pasted paragraphs
# certain to fail and waste billing; actual duration validation remains post-persistence in execution.
VOICE_SAMPLE_TEXT_MAX_LENGTH = 200

REFERENCE_AUDIO_DIR = "characters/refs_audio"

#: Price estimates use the same character-count usage basis as the project cost estimate for narration TTS.
VOICE_SAMPLE_ESTIMATE_BASIS = "text_characters"

_READ_CHUNK = 1024 * 1024


# ==================== Voice catalog ====================


@dataclass(frozen=True, slots=True)
class VoiceCatalog:
    """The project's effective audio backend and the voices it enumerates (backend order).

    ``configured=False`` means no audio provider resolves for the project; every other field is empty then."""

    configured: bool
    provider_id: str | None = None
    model: str | None = None
    backend_name: str | None = None
    voices: tuple[VoiceOption, ...] = ()

    def has_voice(self, voice: str) -> bool:
        return any(option.id == voice for option in self.voices)


async def require_audio_provider(project: dict, *, resolver: ConfigResolver) -> str:
    """Resolve the project's audio provider ID, raising ``audio_provider_not_configured`` when none resolves.

    Resolution failure (no global default and auto-resolution finds no ready audio provider) means unconfigured.
    Successful resolution followed by invalid credentials or other runtime errors belongs to workers/task panels.
    ``ModelNotInCatalogError`` keeps its own guidance (model reselection) and propagates unchanged."""
    try:
        resolved = await resolver.resolve_audio_backend(project, None)
    except ModelNotInCatalogError:
        raise
    except ValueError as exc:
        raise BadRequestError("audio_provider_not_configured") from exc
    return resolved.provider_id


async def resolve_voice_catalog(project_name: str, project: dict, *, resolver: ConfigResolver) -> VoiceCatalog:
    """Return the voice catalog of the project's actual effective audio backend, never a global narration field.

    Voices come from the constructed backend's own enumeration; nothing here is hard-coded per provider."""
    try:
        await require_audio_provider(project, resolver=resolver)
    except BadRequestError:
        return VoiceCatalog(configured=False)
    ctx = await resolve_generation_context(project_name, None, project=project, audio=AudioLaneRequest())
    audio = ctx.audio
    return VoiceCatalog(
        configured=True,
        provider_id=audio.provider_model.provider_id,
        model=audio.backend_model,
        backend_name=audio.backend_name,
        voices=tuple(audio.voices),
    )


# ==================== Sample submission ====================


@dataclass(frozen=True, slots=True)
class PreparedVoiceSample:
    """A validated sample request: explicit text and voice for an existing character, plus the resolved audio provider."""

    project: dict
    character: str
    text: str
    voice: str
    provider_id: str


def validate_voice_sample_text_and_voice(text: str, voice: str) -> tuple[str, str]:
    """Explicit text and voice are required; no narrator or project fallback. Preserves the native text-length guard."""
    text = text.strip()
    voice = voice.strip()
    if not text:
        raise BadRequestError("prompt_text_empty")
    if len(text) > VOICE_SAMPLE_TEXT_MAX_LENGTH:
        raise BadRequestError("voice_sample_text_too_long", max_length=VOICE_SAMPLE_TEXT_MAX_LENGTH)
    if not voice:
        raise BadRequestError("voice_sample_voice_required")
    return text, voice


def resolve_sample_character(project: Mapping[str, Any], name: str) -> str:
    """Validate a character name and confirm it exists; existing keys may use NFD, so resolve in the coordinate system."""
    try:
        char_name = validate_asset_name(name)
    except ValueError as exc:
        raise BadRequestError("asset_invalid_name", name=name) from exc
    if resolve_asset_key(project.get("characters"), char_name) is None:
        raise NotFoundError("character_not_found", name=char_name)
    return char_name


async def prepare_voice_sample(
    project_name: str,
    name: str,
    *,
    text: str,
    voice: str,
    projects: ProjectManager,
    resolver: ConfigResolver,
) -> PreparedVoiceSample:
    """Validate one sample request in the native order: text/voice, character, then audio provider."""
    text, voice = validate_voice_sample_text_and_voice(text, voice)

    def _sync() -> tuple[dict, str]:
        project = projects.load_project(project_name)
        return project, resolve_sample_character(project, name)

    project, char_name = await asyncio.to_thread(_sync)
    provider_id = await require_audio_provider(project, resolver=resolver)
    return PreparedVoiceSample(project=project, character=char_name, text=text, voice=voice, provider_id=provider_id)


def voice_sample_task_spec(sample: PreparedVoiceSample, *, source: str) -> TaskSpec:
    """The native ``voice_sample`` task: preview only, using the existing audio lane and accounting."""
    return TaskSpec.from_request(
        task_type=VOICE_SAMPLE_TASK_TYPE,
        media_type="audio",
        resource_id=sample.character,
        prompt=sample.text,
        extra_payload={"voice": sample.voice},
        source=source,
    )


@dataclass(frozen=True, slots=True)
class VoiceSampleQuote:
    """Pre-submission price of one sample at current prices.

    ``amount`` of ``None`` means unpriced, explained by ``unpriced_reason``; it never means free."""

    provider_id: str
    model: str
    amount: float | None
    currency: str | None
    unpriced_reason: str | None
    estimate_basis: str = VOICE_SAMPLE_ESTIMATE_BASIS

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "amount": self.amount,
            "currency": self.currency,
            "unpriced": self.amount is None,
            "unpriced_reason": self.unpriced_reason,
            "estimate_basis": self.estimate_basis,
        }


async def quote_voice_sample(
    *,
    provider_id: str,
    model: str,
    text: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> VoiceSampleQuote:
    """Quote one sample with the settlement catalog query and calculator (character-count usage of the exact text).

    Models priced by tokens or seconds have no pre-submission estimator and stay unpriced. A database failure is also
    reported as unpriced, never as zero."""
    try:
        async with session_factory() as session:
            custom = await load_custom_price_source(session, provider_id, model)
            multiplier = await get_provider_multiplier(session, provider_id)
    except (SQLAlchemyError, ValueError):
        logger.warning("voice sample quote: price sources unavailable provider=%s model=%s", provider_id, model)
        return VoiceSampleQuote(provider_id, model, None, None, "price_source_unavailable")
    requests = (Usage(text=text),)
    cost = (
        custom.price(model=model, media_type="audio", requests=requests, provider_multiplier=multiplier, estimate=True)
        if custom is not None
        else price_builtin_call(
            provider=provider_id,
            model=model,
            media_type="audio",
            requests=requests,
            provider_multiplier=multiplier,
            estimate=True,
        )
    )
    if isinstance(cost, Priced):
        return VoiceSampleQuote(provider_id, model, round(cost.amount, 6), cost.currency, None)
    return VoiceSampleQuote(provider_id, model, None, None, str(cost.reason))


# ==================== Media identity ====================


@dataclass(frozen=True, slots=True)
class VoiceMedia:
    """A resolved voice-reference audio file. ``relative_path`` is project-relative and never leaves the server.

    ``version`` is a content token (``sha256:<hex>``): samples are immutable per task and the bound reference keeps a
    fixed filename, so the digest is what distinguishes revisions."""

    kind: str
    character: str
    relative_path: str
    size_bytes: int
    sha256: str
    mime_type: str
    task_id: str | None = None

    @property
    def version(self) -> str:
        return f"sha256:{self.sha256}"


def audio_mime_type(relative_path: str) -> str:
    suffix = PurePosixPath(relative_path).suffix.lower()
    if suffix == ".wav":
        return "audio/wav"
    if suffix == ".mp3":
        return "audio/mpeg"
    return mimetypes.guess_type(relative_path)[0] or "application/octet-stream"


def _file_digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(_READ_CHUNK):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def _regular_file(project_dir: Path, relative_path: str) -> Path | None:
    """Resolve a project-relative path inside the project directory; ``None`` if absent, escaping, or not a regular file."""
    try:
        if not safe_exists(project_dir, relative_path):
            return None
        path = safe_join(project_dir, relative_path)
    except ValueError:
        return None
    # safe_join resolves the path (symlinks included) and confines it to the project; only regular files qualify.
    return path if path.is_file() else None


class _InvalidReferencePointer(Exception):
    """``reference_audio`` points outside ``characters/refs_audio`` (e.g. at project.json)."""


def _reference_file(project_dir: Path, ref: str) -> Path | None:
    """Resolve a bound reference with the native rule (``resolve_audio_ref_path``): it must lie in characters/refs_audio.

    Returns ``None`` when the file is missing; raises :class:`_InvalidReferencePointer` for pointers outside that
    directory, which are never treated as reference audio."""
    resolved = resolve_audio_ref_path(project_dir, project_dir / REFERENCE_AUDIO_DIR, ref)
    if resolved is None:
        raise _InvalidReferencePointer(ref)
    return resolved if resolved.is_file() else None


def _describe_file(
    project_dir: Path, relative_path: str, *, kind: str, character: str, task_id: str | None
) -> VoiceMedia | None:
    path = _regular_file(project_dir, relative_path)
    if path is None:
        return None
    size, sha256 = _file_digest(path)
    return VoiceMedia(
        kind=kind,
        character=character,
        relative_path=relative_path,
        size_bytes=size,
        sha256=sha256,
        mime_type=audio_mime_type(relative_path),
        task_id=task_id,
    )


def _current_reference_sync(projects: ProjectManager, project_name: str, character: str) -> VoiceMedia | None:
    project = projects.load_project(project_name)
    key = resolve_asset_key(project.get("characters"), character)
    if key is None:
        raise NotFoundError("character_not_found", name=character)
    entry = project["characters"][key]
    ref = entry.get("reference_audio") if isinstance(entry, dict) else None
    if not isinstance(ref, str) or not ref:
        return None
    project_dir = projects.get_project_path(project_name)
    try:
        path = _reference_file(project_dir, ref)
    except _InvalidReferencePointer as exc:
        raise ConflictError("voice_reference_path_invalid", name=key) from exc
    if path is None:
        return None
    size, sha256 = _file_digest(path)
    return VoiceMedia(
        kind="character_voice_reference",
        character=key,
        relative_path=path.relative_to(project_dir.resolve()).as_posix(),
        size_bytes=size,
        sha256=sha256,
        mime_type=audio_mime_type(ref),
        task_id=None,
    )


def _reference_pointer_sync(projects: ProjectManager, project_name: str, character: str) -> str | None:
    project = projects.load_project(project_name)
    key = resolve_asset_key(project.get("characters"), character)
    if key is None:
        raise NotFoundError("character_not_found", name=character)
    entry = project["characters"][key]
    ref = entry.get("reference_audio") if isinstance(entry, dict) else None
    if not isinstance(ref, str) or not ref:
        return None
    project_dir = projects.get_project_path(project_name)
    if resolve_audio_ref_path(project_dir, project_dir / REFERENCE_AUDIO_DIR, ref) is None:
        raise ConflictError("voice_reference_path_invalid", name=key)
    return ref


async def character_reference_pointer(project_name: str, character: str, *, projects: ProjectManager) -> str | None:
    """The character's validated ``reference_audio`` pointer (project-relative, inside characters/refs_audio), without
    reading the file, so callers can materialize object-storage working files before hashing or probing it.

    ``None`` when unbound; raises ``character_not_found`` / ``asset_invalid_name`` / ``voice_reference_path_invalid``."""
    try:
        char_name = validate_asset_name(character)
    except ValueError as exc:
        raise BadRequestError("asset_invalid_name", name=character) from exc
    return await asyncio.to_thread(_reference_pointer_sync, projects, project_name, char_name)


async def resolve_character_voice_reference_media(
    project_name: str, character: str, *, projects: ProjectManager
) -> VoiceMedia | None:
    """Resolve a character's currently bound reference audio; ``None`` when unbound or its file is missing.

    Media-transport entry point for ``describe_media(kind=character_voice_reference)``. Raises
    ``character_not_found`` / ``asset_invalid_name``, or ``voice_reference_path_invalid`` when the stored pointer lies
    outside characters/refs_audio (native ``resolve_audio_ref_path`` rule). Read-only; no task or provider call."""
    try:
        char_name = validate_asset_name(character)
    except ValueError as exc:
        raise BadRequestError("asset_invalid_name", name=character) from exc
    return await asyncio.to_thread(_current_reference_sync, projects, project_name, char_name)


def require_project_voice_sample_task(task: Mapping[str, Any] | None, *, project_name: str, task_id: str) -> dict:
    """Return a ``voice_sample`` task of this project, or raise ``task_not_found`` (other projects are indistinguishable from absent)."""
    if task is None or task.get("project_name") != project_name or task.get("task_type") != VOICE_SAMPLE_TASK_TYPE:
        raise NotFoundError("task_not_found", id=task_id)
    return dict(task)


def sample_relative_path(task: Mapping[str, Any]) -> str:
    """The sample file of a succeeded task; ``voice_sample_not_ready`` otherwise. Never a client-supplied path."""
    if task.get("status") != "succeeded":
        raise BadRequestError("voice_sample_not_ready")
    result = task.get("result") or {}
    sample_rel = result.get("file_path") if isinstance(result, dict) else None
    if not isinstance(sample_rel, str) or not sample_rel:
        raise BadRequestError("voice_sample_not_ready")
    return sample_rel


def _sample_media_sync(projects: ProjectManager, project_name: str, task: Mapping[str, Any]) -> VoiceMedia:
    sample_rel = sample_relative_path(task)
    media = _describe_file(
        projects.get_project_path(project_name),
        sample_rel,
        kind="voice_sample",
        character=str(task.get("resource_id") or ""),
        task_id=str(task.get("task_id") or ""),
    )
    if media is None:
        raise NotFoundError("voice_sample_file_missing")
    recorded = (task.get("result") or {}).get("sha256")
    if isinstance(recorded, str) and recorded and recorded != media.sha256:
        # The task recorded its own bytes' digest; different bytes are not this paid sample.
        raise ConflictError("voice_sample_content_changed", id=task.get("task_id"))
    return media


async def resolve_voice_sample_media(
    project_name: str, task_id: str, *, projects: ProjectManager, queue: Any
) -> VoiceMedia:
    """Resolve a succeeded ``voice_sample`` task to its preview file (project-relative path, size, sha256).

    Media-transport entry point for ``describe_media(kind=voice_sample)``. Raises ``task_not_found`` (unknown,
    other project, other task type), ``voice_sample_not_ready``, ``voice_sample_file_missing`` or
    ``voice_sample_content_changed``. Read-only; no task or provider call."""
    task = require_project_voice_sample_task(await queue.get_task(task_id), project_name=project_name, task_id=task_id)
    return await asyncio.to_thread(_sample_media_sync, projects, project_name, task)


# ==================== Confirmation ====================


@dataclass(frozen=True, slots=True)
class ConfirmedVoiceSample:
    path: str
    sha256: str
    already_bound: bool


def _reference_target(char_name: str) -> str:
    return f"{REFERENCE_AUDIO_DIR}/{char_name}.wav"


def _emit_reference_audio_change(
    project_name: str, char_name: str, ref_audio_rel: str, target: Path, source: ProjectChangeSource
) -> None:
    # Fixed target name {char_name}.wav means reference_audio stays unchanged after regeneration/reconfirmation
    # (same path string). project.json field diffs cannot detect changes or automatically broadcast refreshes,
    # although persisted bytes changed. Emit character:updated explicitly with new mtime fingerprints
    # so other open clients cache-bust the audio without waiting for an unrelated
    # project refresh to synchronize by chance.
    try:
        emit_project_change_batch(
            project_name,
            [
                {
                    "entity_type": "character",
                    "action": "updated",
                    "entity_id": char_name,
                    **build_change_label("character_reference_audio", id=char_name),
                    "focus": None,
                    "important": False,
                    "asset_fingerprints": {ref_audio_rel: target.stat().st_mtime_ns},
                }
            ],
            source=source,
        )
    except Exception:
        logger.exception("发送试听样本确认项目事件失败 project=%s character=%s", project_name, char_name)


def _bound_digest(project_dir: Path, project: Mapping[str, Any], char_name: str) -> str | None:
    key = resolve_asset_key(project.get("characters"), char_name)
    if key is None:
        raise NotFoundError("character_not_found", name=char_name)
    entry = project["characters"][key]
    ref = entry.get("reference_audio") if isinstance(entry, dict) else None
    if not isinstance(ref, str) or not ref:
        return None
    try:
        path = _reference_file(project_dir, ref)
    except _InvalidReferencePointer:
        # A pointer outside characters/refs_audio is not a reference: treat the character as unbound.
        return None
    return _file_digest(path)[1] if path is not None else None


async def confirm_voice_sample(
    project_name: str,
    name: str,
    task_id: str,
    *,
    projects: ProjectManager,
    queue: Any,
    source: ProjectChangeSource,
    expected_reference_sha256: str | None = None,
    expect_unbound: bool = False,
    idempotent: bool = False,
) -> ConfirmedVoiceSample:
    """Promote a succeeded TTS sample to the character's reference audio through the native install transaction.

    Trusts only the task's own result path, never client paths. Execution already validated format/duration/size
    under upload rules (see ``execute_character_voice_sample_task``), so bytes are installed unchanged, without
    repeating validation or transcoding. No TTS call and no task is created.

    ``expected_reference_sha256`` / ``expect_unbound`` protect against concurrent revisions: the current binding is
    rechecked inside the project write lock and a mismatch raises ``voice_reference_revision_conflict``.
    ``idempotent`` returns ``already_bound`` without writing when the bound bytes already equal the sample."""
    try:
        char_name = validate_asset_name(name)
    except ValueError as exc:
        raise BadRequestError("asset_invalid_name", name=name) from exc
    task = await queue.get_task(task_id)
    if task is None or task.get("resource_id") != char_name:
        raise NotFoundError("task_not_found", id=task_id)
    task = require_project_voice_sample_task(task, project_name=project_name, task_id=task_id)
    sample_rel = sample_relative_path(task)
    ref_audio_rel = _reference_target(char_name)
    check_revision = expected_reference_sha256 is not None or expect_unbound

    def _sync() -> ConfirmedVoiceSample:
        project_dir = projects.get_project_path(project_name)
        if not safe_exists(project_dir, sample_rel):
            raise NotFoundError("voice_sample_file_missing")
        sample_abs = safe_join(project_dir, sample_rel)
        content = sample_abs.read_bytes()
        sample_sha = hashlib.sha256(content).hexdigest()
        recorded = (task.get("result") or {}).get("sha256")
        if isinstance(recorded, str) and recorded and recorded != sample_sha:
            raise ConflictError("voice_sample_content_changed", id=task_id)

        if idempotent:
            project = projects.load_project(project_name)
            key = resolve_asset_key(project.get("characters"), char_name)
            current_ref = project["characters"][key].get("reference_audio") if key is not None else None
            if current_ref == ref_audio_rel and _bound_digest(project_dir, project, char_name) == sample_sha:
                return ConfirmedVoiceSample(path=ref_audio_rel, sha256=sample_sha, already_bound=True)

        def _precondition(project: dict) -> None:
            if not check_revision:
                return
            current = _bound_digest(project_dir, project, char_name)
            expected = None if expect_unbound else expected_reference_sha256
            if current != expected:
                raise ConflictError("voice_reference_revision_conflict", name=char_name)

        try:
            with project_change_source(source):
                projects.install_character_reference_audio(
                    project_name,
                    char_name,
                    ref_audio_rel,
                    content,
                    **({"precondition": _precondition} if check_revision else {}),
                )
        except KeyError as exc:
            raise NotFoundError("character_not_found", name=char_name) from exc
        _emit_reference_audio_change(project_name, char_name, ref_audio_rel, project_dir / ref_audio_rel, source)
        return ConfirmedVoiceSample(path=ref_audio_rel, sha256=sample_sha, already_bound=False)

    return await run_sync_transaction(_sync)


# ==================== Sample records ====================


@dataclass(frozen=True, slots=True)
class SampleCost:
    status: str
    provider: str
    model: str
    amount: float | None
    currency: str | None
    unpriced_reason: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "amount": self.amount,
            "currency": self.currency,
            "unpriced_reason": self.unpriced_reason,
        }


async def load_sample_costs(
    task_ids: Sequence[str], *, session_factory: async_sessionmaker[AsyncSession]
) -> dict[str, list[SampleCost]] | None:
    """Recorded provider calls per task; ``None`` when the usage store cannot be read (unknown, not zero)."""
    if not task_ids:
        return {}
    try:
        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        ApiCall.task_id,
                        ApiCall.status,
                        ApiCall.provider,
                        ApiCall.model,
                        ApiCall.cost_amount,
                        ApiCall.currency,
                        ApiCall.unpriced_reason,
                    ).where(ApiCall.task_id.in_(list(task_ids)))
                )
            ).all()
    except SQLAlchemyError:
        logger.warning("voice sample listing: usage records unavailable", exc_info=True)
        return None
    costs: dict[str, list[SampleCost]] = {}
    for task_id, status, provider, model, amount, currency, reason in rows:
        priced = amount is not None and status != "pending"
        costs.setdefault(task_id, []).append(
            SampleCost(
                status=status,
                provider=provider,
                model=model,
                amount=amount if priced else None,
                currency=currency if priced else None,
                unpriced_reason=reason if amount is None else ("pending_settlement" if status == "pending" else None),
            )
        )
    return costs


async def list_voice_sample_tasks(
    project_name: str, *, queue: Any, character: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    """Every ``voice_sample`` task of the project (newest first), optionally for one character, from durable task records."""
    tasks: list[dict[str, Any]] = []
    page = 1
    while len(tasks) < limit:
        listing = await queue.list_tasks(
            project_name=project_name, task_type=VOICE_SAMPLE_TASK_TYPE, page=page, page_size=100
        )
        items = listing.get("items") or []
        for task in items:
            if task.get("project_name") != project_name or task.get("task_type") != VOICE_SAMPLE_TASK_TYPE:
                continue
            if character is not None and task.get("resource_id") != character:
                continue
            tasks.append(task)
        if len(items) < 100 or page * 100 >= int(listing.get("total") or 0):
            break
        page += 1
    return tasks[:limit]


@dataclass(slots=True)
class SampleFileFacts:
    state: str  # "available" | "missing" | "content_changed" | "not_produced"
    relative_path: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    mime_type: str | None = None


def sample_file_facts(project_dir: Path, task: Mapping[str, Any]) -> SampleFileFacts:
    """Synchronous file facts for one sample task (hashing; call from a worker thread)."""
    result = task.get("result") or {}
    rel = result.get("file_path") if isinstance(result, dict) else None
    if task.get("status") != "succeeded" or not isinstance(rel, str) or not rel:
        return SampleFileFacts(state="not_produced")
    path = _regular_file(project_dir, rel)
    if path is None:
        return SampleFileFacts(state="missing", mime_type=audio_mime_type(rel))
    size, sha256 = _file_digest(path)
    recorded = result.get("sha256")
    state = "content_changed" if isinstance(recorded, str) and recorded and recorded != sha256 else "available"
    return SampleFileFacts(state=state, size_bytes=size, sha256=sha256, mime_type=audio_mime_type(rel))


def bound_reference_digests(projects: ProjectManager, project_name: str) -> dict[str, str | None]:
    """Digest of each character's bound reference audio (``None`` when unbound or missing); synchronous."""
    project = projects.load_project(project_name)
    project_dir = projects.get_project_path(project_name)
    characters = project.get("characters")
    digests: dict[str, str | None] = {}
    if not isinstance(characters, dict):
        return digests
    for key in characters:
        digests[key] = _bound_digest(project_dir, project, key)
    return digests


@dataclass(frozen=True, slots=True)
class ReferenceLimits:
    min_seconds: float = AUDIO_REFERENCE_MIN_SECONDS
    max_seconds: float = AUDIO_REFERENCE_MAX_SECONDS
    max_bytes: int = AUDIO_REFERENCE_MAX_BYTES

    def to_payload(self) -> dict[str, Any]:
        return {"min_seconds": self.min_seconds, "max_seconds": self.max_seconds, "max_bytes": self.max_bytes}


REFERENCE_LIMITS = ReferenceLimits()


__all__ = [
    "REFERENCE_AUDIO_DIR",
    "REFERENCE_LIMITS",
    "VOICE_SAMPLE_TASK_TYPE",
    "VOICE_SAMPLE_TEXT_MAX_LENGTH",
    "ConfirmedVoiceSample",
    "PreparedVoiceSample",
    "SampleCost",
    "SampleFileFacts",
    "VoiceCatalog",
    "VoiceMedia",
    "VoiceSampleQuote",
    "audio_mime_type",
    "bound_reference_digests",
    "character_reference_pointer",
    "confirm_voice_sample",
    "list_voice_sample_tasks",
    "load_sample_costs",
    "prepare_voice_sample",
    "quote_voice_sample",
    "require_audio_provider",
    "require_project_voice_sample_task",
    "resolve_character_voice_reference_media",
    "resolve_sample_character",
    "resolve_voice_catalog",
    "resolve_voice_sample_media",
    "sample_file_facts",
    "sample_relative_path",
    "validate_voice_sample_text_and_voice",
    "voice_sample_task_spec",
]
