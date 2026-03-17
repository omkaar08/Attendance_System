from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.core.security import Principal, verify_supabase_jwt
from app.db.models import AppRole, Faculty, User
from app.db.session import get_db_session

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApplicationError(status_code=401, code="missing_credentials", message="Missing bearer token.")

    claims = verify_supabase_jwt(credentials.credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise ApplicationError(status_code=401, code="invalid_token", message="Token is missing subject.")

    statement = (
        select(User, Faculty.id.label("faculty_id"))
        .outerjoin(Faculty, Faculty.user_id == User.id)
        .where(User.id == UUID(user_id))
    )
    record = (await session.execute(statement)).one_or_none()
    if record is None:
        raise ApplicationError(status_code=403, code="profile_not_found", message="User profile not found.")

    user, faculty_id = record
    if not user.is_active:
        raise ApplicationError(status_code=403, code="user_inactive", message="User account is inactive.")

    return Principal(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        department_id=user.department_id,
        faculty_id=faculty_id,
        claims=claims,
    )


def require_roles(*roles: AppRole) -> Callable[[Principal], Principal]:
    def dependency(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if principal.role not in roles:
            raise ApplicationError(status_code=403, code="insufficient_role", message="Operation not permitted.")
        return principal

    return dependency