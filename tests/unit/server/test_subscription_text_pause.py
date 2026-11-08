"""Subscription quota remains a director-visible pause across text consumers and queued failures."""

import pytest

from lib.backends.text_backends.base import SubscriptionQuotaPaused
from lib.generation.generation_result import GenerationAction, problem_from_task_failure
from lib.generation.task_failure import encode_failure
from server.text_generation import UnexpectedTextGenerationError
from server.tool_runtime import _run_text_generation


@pytest.mark.parametrize("wrapped", [False, True])
async def test_text_consumer_pause_is_preserved_through_wrapper_and_queue_encoding(wrapped):
    async def operation():
        try:
            raise SubscriptionQuotaPaused()
        except SubscriptionQuotaPaused as exc:
            if wrapped:
                raise UnexpectedTextGenerationError("Text operation failed") from exc
            raise

    result = await _run_text_generation("generate_script_plan", operation())
    assert result.problem is not None
    assert result.problem.code == "subscription_quota_paused"
    assert result.problem.action == GenerationAction.NONE
    assert result.problem.params == {"resumable": True}
    assert "resume after quota resets" in result.problem.detail
    persisted = encode_failure(result.problem.code, **(result.problem.params or {}))
    restored = problem_from_task_failure(persisted)
    assert restored.code == "subscription_quota_paused"
    assert restored.action == GenerationAction.NONE
    assert restored.params == {"resumable": True}
