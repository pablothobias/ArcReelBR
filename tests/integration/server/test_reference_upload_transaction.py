"""Character-image MCP uploads share native project/file transaction guarantees."""

from __future__ import annotations

import asyncio
import base64
import os
import threading
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from PIL import Image

from lib.i18n import _
from lib.project.project_manager import ProjectManager, get_project_manager
from server.media_tools.workflow_access import UploadReferenceRequest, upload_reference
from server.routers.files import upload_project_file
from server.tool_runtime import CallerContext, ProjectScope, Services, ToolRequest


@pytest.fixture
def reference_project(isolated_data_root):
    pm = get_project_manager()
    pm.create_project("demo", content_mode="drama")
    pm.create_project_metadata("demo", "O café", content_mode="drama")
    pm.add_project_character("demo", "Ana", "A fictional person")
    pm.update_project("demo", lambda p: p.update({"source_language": "pt-BR"}))
    return pm


def image_bytes(color):
    data = BytesIO()
    Image.new("RGB", (16, 16), color).save(data, format="PNG")
    return data.getvalue()


async def upload(pm, content, *, name="Ana"):
    return await upload_reference(
        ToolRequest(
            UploadReferenceRequest(
                kind="character_image",
                name=name,
                filename="reference.png",
                content_base64=base64.b64encode(content).decode(),
            )
        ),
        ProjectScope("demo", pm.data_root),
        CallerContext("test", "mcp"),
        Services.defaults(pm),
    )


def assert_no_transaction_debris(path):
    assert not [p for p in path.rglob("*") if p.is_file() and p.suffix in {".tmp", ".bak"}]


async def test_native_deletion_after_mcp_precheck_refuses_without_orphan(reference_project):
    pm = reference_project
    entered, release = threading.Event(), threading.Event()

    class PausedPrecheck(ProjectManager):
        def load_project(self, project_name):
            snapshot = super().load_project(project_name)
            if not entered.is_set():
                entered.set()
                assert release.wait(5), "Precheck was not released"
            return snapshot

    task = asyncio.create_task(upload(PausedPrecheck(pm.data_root), image_bytes("blue")))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        await asyncio.to_thread(pm.delete_asset, "demo", "characters", "Ana")
        release.set()
        result = await task
        assert result.problem is not None
        assert result.problem.code == "reference_upload_failed"
        assert "Ana" not in pm.load_project("demo")["characters"]
        assert not (pm.get_project_path("demo") / "characters/refs/Ana.png").exists()
        assert_no_transaction_debris(pm.get_project_path("demo"))
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_successful_replacement_keeps_native_metadata_and_ptbr(reference_project):
    pm = reference_project
    first = await upload(pm, image_bytes("blue"))
    assert first.problem is None
    old_path = first.value["path"]
    second = await upload(pm, image_bytes("red"))
    assert second.problem is None
    assert second.value["path"] == old_path
    project = pm.load_project("demo")
    assert project["characters"]["Ana"]["reference_image"] == old_path
    assert project["source_language"] == "pt-BR"
    assert not project["characters"]["Ana"].get("character_sheet")
    assert (pm.get_project_path("demo") / old_path).read_bytes() == image_bytes("red")
    assert_no_transaction_debris(pm.get_project_path("demo"))


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure_stage", ["staging", "install", "metadata"])
async def test_upload_filesystem_failure_rolls_back_bytes_and_pointer(
    reference_project, monkeypatch, existing, failure_stage
):
    pm = reference_project
    if existing:
        result = await upload(pm, image_bytes("blue"))
        assert result.problem is None
    path = pm.get_project_path("demo")
    target = path / "characters/refs/Ana.png"
    project_file = path / "project.json"
    before = project_file.read_bytes(), target.read_bytes() if target.exists() else None
    real_replace = os.replace
    failed = False

    def fail_once(source, destination, *args, **kwargs):
        nonlocal failed
        destination = Path(destination)
        selected = (
            (failure_stage == "staging" and destination.parent == target.parent and destination.suffix == ".tmp")
            or (failure_stage == "install" and destination == target)
            or (failure_stage == "metadata" and destination == project_file)
        )
        if selected and not failed:
            failed = True
            raise OSError("Simulated filesystem write failure")
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "replace", fail_once)
    result = await upload(pm, image_bytes("red"))
    assert failed
    assert result.problem is not None
    assert project_file.read_bytes() == before[0]
    assert (target.read_bytes() if target.exists() else None) == before[1]
    assert_no_transaction_debris(path)


async def test_two_same_target_uploads_finish_with_one_coherent_reference(reference_project):
    pm = reference_project
    contents = [image_bytes("blue"), image_bytes("red")]
    results = await asyncio.gather(*(upload(pm, content) for content in contents))
    assert all(result.problem is None for result in results)
    assert results[0].value["path"] == results[1].value["path"]
    project = pm.load_project("demo")
    relative = project["characters"]["Ana"]["reference_image"]
    assert (pm.get_project_path("demo") / relative).read_bytes() in contents
    assert project["source_language"] == "pt-BR"
    assert_no_transaction_debris(pm.get_project_path("demo"))


async def test_cancelled_upload_waits_for_native_commit(reference_project, monkeypatch):
    pm = reference_project
    project_file = pm.get_project_path("demo") / "project.json"
    entered, release = threading.Event(), threading.Event()
    real_replace = os.replace

    def paused_commit(source, destination, *args, **kwargs):
        if Path(destination) == project_file:
            entered.set()
            assert release.wait(5), "Commit was not released"
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "replace", paused_commit)
    content = image_bytes("red")
    task = asyncio.create_task(upload(pm, content))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        project = pm.load_project("demo")
        relative = project["characters"]["Ana"]["reference_image"]
        assert (pm.get_project_path("demo") / relative).read_bytes() == content
        assert_no_transaction_debris(pm.get_project_path("demo"))
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_web_reference_upload_keeps_missing_host_semantics(reference_project):
    pm = reference_project
    file = UploadFile(file=BytesIO(image_bytes("blue")), filename="reference.png")
    try:
        result = await upload_project_file(
            project_name="demo",
            upload_type="character_ref",
            _t=_,
            file=file,
            name="Missing",
            manager=pm,
            change_source="webui",
        )
    finally:
        await file.close()
    assert result["success"] is True
    assert "Missing" not in pm.load_project("demo")["characters"]
    assert (pm.get_project_path("demo") / result["path"]).is_file()


async def test_committed_upload_can_be_deleted_by_native_transaction(reference_project):
    pm = reference_project
    uploaded = await upload(pm, image_bytes("blue"))
    assert uploaded.problem is None
    project = pm.load_project("demo")
    assert project["characters"]["Ana"]["reference_image"] == uploaded.value["path"]
    assert (pm.get_project_path("demo") / uploaded.value["path"]).is_file()
    await asyncio.to_thread(pm.delete_asset, "demo", "characters", "Ana")
    assert "Ana" not in pm.load_project("demo")["characters"]
    assert_no_transaction_debris(pm.get_project_path("demo"))


async def test_image_commit_resolves_unicode_host_without_renaming_it(reference_project):
    pm = reference_project
    decomposed = "Cafe\u0301"
    pm.update_project("demo", lambda p: p["characters"].update({decomposed: {"description": "A fictional person"}}))
    result = await upload(pm, image_bytes("blue"), name="Café")
    assert result.problem is None
    characters = pm.load_project("demo")["characters"]
    assert "Café" not in characters
    assert characters[decomposed]["reference_image"] == result.value["path"]
    assert (pm.get_project_path("demo") / result.value["path"]).read_bytes() == image_bytes("blue")


async def test_failed_upload_cannot_remove_a_concurrent_success(reference_project, monkeypatch):
    pm = reference_project
    initial = await upload(pm, image_bytes("blue"))
    assert initial.problem is None
    project_file = pm.get_project_path("demo") / "project.json"
    entered, release = threading.Event(), threading.Event()
    real_replace = os.replace

    def fail_first_commit(source, destination, *args, **kwargs):
        if Path(destination) == project_file and not entered.is_set():
            entered.set()
            assert release.wait(5), "Commit was not released"
            raise OSError("Simulated first upload commit failure")
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "replace", fail_first_commit)
    first = asyncio.create_task(upload(pm, image_bytes("red")))
    second = None
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        second = asyncio.create_task(upload(pm, image_bytes("green")))
        await asyncio.sleep(0)
        release.set()
        refused, accepted = await asyncio.gather(first, second)
        assert refused.problem is not None
        assert accepted.problem is None
        project = pm.load_project("demo")
        relative = project["characters"]["Ana"]["reference_image"]
        assert relative == accepted.value["path"]
        assert (pm.get_project_path("demo") / relative).read_bytes() == image_bytes("green")
        assert_no_transaction_debris(pm.get_project_path("demo"))
    finally:
        release.set()
        await asyncio.gather(*([first, second] if second is not None else [first]), return_exceptions=True)
