from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.ai.base import LLMProvider
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.openai_provider import OpenAIProvider


@dataclass
class ProviderInfo:
    """What the setup form needs to know about one LLM provider."""

    name: str
    label: str
    available: bool
    models: list[dict]   # [{id, label, default}]
    default_model: str | None


# Substrings that mark an OpenAI model id as not being a chat model.
_OPENAI_EXCLUDE = (
    "embedding", "whisper", "tts", "audio", "dall-e", "image", "moderation",
    "realtime", "transcribe", "search", "davinci", "babbage", "codex",
)


def _is_openai_chat_model(mid: str) -> bool:
    """
    Decide whether an OpenAI model id is a chat model (gpt-* or reasoning models o<n>-*).

    :param mid: The model id.
    :return: True if the model can be used for chat completions.
    """
    low = mid.lower()
    if any(bad in low for bad in _OPENAI_EXCLUDE):
        return False
    return low.startswith("gpt") or (len(low) > 1 and low[0] == "o" and low[1].isdigit())


def _mark_default(models: list[dict], preferred: str | None) -> tuple[list[dict], str | None]:
    """
    Flag the preferred model as default, or the first model if it is not in the list.

    :param models: The models as {id, label} dicts.
    :param preferred: The id of the preferred model.
    :return: The models with a "default" flag, and the id of the default model.
    """
    if not models:
        return [], None
    ids = [m["id"] for m in models]
    default = preferred if preferred in ids else ids[0]
    return (
        [{**m, "default": m["id"] == default} for m in models],
        default,
    )


async def _anthropic_models(api_key: str) -> list[dict]:
    """
    Fetch the models available to an Anthropic API key.

    The installed SDK has no models resource, so the REST endpoint is called directly.

    :param api_key: The Anthropic API key.
    :return: The models as {id, label} dicts.
    """
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
    """
    Fetch the chat models available to an OpenAI API key.

    :param api_key: The OpenAI API key.
    :return: The chat models as {id, label} dicts, sorted by id.
    """
    client = AsyncOpenAI(api_key=api_key)
    page = await client.models.list()
    models = [
        {"id": m.id, "label": m.id}
        for m in page.data
        if _is_openai_chat_model(m.id)
    ]
    models.sort(key=lambda m: m["id"])
    return models


def _cluster_http_client() -> httpx.AsyncClient | None:
    """
    Build the HTTP client with the TLS setup for the private cluster endpoint.

    A self-signed certificate is trusted by naming it as the only anchor, so the
    connection stays protected against a man in the middle. The timeouts match the
    SDK default, since passing a client of our own replaces it.

    :return: The configured client, or None to use the SDK default.
    :raises ValueError: If CLUSTER_CA_BUNDLE does not point to a file.
    """
    timeout = httpx.Timeout(timeout=600.0, connect=5.0)
    if settings.cluster_ca_bundle:
        path = Path(settings.cluster_ca_bundle)
        if not path.is_file():
            raise ValueError(f"CLUSTER_CA_BUNDLE is not a file: {path}")
        return httpx.AsyncClient(verify=str(path), timeout=timeout)
    if not settings.cluster_verify_ssl:
        return httpx.AsyncClient(verify=False, timeout=timeout)
    return None


async def _cluster_models() -> list[dict]:
    """
    Fetch all models the cluster gateway offers.

    Unlike for OpenAI, the list is not filtered: _is_openai_chat_model only accepts
    gpt-* and o<n>-* and would drop ids such as "zai-org/GLM-5.3" or "ultrabrain".

    :return: The models as {id, label} dicts, sorted by id.
    """
    client = AsyncOpenAI(
        api_key=settings.cluster_api_key or "not-needed",
        base_url=settings.cluster_base_url,
        http_client=_cluster_http_client(),
        timeout=20,
    )
    page = await client.models.list()
    models = [{"id": m.id, "label": m.id} for m in page.data if m.id]
    models.sort(key=lambda m: m["id"].lower())
    return models


async def list_providers() -> list[ProviderInfo]:
    """
    Describe every provider with its availability and models.

    Models are fetched live. If that fails, the configured models are offered instead.

    :return: The Anthropic, OpenAI and cluster provider info.
    """
    anthropic_available = bool(settings.anthropic_api_key)
    anthropic_models: list[dict] = []
    if anthropic_available:
        try:
            anthropic_models = await _anthropic_models(settings.anthropic_api_key)
        except Exception:
            anthropic_models = []
    if not anthropic_models:
        anthropic_models = [
            {"id": settings.anthropic_model, "label": settings.anthropic_model},
            {"id": settings.anthropic_model_fast, "label": settings.anthropic_model_fast},
        ]
    anthropic_models, anthropic_default = _mark_default(anthropic_models, settings.anthropic_model)

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

    cluster_available = bool(settings.cluster_base_url)
    cluster_models: list[dict] = []
    if cluster_available:
        try:
            cluster_models = await _cluster_models()
        except Exception:
            cluster_models = []
    if not cluster_models:
        cluster_models = [{"id": settings.cluster_model, "label": settings.cluster_model}]
        if settings.cluster_model_fast:
            cluster_models.append({
                "id": settings.cluster_model_fast,
                "label": settings.cluster_model_fast,
            })
    cluster_models, cluster_default = _mark_default(cluster_models, settings.cluster_model)

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
        ProviderInfo(
            name="cluster",
            label=settings.cluster_label,
            available=cluster_available,
            models=cluster_models,
            default_model=cluster_default,
        ),
    ]


def get_provider(name: str) -> LLMProvider:
    """
    Create the provider adapter for a provider name.

    :param name: "anthropic", "openai" or "cluster".
    :return: The provider adapter.
    :raises ValueError: If the provider is unknown or not configured.
    """
    if name == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        return AnthropicProvider(settings.anthropic_api_key)
    if name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        return OpenAIProvider(settings.openai_api_key)
    if name == "cluster":
        if not settings.cluster_base_url:
            raise ValueError("CLUSTER_BASE_URL is not configured")
        # The gateway needs no key of its own on some installations, but the
        # SDK insists on a non-empty value.
        return OpenAIProvider(
            settings.cluster_api_key or "not-needed",
            base_url=settings.cluster_base_url,
            http_client=_cluster_http_client(),
            blank_assistant_content=True,
            name="cluster",
        )
    raise ValueError(f"unknown provider '{name}'")
