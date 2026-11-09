"""Authenticated remote control of the existing embedded Agent service.

These tools are external-only: the embedded Agent must not recursively start
another Agent session through its production toolset.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Annotated, Any, Literal

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.tools import Tool
from pydantic import Field

from lib.project.project_manager import ProjectManager
from server.agent_runtime.models import SessionMeta
from server.agent_runtime.service import AssistantService, SessionSupersededError
from server.agent_runtime.session_manager import AgentStartupError, SessionCapacityError, UnrecordedMessageError
from server.agent_toolset.remote import authenticated_caller, resolve_project_scope

SESSION_MCP_TOOL_IDS = frozenset(
    {
        "send_agent_message",
        "get_agent_session",
        "list_agent_session_entries",
        "list_agent_questions",
        "answer_agent_question",
        "interrupt_agent_session",
        "list_agent_sessions",
        "act_on_agent_queued_message",
    }
)


class _SessionTool(Tool):
    """Do not expose runtime diagnostics or server paths through MCP errors."""

    async def run(self, arguments: dict[str, Any], context: Any = None, convert_result: bool = False) -> Any:
        try:
            result = await self.fn_metadata.call_fn_with_arg_validation(
                self.fn,
                self.is_async,
                arguments,
                {self.context_kwarg: context} if self.context_kwarg is not None else None,
            )
            return self.fn_metadata.convert_result(result) if convert_result else result
        except ToolError:
            raise
        except AgentStartupError:
            raise ToolError(
                "Embedded Agent startup failed; inspect local diagnostics and authentication before retrying"
            ) from None
        except SessionCapacityError:
            raise ToolError("Session capacity reached; reconcile active sessions before retrying") from None
        except SessionSupersededError:
            raise ToolError("Session was superseded; read its current branch before sending") from None
        except UnrecordedMessageError:
            raise ToolError(
                "Message acceptance was not recorded; reconcile the session before retrying with the same client_key"
            ) from None
        except (ValueError, FileNotFoundError):
            raise ToolError("Session operation unavailable; refresh session state and pending questions") from None
        except Exception:
            raise ToolError(
                "Session operation failed; inspect local diagnostics and reconcile state before retrying"
            ) from None


def default_session_service() -> AssistantService:
    """Resolve the running application's service without creating a second harness."""
    from server.routers.assistant import get_assistant_service

    return get_assistant_service()


def session_tools(
    *,
    projects: ProjectManager,
    service_factory: Callable[[], AssistantService] = default_session_service,
    authenticate: Callable[[], object] = authenticated_caller,
) -> list[Tool]:
    async def locate(project: str, session_id: str | None = None) -> tuple[AssistantService, str, SessionMeta | None]:
        authenticate()
        try:
            scope = await asyncio.to_thread(resolve_project_scope, project, projects)
        except (FileNotFoundError, ValueError) as exc:
            raise ToolError("Invalid or unavailable project") from exc
        service = service_factory()
        if service.pm.data_root != projects.data_root:
            raise ToolError("Session service and MCP project roots differ")
        meta = None
        if session_id is not None:
            meta = await service.get_session(session_id)
            if meta is None or meta.project_name != scope.project_name:
                raise ToolError("Session not found in this project")
        return service, scope.project_name, meta

    async def send_agent_message(
        project: str,
        content: Annotated[str, Field(min_length=1)],
        client_key: Annotated[str, Field(min_length=1, max_length=128)],
        session_id: str | None = None,
        locale: Literal["en", "zh", "vi", "ru"] = "en",
    ) -> dict[str, Any]:
        """Delegate text to the existing embedded Agent, creating a session when session_id is omitted.

        Persist client_key before sending and reuse it unchanged on transport retries.
        Returns the service's authoritative accepted entry or queued_message. Queued
        work is not accepted work. Poll get_agent_session and cursor-based entries;
        a turn result or silence does not establish session or production completion.
        Production still uses existing confirmation parameters and generation-batch polling.
        """
        service, project_name, _ = await locate(project, session_id)
        return await service.send_or_create(
            project_name, content, session_id=session_id, locale=locale, client_key=client_key
        )

    async def get_agent_session(project: str, session_id: str) -> dict[str, Any]:
        """Read actual session metadata, queued messages and pending questions.

        Poll after a turn result; idle is the current runtime state, not proof that
        production is complete. Unsent queued messages require explicit recovery.
        """
        service, _, meta = await locate(project, session_id)
        assert meta is not None
        return {
            "session": meta.model_dump(mode="json"),
            "queued_messages": service.session_manager.get_queued_messages_snapshot(session_id),
            "pending_questions": await service.session_manager.get_pending_questions_snapshot(session_id),
        }

    async def list_agent_session_entries(
        project: str, session_id: str, after_seq: Annotated[int, Field(ge=-1)] = -1
    ) -> dict[str, Any]:
        """Read authoritative entries strictly after after_seq, plus current status and streaming draft.

        Store next_after_seq after processing entries and reuse it on reconnect.
        Empty results preserve the cursor; result entries only describe turn endings.
        """
        service, _, meta = await locate(project, session_id)
        result = await service.list_session_entries(session_id, meta=meta, after_seq=after_seq)
        return {
            **result,
            "next_after_seq": max([after_seq, *(entry["seq"] for entry in result["entries"])]),
        }

    async def list_agent_questions(project: str, session_id: str) -> dict[str, Any]:
        """Read unresolved AskUserQuestion cards, including after MCP reconnection."""
        service, _, _ = await locate(project, session_id)
        return {
            "session_id": session_id,
            "questions": await service.session_manager.get_pending_questions_snapshot(session_id),
        }

    async def answer_agent_question(
        project: str, session_id: str, question_id: str, answers: Annotated[dict[str, str], Field(min_length=1)]
    ) -> dict[str, Any]:
        """Answer an existing question using its original question_id and answer keys.

        Re-read pending questions after a lost response before attempting another answer.
        """
        service, _, meta = await locate(project, session_id)
        return await service.answer_user_question(session_id, question_id, answers, meta=meta)

    async def interrupt_agent_session(project: str, session_id: str) -> dict[str, Any]:
        """Request interruption through the existing SessionActor; reconcile state afterwards.

        Interruption does not cancel already submitted media calls or establish settlement.
        """
        service, _, meta = await locate(project, session_id)
        return await service.interrupt_session(session_id, meta=meta)

    async def list_agent_sessions(
        project: str,
        status: Literal["idle", "running", "completed", "error", "interrupted", "closed"] | None = None,
        limit: Annotated[int, Field(ge=1, le=200)] = 50,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict[str, Any]:
        """Rediscover existing project sessions before starting or resending work. Read-only."""
        service, project_name, _ = await locate(project)
        sessions = await service.list_sessions(project_name=project_name, status=status, limit=limit, offset=offset)
        return {"sessions": [session.model_dump(mode="json") for session in sessions]}

    async def act_on_agent_queued_message(
        project: str,
        session_id: str,
        message_id: str,
        action: Literal["edit", "delete", "resend", "send_now"],
        locale: Literal["en", "zh", "vi", "ru"] = "en",
    ) -> dict[str, Any]:
        """Recover an existing queued message through the native session actor.

        edit withdraws it and returns its text; delete withdraws and discards it.
        resend retries an unsent message; send_now interrupts the active turn to prioritize it.
        Re-read the queue after uncertain results; accepted messages must not be submitted again.
        """
        service, project_name, _ = await locate(project, session_id)
        if action == "edit" or action == "delete":
            return await service.withdraw_queued_message(project_name, session_id, message_id, intent=action)
        if action == "resend":
            return await service.resend_queued_message(project_name, session_id, message_id, locale=locale)
        return await service.send_queued_message_now(project_name, session_id, message_id)

    return [
        _SessionTool.from_function(function)
        for function in (
            send_agent_message,
            get_agent_session,
            list_agent_session_entries,
            list_agent_questions,
            answer_agent_question,
            interrupt_agent_session,
            list_agent_sessions,
            act_on_agent_queued_message,
        )
    ]
