from fastapi import APIRouter

from app.ai.registry import list_providers

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/providers")
async def providers():
    """
    List the LLM providers with their availability and models for the setup form.

    :return: One entry per provider with name, label, available, models and default_model.
    """
    return [
        {
            "name": p.name,
            "label": p.label,
            "available": p.available,
            "models": p.models,
            "default_model": p.default_model,
        }
        for p in await list_providers()
    ]
