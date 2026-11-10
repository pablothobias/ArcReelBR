"""Global ArcReel asset-library Agent tools (MCP-018): list/read, save from a project and apply to another project.

The tools reuse the same service as the Web ``/assets`` routes; these cases check the tool contract: derivatives and
reference audio travel with the character, provenance is kept, conflicts follow the explicit policy, results carry no
storage paths, products are not library types, and no generation task is enqueued.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from lib.generation.generation_queue import GenerationQueue
from lib.project.asset_derivatives import derivative_sheet_relative_path
from lib.project.asset_types import DERIVATIVES_FIELD, GLOBAL_LIBRARY_ASSET_TYPES
from lib.project.project_manager import ProjectManager
from server.agent_toolset.declaration import invoke_unscoped_declaration
from server.agent_toolset.global_asset_library import (
    APPLY_GLOBAL_LIBRARY_ASSETS,
    GET_GLOBAL_LIBRARY_ASSET,
    LIST_GLOBAL_LIBRARY_ASSETS,
    SAVE_ASSET_TO_GLOBAL_LIBRARY,
)
from server.media_tools.global_asset_library import SaveToGlobalLibraryRequest
from server.tool_runtime import CallerContext, Services, ToolOutcome
from tests.fakes import bind_session_factory
from tests.integration.server.agent_tool_support import ToolHarness, problem_of, run_declared_tool


@pytest.fixture
def library(tmp_path: Path, db_factory, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    bind_session_factory(monkeypatch, db_factory)
    pm = ProjectManager(tmp_path / "projects")
    monkeypatch.setenv("ARCREEL_DATA_DIR", str(pm.data_root))

    pm.create_project("source")
    pm.create_project_metadata("source", "Source")
    pm.add_project_character("source", "王", "白衣少年", "清朗")
    pm.install_asset_sheet_bytes("character", "source", "王", "characters/王.png", b"owner-sheet")
    project_dir = pm.get_project_path("source")
    derivative_rel = derivative_sheet_relative_path("王", "战斗装")
    (project_dir / derivative_rel).parent.mkdir(parents=True, exist_ok=True)
    (project_dir / derivative_rel).write_bytes(b"battle-sheet")
    audio_rel = "characters/refs_audio/王.wav"
    (project_dir / audio_rel).parent.mkdir(parents=True, exist_ok=True)
    (project_dir / audio_rel).write_bytes(b"voice-bytes")

    def _bind(entry: dict) -> None:
        entry[DERIVATIVES_FIELD] = {"战斗装": {"description": "黑甲", "character_sheet": derivative_rel}}
        entry["reference_audio"] = audio_rel

    pm.update_asset_entry("character", "source", "王", _bind)

    pm.create_project("target")
    pm.create_project_metadata("target", "Target")
    queue = GenerationQueue(session_factory=db_factory)
    return {"pm": pm, "data_root": tmp_path, "queue": queue, "db_factory": db_factory}


class _LibraryHarness(ToolHarness):
    """Tool harness whose ``Services.sessions`` is the test database, as the library tools read it."""

    def __init__(self, *args: Any, sessions: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._sessions = sessions

    @property
    def services(self) -> Services:
        return replace(super().services, sessions=self._sessions)


def _harness(library: dict[str, Any], project: str) -> ToolHarness:
    return _LibraryHarness(
        project,
        library["data_root"],
        pm=library["pm"],
        queue=library["queue"],
        caller=CallerContext(user_id="default", source="mcp"),
        sessions=library["db_factory"],
    )


async def _unscoped(declaration, library: dict[str, Any], arguments: dict[str, Any]) -> ToolOutcome[Any]:
    ctx = _harness(library, "source")
    return await invoke_unscoped_declaration(declaration, arguments, ctx.caller, ctx.services)


async def _assert_no_generation(library: dict[str, Any]) -> None:
    for project in ("source", "target"):
        for status in ("queued", "running", "succeeded", "failed"):
            listing = await library["queue"].list_tasks(project_name=project, status=status, page=1, page_size=50)
            assert listing["items"] == [], (project, status)


def _assert_no_paths(value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False)
    assert "global_assets" not in text
    assert "image_path" not in text
    assert "audio_path" not in text


async def test_character_round_trips_with_derivatives_audio_and_provenance(library) -> None:
    saved = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY, _harness(library, "source"), {"resource_type": "character", "name": "王"}
    )
    assert saved.problem is None
    asset = saved.value["asset"]
    assert (asset["name"], asset["source_project"], asset["description"], asset["voice_style"]) == (
        "王",
        "source",
        "白衣少年",
        "清朗",
    )
    assert asset["has_image"]
    assert asset["has_reference_audio"]
    assert asset["derivatives"] == [{"name": "战斗装", "description": "黑甲", "has_image": True}]
    _assert_no_paths(saved.value)

    listed = await _unscoped(LIST_GLOBAL_LIBRARY_ASSETS, library, {"type": "character"})
    assert [item["id"] for item in listed.value["items"]] == [asset["id"]]
    assert listed.value["counts"] == {"character": 1, "prop": 0, "scene": 0}
    _assert_no_paths(listed.value)
    read = await _unscoped(GET_GLOBAL_LIBRARY_ASSET, library, {"asset_id": asset["id"]})
    assert read.value["asset"] == asset

    applied = await run_declared_tool(
        APPLY_GLOBAL_LIBRARY_ASSETS,
        _harness(library, "target"),
        {"asset_ids": [asset["id"]], "conflict_policy": "skip"},
    )
    assert applied.problem is None
    assert applied.value == {"succeeded": [{"id": asset["id"], "name": "王"}], "skipped": [], "failed": []}

    pm: ProjectManager = library["pm"]
    target_dir = pm.get_project_path("target")
    character = pm.load_project("target")["characters"]["王"]
    assert (target_dir / character["character_sheet"]).read_bytes() == b"owner-sheet"
    assert (target_dir / character["reference_audio"]).read_bytes() == b"voice-bytes"
    derivative = character[DERIVATIVES_FIELD]["战斗装"]
    assert derivative["description"] == "黑甲"
    assert (target_dir / derivative["character_sheet"]).read_bytes() == b"battle-sheet"
    await _assert_no_generation(library)


async def test_conflicts_follow_the_explicit_policy(library) -> None:
    source = _harness(library, "source")
    asset = (
        await run_declared_tool(SAVE_ASSET_TO_GLOBAL_LIBRARY, source, {"resource_type": "character", "name": "王"})
    ).value["asset"]

    duplicate = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY, source, {"resource_type": "character", "name": "王"}
    )
    problem = problem_of(duplicate)
    assert problem.code == "asset_already_exists"
    assert problem.params["existing"]["id"] == asset["id"]
    _assert_no_paths(problem.params)
    overwritten = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY, source, {"resource_type": "character", "name": "王", "overwrite": True}
    )
    assert overwritten.value["asset"]["id"] == asset["id"]

    target = _harness(library, "target")
    library["pm"].add_project_character("target", "王", "原有描述", "")

    skipped = await run_declared_tool(
        APPLY_GLOBAL_LIBRARY_ASSETS, target, {"asset_ids": [asset["id"]], "conflict_policy": "skip"}
    )
    assert skipped.value["skipped"] == [{"id": asset["id"], "name": "王"}]
    assert library["pm"].load_project("target")["characters"]["王"]["description"] == "原有描述"

    renamed = await run_declared_tool(
        APPLY_GLOBAL_LIBRARY_ASSETS, target, {"asset_ids": [asset["id"]], "conflict_policy": "rename"}
    )
    assert renamed.value["succeeded"] == [{"id": asset["id"], "name": "王 (2)"}]

    overwrite = await run_declared_tool(
        APPLY_GLOBAL_LIBRARY_ASSETS, target, {"asset_ids": [asset["id"], "missing"], "conflict_policy": "overwrite"}
    )
    assert overwrite.value["succeeded"] == [{"id": asset["id"], "name": "王"}]
    assert overwrite.value["failed"] == [{"id": "missing", "reason": "not_found"}]
    characters = library["pm"].load_project("target")["characters"]
    assert characters["王"]["description"] == "白衣少年"
    assert set(characters) == {"王", "王 (2)"}
    await _assert_no_generation(library)


async def test_conflict_policy_is_required_and_products_are_not_library_types(library) -> None:
    target = _harness(library, "target")
    missing_policy = await run_declared_tool(APPLY_GLOBAL_LIBRARY_ASSETS, target, {"asset_ids": ["x"]})
    assert problem_of(missing_policy).code == "invalid_request"

    product = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY, _harness(library, "source"), {"resource_type": "product", "name": "保温杯"}
    )
    assert problem_of(product).code == "invalid_request"
    schema_types = SaveToGlobalLibraryRequest.model_json_schema()["properties"]["resource_type"]["enum"]
    assert set(schema_types) == set(GLOBAL_LIBRARY_ASSET_TYPES)


async def test_unknown_project_asset_and_entry_are_reported(library) -> None:
    missing_asset = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY, _harness(library, "source"), {"resource_type": "scene", "name": "不存在"}
    )
    assert problem_of(missing_asset).code == "asset_source_resource_not_found"

    missing_entry = await _unscoped(GET_GLOBAL_LIBRARY_ASSET, library, {"asset_id": "nope"})
    assert problem_of(missing_entry).code == "asset_not_found"


async def test_overwriting_another_projects_library_entry_needs_explicit_confirmation(library) -> None:
    asset = (
        await run_declared_tool(
            SAVE_ASSET_TO_GLOBAL_LIBRARY, _harness(library, "source"), {"resource_type": "character", "name": "王"}
        )
    ).value["asset"]
    library["pm"].add_project_character("target", "王", "另一个王", "")
    target = _harness(library, "target")

    refused = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY, target, {"resource_type": "character", "name": "王", "overwrite": True}
    )
    problem = problem_of(refused)
    assert problem.code == "library_cross_project_overwrite_requires_confirmation"
    assert problem.params["existing_source_project"] == "source"
    _assert_no_paths(problem.params)
    unchanged = (await _unscoped(GET_GLOBAL_LIBRARY_ASSET, library, {"asset_id": asset["id"]})).value["asset"]
    assert (unchanged["source_project"], unchanged["description"]) == ("source", "白衣少年")

    assert problem.params["existing_updated_at"] == unchanged["updated_at"]

    not_strict = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY, target, {"resource_type": "character", "name": "王", "overwrite": "true"}
    )
    assert problem_of(not_strict).code == "invalid_request"

    # Consent that does not match what the refusal reported (a blind or outdated guess) is refused again.
    blind = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY,
        target,
        {
            "resource_type": "character",
            "name": "王",
            "overwrite": True,
            "cross_project_overwrite": {
                "existing_source_project": "source",
                "existing_updated_at": "2000-01-01T00:00:00",
            },
        },
    )
    again = problem_of(blind)
    assert again.code == "library_cross_project_overwrite_requires_confirmation"
    assert again.params["existing_updated_at"] == unchanged["updated_at"]

    confirmed = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY,
        target,
        {
            "resource_type": "character",
            "name": "王",
            "overwrite": True,
            "cross_project_overwrite": {
                "existing_source_project": problem.params["existing_source_project"],
                "existing_updated_at": problem.params["existing_updated_at"],
            },
        },
    )
    assert confirmed.problem is None
    replaced = confirmed.value["asset"]
    assert (replaced["id"], replaced["source_project"], replaced["description"]) == (asset["id"], "target", "另一个王")

    # The consent observed before the overwrite is stale now: the source project cannot reuse it to take the entry back.
    stale = await run_declared_tool(
        SAVE_ASSET_TO_GLOBAL_LIBRARY,
        _harness(library, "source"),
        {
            "resource_type": "character",
            "name": "王",
            "overwrite": True,
            "cross_project_overwrite": {
                "existing_source_project": "source",
                "existing_updated_at": unchanged["updated_at"],
            },
        },
    )
    assert problem_of(stale).params["existing_source_project"] == "target"
    await _assert_no_generation(library)
