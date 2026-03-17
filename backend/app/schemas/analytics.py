from uuid import UUID

from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    total_students: int
    total_faculty: int
    total_subjects: int
    today_attendance_percent: float
    average_attendance_percent: float


class SubjectAttendanceItem(BaseModel):
    subject_id: UUID
    subject_name: str
    subject_code: str
    attendance_percent: float


class SubjectAttendanceResponse(BaseModel):
    items: list[SubjectAttendanceItem]