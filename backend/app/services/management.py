from __future__ import annotations

from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import (
    AppRole,
    Attendance,
    AttendanceStatus,
    Department,
    Faculty,
    Student,
    Subject,
    User,
)
from app.schemas.management import (
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentManagementSummary,
    FacultyCreateRequest,
    FacultyListResponse,
    FacultyManagementSummary,
    HodCreateRequest,
)
from app.services.supabase_admin import SupabaseAuthAdminClient

DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE = "Department mapping not found."


def _normalize_auth_user_payload(payload: dict) -> dict:
    user_payload = payload.get("user") if isinstance(payload.get("user"), dict) else payload
    user_id = user_payload.get("id")
    if not user_id:
        raise ApplicationError(status_code=502, code="auth_user_missing", message="Auth user id is missing in response.")
    return user_payload


async def _ensure_auth_user(
    *,
    email: str,
    password: str,
    full_name: str,
    role: AppRole,
    department_id: UUID | None,
) -> UUID:
    settings = get_settings()
    client = SupabaseAuthAdminClient(
        base_url=str(settings.supabase_url),
        service_role_key=settings.supabase_service_role_key.get_secret_value(),
    )

    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"full_name": full_name},
        "app_metadata": {"role": role.value, "department_id": str(department_id) if department_id else None},
    }

    try:
        existing = await client.find_user_by_email(email)

        if existing is None:
            try:
                created = await client.create_user(payload)
                user_payload = _normalize_auth_user_payload(created)
                return UUID(str(user_payload["id"]))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 422:
                    raise ApplicationError(
                        status_code=502,
                        code="auth_user_create_failed",
                        message="Could not create authentication user.",
                    ) from exc
                existing = await client.find_user_by_email(email)
                if existing is None:
                    raise ApplicationError(
                        status_code=502,
                        code="auth_user_create_failed",
                        message="Could not create authentication user.",
                    ) from exc

        try:
            updated = await client.update_user(str(existing["id"]), payload)
        except httpx.HTTPStatusError as exc:
            raise ApplicationError(
                status_code=502,
                code="auth_user_update_failed",
                message="Could not update authentication user.",
            ) from exc

        user_payload = _normalize_auth_user_payload(updated)
        return UUID(str(user_payload["id"]))
    finally:
        await client.aclose()


async def _department_metrics(session: AsyncSession, department_id: UUID) -> tuple[int, int, int, float]:
    total_students = int(
        (await session.execute(select(func.count(Student.id)).where(Student.department_id == department_id))).scalar_one()
    )
    total_faculty = int(
        (await session.execute(select(func.count(Faculty.id)).where(Faculty.department_id == department_id))).scalar_one()
    )
    total_subjects = int(
        (await session.execute(select(func.count(Subject.id)).where(Subject.department_id == department_id))).scalar_one()
    )

    present_count = int(
        (
            await session.execute(
                select(func.count(Attendance.id))
                .join(Subject, Subject.id == Attendance.subject_id)
                .where(
                    Subject.department_id == department_id,
                    Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]),
                )
            )
        ).scalar_one()
    )
    total_attendance = int(
        (
            await session.execute(
                select(func.count(Attendance.id))
                .join(Subject, Subject.id == Attendance.subject_id)
                .where(Subject.department_id == department_id)
            )
        ).scalar_one()
    )
    attendance_percent = round((present_count / total_attendance) * 100, 2) if total_attendance else 0.0

    return total_students, total_faculty, total_subjects, attendance_percent


async def _build_department_summary(
    session: AsyncSession,
    *,
    department: Department,
    hod_name: str | None,
    hod_email: str | None,
) -> DepartmentManagementSummary:
    total_students, total_faculty, total_subjects, attendance_percent = await _department_metrics(
        session,
        department.id,
    )

    return DepartmentManagementSummary(
        id=department.id,
        code=department.code,
        name=department.name,
        hod_user_id=department.hod_user_id,
        hod_name=hod_name,
        hod_email=hod_email,
        total_students=total_students,
        total_faculty=total_faculty,
        total_subjects=total_subjects,
        attendance_percent=attendance_percent,
    )


async def _get_department_or_404(session: AsyncSession, department_id: UUID) -> Department:
    department = (
        await session.execute(select(Department).where(Department.id == department_id))
    ).scalar_one_or_none()
    if department is None:
        raise ApplicationError(status_code=404, code="department_not_found", message="Department not found.")
    return department


async def _get_department_summary_by_id(session: AsyncSession, department_id: UUID) -> DepartmentManagementSummary:
    row = (
        await session.execute(
            select(Department, User.full_name.label("hod_name"), User.email.label("hod_email"))
            .outerjoin(User, User.id == Department.hod_user_id)
            .where(Department.id == department_id)
        )
    ).one_or_none()
    if row is None:
        raise ApplicationError(status_code=404, code="department_not_found", message="Department not found.")

    department, hod_name, hod_email = row
    return await _build_department_summary(session, department=department, hod_name=hod_name, hod_email=hod_email)


async def list_departments(*, session: AsyncSession, principal: Principal) -> DepartmentListResponse:
    statement = (
        select(Department, User.full_name.label("hod_name"), User.email.label("hod_email"))
        .outerjoin(User, User.id == Department.hod_user_id)
        .order_by(Department.code)
    )

    if principal.role == AppRole.HOD:
        if principal.department_id is None:
            raise ApplicationError(
                status_code=403,
                code="department_missing",
                message=DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE,
            )
        statement = statement.where(Department.id == principal.department_id)

    rows = (await session.execute(statement)).all()
    items = [
        await _build_department_summary(session, department=department, hod_name=hod_name, hod_email=hod_email)
        for department, hod_name, hod_email in rows
    ]
    return DepartmentListResponse(items=items)


async def create_department(
    *,
    session: AsyncSession,
    payload: DepartmentCreateRequest,
) -> DepartmentManagementSummary:
    code = payload.code.strip().upper()
    name = payload.name.strip()
    if not code or not name:
        raise ApplicationError(status_code=400, code="invalid_department", message="Department code and name are required.")

    department = Department(code=code, name=name)
    session.add(department)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            status_code=409,
            code="department_conflict",
            message="Department code or name already exists.",
        ) from exc

    await session.refresh(department)
    return await _build_department_summary(session, department=department, hod_name=None, hod_email=None)


async def delete_department(*, session: AsyncSession, department_id: UUID) -> None:
    department = await _get_department_or_404(session, department_id)

    total_students, total_faculty, total_subjects, _ = await _department_metrics(session, department_id)
    if total_students or total_faculty or total_subjects:
        raise ApplicationError(
            status_code=400,
            code="department_not_empty",
            message="Department cannot be deleted while students, faculty, or subjects exist.",
            details={
                "total_students": total_students,
                "total_faculty": total_faculty,
                "total_subjects": total_subjects,
            },
        )

    await session.delete(department)
    await session.commit()


def _resolve_department_scope_for_write(principal: Principal, requested_department_id: UUID | None) -> UUID:
    if principal.role == AppRole.HOD:
        if principal.department_id is None:
            raise ApplicationError(
                status_code=403,
                code="department_missing",
                message=DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE,
            )
        if requested_department_id and requested_department_id != principal.department_id:
            raise ApplicationError(status_code=403, code="department_forbidden", message="You can only manage your department.")
        return principal.department_id

    if principal.role == AppRole.ADMIN:
        if requested_department_id is None:
            raise ApplicationError(status_code=400, code="department_required", message="department_id is required.")
        return requested_department_id

    raise ApplicationError(status_code=403, code="insufficient_role", message="Operation not permitted.")


async def _upsert_public_user(
    *,
    session: AsyncSession,
    user_id: UUID,
    full_name: str,
    email: str,
    role: AppRole,
    department_id: UUID | None,
) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    if user is None:
        email_conflict = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if email_conflict and email_conflict.id != user_id:
            raise ApplicationError(
                status_code=409,
                code="user_email_conflict",
                message="Email is already mapped to a different user.",
            )

        user = User(
            id=user_id,
            full_name=full_name,
            email=email,
            role=role,
            department_id=department_id,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        return user

    user.full_name = full_name
    user.email = email
    user.role = role
    user.department_id = department_id
    user.is_active = True
    await session.flush()
    return user


async def _upsert_faculty_profile(
    *,
    session: AsyncSession,
    user_id: UUID,
    department_id: UUID,
    employee_code: str,
    designation: str,
) -> Faculty:
    faculty = (await session.execute(select(Faculty).where(Faculty.user_id == user_id))).scalar_one_or_none()
    if faculty is None:
        faculty = (
            await session.execute(select(Faculty).where(Faculty.employee_code == employee_code))
        ).scalar_one_or_none()

    if faculty is None:
        faculty = Faculty(
            user_id=user_id,
            department_id=department_id,
            employee_code=employee_code,
            designation=designation,
        )
        session.add(faculty)
        await session.flush()
        return faculty

    faculty.user_id = user_id
    faculty.department_id = department_id
    faculty.employee_code = employee_code
    faculty.designation = designation
    await session.flush()
    return faculty


async def _build_faculty_summary_by_id(session: AsyncSession, faculty_id: UUID) -> FacultyManagementSummary:
    row = (
        await session.execute(
            select(
                Faculty.id,
                Faculty.user_id,
                User.full_name,
                User.email,
                Faculty.employee_code,
                Faculty.designation,
                Faculty.department_id,
                func.count(Subject.id).label("subject_count"),
            )
            .join(User, User.id == Faculty.user_id)
            .outerjoin(Subject, Subject.faculty_id == Faculty.id)
            .where(Faculty.id == faculty_id)
            .group_by(
                Faculty.id,
                Faculty.user_id,
                User.full_name,
                User.email,
                Faculty.employee_code,
                Faculty.designation,
                Faculty.department_id,
            )
        )
    ).one_or_none()

    if row is None:
        raise ApplicationError(status_code=404, code="faculty_not_found", message="Faculty profile not found.")

    return FacultyManagementSummary(
        faculty_id=row.id,
        user_id=row.user_id,
        full_name=row.full_name,
        email=row.email,
        employee_code=row.employee_code,
        designation=row.designation,
        department_id=row.department_id,
        assigned_subject_count=int(row.subject_count or 0),
    )


async def list_faculty_members(
    *,
    session: AsyncSession,
    principal: Principal,
    department_id: UUID | None,
) -> FacultyListResponse:
    if principal.role == AppRole.HOD:
        if principal.department_id is None:
            raise ApplicationError(
                status_code=403,
                code="department_missing",
                message=DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE,
            )
        scoped_department_id = principal.department_id
    elif principal.role == AppRole.ADMIN:
        scoped_department_id = department_id
    else:
        raise ApplicationError(status_code=403, code="insufficient_role", message="Operation not permitted.")

    statement = (
        select(
            Faculty.id,
            Faculty.user_id,
            User.full_name,
            User.email,
            Faculty.employee_code,
            Faculty.designation,
            Faculty.department_id,
            Department.name.label("department_name"),
            func.count(Subject.id).label("subject_count"),
        )
        .join(User, User.id == Faculty.user_id)
        .join(Department, Department.id == Faculty.department_id)
        .outerjoin(Subject, Subject.faculty_id == Faculty.id)
        .group_by(
            Faculty.id,
            Faculty.user_id,
            User.full_name,
            User.email,
            Faculty.employee_code,
            Faculty.designation,
            Faculty.department_id,
            Department.name,
        )
        .order_by(User.full_name)
    )

    if scoped_department_id is not None:
        statement = statement.where(Faculty.department_id == scoped_department_id)

    rows = (await session.execute(statement)).all()
    return FacultyListResponse(
        items=[
            FacultyManagementSummary(
                faculty_id=row.id,
                user_id=row.user_id,
                full_name=row.full_name,
                email=row.email,
                employee_code=row.employee_code,
                designation=row.designation,
                department_id=row.department_id,
                department_name=row.department_name,
                assigned_subject_count=int(row.subject_count or 0),
            )
            for row in rows
        ]
    )


async def create_faculty_member(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: FacultyCreateRequest,
) -> FacultyManagementSummary:
    scoped_department_id = _resolve_department_scope_for_write(principal, payload.department_id)
    await _get_department_or_404(session, scoped_department_id)

    auth_user_id = await _ensure_auth_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=AppRole.FACULTY,
        department_id=scoped_department_id,
    )

    try:
        await _upsert_public_user(
            session=session,
            user_id=auth_user_id,
            full_name=payload.full_name,
            email=str(payload.email),
            role=AppRole.FACULTY,
            department_id=scoped_department_id,
        )
        faculty = await _upsert_faculty_profile(
            session=session,
            user_id=auth_user_id,
            department_id=scoped_department_id,
            employee_code=payload.employee_code,
            designation=payload.designation,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            status_code=409,
            code="faculty_conflict",
            message="Faculty profile already exists with conflicting data.",
        ) from exc

    return await _build_faculty_summary_by_id(session, faculty.id)


async def create_or_assign_hod(
    *,
    session: AsyncSession,
    department_id: UUID,
    payload: HodCreateRequest,
) -> DepartmentManagementSummary:
    department = await _get_department_or_404(session, department_id)

    auth_user_id = await _ensure_auth_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=AppRole.HOD,
        department_id=department_id,
    )

    try:
        await _upsert_public_user(
            session=session,
            user_id=auth_user_id,
            full_name=payload.full_name,
            email=str(payload.email),
            role=AppRole.HOD,
            department_id=department_id,
        )
        await _upsert_faculty_profile(
            session=session,
            user_id=auth_user_id,
            department_id=department_id,
            employee_code=payload.employee_code,
            designation=payload.designation,
        )

        department.hod_user_id = auth_user_id
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            status_code=409,
            code="hod_assignment_conflict",
            message="Could not assign HOD because of conflicting records.",
        ) from exc

    return await _get_department_summary_by_id(session, department.id)
