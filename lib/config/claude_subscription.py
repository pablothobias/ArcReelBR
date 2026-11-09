"""Explicit local subscription text selection, independent of API-provider catalogs."""

from collections.abc import Mapping

from lib.config.env_keys import CLAUDE_CLOUD_ROUTE_ENV_KEYS
from lib.infra.retry import NonRetryableError

CLAUDE_SUBSCRIPTION_PROVIDER = "claude-subscription"
CLAUDE_SUBSCRIPTION_MODEL = "claude-opus-5-5"
CLAUDE_SUBSCRIPTION_PAIR = f"{CLAUDE_SUBSCRIPTION_PROVIDER}/{CLAUDE_SUBSCRIPTION_MODEL}"


def enabled_claude_cloud_routes(environment: Mapping[str, str]) -> tuple[str, ...]:
    """Resolve cloud selectors using the Claude CLI's case-insensitive, whitespace-trimmed boolean values."""
    return tuple(
        key
        for key in CLAUDE_CLOUD_ROUTE_ENV_KEYS
        if environment.get(key, "").strip().lower() in {"1", "true", "yes", "on"}
    )


class SubscriptionRouteConflictError(NonRetryableError):
    """Local subscription pricing cannot represent an explicitly enabled cloud route."""

    def __init__(self, routes: tuple[str, ...]) -> None:
        super().__init__(
            "Local subscription Agent pricing conflicts with enabled cloud route flags: "
            + ", ".join(routes)
            + ". Use a clean local subscription route; this request did not start inference."
        )
