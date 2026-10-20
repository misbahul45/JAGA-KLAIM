from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import error_body

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def install_origin_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def origin_guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in UNSAFE_METHODS:
            settings = get_settings()
            origin = request.headers.get("origin")
            has_session_cookie = settings.session_cookie_name in request.cookies
            rejected = (origin is not None and origin not in settings.cors_origins) or (
                origin is None and has_session_cookie
            )
            if rejected:
                return JSONResponse(
                    status_code=403,
                    content=error_body(
                        "origin_not_allowed", "Asal permintaan tidak diizinkan"
                    ),
                )
        return await call_next(request)
