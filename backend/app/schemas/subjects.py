from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import SubjectSummary


class SubjectAssignmentRequest(BaseModel):
    faculty_id: UUID


class SubjectCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=255)
    semester: int = Field(ge=1, le=12)
    section: str = Field(min_length=1, max_length=20)
    faculty_id: UUID
    attendance_grace_minutes: int = Field(default=15, ge=0, le=240)


class SubjectResponse(SubjectSummary):
    pass