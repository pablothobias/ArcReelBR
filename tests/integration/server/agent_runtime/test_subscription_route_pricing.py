"""Native route/pricing construction with isolated DBs and an intercepted SDK process boundary."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from claude_agent_sdk import ClaudeAgentOptions, CLIConnectionError
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

from lib.config.claude_subscription import SubscriptionRouteConflictError
from lib.config.env_keys import CLAUDE_CLOUD_ROUTE_ENV_KEYS
from lib.config.repository import SystemSettingRepository
from lib.db.repositories.agent_credential_repo import AgentCredentialRepository
from server.agent_runtime.options_assembler import agent_pricing_of, load_provider_env_overrides
from tests.fakes import bind_session_factory

CLOUD_FLAGS = CLAUDE_CLOUD_ROUTE_ENV_KEYS


@pytest.fixture(autouse=True)
def route_environment(monkeypatch, file_db_factory):
    bind_session_factory(monkeypatch, file_db_factory)
    for key in CLOUD_FLAGS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK", "1")


async def capture_spawn(monkeypatch, overrides, captured):
    async def prevent_spawn(*args, **kwargs):
        captured.append({key: kwargs["env"].get(key) for key in CLOUD_FLAGS})
        raise RuntimeError("Audit process creation prevented")

    monkeypatch.setattr("anyio.open_process", prevent_spawn)
    transport = SubprocessCLITransport(
        prompt="audit", options=ClaudeAgentOptions(cli_path="/unused/claude", env=overrides)
    )
    await transport.connect()


async def configure_and_capture(monkeypatch, captured):
    overrides = await load_provider_env_overrides()
    await capture_spawn(monkeypatch, overrides, captured)


@pytest.mark.parametrize("flag", CLOUD_FLAGS)
async def test_cloud_route_cannot_reach_zero_price_sdk_spawn(monkeypatch, flag):
    monkeypatch.setenv(flag, "1")
    captured = []
    with pytest.raises(SubscriptionRouteConflictError, match="cloud route"):
        await configure_and_capture(monkeypatch, captured)
    assert captured == []
    assert os.environ[flag] == "1"


@pytest.mark.parametrize("legacy_api", [False, True])
@pytest.mark.parametrize("cloud_enabled", [False, True])
async def test_configured_api_pricing_and_environment_are_retained(
    file_db_factory, monkeypatch, legacy_api, cloud_enabled
):
    if cloud_enabled:
        monkeypatch.setenv("CLAUDE_CODE_USE_BEDROCK", "1")
    async with file_db_factory() as session:
        if legacy_api:
            settings = SystemSettingRepository(session)
            await settings.set("anthropic_api_key", "synthetic-api-key")
            await settings.set("anthropic_base_url", "https://gateway.invalid")
        else:
            repo = AgentCredentialRepository(session)
            credential = await repo.create(
                preset_id="__custom__",
                display_name="Synthetic",
                api_key="synthetic-api-key",
                base_url="https://gateway.invalid",
                multiplier=0.4,
                model="synthetic-model",
            )
            await repo.set_active(credential.id)
        await session.commit()
    overrides = await load_provider_env_overrides()
    assert overrides["ANTHROPIC_API_KEY"] == "synthetic-api-key"
    assert overrides["ANTHROPIC_BASE_URL"] == "https://gateway.invalid"
    assert agent_pricing_of(SimpleNamespace(env=overrides)).multiplier == (1 if legacy_api else 0.4)
    assert os.environ.get("CLAUDE_CODE_USE_BEDROCK") == ("1" if cloud_enabled else None)


@pytest.mark.parametrize("flag", CLOUD_FLAGS)
async def test_disabled_cloud_flag_keeps_zero_price_and_reaches_only_intercepted_spawn(monkeypatch, flag):
    monkeypatch.setenv(flag, " FaLsE ")
    overrides = await load_provider_env_overrides()
    assert agent_pricing_of(SimpleNamespace(env=overrides)).multiplier == 0
    assert overrides["ANTHROPIC_API_KEY"] == ""
    captured = []
    with pytest.raises(CLIConnectionError, match="Audit process creation prevented"):
        await capture_spawn(monkeypatch, overrides, captured)
    assert len(captured) == 1
    assert captured[0][flag] == " FaLsE "


async def test_clean_subscription_keeps_zero_price_without_claiming_login(monkeypatch):
    overrides = await load_provider_env_overrides()
    assert agent_pricing_of(SimpleNamespace(env=overrides)).multiplier == 0
    assert overrides["ANTHROPIC_API_KEY"] == ""
    captured = []
    with pytest.raises(CLIConnectionError, match="Audit process creation prevented"):
        await capture_spawn(monkeypatch, overrides, captured)
    assert captured == [dict.fromkeys(CLOUD_FLAGS)]


def test_local_launcher_clean_boundary_excludes_inherited_cloud_selectors(tmp_path):
    launcher = Path("scripts/run_local.sh").read_text(encoding="utf-8")
    # The clean boundary is the CLEAN_ENV array plus the one-line clean() function that applies it; the
    # servers start through the same array.
    start = launcher.index("CLEAN_ENV=(")
    end = launcher.index("\n", launcher.index("clean() {"))
    probe = "import json,os; print(json.dumps({key: os.environ.get(key) for key in " + repr(CLOUD_FLAGS) + "}))"
    command = launcher[start:end] + '\nclean "$@"'
    result = subprocess.run(
        ["/bin/bash", "-c", command, "launcher-clean-test", sys.executable, "-c", probe],
        env={
            "HOME": str(tmp_path),
            "USER": "synthetic-user",
            "CLEAN_PATH": os.defpath,
            **dict.fromkeys(CLOUD_FLAGS, "true"),
        },
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == dict.fromkeys(CLOUD_FLAGS)
