from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    attendance,
    auth,
    extended,
    faculty,
    management,
    recognition,
    reports,
    students,
    subjects,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(faculty.router, prefix="/faculty", tags=["faculty"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(recognition.router, prefix="/recognition", tags=["recognition"])
api_router.include_router(management.router, prefix="/management", tags=["management"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(extended.router, tags=["extended", "recognition", "batch", "audit"])