from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.ai import Message, ToolSchema, LLMResponse


class LLMProvider(ABC):
    """
    A chat-with-tools backend. Adapters translate the normalized Message,
    ToolSchema and LLMResponse types to and from a provider's wire format.
    """

    name: str

    @abstractmethod
    async def chat(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolSchema],
        model: str,
        max_tokens: int,
    ) -> LLMResponse:
        """
        Send one chat turn with tools to the provider.

        :param system: The system prompt.
        :param messages: The conversation so far in normalized form.
        :param tools: The tools the model may call.
        :param model: The provider-specific model id.
        :param max_tokens: The upper bound for generated tokens.
        :return: The assistant message, the normalized stop reason and token usage.
        """
        ...
