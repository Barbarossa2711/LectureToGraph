from __future__ import annotations

import json

import httpx
from openai import AsyncOpenAI

from app.ai.base import LLMProvider
from app.models.ai import (
    Message, ToolSchema, LLMResponse,
    TextBlock, ImageBlock, ToolUseBlock, ToolResultBlock,
)


def _image_part(block: ImageBlock) -> dict:
    """
    Convert an image block into an OpenAI image_url content part.

    :param block: The image block.
    :return: The content part with the image as a data URL.
    """
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{block.media_type};base64,{block.data_b64}"},
    }


def _to_openai_messages(
    system: str,
    messages: list[Message],
    *,
    blank_assistant_content: bool = False,
) -> list[dict]:
    """
    Flatten normalized messages into OpenAI chat messages.

    Assistant text and tool_use blocks become one assistant message with tool_calls.
    Each tool_result becomes one role "tool" message with text only. Images from a
    tool result follow as a role "user" message, since the tool role accepts no images.

    :param system: The system prompt, sent as the first message.
    :param messages: The conversation in normalized form.
    :param blank_assistant_content: Write "" instead of null for an assistant message
        that carries only tool_calls. api.openai.com accepts null, but an OpenWebUI
        gateway measures the field's length and answers
        400 "object of type 'NoneType' has no len()".
    :return: The messages in the OpenAI chat completions format.
    """
    out: list[dict] = [{"role": "system", "content": system}]

    for m in messages:
        if m.role == "assistant":
            text = m.text_parts()
            tool_calls = [
                {
                    "id": b.id,
                    "type": "function",
                    "function": {"name": b.name, "arguments": json.dumps(b.input)},
                }
                for b in m.content if isinstance(b, ToolUseBlock)
            ]
            msg: dict = {
                "role": "assistant",
                "content": text or ("" if blank_assistant_content else None),
            }
            if tool_calls:
                msg["tool_calls"] = tool_calls
            out.append(msg)
            continue

        plain_parts: list[dict] = []
        deferred_images: list[dict] = []
        for b in m.content:
            if isinstance(b, ToolResultBlock):
                texts = [p.text for p in b.content if isinstance(p, TextBlock)]
                imgs = [p for p in b.content if isinstance(p, ImageBlock)]
                out.append({
                    "role": "tool",
                    "tool_call_id": b.tool_use_id,
                    "content": ("\n".join(texts) or ("[error]" if b.is_error else "[ok]")),
                })
                if imgs:
                    deferred_images.append({
                        "type": "text",
                        "text": f"Images returned by tool call {b.tool_use_id}:",
                    })
                    deferred_images.extend(_image_part(p) for p in imgs)
            elif isinstance(b, TextBlock):
                plain_parts.append({"type": "text", "text": b.text})
            elif isinstance(b, ImageBlock):
                plain_parts.append(_image_part(b))

        parts = plain_parts + deferred_images
        if parts:
            out.append({"role": "user", "content": parts})

    return out


class OpenAIProvider(LLMProvider):
    """Adapter for api.openai.com and for any OpenAI-compatible endpoint."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        blank_assistant_content: bool = False,
        name: str | None = None,
    ):
        """
        Create the OpenAI client. With the defaults it talks to api.openai.com.

        :param api_key: The API key of the endpoint.
        :param base_url: The base URL of an OpenAI-compatible endpoint, or None for api.openai.com.
        :param http_client: A preconfigured HTTP client, e.g. to trust a self-signed certificate.
        :param blank_assistant_content: Send "" instead of null as content of an assistant
            message with only tool calls, as required by OpenWebUI gateways.
        :param name: The provider name to report, or None for "openai".
        """
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if http_client is not None:
            kwargs["http_client"] = http_client
        self._client = AsyncOpenAI(**kwargs)
        self._blank_assistant_content = blank_assistant_content
        if name:
            self.name = name

    async def chat(self, *, system, messages, tools, model, max_tokens) -> LLMResponse:
        """
        Send one chat turn with tools to the chat completions endpoint.

        :param system: The system prompt.
        :param messages: The conversation so far in normalized form.
        :param tools: The tools the model may call.
        :param model: The model id of the endpoint.
        :param max_tokens: The upper bound for generated tokens.
        :return: The assistant message, the normalized stop reason and token usage.
        """
        resp = await self._client.chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=_to_openai_messages(
                system, messages,
                blank_assistant_content=self._blank_assistant_content,
            ),
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ],
        )

        choice = resp.choices[0]
        msg = choice.message
        out: list = []
        if msg.content:
            out.append(TextBlock(text=msg.content))
        for call in (msg.tool_calls or []):
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"__parse_error__": call.function.arguments}
            out.append(ToolUseBlock(id=call.id, name=call.function.name, input=args))

        stop = "tool_use" if choice.finish_reason == "tool_calls" else (
            "max_tokens" if choice.finish_reason == "length" else
            "end_turn" if choice.finish_reason == "stop" else "other"
        )
        usage = {}
        if resp.usage:
            usage = {
                "input_tokens": resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
        return LLMResponse(
            assistant_message=Message(role="assistant", content=out),
            stop_reason=stop,
            usage=usage,
        )
