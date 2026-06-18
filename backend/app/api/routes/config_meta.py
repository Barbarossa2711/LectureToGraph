from fastapi import APIRouter

from app.ai.registry import list_providers

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/providers")
async def providers():
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
