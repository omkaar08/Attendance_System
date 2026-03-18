"""
Face recognition pipeline — enrolment and identification.

Enrolment
---------
Accept raw image bytes for a student, run InsightFace analysis, persist the
512-d embedding vector in ``face_embeddings`` via async SQLAlchemy.

Identification
--------------
Accept a raw video frame, run InsightFace analysis to get one embedding per
face, and for each embedding perform a pgvector cosine-distance (<=>) query
restricted to the subject's cohort.  Matches above the configurable threshold
are returned and optionally auto-submitted to the attendance service.
"""
from __future__ import annotations

import base64
import binascii
import io
import threading
import time
from datetime import date
from uuid import UUID

import numpy as np
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import (
    Attendance,
    AttendanceStatus,
    FaceEmbedding,
    FaceEmbeddingStatus,
    FaceSampleSource,
    Student,
    Subject,
)
from app.schemas.recognition import (
    EmbeddingListResponse,
    EmbeddingMeta,
    EnrollRequest,
    EnrollResponse,
    IdentifyRequest,
    IdentifyResponse,
    RecognizedFace,
)
from app.services.face import EMBEDDING_DIM, FaceAnalyzer
from app.services.subjects import faculty_can_manage_cohort, get_subject_for_principal

# --------------------------------------------------------------------------- #
_LANDMARK_KEYS = ["left_eye", "right_eye", "nose", "left_mouth", "right_mouth"]

# --------------------------------------------------------------------------- #
#  Image compression helper                                                     #
# --------------------------------------------------------------------------- #

_MAX_IMAGE_DIM = 1280  # pixels — resize if larger, shrinks memory + model latency
_JPEG_QUALITY = 85


def _compress_image_bytes(raw: bytes) -> bytes:
    """
    Resize oversized images and re-encode as JPEG if PIL is available.
    Falls back silently to the original bytes on any error.
    """
    try:
        from PIL import Image  # noqa: PLC0415 — optional dep

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        if img.width > _MAX_IMAGE_DIM or img.height > _MAX_IMAGE_DIM:
            img.thumbnail((_MAX_IMAGE_DIM, _MAX_IMAGE_DIM), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return raw


# --------------------------------------------------------------------------- #
#  Cohort embedding cache                                                       #
# --------------------------------------------------------------------------- #

# Each entry: { cohort_key: (loaded_at, [(student_id, full_name, roll_number, np.ndarray)]) }
_COHORT_CACHE: dict[str, tuple[float, list[tuple[UUID, str, str, np.ndarray]]]] = {}
_COHORT_CACHE_TTL = 60.0  # seconds
_CACHE_LOCK = threading.Lock()


def _cohort_key(department_id: UUID, semester: int, section: str) -> str:
    return f"{department_id}:{semester}:{section}"


def _invalidate_cohort(department_id: UUID, semester: int, section: str) -> None:
    """Remove stale cohort from cache after a new enrollment."""
    key = _cohort_key(department_id, semester, section)
    with _CACHE_LOCK:
        _COHORT_CACHE.pop(key, None)


async def _load_cohort_embeddings(
    session,
    department_id: UUID,
    semester: int,
    section: str,
) -> list[tuple[UUID, str, str, np.ndarray]]:
    """
    Return active embedding vectors for the given cohort.  Results are cached
    in process memory for ``_COHORT_CACHE_TTL`` seconds so that each polling
    frame does not hit the database once per face.
    """
    key = _cohort_key(department_id, semester, section)
    now = time.monotonic()

    with _CACHE_LOCK:
        entry = _COHORT_CACHE.get(key)
        if entry is not None and (now - entry[0]) < _COHORT_CACHE_TTL:
            return entry[1]

    rows = (
        await session.execute(
            select(
                FaceEmbedding.student_id,
                FaceEmbedding.embedding,
                Student.full_name,
                Student.roll_number,
            )
            .join(Student, Student.id == FaceEmbedding.student_id)
            .where(
                FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE,
                Student.department_id == department_id,
                Student.semester == semester,
                Student.section == section,
                Student.status == "active",
            )
        )
    ).all()

    data: list[tuple[UUID, str, str, np.ndarray]] = [
        (row.student_id, row.full_name, row.roll_number, np.array(row.embedding, dtype=np.float32))
        for row in rows
    ]

    with _CACHE_LOCK:
        _COHORT_CACHE[key] = (time.monotonic(), data)

    return data


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


# --------------------------------------------------------------------------- #


def _decode_base64_image(b64: str) -> bytes:
    """Strip optional data-URI prefix and decode base64 to raw bytes."""
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    try:
        return base64.b64decode(b64)
    except binascii.Error as exc:
        raise ApplicationError(
            status_code=400,
            code="invalid_image",
            message="Image data is not valid base64.",
        ) from exc


# --------------------------------------------------------------------------- #
#  Enrolment                                                                    #
# --------------------------------------------------------------------------- #

async def enroll_face(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: EnrollRequest,
) -> EnrollResponse:
    """
    Extract an ArcFace embedding from *payload.image_base64* and store it in
    ``face_embeddings``.  Enforces:
    - single-face images only
    - minimum detection quality
    - faculty/HOD/admin can only enrol students in their cohort
    """
    settings = get_settings()

    # --- verify student exists and caller may manage them
    student = (
        await session.execute(select(Student).where(Student.id == payload.student_id))
    ).scalar_one_or_none()
    if student is None:
        raise ApplicationError(status_code=404, code="student_not_found", message="Student not found.")

    can_manage = await faculty_can_manage_cohort(
        session=session,
        principal=principal,
        department_id=student.department_id,
        semester=student.semester,
        section=student.section,
    )
    if not can_manage:
        raise ApplicationError(
            status_code=403,
            code="enroll_forbidden",
            message="You cannot enrol faces for this student.",
        )

    # --- run face analysis (compress oversized images first)
    image_bytes = _compress_image_bytes(_decode_base64_image(payload.image_base64))
    try:
        analyzer = FaceAnalyzer.get()
        faces = analyzer.analyze(image_bytes)
    except Exception as exc:  # noqa: BLE001
        raise ApplicationError(
            status_code=503,
            code="face_model_unavailable",
            message="Face recognition engine is not available on this server.",
        ) from exc

    if not faces:
        raise ApplicationError(status_code=400, code="no_face_detected", message="No face detected in the image.")
    if len(faces) > 1:
        raise ApplicationError(
            status_code=400,
            code="multiple_faces",
            message=f"Found {len(faces)} faces. Please use a single-face image.",
        )

    face = faces[0]
    if face.quality_score < settings.face_min_quality_score:
        raise ApplicationError(
            status_code=400,
            code="low_quality_face",
            message=(
                f"Detection quality {face.quality_score:.2f} is below the minimum "
                f"{settings.face_min_quality_score:.2f}. Ensure good lighting and a clear view."
            ),
        )

    # --- determine is_primary (first active embedding for this student)
    existing_count: int = (
        await session.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.student_id == payload.student_id,
                FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE,
            )
        )
    ).scalars().all().__len__()  # noqa: SLF001

    row = FaceEmbedding(
        student_id=payload.student_id,
        embedding=face.embedding,
        model_name=analyzer.model_name,
        model_version=analyzer.model_version,
        sample_source=FaceSampleSource(payload.source),
        storage_path=payload.storage_path,
        quality_score=face.quality_score,
        landmarks=face.landmarks,
        is_primary=existing_count == 0,
        status=FaceEmbeddingStatus.ACTIVE,
        created_by=principal.user_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Invalidate the cohort cache so the new embedding is picked up immediately.
    _invalidate_cohort(student.department_id, student.semester, student.section)

    warning = None
    if existing_count >= settings.face_max_embeddings_per_student:
        warning = (
            f"Student already has {existing_count} active embeddings. "
            "Consider removing older ones."
        )

    return EnrollResponse(embedding=EmbeddingMeta.model_validate(row), warning=warning)


# --------------------------------------------------------------------------- #
#  Identification                                                               #
# --------------------------------------------------------------------------- #

async def identify_faces(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: IdentifyRequest,
) -> IdentifyResponse:
    """
    Detect all faces in *payload.frame_base64*, match each to the closest
    student embedding in the subject's cohort using pgvector cosine distance,
    and optionally auto-mark attendance.
    """
    settings = get_settings()
    subject = await get_subject_for_principal(session, principal, payload.subject_id)

    image_bytes = _compress_image_bytes(_decode_base64_image(payload.frame_base64))
    try:
        analyzer = FaceAnalyzer.get()
        faces = analyzer.analyze(image_bytes)
    except Exception as exc:  # noqa: BLE001
        raise ApplicationError(
            status_code=503,
            code="face_model_unavailable",
            message="Face recognition engine is not available on this server.",
        ) from exc

    if not faces:
        return IdentifyResponse(recognized=[], frame_face_count=0, unmatched_face_count=0)

    threshold: float = settings.face_recognition_threshold

    # Load cohort embeddings once (cached in process memory, TTL=60 s).
    # This replaces N per-face pgvector queries with one DB load + numpy ops.
    cohort = await _load_cohort_embeddings(
        session, subject.department_id, subject.semester, subject.section
    )

    recognized: list[RecognizedFace] = []
    matched_student_ids: set[UUID] = set()

    for face in faces:
        face_vec = np.array(face.embedding, dtype=np.float32)

        best_idx = -1
        best_sim = -1.0
        for idx, (_sid, _fn, _rn, stored_vec) in enumerate(cohort):
            sim = _cosine_similarity(face_vec, stored_vec)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx

        if best_idx == -1:
            continue

        confidence = round(best_sim, 4)
        if confidence < threshold:
            continue

        student_id, full_name, roll_number, _ = cohort[best_idx]

        # deduplicate: one recognition result per student per frame
        if student_id in matched_student_ids:
            continue
        matched_student_ids.add(student_id)

        attendance_id: UUID | None = None
        attendance_marked = False

        if payload.auto_mark_attendance:
            # check for existing attendance first (anti-duplicate)
            existing = (
                await session.execute(
                    select(Attendance.id)
                    .where(
                        Attendance.student_id == student_id,
                        Attendance.subject_id == subject.id,
                        Attendance.class_date == payload.class_date,
                        Attendance.session_key == payload.session_key,
                    )
                    .order_by(Attendance.created_at.desc())
                    .limit(1)
                )
            ).scalar()

            if existing is not None:
                attendance_id = existing
            else:
                record = Attendance(
                    student_id=student_id,
                    subject_id=subject.id,
                    faculty_id=subject.faculty_id,
                    marked_by_user_id=principal.user_id,
                    class_date=payload.class_date,
                    session_key=payload.session_key,
                    session_label=payload.session_label,
                    status=AttendanceStatus.PRESENT,
                    confidence_score=confidence,
                    recognition_metadata={
                        "source": "face_recognition",
                        "model": analyzer.model_name,
                        "model_version": analyzer.model_version,
                    },
                )
                session.add(record)
                await session.flush()
                attendance_id = record.id
                attendance_marked = True

        recognized.append(
            RecognizedFace(
                student_id=student_id,
                full_name=full_name,
                roll_number=roll_number,
                confidence=confidence,
                attendance_marked=attendance_marked,
                attendance_id=attendance_id,
            )
        )

    if payload.auto_mark_attendance and any(r.attendance_marked for r in recognized):
        await session.commit()

    unmatched = len(faces) - len(recognized)
    return IdentifyResponse(
        recognized=recognized,
        frame_face_count=len(faces),
        unmatched_face_count=max(unmatched, 0),
    )


# --------------------------------------------------------------------------- #
#  Embedding management                                                         #
# --------------------------------------------------------------------------- #

async def list_embeddings(
    *,
    session: AsyncSession,
    principal: Principal,
    student_id: UUID,
) -> EmbeddingListResponse:
    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        raise ApplicationError(status_code=404, code="student_not_found", message="Student not found.")

    can_manage = await faculty_can_manage_cohort(
        session=session,
        principal=principal,
        department_id=student.department_id,
        semester=student.semester,
        section=student.section,
    )
    if not can_manage:
        raise ApplicationError(
            status_code=403,
            code="embed_list_forbidden",
            message="You cannot view embeddings for this student.",
        )

    rows = (
        await session.execute(
            select(FaceEmbedding)
            .where(FaceEmbedding.student_id == student_id)
            .order_by(FaceEmbedding.created_at.desc())
        )
    ).scalars().all()

    items = [EmbeddingMeta.model_validate(r) for r in rows]
    return EmbeddingListResponse(items=items, total=len(items))


async def delete_embedding(
    *,
    session: AsyncSession,
    principal: Principal,
    embedding_id: UUID,
) -> None:
    """Soft-delete: mark embedding ``deprecated`` rather than hard-deleting."""
    row = (
        await session.execute(
            select(FaceEmbedding).where(FaceEmbedding.id == embedding_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise ApplicationError(status_code=404, code="embedding_not_found", message="Embedding not found.")

    student = (
        await session.execute(select(Student).where(Student.id == row.student_id))
    ).scalar_one_or_none()

    can_manage = student is not None and await faculty_can_manage_cohort(
        session=session,
        principal=principal,
        department_id=student.department_id,
        semester=student.semester,
        section=student.section,
    )
    if not can_manage:
        raise ApplicationError(
            status_code=403,
            code="embed_delete_forbidden",
            message="You cannot delete this embedding.",
        )

    row.status = FaceEmbeddingStatus.DEPRECATED
    await session.commit()
