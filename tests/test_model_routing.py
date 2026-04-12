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
