"""
Batch operations for importing and exporting student data.
Supports CSV format for bulk operations.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import Department, Student, Subject
from app.services.audit import AuditEventType, log_student_registered, audit_logger

_logger = logging.getLogger(__name__)


# ============================================================================ #
# Student Import                                                               #
# ============================================================================ #

@dataclass
class StudentImportRow:
    """Parsed row from import CSV."""
    name: str
    roll_number: str
    email: str
    department_code: str
    semester: int
    section: str
    phone: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if row has all required fields."""
        return (
            self.name and
            self.roll_number and
            self.email and
            self.department_code and
            self.semester and
            self.section and
            len(self.errors) == 0
        )


@dataclass
class StudentImportResult:
    """Result of batch import operation."""
    total_rows: int
    successful: int
    failed: int
    skipped: int
    errors: list[dict[str, Any]]  # List of row errors
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


async def import_students_csv(
    csv_content: str,
    session: AsyncSession,
    principal: Principal,
) -> StudentImportResult:
    """
    Import students from CSV content.
    CSV columns: name, roll_number, email, department_code, semester, section, phone (optional)
    """
    result = StudentImportResult(
        total_rows=0,
        successful=0,
        failed=0,
        skipped=0,
        errors=[],
    )

    try:
        rows = csv.DictReader(io.StringIO(csv_content))
        if not rows:
            raise ApplicationError("empty_csv", "CSV file is empty")

        # Verify principal is at least HOD/Admin
        if principal.role not in ("admin", "hod"):
            raise ApplicationError(
                "permission_denied",
                "Only HOD or Admin can import students"
            )

        for row_idx, row in enumerate(rows, start=2):  # 2 because header is row 1
            try:
                result.total_rows += 1

                # Parse and validate row
                parsed_row = _parse_student_row(row, row_idx)
                if not parsed_row.is_valid():
                    result.failed += 1
                    result.errors.append({
                        "row": row_idx,
                        "values": row,
                        "errors": parsed_row.errors,
                    })
                    continue

                # Lookup department
                dept_stmt = select(Department).where(
                    Department.code == parsed_row.department_code
                )
                department = await session.scalar(dept_stmt)
                if not department:
                    result.failed += 1
                    result.errors.append({
                        "row": row_idx,
                        "values": row,
                        "errors": [f"Department '{parsed_row.department_code}' not found"],
                    })
                    continue

                # Check HOD can only import to their department
                if principal.role == "hod" and principal.department_id != department.id:
                    result.failed += 1
                    result.errors.append({
                        "row": row_idx,
                        "values": row,
                        "errors": ["You can only import students to your department"],
                    })
                    continue

                # Check if student already exists
                existing_stmt = select(Student).where(
                    Student.roll_number == parsed_row.roll_number
                )
                existing = await session.scalar(existing_stmt)
                if existing:
                    result.skipped += 1
                    _logger.info(f"Skipping row {row_idx}: Student {parsed_row.roll_number} already exists")
                    continue

                # Create student
                student = Student(
                    id=uuid4(),
                    name=parsed_row.name,
                    email=parsed_row.email,
                    roll_number=parsed_row.roll_number,
                    phone=parsed_row.phone,
                    department_id=department.id,
                    semester=parsed_row.semester,
                    section=parsed_row.section,
                )
                session.add(student)

                # Log creation
                await log_student_registered(
                    session,
                    str(principal.user_id),
                    principal.role,
                    str(student.id),
                    student.name,
                )

                result.successful += 1
                _logger.info(f"Imported student: {parsed_row.name} ({parsed_row.roll_number})")

            except Exception as e:
                result.failed += 1
                result.errors.append({
                    "row": row_idx,
                    "values": row,
                    "errors": [str(e)],
                })
                _logger.error(f"Error importing row {row_idx}: {e}")

        # Commit all at once
        await session.commit()

    except ApplicationError:
        raise
    except Exception as e:
        _logger.error(f"CSV import failed: {e}")
        raise ApplicationError("import_failed", f"CSV import failed: {e}")

    return result


def _parse_student_row(row: dict[str, str], row_idx: int) -> StudentImportRow:
    """Parse and validate a single CSV row."""
    errors = []

    # Required fields
    name = (row.get("name") or "").strip()
    if not name:
        errors.append("'name' is required")

    roll_number = (row.get("roll_number") or "").strip()
    if not roll_number:
        errors.append("'roll_number' is required")

    email = (row.get("email") or "").strip()
    if not email:
        errors.append("'email' is required")
    elif "@" not in email:
        errors.append("'email' must be valid")

    department_code = (row.get("department_code") or "").strip()
    if not department_code:
        errors.append("'department_code' is required")

    semester_str = (row.get("semester") or "").strip()
    semester = None
    if not semester_str:
        errors.append("'semester' is required")
    else:
        try:
            semester = int(semester_str)
            if semester < 1 or semester > 8:
                errors.append("'semester' must be between 1 and 8")
        except ValueError:
            errors.append("'semester' must be numeric")

    section = (row.get("section") or "").strip()
    if not section:
        errors.append("'section' is required")

    # Optional fields
    phone = (row.get("phone") or "").strip() or None

    return StudentImportRow(
        name=name,
        roll_number=roll_number,
        email=email,
        department_code=department_code,
        semester=semester or 0,
        section=section,
        phone=phone,
        errors=errors,
    )


# ============================================================================ #
# Student Export                                                               #
# ============================================================================ #

async def export_students_csv(
    session: AsyncSession,
    principal: Principal,
    department_id: Optional[UUID] = None,
    semester: Optional[int] = None,
) -> str:
    """
    Export students to CSV format.
    Respects principal's access level.
    """
    # Build query
    query = select(Student)

    # Apply filters based on principal role
    if principal.role == "faculty":
        # Faculty can't export students directly (would need subject filter)
        raise ApplicationError(
            "permission_denied",
            "Faculty members cannot export student lists"
        )
    elif principal.role == "hod":
        # HOD can only export their department
        if not department_id:
            department_id = principal.department_id
        elif department_id != principal.department_id:
            raise ApplicationError(
                "permission_denied",
                "You can only export your department's students"
            )
        query = query.where(Student.department_id == department_id)
    else:  # admin
        if department_id:
            query = query.where(Student.department_id == department_id)

    if semester:
        query = query.where(Student.semester == semester)

    # Fetch students
    students = await session.scalars(query)
    student_list = students.all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "name",
            "roll_number",
            "email",
            "phone",
            "department_id",
            "semester",
            "section",
            "created_at",
        ]
    )

    writer.writeheader()
    for student in student_list:
        writer.writerow({
            "id": str(student.id),
            "name": student.name,
            "roll_number": student.roll_number,
            "email": student.email,
            "phone": student.phone or "",
            "department_id": str(student.department_id),
            "semester": student.semester,
            "section": student.section,
            "created_at": student.created_at.isoformat() if student.created_at else "",
        })

    return output.getvalue()


# ============================================================================ #
# Import/Export Errors                                                         #
# ============================================================================ #

@dataclass
class ImportExportError:
    """Error during import/export."""
    row: int
    field: str
    message: str

    def to_dict(self) -> dict:
        return {
            "row": self.row,
            "field": self.field,
            "message": self.message,
        }


def validate_csv_headers(csv_content: str) -> list[str]:
    """Validate CSV headers are present."""
    reader = csv.DictReader(io.StringIO(csv_content))
    required_fields = [
        "name",
        "roll_number",
        "email",
        "department_code",
        "semester",
        "section",
    ]

    if not reader.fieldnames:
        raise ApplicationError("invalid_csv", "CSV has no headers")

    missing = [f for f in required_fields if f not in reader.fieldnames]
    if missing:
        raise ApplicationError(
            "invalid_csv",
            f"CSV missing required headers: {', '.join(missing)}"
        )

    return reader.fieldnames
