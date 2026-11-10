"""Global endpoint/provider configuration through a real MCP client (MCP-009).

Reproduces the ce-1/custom-1 configuration observed in production (a MiniMax H3 built-in copy that sends WAV
reference audio as ``data:audio/wav;base64,`` and a custom provider on https://api.minimax.io reusing an existing
credential by reference) in a disposable DB and data root, entirely through the tools. Proves no credential value
reaches results or logs, refusals for a different host / stale revision / invalid definition, no unrelated
project or global default changes, zero outbound HTTP and zero jobs, and operator gating of the tool surface."""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from sqlalchemy import func, select

from lib.config.service import ConfigService
from lib.db.models.api_call import ApiCall
from lib.db.models.custom_provider import CustomProvider
from lib.db.models.task import Task
from lib.db.repositories.credential_repository import CredentialRepository
from lib.db.repositories.custom_endpoint_repo import CustomEndpointRepository
from lib.project.project_manager import ProjectManager
from server.agent_toolset.global_config import (
    GLOBAL_CONFIG_API_KEYS_ENV,
    GLOBAL_CONFIG_TOOL_IDS,
    GatedToolsFastMCP,
    build_global_config_tools,
)
from server.agent_toolset.toolset import AGENT_TOOLSET
from server.remote_mcp import ArcApiKeyVerifier, build_remote_mcp_server, mount_remote_mcp
from server.tool_runtime import Services

SECRET = "sk-fake-minimax-SECRET-0123456789abcdef"
OTHER_SECRET = "sk-fake-other-SECRET-fedcba9876543210"

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


class _Planner:
    async def get_plan(self, *_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("configuration tools never plan workflows")


class _Capabilities:
    pass


class _Reloads:
    def __init__(self) -> None:
        self.count = 0

    async def __call__(self) -> None:
        self.count += 1


async def _verify(token: str) -> dict[str, str] | None:
    subjects = {"arc-admin": "apikey:config-admin", "arc-other": "apikey:producer"}
    return {"sub": subjects[token], "via": "apikey"} if token in subjects else None


def _server(projects: ProjectManager, services: Services, reloads: _Reloads | None, names: frozenset[str]):
    tools = build_global_config_tools(
        projects=projects, services=services, reload_limits=reloads, authorized_names=names
    )
    return GatedToolsFastMCP(
        "arcreel-test",
        tools=tools,
        gated_tool_names=GLOBAL_CONFIG_TOOL_IDS,
        is_authorized=lambda: _authorized(names),
        token_verifier=ArcApiKeyVerifier(_verify),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl("http://localhost/"), resource_server_url=None, required_scopes=["arcreel"]
        ),
        stateless_http=True,
        streamable_http_path="/",
        json_response=False,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


def _authorized(names: frozenset[str]) -> bool:
    from server.agent_toolset.global_config import global_config_authorized

    return global_config_authorized(names)


def _app(server) -> FastAPI:
    app = FastAPI()
    mount_remote_mcp(app, server.streamable_http_app())
    return app


class _Client:
    """One authenticated MCP client session against the isolated server."""

    def __init__(self, app: FastAPI, token: str) -> None:
        self._asgi = app
        self._token = token

    async def __aenter__(self) -> ClientSession:
        self._http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self._asgi),
            base_url="http://localhost",
            headers={"Authorization": f"Bearer {self._token}"},
            follow_redirects=True,
        )
        await self._http.__aenter__()
        self._stream = streamable_http_client("http://localhost/mcp", http_client=self._http)
        read, write, _ = await self._stream.__aenter__()
        self._session = ClientSession(read, write)
        session = await self._session.__aenter__()
        await session.initialize()
        return session

    async def __aexit__(self, *exc: object) -> None:
        await self._session.__aexit__(*exc)
        await self._stream.__aexit__(*exc)
        await self._http.__aexit__(*exc)


def _structured(result) -> dict[str, Any]:
    assert result.structuredContent is not None, result.content
    return result.structuredContent


def _text(result) -> str:
    return "\n".join(getattr(block, "text", "") for block in result.content) + json.dumps(
        result.structuredContent or {}, ensure_ascii=False
    )


def _wav_variant(definition: dict[str, Any]) -> dict[str, Any]:
    """The ce-1 edit: bare base64 audio wrapped in a fixed WAV data URI (WAV-only workaround)."""
    edited = copy.deepcopy(definition)
    edited["inputs"]["ref_audio"] = {"source": "reference_audio_files", "encoding": "base64"}
    for item in edited["submit"]["body"]["content"]:
        each = item.get("$each") if isinstance(item, dict) else None
        if each and each.get("in") == "inputs.ref_audio":
            each["item"]["audio_url"]["url"] = "data:audio/wav;base64,{{ audio }}"
    return edited


@pytest.fixture
def outbound_http(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record (and refuse) any real outbound HTTP; the in-process ASGI MCP transport is unaffected."""
    calls: list[str] = []

    async def refuse_async(self, request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        raise AssertionError(f"unexpected outbound request {request.url}")

    def refuse_sync(self, request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        raise AssertionError(f"unexpected outbound request {request.url}")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", refuse_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse_sync)
    return calls


@pytest.fixture
async def seeded(tmp_path: Path, db_factory):
    projects = ProjectManager(tmp_path)
    projects.create_project("other", content_mode="drama")
    projects.create_project_metadata("other", "Other", "", "drama")

    def mark_project(project: dict) -> None:
        project["video_backend"] = "minimax/MiniMax-H3"

    projects.update_project("other", mark_project)
    async with db_factory() as session:
        repo = CredentialRepository(session)
        await repo.create("minimax", "fake official", api_key=SECRET, base_url="https://api.minimax.io/v1")
        await repo.create("openai", "fake other", api_key=OTHER_SECRET)
        await ConfigService(session).set_setting("default_video_backend", "minimax/MiniMax-H3")
        await session.commit()
    services = Services(
        projects=projects, workflow_planner=_Planner(), capabilities=_Capabilities(), sessions=db_factory
    )
    return projects, services


async def _global_settings(db_factory) -> dict[str, str]:
    async with db_factory() as session:
        return await ConfigService(session).get_all_settings()


async def test_reproduces_ce1_custom1_configuration_through_mcp_tools(
    seeded, db_factory, outbound_http: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    projects, services = seeded
    reloads = _Reloads()
    server = _server(projects, services, reloads, frozenset({"config-admin"}))
    other_project_before = (projects.get_project_path("other") / "project.json").read_bytes()
    settings_before = await _global_settings(db_factory)
    caplog.set_level(logging.DEBUG)

    app = _app(server)
    async with server.session_manager.run(), _Client(app, "arc-admin") as mcp:
        listed = {tool.name for tool in (await mcp.list_tools()).tools}
        assert listed >= GLOBAL_CONFIG_TOOL_IDS

        providers = await mcp.call_tool("list_global_providers", {})
        minimax = next(p for p in _structured(providers)["providers"]["builtin"] if p["provider_id"] == "minimax")
        assert minimax["credential"] == {
            "ref": "minimax",
            "configured": True,
            "origin": "https://api.minimax.io:443",
            "reusable": True,
        }

        builtin = _structured(await mcp.call_tool("get_endpoint_definition", {"endpoint_key": "minimax-h3"}))
        wav_definition = _wav_variant(builtin["endpoint"]["definition"])

        validation = _structured(await mcp.call_tool("validate_endpoint_definition", {"definition": wav_definition}))
        assert validation["validation"]["valid"] is True, validation
        assert validation["validation"]["errors"] == []

        preview = await mcp.call_tool(
            "preview_endpoint_request",
            {
                "definition": wav_definition,
                "parameters": {"model": "MiniMax-H3", "prompt": "capivara", "duration_seconds": 10},
                "base_url": "https://api.minimax.io",
            },
        )
        submit = _structured(preview)["preview"]["submit"]
        assert submit["url"] == "https://api.minimax.io/v2/video_generation"
        assert submit["headers"]["Authorization"] == "Bearer ****"
        audio_urls = [item["audio_url"]["url"] for item in submit["body"]["content"] if item.get("type") == "audio_url"]
        assert audio_urls
        assert all(url.startswith("data:audio/wav;base64,") for url in audio_urls)

        copied = _structured(await mcp.call_tool("copy_builtin_endpoint", {"endpoint_key": "minimax-h3"}))
        key = copied["endpoint"]["key"]
        assert key == "ce-1"
        duplicate = await mcp.call_tool("copy_builtin_endpoint", {"endpoint_key": "minimax-h3"})
        assert duplicate.isError
        assert _structured(duplicate)["problem"]["code"] == "endpoint_duplicate_exists"

        revision = _structured(await mcp.call_tool("get_endpoint_definition", {"endpoint_key": key}))["endpoint"][
            "revision"
        ]
        dry_run = _structured(
            await mcp.call_tool(
                "update_custom_endpoint",
                {"endpoint_key": key, "definition": wav_definition, "expected_revision": revision},
            )
        )["endpoint_update"]
        assert dry_run["applied"] is False
        assert "inputs.ref_audio.encoding" in dry_run["changed_fields"]
        assert dry_run["impact"] == {"model_rows": [], "projects": [], "global_settings": []}

        invalid = await mcp.call_tool(
            "update_custom_endpoint",
            {"endpoint_key": key, "definition": {"kind": "declarative"}, "expected_revision": revision, "apply": True},
        )
        assert _structured(invalid)["problem"]["code"] == "custom_endpoint_definition_invalid"

        applied = _structured(
            await mcp.call_tool(
                "update_custom_endpoint",
                {"endpoint_key": key, "definition": wav_definition, "expected_revision": revision, "apply": True},
            )
        )["endpoint_update"]
        assert applied["applied"] is True
        assert applied["revision"] != revision

        stale = await mcp.call_tool(
            "update_custom_endpoint",
            {"endpoint_key": key, "definition": wav_definition, "expected_revision": revision, "apply": True},
        )
        assert _structured(stale)["problem"]["code"] == "revision_conflict"

        model = {"model_id": "MiniMax-H3", "display_name": "MiniMax H3", "endpoint": key, "is_default": True}
        provider_args = {
            "display_name": "MiniMax official (WAV)",
            "discovery_format": "openai",
            "base_url": "https://api.minimax.io",
            "credential_ref": "minimax",
            "models": [model],
        }
        other_host = await mcp.call_tool(
            "configure_custom_provider", {**provider_args, "base_url": "https://api.minimaxi.com", "apply": True}
        )
        assert _structured(other_host)["problem"]["code"] == "credential_host_mismatch"
        unknown = await mcp.call_tool(
            "configure_custom_provider", {**provider_args, "credential_ref": "custom-99", "apply": True}
        )
        assert _structured(unknown)["problem"]["code"] == "credential_ref_unknown"

        planned = _structured(await mcp.call_tool("configure_custom_provider", provider_args))
        assert planned["provider_configuration"]["applied"] is False
        created = await mcp.call_tool("configure_custom_provider", {**provider_args, "apply": True})
        provider = _structured(created)["provider_configuration"]["provider"]
        assert provider["provider_id"] == "custom-1"
        assert provider["credential"] == {"ref": "custom-1", "configured": True, "origin": "https://api.minimax.io:443"}
        assert [(m["model_id"], m["endpoint"]) for m in provider["models"]] == [("MiniMax-H3", key)]

        stale_provider = await mcp.call_tool(
            "configure_custom_provider",
            {
                "provider_id": "custom-1",
                "display_name": "renamed",
                "base_url": "https://api.minimax.io",
                "expected_revision": "sha256-v1:stale",
                "apply": True,
            },
        )
        assert _structured(stale_provider)["problem"]["code"] == "revision_conflict"
        moved = await mcp.call_tool(
            "configure_custom_provider",
            {
                "provider_id": "custom-1",
                "display_name": "moved",
                "base_url": "https://elsewhere.example",
                "expected_revision": provider["revision"],
                "apply": True,
            },
        )
        assert _structured(moved)["problem"]["code"] == "credential_host_mismatch"

        impact = _structured(await mcp.call_tool("get_endpoint_definition", {"endpoint_key": key}))["endpoint"][
            "impact"
        ]
        assert impact["model_rows"] == [{"provider_id": "custom-1", "model_id": "MiniMax-H3"}]

        readbacks = [
            providers,
            preview,
            created,
            await mcp.call_tool("list_global_providers", {}),
            await mcp.call_tool("list_global_endpoints", {}),
        ]

    for result in readbacks:
        text = _text(result)
        assert SECRET not in text
        assert SECRET[-4:] not in text
        assert OTHER_SECRET not in text
        assert OTHER_SECRET[-4:] not in text
    logged = "\n".join(record.getMessage() + repr(record.__dict__) for record in caplog.records)
    assert SECRET not in logged
    assert SECRET[-4:] not in logged
    audits = [record for record in caplog.records if record.name == "arcreel.audit.global_config"]
    assert [(r.operation, r.target) for r in audits] == [
        ("copy_builtin_endpoint", "ce-1"),
        ("update_custom_endpoint", "ce-1"),
        ("create_custom_provider", "custom-1"),
    ]
    assert {r.identity for r in audits} == {"apikey:config-admin"}
    assert "credential" in audits[-1].changed_fields

    async with db_factory() as session:
        stored = (await session.execute(select(CustomProvider))).scalar_one()
        assert stored.api_key == SECRET  # Reused server-side by reference.
        assert (await session.execute(select(func.count()).select_from(Task))).scalar_one() == 0
        assert (await session.execute(select(func.count()).select_from(ApiCall))).scalar_one() == 0
    assert outbound_http == []
    assert reloads.count == 1
    assert (projects.get_project_path("other") / "project.json").read_bytes() == other_project_before
    assert await _global_settings(db_factory) == settings_before


async def test_unauthorized_key_neither_lists_nor_calls_global_config_tools(seeded) -> None:
    projects, services = seeded
    server = _server(projects, services, _Reloads(), frozenset({"config-admin"}))
    app = _app(server)
    async with server.session_manager.run(), _Client(app, "arc-other") as mcp:
        listed = {tool.name for tool in (await mcp.list_tools()).tools}
        result = await mcp.call_tool("list_global_providers", {})
        copy_attempt = await mcp.call_tool("copy_builtin_endpoint", {"endpoint_key": "minimax-h3"})

    assert listed.isdisjoint(GLOBAL_CONFIG_TOOL_IDS)
    assert result.isError
    assert "Unknown tool" in _text(result)
    assert copy_attempt.isError
    assert SECRET not in _text(copy_attempt)


async def test_global_config_tools_are_not_registered_without_granted_keys(
    seeded, monkeypatch: pytest.MonkeyPatch
) -> None:
    projects, services = seeded
    monkeypatch.delenv(GLOBAL_CONFIG_API_KEYS_ENV, raising=False)
    assert build_global_config_tools(projects=projects, services=services, reload_limits=None) == []
    monkeypatch.setenv(GLOBAL_CONFIG_API_KEYS_ENV, " , ")
    assert build_global_config_tools(projects=projects, services=services, reload_limits=None) == []
    monkeypatch.setenv(GLOBAL_CONFIG_API_KEYS_ENV, "config-admin")
    assert {
        tool.name for tool in build_global_config_tools(projects=projects, services=services, reload_limits=None)
    } == (GLOBAL_CONFIG_TOOL_IDS)

    # The current remote host (not yet wired) and the embedded toolset expose none of them.
    remote = build_remote_mcp_server(projects=projects, services=services, token_verifier=ArcApiKeyVerifier(_verify))
    assert {tool.name for tool in await remote.list_tools()}.isdisjoint(GLOBAL_CONFIG_TOOL_IDS)
    assert {declaration.name for declaration in AGENT_TOOLSET}.isdisjoint(GLOBAL_CONFIG_TOOL_IDS)


async def test_provider_update_reveals_project_impact_before_applying(seeded, db_factory) -> None:
    from server.services.configuration import global_config as config
    from server.services.configuration.custom_providers import ModelInput

    projects, _ = seeded

    def identity(key: str, **params: object) -> str:
        return key

    async with db_factory() as session:
        created = await config.configure_custom_provider(
            session,
            projects,
            config.ProviderPlan(
                provider_id=None,
                display_name="MiniMax official",
                discovery_format="openai",
                base_url="https://api.minimax.io",
                credential_ref="minimax",
                models=[ModelInput(model_id="MiniMax-H3", display_name="H3", endpoint="minimax-h3")],
                expected_revision=None,
            ),
            identity,
            apply=True,
            reload_limits=_Reloads(),
            identity="apikey:test",
        )
    provider = created["provider"]

    def reference(project: dict) -> None:
        project["video_provider_r2v"] = "custom-1/MiniMax-H3"

    projects.update_project("other", reference)
    before = (projects.get_project_path("other") / "project.json").read_bytes()
    async with db_factory() as session:
        report = await config.configure_custom_provider(
            session,
            projects,
            config.ProviderPlan(
                provider_id="custom-1",
                display_name="MiniMax official",
                discovery_format=None,
                base_url="https://api.minimax.io",
                credential_ref=None,
                models=[],
                expected_revision=provider["revision"],
            ),
            identity,
            apply=False,
            reload_limits=None,
            identity="apikey:test",
        )

    assert report["applied"] is False
    assert report["removed_models"] == ["MiniMax-H3"]
    assert report["impact"]["projects"] == [{"project": "other", "keys": ["video_provider_r2v"]}]
    assert (projects.get_project_path("other") / "project.json").read_bytes() == before


async def test_credentials_without_a_single_api_key_or_known_origin_are_not_reusable(db_factory) -> None:
    from server.services.configuration import global_config as config

    async with db_factory() as session:
        await CredentialRepository(session).create("kling", "fake", access_key="ak", secret_key="sk")
        await session.commit()
        with pytest.raises(config.GlobalConfigRefused) as kling:
            await config.resolve_credential_ref(session, "kling")
        with pytest.raises(config.GlobalConfigRefused) as missing:
            await config.resolve_credential_ref(session, "minimax")

    assert kling.value.code == "credential_ref_unusable"
    assert missing.value.code == "credential_ref_unusable"
    assert config.origin_of("https://API.minimax.io/v1") == config.origin_of("https://api.minimax.io:443")
    assert config.origin_of("http://api.minimax.io") != config.origin_of("https://api.minimax.io")
    assert config.origin_of("api.minimax.io") is None


def _redirected(definition: dict[str, Any], section: str, url: str) -> dict[str, Any]:
    edited = copy.deepcopy(definition)
    edited[section]["url"] = url
    return edited


async def _custom_copy(mcp: ClientSession, definition: dict[str, Any] | None = None) -> tuple[str, str]:
    copied = _structured(
        await mcp.call_tool("copy_builtin_endpoint", {"endpoint_key": "minimax-h3", "allow_duplicate": True})
    )["endpoint"]
    key, revision = copied["key"], copied["revision"]
    if definition is not None:
        updated = _structured(
            await mcp.call_tool(
                "update_custom_endpoint",
                {"endpoint_key": key, "definition": definition, "expected_revision": revision, "apply": True},
            )
        )["endpoint_update"]
        assert updated["applied"] is True
        revision = updated["revision"]
    return key, revision


async def test_credential_reuse_refuses_endpoints_that_send_requests_to_another_host(
    seeded, db_factory, outbound_http: list[str]
) -> None:
    projects, services = seeded
    server = _server(projects, services, _Reloads(), frozenset({"config-admin"}))
    app = _app(server)
    async with server.session_manager.run(), _Client(app, "arc-admin") as mcp:
        builtin = _structured(await mcp.call_tool("get_endpoint_definition", {"endpoint_key": "minimax-h3"}))
        definition = builtin["endpoint"]["definition"]
        foreign_submit, _ = await _custom_copy(mcp, _redirected(definition, "submit", "https://collector.example/x"))
        foreign_poll, _ = await _custom_copy(
            mcp, _redirected(definition, "poll", "https://collector.example/q/{{ task_id }}")
        )
        clean, clean_revision = await _custom_copy(mcp)

        def provider_args(endpoint: str) -> dict[str, Any]:
            return {
                "display_name": "MiniMax",
                "discovery_format": "openai",
                "base_url": "https://api.minimax.io",
                "credential_ref": "minimax",
                "models": [{"model_id": "MiniMax-H3", "display_name": "H3", "endpoint": endpoint}],
                "apply": True,
            }

        submit_refusal = await mcp.call_tool("configure_custom_provider", provider_args(foreign_submit))
        poll_refusal = await mcp.call_tool("configure_custom_provider", provider_args(foreign_poll))
        created = _structured(await mcp.call_tool("configure_custom_provider", provider_args(clean)))
        provider = created["provider_configuration"]["provider"]

        rebind = await mcp.call_tool(
            "configure_custom_provider",
            {
                **provider_args(foreign_submit),
                "provider_id": provider["provider_id"],
                "expected_revision": provider["revision"],
                "credential_ref": None,
            },
        )
        redirect_attached = {
            "endpoint_key": clean,
            "definition": _redirected(definition, "submit", "https://collector.example/x"),
            "expected_revision": clean_revision,
        }
        attached_dry_run = await mcp.call_tool("update_custom_endpoint", redirect_attached)
        attached_apply = await mcp.call_tool("update_custom_endpoint", {**redirect_attached, "apply": True})
        attached_after = _structured(await mcp.call_tool("get_endpoint_definition", {"endpoint_key": clean}))

    for result, request in ((submit_refusal, "submit"), (poll_refusal, "poll")):
        problem = _structured(result)["problem"]
        assert problem["code"] == "credential_host_mismatch"
        assert problem["params"]["request"] == request
        assert problem["params"]["destination_origin"] == "https://collector.example:443"
    assert created["provider_configuration"]["applied"] is True
    assert _structured(rebind)["problem"]["code"] == "credential_host_mismatch"
    assert _structured(attached_dry_run)["problem"]["code"] == "credential_host_mismatch"
    assert _structured(attached_apply)["problem"]["code"] == "credential_host_mismatch"
    assert attached_after["endpoint"]["revision"] == clean_revision
    async with db_factory() as session:
        assert (await session.execute(select(func.count()).select_from(CustomProvider))).scalar_one() == 1
    assert outbound_http == []


async def test_unexpected_database_errors_never_echo_bound_parameters(
    seeded, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from sqlalchemy.exc import OperationalError

    from lib.db.repositories.custom_provider_repo import CustomProviderRepository

    async def failing(self) -> list[CustomProvider]:
        raise OperationalError(
            "SELECT custom_provider.api_key WHERE api_key = ?", {"api_key": SECRET}, Exception(SECRET)
        )

    monkeypatch.setattr(CustomProviderRepository, "list_providers", failing)
    projects, services = seeded
    server = _server(projects, services, _Reloads(), frozenset({"config-admin"}))
    app = _app(server)
    caplog.set_level(logging.DEBUG)
    async with server.session_manager.run(), _Client(app, "arc-admin") as mcp:
        result = await mcp.call_tool("list_global_providers", {})

    assert result.isError
    assert _structured(result)["problem"]["code"] == "internal_error"
    assert SECRET not in _text(result)
    logged = "\n".join(record.getMessage() + repr(record.__dict__) for record in caplog.records)
    assert SECRET not in logged


async def test_provider_writes_refuse_without_an_injected_reload_callback_and_codes_stay_stable(
    seeded, db_factory
) -> None:
    projects, services = seeded
    server = _server(projects, services, None, frozenset({"config-admin"}))
    app = _app(server)
    args = {
        "display_name": "MiniMax",
        "discovery_format": "openai",
        "base_url": "https://api.minimax.io",
        "credential_ref": "minimax",
        "models": [{"model_id": "MiniMax-H3", "display_name": "H3", "endpoint": "minimax-h3"}],
    }
    duplicate_models = {**args, "models": [args["models"][0], args["models"][0]]}
    async with server.session_manager.run(), _Client(app, "arc-admin") as mcp:
        dry_run = _structured(await mcp.call_tool("configure_custom_provider", args))
        refused = await mcp.call_tool("configure_custom_provider", {**args, "apply": True})
        invalid = await mcp.call_tool("configure_custom_provider", duplicate_models)
        missing = await mcp.call_tool(
            "configure_custom_provider",
            {**args, "provider_id": "custom-42", "expected_revision": "sha256-v1:x", "credential_ref": None},
        )

    assert dry_run["provider_configuration"]["applied"] is False
    assert _structured(refused)["problem"]["code"] == "reload_limits_unavailable"
    assert _structured(invalid)["problem"]["code"] == "duplicate_model_id"
    assert _structured(missing)["problem"]["code"] == "provider_not_found"
    async with db_factory() as session:
        assert (await session.execute(select(func.count()).select_from(CustomProvider))).scalar_one() == 0


async def test_gated_handlers_refuse_without_a_granted_identity(seeded) -> None:
    from server.agent_toolset.declaration import invoke_unscoped_declaration
    from server.agent_toolset.global_config import global_config_declarations
    from server.tool_runtime import CallerContext

    _, services = seeded
    (declaration,) = [d for d in global_config_declarations(None) if d.name == "list_global_providers"]
    # No MCP request token (e.g. a host that bypassed the gated tool wrapper): the handler itself refuses.
    outcome = await invoke_unscoped_declaration(declaration, {}, CallerContext(user_id="u", source="mcp"), services)

    assert outcome.problem is not None
    assert outcome.problem.code == "global_config_forbidden"
    assert outcome.value is None


@pytest.mark.parametrize(
    ("section", "url"),
    [
        ("submit", "https://api.minimax.io{{ prompt }}"),
        ("submit", "{{ base_url }}{{ prompt }}"),
        ("poll", "https://api.minimax.io{{ task_id }}/q"),
    ],
)
async def test_credential_reuse_refuses_urls_whose_host_a_rendered_value_can_choose(
    seeded, db_factory, outbound_http: list[str], section: str, url: str
) -> None:
    """A placeholder inside/after the authority renders unescaped: ``@collector.example/steal`` moves the host.

    Two layers refuse it: the definition validator rejects such a URL on any new write, and credential reuse
    re-checks definitions stored before that rule existed (simulated by writing the legacy row directly).
    """
    projects, services = seeded
    server = _server(projects, services, _Reloads(), frozenset({"config-admin"}))
    app = _app(server)
    async with server.session_manager.run(), _Client(app, "arc-admin") as mcp:
        builtin = _structured(await mcp.call_tool("get_endpoint_definition", {"endpoint_key": "minimax-h3"}))
        definition = builtin["endpoint"]["definition"]
        legacy, _ = await _custom_copy(mcp)
        clean, clean_revision = await _custom_copy(mcp)
        async with db_factory() as session:
            row = await CustomEndpointRepository(session).get(int(legacy.removeprefix("ce-")))
            assert row is not None
            row.definition = _redirected(definition, section, url)
            await session.commit()

        def provider_args(endpoint: str) -> dict[str, Any]:
            return {
                "display_name": "MiniMax",
                "discovery_format": "openai",
                "base_url": "https://api.minimax.io",
                "credential_ref": "minimax",
                "models": [{"model_id": "MiniMax-H3", "display_name": "H3", "endpoint": endpoint}],
                "apply": True,
            }

        create_refusal = await mcp.call_tool("configure_custom_provider", provider_args(legacy))
        created = _structured(await mcp.call_tool("configure_custom_provider", provider_args(clean)))
        provider = created["provider_configuration"]["provider"]
        update_refusal = await mcp.call_tool(
            "configure_custom_provider",
            {
                **provider_args(legacy),
                "provider_id": provider["provider_id"],
                "expected_revision": provider["revision"],
                "credential_ref": None,
            },
        )
        redirect_attached = {
            "endpoint_key": clean,
            "definition": _redirected(definition, section, url),
            "expected_revision": clean_revision,
        }
        attached_dry_run = await mcp.call_tool("update_custom_endpoint", redirect_attached)
        attached_apply = await mcp.call_tool("update_custom_endpoint", {**redirect_attached, "apply": True})
        attached_after = _structured(await mcp.call_tool("get_endpoint_definition", {"endpoint_key": clean}))

    assert created["provider_configuration"]["applied"] is True
    for result in (create_refusal, update_refusal):
        problem = _structured(result)["problem"]
        assert problem["code"] == "credential_host_unverifiable"
        assert problem["params"]["request"] == section
    for result in (attached_dry_run, attached_apply):
        assert result.isError
        refusal = json.dumps(_structured(result)["problem"])
        assert "url_authority_placeholder" in refusal or "credential_host_unverifiable" in refusal
    assert attached_after["endpoint"]["revision"] == clean_revision
    async with db_factory() as session:
        assert (await session.execute(select(func.count()).select_from(CustomProvider))).scalar_one() == 1
    assert outbound_http == []


@pytest.mark.parametrize(
    ("template", "fixed"),
    [
        ("{{ base_url }}/v2/video_generation", True),
        ("{{ base_url }}/v2/query/{{ task_id }}", True),
        ("{{override_base_url}}?id={{ task_id }}", True),
        ("{{ base_url }}", True),
        ("https://api.minimax.io/v2/{{ prompt }}", True),
        ("https://api.minimax.io#{{ prompt }}", True),
        ("https://api.minimax.io{{ prompt }}", False),
        ("{{ base_url }}{{ prompt }}", False),
        ("{{ base_url }}.collector.example/x", False),
        ("{{ base_url }}@collector.example/x", False),
        ("{{ base_url }}:8443/x", False),
        ("{{ prompt }}/x", False),
        ("https://{{ model }}.collector.example/x", False),
        ("https://{{ task_id }}/q", False),
        ("//collector.example/x", False),
        ("https:///x", False),
    ],
)
def test_url_authority_is_fixed_only_by_the_base_url_or_a_literal(template: str, fixed: bool) -> None:
    from server.services.configuration.global_config import url_authority_is_fixed

    assert url_authority_is_fixed(template) is fixed
