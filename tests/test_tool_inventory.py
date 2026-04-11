from niuniu_agent.tools_inventory import default_tool_inventory


def test_default_tool_inventory_contains_core_tools() -> None:
    inventory = default_tool_inventory()
    names = {item.name for item in inventory}

    assert "python3" in names
    assert "curl" in names
    assert "jq" in names
    assert "rg" in names
    assert "nmap" in names
    assert "openssl" in names
    assert "impacket-secretsdump" in names
