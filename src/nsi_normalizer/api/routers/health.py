from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"


@router.get("/live", response_model=HealthResponse, summary="Liveness probe")
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse, summary="Readiness probe")
async def readiness() -> HealthResponse:
    return HealthResponse(status="ok")
