from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentMode(str, Enum):
    DEBUG = "debug"
    COMPETITION = "competition"


@dataclass(frozen=True, slots=True)
class ModelProviderConfig:
    provider_id: str
    display_name: str
    model: str
    base_url: str
    api_key: str
    priority: int


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
    model_provider_id: str = "official"
    model_provider_name: str = "官方提供"
    fallback_model: str | None = None
    fallback_model_base_url: str | None = None
    fallback_model_api_key: str | None = None
    fallback_model_provider_id: str = "fallback"
    fallback_model_provider_name: str = "备用供应商"
    model_failover_enabled: bool = True
    contest_host: str
    contest_token: str
    poll_interval_seconds: int | None = None
    runtime_dir: Path = Path("runtime")
    competition_idle_sleep_seconds: int = 15
    competition_error_backoff_seconds: int = 10
    competition_max_error_backoff_seconds: int = 120
    competition_worker_max_seconds_per_challenge: int = 3600
    competition_worker_stall_seconds: int = 180
    competition_defer_seconds: int = 60
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

    @property
    def model_providers(self) -> tuple[ModelProviderConfig, ...]:
        providers = [
            ModelProviderConfig(
                provider_id=self.model_provider_id,
                display_name=self.model_provider_name,
                model=self.model,
                base_url=self.model_base_url.rstrip("/"),
                api_key=self.model_api_key,
                priority=0,
            )
        ]
        if self.fallback_model and self.fallback_model_base_url and self.fallback_model_api_key:
            providers.append(
                ModelProviderConfig(
                    provider_id=self.fallback_model_provider_id,
                    display_name=self.fallback_model_provider_name,
                    model=self.fallback_model,
                    base_url=self.fallback_model_base_url.rstrip("/"),
                    api_key=self.fallback_model_api_key,
                    priority=1,
                )
            )
        return tuple(providers)

    @model_validator(mode="after")
    def apply_mode_defaults(self) -> "AgentSettings":
        if self.poll_interval_seconds is None:
            self.poll_interval_seconds = 15 if self.mode is AgentMode.DEBUG else 30
        if self.session_db_path is None:
            self.session_db_path = self.runtime_dir / "sessions.sqlite3"
        return self
