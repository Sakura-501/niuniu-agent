# Base Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable `niuniu-agent` foundation for the Tencent hackathon main battlefield using MCP only, with debug and competition modes.

**Architecture:** A single controller process manages contest lifecycle through MCP, delegates challenge solving to an LLM-backed local tool loop, and persists state plus logs for later UI work. Four track strategies are isolated behind a registry so prompts and heuristics can evolve independently.

**Tech Stack:** Python 3.14, OpenAI-compatible SDK, MCP Python SDK, Typer CLI, Pydantic settings/models, SQLite, pytest

---

### Task 1: Repository Bootstrap

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `VERSION`
- Create: `src/niuniu_agent/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
from niuniu_agent import __version__


def test_version_is_exposed() -> None:
    assert __version__ == "0.1.1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_version.py -v`
Expected: FAIL because the package and version are not defined yet.

- [ ] **Step 3: Write minimal implementation**

```python
__version__ = "0.1.1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_version.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md .gitignore pyproject.toml VERSION src/niuniu_agent/__init__.py tests/test_version.py
git commit -m "feat: bootstrap versioned agent package"
```

### Task 2: Settings and Mode Handling

**Files:**
- Create: `src/niuniu_agent/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
from niuniu_agent.config import AgentMode, AgentSettings


def test_settings_load_debug_defaults(monkeypatch) -> None:
    monkeypatch.setenv("NIUNIU_AGENT_MODE", "debug")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL", "ep-jsc7o0kw")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_BASE_URL", "http://10.0.0.24/70_f8g1qfuu/v1")
    monkeypatch.setenv("NIUNIU_AGENT_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_HOST", "10.0.0.44:8000")
    monkeypatch.setenv("NIUNIU_AGENT_CONTEST_TOKEN", "token")

    settings = AgentSettings()

    assert settings.mode is AgentMode.DEBUG
    assert settings.poll_interval_seconds == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL because `AgentSettings` is undefined.

- [ ] **Step 3: Write minimal implementation**

```python
class AgentMode(str, Enum):
    DEBUG = "debug"
    COMPETITION = "competition"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/niuniu_agent/config.py tests/test_config.py
git commit -m "feat: add settings and mode parsing"
```

### Task 3: State Store and Telemetry

**Files:**
- Create: `src/niuniu_agent/state_store.py`
- Create: `src/niuniu_agent/telemetry.py`
- Test: `tests/test_state_store.py`
- Test: `tests/test_telemetry.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_state_store_records_submitted_flag(tmp_path) -> None:
    ...


def test_telemetry_writes_jsonl(tmp_path) -> None:
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_state_store.py tests/test_telemetry.py -v`
Expected: FAIL because modules are missing.

- [ ] **Step 3: Write minimal implementation**

```python
class StateStore:
    ...


class EventLogger:
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_state_store.py tests/test_telemetry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/niuniu_agent/state_store.py src/niuniu_agent/telemetry.py tests/test_state_store.py tests/test_telemetry.py
git commit -m "feat: add persistent state and telemetry logging"
```

### Task 4: Strategy Routing

**Files:**
- Create: `src/niuniu_agent/models.py`
- Create: `src/niuniu_agent/strategies/base.py`
- Create: `src/niuniu_agent/strategies/router.py`
- Create: `src/niuniu_agent/strategies/track1.py`
- Create: `src/niuniu_agent/strategies/track2.py`
- Create: `src/niuniu_agent/strategies/track3.py`
- Create: `src/niuniu_agent/strategies/track4.py`
- Test: `tests/test_router.py`

- [ ] **Step 1: Write the failing test**

```python
def test_router_prefers_keyword_override() -> None:
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_router.py -v`
Expected: FAIL because router modules do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class StrategyRouter:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/niuniu_agent/models.py src/niuniu_agent/strategies tests/test_router.py
git commit -m "feat: add four-track strategy registry"
```

### Task 5: Contest MCP Adapter

**Files:**
- Create: `src/niuniu_agent/contest_mcp.py`
- Test: `tests/test_contest_mcp.py`

- [ ] **Step 1: Write the failing test**

```python
def test_normalize_entrypoints() -> None:
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_contest_mcp.py -v`
Expected: FAIL because the adapter module does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class ContestMCPClient:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_contest_mcp.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/niuniu_agent/contest_mcp.py tests/test_contest_mcp.py
git commit -m "feat: add official contest MCP adapter"
```

### Task 6: LLM Tool Loop and Local Tools

**Files:**
- Create: `src/niuniu_agent/llm.py`
- Create: `src/niuniu_agent/tooling.py`
- Test: `tests/test_tooling.py`

- [ ] **Step 1: Write the failing test**

```python
def test_http_tool_schema_contains_method_and_url() -> None:
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tooling.py -v`
Expected: FAIL because tooling modules are missing.

- [ ] **Step 3: Write minimal implementation**

```python
class LocalToolbox:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tooling.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/niuniu_agent/llm.py src/niuniu_agent/tooling.py tests/test_tooling.py
git commit -m "feat: add local tool loop foundation"
```

### Task 7: Controller and CLI

**Files:**
- Create: `src/niuniu_agent/controller.py`
- Create: `src/niuniu_agent/cli.py`
- Test: `tests/test_controller.py`

- [ ] **Step 1: Write the failing test**

```python
def test_controller_skips_already_submitted_flags(tmp_path) -> None:
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_controller.py -v`
Expected: FAIL because controller modules are missing.

- [ ] **Step 3: Write minimal implementation**

```python
class AgentController:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_controller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/niuniu_agent/controller.py src/niuniu_agent/cli.py tests/test_controller.py
git commit -m "feat: add autonomous controller and cli"
```

### Task 8: Verification and Deployment

**Files:**
- Modify: `README.md`
- Create: `.env.example`

- [ ] **Step 1: Write the deployment notes**

```text
Describe local run, debug run, competition run, and debug-server bootstrap.
```

- [ ] **Step 2: Run verification**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 3: Push and tag**

```bash
git push origin main
git push origin --tags
```

- [ ] **Step 4: Deploy to debug host**

```bash
ssh ubuntu@129.211.15.16
git clone https://github.com/Sakura-501/niuniu-agent.git
```

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example
git commit -m "docs: add runbook and deployment notes"
```
