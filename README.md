# niuniu-agent

Autonomous MCP-only pentest agent foundation for the Tencent hackathon main battlefield.

## Scope

- Main battlefield only
- Official MCP only
- `debug` and `competition` run modes
- Four-track strategy router
- Structured logs and persistent state for later UI work

## Runtime Layout

- `runtime/events.jsonl`: structured execution events
- `runtime/state.db`: submitted-flag state
- `runtime/snippets/`: generated Python snippets

## Environment

Copy `.env.example` to `.env` and fill in your model and contest credentials.

Required variables:

- `NIUNIU_AGENT_MODEL`
- `NIUNIU_AGENT_MODEL_BASE_URL`
- `NIUNIU_AGENT_MODEL_API_KEY`
- `NIUNIU_AGENT_CONTEST_HOST`
- `NIUNIU_AGENT_CONTEST_TOKEN`

## Local Usage

Install dependencies:

```bash
uv sync
```

Run a single debug pass against one challenge:

```bash
set -a
source .env
set +a
uv run niuniu-agent run --mode debug --once --challenge-code <challenge_code>
```

Run as a long-lived loop:

```bash
set -a
source .env
set +a
uv run niuniu-agent run --mode competition
```

## Tests

```bash
uv run pytest -v
```

## Debug Server Deployment

```bash
git clone https://github.com/Sakura-501/niuniu-agent.git
cd niuniu-agent
uv sync
cp .env.example .env
```

Then fill in `.env`, start the agent in `debug` mode, verify logs under `runtime/`, and only switch the official platform to answer mode after the agent is already running.
