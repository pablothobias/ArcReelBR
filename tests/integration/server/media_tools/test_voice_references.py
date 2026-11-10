"""Character voice-reference tools (MCP-003/004): voices, sample quote/generation, listing, confirmation and inspection.

A fake audio backend writes real WAV bytes; no real TTS, ASR model or provider is reached. The queue and usage
records are the real repositories on a per-test database.
"""

from __future__ import annotations

import io
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from lib.backends.audio_backends.base import VoiceOption
from lib.config.resolver import ConfigResolver, ProviderModel
from lib.db.models.api_call import ApiCall
from lib.generation.generation_batch import GenerationBatchReadModel
from lib.generation.generation_queue import GenerationQueue
from lib.infra.api_errors import ConflictError
from lib.project.project_manager import ProjectManager
from lib.project.resource_paths import resource_relative_path
from server.agent_toolset.declaration import invoke_declaration
from server.agent_toolset.voice_references import (
    CONFIRM_VOICE_SAMPLE,
    GENERATE_VOICE_SAMPLE,
    INSPECT_VOICE_REFERENCE,
    LIST_TTS_VOICES,
    LIST_VOICE_SAMPLES,
    VOICE_REFERENCE_TOOLS,
)
from server.media_tools import voice_references as voice_tools
from server.services import voice_references
from server.services.project import workflow_planner
from server.services.tasks import generation_tasks
from server.services.tasks.generation_context import AudioLaneResult, GenerationContext
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolOutcome
from tests.fakes import bind_session_factory, use_generation_context, use_project_manager, write_backend_output

PROJECT = "demo"
VOICES = (VoiceOption(id="voice-a", label="voice-a"), VoiceOption(id="voice-b", label="voice-b"))


def wav_bytes(seconds: float, *, frequency: int = 0) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        frames = int(16000 * seconds)
        out.writeframes(bytes([frequency % 256, 0]) * frames)
    return buffer.getvalue()


class FakeTts:
    """Audio backend substitute: writes a WAV per resource and records one priced usage row like the real generator."""

    def __init__(self, project_dir: Path, factory) -> None:
        self.project_dir = project_dir
        self.factory = factory
        self.calls: list[dict[str, Any]] = []
        self.seconds = 3.0
        self.versions = self

    async def generate_audio_async(self, *, text, resource_id, voice, speed, task_id=None, target_resource=None):
        self.calls.append({"text": text, "voice": voice, "resource_id": resource_id, "task_id": task_id})
        path = self.project_dir / resource_relative_path("audio", resource_id)
        # Distinct bytes per voice so two characters' samples differ.
        await write_backend_output(path, wav_bytes(self.seconds, frequency=len(voice) + len(self.calls)))
        async with self.factory() as session:
            session.add(
                ApiCall(
                    project_name=PROJECT,
                    call_type="audio",
                    model="fake-model",
                    provider="fake-tts",
                    status="success",
                    started_at=datetime.now(UTC),
                    cost_amount=0.0125,
                    currency="USD",
                    task_id=task_id,
                )
            )
            await session.commit()
        return path, 1

    def get_versions(self, resource_type, resource_id):
        return {"versions": []}


class Env:
    def __init__(self, pm: ProjectManager, queue: GenerationQueue, factory, tts: FakeTts, data_root: Path) -> None:
        self.pm = pm
        self.queue = queue
        self.factory = factory
        self.tts = tts
        self.data_root = data_root

    @property
    def services(self) -> Services:
        return Services(
            projects=self.pm,
            workflow_planner=workflow_planner.get_workflow_planner(self.pm),
            capabilities=ConfigResolver(self.factory),
            queue=self.queue,
            sessions=self.factory,
        )

    async def call(self, declaration, arguments: dict[str, Any], *, project: str = PROJECT) -> ToolOutcome[Any]:
        caller = CallerContext(user_id="default", source="mcp")
        scope = ProjectScope(project_name=project, data_root=self.data_root)
        return await invoke_declaration(declaration, arguments, scope, caller, self.services)

    async def confirm(self, task_id: str, character: str) -> dict[str, Any]:
        """Confirm the way an agent must: state the binding last inspected (default deny on blind overwrite)."""
        current = _value(await self.call(INSPECT_VOICE_REFERENCE, {"character": character}))
        expectation: dict[str, Any] = (
            {"expected_reference_sha256": current["media"]["sha256"]} if current["bound"] else {"expect_unbound": True}
        )
        return _value(
            await self.call(CONFIRM_VOICE_SAMPLE, {"task_id": task_id, "character": character, **expectation})
        )

    async def task_count(self) -> int:
        return int((await self.queue.list_tasks(project_name=None, page_size=500))["total"])

    async def run_worker(self) -> dict[str, Any]:
        """Claim and execute one queued audio task exactly as the worker does, then settle it."""
        task = await self.queue.claim_next_task("audio")
        assert task is not None
        try:
            result = await generation_tasks.execute_character_voice_sample_task(
                task["project_name"], task["resource_id"], task["payload"], task_id=task["task_id"]
            )
        except Exception as exc:
            await self.queue.mark_task_failed(task["task_id"], str(exc))
        else:
            await self.queue.mark_task_succeeded(task["task_id"], result)
        stored = await self.queue.get_task(task["task_id"])
        assert stored is not None
        return stored

    async def generate(self, character: str, voice: str, text: str = "Olá, eu sou a voz de teste.") -> str:
        out = await self.call(GENERATE_VOICE_SAMPLE, {"character": character, "voice": voice, "text": text})
        assert out.problem is None, out.problem
        assert isinstance(out.value, GenerationBatchReadModel)
        task = await self.run_worker()
        return task["task_id"]


@pytest.fixture
async def env(tmp_path: Path, concurrent_session_factory, monkeypatch: pytest.MonkeyPatch) -> Env:
    factory = concurrent_session_factory
    bind_session_factory(monkeypatch, factory)
    pm = ProjectManager(tmp_path / "projects")
    pm.create_project(PROJECT)
    pm.create_project_metadata(PROJECT, "Demo", "Anime", "narration")
    for name in ("Ana", "Bento", "Gato"):
        pm.add_character(PROJECT, name, f"{name} description")
    pm.create_project("other")
    pm.create_project_metadata("other", "Other", "Anime", "narration")
    pm.add_character("other", "Ana", "other Ana")
    use_project_manager(monkeypatch, pm)

    async def _resolve_audio(self, project, payload):
        return ProviderModel("fake-tts", "fake-model")

    monkeypatch.setattr(ConfigResolver, "resolve_audio_backend", _resolve_audio)
    tts = FakeTts(pm.get_project_path(PROJECT), factory)

    async def _ctx(*_args, **_kwargs):
        return GenerationContext(
            generator=tts,
            audio_lane=AudioLaneResult(
                provider_model=ProviderModel("fake-tts", "fake-model"),
                backend_name="fake-tts",
                backend_model="fake-model",
                voices=VOICES,
            ),
        )

    monkeypatch.setattr(voice_references, "resolve_generation_context", _ctx)
    use_generation_context(monkeypatch, _ctx)
    monkeypatch.delenv("ARCREEL_SPEECH_REVIEW_MODEL", raising=False)
    queue = GenerationQueue(session_factory=factory)
    # Enqueue refuses work while no worker holds the lease; the test drives execution itself through run_worker.
    assert await queue.acquire_or_renew_worker_lease(name="default", owner_id="test-worker", ttl_seconds=600)
    return Env(pm, queue, factory, tts, tmp_path)


def _value(out: ToolOutcome[Any]) -> Any:
    assert out.problem is None, out.problem
    return out.value


def _problem_code(out: ToolOutcome[Any]) -> str:
    assert out.problem is not None, out.value
    return out.problem.code


async def test_declarations_are_shared_and_policies_match() -> None:
    names = [d.name for d in VOICE_REFERENCE_TOOLS]
    assert names == [
        "list_tts_voices",
        "generate_voice_sample",
        "list_voice_samples",
        "confirm_voice_sample",
        "inspect_voice_reference",
    ]
    assert GENERATE_VOICE_SAMPLE.long_task is True
    assert "proves neither voice identity" in INSPECT_VOICE_REFERENCE.description


async def test_list_tts_voices_discovers_backend_voices_without_tasks(env: Env) -> None:
    value = _value(await env.call(LIST_TTS_VOICES, {}))

    assert value["configured"] is True
    assert (value["provider_id"], value["model"]) == ("fake-tts", "fake-model")
    assert [v["id"] for v in value["voices"]] == ["voice-a", "voice-b"]
    assert await env.task_count() == 0
    assert env.tts.calls == []


async def test_list_tts_voices_reports_unconfigured(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _none(self, project, payload):
        raise ValueError("no audio provider")

    monkeypatch.setattr(ConfigResolver, "resolve_audio_backend", _none)
    value = _value(await env.call(LIST_TTS_VOICES, {}))
    assert value["configured"] is False
    assert value["voices"] == []


async def test_preview_quotes_unknown_price_as_null_without_task(env: Env) -> None:
    out = await env.call(
        GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-a", "text": "Oi, tudo bem?", "preview": True}
    )
    quote = _value(out)["voice_sample_quote"]

    assert quote["voice"] == "voice-a"
    assert quote["text"] == "Oi, tudo bem?"
    assert (quote["provider_id"], quote["model"]) == ("fake-tts", "fake-model")
    assert quote["estimated_cost"]["amount"] is None
    assert quote["estimated_cost"]["unpriced"] is True
    assert quote["estimated_cost"]["unpriced_reason"]
    assert quote["binds_reference"] is False
    assert await env.task_count() == 0
    assert env.tts.calls == []


async def test_preview_uses_settlement_pricing_when_priced(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.billing.metering import Priced

    seen: list[str | None] = []

    def _price(*, provider, model, media_type, requests, provider_multiplier, estimate):
        seen.append(requests[0].text)
        assert (provider, model, media_type, estimate) == ("fake-tts", "fake-model", "audio", True)
        return Priced(0.002, "USD")

    monkeypatch.setattr(voice_references, "price_builtin_call", _price)
    out = await env.call(
        GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-a", "text": " Oi ", "preview": True}
    )
    cost = _value(out)["voice_sample_quote"]["estimated_cost"]
    assert (cost["amount"], cost["currency"], cost["unpriced"]) == (0.002, "USD", False)
    assert seen == ["Oi"]


@pytest.mark.parametrize(
    ("arguments", "code"),
    [
        ({"character": "Ana", "voice": " ", "text": "Oi"}, "voice_sample_voice_required"),
        ({"character": "Ana", "voice": "voice-a", "text": "  "}, "prompt_text_empty"),
        ({"character": "Ana", "voice": "voice-a", "text": "x" * 201}, "voice_sample_text_too_long"),
        ({"character": "Ninguém", "voice": "voice-a", "text": "Oi"}, "character_not_found"),
        ({"character": "Ana", "voice": "voice-z", "text": "Oi"}, "voice_sample_voice_unknown"),
    ],
)
async def test_generation_requires_explicit_valid_inputs(env: Env, arguments: dict[str, Any], code: str) -> None:
    for preview in (True, False):
        out = await env.call(GENERATE_VOICE_SAMPLE, {**arguments, "preview": preview})
        assert _problem_code(out) == code
    assert await env.task_count() == 0
    assert env.tts.calls == []


async def test_two_characters_distinct_voices_and_animal_without_voice(env: Env) -> None:
    ana_task = await env.generate("Ana", "voice-a", "Eu sou a Ana.")
    bento_task = await env.generate("Bento", "voice-b", "Eu sou o Bento.")

    assert [(c["voice"], c["text"]) for c in env.tts.calls] == [
        ("voice-a", "Eu sou a Ana."),
        ("voice-b", "Eu sou o Bento."),
    ]
    listing = _value(await env.call(LIST_VOICE_SAMPLES, {}))["samples"]
    by_task = {s["task_id"]: s for s in listing}
    assert by_task[ana_task]["character"] == "Ana"
    assert by_task[ana_task]["voice"] == "voice-a"
    assert by_task[bento_task]["character"] == "Bento"
    assert by_task[bento_task]["voice"] == "voice-b"
    assert by_task[ana_task]["media"]["sha256"] != by_task[bento_task]["media"]["sha256"]
    # Generation never binds: the native preview/confirm separation holds.
    assert not any(s["bound"] for s in listing)
    assert env.pm.load_project(PROJECT)["characters"]["Ana"].get("reference_audio") in (None, "")

    tts_calls = len(env.tts.calls)
    for character, task_id in (("Ana", ana_task), ("Bento", bento_task)):
        confirmed = _value(
            await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": task_id, "character": character, "expect_unbound": True})
        )
        assert confirmed["bound"] is True
        assert confirmed["already_bound"] is False
    characters = env.pm.load_project(PROJECT)["characters"]
    assert characters["Ana"]["reference_audio"] == "characters/refs_audio/Ana.wav"
    assert characters["Bento"]["reference_audio"] == "characters/refs_audio/Bento.wav"

    # The animal keeps no voice reference: listing and inspection say so explicitly, without errors or tasks.
    gato = _value(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Gato"}))
    assert gato["bound"] is False
    assert _value(await env.call(LIST_VOICE_SAMPLES, {"character": "Gato"}))["samples"] == []
    assert len(env.tts.calls) == tts_calls
    assert await env.task_count() == 2


async def test_two_previews_do_not_overwrite_each_other(env: Env) -> None:
    first = await env.generate("Ana", "voice-a", "Primeira versão.")
    second = await env.generate("Ana", "voice-b", "Segunda versão.")

    samples = {s["task_id"]: s for s in _value(await env.call(LIST_VOICE_SAMPLES, {"character": "Ana"}))["samples"]}
    assert samples[first]["media"]["state"] == samples[second]["media"]["state"] == "available"
    assert samples[first]["media"]["sha256"] != samples[second]["media"]["sha256"]
    assert samples[first]["text"] == "Primeira versão."
    assert samples[second]["text"] == "Segunda versão."

    # Choose the first (older) version explicitly.
    await env.confirm(first, "Ana")
    samples = {s["task_id"]: s for s in _value(await env.call(LIST_VOICE_SAMPLES, {"character": "Ana"}))["samples"]}
    assert samples[first]["bound"] is True
    assert samples[second]["bound"] is False


async def test_active_sample_is_reported_instead_of_resubmitted(env: Env) -> None:
    out = await env.call(GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-a", "text": "Um."})
    assert isinstance(_value(out), GenerationBatchReadModel)

    again = await env.call(GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-b", "text": "Dois."})
    assert _problem_code(again) == "voice_sample_in_progress"
    quote = _value(
        await env.call(
            GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-b", "text": "Dois.", "preview": True}
        )
    )
    assert quote["voice_sample_quote"]["active_task_id"]
    assert await env.task_count() == 1


async def test_recovery_after_restart_confirms_original_without_new_charge(env: Env) -> None:
    task_id = await env.generate("Ana", "voice-a")
    calls_before = len(env.tts.calls)

    # Simulated restart: brand-new queue, project manager and services over the same durable stores.
    restarted = Env(
        ProjectManager(env.data_root / "projects"),
        GenerationQueue(session_factory=env.factory),
        env.factory,
        env.tts,
        env.data_root,
    )
    samples = _value(await restarted.call(LIST_VOICE_SAMPLES, {"character": "Ana"}))["samples"]
    assert [s["task_id"] for s in samples] == [task_id]
    sample = samples[0]
    assert sample["status"] == "succeeded"
    assert sample["confirmable"] is True
    assert sample["cost"]["totals"] == {"USD": 0.0125}
    assert sample["cost"]["known"] is True
    assert (sample["provider_id"], sample["model"]) == ("fake-tts", "fake-model")

    confirmed = await restarted.confirm(task_id, "Ana")
    again = await restarted.confirm(task_id, "Ana")

    assert confirmed["already_bound"] is False
    assert again["already_bound"] is True
    assert confirmed["reference_sha256"] == sample["media"]["sha256"] == again["reference_sha256"]
    assert len(env.tts.calls) == calls_before
    assert await restarted.task_count() == 1


async def test_confirmation_refuses_foreign_or_mismatched_tasks(env: Env) -> None:
    task_id = await env.generate("Ana", "voice-a")

    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": task_id, "character": "Bento", "expect_unbound": True})
    ) == ("task_not_found")
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": "nope", "character": "Ana", "expect_unbound": True})
    ) == ("task_not_found")
    foreign = await env.call(
        CONFIRM_VOICE_SAMPLE, {"task_id": task_id, "character": "Ana", "expect_unbound": True}, project="other"
    )
    assert _problem_code(foreign) == "task_not_found"
    assert env.pm.load_project("other")["characters"]["Ana"].get("reference_audio") in (None, "")
    # A non-sample task of the same project is not a sample.
    other_task = await env.queue.enqueue_task(
        project_name=PROJECT, task_type="character", media_type="image", resource_id="Ana", payload={}
    )
    assert _problem_code(
        await env.call(
            CONFIRM_VOICE_SAMPLE, {"task_id": other_task["task_id"], "character": "Ana", "expect_unbound": True}
        )
    ) == ("task_not_found")
    inspect_foreign = await env.call(INSPECT_VOICE_REFERENCE, {"task_id": task_id}, project="other")
    assert _problem_code(inspect_foreign) == "task_not_found"


async def test_confirmation_refuses_unfinished_missing_and_altered_samples(env: Env) -> None:
    out = await env.call(GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-a", "text": "Oi."})
    pending = (await env.queue.list_tasks(project_name=PROJECT, task_type="voice_sample"))["items"][0]["task_id"]
    assert isinstance(_value(out), GenerationBatchReadModel)
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": pending, "character": "Ana", "expect_unbound": True})
    ) == ("voice_sample_not_ready")

    await env.run_worker()
    sample_path = env.pm.get_project_path(PROJECT) / resource_relative_path("audio", f"voice_sample__Ana__{pending}")
    sample_path.write_bytes(wav_bytes(4.0, frequency=99))
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": pending, "character": "Ana", "expect_unbound": True})
    ) == ("voice_sample_content_changed")
    listed = _value(await env.call(LIST_VOICE_SAMPLES, {}))["samples"][0]
    assert listed["media"]["state"] == "content_changed"
    assert listed["confirmable"] is False

    sample_path.unlink()
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": pending, "character": "Ana", "expect_unbound": True})
    ) == ("voice_sample_file_missing")
    assert _problem_code(await env.call(INSPECT_VOICE_REFERENCE, {"task_id": pending})) == "voice_sample_file_missing"
    assert _value(await env.call(LIST_VOICE_SAMPLES, {}))["samples"][0]["media"]["state"] == "missing"


async def test_renamed_character_and_concurrent_revision_are_refused(env: Env) -> None:
    first = await env.generate("Ana", "voice-a", "Um.")
    second = await env.generate("Ana", "voice-b", "Dois.")
    await env.confirm(first, "Ana")
    bound_sha = _value(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Ana"}))["media"]["sha256"]

    # Another client binds the second sample after our inspection.
    await env.confirm(second, "Ana")
    stale = await env.call(
        CONFIRM_VOICE_SAMPLE, {"task_id": first, "character": "Ana", "expected_reference_sha256": bound_sha}
    )
    assert _problem_code(stale) == "voice_reference_revision_conflict"
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": first, "character": "Ana", "expect_unbound": True})
    ) == ("voice_reference_revision_conflict")
    current = _value(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Ana"}))
    assert current["provenance"]["task_id"] == second

    def _rename(project: dict) -> None:
        project["characters"]["Ana Maria"] = project["characters"].pop("Ana")

    env.pm.update_project(PROJECT, _rename)
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": first, "character": "Ana", "expect_unbound": True})
    ) == ("character_not_found")
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": first, "character": "Ana Maria", "expect_unbound": True})
    ) == ("task_not_found")
    listed = _value(await env.call(LIST_VOICE_SAMPLES, {"character": "Ana"}))["samples"]
    assert {s["character_exists"] for s in listed} == {False}


async def test_post_generation_validation_failure_keeps_recorded_cost(env: Env) -> None:
    env.tts.seconds = 20.0  # outside the 2-10 second reference window
    out = await env.call(GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-a", "text": "Longo demais."})
    assert isinstance(_value(out), GenerationBatchReadModel)
    task = await env.run_worker()
    assert task["status"] == "failed"

    sample = _value(await env.call(LIST_VOICE_SAMPLES, {}))["samples"][0]
    assert sample["status"] == "failed"
    assert sample["error"]["code"]
    assert sample["confirmable"] is False
    # The provider was paid before validation failed: the recorded cost is reported, never zero by assumption.
    assert sample["cost"]["totals"] == {"USD": 0.0125}
    assert sample["cost"]["calls"][0]["amount"] == 0.0125
    assert _problem_code(
        await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": task["task_id"], "character": "Ana", "expect_unbound": True})
    ) == ("voice_sample_not_ready")


async def test_sample_without_recorded_call_is_not_reported_as_free(env: Env) -> None:
    task_id = await env.generate("Ana", "voice-a")
    async with env.factory() as session:
        from sqlalchemy import delete

        await session.execute(delete(ApiCall))
        await session.commit()
    cost = _value(await env.call(LIST_VOICE_SAMPLES, {}))["samples"][0]["cost"]
    assert cost["known"] is False
    assert cost["totals"] is None
    assert cost["reason"] == "no_provider_call_recorded"
    assert task_id


async def test_reads_and_confirmation_enqueue_nothing_and_call_no_tts(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_id = await env.generate("Ana", "voice-a")
    tasks_before = await env.task_count()
    calls_before = len(env.tts.calls)

    async def _no_enqueue(*_args, **_kwargs):
        raise AssertionError("no task may be enqueued")

    monkeypatch.setattr(env.queue, "enqueue_task", _no_enqueue)
    _value(await env.call(LIST_TTS_VOICES, {}))
    _value(await env.call(LIST_VOICE_SAMPLES, {}))
    _value(await env.call(INSPECT_VOICE_REFERENCE, {"task_id": task_id}))
    await env.confirm(task_id, "Ana")
    _value(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Ana", "transcribe": True, "language": "pt"}))
    _value(
        await env.call(GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-a", "text": "Oi", "preview": True})
    )

    assert await env.task_count() == tasks_before
    assert len(env.tts.calls) == calls_before


async def test_inspection_measures_audio_and_reports_provenance(env: Env) -> None:
    task_id = await env.generate("Ana", "voice-a", "Medindo.")
    sample = _value(await env.call(INSPECT_VOICE_REFERENCE, {"task_id": task_id}))

    assert sample["subject"] == "voice_sample"
    assert sample["bound"] is False
    assert sample["media"]["mime_type"] == "audio/wav"
    assert sample["media"]["format"] == "wav"
    assert sample["media"]["size_bytes"] > 0
    assert len(sample["media"]["sha256"]) == 64
    assert sample["measurement"]["available"] is True
    assert sample["measurement"]["duration_seconds"] == pytest.approx(3.0, abs=0.05)
    assert sample["measurement"]["audio_codec"]
    assert sample["within_reference_limits"] is True
    assert sample["provenance"] == {
        "source": "voice_sample_task",
        "task_id": task_id,
        "voice": "voice-a",
        "text": "Medindo.",
        "provider_id": "fake-tts",
        "model": "fake-model",
        "recorded_duration_seconds": pytest.approx(3.0, abs=0.05),
        "created_at": sample["provenance"]["created_at"],
    }
    assert "transcript" not in sample

    await env.confirm(task_id, "Ana")
    reference = _value(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Ana"}))
    assert reference["bound"] is True
    assert reference["media"]["sha256"] == sample["media"]["sha256"]
    assert reference["provenance"]["task_id"] == task_id


async def test_uploaded_reference_has_unknown_provenance(env: Env) -> None:
    target = env.pm.get_project_path(PROJECT) / "characters" / "refs_audio" / "Bento.wav"
    env.pm.install_character_reference_audio(PROJECT, "Bento", "characters/refs_audio/Bento.wav", wav_bytes(2.5))
    reference = _value(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Bento"}))
    assert target.is_file()
    assert reference["provenance"]["source"] == "unknown"
    assert reference["bound"] is True


async def test_missing_measurement_is_explicit(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.infra.ffmpeg import FfmpegUnavailableError

    task_id = await env.generate("Ana", "voice-a")

    async def _unavailable(_path, **_kwargs):
        raise FfmpegUnavailableError("no ffmpeg")

    monkeypatch.setattr(voice_tools, "probe_media", _unavailable)
    value = _value(await env.call(INSPECT_VOICE_REFERENCE, {"task_id": task_id}))
    assert value["measurement"] == {"available": False, "reason": "ffmpeg_unavailable"}
    assert value["within_reference_limits"] is None
    assert value["media"]["sha256"]


async def test_asr_absent_returns_explicit_limitation(env: Env) -> None:
    task_id = await env.generate("Ana", "voice-a")
    value = _value(await env.call(INSPECT_VOICE_REFERENCE, {"task_id": task_id, "transcribe": True, "language": "pt"}))

    transcript = value["transcript"]
    assert transcript["available"] is False
    assert "ARCREEL_SPEECH_REVIEW_MODEL" in transcript["limitation"]
    assert "voice identity" in transcript["limits"]
    # Metadata and the original sample stay available.
    assert value["media"]["sha256"]
    assert value["measurement"]["available"] is True


async def test_asr_is_blind(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    task_id = await env.generate("Ana", "voice-a", "Texto canônico secreto.")
    received: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def _recognize(*args, **kwargs):
        received.append((args, kwargs))
        return {
            "engine": "faster-whisper",
            "model_digest": "d",
            "language": "pt",
            "words": [{"text": " olá", "start": 0.0, "end": 0.5, "probability": 0.9}],
            "prompt_supplied": False,
        }

    monkeypatch.setattr(voice_tools, "transcribe_media", _recognize)
    value = _value(await env.call(INSPECT_VOICE_REFERENCE, {"task_id": task_id, "transcribe": True, "language": "pt"}))

    assert value["transcript"]["text"] == "olá"
    assert value["transcript"]["prompt_supplied"] is False
    ((args, kwargs),) = received
    assert len(args) == 1
    assert isinstance(args[0], Path)
    assert kwargs == {"language": "pt"}
    assert "Texto canônico secreto." not in repr(received)


@pytest.mark.parametrize(
    "arguments",
    [{}, {"character": "Ana", "task_id": "x"}, {"character": "Ana", "transcribe": True}],
)
async def test_inspection_request_validation(env: Env, arguments: dict[str, Any]) -> None:
    assert _problem_code(await env.call(INSPECT_VOICE_REFERENCE, arguments)) == "invalid_request"


async def test_media_resolvers_for_transport(env: Env) -> None:
    task_id = await env.generate("Ana", "voice-a")
    sample = await voice_references.resolve_voice_sample_media(PROJECT, task_id, projects=env.pm, queue=env.queue)
    assert sample.kind == "voice_sample"
    assert sample.task_id == task_id
    assert sample.relative_path.startswith("audio/")
    assert sample.version == f"sha256:{sample.sha256}"
    assert await voice_references.resolve_character_voice_reference_media(PROJECT, "Ana", projects=env.pm) is None
    await env.confirm(task_id, "Ana")
    bound = await voice_references.resolve_character_voice_reference_media(PROJECT, "Ana", projects=env.pm)
    assert bound is not None
    assert bound.sha256 == sample.sha256
    assert bound.relative_path == "characters/refs_audio/Ana.wav"


async def test_embedded_generation_waits_and_reports_unbound_sample(env: Env) -> None:
    from lib.generation.generation_queue_client import BatchTaskResult

    async def _waiter(*, specs, **_kwargs):
        (spec,) = specs
        assert (spec.task_type, spec.resource_id, spec.payload["voice"]) == ("voice_sample", "Bento", "voice-b")
        return [
            BatchTaskResult(resource_id="Bento", task_id="t-1", status="succeeded", result={"file_path": "audio/x.wav"})
        ], []

    caller = CallerContext(user_id="default", source="embedded", batch_waiter=_waiter)
    out = await invoke_declaration(
        GENERATE_VOICE_SAMPLE,
        {"character": "Bento", "voice": "voice-b", "text": "Oi."},
        ProjectScope(project_name=PROJECT, data_root=env.data_root),
        caller,
        env.services,
    )
    value = _value(out)
    result = value["generation_result"]
    assert result.succeeded == ["Bento"]
    assert result.items[0].task_id == "t-1"
    assert value["binds_reference"] is False
    assert env.pm.load_project(PROJECT)["characters"]["Bento"].get("reference_audio") in (None, "")


@pytest.mark.parametrize(
    "expectation",
    [{}, {"expect_unbound": True, "expected_reference_sha256": "a" * 64}, {"expect_unbound": False}],
)
async def test_confirmation_requires_exactly_one_expectation(env: Env, expectation: dict[str, Any]) -> None:
    task_id = await env.generate("Ana", "voice-a")
    out = await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": task_id, "character": "Ana", **expectation})
    assert _problem_code(out) == "invalid_request"
    assert env.pm.load_project(PROJECT)["characters"]["Ana"].get("reference_audio") in (None, "")


async def test_reference_pointer_outside_refs_audio_is_never_served(env: Env) -> None:
    """A PATCH can store any project-relative string; project.json must not be read as reference audio."""

    def _point_at_project_json(project: dict) -> None:
        project["characters"]["Ana"]["reference_audio"] = "project.json"

    env.pm.update_project(PROJECT, _point_at_project_json)

    with pytest.raises(ConflictError) as caught:
        await voice_references.resolve_character_voice_reference_media(PROJECT, "Ana", projects=env.pm)
    assert caught.value.key == "voice_reference_path_invalid"
    assert _problem_code(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Ana"})) == (
        "voice_reference_path_invalid"
    )
    listing = _value(await env.call(LIST_VOICE_SAMPLES, {}))
    assert "Ana" not in listing["characters_with_reference"]
    assert "project.json" not in repr(listing)

    # The invalid pointer counts as unbound: binding a real sample over it requires expect_unbound.
    task_id = await env.generate("Ana", "voice-a")
    _value(await env.call(CONFIRM_VOICE_SAMPLE, {"task_id": task_id, "character": "Ana", "expect_unbound": True}))
    assert env.pm.load_project(PROJECT)["characters"]["Ana"]["reference_audio"] == "characters/refs_audio/Ana.wav"
    assert (env.pm.get_project_path(PROJECT) / "project.json").is_file()


async def test_concurrent_mismatched_request_is_refused_not_attached(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two requests pass the pre-check together; the queue guard refuses the loser instead of attaching it."""
    winner = await env.queue.enqueue_task(
        project_name=PROJECT,
        task_type="voice_sample",
        media_type="audio",
        resource_id="Ana",
        payload={"prompt": "Primeiro.", "voice": "voice-a"},
    )
    real_lookup = voice_tools._active_sample_task_id
    calls = 0

    async def _stale_precheck(*args, **kwargs):
        nonlocal calls
        calls += 1
        return None if calls == 1 else await real_lookup(*args, **kwargs)

    monkeypatch.setattr(voice_tools, "_active_sample_task_id", _stale_precheck)
    out = await env.call(GENERATE_VOICE_SAMPLE, {"character": "Ana", "voice": "voice-b", "text": "Segundo."})

    problem = out.problem
    assert problem is not None
    assert problem.code == "voice_sample_in_progress"
    assert problem.params is not None
    assert problem.params["task_id"] == winner["task_id"]
    assert await env.task_count() == 1
    stored = await env.queue.get_task(winner["task_id"])
    assert stored is not None
    assert stored["payload"]["voice"] == "voice-a"


async def test_queue_dedupes_only_identical_voice_sample_requests(env: Env) -> None:
    from lib.generation.generation_queue import ActiveTaskRequestConflict

    base = {"project_name": PROJECT, "task_type": "voice_sample", "media_type": "audio", "resource_id": "Ana"}
    first = await env.queue.enqueue_task(**base, payload={"prompt": "Oi.", "voice": "voice-a"})
    same = await env.queue.enqueue_task(**base, payload={"prompt": "Oi.", "voice": "voice-a"})
    assert same["deduped"] is True
    assert same["task_id"] == first["task_id"]
    for payload in ({"prompt": "Oi.", "voice": "voice-b"}, {"prompt": "Tchau.", "voice": "voice-a"}):
        with pytest.raises(ActiveTaskRequestConflict):
            await env.queue.enqueue_task(**base, payload=payload)


async def test_inspection_materializes_working_files_before_reading(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    import contextlib

    task_id = await env.generate("Ana", "voice-a")
    held: list[list[str]] = []

    @contextlib.asynccontextmanager
    async def _recording(project_path, paths, *, session_factory=None):
        assert session_factory is env.factory
        held.append([str(p) for p in paths])
        yield

    monkeypatch.setattr(voice_tools, "local_work_files", _recording)
    _value(await env.call(INSPECT_VOICE_REFERENCE, {"task_id": task_id}))
    await env.confirm(task_id, "Ana")
    held.clear()
    _value(await env.call(INSPECT_VOICE_REFERENCE, {"character": "Ana"}))
    assert held == [["characters/refs_audio/Ana.wav"]]
