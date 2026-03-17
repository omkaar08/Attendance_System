from datetime import date
from uuid import UUID

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import AppRole, Attendance, AttendanceStatus, Faculty, Student, Subject
from app.schemas.analytics import AnalyticsOverviewResponse, SubjectAttendanceResponse, SubjectAttendanceItem
from app.services.subjects import get_subject_for_principal


async def get_analytics_overview(
    *,
    session: AsyncSession,
    principal: Principal,
    department_id: UUID | None,
    subject_id: UUID | None,
) -> AnalyticsOverviewResponse:
    subject_scope = None
    if subject_id is not None:
        subject_scope = await get_subject_for_principal(session, principal, subject_id)

    if principal.role == AppRole.HOD:
        department_scope = principal.department_id
    elif principal.role == AppRole.FACULTY:
        department_scope = principal.department_id
    else:
        department_scope = department_id

    if subject_scope is not None:
        department_scope = subject_scope.department_id

    student_count_stmt = select(func.count(Student.id))
    faculty_count_stmt = select(func.count(Faculty.id))
    subject_count_stmt = select(func.count(Subject.id))
    today_attendance_stmt = select(func.count(distinct(Attendance.student_id))).where(Attendance.class_date == date.today())
    average_attendance_stmt = select(func.count(Attendance.id), func.count(distinct(Attendance.student_id)))

    if department_scope is not None:
        student_count_stmt = student_count_stmt.where(Student.department_id == department_scope)
        faculty_count_stmt = faculty_count_stmt.where(Faculty.department_id == department_scope)
        subject_count_stmt = subject_count_stmt.where(Subject.department_id == department_scope)
        today_attendance_stmt = today_attendance_stmt.join(Subject, Subject.id == Attendance.subject_id).where(
            Subject.department_id == department_scope
        )
        average_attendance_stmt = average_attendance_stmt.join(Subject, Subject.id == Attendance.subject_id).where(
            Subject.department_id == department_scope
        )

    if subject_scope is not None:
        student_count_stmt = student_count_stmt.where(
            Student.department_id == subject_scope.department_id,
            Student.semester == subject_scope.semester,
            Student.section == subject_scope.section,
        )
        faculty_count_stmt = faculty_count_stmt.where(Faculty.id == subject_scope.faculty_id)
        subject_count_stmt = subject_count_stmt.where(Subject.id == subject_scope.id)
        today_attendance_stmt = today_attendance_stmt.where(Attendance.subject_id == subject_scope.id)
        average_attendance_stmt = average_attendance_stmt.where(Attendance.subject_id == subject_scope.id)

    if principal.role == AppRole.FACULTY:
        if principal.faculty_id is None:
            raise ApplicationError(status_code=403, code="faculty_profile_missing", message="Faculty profile not found.")
        if subject_scope is None:
            subject_count_stmt = subject_count_stmt.where(Subject.faculty_id == principal.faculty_id)
            today_attendance_stmt = today_attendance_stmt.where(Attendance.faculty_id == principal.faculty_id)
            average_attendance_stmt = average_attendance_stmt.where(Attendance.faculty_id == principal.faculty_id)

    total_students = int((await session.execute(student_count_stmt)).scalar_one())
    total_faculty = int((await session.execute(faculty_count_stmt)).scalar_one())
    total_subjects = int((await session.execute(subject_count_stmt)).scalar_one())
    today_present_students = int((await session.execute(today_attendance_stmt)).scalar_one())
    total_attendance_rows, distinct_attendance_students = (await session.execute(average_attendance_stmt)).one()

    today_attendance_percent = round((today_present_students / total_students) * 100, 2) if total_students else 0.0
    average_attendance_percent = (
        round((int(distinct_attendance_students or 0) / max(int(total_students or 0), 1)) * 100, 2)
        if total_students
        else 0.0
    )

    return AnalyticsOverviewResponse(
        total_students=total_students,
        total_faculty=total_faculty,
        total_subjects=total_subjects,
        today_attendance_percent=today_attendance_percent,
        average_attendance_percent=average_attendance_percent,
    )


async def get_subject_attendance_stats(
    *,
    session: AsyncSession,
    principal: Principal,
    department_id: UUID | None,
) -> SubjectAttendanceResponse:
    """Get average attendance percentage for each subject."""
    # Determine which department to use
    if principal.role == AppRole.HOD:
        target_department_id = principal.department_id
    elif principal.role == AppRole.ADMIN:
        target_department_id = department_id
    else:
        raise ApplicationError(status_code=403, code="insufficient_permissions", message="Access denied.")

    # Get all subjects in the department
    subjects_stmt = select(Subject).where(Subject.department_id == target_department_id).order_by(Subject.name)
    subjects = (await session.execute(subjects_stmt)).scalars().all()

    items = []
    for subject in subjects:
        # Count distinct sessions (unique combinations of class_date and session_key)
        distinct_sessions_subquery = (
            select(Attendance.class_date, Attendance.session_key)
            .where(Attendance.subject_id == subject.id)
            .distinct()
            .subquery()
        )
        total_sessions_stmt = select(func.count()).select_from(distinct_sessions_subquery)

        total_students_stmt = select(func.count(distinct(Student.id))).where(
            and_(
                Student.department_id == target_department_id,
                Student.semester == subject.semester,
                Student.section == subject.section,
            )
        )

        # Count total attendance records (present marks) for this subject
        attendance_count_stmt = select(func.count(Attendance.id)).where(
            and_(
                Attendance.subject_id == subject.id,
                Attendance.status == AttendanceStatus.PRESENT,
            )
        )

        total_sessions = int((await session.execute(total_sessions_stmt)).scalar_one() or 0)
        total_students = int((await session.execute(total_students_stmt)).scalar_one() or 0)
        attendance_count = int((await session.execute(attendance_count_stmt)).scalar_one() or 0)

        # Calculate percentage: (total present marks) / (total sessions * total students) * 100
        if total_sessions > 0 and total_students > 0:
            attendance_percent = round((attendance_count / (total_sessions * total_students)) * 100, 2)
        else:
            attendance_percent = 0.0

        items.append(
            SubjectAttendanceItem(
                subject_id=subject.id,
                subject_name=subject.name,
                subject_code=subject.code,
                attendance_percent=attendance_percent,
            )
        )

    return SubjectAttendanceResponse(items=items)