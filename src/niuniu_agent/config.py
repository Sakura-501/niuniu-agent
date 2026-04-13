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
    model_rate_limit_retry_attempts: int = 3
    model_rate_limit_retry_base_delay_seconds: float = 1.0
    callback_public_ip: str | None = None
    callback_username: str | None = None
    callback_password: str | None = None
    callback_usage: str = "Use this public callback server for reverse shells, pivoting, and persistence when a target must call back."
    contest_host: str
    contest_token: str
    poll_interval_seconds: int | None = None
    runtime_dir: Path = Path("runtime")
    competition_idle_sleep_seconds: int = 15
    competition_error_backoff_seconds: int = 10
    competition_max_error_backoff_seconds: int = 120
    competition_worker_max_seconds_per_challenge: int = 1800
    competition_worker_stall_seconds: int = 180
    competition_defer_seconds: int = 60
    official_completion_grace_seconds: int = 30
    model_context_window_tokens: int = 204800
    context_compaction_threshold_ratio: float = 0.8
    estimated_chars_per_token: int = 4
    context_compaction_keep_tail_messages: int = 8
    context_compaction_keep_recent_tool_results: int = 3
    context_compaction_tool_result_preview_chars: int = 240
    context_compaction_summary_input_chars: int = 80000
    context_compaction_summary_max_tokens: int = 2000
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

    @property
    def callback_resource(self) -> dict[str, str] | None:
        if not (self.callback_public_ip and self.callback_username and self.callback_password):
            return None
        return {
            "host": self.callback_public_ip,
            "username": self.callback_username,
            "password": self.callback_password,
            "usage": self.callback_usage,
        }

    @property
    def context_compaction_threshold_chars(self) -> int:
        return int(
            self.model_context_window_tokens
            * self.context_compaction_threshold_ratio
            * self.estimated_chars_per_token
        )

    @model_validator(mode="after")
    def apply_mode_defaults(self) -> "AgentSettings":
        if self.poll_interval_seconds is None:
            self.poll_interval_seconds = 15 if self.mode is AgentMode.DEBUG else 30
        if self.session_db_path is None:
            self.session_db_path = self.runtime_dir / "sessions.sqlite3"
        return self
