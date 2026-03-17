from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# --------------------------------------------------------------------------- #
#  Enrolment                                                                    #
# --------------------------------------------------------------------------- #

class EnrollRequest(BaseModel):
    student_id: UUID
    image_base64: str = Field(min_length=10, description="Base64-encoded JPEG / PNG / WebP image.")
    source: Literal["camera", "upload", "imported"] = "upload"
    storage_path: str | None = Field(default=None, max_length=500)


class EmbeddingMeta(ORMModel):
    id: UUID
    student_id: UUID
    model_name: str
    model_version: str
    sample_source: str
    quality_score: float
    is_primary: bool
    status: str
    storage_path: str | None = None
    created_at: datetime


class EnrollResponse(BaseModel):
    embedding: EmbeddingMeta
    warning: str | None = None


# --------------------------------------------------------------------------- #
#  Identification                                                               #
# --------------------------------------------------------------------------- #

class IdentifyRequest(BaseModel):
    frame_base64: str = Field(
        min_length=10,
        description="Base64-encoded single video frame (JPEG / PNG / WebP).",
    )
    subject_id: UUID
    class_date: date
    session_key: str = Field(min_length=1, max_length=80)
    session_label: str = Field(default="", max_length=120)
    auto_mark_attendance: bool = True


class RecognizedFace(BaseModel):
    student_id: UUID
    full_name: str
    roll_number: str
    confidence: float
    attendance_marked: bool
    attendance_id: UUID | None = None


class IdentifyResponse(BaseModel):
    recognized: list[RecognizedFace]
    frame_face_count: int
    unmatched_face_count: int


# --------------------------------------------------------------------------- #
#  Embedding management                                                         #
# --------------------------------------------------------------------------- #

class EmbeddingListResponse(BaseModel):
    items: list[EmbeddingMeta]
    total: int
