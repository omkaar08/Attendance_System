from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.attendance import (
    AttendanceMarkRequest,
    AttendanceMarkResponse,
    AttendanceReportResponse,
    LowAttendanceAlertResponse,
)
from app.services.attendance import low_attendance_alerts, mark_attendance, report_attendance

router = APIRouter()


@router.post("/mark")
async def create_attendance(
    payload: AttendanceMarkRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AttendanceMarkResponse:
    return await mark_attendance(session=session, principal=principal, payload=payload)


@router.get("/report")
async def attendance_report(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    subject_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
    student_id: Annotated[UUID | None, Query()] = None,
    section: Annotated[str | None, Query(max_length=20)] = None,
) -> AttendanceReportResponse:
    return await report_attendance(
        session=session,
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        subject_id=subject_id,
        department_id=department_id,
        student_id=student_id,
        section=section,
    )


@router.get("/alerts/low")
async def attendance_low_alerts(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    threshold_percent: Annotated[float, Query(ge=1, le=100)] = 75,
    min_sessions: Annotated[int, Query(ge=1, le=100)] = 3,
    subject_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
) -> LowAttendanceAlertResponse:
    return await low_attendance_alerts(
        session=session,
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        threshold_percent=threshold_percent,
        min_sessions=min_sessions,
        subject_id=subject_id,
        department_id=department_id,
    )