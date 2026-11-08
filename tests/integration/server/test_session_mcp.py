"""Session MCP contracts with the real service, replacing only the SDK process boundary."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from lib import PROJECT_ROOT
from server.agent_runtime.event_log import EventLogService, EventLogStore
from server.agent_runtime.service import AssistantService
from server.agent_runtime.session_store import SessionMetaStore
from server.remote_mcp import ArcApiKeyVerifier, build_remote_mcp_server, mount_remote_mcp
from tests.fakes import FakeSDKClient, system_frame


@pytest.fixture
async def session_bridge(isolated_data_root, file_db_factory, monkeypatch):
    service = AssistantService(PROJECT_ROOT)
    service.meta_store = SessionMetaStore(session_factory=file_db_factory)
    service.event_log_store = EventLogStore(session_factory=file_db_factory)
    service.session_manager.meta_store = service.meta_store
    service.session_manager.event_log_store = service.event_log_store
    service.event_log = EventLogService(service.event_log_store, service.transcript_adapter)
    projects = service.pm
    await asyncio.to_thread(projects.create_project, "demo", content_mode="drama")
    await asyncio.to_thread(projects.create_project, "other", content_mode="drama")
    client = FakeSDKClient(frames=[system_frame("init", session_id="session-mcp-demo")])
    monkeypatch.setattr("server.agent_runtime.session_manager.ClaudeSDKClient", lambda options: client)

    async def verify(token):
        return {"sub": "apikey:test"} if token == "arc-session-test" else None

    server = build_remote_mcp_server(
        projects=projects,
        session_service_factory=lambda: service,
        token_verifier=ArcApiKeyVerifier(verify),
    )
    app = FastAPI()
    mount_remote_mcp(app, server.streamable_http_app())
    try:
        yield service, client, app, server
    finally:
        client.close_stream()
        await service.shutdown()


@asynccontextmanager
async def connect(app):
    async with (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost",
            headers={"Authorization": "Bearer arc-session-test"},
        ) as client,
        streamable_http_client("http://localhost/mcp", http_client=client) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session


async def test_session_bridge_send_retry_reconnect_questions_cursor_and_interrupt(session_bridge):
    service, sdk, app, server = session_bridge
    async with server.session_manager.run():
        request = {
            "project": "demo",
            "content": "Inspect this project without generating media.",
            "client_key": "first",
        }
        async with connect(app) as session:
            result = await session.call_tool("send_agent_message", request)
            assert not result.isError, result
            accepted = result.structuredContent
            assert accepted["entry"]["type"] == "user"
            assert accepted["queued_message"] is None
            session_id = accepted["session_id"]
            retry = await session.call_tool("send_agent_message", request)
            assert retry.structuredContent == accepted
            state = await session.call_tool("get_agent_session", {"project": "demo", "session_id": session_id})
            assert state.structuredContent["session"]["status"] == "running"
            pending = service.session_manager.sessions[session_id].add_pending_question(
                {"question_id": "question-1", "questions": [{"question": "Continue?", "options": [{"label": "Yes"}]}]}
            )
            entries = await session.call_tool(
                "list_agent_session_entries", {"project": "demo", "session_id": session_id}
            )
            assert entries.structuredContent["entries"] == [accepted["entry"]]
            cursor = entries.structuredContent["next_after_seq"]

        async with connect(app) as session:
            args = {"project": "demo", "session_id": session_id}
            questions = await session.call_tool("list_agent_questions", args)
            assert questions.structuredContent["questions"][0]["question_id"] == "question-1"
            answer = await session.call_tool(
                "answer_agent_question", {**args, "question_id": "question-1", "answers": {"Continue?": "Yes"}}
            )
            assert answer.structuredContent["status"] == "accepted"
            assert await pending.answer_future == {"Continue?": "Yes"}
            questions = await session.call_tool("list_agent_questions", args)
            assert questions.structuredContent["questions"] == []
            stale_answer = await session.call_tool(
                "answer_agent_question", {**args, "question_id": "question-1", "answers": {"Continue?": "Yes"}}
            )
            assert stale_answer.isError
            assert "refresh session state and pending questions" in stale_answer.content[0].text
            resumed = await session.call_tool("list_agent_session_entries", {**args, "after_seq": cursor})
            assert resumed.structuredContent["entries"] == []
            assert resumed.structuredContent["next_after_seq"] == cursor
            queued = await session.call_tool(
                "send_agent_message", {**args, "content": "Wait for review.", "client_key": "second"}
            )
            assert queued.structuredContent["entry"] is None
            assert queued.structuredContent["queued_message"]["state"] == "queued"
            queued_retry = await session.call_tool(
                "send_agent_message", {**args, "content": "Wait for review.", "client_key": "second"}
            )
            assert queued_retry.structuredContent == queued.structuredContent
            snapshot = await session.call_tool("get_agent_session", args)
            assert snapshot.structuredContent["queued_messages"] == [queued.structuredContent["queued_message"]]
            interrupted = await session.call_tool("interrupt_agent_session", args)
            assert interrupted.structuredContent["status"] == "accepted"
            assert sdk.interrupted
        assert len(sdk.sent_messages) == 2


@pytest.mark.parametrize(
    ("name", "extra"),
    [
        ("get_agent_session", {}),
        ("list_agent_session_entries", {}),
        ("list_agent_questions", {}),
        ("answer_agent_question", {"question_id": "q", "answers": {"x": "y"}}),
        ("interrupt_agent_session", {}),
        ("send_agent_message", {"content": "Do not execute.", "client_key": "cross-project"}),
    ],
)
async def test_session_bridge_rejects_cross_project_ownership(session_bridge, name, extra):
    service, sdk, app, server = session_bridge
    async with server.session_manager.run():
        await service.meta_store.create("other", "other-session")
        async with connect(app) as session:
            result = await session.call_tool(name, {"project": "demo", "session_id": "other-session", **extra})
        assert result.isError
        assert "Session not found in this project" in result.content[0].text
        assert sdk.sent_messages == []


async def test_session_bridge_requires_retry_key_before_submitting(session_bridge):
    _, sdk, app, server = session_bridge
    async with server.session_manager.run(), connect(app) as session:
        result = await session.call_tool("send_agent_message", {"project": "demo", "content": "Inspect only."})
    assert result.isError
    assert sdk.sent_messages == []
