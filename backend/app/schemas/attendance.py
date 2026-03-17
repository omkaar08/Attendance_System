from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import AttendanceStatus


class AttendanceEntry(BaseModel):
    student_id: UUID
    confidence_score: float = Field(ge=0.0, le=1.0)
    recognition_metadata: dict = Field(default_factory=dict)
    status: AttendanceStatus = AttendanceStatus.PRESENT


class AttendanceMarkRequest(BaseModel):
    subject_id: UUID
    class_date: date
    session_key: str = Field(min_length=1, max_length=80)
    session_label: str = Field(min_length=1, max_length=120)
    entries: list[AttendanceEntry] = Field(min_length=1, max_length=200)


class AttendanceAccepted(BaseModel):
    student_id: UUID
    attendance_id: UUID
    confidence_score: float
    created_at: datetime


class AttendanceDuplicate(BaseModel):
    student_id: UUID
    reason: str


class AttendanceMarkResponse(BaseModel):
    accepted: list[AttendanceAccepted]
    duplicates: list[AttendanceDuplicate]


class AttendanceReportItem(BaseModel):
    id: UUID
    student_id: UUID
    student_name: str
    roll_number: str
    subject_id: UUID
    subject_name: str
    faculty_id: UUID
    class_date: date
    session_key: str
    session_label: str
    status: AttendanceStatus
    confidence_score: float
    captured_at: datetime


class AttendanceReportSummary(BaseModel):
    total_records: int
    present_count: int
    late_count: int
    average_confidence_score: float | None = None


class AttendanceReportResponse(BaseModel):
    items: list[AttendanceReportItem]
    summary: AttendanceReportSummary


class LowAttendanceAlertItem(BaseModel):
    student_id: UUID
    full_name: str
    roll_number: str
    subject_id: UUID
    subject_name: str
    department_id: UUID
    semester: int
    section: str
    total_sessions: int
    present_sessions: int
    attendance_percent: float


class LowAttendanceAlertResponse(BaseModel):
    threshold_percent: float
    min_sessions: int
    items: list[LowAttendanceAlertItem]