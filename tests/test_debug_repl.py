from niuniu_agent.runtime.debug_repl import _build_greeting_reply, _is_greeting


def test_debug_repl_detects_greetings() -> None:
    assert _is_greeting("你好") is True
    assert _is_greeting("hello") is True
    assert _is_greeting("请扫描这个目标") is False


def test_debug_repl_builds_greeting_reply() -> None:
    reply = _build_greeting_reply("current_level=1")

    assert "你好" in reply
    assert "current_level=1" in reply
