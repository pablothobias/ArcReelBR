"""Tests for validate_script_filename."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# validate_script_filename — shared guard for all enqueue tools
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "scripts/episode_1.json",  # Reject every separator, including a scripts/ prefix.
        "../etc/passwd",
        "sub/dir/file.json",
        "a\\b.json",
        ".",
        "..",
    ],
)
def test_validate_script_filename_rejects_paths(bad: str) -> None:
    from server.media_tools.context import validate_script_filename

    with pytest.raises(
        ValueError, match=r"script (filename must not be empty|must be a bare filename without path separators)"
    ):
        validate_script_filename(bad)


@pytest.mark.parametrize("bad", [1, None, ["episode_1.json"], {"name": "episode_1.json"}])
def test_validate_script_filename_rejects_non_string_agent_args(bad: object) -> None:
    """The Agent supplies raw JSON values; nonstrings must also become ValueError."""

    from server.media_tools.context import validate_script_filename

    with pytest.raises(ValueError, match="script filename must not be empty"):
        validate_script_filename(bad)


def test_validate_script_filename_accepts_basename() -> None:
    from server.media_tools.context import validate_script_filename

    assert validate_script_filename("episode_1.json") == "episode_1.json"
