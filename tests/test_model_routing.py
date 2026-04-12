import pytest

from niuniu_agent.config import AgentSettings
from niuniu_agent.model_routing import ModelProviderRouter
from niuniu_agent.state_store import StateStore


def build_settings() -> AgentSettings:
    return AgentSettings.model_construct(
        mode="competition",
        model="ep-jsc7o0kw",
        model_base_url="http://10.0.0.24/70_f8g1qfuu/v1",
        model_api_key="official-key",
        model_provider_id="official",
        model_provider_name="官方提供",
        fallback_model="gpt-5.4-xhigh",
        fallback_model_base_url="http://10.0.0.24/70_tsdb3cwf/codex/v1",
        fallback_model_api_key="fallback-key",
        fallback_model_provider_id="rightcodes",
        fallback_model_provider_name="rightcodes供应商",
        contest_host="https://challenge.zc.tencent.com",
        contest_token="token",
        runtime_dir="runtime",
    )


def test_model_provider_router_prefers_manual_selection(tmp_path) -> None:
    settings = build_settings()
    state_store = StateStore(tmp_path / "state.db")
    router = ModelProviderRouter(settings, state_store)

    state_store.set_runtime_option("selected_model_provider_id", "rightcodes")
    state_store.set_runtime_option("selected_model_override", "custom-model")

    summary = router.describe()
    order = router.execution_order()

    assert summary["selected_provider_id"] == "rightcodes"
    assert summary["selected_model"] == "custom-model"
    assert [provider.provider_id for provider in order] == ["rightcodes", "official"]


@pytest.mark.anyio
async def test_model_provider_router_retries_same_provider_on_rate_limit_then_succeeds(tmp_path, monkeypatch) -> None:
    settings = build_settings()
    state_store = StateStore(tmp_path / "state.db")
    router = ModelProviderRouter(settings, state_store)
    sleeps = []

    class FakeCompletions:
        def __init__(self) -> None:
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("429 rate_limit_exceeded")
            return {"ok": True, "model": kwargs["model"]}

    fake_completions = FakeCompletions()

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = type("Chat", (), {"completions": fake_completions})()

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("niuniu_agent.model_routing.AsyncOpenAI", FakeClient)
    monkeypatch.setattr(router, "_sleep", fake_sleep)

    result = await router.create_completion(messages=[], model="ignored")

    assert result["ok"] is True
    assert fake_completions.calls == 2
    assert sleeps == [1.0]


@pytest.mark.anyio
async def test_model_provider_router_falls_back_after_repeated_rate_limit(tmp_path, monkeypatch) -> None:
    settings = build_settings()
    state_store = StateStore(tmp_path / "state.db")
    router = ModelProviderRouter(settings, state_store)
    sleeps = []

    class FakeCompletions:
        def __init__(self, provider_id: str) -> None:
            self.provider_id = provider_id
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            if self.provider_id == "official":
                raise RuntimeError("429 rate_limit_exceeded")
            return {"provider": self.provider_id, "model": kwargs["model"]}

    clients = {}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            base_url = kwargs["base_url"]
            provider_id = "official" if "70_f8g1qfuu" in base_url else "rightcodes"
            completions = clients.setdefault(provider_id, FakeCompletions(provider_id))
            self.chat = type("Chat", (), {"completions": completions})()

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("niuniu_agent.model_routing.AsyncOpenAI", FakeClient)
    monkeypatch.setattr(router, "_sleep", fake_sleep)

    result = await router.create_completion(messages=[], model="ignored")

    assert result["provider"] == "rightcodes"
    assert clients["official"].calls == router.settings.model_rate_limit_retry_attempts
    assert clients["rightcodes"].calls == 1
    assert sleeps == [1.0, 2.0]
