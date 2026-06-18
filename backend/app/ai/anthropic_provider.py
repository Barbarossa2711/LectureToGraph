from __future__ import annotations

from anthropic import AsyncAnthropic

from app.ai.base import LLMProvider
from app.models.ai import (
    Message, ToolSchema, LLMResponse,
    TextBlock, ImageBlock, ToolUseBlock, ToolResultBlock,
)

_STOP_MAP = {
    "end_turn": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "stop_sequence": "end_turn",
}


def _block_to_anthropic(block) -> dict:
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ImageBlock):
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": block.media_type, "data": block.data_b64},
        }
    if isinstance(block, ToolUseBlock):
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    if isinstance(block, ToolResultBlock):
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "is_error": block.is_error,
            "content": [_block_to_anthropic(b) for b in block.content],
        }
    raise TypeError(f"unknown block {block!r}")


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str):
        self._client = AsyncAnthropic(api_key=api_key)

    async def chat(self, *, system, messages, tools, model, max_tokens) -> LLMResponse:
        resp = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=[
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ],
            messages=[
                {"role": m.role, "content": [_block_to_anthropic(b) for b in m.content]}
                for m in messages
            ],
        )

        out: list = []
        for block in resp.content:
            if block.type == "text":
                out.append(TextBlock(text=block.text))
            elif block.type == "tool_use":
                out.append(ToolUseBlock(id=block.id, name=block.name, input=dict(block.input)))
            # thinking blocks (if ever enabled) are ignored on purpose

        return LLMResponse(
            assistant_message=Message(role="assistant", content=out),
            stop_reason=_STOP_MAP.get(resp.stop_reason, "other"),
            usage={
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
        )
