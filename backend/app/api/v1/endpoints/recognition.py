from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.core.security import Principal
from app.db.models import AppRole
from app.db.session import get_db_session
from app.schemas.recognition import (
    EmbeddingListResponse,
    EnrollRequest,
    EnrollResponse,
    IdentifyRequest,
    IdentifyResponse,
)
from app.services.recognition import delete_embedding, enroll_face, identify_faces, list_embeddings

router = APIRouter()


@router.post("/enroll", summary="Enrol a student face and store embedding")
async def enroll_student_face(
    payload: EnrollRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EnrollResponse:
    """
    Accept a base64-encoded image, detect the face, extract a 512-d ArcFace
    embedding, and persist it in ``face_embeddings``.

    - Rejects images with 0 or 2+ faces.
    - Stores quality score, landmarks, and the source bucket path.
    """
    return await enroll_face(session=session, principal=principal, payload=payload)


@router.post("/identify", summary="Identify faces in a frame and optionally mark attendance")
async def identify_frame(
    payload: IdentifyRequest,
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IdentifyResponse:
    """
    Accept a single base64-encoded video frame, detect all faces, match each
    to the closest active student embedding in the subject cohort using
    pgvector cosine distance, and (when ``auto_mark_attendance=true``) record
    attendance for every match above the configured confidence threshold.

    Duplicate attendance for the same student / subject / date / session is
    silently skipped (idempotent).
    """
    return await identify_faces(session=session, principal=principal, payload=payload)


@router.get(
    "/students/{student_id}/embeddings",
    summary="List face embeddings for a student",
)
async def get_student_embeddings(
    student_id: Annotated[UUID, Path()],
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EmbeddingListResponse:
    return await list_embeddings(session=session, principal=principal, student_id=student_id)


@router.delete(
    "/embeddings/{embedding_id}",
    status_code=204,
    summary="Soft-delete a face embedding",
)
async def remove_embedding(
    embedding_id: Annotated[UUID, Path()],
    principal: Annotated[Principal, Depends(require_roles(AppRole.FACULTY, AppRole.HOD, AppRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    await delete_embedding(session=session, principal=principal, embedding_id=embedding_id)
