from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents import RunHooks


@dataclass(slots=True)
class TraceEvent:
    kind: str
    name: str
    detail: str = ""


@dataclass(slots=True)
class TraceRecorder:
    events: list[TraceEvent] = field(default_factory=list)

    def add(self, kind: str, name: str, detail: str = "") -> None:
        self.events.append(TraceEvent(kind=kind, name=name, detail=detail))

    def render(self) -> str:
        lines: list[str] = []
        for event in self.events:
            if event.detail:
                lines.append(f"[{event.kind}] {event.name}: {event.detail}")
            else:
                lines.append(f"[{event.kind}] {event.name}")
        return "\n".join(lines)


class RuntimeTraceHooks(RunHooks[object]):
    def __init__(self, recorder: TraceRecorder, event_logger: Any | None = None) -> None:
        self.recorder = recorder
        self.event_logger = event_logger

    async def on_handoff(self, context, from_agent, to_agent) -> None:
        self.recorder.add("handoff", f"{from_agent.name} -> {to_agent.name}")

    async def on_tool_start(self, context, agent, tool) -> None:
        self.recorder.add("tool.start", tool.name)

    async def on_tool_end(self, context, agent, tool, result: str) -> None:
        detail = result if len(result) < 240 else result[:237] + "..."
        self.recorder.add("tool.end", tool.name, detail)
        if self.event_logger is not None:
            self.event_logger.log(
                "agent.tool_end",
                {"tool": tool.name, "agent": agent.name, "detail": detail},
            )
