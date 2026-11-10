"""Shared mapping of whole-source file changes (``SourceFileChangeOutcome`` / ``SourceFileChangeError``) to HTTP responses.

Commands surface through ``episodes_view`` (the episode view’s file bar) and ``files`` (source uploads, filename-based writes
and deletion); identical results produce the same response shape."""

from collections.abc import Callable

from fastapi import HTTPException

from lib.episode.source_file_changes import SourceFileChangeError, SourceFileChangeOutcome
from server.i18n import Translator
from server.routers.episode_management import episode_has_active_tasks
from server.services.project.episode_operations import (
    EpisodeOperationRefused,
    ensure_no_displaced_source_tasks,
    source_file_change_payload,
)

_STATUS: dict[str, int] = {
    "source_file_not_found": 404,
    "source_file_unreadable": 422,
    "source_text_empty": 422,
}


def source_file_change_http_error(exc: SourceFileChangeError, _t: Translator) -> HTTPException:
    return HTTPException(status_code=_STATUS.get(exc.code, 409), detail=_t(f"source_file_change_{exc.code}"))


async def ensure_no_displaced_tasks(
    project_name: str,
    revision: str | None,
    preview: Callable[[], SourceFileChangeOutcome],
    _t: Translator,
) -> None:
    """Before executing with ``revision``, recompute affected episodes using ``preview`` (the command’s ``dry_run``).

    If the list matches the confirmed one but episodes being retired or removed still have queued/running tasks, return 409
    without writing. Do not block when ``revision`` is absent or the list changed; let the command return confirmation itself."""
    try:
        await ensure_no_displaced_source_tasks(
            revision, preview, lambda episode: episode_has_active_tasks(project_name, episode)
        )
    except EpisodeOperationRefused as exc:
        raise HTTPException(status_code=409, detail=_t(exc.code)) from exc


__all__ = ["ensure_no_displaced_tasks", "source_file_change_http_error", "source_file_change_payload"]
