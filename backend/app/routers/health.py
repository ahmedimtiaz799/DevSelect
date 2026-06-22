from fastapi import APIRouter

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
    }
