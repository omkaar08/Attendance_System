from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import StudentSummary


class StudentRegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    roll_number: str = Field(min_length=1, max_length=50)
    department_id: UUID
    semester: int = Field(ge=1, le=12)
    section: str = Field(min_length=1, max_length=20)
    batch_year: int = Field(ge=2000, le=2100)
    email: EmailStr | None = None


class StudentResponse(StudentSummary):
    pass


class StudentListResponse(BaseModel):
    items: list[StudentSummary]


class FaceUploadRequest(BaseModel):
    student_id: UUID
    file_name: str = Field(min_length=3, max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    asset_kind: Literal["student-image", "face-training"] = "face-training"


class FaceUploadResponse(BaseModel):
    bucket: str
    storage_path: str
    signed_upload_url: str
    token: str | None = None
    expires_in: int
    created_at: datetime