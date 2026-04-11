from __future__ import annotations

from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentMode(str, Enum):
    DEBUG = "debug"
    COMPETITION = "competition"


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NIUNIU_AGENT_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    mode: AgentMode = AgentMode.DEBUG
    model: str
    model_base_url: str
    model_api_key: str
    contest_host: str
    contest_token: str
    poll_interval_seconds: int | None = None
    runtime_dir: Path = Path("runtime")
    competition_idle_sleep_seconds: int = 15
    competition_error_backoff_seconds: int = 10
    competition_max_error_backoff_seconds: int = 120
    competition_run_id: str | None = None
    web_host: str = "0.0.0.0"
    web_port: int = 8081
    session_db_path: Path | None = None
    request_timeout_seconds: int = 20

    @property
    def contest_mcp_url(self) -> str:
        host = self.contest_host.rstrip("/")
        if not urlparse(host).scheme:
            host = f"http://{host}"
        return f"{host}/mcp"

    @model_validator(mode="after")
    def apply_mode_defaults(self) -> "AgentSettings":
        if self.poll_interval_seconds is None:
            self.poll_interval_seconds = 15 if self.mode is AgentMode.DEBUG else 30
        if self.session_db_path is None:
            self.session_db_path = self.runtime_dir / "sessions.sqlite3"
        return self
