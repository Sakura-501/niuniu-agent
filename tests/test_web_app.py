from __future__ import annotations

from fastapi.testclient import TestClient

from niuniu_agent.web.app import create_app


class FakeWebService:
    async def overview(self) -> dict[str, object]:
        return {
            "process": {"competition": {"running": False, "run_id": "run1"}, "ui": {"running": True}},
            "contest": {
                "current_level": 1,
                "total_challenges": 2,
                "solved_challenges": 1,
                "challenges": [
                    {
                        "code": "c1",
                        "title": "demo",
                        "instance_status": "running",
                        "completed": False,
                        "hint_viewed": True,
                        "notes": {},
                    }
                ],
            },
            "agents": [{"agent_id": "manager:competition:run1", "status": "running", "role": "manager"}],
        }

    async def challenge_detail(self, code: str) -> dict[str, object]:
        return {
            "code": code,
            "availability": "official+local",
            "official": {"code": code, "hint_viewed": True, "instance_status": "running"},
            "local": {"runtime_state": {}, "notes": {}, "history": [], "agent_statuses": [], "events": []},
        }

    async def agent_detail(self, agent_id: str) -> dict[str, object]:
        return {"agent_id": agent_id, "status": {"agent_id": agent_id, "role": "debug"}, "events": []}

    async def create_debug_session(self) -> dict[str, object]:
        return {"session_id": "session-1"}

    async def get_debug_session(self, session_id: str) -> dict[str, object]:
        return {
            "session_id": session_id,
            "agent_id": f"debug:{session_id}",
            "status": "idle",
            "transcript": [
                {"role": "user", "text": "hello"},
                {"role": "assistant", "text": "world"},
            ],
        }

    async def stream_debug_reply(self, session_id: str, message: str):
        yield "event: message\ndata: hello\n\n"

    async def stop_agent(self, agent_id: str) -> dict[str, object]:
        return {"ok": True, "agent_id": agent_id, "action": "stop"}

    async def pause_agent(self, agent_id: str) -> dict[str, object]:
        return {"ok": True, "agent_id": agent_id, "action": "pause"}

    async def delete_agent(self, agent_id: str) -> dict[str, object]:
        return {"ok": True, "agent_id": agent_id, "action": "delete"}

    async def start_competition(self) -> dict[str, object]:
        return {
            "ok": True,
            "agents_seeded": [
                {"agent_id": "manager:competition:run1", "role": "manager", "status": "starting"},
            ],
        }

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
    assert payload["agents"][0]["agent_id"] == "manager:competition:run1"
    assert payload["contest"]["challenges"][0]["hint_viewed"] is True


def test_web_debug_session_and_agent_action_endpoints() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    session_response = client.get("/api/debug/sessions/session-1")
    stop_response = client.post("/api/agents/debug:session-1/stop")
    delete_response = client.delete("/api/agents/debug:session-1")

    assert session_response.status_code == 200
    assert session_response.json()["transcript"][0]["role"] == "user"
    assert stop_response.status_code == 200
    assert stop_response.json()["action"] == "stop"
    assert delete_response.status_code == 200
    assert delete_response.json()["action"] == "delete"


def test_web_worker_pause_endpoint() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.post("/api/agents/worker:c1:abcd/pause")

    assert response.status_code == 200
    assert response.json()["action"] == "pause"


def test_web_start_competition_returns_seeded_agent_status() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.post("/api/competition/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["agents_seeded"][0]["agent_id"] == "manager:competition:run1"
