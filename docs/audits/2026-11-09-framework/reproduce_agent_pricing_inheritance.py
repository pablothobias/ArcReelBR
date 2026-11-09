"""Audit-only pre-spawn capture: no real credentials, subprocesses or provider calls."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk._internal.transport import subprocess_cli

from lib.config.service import build_anthropic_env
from server.agent_runtime.options_assembler import load_provider_env_overrides, agent_pricing_of


@pytest.mark.parametrize('mode_key', ['CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY'])
async def test_zero_price_with_inherited_cloud_mode(monkeypatch, mode_key):
    # Synthetic process flags only; do not inspect or output any real credential.
    for key in ['CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY']:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(mode_key, '1')
    credential_repo = AsyncMock()
    credential_repo.get_active.return_value = None
    settings_repo = AsyncMock()
    settings_repo.get_all.return_value = {}
    monkeypatch.setattr('lib.db.repositories.agent_credential_repo.AgentCredentialRepository', lambda _: credential_repo)
    monkeypatch.setattr('lib.config.service.SystemSettingRepository', lambda _: settings_repo)
    built = await build_anthropic_env(AsyncMock())
    assert built.pricing.multiplier == 0
    async def already_built(_):
        return built
    monkeypatch.setattr('lib.config.service.build_anthropic_env', already_built)
    overrides = await load_provider_env_overrides()
    assert mode_key not in overrides
    assert overrides['ANTHROPIC_API_KEY'] == ''
    assert overrides['ANTHROPIC_AUTH_TOKEN'] == ''
    assert overrides['CLAUDE_CODE_OAUTH_TOKEN'] == ''
    captured = {}
    async def prevent_spawn(*args, **kwargs):
        captured['mode'] = kwargs['env'].get(mode_key)
        captured['api_key_empty'] = kwargs['env'].get('ANTHROPIC_API_KEY') == ''
        raise RuntimeError('isolated audit: subprocess creation prevented')
    monkeypatch.setattr(subprocess_cli.anyio, 'open_process', prevent_spawn)
    transport = subprocess_cli.SubprocessCLITransport(prompt='audit', options=ClaudeAgentOptions(cli_path='/bin/true', env=overrides))
    monkeypatch.setattr(transport, '_check_claude_version', AsyncMock())
    with pytest.raises(Exception):
        await transport.connect()
    assert captured == {'mode': '1', 'api_key_empty': True}
    assert agent_pricing_of(SimpleNamespace(env=overrides)).multiplier == 0
    print({'synthetic_cloud_flag': mode_key, 'survives_sdk_environment_merge': True,
           'agent_pricing_multiplier': 0.0, 'process_spawned': False})
