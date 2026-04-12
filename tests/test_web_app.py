from __future__ import annotations

from fastapi.testclient import TestClient

from niuniu_agent.web.app import create_app


class FakeWebService:
    async def overview(self) -> dict[str, object]:
        return {
            "process": {"competition": {"running": False, "run_id": "run1"}, "ui": {"running": True}},
            "model_routing": {
                "selected_provider_id": "official",
                "selected_model": "ep-jsc7o0kw",
                "providers": [
                    {"provider_id": "official", "display_name": "官方提供", "base_url": "http://10.0.0.24/70_f8g1qfuu/v1", "model": "ep-jsc7o0kw"},
                    {"provider_id": "rightcodes", "display_name": "rightcodes供应商", "base_url": "http://10.0.0.24/70_tsdb3cwf/codex/v1", "model": "gpt-5.4-xhigh"},
                ],
            },
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
                        "scheduler_status": "dispatchable",
                        "scheduler_reason": "unsolved challenge with no assigned worker",
                        "notes": {},
                    }
                ],
            },
            "agents": [{"agent_id": "manager:competition:run1", "status": "running", "role": "manager"}],
            "agent_tree": [
                {
                    "manager": {"agent_id": "manager:competition:run1", "status": "running", "role": "manager", "summary": "active=1 dispatchable=2 paused=1"},
                    "workers": [{"agent_id": "worker:c1:abcd", "status": "running", "role": "challenge_worker"}],
                }
            ],
        }

    async def challenge_detail(self, code: str) -> dict[str, object]:
        return {
            "code": code,
            "availability": "official+local",
            "official": {"code": code, "hint_viewed": True, "instance_status": "running"},
            "local": {"runtime_state": {}, "notes": {}, "history": [], "agent_statuses": [], "events": []},
        }

    async def agent_detail(self, agent_id: str) -> dict[str, object]:
        role = "manager" if agent_id.startswith("manager:") else "debug"
        return {"agent_id": agent_id, "status": {"agent_id": agent_id, "role": role}, "events": []}

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

    async def get_model_routing(self) -> dict[str, object]:
        return (await self.overview())["model_routing"]

    async def select_model_routing(self, provider_id: str, model_override: str | None) -> dict[str, object]:
        return {"ok": True, "selected_provider_id": provider_id, "selected_model": model_override or provider_id}

    async def reset_model_routing(self) -> dict[str, object]:
        return {"ok": True, "selected_provider_id": "official", "selected_model": "ep-jsc7o0kw"}


def test_web_dashboard_renders() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.get("/")

    assert response.status_code == 200
    assert "Agent Console" in response.text
    assert "8081" in response.text
    assert "defaultModel" in response.text


def test_web_overview_endpoint_returns_json() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.get("/api/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["process"]["ui"]["running"] is True
    assert payload["agents"][0]["agent_id"] == "manager:competition:run1"
    assert payload["contest"]["challenges"][0]["hint_viewed"] is True
    assert payload["contest"]["challenges"][0]["scheduler_status"] == "dispatchable"


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


def test_web_manager_delete_endpoint() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.delete("/api/agents/manager:competition:run1")

    assert response.status_code == 200
    assert response.json()["action"] == "delete"


def test_web_legacy_manager_delete_endpoint() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.delete("/api/agents/manager:competition")

    assert response.status_code == 200
    assert response.json()["action"] == "delete"


def test_web_start_competition_returns_seeded_agent_status() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    response = client.post("/api/competition/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["agents_seeded"][0]["agent_id"] == "manager:competition:run1"


def test_web_model_routing_endpoints() -> None:
    client = TestClient(create_app(service=FakeWebService()))

    get_response = client.get("/api/model-routing")
    select_response = client.post(
        "/api/model-routing/select",
        json={"provider_id": "rightcodes", "model_override": "gpt-5.4-xhigh"},
    )
    reset_response = client.post("/api/model-routing/reset")

    assert get_response.status_code == 200
    assert get_response.json()["selected_provider_id"] == "official"
    assert select_response.status_code == 200
    assert select_response.json()["selected_provider_id"] == "rightcodes"
    assert reset_response.status_code == 200
