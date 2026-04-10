import json

from niuniu_agent.telemetry import EventLogger


def test_telemetry_writes_jsonl(tmp_path) -> None:
    logger = EventLogger(tmp_path / "events.jsonl")

    logger.log("challenge.started", {"code": "challenge-1", "mode": "debug"})

    payload = json.loads((tmp_path / "events.jsonl").read_text().strip())
    assert payload["event"] == "challenge.started"
    assert payload["code"] == "challenge-1"
    assert payload["mode"] == "debug"
    assert "timestamp" in payload
