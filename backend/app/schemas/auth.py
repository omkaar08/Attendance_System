from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.db.models import AppRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginUser(BaseModel):
    id: UUID
    role: AppRole
    department_id: UUID | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: LoginUser


class CurrentUserResponse(BaseModel):
    id: UUID
    full_name: str | None = None
    email: EmailStr
    role: AppRole
    department_id: UUID | None = None
    faculty_profile_id: UUID | None = None