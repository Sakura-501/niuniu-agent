from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentMode(str, Enum):
    DEBUG = "debug"
    COMPETITION = "competition"


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NIUNIU_AGENT_",
        extra="ignore",
    )

    mode: AgentMode = AgentMode.DEBUG
    model: str
    model_base_url: str
    model_api_key: str
    contest_host: str
    contest_token: str
    poll_interval_seconds: int | None = None
    runtime_dir: Path = Path("runtime")
    llm_max_iterations: int = 12
    request_timeout_seconds: int = 20

    @property
    def contest_mcp_url(self) -> str:
        return f"http://{self.contest_host}/mcp"

    @model_validator(mode="after")
    def apply_mode_defaults(self) -> "AgentSettings":
        if self.poll_interval_seconds is None:
            self.poll_interval_seconds = 15 if self.mode is AgentMode.DEBUG else 30
        return self
