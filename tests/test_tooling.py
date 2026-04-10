from niuniu_agent.tooling import LocalToolbox


def test_http_tool_schema_contains_method_and_url(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    tools = {
        entry["function"]["name"]: entry
        for entry in toolbox.describe_tools()
    }

    http_tool = tools["http_request"]
    properties = http_tool["function"]["parameters"]["properties"]

    assert "method" in properties
    assert "url" in properties


def test_extract_flags_deduplicates_matches(tmp_path) -> None:
    toolbox = LocalToolbox(tmp_path)

    flags = toolbox.extract_flags("flag{one} ignore flag{one} and flag{two}")

    assert flags == ["flag{one}", "flag{two}"]
