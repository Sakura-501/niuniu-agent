from niuniu_agent.tools_inventory import default_tool_inventory


def test_default_tool_inventory_includes_internal_ad_helpers() -> None:
    inventory = {item.name: item for item in default_tool_inventory()}

    assert inventory["petitpotam"].available is True
    assert inventory["dfscoerce"].available is True
    assert inventory["passthecert"].available is True
    assert inventory["nopac"].available is True
    assert inventory["nopac-scanner"].available is True
    assert inventory["ajpy-tomcat"].available is True
    assert inventory["phpggc"].available is True
    assert inventory["redis-rogue-server"].available is True
    assert inventory["rogue-mysql-server"].available is True
    assert inventory["grafana-exp"].available is True
    assert inventory["powermad-asset"].available is True
    assert inventory["privesccheck-asset"].available is True
    assert inventory["certify-asset"].available is True
    assert inventory["ms14-068-asset"].available is True
    assert inventory["rubeus-asset"].available is True
    assert inventory["sharphound-asset"].available is True
    assert inventory["sweetpotato-asset"].available is True
    assert inventory["sebackupprivilege-asset"].available is True
