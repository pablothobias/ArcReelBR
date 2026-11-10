"""Subscription text contracts without invoking the local runtime or providers."""

import asyncio
import json
from pathlib import Path

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock
from pydantic import BaseModel

from lib.backends.text_backends.base import (
    ImageInput,
    StructuredOutputExhaustedError,
    TextGenerationRequest,
    TextOutputTruncatedError,
)
from lib.backends.text_backends.claude_subscription import (
    ClaudeSubscriptionTextBackend,
    SubscriptionAuthenticationError,
    SubscriptionQuotaPaused,
    verify_local_subscription,
)
from lib.config.claude_subscription import CLAUDE_SUBSCRIPTION_MODEL, CLAUDE_SUBSCRIPTION_PAIR
from lib.config.env_keys import CLAUDE_CLOUD_ROUTE_ENV_KEYS
from lib.infra.api_errors import BadRequestError
from server.routers._validators import validate_backend_value


class Answer(BaseModel):
    answer: str


class Runtime:
    def __init__(self, *, text="Hello", structured=None, error=False, status=None, stop_reason=None):
        self.text = text
        self.structured = structured
        self.error = error
        self.status = status
        self.stop_reason = stop_reason
        self.options = None
        self.messages = []
        self.auth_calls = 0

    async def auth(self, cli, cwd):
        self.auth_calls += 1
        assert Path(cli).name == "claude"
        assert await asyncio.to_thread(Path(cwd).is_dir)

    async def query(self, *, prompt, options):
        self.options = options
        self.messages = [message async for message in prompt]
        yield AssistantMessage(content=[TextBlock(self.text)], model=CLAUDE_SUBSCRIPTION_MODEL)
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=self.error,
            num_turns=1,
            session_id="isolated",
            result=self.text,
            structured_output=self.structured,
            stop_reason=self.stop_reason,
            api_error_status=self.status,
            usage={
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read_input_tokens": 3,
                "cache_creation_input_tokens": 2,
            },
            total_cost_usd=12.34,
        )

    def backend(self):
        return ClaudeSubscriptionTextBackend(sdk_query=self.query, auth_check=self.auth)


async def test_structured_output_is_validated_and_tokens_preserve_subscription_usage():
    runtime = Runtime(structured={"answer": "Olá"})
    result = await runtime.backend().generate(TextGenerationRequest(prompt="Answer", response_schema=Answer))
    assert json.loads(result.text) == {"answer": "Olá"}
    assert (result.input_tokens, result.output_tokens, result.cache_read_tokens, result.cache_write_5m_tokens) == (
        15,
        5,
        3,
        2,
    )
    assert result.provider == "claude-subscription"
    assert result.model == CLAUDE_SUBSCRIPTION_MODEL
    assert result.request_tokens()[0].input_tokens == 15
    options = runtime.options
    assert options.model == CLAUDE_SUBSCRIPTION_MODEL
    assert options.effort == "medium"
    assert options.tools == []
    assert options.mcp_servers == {}
    assert options.strict_mcp_config
    assert options.setting_sources == []
    assert options.skills == []
    assert options.plugins == []
    assert options.fallback_model is None
    assert options.resume is None
    assert not options.continue_conversation
    assert options.extra_args == {"no-session-persistence": None}
    assert not await asyncio.to_thread(Path(options.cwd).exists)


async def test_image_and_system_prompt_reach_isolated_runtime():
    runtime = Runtime()
    result = await runtime.backend().generate(
        TextGenerationRequest(
            prompt="Describe this",
            system_prompt="Use Brazilian Portuguese",
            images=[ImageInput(url="https://example.com/image.png")],
            max_output_tokens=20,
        )
    )
    assert result.text == "Hello"
    assert runtime.messages[0]["message"]["content"] == [
        {"type": "image", "source": {"type": "url", "url": "https://example.com/image.png"}},
        {"type": "text", "text": "Describe this"},
    ]
    assert runtime.options.system_prompt == "Use Brazilian Portuguese"
    assert runtime.options.env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "20"


async def test_invalid_structured_result_stops_without_another_generation():
    runtime = Runtime(structured={"wrong": 1})
    with pytest.raises(StructuredOutputExhaustedError):
        await runtime.backend().generate(TextGenerationRequest(prompt="Answer", response_schema=Answer))
    assert runtime.auth_calls == 1
    assert not await asyncio.to_thread(Path(runtime.options.cwd).exists)


async def test_truncation_is_exposed_for_text_and_rejected_for_structured_requests():
    runtime = Runtime(stop_reason="max_tokens")
    result = await runtime.backend().generate(TextGenerationRequest(prompt="Answer"))
    assert result.truncated
    with pytest.raises(TextOutputTruncatedError):
        await runtime.backend().generate(TextGenerationRequest(prompt="Answer", response_schema=Answer))


async def test_quota_is_a_resumable_pause_without_automatic_retry():
    runtime = Runtime(error=True, status=429)
    with pytest.raises(SubscriptionQuotaPaused) as captured:
        await runtime.backend().generate(TextGenerationRequest(prompt="Answer"))
    assert captured.value.resumable
    assert captured.value.code == "subscription_quota_paused"
    assert runtime.auth_calls == 1
    assert not await asyncio.to_thread(Path(runtime.options.cwd).exists)


async def test_cancelled_operation_closes_runtime_and_removes_isolation_directory():
    runtime = Runtime()
    entered = asyncio.Event()
    stopped = asyncio.Event()

    async def blocked_query(*, prompt, options):
        runtime.options = options
        try:
            entered.set()
            await asyncio.Event().wait()
            yield
        finally:
            stopped.set()

    backend = ClaudeSubscriptionTextBackend(sdk_query=blocked_query, auth_check=runtime.auth)
    task = asyncio.create_task(backend.generate(TextGenerationRequest(prompt="Answer")))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stopped.is_set()
    assert not await asyncio.to_thread(Path(runtime.options.cwd).exists)


async def test_api_environment_is_rejected_before_authentication(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-value")
    with pytest.raises(SubscriptionAuthenticationError, match="clean local login"):
        await verify_local_subscription("unused-cli", str(tmp_path))


@pytest.mark.parametrize("field", ["text_backend_simple", "text_backend_complex", "default_text_backend"])
def test_existing_settings_and_project_fields_accept_explicit_subscription_selection(field):
    validate_backend_value(CLAUDE_SUBSCRIPTION_PAIR, field)
    assert f"claude-subscription/{CLAUDE_SUBSCRIPTION_MODEL}" == CLAUDE_SUBSCRIPTION_PAIR


@pytest.mark.parametrize(
    ("value", "field"),
    [
        ("claude-subscription/claude-sonnet", "text_backend_simple"),
        (CLAUDE_SUBSCRIPTION_PAIR, "video_backend"),
        (CLAUDE_SUBSCRIPTION_PAIR, "image_backend"),
        ("claude-subscription", "text_backend_complex"),
    ],
)
def test_subscription_selection_rejects_model_substitution_and_other_media(value, field):
    with pytest.raises(BadRequestError):
        validate_backend_value(value, field)


async def test_timeout_stops_before_submission_and_cleans_up():
    runtime = Runtime()
    entered = asyncio.Event()

    async def pending_auth(cli, cwd):
        entered.set()
        await asyncio.Event().wait()

    backend = ClaudeSubscriptionTextBackend(timeout_seconds=0, sdk_query=runtime.query, auth_check=pending_auth)
    with pytest.raises(TimeoutError):
        await backend.generate(TextGenerationRequest(prompt="Answer"))
    assert entered.is_set()
    assert runtime.options is None


async def test_authentication_failure_never_submits_to_runtime():
    runtime = Runtime()

    async def failed_auth(cli, cwd):
        raise SubscriptionAuthenticationError("Login required")

    backend = ClaudeSubscriptionTextBackend(sdk_query=runtime.query, auth_check=failed_auth)
    with pytest.raises(SubscriptionAuthenticationError):
        await backend.generate(TextGenerationRequest(prompt="Answer"))
    assert runtime.options is None


@pytest.mark.parametrize(
    ("status", "accepted"),
    [
        ({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}, True),
        ({"loggedIn": True, "authMethod": "api_key", "apiProvider": "firstParty"}, False),
        ({"loggedIn": False}, False),
    ],
)
async def test_official_auth_status_requires_local_first_party_subscription(status, accepted, monkeypatch, tmp_path):
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_OAUTH_TOKEN"):
        monkeypatch.delenv(key, raising=False)

    class Process:
        returncode = 0

        async def communicate(self):
            return json.dumps(status).encode(), None

    async def process_factory(*args, **kwargs):
        assert args == ("official-cli", "auth", "status", "--json")
        return Process()

    if accepted:
        await verify_local_subscription("official-cli", str(tmp_path), process_factory=process_factory)
        assert status["subscriptionType"] == "max"
    else:
        with pytest.raises(SubscriptionAuthenticationError):
            await verify_local_subscription("official-cli", str(tmp_path), process_factory=process_factory)


async def test_auth_status_never_inherits_the_server_terminal(monkeypatch, tmp_path):
    # A child that inherits a background job's tty stdin gets SIGTTIN/SIGTTOU, which stops the whole
    # server process group (uv, uvicorn and the child), so the backend stops accepting connections.
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_OAUTH_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    status = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}
    seen: dict = {}

    class Process:
        returncode = 0

        async def communicate(self):
            return json.dumps(status).encode(), None

    async def process_factory(*args, **kwargs):
        seen.update(kwargs)
        return Process()

    await verify_local_subscription("official-cli", str(tmp_path), process_factory=process_factory)
    assert seen.get("stdin") == asyncio.subprocess.DEVNULL


async def test_rejected_quota_event_closes_stream_before_overage_or_another_submission():
    from claude_agent_sdk import RateLimitEvent, RateLimitInfo

    runtime = Runtime()
    closed = asyncio.Event()

    async def exhausted_query(*, prompt, options):
        try:
            yield RateLimitEvent(
                rate_limit_info=RateLimitInfo(status="rejected", overage_status="allowed"),
                uuid="event",
                session_id="isolated",
            )
            pytest.fail("A rejected quota event must stop consumption")
        finally:
            closed.set()

    backend = ClaudeSubscriptionTextBackend(sdk_query=exhausted_query, auth_check=runtime.auth)
    with pytest.raises(SubscriptionQuotaPaused):
        await backend.generate(TextGenerationRequest(prompt="Answer"))
    assert closed.is_set()


async def test_subscription_usage_keeps_one_hour_cache_creation_separate():
    runtime = Runtime()

    async def cached_query(*, prompt, options):
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="isolated",
            result="ok",
            usage={
                "input_tokens": 2,
                "output_tokens": 60,
                "cache_creation_input_tokens": 1098,
                "cache_creation": {"ephemeral_1h_input_tokens": 1098, "ephemeral_5m_input_tokens": 0},
            },
        )

    result = await ClaudeSubscriptionTextBackend(sdk_query=cached_query, auth_check=runtime.auth).generate(
        TextGenerationRequest(prompt="Answer")
    )
    assert result.input_tokens == 1100
    assert result.cache_write_1h_tokens == 1098
    assert result.cache_write_5m_tokens == 0


async def test_concurrent_generations_use_distinct_sessions_and_isolation_directories():
    directories = []
    admitted = asyncio.Event()
    runtime = Runtime()

    async def overlapping_query(*, prompt, options):
        directories.append(options.cwd)
        if len(directories) == 2:
            admitted.set()
        await admitted.wait()
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="isolated",
            result="ok",
        )

    backend = ClaudeSubscriptionTextBackend(sdk_query=overlapping_query, auth_check=runtime.auth)
    results = await asyncio.gather(*(backend.generate(TextGenerationRequest(prompt="Answer")) for _ in range(2)))
    assert [result.text for result in results] == ["ok", "ok"]
    assert len(set(directories)) == 2
    assert runtime.auth_calls == 2
    assert not any(await asyncio.gather(*(asyncio.to_thread(Path(directory).exists) for directory in directories)))


@pytest.mark.parametrize("flag", CLAUDE_CLOUD_ROUTE_ENV_KEYS)
@pytest.mark.parametrize("enabled", [True, False])
async def test_subscription_auth_uses_shared_cloud_route_semantics(monkeypatch, tmp_path, flag, enabled):
    from lib.config.env_keys import CLAUDE_CLOUD_ROUTE_ENV_KEYS, CLAUDE_SUBSCRIPTION_API_ENV_KEYS

    for key in (*CLAUDE_CLOUD_ROUTE_ENV_KEYS, *CLAUDE_SUBSCRIPTION_API_ENV_KEYS):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(flag, " YES " if enabled else "false")

    class Process:
        returncode = 0

        async def communicate(self):
            return json.dumps(
                {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}
            ).encode(), None

    async def process_factory(*args, **kwargs):
        assert not enabled, "An enabled cloud route must be refused before authentication"
        return Process()

    if enabled:
        with pytest.raises(SubscriptionAuthenticationError, match="clean local login"):
            await verify_local_subscription("unused-cli", str(tmp_path), process_factory=process_factory)
    else:
        assert await verify_local_subscription("unused-cli", str(tmp_path), process_factory=process_factory) is None
