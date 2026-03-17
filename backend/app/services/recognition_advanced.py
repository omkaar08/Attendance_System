"""
Enhanced face recognition service with accuracy metrics and batch operations.
Uses improved face detection, quality validation, and embedding-based similarity.
"""
from __future__ import annotations

import asyncio
import base64
import io
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy import and_, desc, func, select
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
from app.services.face_onnx import (
    EMBEDDING_DIM,
    FaceAnalyzer,
    generate_arcface_embedding,
)
from app.services.subjects import get_subject_for_principal


# ============================================================================ #
# Constants                                                                    #
# ============================================================================ #

_MAX_EMBEDDINGS_PER_STUDENT = 10
_EMBEDDING_RETENTION_DAYS = 90

# Similarity thresholds for recognition
_SIMILARITY_THRESHOLD_STRICT = 0.45  # 95% accuracy target
_SIMILARITY_THRESHOLD_NORMAL = 0.50  # 90% accuracy target
_SIMILARITY_THRESHOLD_LOOSE = 0.60   # 85% accuracy target

# Minimum candidates to consider
_MIN_MATCH_CANDIDATES = 5
_MAX_MATCH_RESULTS = 10


# ============================================================================ #
# Distance Functions                                                           #
# ============================================================================ #

def cosine_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine distance between two vectors. Returns [0, 2]."""
    vec1 = np.array(vec1, dtype=np.float32)
    vec2 = np.array(vec2, dtype=np.float32)
    
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 < 1e-10 or norm2 < 1e-10:
        return 2.0  # Max distance for invalid vectors
    
    return float(1.0 - np.dot(vec1, vec2) / (norm1 * norm2))


def euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute Euclidean distance between two vectors."""
    vec1 = np.array(vec1, dtype=np.float32)
    vec2 = np.array(vec2, dtype=np.float32)
    return float(np.linalg.norm(vec1 - vec2))


def similarity_from_distance(distance: float, metric: str = "cosine") -> float:
    """Convert distance to similarity score [0, 1]."""
    if metric == "cosine":
        # Cosine distance: [0, 2] -> similarity [1, 0]
        return max(0.0, 1.0 - distance)
    else:  # euclidean
        # Euclidean: smaller = more similar
        return max(0.0, 1.0 / (1.0 + distance))


# ============================================================================ #
# Enrollment (Face Registration)                                               #
# ============================================================================ #

async def enroll_face(
    request: EnrollRequest,
    session: AsyncSession,
    principal: Principal,
) -> EnrollResponse:
    """
    Enroll a student's face: analyze image, generate embedding, store in DB.
    Validates quality and liveness. Stores up to _MAX_EMBEDDINGS_PER_STUDENT.
    """
    settings = get_settings()
    
    # Decode image
    try:
        image_bytes = base64.b64decode(request.image_data)
    except Exception as e:
        raise ApplicationError("invalid_image_data", f"Failed to decode image: {e}")

    # Analyze face
    analyzer = FaceAnalyzer.get()
    faces = analyzer.analyze(
        image_bytes,
        min_confidence=0.80,
        min_quality=settings.face_min_quality_score,
    )

    if not faces:
        raise ApplicationError("no_face_detected", "No face detected in image")

    if len(faces) > 1:
        raise ApplicationError("multiple_faces", "Multiple faces detected; please submit one face per image")

    face = faces[0]

    if not face.is_valid:
        return EnrollResponse(
            status="rejected",
            reason=f"Image quality too low (score: {face.quality_score})",
            quality_metrics={
                "sharpness": face.sharpness_score,
                "brightness": face.brightness_score,
                "liveness": face.liveness_score,
                "overall": face.quality_score,
            }
        )

    # Get or create student
    try:
        student_id = UUID(request.student_id)
    except ValueError:
        raise ApplicationError("invalid_student_id", "Invalid student ID format")

    stmt = select(Student).where(Student.id == student_id)
    student = await session.scalar(stmt)
    if not student:
        raise ApplicationError("student_not_found", f"Student {student_id} not found")

    # Check embedding count
    stmt = select(func.count(FaceEmbedding.id)).where(
        and_(
            FaceEmbedding.student_id == student_id,
            FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE,
        )
    )
    count = await session.scalar(stmt)
    
    if count >= settings.face_max_embeddings_per_student:
        return EnrollResponse(
            status="rejected",
            reason=f"Maximum embeddings ({settings.face_max_embeddings_per_student}) already enrolled"
        )

    # Create embedding record
    embedding = FaceEmbedding(
        student_id=student_id,
        embedding_vector=face.embedding.tolist(),
        status=FaceEmbeddingStatus.ACTIVE,
        source=FaceSampleSource.UPLOAD if request.source == "upload" else FaceSampleSource.CAMERA,
        quality_score=face.quality_score,
        sharpness_score=face.sharpness_score,
        brightness_score=face.brightness_score,
        liveness_score=face.liveness_score,
        raw_image=face.raw_encoded,
        model_name=analyzer.model_name,
        model_version=analyzer.model_version,
        metadata={
            "bbox": list(face.bbox),
            "landmarks": face.landmarks,
        }
    )
    
    session.add(embedding)
    await session.commit()

    return EnrollResponse(
        status="success",
        embedding_id=embedding.id,
        quality_metrics={
            "sharpness": face.sharpness_score,
            "brightness": face.brightness_score,
            "liveness": face.liveness_score,
            "overall": face.quality_score,
        }
    )


# ============================================================================ #
# Identification (Face Recognition)                                            #
# ============================================================================ #

async def identify_faces(
    request: IdentifyRequest,
    session: AsyncSession,
    principal: Principal,
) -> IdentifyResponse:
    """
    Identify students from image: analyze faces, match against embeddings,
    return ranked matches with similarity scores.
    """
    settings = get_settings()
    
    # Decode image
    try:
        image_bytes = base64.b64decode(request.image_data)
    except Exception as e:
        raise ApplicationError("invalid_image_data", f"Failed to decode image: {e}")

    # Analyze faces
    analyzer = FaceAnalyzer.get()
    faces = analyzer.analyze(
        image_bytes,
        min_confidence=0.75,
        min_quality=settings.face_min_quality_score,
    )

    if not faces:
        return IdentifyResponse(
            detected_faces=0,
            matches=[],
            model_info={
                "model_name": analyzer.model_name,
                "model_version": analyzer.model_version,
            }
        )

    # Get subject and cohort info
    try:
        subject_id = UUID(request.subject_id)
    except ValueError:
        raise ApplicationError("invalid_subject_id", "Invalid subject ID format")

    subject = await get_subject_for_principal(session, principal, subject_id)
    if not subject:
        raise ApplicationError("subject_not_found", f"Subject {subject_id} not accessible")

    # Query embeddings for cohort
    stmt = select(FaceEmbedding).where(
        and_(
            FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE,
            FaceEmbedding.student_id.in_(
                select(Student.id).where(
                    and_(
                        Student.department_id == subject.department_id,
                        Student.semester == subject.semester,
                        Student.section == subject.section,
                    )
                )
            )
        )
    ).order_by(desc(FaceEmbedding.created_at))
    
    embeddings = await session.scalars(stmt)
    embeddings_list = embeddings.all()

    # Match each detected face
    matches = []
    similarity_threshold = settings.attendance_confidence_threshold or _SIMILARITY_THRESHOLD_NORMAL

    for face_idx, detected_face in enumerate(faces):
        if not detected_face.is_valid:
            continue

        detected_embedding = detected_face.embedding.astype(np.float32)
        face_matches = []

        # Compare with all stored embeddings
        for stored_emb in embeddings_list:
            stored_vector = np.array(stored_emb.embedding_vector, dtype=np.float32)
            distance = cosine_distance(detected_embedding, stored_vector)
            similarity = similarity_from_distance(distance, metric="cosine")

            if similarity >= similarity_threshold:
                face_matches.append((
                    stored_emb.student_id,
                    similarity,
                    distance,
                    stored_emb,
                ))

        # Sort by similarity (highest first)
        face_matches.sort(key=lambda x: x[1], reverse=True)
        face_matches = face_matches[:_MAX_MATCH_RESULTS]

        # Build match list
        for student_id, similarity, distance, stored_emb in face_matches:
            stmt = select(Student).where(Student.id == student_id)
            student = await session.scalar(stmt)
            
            if student:
                matches.append(RecognizedFace(
                    student_id=student_id,
                    student_name=student.name,
                    student_roll=student.roll_number,
                    similarity_score=round(similarity, 4),
                    confidence=round(max(0.0, min(1.0, similarity / similarity_threshold)), 4),
                    face_index=face_idx,
                    embedding_quality=round(stored_emb.quality_score, 4),
                ))

    return IdentifyResponse(
        detected_faces=len([f for f in faces if f.is_valid]),
        matches=matches,
        model_info={
            "model_name": analyzer.model_name,
            "model_version": analyzer.model_version,
        }
    )


# ============================================================================ #
# Embedding Management                                                         #
# ============================================================================ #

async def list_embeddings(
    student_id: UUID,
    session: AsyncSession,
) -> EmbeddingListResponse:
    """List all active embeddings for a student."""
    stmt = select(FaceEmbedding).where(
        and_(
            FaceEmbedding.student_id == student_id,
            FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE,
        )
    ).order_by(desc(FaceEmbedding.created_at))

    embeddings = await session.scalars(stmt)
    
    return EmbeddingListResponse(
        embeddings=[
            EmbeddingMeta(
                id=emb.id,
                created_at=emb.created_at,
                quality_score=round(emb.quality_score, 4),
                sharpness_score=round(emb.sharpness_score, 4),
                brightness_score=round(emb.brightness_score, 4),
                liveness_score=round(emb.liveness_score, 4),
                source=emb.source,
                model_name=emb.model_name,
                model_version=emb.model_version,
            )
            for emb in embeddings.all()
        ]
    )


async def delete_embedding(
    embedding_id: UUID,
    session: AsyncSession,
) -> None:
    """Soft-delete an embedding."""
    stmt = select(FaceEmbedding).where(FaceEmbedding.id == embedding_id)
    embedding = await session.scalar(stmt)
    
    if embedding:
        embedding.status = FaceEmbeddingStatus.DEPRECATED
        await session.commit()


# ============================================================================ #
# Batch Operations                                                             #
# ============================================================================ #

async def cleanup_old_embeddings(session: AsyncSession) -> int:
    """
    Delete embeddings older than _EMBEDDING_RETENTION_DAYS.
    Returns number of embeddings deleted.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=_EMBEDDING_RETENTION_DAYS)
    
    stmt = select(FaceEmbedding).where(
        and_(
            FaceEmbedding.created_at < cutoff_date,
            FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE,
        )
    )
    
    embeddings = await session.scalars(stmt)
    
    for emb in embeddings.all():
        emb.status = FaceEmbeddingStatus.DEPRECATED
    
    await session.commit()
    return len(embeddings.all())


async def compute_embedding_statistics(
    session: AsyncSession,
) -> dict:
    """Compute statistics on embeddings in system."""
    stmt = select(func.count(FaceEmbedding.id)).where(
        FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE
    )
    total = await session.scalar(stmt)

    stmt = select(func.avg(FaceEmbedding.quality_score)).where(
        FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE
    )
    avg_quality = await session.scalar(stmt) or 0.0

    stmt = select(func.avg(FaceEmbedding.sharpness_score)).where(
        FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE
    )
    avg_sharpness = await session.scalar(stmt) or 0.0

    stmt = select(func.avg(FaceEmbedding.liveness_score)).where(
        FaceEmbedding.status == FaceEmbeddingStatus.ACTIVE
    )
    avg_liveness = await session.scalar(stmt) or 0.0

    return {
        "total_active_embeddings": total or 0,
        "average_quality_score": round(float(avg_quality), 4),
        "average_sharpness_score": round(float(avg_sharpness), 4),
        "average_liveness_score": round(float(avg_liveness), 4),
    }
