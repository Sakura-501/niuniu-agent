from __future__ import annotations

from typing import Any

from agents import Runner
from agents.exceptions import MaxTurnsExceeded


TURN_CHUNK_SIZE = 12
CONTINUE_MESSAGE = (
    "Continue from the current state. "
    "Do not restart completed work. "
    "Keep using tools if needed, and only stop when you have a final answer."
)


async def run_until_final_output(
    agent: Any,
    initial_input: str,
    context: Any,
    session: Any,
    hooks: Any,
    event_logger: Any | None,
) -> Any:
    current_input = initial_input

    while True:
        try:
            return await Runner.run(
                agent,
                current_input,
                context=context,
                max_turns=TURN_CHUNK_SIZE,
                hooks=hooks,
                session=session,
            )
        except MaxTurnsExceeded:
            if event_logger is not None:
                event_logger.log(
                    "agent.turn_chunk_exhausted",
                    {"turn_chunk_size": TURN_CHUNK_SIZE},
                )
            current_input = CONTINUE_MESSAGE
