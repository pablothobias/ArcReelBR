from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.auth import CurrentUserInfo, get_current_user
from server.error_handlers import register_error_handlers
from server.routers import scenes
from tests.auth_deps import AUTH_DEPENDENCIES
from tests.fakes import FakeProjectAssetMutationMixin, use_project_manager


class _FakePM(FakeProjectAssetMutationMixin):
    def __init__(self):
        self.projects = {
            "demo": {
                "scenes": {
                    "Shrine": {"description": "old", "scene_sheet": ""},
                }
            }
        }

    def _add_asset(self, asset_type, project_name, name, entry):
        if project_name not in self.projects:
            raise FileNotFoundError(project_name)
        bucket = self.projects[project_name].setdefault("scenes", {})
        if name in bucket:
            return False
        bucket[name] = entry
        return True

    def load_project(self, project_name):
        if project_name not in self.projects:
            raise FileNotFoundError(project_name)
        return self.projects[project_name]

    def save_project(self, project_name, project):
        self.projects[project_name] = project

    def update_project(self, project_name, mutate_fn):
        project = self.load_project(project_name)
        mutate_fn(project)
        self.save_project(project_name, project)


def _client(monkeypatch, fake_pm):
    monkeypatch.setattr(scenes, "get_project_manager", lambda: fake_pm)
    app = FastAPI()
    register_error_handlers(app)
    app.dependency_overrides[get_current_user] = lambda: CurrentUserInfo(id="default", sub="testuser", role="admin")
    app.include_router(scenes.router, prefix="/api/v1", dependencies=AUTH_DEPENDENCIES)
    return TestClient(app)


class TestScenesRouter:
    def test_add_update_delete(self, monkeypatch):
        fake_pm = _FakePM()
        with _client(monkeypatch, fake_pm) as client:
            add_resp = client.post(
                "/api/v1/projects/demo/scenes",
                json={"name": "Glacier", "description": "Stark"},
            )
            assert add_resp.status_code == 200
            assert add_resp.json()["scene"]["description"] == "Stark"

            patch_resp = client.patch(
                "/api/v1/projects/demo/scenes/Shrine",
                json={"description": "new", "scene_sheet": "scenes/Shrine.png"},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["scene"]["scene_sheet"].endswith("Shrine.png")

            delete_resp = client.delete("/api/v1/projects/demo/scenes/Glacier")
            assert delete_resp.status_code == 200

    def test_error_mapping(self, monkeypatch):
        fake_pm = _FakePM()
        with _client(monkeypatch, fake_pm) as client:
            # Duplicate name → 409
            dup_resp = client.post(
                "/api/v1/projects/demo/scenes",
                json={"name": "Shrine", "description": ""},
            )
            assert dup_resp.status_code == 409

            # Missing scene → 404
            missing_resp = client.patch(
                "/api/v1/projects/demo/scenes/Missing",
                json={"description": "x"},
            )
            assert missing_resp.status_code == 404

            missing_del = client.delete("/api/v1/projects/demo/scenes/Missing")
            assert missing_del.status_code == 404


class TestScenesRouterDoesNotCollideWithProjects:
    """Path-template collision regression guard.

    projects.router and scenes.router register under the same ``/api/v1`` prefix and historically
    both used ``PATCH /projects/{name}/scenes/{*}``. FastAPI matches path templates in registration
    order; matching drama endpoints (required ``script_file`` / ``updates``) first
    makes SceneCard Save requests receive 422 "Field required; Field required".
    """

    def test_patch_scene_with_description_only_body_hits_asset_router(self, monkeypatch):
        from server.routers import projects as projects_router

        fake_pm = _FakePM()
        monkeypatch.setattr(scenes, "get_project_manager", lambda: fake_pm)
        use_project_manager(monkeypatch, fake_pm)

        app = FastAPI()
        register_error_handlers(app)
        app.dependency_overrides[get_current_user] = lambda: CurrentUserInfo(id="default", sub="testuser", role="admin")
        # Same order as server/app.py: include projects first.
        app.include_router(projects_router.router, prefix="/api/v1", dependencies=AUTH_DEPENDENCIES)
        app.include_router(scenes.router, prefix="/api/v1", dependencies=AUTH_DEPENDENCIES)

        with TestClient(app) as client:
            resp = client.patch(
                "/api/v1/projects/demo/scenes/Shrine",
                json={"description": "Outdoor seascape from dusk to dawn"},
            )
            assert resp.status_code == 200, resp.json()
            assert resp.json()["scene"]["description"] == "Outdoor seascape from dusk to dawn"


class TestSceneOccupancy:
    def test_create_and_patch_store_an_explicit_occupancy(self, monkeypatch):
        fake_pm = _FakePM()
        with _client(monkeypatch, fake_pm) as client:
            created = client.post(
                "/api/v1/projects/demo/scenes", json={"name": "Classroom", "description": "d", "occupancy": "occupied"}
            )
            plain = client.post("/api/v1/projects/demo/scenes", json={"name": "Snowy peak", "description": "d"})
            patched = client.patch("/api/v1/projects/demo/scenes/Shrine", json={"occupancy": "occupied"})
            reverted = client.patch("/api/v1/projects/demo/scenes/Shrine", json={"occupancy": "empty"})

        assert created.json()["scene"]["occupancy"] == "occupied"
        assert "occupancy" not in plain.json()["scene"]
        assert patched.json()["scene"]["occupancy"] == "occupied"
        assert reverted.json()["scene"]["occupancy"] == "empty"

    def test_unknown_occupancy_is_rejected_without_writing(self, monkeypatch):
        fake_pm = _FakePM()
        with _client(monkeypatch, fake_pm) as client:
            created = client.post(
                "/api/v1/projects/demo/scenes", json={"name": "Classroom", "description": "d", "occupancy": "crowded"}
            )
            patched = client.patch("/api/v1/projects/demo/scenes/Shrine", json={"occupancy": "crowded"})

        assert created.status_code == 422
        assert patched.status_code == 422
        assert "Classroom" not in fake_pm.projects["demo"]["scenes"]
        assert "occupancy" not in fake_pm.projects["demo"]["scenes"]["Shrine"]

    def test_blank_occupancy_is_accepted_as_the_default_like_the_validator(self, monkeypatch):
        fake_pm = _FakePM()
        with _client(monkeypatch, fake_pm) as client:
            patched = client.patch("/api/v1/projects/demo/scenes/Shrine", json={"occupancy": ""})

        assert patched.status_code == 200
