from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.middleware import install_origin_guard
from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.redis import get_redis
from app.db.session import get_engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    get_redis().close()
    get_engine().dispose()


settings = get_settings()

app = FastAPI(
    title="JAGA-KLAIM API",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

register_error_handlers(app)
install_origin_guard(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)

app.include_router(health_router)
app.include_router(api_router)
