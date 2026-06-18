from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.ai import Message, ToolSchema, LLMResponse


class LLMProvider(ABC):
    """A chat-with-tools backend. Adapters translate the normalized Message /
    ToolSchema / LLMResponse types to and from a specific provider's wire format."""

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
    ) -> LLMResponse: ...
