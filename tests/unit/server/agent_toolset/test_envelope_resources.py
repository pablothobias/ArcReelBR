"""Declared binary resources reach both hosts as identical embedded blob resources, never inside JSON."""

from __future__ import annotations

import base64
import json
from typing import Any

from mcp import types
from pydantic import BaseModel, ConfigDict

from server.agent_toolset.declaration import READ_CHECK, ToolDeclaration, ToolImage, ToolResource
from server.agent_toolset.embedded import embedded_result
from server.agent_toolset.envelope import encode_outcome
from server.agent_toolset.remote import remote_result
from server.tool_runtime import ToolOutcome, ToolProblem


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


async def _handler(*_args: Any) -> ToolOutcome[bytes]:
    raise AssertionError("not called")


_DECLARATION = ToolDeclaration(
    name="blob_tool",
    description="test",
    request_model=_Request,
    migration=READ_CHECK,
    domain_key="blob",
    handler=_handler,
    projection=lambda value: {"blob": {"length": len(value)}},
    images=lambda _value: [ToolImage(data=b"\xff\xd8jpeg", mime_type="image/jpeg")],
    resources=lambda value: [ToolResource(uri="arcreel://media/demo/m/0", data=value)],
)

_PAYLOAD = bytes(range(256)) * 3


def _blocks(result: types.CallToolResult) -> list[tuple[str, Any]]:
    shaped: list[tuple[str, Any]] = []
    for block in result.content:
        if isinstance(block, types.EmbeddedResource):
            resource = block.resource
            assert isinstance(resource, types.BlobResourceContents)
            shaped.append(("resource", (str(resource.uri), resource.mimeType, base64.b64decode(resource.blob))))
        elif isinstance(block, types.ImageContent):
            shaped.append(("image", block.mimeType))
        else:
            assert isinstance(block, types.TextContent)
            shaped.append(("text", json.loads(block.text)))
    return shaped


def test_resources_follow_images_identically_on_both_hosts() -> None:
    outcome = ToolOutcome(value=_PAYLOAD)

    embedded = embedded_result(_DECLARATION, outcome)
    remote = remote_result(_DECLARATION, outcome)

    expected = [
        ("text", {"blob": {"length": len(_PAYLOAD)}}),
        ("image", "image/jpeg"),
        ("resource", ("arcreel://media/demo/m/0", "application/octet-stream", _PAYLOAD)),
    ]
    assert _blocks(embedded) == expected
    assert _blocks(remote) == expected
    assert remote.structuredContent == {"blob": {"length": len(_PAYLOAD)}}
    # The bytes never appear inside the JSON text block.
    assert base64.b64encode(_PAYLOAD).decode() not in embedded.content[0].text


def test_problems_and_undeclared_resources_carry_no_resource_blocks() -> None:
    problem = encode_outcome(_DECLARATION, ToolOutcome(problem=ToolProblem("media_missing", "gone")))
    plain = ToolDeclaration(
        name="plain",
        description="test",
        request_model=_Request,
        migration=READ_CHECK,
        domain_key="plain",
        handler=_handler,
    )

    assert problem.resources == ()
    assert encode_outcome(plain, ToolOutcome(value={"a": 1})).resources == ()
