"""The local policy CLI durably reserves intention before any external dispatch."""

import json
import subprocess
import sys
from pathlib import Path

_POLICY = Path(__file__).resolve().parents[3] / ".agents/skills/direct-brazilian-production/scripts/policy.py"


def test_cli_reserves_then_reconciles_interrupted_work_without_duplicate_intent(tmp_path):
    record = tmp_path / "recovery.json"
    data = tmp_path / "input.json"
    record.write_text(
        json.dumps(
            {
                "approval": {
                    "round": "sample-9",
                    "currency": "USD",
                    "round_limit": "5",
                    "per_video": {"sample": "5"},
                    "user_evidence_ref": "chat:approved",
                    "quote_refs": ["quote:1"],
                },
                "intents": [],
            }
        )
    )
    candidate = {
        "intent_id": "one",
        "client_key": "stable-one",
        "kind": "initial",
        "video_id": "sample",
        "segment_id": "E1U01",
        "quote_ref": "quote:1",
        "currency": "USD",
        "maximum": "4",
    }

    def command(name, payload):
        data.write_text(json.dumps(payload))
        result = subprocess.run(
            [sys.executable, str(_POLICY), name, "--record", str(record), "--input", str(data)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, json.loads(result.stdout)

    status, result = command("reserve", candidate)
    assert status == 0
    assert result["decision"] == "reserve_before_delegating"
    assert json.loads(record.read_text())["intents"][0]["status"] == "pending"
    status, result = command("reserve", candidate)
    assert status == 0
    assert result["decision"] == "reconcile_existing"
    assert len(json.loads(record.read_text())["intents"]) == 1
    status, result = command(
        "reconcile",
        {
            "intent_id": "one",
            "status": "complete",
            "job_ref": "task:existing",
            "state_evidence_ref": "queried:current",
            "currency": "USD",
            "usage_ref": "usage:1",
            "settled_amount": "4",
        },
    )
    assert status == 0
    status, result = command("reserve", candidate)
    assert result["decision"] == "reuse_complete"
    assert len(json.loads(record.read_text())["intents"]) == 1
    before = record.read_bytes()
    status, result = command(
        "reserve", {**candidate, "intent_id": "two", "client_key": "stable-two", "segment_id": "E1U02"}
    )
    assert status == 2
    assert result["decision"] == "pause"
    assert record.read_bytes() == before
