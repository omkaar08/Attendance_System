from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.analytics import AnalyticsOverviewResponse, SubjectAttendanceResponse
from app.services.analytics import get_analytics_overview, get_subject_attendance_stats

router = APIRouter()


@router.get("/overview")
async def overview(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    department_id: Annotated[UUID | None, Query()] = None,
    subject_id: Annotated[UUID | None, Query()] = None,
) -> AnalyticsOverviewResponse:
    return await get_analytics_overview(
        session=session,
        principal=principal,
        department_id=department_id,
        subject_id=subject_id,
    )


@router.get("/subject-attendance")
async def subject_attendance_stats(
    principal: Annotated[Principal, Depends(require_roles(AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    department_id: Annotated[UUID | None, Query()] = None,
) -> SubjectAttendanceResponse:
    return await get_subject_attendance_stats(
        session=session,
        principal=principal,
        department_id=department_id,
    )