"""Upload staging limits: per-purpose native ceilings, per-client and per-project quotas, and immutability once verified."""

from __future__ import annotations

import hashlib

import pytest

from lib.project.project_manager import ProjectManager
from server.services.media_transport import uploads
from server.services.media_transport.errors import MediaTransportError

_CLIENT = "apikey:test"


async def _begin(projects: ProjectManager, size: int, *, purpose: str = "unit_video", client: str = _CLIENT):
    return await uploads.begin_upload(
        projects,
        "demo",
        filename="clip.mp4",
        size_bytes=size,
        sha256="0" * 64,
        purpose=purpose,
        client_id=client,
    )


async def _code(awaitable) -> str:
    with pytest.raises(MediaTransportError) as caught:
        await awaitable
    return caught.value.code


async def test_purpose_caps_size_at_the_native_limit(timeline_project: ProjectManager) -> None:
    image_limit = uploads.UPLOAD_PURPOSE_LIMITS["asset_image"]

    assert await _code(_begin(timeline_project, image_limit + 1, purpose="asset_image")) == "upload_too_large"
    assert await _code(_begin(timeline_project, 10, purpose="anything")) == "upload_chunk_invalid"
    assert (await _begin(timeline_project, image_limit, purpose="asset_image")).size_bytes == image_limit


async def test_active_upload_and_staged_byte_quotas(
    timeline_project: ProjectManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    for _ in range(uploads.MAX_ACTIVE_UPLOADS_PER_CLIENT):
        await _begin(timeline_project, 10)
    per_client = await _code(_begin(timeline_project, 10))
    other_client = await _begin(timeline_project, 10, client="apikey:other")

    monkeypatch.setattr(uploads, "MAX_STAGED_BYTES_PER_PROJECT", 60)
    total_bytes = await _code(_begin(timeline_project, 25, client="apikey:third"))

    assert per_client == "upload_quota_exceeded"
    assert other_client.upload_id
    assert total_bytes == "upload_quota_exceeded"


async def test_verified_upload_refuses_further_appends(timeline_project: ProjectManager) -> None:
    content = b"final bytes"
    began = await uploads.begin_upload(
        timeline_project,
        "demo",
        filename="clip.mp4",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        purpose="unit_video",
        client_id=_CLIENT,
    )
    done = await uploads.append_upload_chunk(
        timeline_project, "demo", began.upload_id, index=0, content=content, client_id=_CLIENT
    )

    overwrite = await _code(
        uploads.append_upload_chunk(
            timeline_project, "demo", began.upload_id, index=0, content=b"other bytes", client_id=_CLIENT
        )
    )

    assert done.complete
    assert overwrite == "upload_already_complete"
    with await uploads.resolve_staged_upload(
        timeline_project, "demo", began.upload_id, client_id=_CLIENT, use_request_client=False
    ) as staged:
        assert staged.stream.read() == content


async def test_consumer_purposes_refuse_an_upload_staged_for_another_purpose(timeline_project: ProjectManager) -> None:
    content = b"\x89PNG grid"
    began = await uploads.begin_upload(
        timeline_project,
        "demo",
        filename="grid.png",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        purpose="grid_composite",
        client_id=_CLIENT,
    )
    await uploads.append_upload_chunk(
        timeline_project, "demo", began.upload_id, index=0, content=content, client_id=_CLIENT
    )

    mismatch = await _code(
        uploads.resolve_staged_upload(
            timeline_project,
            "demo",
            began.upload_id,
            client_id=_CLIENT,
            use_request_client=False,
            purposes=("unit_video",),
        )
    )
    with await uploads.resolve_staged_upload(
        timeline_project,
        "demo",
        began.upload_id,
        client_id=_CLIENT,
        use_request_client=False,
        purposes=("grid_composite",),
    ) as staged:
        assert staged.purpose == "grid_composite"

    assert mismatch == "upload_purpose_mismatch"
    assert uploads.UPLOAD_PURPOSE_LIMITS["grid_composite"] == 30 * 1024 * 1024


async def test_record_lock_map_does_not_grow_with_uploads(timeline_project: ProjectManager) -> None:
    from server.services.media_transport import private_store

    before = private_store.record_lock_count()
    for _ in range(3):
        content = b"x"
        began = await uploads.begin_upload(
            timeline_project,
            "demo",
            filename="a.mp4",
            size_bytes=1,
            sha256=hashlib.sha256(content).hexdigest(),
            purpose="unit_video",
            client_id=_CLIENT,
        )
        await uploads.append_upload_chunk(
            timeline_project, "demo", began.upload_id, index=0, content=content, client_id=_CLIENT
        )
        await uploads.discard_staged_upload(
            timeline_project, "demo", began.upload_id, client_id=_CLIENT, use_request_client=False
        )

    assert private_store.record_lock_count() == before
