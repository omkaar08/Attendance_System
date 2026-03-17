"""
Audit logging service for tracking all sensitive operations.
Logs are stored in database for compliance and security auditing.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

_logger = logging.getLogger(__name__)


# ============================================================================ #
# Audit Event Types                                                            #
# ============================================================================ #

class AuditEventType(str, Enum):
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # Student Management
    STUDENT_REGISTERED = "student_registered"
    STUDENT_DELETED = "student_deleted"
    STUDENT_UPDATED = "student_updated"

    # Face Recognition
    FACE_ENROLLED = "face_enrolled"
    FACE_DELETED = "face_deleted"
    FACE_REJECTED = "face_rejected"
    RECOGNITION_PERFORMED = "recognition_performed"

    # Attendance
    ATTENDANCE_MARKED = "attendance_marked"
    ATTENDANCE_CORRECTED = "attendance_corrected"
    ATTENDANCE_DELETED = "attendance_deleted"

    # Faculty/Subject Management
    SUBJECT_CREATED = "subject_created"
    SUBJECT_ASSIGNED = "subject_assigned"
    SUBJECT_DELETED = "subject_deleted"
    FACULTY_CREATED = "faculty_created"
    FACULTY_DELETED = "faculty_deleted"

    # Department/HOD Management
    DEPARTMENT_CREATED = "department_created"
    DEPARTMENT_DELETED = "department_deleted"
    HOD_ASSIGNED = "hod_assigned"

    # System Operations
    SETTINGS_CHANGED = "settings_changed"
    DATA_EXPORTED = "data_exported"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ============================================================================ #
# Audit Log Entry                                                              #
# ============================================================================ #

@dataclass
class AuditLog:
    """Audit log entry."""
    event_type: AuditEventType
    actor_id: str  # User who performed action
    actor_role: str
    resource_type: str  # e.g., "student", "face_embedding", "attendance"
    resource_id: str
    description: str
    severity: AuditSeverity = AuditSeverity.INFO
    old_values: Optional[dict] = None  # Before values for updates
    new_values: Optional[dict] = None  # After values for updates
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"  # "success", "failure", "partial"
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
            "severity": self.severity.value,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }


# ============================================================================ #
# Audit Logger                                                                 #
# ============================================================================ #

class AuditLogger:
    """Thread-safe audit logging service."""

    def __init__(self):
        self._audit_logs: list[AuditLog] = []
        self._max_buffer = 1000

    async def log(
        self,
        session: AsyncSession,
        event_type: AuditEventType,
        actor_id: str,
        actor_role: str,
        resource_type: str,
        resource_id: str,
        description: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Log an audit event."""
        log_entry = AuditLog(
            event_type=event_type,
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            severity=severity,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            status_code=status_code,
            error_message=error_message,
        )

        # Log to application logger
        log_dict = log_entry.to_dict()
        _logger.info(
            f"AUDIT: {event_type.value} | {actor_role}({actor_id}) | "
            f"{resource_type}({resource_id}) | {description} | {status}"
        )

        # Store in buffer (would persist to DB in production)
        self._audit_logs.append(log_entry)
        if len(self._audit_logs) > self._max_buffer:
            self._audit_logs = self._audit_logs[-500:]  # Keep last 500


# Global audit logger instance
audit_logger = AuditLogger()


# ============================================================================ #
# Convenience Logging Functions                                                #
# ============================================================================ #

async def log_login(
    session: AsyncSession,
    user_id: str,
    role: str,
    success: bool = True,
    ip_address: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Log login attempt."""
    await audit_logger.log(
        session,
        AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE,
        user_id,
        role,
        "user",
        user_id,
        f"Login {'successful' if success else 'failed'}",
        severity=AuditSeverity.WARNING if not success else AuditSeverity.INFO,
        ip_address=ip_address,
        status="success" if success else "failure",
        error_message=error_message,
    )


async def log_face_enrolled(
    session: AsyncSession,
    actor_id: str,
    actor_role: str,
    student_id: str,
    quality_score: float,
    ip_address: Optional[str] = None,
) -> None:
    """Log face enrollment."""
    await audit_logger.log(
        session,
        AuditEventType.FACE_ENROLLED,
        actor_id,
        actor_role,
        "face_embedding",
        str(student_id),
        f"Face enrolled for student {student_id} (quality: {quality_score:.2f})",
        new_values={"quality_score": quality_score},
        ip_address=ip_address,
    )


async def log_attendance_marked(
    session: AsyncSession,
    actor_id: str,
    actor_role: str,
    student_id: str,
    subject_id: str,
    status: str,
    confidence: float,
    ip_address: Optional[str] = None,
) -> None:
    """Log attendance marking."""
    await audit_logger.log(
        session,
        AuditEventType.ATTENDANCE_MARKED,
        actor_id,
        actor_role,
        "attendance",
        f"{student_id}_{subject_id}",
        f"Attendance marked as {status} with confidence {confidence:.2f}",
        new_values={"status": status, "confidence": confidence},
        ip_address=ip_address,
    )


async def log_student_registered(
    session: AsyncSession,
    actor_id: str,
    actor_role: str,
    student_id: str,
    student_name: str,
    ip_address: Optional[str] = None,
) -> None:
    """Log student registration."""
    await audit_logger.log(
        session,
        AuditEventType.STUDENT_REGISTERED,
        actor_id,
        actor_role,
        "student",
        str(student_id),
        f"Student registered: {student_name}",
        new_values={"name": student_name},
        ip_address=ip_address,
    )


async def log_subject_assigned(
    session: AsyncSession,
    actor_id: str,
    actor_role: str,
    faculty_id: str,
    subject_id: str,
    subject_name: str,
    ip_address: Optional[str] = None,
) -> None:
    """Log subject assignment to faculty."""
    await audit_logger.log(
        session,
        AuditEventType.SUBJECT_ASSIGNED,
        actor_id,
        actor_role,
        "subject",
        str(subject_id),
        f"Subject {subject_name} assigned to faculty {faculty_id}",
        new_values={"assigned_faculty": faculty_id},
        ip_address=ip_address,
    )


async def log_hod_assigned(
    session: AsyncSession,
    actor_id: str,
    hod_id: str,
    department_id: str,
    department_name: str,
    ip_address: Optional[str] = None,
) -> None:
    """Log HOD assignment."""
    await audit_logger.log(
        session,
        AuditEventType.HOD_ASSIGNED,
        actor_id,
        "admin",
        "department",
        str(department_id),
        f"HOD {hod_id} assigned to department {department_name}",
        new_values={"hod_id": str(hod_id)},
        ip_address=ip_address,
    )


# ============================================================================ #
# Query Functions                                                              #
# ============================================================================ #

def get_audit_logs(
    actor_id: Optional[str] = None,
    event_type: Optional[AuditEventType] = None,
    resource_type: Optional[str] = None,
    severity: Optional[AuditSeverity] = None,
    limit: int = 100,
) -> list[AuditLog]:
    """
    Retrieve audit logs with optional filtering.
    In production, this would query the database.
    """
    logs = audit_logger._audit_logs.copy()

    if actor_id:
        logs = [l for l in logs if l.actor_id == actor_id]
    if event_type:
        logs = [l for l in logs if l.event_type == event_type]
    if resource_type:
        logs = [l for l in logs if l.resource_type == resource_type]
    if severity:
        logs = [l for l in logs if l.severity == severity]

    # Return most recent first
    return sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]
