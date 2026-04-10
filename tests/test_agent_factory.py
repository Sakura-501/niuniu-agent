from niuniu_agent.agent_stack.factory import build_agent_assembly
from niuniu_agent.config import AgentSettings


def test_agent_factory_builds_manager_and_specialists() -> None:
    settings = AgentSettings(
        model="ep-jsc7o0kw",
        model_base_url="https://tokenhub.tencentmaas.com/v1",
        model_api_key="test-key",
        contest_host="10.0.0.44:8000",
        contest_token="token",
    )

    assembly = build_agent_assembly(settings)

    assert assembly.manager.name == "contest-manager"
    assert set(assembly.specialists.keys()) == {"track1", "track2", "track3", "track4"}
    assert assembly.contest_server.name == "contest-mcp"
