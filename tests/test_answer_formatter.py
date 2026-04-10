from niuniu_agent.runtime.answer_formatter import build_formatter_prompt, should_format_debug_answer
from niuniu_agent.agent_stack.agent import ToolEvent


def test_should_format_debug_answer_when_tool_events_exist() -> None:
    event = ToolEvent(name="http_request", arguments={}, output="ok")
    assert should_format_debug_answer("你好", [event]) is True


def test_build_formatter_prompt_contains_sections_hint() -> None:
    event = ToolEvent(name="submit_flag", arguments={"flag": "flag{demo}"}, output="correct")
    prompt = build_formatter_prompt("给我 flag", "raw", [event])

    assert "## 结论" in prompt
    assert "submit_flag" in prompt
