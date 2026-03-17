from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models import AppRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class SubjectSummary(ORMModel):
    id: UUID
    code: str
    name: str
    department_id: UUID
    semester: int
    section: str
    faculty_id: UUID
    is_active: bool


class StudentSummary(ORMModel):
    id: UUID
    full_name: str
    roll_number: str
    department_id: UUID
    semester: int
    section: str
    batch_year: int
    email: str | None = None
    image_url: str | None = None
    created_at: datetime


class UserSummary(ORMModel):
    id: UUID
    email: str
    role: AppRole
    department_id: UUID | None = None