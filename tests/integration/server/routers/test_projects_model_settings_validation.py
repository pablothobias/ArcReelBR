"""Web create/PATCH refuse model_settings values the executing endpoint cannot render (MCP-005), writing nothing."""

from tests.integration.server.routers.projects_router_support import (
    _FakePM,
    build_projects_client,
)

H3 = "minimax/MiniMax-H3"


def _assert_refused(resp) -> None:
    assert resp.status_code == 422
    body = resp.json()
    assert "2K" in body["detail"]
    assert "768p, 2k" in body["detail"]
    assert body["diagnostic"] == {
        "model_key": H3,
        "field": "resolution",
        "value": "2K",
        "allowed_values": ["768p", "2k"],
        "suggestion": "2k",
    }


def test_create_refuses_unrenderable_resolution_before_any_directory(tmp_path, monkeypatch):
    fake_pm = _FakePM(tmp_path)
    client = build_projects_client(monkeypatch, fake_pm)
    with client:
        resp = client.post(
            "/api/v1/projects",
            json={
                "generation_mode": "reference_video",
                "name": "demo-2k",
                "title": "T",
                "model_settings": {H3: {"resolution": "2K"}},
            },
        )
    _assert_refused(resp)
    assert "demo-2k" not in fake_pm.project_data
    assert not (tmp_path / "demo-2k").exists()


def test_patch_refuses_unrenderable_resolution_and_keeps_the_project(tmp_path, monkeypatch):
    fake_pm = _FakePM(tmp_path)
    client = build_projects_client(monkeypatch, fake_pm)
    before = dict(fake_pm.project_data["ready"])
    with client:
        resp = client.patch("/api/v1/projects/ready", json={"model_settings": {H3: {"resolution": "2K"}}})
    _assert_refused(resp)
    assert fake_pm.project_data["ready"] == before


def test_patch_accepts_the_renderable_value_and_replaces_the_map(tmp_path, monkeypatch):
    fake_pm = _FakePM(tmp_path)
    client = build_projects_client(monkeypatch, fake_pm)
    with client:
        resp = client.patch("/api/v1/projects/ready", json={"model_settings": {H3: {"resolution": "2k"}}})
    assert resp.status_code == 200
    assert fake_pm.project_data["ready"]["model_settings"] == {H3: {"resolution": "2k"}}


def test_patch_keeps_an_unchanged_stale_entry_while_saving_another_model(tmp_path, monkeypatch):
    """The settings form sends the whole map: a stored legacy value must not block an unrelated change."""
    fake_pm = _FakePM(tmp_path)
    fake_pm.project_data["ready"]["model_settings"] = {H3: {"resolution": "2K"}}
    client = build_projects_client(monkeypatch, fake_pm)
    other = "openai/sora-2"
    with client:
        resp = client.patch(
            "/api/v1/projects/ready",
            json={"model_settings": {H3: {"resolution": "2K"}, other: {"resolution": "720p"}}},
        )
        changed = client.patch("/api/v1/projects/ready", json={"model_settings": {H3: {"resolution": "4K"}}})
    assert resp.status_code == 200
    assert fake_pm.project_data["ready"]["model_settings"][H3] == {"resolution": "2K"}
    assert changed.status_code == 422
