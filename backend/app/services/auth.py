from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.db.models import User
from app.schemas.auth import LoginRequest, LoginResponse, LoginUser
from app.services.supabase import get_public_supabase_client


async def login_with_password(payload: LoginRequest, session: AsyncSession) -> LoginResponse:
    try:
        auth_response = get_public_supabase_client().auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception as exc:
        raise ApplicationError(status_code=401, code="invalid_credentials", message="Login failed.") from exc

    auth_session = getattr(auth_response, "session", None)
    auth_user = getattr(auth_response, "user", None)
    if auth_session is None or auth_user is None:
        raise ApplicationError(status_code=401, code="invalid_credentials", message="Login failed.")

    user = (
        await session.execute(select(User).where(User.id == auth_user.id))
    ).scalar_one_or_none()
    if user is None:
        raise ApplicationError(status_code=403, code="profile_not_found", message="User profile not provisioned.")

    return LoginResponse(
        access_token=auth_session.access_token,
        refresh_token=auth_session.refresh_token,
        expires_in=auth_session.expires_in,
        user=LoginUser(id=user.id, role=user.role, department_id=user.department_id),
    )