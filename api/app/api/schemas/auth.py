import uuid

from pydantic import BaseModel, EmailStr, Field

from app.domain.enums import Role
from app.services.auth import Principal


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=1, max_length=256)


class PrincipalResponse(BaseModel):
    user_id: uuid.UUID
    faskes_id: uuid.UUID
    name: str
    email: str
    role: Role
    permissions: list[str]

    @classmethod
    def from_principal(cls, principal: Principal) -> "PrincipalResponse":
        return cls(
            user_id=principal.user_id,
            faskes_id=principal.faskes_id,
            name=principal.name,
            email=principal.email,
            role=principal.role,
            permissions=sorted(p.value for p in principal.permissions),
        )


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: Role
    password: str = Field(min_length=1, max_length=256)


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: Role
    is_active: bool
