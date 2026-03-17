from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_principal
from app.core.limiter import limiter
from app.core.security import Principal
from app.db.session import get_db_session
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.services.auth import login_with_password

router = APIRouter()


@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,  # required by slowapi for IP-based limiting
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
    return await login_with_password(payload, session)


@router.get("/me")
async def me(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=principal.user_id,
        full_name=principal.full_name,
        email=principal.email,
        role=principal.role,
        department_id=principal.department_id,
        faculty_profile_id=principal.faculty_id,
    )