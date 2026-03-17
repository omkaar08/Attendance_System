from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.subjects import SubjectAssignmentRequest, SubjectCreateRequest, SubjectResponse
from app.services.subjects import assign_subject_faculty, create_subject_for_hod

router = APIRouter()


@router.post("")
async def create_subject(
    payload: SubjectCreateRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.HOD))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubjectResponse:
    return await create_subject_for_hod(session=session, principal=principal, payload=payload)


@router.post("/{subject_id}/assign-faculty")
async def assign_faculty(
    payload: SubjectAssignmentRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.HOD))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    subject_id: Annotated[UUID, Path()],
) -> SubjectResponse:
    return await assign_subject_faculty(
        session=session,
        principal=principal,
        subject_id=subject_id,
        faculty_id=payload.faculty_id,
    )