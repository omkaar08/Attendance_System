from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    total_students: int
    total_faculty: int
    total_subjects: int
    today_attendance_percent: float
    average_attendance_percent: float