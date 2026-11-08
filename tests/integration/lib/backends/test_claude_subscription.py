"""Subscription selection and accounting through real configuration and ledger consumers."""

import asyncio

from claude_agent_sdk import ResultMessage
from sqlalchemy import select

from lib.backends.providers import CallPurpose
from lib.backends.text_backends.base import TextGenerationRequest, TextTaskType
from lib.backends.text_backends.claude_subscription import ClaudeSubscriptionTextBackend
from lib.backends.text_backends.factory import create_text_backend_for_task
from lib.backends.text_generator import TextGenerator
from lib.billing.ledger import Ledger
from lib.config.claude_subscription import CLAUDE_SUBSCRIPTION_MODEL, CLAUDE_SUBSCRIPTION_PAIR
from lib.config.resolver import ConfigResolver
from lib.config.service import ConfigService
from lib.db.models.api_call import ApiCall
from lib.project.project_manager import get_project_manager


async def test_tiers_and_project_override_preserve_existing_resolution(db_factory, monkeypatch):
    async with db_factory() as session:
        service = ConfigService(session)
        await service.set_setting("text_backend_simple", CLAUDE_SUBSCRIPTION_PAIR)
        await service.set_setting("text_backend_complex", "gemini-aistudio/gemini-3-flash-preview")
        await session.commit()
    resolver = ConfigResolver(db_factory)
    assert await resolver.text_backend_for_task(TextTaskType.OVERVIEW) == (
        "claude-subscription",
        CLAUDE_SUBSCRIPTION_MODEL,
    )
    assert await resolver.text_backend_for_task(TextTaskType.STYLE_ANALYSIS) == (
        "claude-subscription",
        CLAUDE_SUBSCRIPTION_MODEL,
    )
    assert await resolver.text_backend_for_task(TextTaskType.SCRIPT) == ("gemini-aistudio", "gemini-3-flash-preview")

    def prepare_project():
        manager = get_project_manager()
        manager.create_project("subscription-test")
        manager.update_project(
            "subscription-test", lambda project: project.update({"default_text_backend": CLAUDE_SUBSCRIPTION_PAIR})
        )

    await asyncio.to_thread(prepare_project)
    assert await resolver.text_backend_for_task(TextTaskType.SCRIPT, "subscription-test") == (
        "claude-subscription",
        CLAUDE_SUBSCRIPTION_MODEL,
    )
    monkeypatch.setattr("lib.backends.text_backends.factory.async_session_factory", db_factory)
    backend, provider = await create_text_backend_for_task(TextTaskType.SCRIPT, "subscription-test")
    assert isinstance(backend, ClaudeSubscriptionTextBackend)
    assert provider == "claude-subscription"
    assert backend.model == CLAUDE_SUBSCRIPTION_MODEL


async def test_text_generator_persists_tokens_without_inventing_subscription_api_price(db_factory):
    async def auth_check(cli, cwd):
        return None

    async def sdk_query(*, prompt, options):
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="isolated",
            result="Olá",
            usage={"input_tokens": 10, "output_tokens": 5},
            total_cost_usd=12.34,
        )

    generator = TextGenerator(
        ClaudeSubscriptionTextBackend(sdk_query=sdk_query, auth_check=auth_check),
        Ledger(session_factory=db_factory),
        "claude-subscription",
        purpose=CallPurpose.PROJECT_OVERVIEW,
    )
    result = await generator.generate(TextGenerationRequest(prompt="A brief overview"), "subscription-test")
    async with db_factory() as session:
        rows = list((await session.execute(select(ApiCall))).scalars())
    assert result.text == "Olá"
    assert len(rows) == 1
    assert rows[0].status == "success"
    assert rows[0].input_tokens == 10
    assert rows[0].output_tokens == 5
    assert rows[0].cost_amount is None
    assert rows[0].provider == "claude-subscription"
    assert rows[0].model == CLAUDE_SUBSCRIPTION_MODEL
