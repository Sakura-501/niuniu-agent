from niuniu_agent.config import AgentMode, AgentSettings


def test_settings_load_debug_defaults(monkeypatch) -> None:
    monkeypatch.setenv("NIUNIU_AGENT_MODE", "debug")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL", "ep-jsc7o0kw")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_HOST", "10.0.0.44:8000")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_TOKEN", "token")

    settings = AgentSettings()

    assert settings.mode is AgentMode.DEBUG
    assert settings.poll_interval_seconds == 15
    assert settings.contest_mcp_url == "http://10.0.0.44:8000/mcp"


def test_settings_load_competition_defaults(monkeypatch) -> None:
    monkeypatch.setenv("NIUNIU_AGENT_MODE", "competition")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL", "ep-jsc7o0kw")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_HOST", "10.0.0.44:8000")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_TOKEN", "token")

    settings = AgentSettings()

    assert settings.mode is AgentMode.COMPETITION
    assert settings.poll_interval_seconds == 30
