# Niuniu Agent OpenAI Agents Rebuild Design

## Objective

Replace the current ad-hoc agent runtime with a new architecture inspired by `learn-claude-code`, using the OpenAI Agents SDK in async mode.

This rebuild explicitly changes both runtime behavior and project structure:

- `debug` becomes an interactive REPL backed by a persistent agent session
- `competition` becomes a nonstop autonomous loop with retry and recovery
- the runtime is reorganized into control-plane, tool bus, memory/state, and execution loops

## Architecture Shape

The rebuilt system follows the same high-level progression emphasized by `learn-claude-code`:

1. Agent loop
2. Tool control plane
3. Persistent state and memory
4. Error recovery and autonomous background runtime

## Core Layers

### 1. Control Plane

The control plane owns contest state that should not depend on LLM reasoning:

- MCP connectivity
- challenge refresh
- challenge normalization
- challenge completion state
- local submission history
- retry bookkeeping

This layer exposes deterministic operations to both debug and competition runtimes.

### 2. Tool Bus

The tool bus is the `learn-claude-code` style control plane for tool execution.

The agent sees two capability sources:

- official contest tools through `MCPServerStreamableHttp`
- local function tools built from Python async functions

The local tools provide:

- challenge summary
- local state inspection
- HTTP requests
- shell execution
- Python snippet execution

### 3. Memory and Runtime State

State is persisted in SQLite and JSONL so both modes can resume and explain what happened.

Persistent items:

- submitted flags
- challenge attempt counters
- last successful activity timestamp
- autonomous loop failure streak
- debug session message history through `SQLiteSession`

### 4. Agent Layer

The OpenAI Agents SDK provides the execution harness.

Agent topology:

- `manager` agent: global orchestrator
- `track1`, `track2`, `track3`, `track4` specialists

The manager can hand off to specialists. Specialists focus on strategy, while contest state comes from tools and control-plane snapshots.

The model backend uses `OpenAIChatCompletionsModel` with a custom `AsyncOpenAI` client so the Tencent-compatible gateway can be used even if the runtime does not expose the Responses API.

### 5. Runtime Loops

#### Debug Runtime

Interactive REPL with a persistent SQLite-backed session.

Each turn:

1. refresh contest snapshot
2. inject snapshot into the control-plane context
3. run the manager agent against user input
4. stream or print the final answer plus visible tool activity

#### Competition Runtime

Autonomous loop that never intentionally stops.

Each cycle:

1. refresh contest state
2. select the highest-priority unfinished challenge
3. run the manager agent with a system task describing current state
4. persist outcomes
5. retry on error with backoff
6. continue forever

Any exception becomes a logged event and a retry, not a process-ending failure.

## Failure Strategy

The competition runtime must keep running even when:

- MCP calls fail
- model calls fail
- a challenge instance cannot be started
- a tool crashes

Recovery policy:

- log the failure
- increment failure counters
- back off
- continue the outer loop

## Compatibility Decision

This rebuild does not preserve internal module compatibility with the previous implementation. The external user-facing concepts that remain are:

- `.env`
- `runtime/`
- `debug` and `competition` modes
- remote control script

## Deliverables

- rebuilt async runtime using `openai-agents`
- new control-plane module layout
- interactive debug REPL
- nonstop competition loop
- updated Chinese documentation
