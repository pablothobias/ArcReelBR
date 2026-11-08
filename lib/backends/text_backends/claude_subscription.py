"""Internal text generation using the official locally authenticated Claude runtime."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import aclosing
from importlib.resources import files
from typing import Any, cast

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, RateLimitEvent, ResultMessage, TextBlock, query

from lib.backends.image_backends.base import image_to_base64_data_uri
from lib.backends.text_backends.base import (
    StructuredOutputExhaustedError,
    SubscriptionQuotaPaused,
    TextCapability,
    TextGenerationRequest,
    TextGenerationResult,
    check_truncation,
    resolve_schema,
    structured_fallback_reason,
)
from lib.config.claude_subscription import CLAUDE_SUBSCRIPTION_MODEL, CLAUDE_SUBSCRIPTION_PROVIDER
from lib.infra.async_thread import run_noninterruptible_sync, run_sync_transaction
from lib.infra.retry import NonRetryableError

# These variables can select separately billed authentication or alternative endpoints.
_API_ENVIRONMENT = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
        "ANTHROPIC_CUSTOM_HEADERS",
        "ANTHROPIC_BEDROCK_BASE_URL",
        "ANTHROPIC_VERTEX_BASE_URL",
    }
)


class SubscriptionAuthenticationError(NonRetryableError):
    """The official runtime cannot verify an isolated subscription login."""


async def verify_local_subscription(
    cli_path: str, cwd: str, *, process_factory: Callable[..., Any] = asyncio.create_subprocess_exec
) -> None:
    """Use official auth status only; never inspect credential files or extract tokens."""
    if any(os.environ.get(key) for key in _API_ENVIRONMENT):
        raise SubscriptionAuthenticationError(
            "Subscription text requires a clean local login environment; remove API, bearer-token and cloud-provider overrides."
        )
    process = await process_factory(
        cli_path,
        "auth",
        "status",
        "--json",
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await process.communicate()
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    try:
        status = json.loads(stdout)
    except (ValueError, TypeError) as exc:
        raise SubscriptionAuthenticationError(
            "Official Claude auth status could not verify a subscription login."
        ) from exc
    if (
        not isinstance(status, dict)
        or process.returncode
        or status.get("loggedIn") is not True
        or status.get("authMethod") != "claude.ai"
        or status.get("apiProvider") != "firstParty"
        or not status.get("subscriptionType")
    ):
        raise SubscriptionAuthenticationError(
            "Sign in to the official Claude runtime with a subscription before resuming internal text generation."
        )


def _content(request: TextGenerationRequest) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for image in request.images or []:
        if image.path:
            header, data = image_to_base64_data_uri(image.path).split(",", 1)
            source = {"type": "base64", "media_type": header.removeprefix("data:").split(";", 1)[0], "data": data}
        elif image.url:
            source = {"type": "url", "url": image.url}
        else:
            raise ValueError("An image input must have a path or URL.")
        content.append({"type": "image", "source": source})
    content.append({"type": "text", "text": request.prompt})
    return content


class ClaudeSubscriptionTextBackend:
    """Tool-free, fresh SDK sessions; no supervising conversation or media credentials."""

    def __init__(
        self,
        *,
        model: str = CLAUDE_SUBSCRIPTION_MODEL,
        timeout_seconds: float = 300,
        sdk_query: Callable[..., AsyncIterator[Any]] = query,
        auth_check: Callable[..., Any] = verify_local_subscription,
    ) -> None:
        if model != CLAUDE_SUBSCRIPTION_MODEL:
            raise ValueError(f"Subscription text requires {CLAUDE_SUBSCRIPTION_MODEL}.")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._query = sdk_query
        self._auth_check = auth_check

    @property
    def name(self) -> str:
        return CLAUDE_SUBSCRIPTION_PROVIDER

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> set[TextCapability]:
        return {TextCapability.TEXT_GENERATION, TextCapability.STRUCTURED_OUTPUT, TextCapability.VISION}

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        directories: list[tempfile.TemporaryDirectory[str]] = []

        def create_directory() -> str:
            directory = tempfile.TemporaryDirectory(prefix="arcreel-internal-text-")
            directories.append(directory)
            return directory.name

        try:
            cwd = await run_sync_transaction(create_directory)
            cli = str(
                files("claude_agent_sdk").joinpath("_bundled", "claude.exe" if sys.platform == "win32" else "claude")
            )
            async with asyncio.timeout(self._timeout_seconds):
                await self._auth_check(cli, cwd)
                content = await asyncio.to_thread(_content, request)
                options = ClaudeAgentOptions(
                    cli_path=cli,
                    cwd=cwd,
                    model=self.model,
                    effort="medium",
                    tools=[],
                    allowed_tools=[],
                    mcp_servers={},
                    strict_mcp_config=True,
                    setting_sources=[],
                    skills=[],
                    plugins=[],
                    permission_mode="dontAsk",
                    max_turns=1,
                    system_prompt=request.system_prompt
                    or "Complete the requested internal text operation without tools.",
                    output_format=(
                        {"type": "json_schema", "schema": resolve_schema(request.response_schema)}
                        if request.response_schema is not None
                        else None
                    ),
                    env={"CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(request.max_output_tokens or 64000)},
                    extra_args={"no-session-persistence": None},
                    stderr=lambda _line: None,
                )

                async def prompt() -> AsyncIterator[dict[str, Any]]:
                    yield {"type": "user", "message": {"role": "user", "content": content}}

                result: ResultMessage | None = None
                text_parts: list[str] = []
                stop_reason: str | None = None
                async with aclosing(
                    cast(AsyncGenerator[Any, None], self._query(prompt=prompt(), options=options))
                ) as messages:
                    async for message in messages:
                        if isinstance(message, RateLimitEvent) and message.rate_limit_info.status == "rejected":
                            raise SubscriptionQuotaPaused()
                        if isinstance(message, AssistantMessage):
                            if message.error == "rate_limit":
                                raise SubscriptionQuotaPaused()
                            if message.error:
                                raise NonRetryableError(
                                    "Claude subscription text operation failed; check the local runtime before resuming."
                                )
                            if message.model != self.model:
                                raise NonRetryableError(
                                    "Claude runtime returned an unexpected model; subscription text operation stopped."
                                )
                            stop_reason = message.stop_reason or stop_reason
                            text_parts.extend(block.text for block in message.content if isinstance(block, TextBlock))
                        elif isinstance(message, ResultMessage):
                            result = message
                if result is None:
                    raise NonRetryableError(
                        "Claude subscription text ended without a terminal result; inspect state before retrying."
                    )
                if result.api_error_status == 429:
                    raise SubscriptionQuotaPaused()
                if result.is_error:
                    raise NonRetryableError(
                        "Claude subscription text operation failed; inspect the local runtime before retrying."
                    )
                usage = result.usage or {}
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_write = usage.get("cache_creation_input_tokens", 0)
                cache_breakdown = usage.get("cache_creation") or {}
                cache_write_1h = cache_breakdown.get("ephemeral_1h_input_tokens", 0)
                cache_write_5m = cache_breakdown.get("ephemeral_5m_input_tokens", cache_write - cache_write_1h)
                input_tokens = usage.get("input_tokens")
                text = (
                    json.dumps(result.structured_output, ensure_ascii=False)
                    if result.structured_output is not None
                    else result.result or "".join(text_parts)
                )
                truncated = check_truncation(
                    result.stop_reason or stop_reason,
                    provider=self.name,
                    model=self.model,
                    structured=request.response_schema is not None,
                    output_tokens=usage.get("output_tokens"),
                )
                reason = structured_fallback_reason(text, request.response_schema)
                if reason:
                    raise StructuredOutputExhaustedError(provider=self.name, model=self.model, reason=reason)
                return TextGenerationResult(
                    text=text,
                    provider=self.name,
                    model=self.model,
                    input_tokens=(input_tokens + cache_read + cache_write if input_tokens is not None else None),
                    output_tokens=usage.get("output_tokens"),
                    cache_read_tokens=cache_read,
                    cache_write_5m_tokens=cache_write_5m,
                    cache_write_1h_tokens=cache_write_1h,
                    truncated=truncated,
                )
        finally:
            for directory in directories:
                await run_noninterruptible_sync(directory.cleanup)
