from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse, summary="Health check")
def read_health() -> HealthResponse:
    return HealthResponse(status="ok")
