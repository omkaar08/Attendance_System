from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import AppRole, Faculty, Subject
from app.schemas.faculty import SubjectListResponse
from app.schemas.common import SubjectSummary
from app.schemas.subjects import SubjectCreateRequest, SubjectResponse

DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE = "Department mapping not found."


async def get_subject_for_principal(session: AsyncSession, principal: Principal, subject_id: UUID) -> Subject:
    subject = (await session.execute(select(Subject).where(Subject.id == subject_id))).scalar_one_or_none()
    if subject is None:
        raise ApplicationError(status_code=404, code="subject_not_found", message="Subject not found.")

    is_authorized = (
        principal.role == AppRole.ADMIN
        or (principal.role == AppRole.HOD and principal.department_id == subject.department_id)
        or (principal.role == AppRole.FACULTY and principal.faculty_id == subject.faculty_id)
    )
    if is_authorized:
        return subject

    raise ApplicationError(status_code=403, code="subject_forbidden", message="You cannot access this subject.")


async def list_faculty_subjects(
    *,
    session: AsyncSession,
    principal: Principal,
    semester: int | None,
    section: str | None,
    active_only: bool,
) -> SubjectListResponse:
    statement = select(Subject)

    if principal.role == AppRole.FACULTY:
        if principal.faculty_id is None:
            raise ApplicationError(status_code=403, code="faculty_profile_missing", message="Faculty profile not found.")
        statement = statement.where(Subject.faculty_id == principal.faculty_id)
    elif principal.role == AppRole.HOD:
        if principal.department_id is None:
            raise ApplicationError(
                status_code=403,
                code="department_missing",
                message=DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE,
            )
        statement = statement.where(Subject.department_id == principal.department_id)
    elif principal.role != AppRole.ADMIN:
        raise ApplicationError(status_code=403, code="subject_forbidden", message="You cannot access subjects.")

    if semester is not None:
        statement = statement.where(Subject.semester == semester)
    if section is not None:
        statement = statement.where(Subject.section == section)
    if active_only:
        statement = statement.where(Subject.is_active.is_(True))
    statement = statement.order_by(Subject.semester, Subject.section, Subject.code)

    items = (await session.execute(statement)).scalars().all()
    return SubjectListResponse(items=[SubjectSummary.model_validate(item) for item in items])


async def assign_subject_faculty(
    *,
    session: AsyncSession,
    principal: Principal,
    subject_id: UUID,
    faculty_id: UUID,
) -> SubjectResponse:
    if principal.role != AppRole.HOD:
        raise ApplicationError(status_code=403, code="subject_forbidden", message="Only HOD can assign subjects.")
    if principal.department_id is None:
        raise ApplicationError(
            status_code=403,
            code="department_missing",
            message=DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE,
        )

    subject = (await session.execute(select(Subject).where(Subject.id == subject_id))).scalar_one_or_none()
    if subject is None:
        raise ApplicationError(status_code=404, code="subject_not_found", message="Subject not found.")

    faculty = (await session.execute(select(Faculty).where(Faculty.id == faculty_id))).scalar_one_or_none()
    if faculty is None:
        raise ApplicationError(status_code=404, code="faculty_not_found", message="Faculty not found.")

    if faculty.department_id != subject.department_id:
        raise ApplicationError(
            status_code=400,
            code="department_mismatch",
            message="Subject and faculty must belong to the same department.",
        )
    if principal.department_id != subject.department_id:
        raise ApplicationError(status_code=403, code="subject_forbidden", message="You cannot assign this subject.")

    subject.faculty_id = faculty.id
    await session.commit()
    await session.refresh(subject)
    return SubjectResponse.model_validate(subject)


async def create_subject_for_hod(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: SubjectCreateRequest,
) -> SubjectResponse:
    if principal.role != AppRole.HOD:
        raise ApplicationError(status_code=403, code="subject_forbidden", message="Only HOD can create subjects.")
    if principal.department_id is None:
        raise ApplicationError(
            status_code=403,
            code="department_missing",
            message=DEPARTMENT_MAPPING_NOT_FOUND_MESSAGE,
        )

    faculty = (await session.execute(select(Faculty).where(Faculty.id == payload.faculty_id))).scalar_one_or_none()
    if faculty is None:
        raise ApplicationError(status_code=404, code="faculty_not_found", message="Faculty not found.")
    if faculty.department_id != principal.department_id:
        raise ApplicationError(
            status_code=400,
            code="department_mismatch",
            message="Faculty must belong to your department.",
        )

    subject = Subject(
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        department_id=principal.department_id,
        faculty_id=faculty.id,
        semester=payload.semester,
        section=payload.section.strip().upper(),
        attendance_grace_minutes=payload.attendance_grace_minutes,
        is_active=True,
    )
    session.add(subject)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            status_code=409,
            code="subject_conflict",
            message="Subject with this code already exists for the selected cohort.",
        ) from exc

    await session.refresh(subject)
    return SubjectResponse.model_validate(subject)


async def faculty_can_manage_cohort(
    *,
    session: AsyncSession,
    principal: Principal,
    department_id: UUID,
    semester: int,
    section: str,
) -> bool:
    if principal.role in {AppRole.ADMIN, AppRole.HOD}:
        return principal.role == AppRole.ADMIN or principal.department_id == department_id
    if principal.faculty_id is None:
        return False

    statement = select(Subject.id).where(
        and_(
            Subject.faculty_id == principal.faculty_id,
            Subject.department_id == department_id,
            Subject.semester == semester,
            Subject.section == section,
            Subject.is_active.is_(True),
        )
    ).limit(1)
    # A faculty can legitimately own multiple subjects in one cohort;
    # use a bounded existence check instead of scalar_one_or_none().
    return (await session.execute(statement)).scalar() is not None