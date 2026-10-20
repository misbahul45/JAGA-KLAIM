from fastapi import APIRouter

from app.api.routes import (
    audit_metrics,
    auth,
    claims,
    governance,
    investigations,
    review,
    sources,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(claims.router)
api_router.include_router(sources.router)
api_router.include_router(investigations.router)
api_router.include_router(review.router)
api_router.include_router(audit_metrics.router)
api_router.include_router(governance.router)
