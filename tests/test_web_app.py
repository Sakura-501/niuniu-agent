from __future__ import annotations

from fastapi.testclient import TestClient

from niuniu_agent.web.app import create_app


class FakeWebService:
    async def overview(self) -> dict[str, object]:
        return {
            "process": {"competition": {"running": False}, "ui": {"running": True}},
            "contest": {"current_level": 1, "total_challenges": 2, "solved_challenges": 1, "challenges": []},
            "agents": [{"agent_id": "manager:competition", "status": "running", "role": "manager"}],
        }

    async def challenge_detail(self, code: str) -> dict[str, object]:
        return {"code": code, "history": [], "notes": {}, "events": []}

    async def agent_detail(self, agent_id: str) -> dict[str, object]:
        return {"agent_id": agent_id, "events": []}

    async def create_debug_session(self) -> dict[str, object]:
        return {"session_id": "session-1"}

    async def stream_debug_reply(self, session_id: str, message: str):
        yield "event: message\ndata: hello\n\n"

    async def start_competition(self) -> dict[str, object]:
        return {"ok": True}

    async def stop_competition(self) -> dict[str, object]:
        return {"ok": True}

    async def restart_competition(self) -> dict[str, object]:
        return {"ok": True}


def test_web_dashboard_renders() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.get("/")

    assert response.status_code == 200
    assert "Agent Console" in response.text
    assert "8081" in response.text


def test_web_overview_endpoint_returns_json() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.get("/api/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["process"]["ui"]["running"] is True
    assert payload["agents"][0]["agent_id"] == "manager:competition"
