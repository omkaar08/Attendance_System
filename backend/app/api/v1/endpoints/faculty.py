from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.faculty import SubjectListResponse
from app.services.subjects import list_faculty_subjects

router = APIRouter()


@router.get("/subjects")
async def faculty_subjects(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    semester: Annotated[int | None, Query(ge=1, le=12)] = None,
    section: Annotated[str | None, Query(max_length=20)] = None,
    active_only: Annotated[bool, Query()] = True,
) -> SubjectListResponse:
    return await list_faculty_subjects(
        session=session,
        principal=principal,
        semester=semester,
        section=section,
        active_only=active_only,
    )