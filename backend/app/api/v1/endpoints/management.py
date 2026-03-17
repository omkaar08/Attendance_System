from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.management import (
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentManagementSummary,
    FacultyCreateRequest,
    FacultyListResponse,
    FacultyManagementSummary,
    HodCreateRequest,
)
from app.services.management import (
    create_department,
    create_faculty_member,
    create_or_assign_hod,
    delete_department,
    list_departments,
    list_faculty_members,
)

router = APIRouter()


@router.get("/departments")
async def get_departments(
    principal: Annotated[Principal, Depends(require_roles(AppRole.ADMIN, AppRole.HOD))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DepartmentListResponse:
    return await list_departments(session=session, principal=principal)


@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department_endpoint(
    payload: DepartmentCreateRequest,
    _: Annotated[Principal, Depends(require_roles(AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DepartmentManagementSummary:
    return await create_department(session=session, payload=payload)


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department_endpoint(
    _: Annotated[Principal, Depends(require_roles(AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    department_id: Annotated[UUID, Path()],
) -> None:
    await delete_department(session=session, department_id=department_id)


@router.post("/departments/{department_id}/hod")
async def create_or_assign_hod_endpoint(
    payload: HodCreateRequest,
    _: Annotated[Principal, Depends(require_roles(AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    department_id: Annotated[UUID, Path()],
) -> DepartmentManagementSummary:
    return await create_or_assign_hod(session=session, department_id=department_id, payload=payload)


@router.get("/faculty")
async def get_faculty(
    principal: Annotated[Principal, Depends(require_roles(AppRole.ADMIN, AppRole.HOD))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    department_id: Annotated[UUID | None, Query()] = None,
) -> FacultyListResponse:
    return await list_faculty_members(
        session=session,
        principal=principal,
        department_id=department_id,
    )


@router.post("/faculty", status_code=status.HTTP_201_CREATED)
async def create_faculty_endpoint(
    payload: FacultyCreateRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.ADMIN, AppRole.HOD))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FacultyManagementSummary:
    return await create_faculty_member(session=session, principal=principal, payload=payload)
