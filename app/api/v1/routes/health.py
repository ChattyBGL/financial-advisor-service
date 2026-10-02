from fastapi import APIRouter, Response, status

from app.api.deps import DBClientDep, SettingsDep
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    """Liveness: the process is up. Does not touch external dependencies."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
def ready(db: DBClientDep, response: Response) -> ReadinessResponse:
    """Readiness: the service can reach Postgres. Returns 503 if not."""
    db_ok = db.ping()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ok" if db_ok else "degraded",
        database="up" if db_ok else "down",
    )
