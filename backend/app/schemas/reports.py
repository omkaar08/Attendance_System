from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class DailyAttendanceRow(BaseModel):
    date: date
    total_records: int
    unique_students: int
    present_count: int
    present_percent: float


class DailyReportResponse(BaseModel):
    items: list[DailyAttendanceRow]
    total_rows: int


class MonthlyAttendanceRow(BaseModel):
    year: int
    month: int
    month_label: str
    total_records: int
    unique_students: int
    present_count: int
    present_percent: float


class MonthlyReportResponse(BaseModel):
    items: list[MonthlyAttendanceRow]
    total_rows: int


class SubjectAttendanceSummaryRow(BaseModel):
    subject_id: UUID
    subject_name: str
    subject_code: str
    department_id: UUID
    department_name: str
    faculty_id: UUID
    faculty_name: str
    semester: int
    section: str
    total_records: int
    unique_students: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percent: float


class SubjectReportResponse(BaseModel):
    items: list[SubjectAttendanceSummaryRow]
    total_rows: int


class StudentAttendanceSummaryRow(BaseModel):
    student_id: UUID
    full_name: str
    roll_number: str
    subject_id: UUID
    subject_name: str
    subject_code: str
    semester: int
    section: str
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percent: float


class StudentReportResponse(BaseModel):
    items: list[StudentAttendanceSummaryRow]
    total_rows: int


class DepartmentReportRow(BaseModel):
    department_id: UUID
    department_name: str
    department_code: str
    total_students: int
    total_faculty: int
    total_subjects: int
    total_sessions: int
    present_count: int
    attendance_percent: float


class DepartmentReportResponse(BaseModel):
    items: list[DepartmentReportRow]
    total_rows: int
