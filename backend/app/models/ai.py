"""Provider-agnostic, persistable representation of an agent conversation.

The internal shape is intentionally Anthropic-flavoured (a list of typed content
blocks, with tool_use / tool_result blocks) because it maps cleanly onto both the
Anthropic and OpenAI wire formats. Each provider adapter converts to/from these
types; the agent loop only ever sees these.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    media_type: str
    data_b64: str


class ToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict


class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    # tool results may carry text and/or images (e.g. read_pdf)
    content: list[Union["TextBlock", "ImageBlock"]] = Field(default_factory=list)
    is_error: bool = False


ContentBlock = Annotated[
    Union[TextBlock, ImageBlock, ToolUseBlock, ToolResultBlock],
    Field(discriminator="type"),
]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: list[ContentBlock]

    def text_parts(self) -> str:
        return "\n".join(b.text for b in self.content if isinstance(b, TextBlock))

    def tool_uses(self) -> list[ToolUseBlock]:
        return [b for b in self.content if isinstance(b, ToolUseBlock)]


class ToolSchema(BaseModel):
    name: str
    description: str
    input_schema: dict


class LLMResponse(BaseModel):
    assistant_message: Message
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "other"]
    usage: dict = Field(default_factory=dict)
