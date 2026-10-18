from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.redis import RedisDep
from app.db.session import SessionDep

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(session: SessionDep, redis: RedisDep) -> dict[str, str]:
    checks = {"database": "ok", "redis": "ok"}
    try:
        session.exec(select(1)).one()
    except Exception:
        checks["database"] = "unavailable"
    try:
        redis.ping()
    except Exception:
        checks["redis"] = "unavailable"
    if "unavailable" in checks.values():
        raise HTTPException(status_code=503, detail=checks)
    return {"status": "ok", **checks}
