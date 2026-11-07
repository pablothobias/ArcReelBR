import pytest

from scripts.project_status_sync import derive_status


@pytest.mark.parametrize(
    ("state", "labels", "has_assignee", "has_open_closing_pr", "expected"),
    [
        # Spec / parked clears Status, ahead of all other signals.
        ("OPEN", {"Spec", "ready-for-agent"}, True, True, None),
        ("CLOSED", {"parked"}, False, False, None),
        # closed → Done, ahead of open PRs and assignees.
        ("CLOSED", {"needs-triage"}, True, True, "Done"),
        # Open closing PR → In review, ahead of assignees and ready labels.
        ("OPEN", {"ready-for-agent"}, True, True, "In review"),
        # assignee → In progress, ahead of ready / needs-info labels.
        ("OPEN", {"ready-for-human", "needs-info"}, True, False, "In progress"),
        # ready-for-agent precedes ready-for-human, which precedes needs-info.
        ("OPEN", {"ready-for-agent", "ready-for-human"}, False, False, "Ready · agent"),
        ("OPEN", {"ready-for-human", "needs-info"}, False, False, "Ready · human"),
        ("OPEN", {"needs-info", "needs-triage"}, False, False, "Needs info"),
        # needs-triage and unlabeled issues both fall back to Inbox.
        ("OPEN", {"needs-triage"}, False, False, "Inbox"),
        ("OPEN", set(), False, False, "Inbox"),
    ],
)
def test_derive_status_priority(state, labels, has_assignee, has_open_closing_pr, expected):
    assert derive_status(state, labels, has_assignee, has_open_closing_pr) == expected


def test_project_sync_requires_explicit_board_before_network(monkeypatch):
    from scripts import project_status_sync as sync

    for key in ("PROJECT_STATUS_PROJECT_ID", "PROJECT_STATUS_FIELD_ID", "PROJECT_STATUS_OPTIONS"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="Configure PROJECT_STATUS"):
        sync.load_project_config()


def test_project_sync_uses_configured_node_for_personal_board(monkeypatch):
    import io
    import json

    from scripts import project_status_sync as sync

    monkeypatch.setenv("GITHUB_REPOSITORY", "pablothobias/ArcReelBR")
    monkeypatch.setenv("PROJECT_STATUS_PROJECT_ID", "PVT_personal")
    monkeypatch.setenv("PROJECT_STATUS_FIELD_ID", "FIELD_personal")
    monkeypatch.setenv("PROJECT_STATUS_OPTIONS", json.dumps(dict.fromkeys(sync.REQUIRED_STATUSES, "option_1")))
    monkeypatch.setenv("GH_TOKEN", "test-token")
    requests = []

    def respond(request, *, timeout):
        payload = json.loads(request.data)
        requests.append(payload)
        empty_page = {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        if "projectId" in payload["variables"]:
            data = {"node": {"items": empty_page}}
        else:
            data = {"repository": {"issues": empty_page}}
        return io.BytesIO(json.dumps({"data": data}).encode())

    monkeypatch.setattr(sync.urllib.request, "urlopen", respond)
    sync.load_project_config()
    sync.sync_all()

    assert requests[0]["variables"] == {"projectId": "PVT_personal", "cursor": None}
    assert "node(id: $projectId)" in requests[0]["query"]
    assert "organization(" not in requests[0]["query"]
    assert requests[1]["variables"]["owner"] == "pablothobias"
    assert requests[1]["variables"]["repo"] == "ArcReelBR"
    assert all("mutation" not in request["query"] for request in requests)


def test_project_sync_rejects_ids_that_could_modify_graphql(monkeypatch):
    import json

    from scripts import project_status_sync as sync

    monkeypatch.setenv("PROJECT_STATUS_PROJECT_ID", 'PVT_"bad')
    monkeypatch.setenv("PROJECT_STATUS_FIELD_ID", "FIELD_personal")
    monkeypatch.setenv("PROJECT_STATUS_OPTIONS", json.dumps(dict.fromkeys(sync.REQUIRED_STATUSES, "option_1")))
    with pytest.raises(ValueError, match="ASCII"):
        sync.load_project_config()
