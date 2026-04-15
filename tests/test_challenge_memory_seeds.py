from niuniu_agent.state_store import StateStore
from niuniu_agent.strategies.challenge_memory_seeds import apply_seed_memories


def test_apply_seed_memories_persists_key_challenge_strategies(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    apply_seed_memories(store)

    bpoxy = store.list_challenge_memories("BpOxyTLXpdveWilhjRCFjZtMGjgr", limit=10)
    gradio = store.list_challenge_memories("3ZdueytTkJeRy2wiYmJiqwrzP2XiNqs", limit=10)
    track3_link = store.list_challenge_memories("6RmRST2HkeTbwgbyMJaN", limit=10)
    track3_layer = store.list_challenge_memories("K7kbx40FbhQNODZkS", limit=10)
    track3_firewall = store.list_challenge_memories("2ihdUTWqg7iVcvvD7GAZzOadCxS", limit=10)

    assert bpoxy
    assert gradio
    assert track3_link
    assert track3_layer
    assert track3_firewall
    assert bpoxy[0]["persistent"] is True
    assert gradio[0]["persistent"] is True
    assert any(item["memory_type"] == "operator_strategy" and item["persistent"] is True for item in track3_link)
    assert any(item["memory_type"] == "operator_strategy" and item["persistent"] is True for item in track3_layer)
    assert any(item["memory_type"] == "operator_strategy" and item["persistent"] is True for item in track3_firewall)


def test_track3_seed_memories_avoid_instance_specific_ips_and_webshell_paths(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    apply_seed_memories(store)

    for code in ("6RmRST2HkeTbwgbyMJaN", "K7kbx40FbhQNODZkS", "2ihdUTWqg7iVcvvD7GAZzOadCxS"):
        memories = store.list_challenge_memories(code, limit=20)
        for item in memories:
            content = item["content"]
            assert "10.0.163." not in content
            assert "172.19.0." not in content
            assert "172.20.0." not in content
            assert "192.168." not in content
            assert "/backup/b.php" not in content
            assert "/uploads/lv.php" not in content
            assert "/uploads/suo5.php" not in content


def test_apply_seed_memories_replaces_outdated_track3_seed_content(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    code = "K7kbx40FbhQNODZkS"
    store.add_challenge_memory(
        code,
        "persistent_flag_record",
        "old seed mentions 172.20.0.3 and /var/www/html/c.php",
        source="seed",
        persistent=True,
    )
    store.add_challenge_memory(
        code,
        "operator_strategy",
        "old seed mentions 172.20.0.5 specifically",
        source="seed",
        persistent=True,
    )

    apply_seed_memories(store)

    memories = store.list_challenge_memories(code, limit=20)
    contents = [item["content"] for item in memories if item["source"] == "seed"]
    assert not any("old seed mentions 172.20.0.3" in item for item in contents)
    assert not any("old seed mentions 172.20.0.5" in item for item in contents)


def test_track3_operator_strategy_contains_curated_attack_routes(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")

    apply_seed_memories(store)

    link = next(
        item for item in store.list_challenge_memories("6RmRST2HkeTbwgbyMJaN", limit=20)
        if item["memory_type"] == "operator_strategy"
    )
    layer = next(
        item for item in store.list_challenge_memories("K7kbx40FbhQNODZkS", limit=20)
        if item["memory_type"] == "operator_strategy"
    )
    firewall = next(
        item for item in store.list_challenge_memories("2ihdUTWqg7iVcvvD7GAZzOadCxS", limit=20)
        if item["memory_type"] == "operator_strategy"
    )

    assert "上传webshell" in link["content"]
    assert "Redis" in link["content"]
    assert "12345678" in link["content"]
    assert "MariaDB" in link["content"]
    assert "root/root" in link["content"]
    assert "Admin@123" in link["content"]
    assert "Flask Web" in link["content"]
    assert "/proxy.php" in layer["content"]
    assert "admin/articles.php?action=edit&id=..." in layer["content"]
    assert "/var/www/html/c.php" in layer["content"]
    assert "数据查询" in layer["content"]
    assert "OA" in layer["content"]
    assert "不要把其他题目的 `admin / Admin@123` 跨题误用到这里" in layer["content"]
    assert "db.sql" in layer["content"]
    assert "services.php" in firewall["content"]
    assert "pearcmd.php" in firewall["content"]
    assert "/backup/tunnel.php" in firewall["content"]
    assert "backup/check_port.php" in firewall["content"]
    assert "不要把其他题目的 `admin / Admin@123` 跨题误用到这里" in firewall["content"]
    assert "SSH" in firewall["content"]
    assert "CVE-2024-6387" in firewall["content"]
