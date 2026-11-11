"""An external agent runs ArcReel production exclusively through the official remote MCP.

Every step below is a tool call or resource read made by a real ``mcp.ClientSession`` over streamable HTTP
(``httpx.ASGITransport``) against ``build_remote_mcp_server`` with an API-key Bearer. Nothing is written to the project
directory or database by the test itself except through those calls; the only helpers that touch the queue directly
simulate the generation worker (claim → production ``execute_generation_task`` → settle), because the worker is a host
process, not an MCP client capability.

Providers are simulated at the backend-assembly seam (``assemble_backend``) and provider resolution
(``ConfigResolver.resolve_*_backend``); MediaGenerator, version history, usage ledger, queue and artifact manifest are
real. No paid call, network, real credential or real data is reached. A passing run proves the MCP surface and native
transactions agree under fakes; it is not production verification of any provider or MCP client (Claude CLI / Codex).
"""

from __future__ import annotations

import base64
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession
from mcp.types import BlobResourceContents

from lib.config.resolver import ConfigResolver, ProviderModel
from lib.custom_provider.declarative_backend import ProviderJobRejectedError
from lib.db.repositories.usage_repo import UsageRepository
from lib.generation.generation_queue import GenerationQueue
from lib.project.project_manager import ProjectManager
from lib.workflow.workflow_state import WorkflowActionType
from server.agent_toolset.global_config import GLOBAL_CONFIG_TOOL_IDS
from server.remote_mcp import ArcApiKeyVerifier, build_remote_mcp_server
from server.services.media_transport import uploads
from server.services.project.workflow_planner import WorkflowPlanner
from server.services.tasks import generation_context
from server.tool_runtime import Services
from tests.fakes import bind_safe_session_factory, bind_session_factory, use_backend_assembler, use_project_manager
from tests.integration.server.mcp_journey_support import (
    API_KEY,
    AUDIO_PROVIDER,
    IMAGE_PROVIDER,
    OTHER_API_KEY,
    PROVIDER_SECRET,
    SIGNED_URL,
    FakeAudioBackend,
    FakeImageBackend,
    FakeRetrievalWorker,
    Journey,
    assert_no_leaks,
    b64,
    describe,
    download,
    jpeg_bytes,
    plan_tool_names,
    png_bytes,
    problem,
    sha256,
    stage_upload,
    structured,
)

PROJECT = "journey"
SCRIPT = "episode_1.json"
CHARACTER = "小雨"
PRODUCT = "保温杯"
NARRATOR_VOICE = "Ethan"
CHARACTER_VOICE = "Cherry"
STAGING_CHUNK = 4096


@pytest.fixture
async def journey(
    tmp_path: Path, concurrent_session_factory, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Journey]:
    factory = concurrent_session_factory
    bind_session_factory(monkeypatch, factory)
    bind_safe_session_factory(monkeypatch, factory)
    # The usage ledger imports the safe factory at module load; bind it so provider-call records share the test DB.
    monkeypatch.setattr("lib.billing.ledger.safe_session_factory", factory)
    monkeypatch.delenv("ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS", raising=False)
    # Small staging chunks so a few-KiB photo really travels as several chunks.
    monkeypatch.setattr(uploads, "UPLOAD_CHUNK_SIZE", STAGING_CHUNK)
    projects = ProjectManager(tmp_path / "root")
    use_project_manager(monkeypatch, projects)
    image, audio = FakeImageBackend(), FakeAudioBackend()

    async def _image(self, project, payload, *, generation_type=None, **_kw):
        return ProviderModel(*IMAGE_PROVIDER)

    async def _audio(self, project, payload, **_kw):
        return ProviderModel(*AUDIO_PROVIDER)

    async def _assemble(*, media_type: str, **_kw):
        return {"image": image, "audio": audio}[media_type]

    monkeypatch.setattr(ConfigResolver, "resolve_image_backend", _image)
    monkeypatch.setattr(ConfigResolver, "resolve_audio_backend", _audio)
    use_backend_assembler(monkeypatch, _assemble)
    generation_context.invalidate_backend_cache()

    queue = GenerationQueue(session_factory=factory, project_manager=projects)
    # Enqueue refuses work while no worker holds the lease; the test drives execution itself through Journey.run_one.
    assert await queue.acquire_or_renew_worker_lease(name="default", owner_id="journey-worker", ttl_seconds=600)
    retrieval = FakeRetrievalWorker()
    services = Services(
        projects=projects,
        workflow_planner=WorkflowPlanner(projects),
        capabilities=ConfigResolver(factory),
        queue=queue,
        sessions=factory,
        artifact_download_worker=retrieval,
    )

    async def verify_api_key(token: str):
        subjects = {API_KEY: "apikey:journey", OTHER_API_KEY: "apikey:other"}
        return {"sub": subjects[token], "via": "apikey"} if token in subjects else None

    def server_factory():
        return build_remote_mcp_server(
            projects=projects, services=services, token_verifier=ArcApiKeyVerifier(verify_api_key)
        )

    yield Journey(
        server=server_factory(),
        projects=projects,
        queue=queue,
        image=image,
        audio=audio,
        root=tmp_path,
        retrieval=retrieval,
        sessions=factory,
        server_factory=server_factory,
    )
    generation_context.invalidate_backend_cache()


def _forbidden(journey: Journey) -> list[str]:
    return [
        str(journey.root),
        os.path.realpath(journey.root),
        API_KEY,
        OTHER_API_KEY,
        PROVIDER_SECRET,
        "X-Amz-Signature",
        "deadbeefcafe",
    ]


async def _bootstrap(journey: Journey, session: ClientSession, name: str = PROJECT) -> dict[str, Any]:
    """Step 1: create the project, an episode and its blank formal script, register assets and write one entry."""
    created = structured(
        await journey.call(
            session,
            "create_project",
            None,
            name=name,
            title="Journey",
            content_mode="narration",
            generation_mode="storyboard",
            narration_delivery="use_tts",
            audio_backend="/".join(AUDIO_PROVIDER),
            narration_voice=NARRATOR_VOICE,
        )
    )["project"]
    assert created["name"] == name
    episode = structured(await journey.call(session, "create_episode", name, title="Rain"))["episode"]
    blank = structured(await journey.call(session, "start_blank_script", name, episode_id=episode["episode_id"]))
    assert blank["start_blank_script"]["created"] is True
    assert blank["start_blank_script"]["script_file"] == SCRIPT
    structured(
        await journey.call(
            session,
            "patch_project",
            name,
            table="characters",
            entries={CHARACTER: {"description": "穿红雨衣的女孩", "voice_style": "温柔"}},
        )
    )
    structured(
        await journey.call(
            session, "patch_project", name, table="products", entries={PRODUCT: {"description": "不锈钢保温杯"}}
        )
    )
    script = structured(await journey.call(session, "get_episode_script", name, script=SCRIPT))["episode_script"]
    patch = structured(
        await journey.call(
            session,
            "patch_episode_script",
            name,
            script=SCRIPT,
            base_revision=script["revision"],
            operations=[
                {
                    "op": "insert",
                    "item": {
                        "duration_seconds": 4,
                        "novel_text": "小雨在雨中奔跑。",
                        "characters_in_segment": [CHARACTER],
                        "image_prompt": "小雨在雨中奔跑",
                        "video_prompt": "镜头跟随小雨",
                    },
                }
            ],
        )
    )
    plan = structured(await journey.call(session, "get_workflow_plan", name, episode_id=episode["episode_id"]))
    return {"episode_id": episode["episode_id"], "patch": patch, "plan": plan["workflow_plan"]}


def _segment_id(journey: Journey, name: str = PROJECT) -> str:
    # Read-only inspection of the result of MCP writes (assertion only; never used to drive production).
    script = journey.projects.load_script(name, SCRIPT)
    return script["segments"][0]["segment_id"]


# ---------------------------------------------------------------------------
# Steps 1, 2, 4: bootstrap, references through staging, previews/quotes enqueue nothing
# ---------------------------------------------------------------------------


async def test_bootstrap_references_and_previews_enqueue_nothing(journey: Journey) -> None:
    char_ref = png_bytes((200, 30, 30))
    photo_a, photo_b = jpeg_bytes((10, 200, 10), (160, 160)), jpeg_bytes((10, 10, 200))
    sheet = png_bytes((90, 90, 90), (96, 128))

    async with journey.session() as session:
        boot = await _bootstrap(journey, session)
        assert boot["plan"]["status"]["target"]["script_filename"] == SCRIPT

        # Step 2: references. Character image inline (upload_reference has no staged form), product photos staged
        # chunk-by-chunk and installed in order, and a finished product sheet installed from a staged upload.
        structured(
            await journey.call(
                session,
                "upload_reference",
                PROJECT,
                kind="character_image",
                name=CHARACTER,
                filename="xiaoyu.png",
                content_base64=b64(char_ref),
            )
        )
        staged_a = await stage_upload(
            journey, session, PROJECT, "cup-front.jpg", photo_a, "product_reference_image", STAGING_CHUNK
        )
        products = structured(
            await journey.call(
                session,
                "upload_product_reference_images",
                PROJECT,
                product=PRODUCT,
                images=[
                    {"filename": "cup-front.jpg", "staged_upload_id": staged_a},
                    {"filename": "cup-side.jpg", "content_base64": b64(photo_b)},
                ],
            )
        )
        listed = structured(await journey.call(session, "list_product_reference_images", PROJECT, product=PRODUCT))
        staged_sheet = await stage_upload(
            journey, session, PROJECT, "cup-sheet.png", sheet, "asset_image", STAGING_CHUNK
        )
        installed = structured(
            await journey.call(
                session,
                "install_finished_media",
                PROJECT,
                target={"kind": "asset_sheet", "asset_type": "product", "name": PRODUCT},
                file={"filename": "cup-sheet.png", "staged_upload_id": staged_sheet},
            )
        )
        first = await describe(
            journey, session, PROJECT, {"kind": "product_reference_image", "product": PRODUCT, "index": 0}
        )
        second = await describe(
            journey, session, PROJECT, {"kind": "product_reference_image", "product": PRODUCT, "index": 1}
        )
        first_bytes = await download(journey, session, PROJECT, first)
        second_bytes = await download(journey, session, PROJECT, second)
        sheet_media = await describe(
            journey, session, PROJECT, {"kind": "asset_sheet", "asset_type": "product", "name": PRODUCT}
        )
        sheet_bytes = await download(journey, session, PROJECT, sheet_media)

        # Step 4: every preview / quote / read; none may enqueue a task or reach a provider.
        segment = _segment_id(journey)
        previews = [
            await journey.call(session, "get_prompt_preview", PROJECT, script=SCRIPT, item_id=segment),
            await journey.call(session, "get_asset_prompt_preview", PROJECT, asset_type="character", name=CHARACTER),
            await journey.call(session, "quote_assets", PROJECT, type="character", names=[CHARACTER]),
            await journey.call(session, "quote_storyboards", PROJECT, episode_id=1),
            await journey.call(
                session,
                "generate_voice_sample",
                PROJECT,
                character=CHARACTER,
                voice=CHARACTER_VOICE,
                text="你好，我是小雨。",
                preview=True,
            ),
            await journey.call(session, "list_tts_voices", PROJECT),
            await journey.call(session, "get_project_content", PROJECT),
        ]
        plan_after = structured(await journey.call(session, "get_workflow_plan", PROJECT, episode_id=1))

    # Staged and inline photos install byte-for-byte, in the given order, without queuing generation.
    installed_photos = products["product_reference_images"]["installed"]
    assert [photo["sha256"] for photo in installed_photos] == [sha256(photo_a), sha256(photo_b)]
    assert all(photo["bytes_preserved"] for photo in installed_photos)
    assert products["product_reference_images"]["generation_submitted"] is False
    listed_refs = listed["product_reference_images"]["reference_images"]
    assert [(ref["index"], ref["sha256"]) for ref in listed_refs] == [(0, sha256(photo_a)), (1, sha256(photo_b))]
    sheet_install = installed["installed_media"]
    assert (sheet_install["version_source"], sheet_install["generation_submitted"]) == ("manual_upload", False)
    assert sheet_install["installed_sha256"] == sha256(sheet)
    assert (first["sha256"], second["sha256"]) == (sha256(photo_a), sha256(photo_b))
    assert (first_bytes, second_bytes) == (photo_a, photo_b)
    assert sheet_bytes == sheet
    for result in previews:
        structured(result)
    assert "workflow_plan" in plan_after
    assert await journey.task_total() == 0
    assert journey.image.calls == []
    assert journey.audio.calls == []
    assert_no_leaks(journey.seen, _forbidden(journey))


# ---------------------------------------------------------------------------
# Step 3: character voice reference vs narrator voice
# ---------------------------------------------------------------------------


async def test_character_voice_reference_is_separate_from_narrator(journey: Journey) -> None:
    async with journey.session() as session:
        await _bootstrap(journey, session)
        voices = structured(await journey.call(session, "list_tts_voices", PROJECT))
        unbound = structured(await journey.call(session, "inspect_voice_reference", PROJECT, character=CHARACTER))
        submitted = structured(
            await journey.call(
                session,
                "generate_voice_sample",
                PROJECT,
                character=CHARACTER,
                voice=CHARACTER_VOICE,
                text="你好，我是小雨。",
            )
        )
        tasks_after_submit = await journey.task_total()
        settled = await journey.run_one("audio")
        samples = structured(await journey.call(session, "list_voice_samples", PROJECT, character=CHARACTER))
        task_id = settled["task_id"]
        sample_view = structured(await journey.call(session, "inspect_voice_reference", PROJECT, task_id=task_id))
        blind = await journey.call(session, "confirm_voice_sample", PROJECT, task_id=task_id, character=CHARACTER)
        confirmed = structured(
            await journey.call(
                session, "confirm_voice_sample", PROJECT, task_id=task_id, character=CHARACTER, expect_unbound=True
            )
        )
        repeated = structured(
            await journey.call(
                session,
                "confirm_voice_sample",
                PROJECT,
                task_id=task_id,
                character=CHARACTER,
                expected_reference_sha256=confirmed["voice_sample_confirmation"]["reference_sha256"],
            )
        )
        bound = structured(await journey.call(session, "inspect_voice_reference", PROJECT, character=CHARACTER))
        media = await describe(journey, session, PROJECT, {"kind": "character_voice_reference", "character": CHARACTER})
        reference_bytes = await download(journey, session, PROJECT, media)
        content = structured(await journey.call(session, "get_project_content", PROJECT))

    # Discovery: voices come from the (fake) backend, not a fixed list; the narrator voice is one of them.
    assert voices["tts_voices"]["configured"] is True
    assert {voice["id"] for voice in voices["tts_voices"]["voices"]} == {CHARACTER_VOICE, NARRATOR_VOICE}
    assert unbound["voice_reference_inspection"]["bound"] is False
    # One paid sample, synthesized with the explicit character voice, never the narrator fallback.
    (member,) = submitted["generation_batch"]["members"]
    assert (member["task_type"], member["status"], member["unit_id"]) == ("voice_sample", "queued", CHARACTER)
    assert settled["status"] == "succeeded"
    assert [call.voice for call in journey.audio.calls] == [CHARACTER_VOICE]
    (sample,) = samples["voice_samples"]["samples"]
    assert (sample["task_id"], sample["voice"], sample["confirmable"], sample["bound"]) == (
        task_id,
        CHARACTER_VOICE,
        True,
        False,
    )
    sample_sha = sample["media"]["sha256"]
    assert sample_view["voice_reference_inspection"]["media"]["sha256"] == sample_sha
    assert sample_view["voice_reference_inspection"]["within_reference_limits"] is True
    # Confirmation without a stated expectation is refused (default deny on blind overwrite).
    assert blind.isError
    assert confirmed["voice_sample_confirmation"]["bound"] is True
    assert confirmed["voice_sample_confirmation"]["reference_sha256"] == sample_sha
    assert repeated["voice_sample_confirmation"]["already_bound"] is True
    assert bound["voice_reference_inspection"]["bound"] is True
    assert bound["voice_reference_inspection"]["provenance"]["voice"] == CHARACTER_VOICE
    # The bound bytes are exactly the sample bytes and match the on-disk reference audio.
    assert media["sha256"] == sample_sha == sha256(reference_bytes)
    project = content["project_content"]["project"]
    on_disk = (
        journey.projects.get_project_path(PROJECT) / project["characters"][CHARACTER]["reference_audio"]
    ).read_bytes()
    assert on_disk == reference_bytes
    # Character voice and narrator voice stay separate settings.
    assert project["narration_voice"] == NARRATOR_VOICE
    # Discovery, inspection, listing and confirmation queued nothing: only the one explicit sample task exists.
    assert await journey.task_total() == tasks_after_submit == 1
    assert_no_leaks(journey.seen, _forbidden(journey))


# ---------------------------------------------------------------------------
# Steps 5 and 7: one paid submission, reconnect dedupe, worker completion, deliverable download
# ---------------------------------------------------------------------------


async def test_generation_dedupes_across_reconnect_and_deliverable_downloads(journey: Journey) -> None:
    request = {"type": "character", "names": [CHARACTER]}
    async with journey.session() as session:
        await _bootstrap(journey, session)
        first = structured(await journey.call(session, "generate_assets", PROJECT, **request))["generation_batch"]

    # The host restarts and the client reconnects with a brand-new session, re-sending the identical request: the
    # durable queue dedupes it onto the same task instead of submitting a second paid job.
    journey.restart_host()
    async with journey.session() as session:
        again = structured(await journey.call(session, "generate_assets", PROJECT, **request))["generation_batch"]
        tasks_before_run = await journey.task_total()
        settled = await journey.run_one("image")
        polled = structured(await journey.call(session, "get_generation_batch", PROJECT, batch_id=first["batch_id"]))[
            "generation_batch"
        ]
        replayed = structured(await journey.call(session, "get_generation_batch", PROJECT, batch_id=again["batch_id"]))[
            "generation_batch"
        ]
        media = await describe(
            journey, session, PROJECT, {"kind": "asset_sheet", "asset_type": "character", "name": CHARACTER}
        )
        delivered = await download(journey, session, PROJECT, media)
        via_resource = await session.read_resource(f"arcreel://media/{PROJECT}/{media['media_id']}/0")
        # After completion a reconnecting client that lost the batch handle re-plans with the missing-only selection.
        missing_only = await journey.call(session, "generate_assets", PROJECT, type="character")

    (member,) = first["members"]
    (replay,) = again["members"]
    assert member["deduped"] is False
    assert replay["deduped"] is True
    assert replay["task_id"] == member["task_id"]
    assert tasks_before_run == 1
    assert settled["status"] == "succeeded"
    assert len(journey.image.calls) == 1
    assert polled["done"] is True
    assert polled["members"][0]["status"] == "succeeded"
    assert replayed["members"][0]["task_id"] == member["task_id"]
    on_disk = (journey.projects.get_project_path(PROJECT) / f"characters/{CHARACTER}.png").read_bytes()
    assert delivered == on_disk
    assert media["sha256"] == sha256(on_disk)
    (contents,) = via_resource.contents
    assert isinstance(contents, BlobResourceContents)
    assert contents.mimeType == "application/octet-stream"
    assert base64.b64decode(contents.blob) == on_disk[: media["chunk_size"]]
    # The missing-only resend after completion skips the current sheet: no second paid task.
    resend = structured(missing_only)["generation_batch"]
    assert resend["members"] == []
    assert [skip["unit_id"] for skip in resend["skipped"]] == [f"character/{CHARACTER}"]
    assert await journey.task_total() == 1
    assert len(journey.image.calls) == 1
    assert_no_leaks(journey.seen, _forbidden(journey))


# ---------------------------------------------------------------------------
# Step 6: provider failure → sanitized diagnostics, no automatic paid retry
# ---------------------------------------------------------------------------


async def test_provider_failure_diagnostics_are_sanitized_and_not_retried(journey: Journey) -> None:
    journey.image.fail_with = ProviderJobRejectedError(
        provider_error_code="1026",
        provider_error_message=(
            f"content moderation rejected the prompt; key={PROVIDER_SECRET} result at {SIGNED_URL}"
        ),
        stage="poll",
        provider_status="failed",
    )
    async with journey.session() as session:
        await _bootstrap(journey, session)
        submitted = structured(
            await journey.call(session, "generate_assets", PROJECT, type="character", names=[CHARACTER])
        )["generation_batch"]
        settled = await journey.run_one("image")
        polled = structured(
            await journey.call(session, "get_generation_batch", PROJECT, batch_id=submitted["batch_id"])
        )["generation_batch"]
        diagnostics = structured(
            await journey.call(
                session,
                "get_generation_diagnostics",
                PROJECT,
                task_id=settled["task_id"],
                include_provider_response=True,
            )
        )
        plan = structured(await journey.call(session, "get_workflow_plan", PROJECT, episode_id=1))

    assert settled["status"] == "failed"
    item = polled["generation_result"]["items"][0]
    assert item["problem"]["code"] == "provider_job_failed_coded"
    assert item["problem"]["action"] == "retry"
    report = diagnostics["generation_diagnostics"]
    assert report["task"]["task_id"] == settled["task_id"]
    assert report["problem"]["code"] == "provider_job_failed_coded"
    assert report["provider_error"]["code"] == "1026"
    assert "content moderation rejected the prompt" in report["provider_error"]["message"]
    # Credentials are masked and signed-URL queries stripped (asserted globally by assert_no_leaks below).
    assert "https://cdn.provider.example/out/job-77.png" in report["provider_error"]["message"]
    assert report["recovery"]["action"] == "retry"
    assert "authorization" in report["recovery"]["guidance"]
    # The failed provider call is settled in the usage ledger and linked to the task, with the same redaction.
    assert (report["usage_record"]["task_id"], report["usage_record"]["status"]) == (settled["task_id"], "failed")
    assert polled["done"] is True
    assert polled["members"][0]["status"] == "failed"
    assert len(journey.image.calls) == 1
    queued = await journey.queue.list_tasks(project_name=PROJECT, status="queued")
    assert queued["total"] == 0
    assert await journey.task_total() == 1
    assert "workflow_plan" in plan
    assert_no_leaks(journey.seen, _forbidden(journey))


HISTORICAL_GENERIC = "provider reported failure (status: failed)"
HISTORICAL_MESSAGE = 'content[5].audio_url: invalid param: audio format ".x-wav" not allowed'


async def test_historical_generic_failure_diagnostics_read_the_persisted_provider_verdict(journey: Journey) -> None:
    """A failure settled before ``extract.error_code`` support: only the persisted response carries the real code."""
    journey.image.fail_with = RuntimeError(HISTORICAL_GENERIC)
    async with journey.session() as session:
        await _bootstrap(journey, session)
        structured(await journey.call(session, "generate_assets", PROJECT, type="character", names=[CHARACTER]))
        settled = await journey.run_one("image")
        # Worker side only: the backend's provider-response hook persisted the last body through the native ledger
        # repository (the image fake has no such hook), exactly as the historical MiniMax H3 row stores it.
        async with journey.sessions() as db:
            usage = UsageRepository(db)
            record = await usage.get_latest_record_for_task(PROJECT, settled["task_id"])
            assert record is not None
            await usage.update_last_provider_response(
                record["id"],
                {
                    "task": {
                        "id": "461931341250972",
                        "model": "MiniMax-H3",
                        "status": "failed",
                        "error": {"code": "2013", "message": HISTORICAL_MESSAGE},
                    },
                    "debug": {"Authorization": f"Bearer {PROVIDER_SECRET}", "result": SIGNED_URL},
                },
            )
            before = await usage.get_latest_record_for_task(PROJECT, settled["task_id"])
        tasks_before = await journey.task_total()
        diagnostics = structured(
            await journey.call(
                session,
                "get_generation_diagnostics",
                PROJECT,
                task_id=settled["task_id"],
                include_provider_response=True,
            )
        )["generation_diagnostics"]
        async with journey.sessions() as db:
            after = await UsageRepository(db).get_latest_record_for_task(PROJECT, settled["task_id"])

    assert settled["status"] == "failed"
    error = diagnostics["provider_error"]
    assert (error["code"], error["code_known"], error["message"]) == ("2013", True, HISTORICAL_MESSAGE)
    assert error["source"] == "last_provider_response"
    assert error["source_path"] == "$.last_provider_response.body.task.error"
    assert error["source_truncated"] is False
    assert HISTORICAL_GENERIC in error["stored_message"]
    # Internal codes stay separate from the provider's own code.
    assert diagnostics["problem"]["code"] != "2013"
    assert diagnostics["usage_record"]["error_code"] is None
    assert diagnostics["recovery"]["action"] == "retry"
    assert "authorization" in diagnostics["recovery"]["guidance"]
    assert diagnostics["provider_calls"] == 0
    # Read-only: no row changed, nothing enqueued, no further provider call.
    assert after == before
    assert await journey.task_total() == tasks_before == 1
    assert len(journey.image.calls) == 1
    assert_no_leaks(journey.seen, _forbidden(journey))


# ---------------------------------------------------------------------------
# Step 8: no escape hatches, gated global configuration, scope refusals, no leaks
# ---------------------------------------------------------------------------

_ESCAPE_NAME_FRAGMENTS = ("sql", "shell", "exec", "bash", "command", "http_request", "fetch_url", "filesystem")
_ESCAPE_DESCRIPTION_PHRASES = ("run sql", "execute sql", "shell command", "arbitrary http", "arbitrary file", "any url")


async def test_catalog_has_no_escape_hatches_and_scope_is_enforced(
    journey: Journey, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with journey.host():
        async with journey.session(nested=True) as session:
            await _bootstrap(journey, session)
            await _bootstrap(journey, session, name="other")
            tools = (await session.list_tools()).tools
            names = {tool.name for tool in tools}
            refusals = {
                "dotdot_project": await journey.call(session, "get_workflow_plan", "../journey", episode_id=1),
                "absolute_project": await journey.call(
                    session, "get_workflow_plan", str(journey.projects.get_project_path(PROJECT)), episode_id=1
                ),
                "dotdot_file": await journey.call(session, "read_project_file", PROJECT, path="../other/project.json"),
                "absolute_file": await journey.call(
                    session,
                    "read_project_file",
                    PROJECT,
                    path=str(journey.projects.get_project_path("other") / "project.json"),
                ),
                "dotdot_upload_name": await journey.call(
                    session,
                    "upload_reference",
                    PROJECT,
                    kind="character_image",
                    name=CHARACTER,
                    filename="../../escape.png",
                    content_base64=b64(png_bytes((1, 2, 3))),
                ),
                "dotdot_source_name": await journey.call(
                    session, "upload_source", PROJECT, filename="../escape.txt", content="越界"
                ),
            }
            # A media_id minted for one project is refused when presented under another project.
            photo = jpeg_bytes((7, 7, 7))
            structured(
                await journey.call(
                    session,
                    "upload_product_reference_images",
                    PROJECT,
                    product=PRODUCT,
                    images=[{"filename": "cup.jpg", "content_base64": b64(photo)}],
                )
            )
            journey_media = await describe(
                journey, session, PROJECT, {"kind": "product_reference_image", "product": PRODUCT, "index": 0}
            )
            foreign_chunk = await journey.call(
                session, "read_media_chunk", "other", media_id=journey_media["media_id"], index=0
            )
            foreign_describe = await journey.call(
                session,
                "describe_media",
                "other",
                selector={"kind": "product_reference_image", "product": PRODUCT, "index": 0},
            )
        async with journey.session(OTHER_API_KEY, nested=True) as other_key_session:
            other_key_names = {tool.name for tool in (await other_key_session.list_tools()).tools}

    # The operator grants global configuration to the "journey" key name only; a restarted host exposes the tools to
    # that key and still hides them from every other key.
    monkeypatch.setenv("ARCREEL_MCP_GLOBAL_CONFIG_API_KEYS", "journey")
    journey.restart_host()
    async with journey.host():
        async with journey.session(nested=True) as granted:
            granted_names = {tool.name for tool in (await granted.list_tools()).tools}
            granted_call = await journey.call(granted, "list_global_endpoints", None)
        async with journey.session(OTHER_API_KEY, nested=True) as denied:
            denied_names = {tool.name for tool in (await denied.list_tools()).tools}
            denied_call = await journey.call(denied, "list_global_providers", None)

    for name in names:
        lowered = name.lower()
        assert not any(fragment in lowered for fragment in _ESCAPE_NAME_FRAGMENTS), name
    for tool in tools:
        description = (tool.description or "").lower()
        assert not any(phrase in description for phrase in _ESCAPE_DESCRIPTION_PHRASES), tool.name
    # Global endpoint/provider configuration is hidden from every key unless the operator grants it.
    assert not names & GLOBAL_CONFIG_TOOL_IDS
    assert not other_key_names & GLOBAL_CONFIG_TOOL_IDS
    assert granted_names == names | GLOBAL_CONFIG_TOOL_IDS
    assert not granted_call.isError
    assert structured(granted_call)["endpoints"]
    assert denied_names == names
    assert not denied_names & GLOBAL_CONFIG_TOOL_IDS
    assert denied_call.isError
    assert {label: problem(result)["code"] for label, result in refusals.items()} == {
        "dotdot_project": "invalid_project",
        "absolute_project": "invalid_project",
        "dotdot_file": "unsafe_path",
        "absolute_file": "unsafe_path",
        "dotdot_upload_name": "invalid_request",
        "dotdot_source_name": "invalid_request",
    }
    assert problem(foreign_chunk)["code"] == "media_project_mismatch"
    # The other project has no photos of its own: its namespace never resolves to this project's files.
    assert foreign_describe.isError
    assert_no_leaks(journey.seen, _forbidden(journey))
    assert await journey.task_total() == 0


# ---------------------------------------------------------------------------
# Step 9: every official workflow variant plans only actions an MCP client can perform
# ---------------------------------------------------------------------------

#: How an external MCP client performs each ``WorkflowActionType`` with the official remote tools. Report-only actions
#: map to the read tools that let the client explain the state; an empty set would mean "only the Web UI can do it".
ACTION_TOOLS: dict[str, frozenset[str]] = {
    "none": frozenset({"get_workflow_plan"}),
    "collect_project_input": frozenset({"upload_source", "patch_project"}),
    "create_episode": frozenset({"create_episode"}),
    "draft_selling_points": frozenset({"patch_project"}),
    "plan_episodes": frozenset({"plan_episodes"}),
    "reset_episode_planning": frozenset({"reset_episode_planning"}),
    "resolve_draft": frozenset({"open_draft", "patch_draft", "promote_draft", "discard_draft"}),
    "prepare_script_plan": frozenset({"generate_script_plan"}),
    "start_blank_script": frozenset({"start_blank_script"}),
    "provide_episode_source": frozenset({"upload_source", "edit_source_text"}),
    "confirm_script_plan": frozenset({"confirm_script_review"}),
    "generate_script": frozenset({"generate_episode_script"}),
    "add_script_items": frozenset({"patch_episode_script"}),
    "author_prompts": frozenset({"generate_episode_script"}),
    "generate_asset_sheets": frozenset({"generate_assets", "install_finished_media"}),
    "generate_storyboards": frozenset({"generate_storyboards", "install_finished_media"}),
    "generate_grid": frozenset({"generate_grid", "list_grids", "inspect_grid", "split_grids"}),
    "repair_video_units": frozenset({"get_episode_script", "patch_episode_script"}),
    "generate_videos": frozenset({"generate_videos", "install_finished_media"}),
    "create_edit_timeline": frozenset({"create_timeline"}),
    "retry_project_migration": frozenset({"retry_project_migration"}),
    "patch_episode_script": frozenset({"patch_episode_script"}),
    "retry": frozenset({"get_generation_diagnostics"}),
    "fix_input": frozenset({"patch_episode_script", "patch_project"}),
    "generate_dependency": frozenset({"generate_assets", "generate_storyboards"}),
    "wait_for_task": frozenset({"get_generation_batch"}),
    "replan_unit": frozenset({"get_episode_script", "patch_episode_script"}),
    "confirm_request_duration": frozenset({"get_workflow_plan"}),
    "configure_provider": frozenset({"configure_project", "get_effective_configuration"}),
    "repair_artifact_state": frozenset({"get_workflow_plan", "list_media_versions", "select_media_version"}),
    # The provider already produced the artifact but retrieval failed: resume the same task, never resubmit generation.
    "retry_artifact_download": frozenset({"retry_artifact_download", "get_generation_diagnostics"}),
}

#: Actions with no MCP tool yet.
MCP_GAPS: frozenset[str] = frozenset()

#: The eight official workflows (docs/workflows): content mode x generation mode, plus grid storyboards on the two
#: storyboard routes that support them (ads refuse grids; reference video has no storyboard-image step).
VARIANTS = [
    ("drama", "storyboard", False),
    ("drama", "storyboard", True),
    ("drama", "reference_video", False),
    ("narration", "storyboard", False),
    ("narration", "storyboard", True),
    ("narration", "reference_video", False),
    ("ad", "storyboard", False),
    ("ad", "reference_video", False),
]


def _actions(plan: dict[str, Any]) -> set[str]:
    found = {plan["next_action"]["type"], *(alt["type"] for alt in plan.get("next_alternatives", []))}
    found |= {step["action"]["type"] for step in plan.get("steps", []) if step.get("action")}
    return found


async def test_action_table_covers_every_workflow_action_with_live_tools(journey: Journey) -> None:
    async with journey.session() as session:
        tools = (await session.list_tools()).tools
    catalog = {tool.name for tool in tools}
    create_schema = next(tool for tool in tools if tool.name == "create_project").inputSchema["properties"]

    assert set(ACTION_TOOLS) == {member.value for member in WorkflowActionType}
    for action, needed in ACTION_TOOLS.items():
        assert bool(needed) is (action not in MCP_GAPS), action
        assert needed <= catalog, (action, needed - catalog)
    derived = {
        (content, generation, grid)
        for content in create_schema["content_mode"]["enum"]
        for generation in create_schema["generation_mode"]["enum"]
        for grid in (False, True)
        if not grid or (generation == "storyboard" and content != "ad")
    }
    assert derived == set(VARIANTS)


@pytest.mark.parametrize(("content_mode", "generation_mode", "grid"), VARIANTS)
async def test_workflow_variant_plans_only_mcp_reachable_actions(
    journey: Journey, content_mode: str, generation_mode: str, grid: bool
) -> None:
    name = f"{content_mode}-{generation_mode.replace('_', '-')}{'-grid' if grid else ''}"
    extra: dict[str, Any] = {"target_duration": 30, "brief": "保温杯卖点"} if content_mode == "ad" else {}
    plans: list[dict[str, Any]] = []
    async with journey.session() as session:
        created = await journey.call(
            session,
            "create_project",
            None,
            name=name,
            title=name,
            content_mode=content_mode,
            generation_mode=generation_mode,
            grid_storyboard=grid,
            **extra,
        )
        assert structured(created)["project"]["project"]["generation_mode"] == generation_mode
        plans.append(structured(await journey.call(session, "get_workflow_plan", name))["workflow_plan"])
        if content_mode != "ad":
            structured(
                await journey.call(session, "upload_source", name, filename="novel.txt", content="第一章 雨夜。")
            )
            plans.append(structured(await journey.call(session, "get_workflow_plan", name))["workflow_plan"])
        episode = await journey.call(session, "create_episode", name, title="Manual")
        plans.append(structured(await journey.call(session, "get_workflow_plan", name))["workflow_plan"])
        blank = await journey.call(session, "start_blank_script", name, episode_id=1)
        plans.append(structured(await journey.call(session, "get_workflow_plan", name))["workflow_plan"])
        tools = {tool.name for tool in (await session.list_tools()).tools}

    if content_mode == "ad":
        # Ads own exactly one episode, created with the project.
        assert problem(episode)["code"] == "episode_manage_ad_episode_locked"
    else:
        assert structured(episode)["episode"]["episode_id"] == 1
    assert structured(blank)["start_blank_script"]["created"] is True
    assert plans[-1]["next_action"]["type"] == "add_script_items"
    seen = set().union(*(_actions(plan) for plan in plans))
    for action in seen:
        assert ACTION_TOOLS[action], f"{action} has no MCP tool"
        assert ACTION_TOOLS[action] <= tools, action
    assert plan_tool_names(plans) <= tools
    assert await journey.task_total() == 0
    assert_no_leaks(journey.seen, _forbidden(journey))


async def test_reference_image_stages_installs_and_reads_back_through_mcp(journey: Journey) -> None:
    """A character reference arrives as a staged upload, reports the installed digest and downloads unchanged."""
    reference = png_bytes((200, 30, 30), (120, 160))
    async with journey.session() as session:
        await _bootstrap(journey, session)
        staged = await stage_upload(journey, session, PROJECT, "xiaoyu.png", reference, "asset_image", STAGING_CHUNK)
        wrong_purpose = await stage_upload(
            journey, session, PROJECT, "xiaoyu.png", reference, "product_reference_image", STAGING_CHUNK
        )
        both = await journey.call(
            session,
            "upload_reference",
            PROJECT,
            kind="character_image",
            name=CHARACTER,
            filename="xiaoyu.png",
            content_base64=b64(reference),
            staged_upload_id=staged,
        )
        mismatch = problem(
            await journey.call(
                session,
                "upload_reference",
                PROJECT,
                kind="character_image",
                name=CHARACTER,
                filename="xiaoyu.png",
                staged_upload_id=wrong_purpose,
            )
        )
        installed = structured(
            await journey.call(
                session,
                "upload_reference",
                PROJECT,
                kind="character_image",
                name=CHARACTER,
                filename="xiaoyu.png",
                staged_upload_id=staged,
            )
        )["reference"]
        reused = problem(
            await journey.call(
                session,
                "upload_reference",
                PROJECT,
                kind="character_image",
                name=CHARACTER,
                filename="xiaoyu.png",
                staged_upload_id=staged,
            )
        )
        media = await describe(journey, session, PROJECT, {"kind": "character_reference_image", "character": CHARACTER})
        downloaded = await download(journey, session, PROJECT, media)
        no_style = problem(await journey.call(session, "describe_media", PROJECT, selector={"kind": "style_image"}))

    assert both.isError
    assert mismatch["code"] == "upload_purpose_mismatch"
    assert installed["sha256"] == media["sha256"] == sha256(downloaded)
    assert media["mime_type"] == "image/png"
    # The staging is discarded once installed.
    assert reused["code"] == "upload_not_found"
    assert no_style["code"] == "media_missing"
    assert await journey.task_total() == 0
    assert_no_leaks(journey.seen, _forbidden(journey))


async def test_artifact_download_failure_resumes_retrieval_through_mcp(journey: Journey) -> None:
    """A paid generation whose output could not be downloaded resumes retrieval through MCP, never a new generation."""
    async with journey.session() as session:
        await _bootstrap(journey, session)
        task_id = await journey.seed_download_failed(PROJECT, CHARACTER)
        other_task = await journey.seed_download_failed("elsewhere", CHARACTER)
        tasks_before = await journey.task_total()
        provider_calls_before = (len(journey.image.calls), len(journey.audio.calls))

        diagnostics = structured(await journey.call(session, "get_generation_diagnostics", PROJECT, task_id=task_id))
        assert "retry_artifact_download" in str(diagnostics)
        foreign = problem(await journey.call(session, "retry_artifact_download", PROJECT, task_id=other_task))
        missing = problem(await journey.call(session, "retry_artifact_download", PROJECT, task_id="no-such-task"))
        resumed = structured(await journey.call(session, "retry_artifact_download", PROJECT, task_id=task_id))
        again = problem(await journey.call(session, "retry_artifact_download", PROJECT, task_id=task_id))

    assert foreign["code"] == missing["code"] == "task_not_found"
    assert foreign["detail"].replace(other_task, "<id>") == missing["detail"].replace("no-such-task", "<id>")
    result = resumed["retry_artifact_download"]
    assert result["task_id"] == task_id
    assert result["status"] == "running"
    assert result["new_task_created"] is False
    # Only the scoped task reached the worker; the reopened task is running again, not resubmitted.
    assert [task["task_id"] for task in journey.retrieval.resumed] == [task_id]
    assert again["code"] == "task_retry_download_ineligible"
    assert await journey.task_total() == tasks_before
    assert (len(journey.image.calls), len(journey.audio.calls)) == provider_calls_before
    stored = await journey.queue.get_task(task_id)
    assert stored is not None
    assert stored["status"] == "running"
    assert (await journey.queue.get_task(other_task) or {})["status"] == "failed"
    assert_no_leaks(journey.seen, _forbidden(journey))
