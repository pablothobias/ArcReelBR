"""Generation diagnostics declaration: sanitized provider verdicts and recovery guidance without UI or REST."""

from __future__ import annotations

from server.agent_toolset.declaration import Exempt, ToolDeclaration
from server.media_tools.generation_diagnostics import GenerationDiagnosticsRequest, get_generation_diagnostics

GET_GENERATION_DIAGNOSTICS = ToolDeclaration(
    name="get_generation_diagnostics",
    description=(
        "Diagnose one generation task or usage record of this project by task_id or record_id: queue status, stage, "
        "provider submission checkpoint (provider_job_id), the provider's own error code and message, timestamps, "
        "the closed recovery action, and explicit truncation flags. Optionally includes the last recorded provider "
        "response, sanitized (credentials, signed URL queries and media payloads removed). Reads persisted records only: "
        "it never polls the provider, enqueues, or charges anything. Observation time of the last provider response is "
        "reported as unknown when not persisted. Returns generation_diagnostics_not_found for IDs outside this project."
    ),
    request_model=GenerationDiagnosticsRequest,
    migration=Exempt(
        "Read-only task and accounting diagnostics; failures from before a migration failure must stay explainable."
    ),
    domain_key="generation_diagnostics",
    handler=get_generation_diagnostics,
)

GENERATION_DIAGNOSTICS_TOOLS = (GET_GENERATION_DIAGNOSTICS,)

__all__ = ["GENERATION_DIAGNOSTICS_TOOLS", "GET_GENERATION_DIAGNOSTICS"]
