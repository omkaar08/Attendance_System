"""
Aggregate report generation — daily, monthly, per-student, per-department.

All queries are scoped by the principal's role (HOD → own department,
faculty → own subjects, admin → optionally filtered by department).
"""
from __future__ import annotations

from calendar import month_abbr
from datetime import date
from uuid import UUID

from sqlalchemy import Integer, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.reports import (
    DailyAttendanceRow,
    DailyReportResponse,
    DepartmentReportRow,
    DepartmentReportResponse,
    MonthlyAttendanceRow,
    MonthlyReportResponse,
    StudentAttendanceSummaryRow,
    StudentReportResponse,
    SubjectAttendanceSummaryRow,
    SubjectReportResponse,
)
from app.services.subjects import get_subject_for_principal

_MONTH_NAMES = list(month_abbr)  # ['', 'Jan', 'Feb', …]

_present_case = case(
    (Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]), 1),
    else_=0,
)
_absent_case = case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)
_late_case = case((Attendance.status == AttendanceStatus.LATE, 1), else_=0)


def _check_date_range(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise ApplicationError(
            status_code=400, code="invalid_date_range", message="to_date must be ≥ from_date."
        )


def _apply_role_scope(stmt, principal: Principal):
    """Restrict an Attendance-joined statement to the principal's data scope."""
    if principal.role == AppRole.HOD:
        return stmt.where(Subject.department_id == principal.department_id)
    if principal.role == AppRole.FACULTY:
        if principal.faculty_id is None:
            raise ApplicationError(
                status_code=403,
                code="faculty_profile_missing",
                message="Faculty profile not found.",
            )
        return stmt.where(Attendance.faculty_id == principal.faculty_id)
    return stmt  # admin — no extra scope by default


# --------------------------------------------------------------------------- #
#  Daily report                                                                 #
# --------------------------------------------------------------------------- #

async def daily_report(
    *,
    session: AsyncSession,
    principal: Principal,
    from_date: date,
    to_date: date,
    subject_id: UUID | None = None,
    department_id: UUID | None = None,
) -> DailyReportResponse:
    _check_date_range(from_date, to_date)

    stmt = (
        select(
            Attendance.class_date,
            func.count(Attendance.id).label("total_records"),
            func.count(func.distinct(Attendance.student_id)).label("unique_students"),
            func.sum(_present_case).label("present_count"),
        )
        .join(Subject, Subject.id == Attendance.subject_id)
        .where(Attendance.class_date.between(from_date, to_date))
        .group_by(Attendance.class_date)
        .order_by(Attendance.class_date)
    )

    stmt = _apply_role_scope(stmt, principal)

    if subject_id is not None:
        await get_subject_for_principal(session, principal, subject_id)
        stmt = stmt.where(Attendance.subject_id == subject_id)
    elif department_id is not None and principal.role == AppRole.ADMIN:
        stmt = stmt.where(Subject.department_id == department_id)

    rows = (await session.execute(stmt)).all()
    items = []
    for row in rows:
        total = int(row.total_records or 0)
        present = int(row.present_count or 0)
        items.append(
            DailyAttendanceRow(
                date=row.class_date,
                total_records=total,
                unique_students=int(row.unique_students or 0),
                present_count=present,
                present_percent=round(present / total * 100, 2) if total else 0.0,
            )
        )
    return DailyReportResponse(items=items, total_rows=len(items))


# --------------------------------------------------------------------------- #
#  Monthly report                                                               #
# --------------------------------------------------------------------------- #

async def monthly_report(
    *,
    session: AsyncSession,
    principal: Principal,
    from_date: date,
    to_date: date,
    subject_id: UUID | None = None,
    department_id: UUID | None = None,
) -> MonthlyReportResponse:
    _check_date_range(from_date, to_date)

    year_col = extract("year", Attendance.class_date).cast(Integer).label("year")
    month_col = extract("month", Attendance.class_date).cast(Integer).label("month")

    stmt = (
        select(
            year_col,
            month_col,
            func.count(Attendance.id).label("total_records"),
            func.count(func.distinct(Attendance.student_id)).label("unique_students"),
            func.sum(_present_case).label("present_count"),
        )
        .join(Subject, Subject.id == Attendance.subject_id)
        .where(Attendance.class_date.between(from_date, to_date))
        .group_by(year_col, month_col)
        .order_by(year_col, month_col)
    )

    stmt = _apply_role_scope(stmt, principal)

    if subject_id is not None:
        await get_subject_for_principal(session, principal, subject_id)
        stmt = stmt.where(Attendance.subject_id == subject_id)
    elif department_id is not None and principal.role == AppRole.ADMIN:
        stmt = stmt.where(Subject.department_id == department_id)

    rows = (await session.execute(stmt)).all()
    items = []
    for row in rows:
        total = int(row.total_records or 0)
        present = int(row.present_count or 0)
        items.append(
            MonthlyAttendanceRow(
                year=int(row.year),
                month=int(row.month),
                month_label=f"{_MONTH_NAMES[int(row.month)]} {int(row.year)}",
                total_records=total,
                unique_students=int(row.unique_students or 0),
                present_count=present,
                present_percent=round(present / total * 100, 2) if total else 0.0,
            )
        )
    return MonthlyReportResponse(items=items, total_rows=len(items))


# --------------------------------------------------------------------------- #
#  Subject performance report                                                   #
# --------------------------------------------------------------------------- #

async def subject_report(
    *,
    session: AsyncSession,
    principal: Principal,
    from_date: date,
    to_date: date,
    subject_id: UUID | None = None,
    department_id: UUID | None = None,
) -> SubjectReportResponse:
    _check_date_range(from_date, to_date)

    # Get all subjects in scope
    subjects_stmt = select(
        Subject.id,
        Subject.name,
        Subject.code,
        Subject.semester,
        Subject.section,
        Department.id.label("department_id"),
        Department.name.label("department_name"),
        Faculty.id.label("faculty_id"),
        User.full_name.label("faculty_name"),
    ).join(Department, Department.id == Subject.department_id).join(Faculty, Faculty.id == Subject.faculty_id).join(User, User.id == Faculty.user_id)

    # Apply role-based filtering
    if principal.role == AppRole.HOD:
        subjects_stmt = subjects_stmt.where(Subject.department_id == principal.department_id)
    elif principal.role == AppRole.FACULTY:
        if principal.faculty_id is None:
            raise ApplicationError(
                status_code=403,
                code="faculty_profile_missing",
                message="Faculty profile not found.",
            )
        subjects_stmt = subjects_stmt.where(Subject.faculty_id == principal.faculty_id)
    elif principal.role == AppRole.ADMIN and department_id is not None:
        subjects_stmt = subjects_stmt.where(Subject.department_id == department_id)

    if subject_id is not None:
        await get_subject_for_principal(session, principal, subject_id)
        subjects_stmt = subjects_stmt.where(Subject.id == subject_id)

    subjects_stmt = subjects_stmt.order_by(Department.name, Subject.code, Subject.section)
    subjects = (await session.execute(subjects_stmt)).all()

    items = []
    for subject_row in subjects:
        # LEFT JOIN attendance for this subject in date range
        attendance_stmt = (
            select(
                func.count(Attendance.id).label("total_records"),
                func.count(func.distinct(Attendance.student_id)).label("unique_students"),
                func.sum(_present_case).label("present_count"),
                func.sum(_absent_case).label("absent_count"),
                func.sum(_late_case).label("late_count"),
            )
            .where(
                Attendance.subject_id == subject_row.id,
                Attendance.class_date.between(from_date, to_date)
            )
        )

        attendance_data = (await session.execute(attendance_stmt)).one()
        
        total = int(attendance_data.total_records or 0)
        present = int(attendance_data.present_count or 0)
        
        items.append(
            SubjectAttendanceSummaryRow(
                subject_id=subject_row.id,
                subject_name=subject_row.name,
                subject_code=subject_row.code,
                department_id=subject_row.department_id,
                department_name=subject_row.department_name,
                faculty_id=subject_row.faculty_id,
                faculty_name=subject_row.faculty_name,
                semester=int(subject_row.semester),
                section=subject_row.section,
                total_records=total,
                unique_students=int(attendance_data.unique_students or 0),
                present_count=present,
                absent_count=int(attendance_data.absent_count or 0),
                late_count=int(attendance_data.late_count or 0),
                attendance_percent=round(present / total * 100, 2) if total else 0.0,
            )
        )
    
    return SubjectReportResponse(items=items, total_rows=len(items))


# --------------------------------------------------------------------------- #
#  Student performance report                                                   #
# --------------------------------------------------------------------------- #

async def student_report(
    *,
    session: AsyncSession,
    principal: Principal,
    from_date: date,
    to_date: date,
    student_id: UUID | None = None,
    subject_id: UUID | None = None,
    department_id: UUID | None = None,
) -> StudentReportResponse:
    _check_date_range(from_date, to_date)

    stmt = (
        select(
            Student.id.label("student_id"),
            Student.full_name,
            Student.roll_number,
            Subject.id.label("subject_id"),
            Subject.name.label("subject_name"),
            Subject.code.label("subject_code"),
            Subject.semester,
            Subject.section,
            func.count(Attendance.id).label("total_sessions"),
            func.sum(_present_case).label("present_count"),
            func.sum(_absent_case).label("absent_count"),
            func.sum(_late_case).label("late_count"),
        )
        .join(Student, Student.id == Attendance.student_id)
        .join(Subject, Subject.id == Attendance.subject_id)
        .where(Attendance.class_date.between(from_date, to_date))
        .group_by(
            Student.id,
            Student.full_name,
            Student.roll_number,
            Subject.id,
            Subject.name,
            Subject.code,
            Subject.semester,
            Subject.section,
        )
        .order_by(Student.full_name, Subject.code)
    )

    stmt = _apply_role_scope(stmt, principal)

    if subject_id is not None:
        await get_subject_for_principal(session, principal, subject_id)
        stmt = stmt.where(Attendance.subject_id == subject_id)
    if student_id is not None:
        stmt = stmt.where(Attendance.student_id == student_id)
    if department_id is not None and principal.role == AppRole.ADMIN:
        stmt = stmt.where(Subject.department_id == department_id)

    rows = (await session.execute(stmt)).all()
    items = []
    for row in rows:
        total = int(row.total_sessions or 0)
        present = int(row.present_count or 0)
        items.append(
            StudentAttendanceSummaryRow(
                student_id=row.student_id,
                full_name=row.full_name,
                roll_number=row.roll_number,
                subject_id=row.subject_id,
                subject_name=row.subject_name,
                subject_code=row.subject_code,
                semester=int(row.semester),
                section=row.section,
                total_sessions=total,
                present_count=present,
                absent_count=int(row.absent_count or 0),
                late_count=int(row.late_count or 0),
                attendance_percent=round(present / total * 100, 2) if total else 0.0,
            )
        )
    return StudentReportResponse(items=items, total_rows=len(items))


# --------------------------------------------------------------------------- #
#  Department performance report (admin / HOD only)                             #
# --------------------------------------------------------------------------- #

async def department_report(
    *,
    session: AsyncSession,
    principal: Principal,
    from_date: date,
    to_date: date,
    department_id: UUID | None = None,
) -> DepartmentReportResponse:
    if principal.role == AppRole.FACULTY:
        raise ApplicationError(
            status_code=403,
            code="insufficient_role",
            message="Faculty cannot access department reports.",
        )
    _check_date_range(from_date, to_date)

    # HOD is always scoped to their own department.
    effective_dept_id: UUID | None = None
    if principal.role == AppRole.HOD:
        effective_dept_id = principal.department_id
    elif department_id is not None:
        effective_dept_id = department_id

    # -- Attendance aggregates per department ------------------------------------
    att_stmt = (
        select(
            Subject.department_id.label("dept_id"),
            func.count(Attendance.id).label("total_sessions"),
            func.sum(_present_case).label("present_count"),
        )
        .join(Subject, Subject.id == Attendance.subject_id)
        .where(Attendance.class_date.between(from_date, to_date))
        .group_by(Subject.department_id)
    )
    if effective_dept_id is not None:
        att_stmt = att_stmt.where(Subject.department_id == effective_dept_id)
    att_map = {row.dept_id: row for row in (await session.execute(att_stmt)).all()}

    # -- Student / faculty / subject counts per department ----------------------
    stu_map = {
        row.department_id: int(row.cnt)
        for row in (
            await session.execute(
                select(Student.department_id, func.count(Student.id).label("cnt")).group_by(
                    Student.department_id
                )
            )
        ).all()
    }
    fac_map = {
        row.department_id: int(row.cnt)
        for row in (
            await session.execute(
                select(Faculty.department_id, func.count(Faculty.id).label("cnt")).group_by(
                    Faculty.department_id
                )
            )
        ).all()
    }
    subj_map = {
        row.department_id: int(row.cnt)
        for row in (
            await session.execute(
                select(Subject.department_id, func.count(Subject.id).label("cnt")).group_by(
                    Subject.department_id
                )
            )
        ).all()
    }

    # -- Department list --------------------------------------------------------
    dept_stmt = select(Department).order_by(Department.name)
    if effective_dept_id is not None:
        dept_stmt = dept_stmt.where(Department.id == effective_dept_id)
    departments = (await session.execute(dept_stmt)).scalars().all()

    items = []
    for dept in departments:
        att_row = att_map.get(dept.id)
        total_sessions = int(att_row.total_sessions or 0) if att_row else 0
        present_count = int(att_row.present_count or 0) if att_row else 0
        items.append(
            DepartmentReportRow(
                department_id=dept.id,
                department_name=dept.name,
                department_code=dept.code,
                total_students=stu_map.get(dept.id, 0),
                total_faculty=fac_map.get(dept.id, 0),
                total_subjects=subj_map.get(dept.id, 0),
                total_sessions=total_sessions,
                present_count=present_count,
                attendance_percent=round(present_count / total_sessions * 100, 2)
                if total_sessions
                else 0.0,
            )
        )
    return DepartmentReportResponse(items=items, total_rows=len(items))
