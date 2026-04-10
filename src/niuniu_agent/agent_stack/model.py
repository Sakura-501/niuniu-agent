from __future__ import annotations

from openai import AsyncOpenAI

from agents import set_default_openai_client, set_tracing_disabled
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from niuniu_agent.config import AgentSettings


def build_async_openai_client(settings: AgentSettings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.model_api_key,
        base_url=settings.model_base_url,
    )


def build_chat_completions_model(settings: AgentSettings) -> OpenAIChatCompletionsModel:
    client = build_async_openai_client(settings)
    set_default_openai_client(client, use_for_tracing=False)
    set_tracing_disabled(True)
    return OpenAIChatCompletionsModel(model=settings.model, openai_client=client)
