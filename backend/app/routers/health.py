from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check the health of the application",
)
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "DevSelect API",
        "environment": settings.FRONTEND_URL,
    }