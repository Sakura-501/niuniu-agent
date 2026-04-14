from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import time
from types import SimpleNamespace
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
        return self.execution_order_for_time()

    def execution_order_for_time(self, *, now: float | None = None) -> list[ModelProviderConfig]:
        selection = self.current_selection()
        selected_id = selection["provider_id"]
        providers = list(self.settings.model_providers)
        selected_order = {
            provider.provider_id: index
            for index, provider in enumerate(self._selected_first_order(providers, selected_id))
        }
        unhealthy: list[ModelProviderConfig] = []
        healthy: list[ModelProviderConfig] = []
        for provider in providers:
            if self._is_provider_in_cooldown(provider.provider_id, now=now):
                unhealthy.append(provider)
            else:
                healthy.append(provider)
        if healthy:
            healthy.sort(key=lambda provider: selected_order[provider.provider_id])
            unhealthy.sort(
                key=lambda provider: (
                    self._provider_cooldown_remaining(provider.provider_id, now=now),
                    selected_order[provider.provider_id],
                )
            )
            return [*healthy, *unhealthy]
        return self._selected_first_order(providers, selected_id)

    @staticmethod
    def _selected_first_order(
        providers: list[ModelProviderConfig],
        selected_id: str | None,
    ) -> list[ModelProviderConfig]:
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

    def _provider_cooldown_remaining(self, provider_id: str, *, now: float | None = None) -> float:
        current = time.time() if now is None else now
        state = self.state_store.get_model_provider_state(provider_id)
        last_failure_at = state.get("last_failure_at")
        if state.get("consecutive_failures", 0) <= 0 or last_failure_at is None:
            return 0.0
        cooldown = float(self.settings.model_provider_failure_cooldown_seconds)
        return max(0.0, float(last_failure_at) + cooldown - current)

    def _is_provider_in_cooldown(self, provider_id: str, *, now: float | None = None) -> bool:
        return self._provider_cooldown_remaining(provider_id, now=now) > 0

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
                    "cooldown_remaining_seconds": self._provider_cooldown_remaining(provider.provider_id),
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
                    if self._uses_responses_api(provider):
                        result = await self._create_via_responses(client, request_kwargs)
                    else:
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
                    if self._is_retryable_error(exc) and attempt < self.settings.model_rate_limit_retry_attempts:
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
    def _uses_responses_api(provider: ModelProviderConfig) -> bool:
        lowered = provider.base_url.lower()
        return "/codex/" in lowered or provider.provider_id == "rightcodes"

    async def _create_via_responses(self, client: AsyncOpenAI, kwargs: dict[str, Any]) -> Any:
        if not hasattr(client, "responses"):
            return await client.chat.completions.create(**kwargs)
        response_kwargs = self._responses_kwargs_from_chat(kwargs)
        if kwargs.get("stream"):
            stream = await client.responses.create(stream=True, **response_kwargs)
            return ResponsesToChatCompletionStream(stream)
        response = await client.responses.create(**response_kwargs)
        return self._responses_response_to_chat_completion(response)

    def _responses_kwargs_from_chat(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        messages = list(kwargs.get("messages") or [])
        tools = kwargs.get("tools") or []
        system_prompt = ""
        if messages and messages[0].get("role") == "system":
            system_prompt = str(messages[0].get("content") or "")
            messages = messages[1:]
        return {
            "model": kwargs["model"],
            "instructions": system_prompt or None,
            "input": self._chat_messages_to_responses_input(messages),
            "tools": self._chat_tools_to_responses_tools(tools),
            "tool_choice": kwargs.get("tool_choice", "auto"),
            "temperature": kwargs.get("temperature"),
            "prompt_cache_key": kwargs.get("prompt_cache_key"),
            "prompt_cache_retention": kwargs.get("prompt_cache_retention"),
        }

    @staticmethod
    def _chat_tools_to_responses_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for tool in tools:
            if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
                function = tool["function"]
                converted.append(
                    {
                        "type": "function",
                        "name": function.get("name", ""),
                        "description": function.get("description"),
                        "parameters": function.get("parameters", {}),
                        "strict": False,
                    }
                )
            else:
                converted.append(tool)
        return converted

    @staticmethod
    def _chat_messages_to_responses_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index, message in enumerate(messages):
            role = str(message.get("role") or "")
            content = str(message.get("content") or "")
            if role == "user":
                items.append(
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": content}],
                    }
                )
                continue
            if role == "assistant":
                if content:
                    items.append(
                        {
                            "type": "message",
                            "id": f"assistant-{index}",
                            "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": content, "annotations": [], "logprobs": []}],
                        }
                    )
                for tool_call in list(message.get("tool_calls") or []):
                    function = tool_call.get("function", {})
                    call_id = str(tool_call.get("id") or "")
                    items.append(
                        {
                            "type": "function_call",
                            "id": call_id,
                            "call_id": call_id,
                            "name": function.get("name", ""),
                            "arguments": function.get("arguments", ""),
                            "status": "completed",
                        }
                    )
                continue
            if role == "tool":
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": str(message.get("tool_call_id") or ""),
                        "output": content,
                        "status": "completed",
                    }
                )
        return items

    @staticmethod
    def _responses_response_to_chat_completion(response: Any) -> Any:
        text_parts: list[str] = []
        tool_calls: list[Any] = []
        for item in list(getattr(response, "output", []) or []):
            item_type = getattr(item, "type", None)
            if item_type == "message":
                for content in list(getattr(item, "content", []) or []):
                    if getattr(content, "type", None) == "output_text":
                        text_parts.append(str(getattr(content, "text", "")))
            elif item_type == "function_call":
                tool_calls.append(
                    SimpleNamespace(
                        id=getattr(item, "call_id", None) or getattr(item, "id", ""),
                        function=SimpleNamespace(
                            name=getattr(item, "name", ""),
                            arguments=getattr(item, "arguments", ""),
                        ),
                    )
                )
        message = SimpleNamespace(
            content="".join(text_parts),
            tool_calls=tool_calls or None,
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=getattr(response, "usage", None),
            response_id=getattr(response, "id", None),
        )

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return any(
            marker in text
            for marker in (
                "rate_limit_exceeded",
                "429",
                "too many requests",
                "timeout",
                "timed out",
                "connection refused",
                "connection error",
                "connect error",
                "failed to connect",
                "server disconnected",
                "temporary failure",
                "temporarily unavailable",
                "service unavailable",
                "name or service not known",
                "nodename nor servname provided",
                "connection reset by peer",
                "remote protocol error",
                "apiconnectionerror",
                "apitimeouterror",
            )
        )


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


class ResponsesToChatCompletionStream:
    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self._saw_tool_arg_delta: set[int] = set()

    def __aiter__(self) -> "ResponsesToChatCompletionStream":
        return self

    async def __anext__(self) -> Any:
        async for event in self.stream:
            event_type = getattr(event, "type", "")
            if event_type == "response.output_text.delta":
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(content=getattr(event, "delta", ""), tool_calls=None)
                        )
                    ]
                )
            if event_type == "response.function_call_arguments.delta":
                output_index = int(getattr(event, "output_index", 0) or 0)
                self._saw_tool_arg_delta.add(output_index)
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(
                                content=None,
                                tool_calls=[
                                    SimpleNamespace(
                                        index=output_index,
                                        id=None,
                                        function=SimpleNamespace(name=None, arguments=getattr(event, "delta", "")),
                                    )
                                ],
                            )
                        )
                    ]
                )
            if event_type == "response.output_item.done" and getattr(getattr(event, "item", None), "type", None) == "function_call":
                item = event.item
                output_index = int(getattr(event, "output_index", 0) or 0)
                arguments = ""
                if output_index not in self._saw_tool_arg_delta:
                    arguments = getattr(item, "arguments", "")
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(
                                content=None,
                                tool_calls=[
                                    SimpleNamespace(
                                        index=output_index,
                                        id=getattr(item, "call_id", None) or getattr(item, "id", ""),
                                        function=SimpleNamespace(
                                            name=getattr(item, "name", ""),
                                            arguments=arguments,
                                        ),
                                    )
                                ],
                            )
                        )
                    ]
                )
        raise StopAsyncIteration


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
