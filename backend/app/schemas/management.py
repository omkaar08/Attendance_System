from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class DepartmentCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=255)


class DepartmentManagementSummary(BaseModel):
    id: UUID
    code: str
    name: str
    hod_user_id: UUID | None = None
    hod_name: str | None = None
    hod_email: str | None = None
    total_students: int
    total_faculty: int
    total_subjects: int
    attendance_percent: float


class DepartmentListResponse(BaseModel):
    items: list[DepartmentManagementSummary]


class FacultyCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    employee_code: str = Field(min_length=2, max_length=50)
    designation: str = Field(min_length=2, max_length=120)
    department_id: UUID | None = None


class FacultyManagementSummary(BaseModel):
    faculty_id: UUID
    user_id: UUID
    full_name: str
    email: str
    employee_code: str
    designation: str
    department_id: UUID
    assigned_subject_count: int


class FacultyListResponse(BaseModel):
    items: list[FacultyManagementSummary]


class HodCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    employee_code: str = Field(min_length=2, max_length=50)
    designation: str = Field(default="Head of Department", min_length=2, max_length=120)
