"""Claude cloud-route booleans match the supported CLI selector contract."""

import pytest

from lib.config.claude_subscription import SubscriptionRouteConflictError, enabled_claude_cloud_routes
from lib.config.env_keys import CLAUDE_CLOUD_ROUTE_ENV_KEYS
from lib.infra.retry import should_retry


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", " TrUe ", " YES "])
def test_enabled_selectors_use_cli_boolean_values(value):
    environment = dict.fromkeys(CLAUDE_CLOUD_ROUTE_ENV_KEYS, value)
    assert enabled_claude_cloud_routes(environment) == CLAUDE_CLOUD_ROUTE_ENV_KEYS
    assert all(raw == value for raw in environment.values())


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", " FaLsE ", "unexpected"])
def test_disabled_or_unknown_values_do_not_select_cloud(value):
    assert enabled_claude_cloud_routes(dict.fromkeys(CLAUDE_CLOUD_ROUTE_ENV_KEYS, value)) == ()


def test_missing_selectors_leave_subscription_route_available():
    assert enabled_claude_cloud_routes({}) == ()


def test_route_conflict_is_nonretryable_and_reports_names_only():
    error = SubscriptionRouteConflictError(("CLAUDE_CODE_USE_VERTEX",))
    assert "CLAUDE_CODE_USE_VERTEX" in str(error)
    assert not should_retry(error, (RuntimeError,))
