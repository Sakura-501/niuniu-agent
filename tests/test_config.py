from niuniu_agent.config import AgentMode, AgentSettings


def test_settings_load_debug_defaults(monkeypatch) -> None:
    monkeypatch.setenv("NIUNIU_AGENT_MODE", "debug")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL", "ep-jsc7o0kw")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_BASE_URL", "http://10.0.0.24/70_f8g1qfuu/v1")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_HOST", "https://challenge.zc.tencent.com")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_TOKEN", "token")

    settings = AgentSettings()

    assert settings.mode is AgentMode.DEBUG
    assert settings.poll_interval_seconds == 15
    assert settings.contest_mcp_url == "https://challenge.zc.tencent.com/mcp"


def test_settings_load_competition_defaults(monkeypatch) -> None:
    monkeypatch.setenv("NIUNIU_AGENT_MODE", "competition")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL", "ep-jsc7o0kw")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_BASE_URL", "http://10.0.0.24/70_f8g1qfuu/v1")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_HOST", "https://challenge.zc.tencent.com")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_TOKEN", "token")

    settings = AgentSettings()

    assert settings.mode is AgentMode.COMPETITION
    assert settings.poll_interval_seconds == 30
