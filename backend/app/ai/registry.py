from __future__ import annotations

from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.ai.base import LLMProvider
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.openai_provider import OpenAIProvider


@dataclass
class ProviderInfo:
    name: str
    label: str
    available: bool
    models: list[dict]   # [{id, label, default}]
    default_model: str | None


# Substrings that mark an OpenAI model id as NOT a chat/completions model.
_OPENAI_EXCLUDE = (
    "embedding", "whisper", "tts", "audio", "dall-e", "image", "moderation",
    "realtime", "transcribe", "search", "davinci", "babbage", "codex",
)


def _is_openai_chat_model(mid: str) -> bool:
    low = mid.lower()
    if any(bad in low for bad in _OPENAI_EXCLUDE):
        return False
    # chat families: gpt-*, and reasoning models o1/o3/o4-*
    return low.startswith("gpt") or (len(low) > 1 and low[0] == "o" and low[1].isdigit())


def _mark_default(models: list[dict], preferred: str | None) -> tuple[list[dict], str | None]:
    """Flag the preferred model as default; fall back to the first model."""
    if not models:
        return [], None
    ids = [m["id"] for m in models]
    default = preferred if preferred in ids else ids[0]
    return (
        [{**m, "default": m["id"] == default} for m in models],
        default,
    )


async def _anthropic_models(api_key: str) -> list[dict]:
    # The installed SDK has no `models` resource, so hit the REST endpoint directly.
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            "https://api.anthropic.com/v1/models",
            params={"limit": 100},
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
    return [
        {"id": m["id"], "label": m.get("display_name") or m["id"]}
        for m in data
        if m.get("id")
    ]


async def _openai_models(api_key: str) -> list[dict]:
    client = AsyncOpenAI(api_key=api_key)
    page = await client.models.list()
    models = [
        {"id": m.id, "label": m.id}
        for m in page.data
        if _is_openai_chat_model(m.id)
    ]
    models.sort(key=lambda m: m["id"])
    return models


async def list_providers() -> list[ProviderInfo]:
    # Anthropic
    anthropic_available = bool(settings.anthropic_api_key)
    anthropic_models: list[dict] = []
    if anthropic_available:
        try:
            anthropic_models = await _anthropic_models(settings.anthropic_api_key)
        except Exception:
            anthropic_models = []
    if not anthropic_models:
        # fall back to the configured defaults so the UI still has options
        anthropic_models = [
            {"id": settings.anthropic_model, "label": settings.anthropic_model},
            {"id": settings.anthropic_model_fast, "label": settings.anthropic_model_fast},
        ]
    anthropic_models, anthropic_default = _mark_default(anthropic_models, settings.anthropic_model)

    # OpenAI
    openai_available = bool(settings.openai_api_key)
    openai_models: list[dict] = []
    if openai_available:
        try:
            openai_models = await _openai_models(settings.openai_api_key)
        except Exception:
            openai_models = []
    if not openai_models:
        openai_models = [
            {"id": settings.openai_model, "label": settings.openai_model},
            {"id": settings.openai_model_fast, "label": settings.openai_model_fast},
        ]
    openai_models, openai_default = _mark_default(openai_models, settings.openai_model)

    return [
        ProviderInfo(
            name="anthropic",
            label="Anthropic (Claude)",
            available=anthropic_available,
            models=anthropic_models,
            default_model=anthropic_default,
        ),
        ProviderInfo(
            name="openai",
            label="OpenAI",
            available=openai_available,
            models=openai_models,
            default_model=openai_default,
        ),
    ]


def get_provider(name: str) -> LLMProvider:
    if name == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        return AnthropicProvider(settings.anthropic_api_key)
    if name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        return OpenAIProvider(settings.openai_api_key)
    raise ValueError(f"unknown provider '{name}'")
