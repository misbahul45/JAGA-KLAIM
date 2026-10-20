from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.errors import forbidden, unauthorized
from app.db.session import SessionDep
from app.domain.permissions import Permission
from app.services.auth import Principal, resolve_session


def get_principal(request: Request, session: SessionDep) -> Principal:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise unauthorized()
    principal = resolve_session(session, token)
    if principal is None:
        raise unauthorized()
    return principal


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require(*permissions: Permission) -> Callable[[Principal], Principal]:
    def dependency(principal: PrincipalDep) -> Principal:
        missing = [p for p in permissions if p not in principal.permissions]
        if missing:
            raise forbidden()
        return principal

    return dependency
