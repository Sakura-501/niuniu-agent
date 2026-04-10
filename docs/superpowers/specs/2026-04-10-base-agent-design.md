# Niuniu Agent Base Design

## Scope

This design covers the first implementation slice of `niuniu-agent`:

- Main battlefield only
- Official contest integration through MCP only
- Autonomous operation in both `debug` and `competition` modes
- Four-track strategy plug-in boundary, with a complete first-pass framework and generic initial strategy prompts
- Structured logs and persisted run state for later UI and control-plane work

This design explicitly excludes:

- The parallel forum battlefield
- A dedicated web UI in the first slice
- Human-in-the-loop steps after the agent enters competition mode

## Goals

The agent must:

1. Load contest and model configuration from environment variables.
2. Connect to the official MCP server and manage the challenge lifecycle.
3. Run as a long-lived process that can continue after SSH access is removed.
4. Persist enough state to resume safely and avoid duplicate submissions.
5. Expose detailed execution logs in a format that a future UI can consume directly.

## Architecture

The first version uses a single controller process with plug-in strategy modules.

### Controller

The controller owns:

- startup and shutdown
- challenge polling
- challenge selection
- instance start/stop
- flag submission
- retry policy
- state persistence

### Contest MCP Adapter

The MCP adapter wraps the official tools:

- `list_challenges`
- `start_challenge`
- `submit_flag`
- `view_hint`
- `stop_challenge`

The controller calls the adapter directly instead of routing contest control through the LLM.

### LLM Solver

The solver is responsible only for analysis and exploitation of a started challenge entrypoint. It can use local execution tools such as HTTP requests, shell commands, and Python proof-of-concept snippets.

### Strategy Registry

Four strategy modules are registered behind one common interface. The first slice provides:

- a router
- track-specific prompts
- track-level execution settings

The initial implementation uses generic, conservative prompts until the official track-specific challenge descriptions are fully mapped.

### State and Telemetry

State is persisted to SQLite for resumability. Detailed execution events are appended to JSONL log files for direct inspection and later UI streaming.

## Modes

### Debug Mode

Used during the official debug phase.

Capabilities:

- run once or loop
- target a single challenge code
- verbose logs
- optional dry-run for strategy planning

### Competition Mode

Used after the operator switches the official platform into answer mode.

Capabilities:

- long-running unattended loop
- resumable state
- strict retry and backoff
- automatic cleanup on challenge completion or repeated failure

## Data Flow

1. Load settings.
2. Initialize telemetry and state.
3. Connect to MCP.
4. List visible challenges.
5. Select the next unfinished challenge.
6. Start the challenge instance if needed.
7. Route the challenge to a strategy.
8. Let the LLM solver use local tools against the challenge entrypoint.
9. Submit any candidate flags immediately.
10. Persist outcomes and stop the instance when appropriate.
11. Repeat based on mode.

## Testing Strategy

The first slice uses test-driven development for:

- settings loading and defaults
- challenge routing
- telemetry event serialization
- state persistence
- controller decisions that do not require live network access

Live MCP and remote-host validation are handled separately on the debug server.

## Risks

- The official track descriptions are only partially available in the local reference set, so the initial strategy prompts must stay generic.
- The isolated competition network means the agent must not depend on interactive setup after startup.
- MCP library behavior can drift, so the adapter must stay thin and well logged.

## Initial Deliverables

- repository scaffold
- versioned package
- MCP adapter
- controller loop
- local tool execution layer
- strategy router
- tests for core non-network behavior
- debug-server deployment instructions
