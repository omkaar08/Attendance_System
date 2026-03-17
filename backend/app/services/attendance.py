from collections.abc import Iterable
from datetime import date
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import Attendance, AttendanceStatus, Student, Subject, User
from app.schemas.attendance import (
    AttendanceAccepted,
    AttendanceDuplicate,
    LowAttendanceAlertItem,
    LowAttendanceAlertResponse,
    AttendanceMarkRequest,
    AttendanceMarkResponse,
    AttendanceReportItem,
    AttendanceReportResponse,
    AttendanceReportSummary,
    ManualAttendanceRequest,
)
from app.services.subjects import get_subject_for_principal


async def mark_attendance(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: AttendanceMarkRequest,
) -> AttendanceMarkResponse:
    subject = await get_subject_for_principal(session, principal, payload.subject_id)
    student_ids = [entry.student_id for entry in payload.entries]

    valid_students = {
        student.id: student
        for student in (
            await session.execute(
                select(Student).where(
                    and_(
                        Student.id.in_(student_ids),
                        Student.department_id == subject.department_id,
                        Student.semester == subject.semester,
                        Student.section == subject.section,
                    )
                )
            )
        ).scalars()
    }

    missing_students = [str(student_id) for student_id in student_ids if student_id not in valid_students]
    if missing_students:
        raise ApplicationError(
            status_code=400,
            code="student_subject_mismatch",
            message="One or more students do not belong to the selected subject cohort.",
            details={"student_ids": missing_students},
        )

    duplicates = {
        student_id
        for student_id, in (
            await session.execute(
                select(Attendance.student_id).where(
                    and_(
                        Attendance.subject_id == payload.subject_id,
                        Attendance.class_date == payload.class_date,
                        Attendance.session_key == payload.session_key,
                        Attendance.student_id.in_(student_ids),
                    )
                )
            )
        ).all()
    }

    accepted: list[AttendanceAccepted] = []
    duplicate_rows: list[AttendanceDuplicate] = []
    for entry in payload.entries:
        if entry.student_id in duplicates:
            duplicate_rows.append(
                AttendanceDuplicate(student_id=entry.student_id, reason="Attendance already exists for this session.")
            )
            continue

        attendance = Attendance(
            student_id=entry.student_id,
            subject_id=subject.id,
            faculty_id=subject.faculty_id,
            marked_by_user_id=principal.user_id,
            class_date=payload.class_date,
            session_key=payload.session_key,
            session_label=payload.session_label,
            status=entry.status,
            confidence_score=entry.confidence_score,
            recognition_metadata=entry.recognition_metadata,
        )
        session.add(attendance)
        await session.flush()
        accepted.append(
            AttendanceAccepted(
                student_id=attendance.student_id,
                attendance_id=attendance.id,
                confidence_score=float(attendance.confidence_score),
                created_at=attendance.created_at,
            )
        )

    await session.commit()
    return AttendanceMarkResponse(accepted=accepted, duplicates=duplicate_rows)


async def mark_attendance_manual(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: ManualAttendanceRequest,
) -> AttendanceMarkResponse:
    """Mark attendance manually for a single student on a specific date."""
    subject = await get_subject_for_principal(session, principal, payload.subject_id)

    # Validate that the student belongs to the subject
    student = (
        await session.execute(
            select(Student).where(
                and_(
                    Student.id == payload.student_id,
                    Student.department_id == subject.department_id,
                    Student.semester == subject.semester,
                    Student.section == subject.section,
                )
            )
        )
    ).scalar_one_or_none()

    if not student:
        raise ApplicationError(
            status_code=400,
            code="student_subject_mismatch",
            message="Student does not belong to the selected subject cohort.",
        )

    # Check for duplicate attendance record on the same date
    existing = (
        await session.execute(
            select(Attendance).where(
                and_(
                    Attendance.subject_id == payload.subject_id,
                    Attendance.student_id == payload.student_id,
                    Attendance.class_date == payload.class_date,
                )
            )
        )
    ).scalar_one_or_none()

    if existing:
        return AttendanceMarkResponse(
            accepted=[],
            duplicates=[
                AttendanceDuplicate(
                    student_id=payload.student_id,
                    reason="Attendance already exists for this date.",
                )
            ],
        )

    # Create attendance record
    attendance = Attendance(
        student_id=payload.student_id,
        subject_id=subject.id,
        faculty_id=subject.faculty_id,
        marked_by_user_id=principal.user_id,
        class_date=payload.class_date,
        session_key="manual",
        session_label=payload.session_label,
        status=payload.status,
        confidence_score=1.0,  # Manual marking has 100% confidence
        recognition_metadata={"method": "manual"},
    )
    session.add(attendance)
    await session.flush()

    await session.commit()
    return AttendanceMarkResponse(
        accepted=[
            AttendanceAccepted(
                student_id=attendance.student_id,
                attendance_id=attendance.id,
                confidence_score=1.0,
                created_at=attendance.created_at,
            )
        ],
        duplicates=[],
    )



async def report_attendance(
    *,
    session: AsyncSession,
    principal: Principal,
    from_date: date,
    to_date: date,
    subject_id: UUID | None,
    department_id: UUID | None,
    student_id: UUID | None,
    section: str | None,
) -> AttendanceReportResponse:
    if to_date < from_date:
        raise ApplicationError(status_code=400, code="invalid_date_range", message="Invalid date range.")

    statement = (
        select(Attendance, Student.full_name, Student.roll_number, Subject.name.label("subject_name"))
        .join(Student, Student.id == Attendance.student_id)
        .join(Subject, Subject.id == Attendance.subject_id)
        .where(Attendance.class_date.between(from_date, to_date))
    )

    if principal.role.value == "hod":
        statement = statement.where(Subject.department_id == principal.department_id)
    elif principal.role.value == "faculty":
        if principal.faculty_id is None:
            raise ApplicationError(status_code=403, code="faculty_profile_missing", message="Faculty profile not found.")
        statement = statement.where(Attendance.faculty_id == principal.faculty_id)
    elif department_id is not None:
        statement = statement.where(Subject.department_id == department_id)

    if subject_id is not None:
        await get_subject_for_principal(session, principal, subject_id)
        statement = statement.where(Attendance.subject_id == subject_id)
    if student_id is not None:
        statement = statement.where(Attendance.student_id == student_id)
    if section is not None:
        statement = statement.where(Subject.section == section)

    statement = statement.order_by(Attendance.class_date.desc(), Attendance.captured_at.desc())
    rows = (await session.execute(statement)).all()

    items = [
        AttendanceReportItem(
            id=attendance.id,
            student_id=attendance.student_id,
            student_name=student_name,
            roll_number=roll_number,
            subject_id=attendance.subject_id,
            subject_name=subject_name,
            faculty_id=attendance.faculty_id,
            class_date=attendance.class_date,
            session_key=attendance.session_key,
            session_label=attendance.session_label,
            status=attendance.status,
            confidence_score=float(attendance.confidence_score),
            captured_at=attendance.captured_at,
        )
        for attendance, student_name, roll_number, subject_name in rows
    ]

    total_records = len(items)
    present_count = sum(1 for item in items if item.status == AttendanceStatus.PRESENT)
    late_count = sum(1 for item in items if item.status == AttendanceStatus.LATE)
    average_confidence = (
        round(sum(item.confidence_score for item in items) / total_records, 4) if total_records else None
    )

    return AttendanceReportResponse(
        items=items,
        summary=AttendanceReportSummary(
            total_records=total_records,
            present_count=present_count,
            late_count=late_count,
            average_confidence_score=average_confidence,
        ),
    )


async def low_attendance_alerts(
    *,
    session: AsyncSession,
    principal: Principal,
    from_date: date,
    to_date: date,
    threshold_percent: float,
    min_sessions: int,
    subject_id: UUID | None,
    department_id: UUID | None,
) -> LowAttendanceAlertResponse:
    if to_date < from_date:
        raise ApplicationError(status_code=400, code="invalid_date_range", message="Invalid date range.")

    present_case = case(
        (Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]), 1),
        else_=0,
    )

    statement = (
        select(
            Student.id.label("student_id"),
            Student.full_name,
            Student.roll_number,
            Student.department_id,
            Student.semester,
            Student.section,
            Subject.id.label("subject_id"),
            Subject.name.label("subject_name"),
            func.count(Attendance.id).label("total_sessions"),
            func.sum(present_case).label("present_sessions"),
        )
        .join(Student, Student.id == Attendance.student_id)
        .join(Subject, Subject.id == Attendance.subject_id)
        .where(Attendance.class_date.between(from_date, to_date))
        .group_by(
            Student.id,
            Student.full_name,
            Student.roll_number,
            Student.department_id,
            Student.semester,
            Student.section,
            Subject.id,
            Subject.name,
        )
    )

    if principal.role.value == "hod":
        statement = statement.where(Subject.department_id == principal.department_id)
    elif principal.role.value == "faculty":
        if principal.faculty_id is None:
            raise ApplicationError(status_code=403, code="faculty_profile_missing", message="Faculty profile not found.")
        statement = statement.where(Attendance.faculty_id == principal.faculty_id)
    elif department_id is not None:
        statement = statement.where(Subject.department_id == department_id)

    if subject_id is not None:
        await get_subject_for_principal(session, principal, subject_id)
        statement = statement.where(Attendance.subject_id == subject_id)

    rows = (await session.execute(statement)).all()

    alerts: list[LowAttendanceAlertItem] = []
    for row in rows:
        total_sessions = int(row.total_sessions or 0)
        present_sessions = int(row.present_sessions or 0)

        if total_sessions < min_sessions:
            continue

        attendance_percent = round((present_sessions / total_sessions) * 100, 2)
        if attendance_percent >= threshold_percent:
            continue

        alerts.append(
            LowAttendanceAlertItem(
                student_id=row.student_id,
                full_name=row.full_name,
                roll_number=row.roll_number,
                subject_id=row.subject_id,
                subject_name=row.subject_name,
                department_id=row.department_id,
                semester=row.semester,
                section=row.section,
                total_sessions=total_sessions,
                present_sessions=present_sessions,
                attendance_percent=attendance_percent,
            )
        )

    alerts.sort(key=lambda item: (item.attendance_percent, item.full_name.lower()))
    return LowAttendanceAlertResponse(
        threshold_percent=threshold_percent,
        min_sessions=min_sessions,
        items=alerts,
    )