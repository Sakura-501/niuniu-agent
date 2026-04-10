# OpenAI Agents Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `niuniu-agent` on top of the OpenAI Agents SDK, following the `learn-claude-code` architectural split between loop, tool control plane, memory/state, and autonomous runtime.

**Architecture:** A deterministic control plane owns contest state and local persistence. An async OpenAI Agents layer provides the manager agent, specialist handoffs, function tools, and MCP tools. Two runtimes sit above it: a persistent interactive debug REPL and a nonstop autonomous competition loop.

**Tech Stack:** Python 3.12+, openai-agents, AsyncOpenAI, MCP streamable HTTP, SQLiteSession, Typer, Pydantic settings, SQLite, pytest

---

### Task 1: Replace Runtime Topology

**Files:**
- Create: `src/niuniu_agent/runtime/`
- Create: `src/niuniu_agent/control_plane/`
- Create: `src/niuniu_agent/agent_stack/`
- Modify: `src/niuniu_agent/cli.py`

- [ ] Write failing tests for the new runtime entry points.
- [ ] Implement new module layout and route CLI to new runtimes.
- [ ] Run focused tests.
- [ ] Commit.

### Task 2: Build Deterministic Control Plane

**Files:**
- Create: `src/niuniu_agent/control_plane/mcp_client.py`
- Create: `src/niuniu_agent/control_plane/challenge_store.py`
- Create: `src/niuniu_agent/control_plane/models.py`
- Modify: `src/niuniu_agent/state_store.py`

- [ ] Write failing tests for challenge refresh, completion state, and local submission state.
- [ ] Implement normalized challenge snapshots and persistence helpers.
- [ ] Run focused tests.
- [ ] Commit.

### Task 3: Build OpenAI Agents Tool Bus

**Files:**
- Create: `src/niuniu_agent/agent_stack/model.py`
- Create: `src/niuniu_agent/agent_stack/tools.py`
- Create: `src/niuniu_agent/agent_stack/factory.py`
- Create: `src/niuniu_agent/agent_stack/hooks.py`

- [ ] Write failing tests for tool registration and debug-safe tool behavior.
- [ ] Implement chat-completions-backed agent factory and MCP server attachment.
- [ ] Run focused tests.
- [ ] Commit.

### Task 4: Rebuild Debug Mode

**Files:**
- Create: `src/niuniu_agent/runtime/debug_repl.py`
- Modify: `src/niuniu_agent/debug_chat.py`

- [ ] Write failing tests for session persistence and non-ASCII input handling.
- [ ] Implement SQLiteSession-backed interactive loop.
- [ ] Run focused tests.
- [ ] Commit.

### Task 5: Rebuild Competition Mode

**Files:**
- Create: `src/niuniu_agent/runtime/autonomous_loop.py`
- Create: `src/niuniu_agent/runtime/recovery.py`

- [ ] Write failing tests for retry, backoff, and nonstop loop behavior.
- [ ] Implement nonstop outer loop with failure recovery.
- [ ] Run focused tests.
- [ ] Commit.

### Task 6: Update Docs and Operations

**Files:**
- Modify: `README.md`
- Modify: `scripts/remote_control.sh`

- [ ] Update Chinese docs to reflect the rebuilt architecture.
- [ ] Verify local tests and a remote smoke run.
- [ ] Commit and push.
