from pydantic import BaseModel

from app.schemas.common import SubjectSummary


class SubjectListResponse(BaseModel):
    items: list[SubjectSummary]