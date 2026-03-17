"""
Extended recognition and batch operations API endpoints.
These routes integrate the advanced face recognition, real-time notifications,
audit logging, and batch operations.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_principal
from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.session import get_db_session
from app.schemas.recognition import (
    EnrollRequest,
    EnrollResponse,
    IdentifyRequest,
    IdentifyResponse,
    EmbeddingListResponse,
)
from app.services.recognition_advanced import (
    enroll_face,
    identify_faces,
    list_embeddings,
    delete_embedding,
    cleanup_old_embeddings,
    compute_embedding_statistics,
)
from app.services.batch import (
    import_students_csv,
    export_students_csv,
    validate_csv_headers,
)
from app.services.websocket import (
    manager,
    websocket_handler,
)
from app.services.audit import (
    log_face_enrolled,
    get_audit_logs,
)

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["extended"])


# ============================================================================ #
# Face Recognition Endpoints                                                   #
# ============================================================================ #

@router.post("/recognition/enroll")
async def enroll_student_face(
    request: EnrollRequest,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> EnrollResponse:
    """
    Enroll a student's face with quality validation and liveness detection.
    
    Returns quality metrics:
    - sharpness: [0, 1] - image clarity
    - brightness: [0, 1] - optimal lighting
    - liveness: [0, 1] - anti-spoofing score
    - overall: [0, 1] - composite quality
    """
    try:
        result = await enroll_face(request, session, principal)
        
        # Log successful enrollments
        if result.status == "success":
            await log_face_enrolled(
                session,
                str(principal.user_id),
                principal.role,
                request.student_id,
                result.quality_metrics.get("overall", 0.0),
            )
        
        return result
    except ApplicationError as e:
        _logger.warning(f"Face enrollment failed: {e}")
        raise
    except Exception as e:
        _logger.error(f"Unexpected error in face enrollment: {e}")
        raise ApplicationError("enrollment_error", str(e))


@router.post("/recognition/identify")
async def identify_faces_endpoint(
    request: IdentifyRequest,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> IdentifyResponse:
    """
    Identify students from an image containing multiple faces.
    Returns ranked matches with similarity scores.
    
    Response fields:
    - detected_faces: Number of valid faces detected
    - matches: List of recognized students with confidence
    - model_info: Current model name and version
    """
    try:
        return await identify_faces(request, session, principal)
    except ApplicationError as e:
        _logger.warning(f"Face identification failed: {e}")
        raise
    except Exception as e:
        _logger.error(f"Unexpected error in face identification: {e}")
        raise ApplicationError("identification_error", str(e))


@router.get("/recognition/embeddings/{student_id}")
async def list_student_embeddings(
    student_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> EmbeddingListResponse:
    """
    List all active face embeddings for a student.
    Includes quality metrics and enrollment source.
    """
    try:
        return await list_embeddings(student_id, session)
    except Exception as e:
        _logger.error(f"Error listing embeddings: {e}")
        raise ApplicationError("list_error", str(e))


@router.delete("/recognition/embeddings/{embedding_id}")
async def delete_student_embedding(
    embedding_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """
    Soft-delete a face embedding (marks as deprecated, doesn't remove).
    """
    try:
        await delete_embedding(embedding_id, session)
        return {"status": "deleted", "embedding_id": str(embedding_id)}
    except Exception as e:
        _logger.error(f"Error deleting embedding: {e}")
        raise ApplicationError("delete_error", str(e))


@router.get("/recognition/statistics")
async def get_recognition_statistics(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """
    Get system-wide face recognition statistics.
    """
    try:
        stats = await compute_embedding_statistics(session)
        return {
            "status": "success",
            "data": stats,
        }
    except Exception as e:
        _logger.error(f"Error computing statistics: {e}")
        raise ApplicationError("stats_error", str(e))


# ============================================================================ #
# Batch Operations Endpoints                                                   #
# ============================================================================ #

@router.post("/students/import-csv")
async def import_students(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """
    Bulk import students from CSV file.
    
    CSV format:
    name,roll_number,email,department_code,semester,section,phone
    John Doe,CSE001,john@example.com,CSE,1,A,9876543210
    
    Returns import results with success/failure counts.
    """
    if principal.role not in ("admin", "hod"):
        raise ApplicationError("permission_denied", "Only HOD or Admin can import students")

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
        
        # Validate headers
        validate_csv_headers(csv_content)
        
        # Import
        result = await import_students_csv(csv_content, session, principal)
        
        return {
            "status": "completed",
            "total_rows": result.total_rows,
            "successful": result.successful,
            "failed": result.failed,
            "skipped": result.skipped,
            "errors": result.errors,
            "timestamp": result.timestamp,
        }
    except ApplicationError:
        raise
    except Exception as e:
        _logger.error(f"CSV import error: {e}")
        raise ApplicationError("import_error", str(e))


@router.get("/students/export-csv")
async def export_students(
    department_id: Optional[UUID] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=8),
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """
    Export students as CSV file.
    HOD can only export their department's students.
    Admin can export all or filtered by department.
    """
    try:
        csv_content = await export_students_csv(
            session,
            principal,
            department_id=department_id,
            semester=semester,
        )
        
        return {
            "status": "success",
            "format": "csv",
            "content": csv_content,
        }
    except ApplicationError:
        raise
    except Exception as e:
        _logger.error(f"CSV export error: {e}")
        raise ApplicationError("export_error", str(e))


# ============================================================================ #
# WebSocket Endpoints (Real-Time Notifications)                                #
# ============================================================================ #

@router.websocket("/ws/attendance/{subject_id}/{user_id}")
async def websocket_attendance(
    websocket: WebSocket,
    subject_id: str,
    user_id: str,
) -> None:
    """
    WebSocket endpoint for real-time attendance notifications.
    
    Expected flow:
    1. Client connects: GET /ws/attendance/{subject_id}/{user_id}
    2. Server accepts and stores connection
    3. Client sends periodic "ping" messages to keep alive
    4. Server broadcasts "attendance_marked" events to all connected clients
    
    Event formats:
    ```json
    {
      "type": "attendance_marked",
      "data": {
        "student_id": "...",
        "student_name": "...",
        "status": "present",
        "confidence": 0.95,
        ...
      }
    }
    ```
    """
    try:
        # For now, store a placeholder user name (would be resolved from JWT in production)
        user_name = f"faculty_{user_id[:8]}"
        
        await websocket_handler(websocket, subject_id, user_id, user_name)
    except Exception as e:
        _logger.error(f"WebSocket error: {e}")
        # Ensure connection is closed
        try:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
        except Exception:
            pass


# ============================================================================ #
# Audit Logging Endpoints                                                      #
# ============================================================================ #

@router.get("/audit/logs")
async def get_audit_logs_endpoint(
    actor_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """
    Retrieve audit logs (Admin only).
    
    Filters:
    - actor_id: User who performed the action
    - event_type: Type of event (e.g., "attendance_marked", "face_enrolled")
    - resource_type: Type of resource affected (e.g., "attendance", "student")
    """
    if principal.role != "admin":
        raise ApplicationError("permission_denied", "Only admins can view audit logs")

    try:
        logs = get_audit_logs(
            actor_id=actor_id,
            event_type=event_type,
            resource_type=resource_type,
            limit=limit,
        )
        
        return {
            "status": "success",
            "count": len(logs),
            "logs": [log.to_dict() for log in logs],
        }
    except Exception as e:
        _logger.error(f"Error retrieving audit logs: {e}")
        raise ApplicationError("audit_error", str(e))


# ============================================================================ #
# System Management Endpoints                                                  #
# ============================================================================ #

@router.post("/system/cleanup")
async def cleanup_system(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """
    Perform system cleanup operations (Admin only).
    - Remove old face embeddings
    """
    if principal.role != "admin":
        raise ApplicationError("permission_denied", "Only admins can perform cleanup")

    try:
        deleted_count = await cleanup_old_embeddings(session)
        
        return {
            "status": "success",
            "operations": {
                "embeddings_cleaned": deleted_count,
            }
        }
    except Exception as e:
        _logger.error(f"Cleanup error: {e}")
        raise ApplicationError("cleanup_error", str(e))


@router.get("/system/health")
async def system_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get system health status.
    Includes database connection, recognition model, and active connections.
    """
    try:
        # Test database
        db_ok = True
        try:
            await session.execute("SELECT 1")
        except Exception:
            db_ok = False

        # Get stats
        stats = await compute_embedding_statistics(session)

        # Get WebSocket connections
        ws_connections = await manager.get_total_connections()

        return {
            "status": "healthy" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "websocket_connections": ws_connections,
            "recognition_model": {
                "name": "arcface-onnx",
                "version": "2.0",
            },
            "embeddings": stats,
        }
    except Exception as e:
        _logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
