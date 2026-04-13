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
    assert settings.competition_worker_max_seconds_per_challenge == 1800


def test_settings_builds_primary_and_fallback_model_providers(monkeypatch) -> None:
    monkeypatch.setenv("NIUNIU_AGENT_MODE", "competition")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_PROVIDER_ID", "official")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_PROVIDER_NAME", "官方提供")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL", "ep-jsc7o0kw")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_BASE_URL", "http://10.0.0.24/70_f8g1qfuu/v1")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_API_KEY", "official-key")
    monkeypatch.setenv("NIUNIU_AGENT_FALLBACK_MODEL_PROVIDER_ID", "rightcodes")
    monkeypatch.setenv("NIUNIU_AGENT_FALLBACK_MODEL_PROVIDER_NAME", "rightcodes供应商")
    monkeypatch.setenv("NIUNIU_AGENT_FALLBACK_MODEL", "gpt-5.4-xhigh")
    monkeypatch.setenv("NIUNIU_AGENT_FALLBACK_MODEL_BASE_URL", "http://10.0.0.24/70_tsdb3cwf/codex/v1")
    monkeypatch.setenv("NIUNIU_AGENT_FALLBACK_MODEL_API_KEY", "fallback-key")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_HOST", "https://challenge.zc.tencent.com")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_TOKEN", "token")

    settings = AgentSettings()

    providers = settings.model_providers

    assert [provider.provider_id for provider in providers] == ["official", "rightcodes"]
    assert providers[0].base_url == "http://10.0.0.24/70_f8g1qfuu/v1"
    assert providers[1].model == "gpt-5.4-xhigh"


def test_settings_exposes_callback_resource(monkeypatch) -> None:
    monkeypatch.setenv("NIUNIU_AGENT_MODE", "debug")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL", "ep-jsc7o0kw")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_BASE_URL", "http://10.0.0.24/70_f8g1qfuu/v1")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_HOST", "https://challenge.zc.tencent.com")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_TOKEN", "token")
    monkeypatch.setenv("NIUNIU_AGENT_CALLBACK_PUBLIC_IP", "129.211.15.16")
    monkeypatch.setenv("NIUNIU_AGENT_CALLBACK_USERNAME", "root")
    monkeypatch.setenv("NIUNIU_AGENT_CALLBACK_PASSWORD", "123QWE@qwe")

    settings = AgentSettings()

    assert settings.callback_resource["host"] == "129.211.15.16"
    assert settings.callback_resource["username"] == "root"
