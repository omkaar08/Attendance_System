from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.reports import (
    DailyReportResponse,
    DepartmentReportResponse,
    MonthlyReportResponse,
    StudentReportResponse,
    SubjectReportResponse,
)
from app.services.reports import (
    daily_report,
    department_report,
    monthly_report,
    student_report,
    subject_report,
)

router = APIRouter()


@router.get("/daily", summary="Attendance totals grouped by date")
async def get_daily_report(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    subject_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
) -> DailyReportResponse:
    return await daily_report(
        session=session,
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        subject_id=subject_id,
        department_id=department_id,
    )


@router.get("/monthly", summary="Attendance totals grouped by month")
async def get_monthly_report(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    subject_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
) -> MonthlyReportResponse:
    return await monthly_report(
        session=session,
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        subject_id=subject_id,
        department_id=department_id,
    )


@router.get("/subject", summary="Per-subject attendance summary")
async def get_subject_report(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    subject_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
) -> SubjectReportResponse:
    return await subject_report(
        session=session,
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        subject_id=subject_id,
        department_id=department_id,
    )


@router.get("/student", summary="Per-student attendance summary per subject")
async def get_student_report(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    subject_id: Annotated[UUID | None, Query()] = None,
    student_id: Annotated[UUID | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
) -> StudentReportResponse:
    return await student_report(
        session=session,
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        subject_id=subject_id,
        student_id=student_id,
        department_id=department_id,
    )


@router.get("/department", summary="Department-wise attendance performance (admin / HOD)")
async def get_department_report(
    principal: Annotated[Principal, Depends(require_roles(AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    department_id: Annotated[UUID | None, Query()] = None,
) -> DepartmentReportResponse:
    return await department_report(
        session=session,
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
    )
