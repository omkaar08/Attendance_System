from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.students import (
    FaceUploadRequest,
    FaceUploadResponse,
    StudentListResponse,
    StudentRegisterRequest,
    StudentResponse,
)
from app.services.storage import create_face_upload_url
from app.services.students import list_students, register_student

router = APIRouter()


@router.post("/register")
async def create_student(
    payload: StudentRegisterRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StudentResponse:
    return await register_student(session=session, principal=principal, payload=payload)


@router.get("")
async def get_students(
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    department_id: Annotated[UUID | None, Query()] = None,
    semester: Annotated[int | None, Query(ge=1, le=12)] = None,
    section: Annotated[str | None, Query(max_length=20)] = None,
    subject_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> StudentListResponse:
    return await list_students(
        session=session,
        principal=principal,
        department_id=department_id,
        semester=semester,
        section=section,
        subject_id=subject_id,
        search=search,
        limit=limit,
    )


@router.post("/upload-face")
async def upload_face(
    payload: FaceUploadRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FaceUploadResponse:
    return await create_face_upload_url(session=session, principal=principal, payload=payload)


@router.post("/{student_id}/upload-face-url")
async def upload_face_alias(
    payload: FaceUploadRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    student_id: Annotated[UUID, Path()],
) -> FaceUploadResponse:
    resolved_payload = payload.model_copy(update={"student_id": student_id})
    return await create_face_upload_url(session=session, principal=principal, payload=resolved_payload)