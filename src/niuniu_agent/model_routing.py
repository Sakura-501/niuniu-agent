from __future__ import annotations

from dataclasses import dataclass
import asyncio
from typing import Any

from openai import AsyncOpenAI

from niuniu_agent.config import AgentSettings, ModelProviderConfig


@dataclass(frozen=True, slots=True)
class RoutedProvider:
    provider_id: str
    display_name: str
    model: str
    base_url: str
    api_key: str


class ModelProviderRouter:
    def __init__(self, settings: AgentSettings, state_store: Any) -> None:
        self.settings = settings
        self.state_store = state_store
        self._sleep = asyncio.sleep

    def current_selection(self) -> dict[str, str | None]:
        provider_id = self.state_store.get_runtime_option("selected_model_provider_id")
        model_override = self.state_store.get_runtime_option("selected_model_override")
        if provider_id is None and self.settings.model_providers:
            provider_id = self.settings.model_providers[0].provider_id
        return {
            "provider_id": provider_id,
            "model_override": model_override,
        }

    def set_selection(self, provider_id: str, model_override: str | None = None) -> dict[str, object]:
        provider = self.get_provider(provider_id)
        self.state_store.set_runtime_option("selected_model_provider_id", provider.provider_id)
        if model_override:
            self.state_store.set_runtime_option("selected_model_override", model_override.strip())
        else:
            self.state_store.delete_runtime_option("selected_model_override")
        return self.describe()

    def clear_selection(self) -> dict[str, object]:
        self.state_store.delete_runtime_option("selected_model_provider_id")
        self.state_store.delete_runtime_option("selected_model_override")
        return self.describe()

    def get_provider(self, provider_id: str) -> ModelProviderConfig:
        for provider in self.settings.model_providers:
            if provider.provider_id == provider_id:
                return provider
        raise ValueError(f"unknown model provider: {provider_id}")

    def execution_order(self) -> list[ModelProviderConfig]:
        selection = self.current_selection()
        selected_id = selection["provider_id"]
        providers = list(self.settings.model_providers)
        ordered: list[ModelProviderConfig] = []
        if selected_id is not None:
            for provider in providers:
                if provider.provider_id == selected_id:
                    ordered.append(provider)
                    break
        for provider in providers:
            if provider.provider_id not in {item.provider_id for item in ordered}:
                ordered.append(provider)
        return ordered

    def resolve_model_name(self, provider: ModelProviderConfig) -> str:
        selection = self.current_selection()
        if selection["provider_id"] == provider.provider_id and selection["model_override"]:
            return str(selection["model_override"])
        return provider.model

    def describe(self) -> dict[str, object]:
        selection = self.current_selection()
        providers: list[dict[str, object]] = []
        for provider in self.settings.model_providers:
            state = self.state_store.get_model_provider_state(provider.provider_id)
            providers.append(
                {
                    "provider_id": provider.provider_id,
                    "display_name": provider.display_name,
                    "base_url": provider.base_url,
                    "model": provider.model,
                    "selected": selection["provider_id"] == provider.provider_id,
                    "effective_model": self.resolve_model_name(provider),
                    "state": state,
                }
            )
        return {
            "selected_provider_id": selection["provider_id"],
            "selected_model": (
                next(
                    (
                        item["effective_model"]
                        for item in providers
                        if item["provider_id"] == selection["provider_id"]
                    ),
                    providers[0]["effective_model"] if providers else None,
                )
            ),
            "failover_enabled": self.settings.model_failover_enabled,
            "providers": providers,
        }

    def build_client(self) -> "RoutedAsyncOpenAI":
        return RoutedAsyncOpenAI(self)

    async def create_completion(self, **kwargs: Any) -> Any:
        stream_requested = bool(kwargs.get("stream"))
        errors: list[str] = []
        for provider in self.execution_order():
            model_name = self.resolve_model_name(provider)
            client = AsyncOpenAI(api_key=provider.api_key, base_url=provider.base_url)
            request_kwargs = dict(kwargs)
            request_kwargs["model"] = model_name
            provider_error: Exception | None = None
            delay = self.settings.model_rate_limit_retry_base_delay_seconds
            for attempt in range(1, self.settings.model_rate_limit_retry_attempts + 1):
                try:
                    result = await client.chat.completions.create(**request_kwargs)
                    if stream_requested:
                        return TrackedCompletionStream(
                            stream=result,
                            router=self,
                            provider_id=provider.provider_id,
                        )
                    self.state_store.record_model_provider_success(provider.provider_id)
                    self.state_store.set_runtime_option("last_model_provider_id", provider.provider_id)
                    return result
                except Exception as exc:  # noqa: BLE001
                    provider_error = exc
                    if self._is_rate_limit_error(exc) and attempt < self.settings.model_rate_limit_retry_attempts:
                        await self._sleep(delay)
                        delay *= 2
                        continue
                    break
            if provider_error is not None:
                self.state_store.record_model_provider_failure(provider.provider_id, str(provider_error))
                errors.append(f"{provider.provider_id}: {provider_error}")
                if not self.settings.model_failover_enabled:
                    raise provider_error
        raise RuntimeError("all model providers failed: " + " | ".join(errors))

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return "rate_limit_exceeded" in text or "429" in text or "too many requests" in text


class RoutedAsyncOpenAI:
    def __init__(self, router: ModelProviderRouter) -> None:
        self.chat = _RoutedChat(router)


class _RoutedChat:
    def __init__(self, router: ModelProviderRouter) -> None:
        self.completions = _RoutedChatCompletions(router)


class _RoutedChatCompletions:
    def __init__(self, router: ModelProviderRouter) -> None:
        self.router = router

    async def create(self, **kwargs: Any) -> Any:
        return await self.router.create_completion(**kwargs)


class TrackedCompletionStream:
    def __init__(self, *, stream: Any, router: ModelProviderRouter, provider_id: str) -> None:
        self.stream = stream
        self.router = router
        self.provider_id = provider_id

    def __aiter__(self) -> "TrackedCompletionStream":
        return self

    async def __anext__(self) -> Any:
        try:
            item = await self.stream.__anext__()
            return item
        except StopAsyncIteration:
            self.router.state_store.record_model_provider_success(self.provider_id)
            self.router.state_store.set_runtime_option("last_model_provider_id", self.provider_id)
            raise
        except Exception as exc:  # noqa: BLE001
            self.router.state_store.record_model_provider_failure(self.provider_id, str(exc))
            raise
