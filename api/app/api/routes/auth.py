import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import PrincipalDep, require
from app.api.schemas.auth import (
    LoginRequest,
    PasswordChange,
    PasswordReset,
    PrincipalResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.api.schemas.common import Message
from app.core.config import get_settings
from app.db.session import SessionDep
from app.domain.permissions import Permission
from app.services import auth as auth_service
from app.services.auth import Principal

router = APIRouter(prefix="/v1", tags=["auth"])


@router.post("/auth/login", response_model=PrincipalResponse)
def login(body: LoginRequest, response: Response, session: SessionDep) -> PrincipalResponse:
    settings = get_settings()
    token, expires_at, principal = auth_service.login(
        session, email=body.email, password=body.password, settings=settings
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        expires=expires_at,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    return PrincipalResponse.from_principal(principal)


@router.post("/auth/logout", response_model=Message)
def logout(response: Response, session: SessionDep, principal: PrincipalDep) -> Message:
    auth_service.logout(session, principal)
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return Message(message="Anda telah keluar")


@router.post("/auth/password", response_model=Message)
def change_password(
    body: PasswordChange, session: SessionDep, principal: PrincipalDep
) -> Message:
    auth_service.change_password(
        session,
        principal,
        current_password=body.current_password,
        new_password=body.new_password,
        settings=get_settings(),
    )
    return Message(message="Kata sandi diperbarui. Sesi di perangkat lain telah diakhiri.")


@router.get("/auth/me", response_model=PrincipalResponse)
def me(principal: PrincipalDep) -> PrincipalResponse:
    return PrincipalResponse.from_principal(principal)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.USER_MANAGE))],
) -> list[UserResponse]:
    return [
        UserResponse.model_validate(u, from_attributes=True)
        for u in auth_service.list_users(session, principal)
    ]


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreate,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.USER_MANAGE))],
) -> UserResponse:
    user = auth_service.create_user(
        session,
        actor=principal,
        name=body.name,
        email=body.email,
        role=body.role,
        password=body.password,
    )
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/users/{user_id}/password", response_model=Message)
def reset_user_password(
    user_id: uuid.UUID,
    body: PasswordReset,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.USER_MANAGE))],
) -> Message:
    auth_service.reset_password(
        session, actor=principal, user_id=user_id, new_password=body.new_password
    )
    return Message(message="Kata sandi pengguna diatur ulang. Seluruh sesinya telah diakhiri.")


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require(Permission.USER_MANAGE))],
) -> UserResponse:
    user = auth_service.update_user(
        session,
        actor=principal,
        user_id=user_id,
        role=body.role,
        is_active=body.is_active,
    )
    return UserResponse.model_validate(user, from_attributes=True)
