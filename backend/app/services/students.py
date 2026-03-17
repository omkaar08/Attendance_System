from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import AppRole, Student, Subject
from app.schemas.common import StudentSummary
from app.schemas.students import StudentListResponse, StudentRegisterRequest, StudentResponse
from app.services.subjects import faculty_can_manage_cohort, get_subject_for_principal


async def register_student(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: StudentRegisterRequest,
) -> StudentResponse:
    can_manage = await faculty_can_manage_cohort(
        session=session,
        principal=principal,
        department_id=payload.department_id,
        semester=payload.semester,
        section=payload.section,
    )
    if not can_manage:
        raise ApplicationError(status_code=403, code="student_forbidden", message="You cannot register this student.")

    student = Student(
        full_name=payload.full_name,
        roll_number=payload.roll_number,
        department_id=payload.department_id,
        semester=payload.semester,
        section=payload.section,
        batch_year=payload.batch_year,
        email=payload.email,
        created_by=principal.user_id,
    )
    session.add(student)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(status_code=409, code="student_conflict", message="Student already exists.") from exc

    await session.refresh(student)
    return StudentResponse.model_validate(student)


async def list_students(
    *,
    session: AsyncSession,
    principal: Principal,
    department_id: UUID | None,
    semester: int | None,
    section: str | None,
    subject_id: UUID | None,
    search: str | None,
    limit: int,
) -> StudentListResponse:
    statement: Select[tuple[Student]] = select(Student)

    if principal.role == AppRole.ADMIN:
        if department_id is not None:
            statement = statement.where(Student.department_id == department_id)
    elif principal.role == AppRole.HOD:
        statement = statement.where(Student.department_id == principal.department_id)
    else:
        if principal.faculty_id is None:
            raise ApplicationError(status_code=403, code="faculty_profile_missing", message="Faculty profile not found.")
        statement = (
            select(Student)
            .join(
                Subject,
                and_(
                    Subject.department_id == Student.department_id,
                    Subject.semester == Student.semester,
                    Subject.section == Student.section,
                ),
            )
            .where(Subject.faculty_id == principal.faculty_id)
            .distinct()
        )
        if subject_id is not None:
            subject = await get_subject_for_principal(session, principal, subject_id)
            statement = statement.where(Subject.id == subject.id)

    if semester is not None:
        statement = statement.where(Student.semester == semester)
    if section is not None:
        statement = statement.where(Student.section == section)
    if search:
        like_pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(Student.full_name.ilike(like_pattern), Student.roll_number.ilike(like_pattern))
        )

    statement = statement.order_by(Student.full_name).limit(limit)
    items = (await session.execute(statement)).scalars().all()
    return StudentListResponse(items=[StudentSummary.model_validate(item) for item in items])