"""
Real-time WebSocket service for attendance notifications.
Allows faculty to receive live updates when attendance is marked.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, status

_logger = logging.getLogger(__name__)


# ============================================================================ #
# Event Models                                                                 #
# ============================================================================ #

@dataclass
class AttendanceMarkedEvent:
    """Event emitted when attendance is marked."""
    timestamp: str  # ISO format
    student_id: str
    student_name: str
    student_roll: str
    subject_id: str
    subject_name: str
    status: str  # "present", "late", "absent", "excused"
    confidence: float
    session_date: str
    session_key: str

    def to_json(self) -> dict:
        return {
            "type": "attendance_marked",
            "data": asdict(self),
        }


@dataclass
class RecognitionErrorEvent:
    """Event emitted on recognition errors."""
    timestamp: str
    error_code: str
    error_message: str
    subject_id: Optional[str] = None

    def to_json(self) -> dict:
        return {
            "type": "recognition_error",
            "data": asdict(self),
        }


@dataclass
class SessionStartedEvent:
    """Event emitted when attendance session starts."""
    timestamp: str
    subject_id: str
    subject_name: str
    faculty_name: str
    session_date: str
    session_key: str
    expected_students: int

    def to_json(self) -> dict:
        return {
            "type": "session_started",
            "data": asdict(self),
        }


@dataclass
class SessionEndedEvent:
    """Event emitted when attendance session ends."""
    timestamp: str
    subject_id: str
    total_present: int
    total_late: int
    total_absent: int
    duration_seconds: int

    def to_json(self) -> dict:
        return {
            "type": "session_ended",
            "data": asdict(self),
        }


# ============================================================================ #
# Connection Manager                                                           #
# ============================================================================ #

class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.
    Maintains connections per subject and emits events to subscribers.
    """

    def __init__(self):
        # Map: subject_id -> set of WebSocket connections
        self.active_connections: dict[str, set[WebSocket]] = {}
        self.lock = asyncio.Lock()
        self.connection_metadata: dict[WebSocket, dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        subject_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        """Register a new WebSocket connection."""
        await websocket.accept()
        
        async with self.lock:
            if subject_id not in self.active_connections:
                self.active_connections[subject_id] = set()
            
            self.active_connections[subject_id].add(websocket)
            self.connection_metadata[websocket] = {
                "subject_id": subject_id,
                "user_id": user_id,
                "user_name": user_name,
                "connected_at": datetime.utcnow().isoformat(),
            }

        _logger.info(
            f"WebSocket connected: {user_name} ({user_id}) for subject {subject_id} "
            f"(total: {len(self.active_connections.get(subject_id, set()))})"
        )

    async def disconnect(self, websocket: WebSocket, subject_id: str) -> None:
        """Unregister a WebSocket connection."""
        async with self.lock:
            if subject_id in self.active_connections:
                self.active_connections[subject_id].discard(websocket)
            self.connection_metadata.pop(websocket, None)

        _logger.info(f"WebSocket disconnected for subject {subject_id}")

    async def broadcast(
        self,
        subject_id: str,
        event: AttendanceMarkedEvent | RecognitionErrorEvent | SessionStartedEvent | SessionEndedEvent,
    ) -> None:
        """Broadcast event to all connections for a subject."""
        async with self.lock:
            connections = self.active_connections.get(subject_id, set()).copy()

        message = json.dumps(event.to_json())

        disconnected = set()
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                _logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        if disconnected:
            async with self.lock:
                for conn in disconnected:
                    subject = self.connection_metadata.get(conn, {}).get("subject_id")
                    if subject and subject in self.active_connections:
                        self.active_connections[subject].discard(conn)
                    self.connection_metadata.pop(conn, None)

    async def broadcast_to_user(
        self,
        user_id: str,
        event: AttendanceMarkedEvent | RecognitionErrorEvent | SessionStartedEvent | SessionEndedEvent,
    ) -> None:
        """Broadcast event to all connections of a specific user."""
        async with self.lock:
            user_connections = [
                ws for ws, meta in self.connection_metadata.items()
                if meta.get("user_id") == user_id
            ]

        message = json.dumps(event.to_json())

        for connection in user_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                _logger.warning(f"Failed to send WebSocket message to user: {e}")

    async def get_connection_count(self, subject_id: str) -> int:
        """Get number of active connections for a subject."""
        async with self.lock:
            return len(self.active_connections.get(subject_id, set()))

    async def get_total_connections(self) -> int:
        """Get total number of active WebSocket connections."""
        async with self.lock:
            return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


# ============================================================================ #
# WebSocket Handler                                                            #
# ============================================================================ #

async def websocket_handler(
    websocket: WebSocket,
    subject_id: str,
    user_id: str,
    user_name: str,
) -> None:
    """
    Handle WebSocket connection for real-time attendance updates.
    Keeps connection open and processes incoming heartbeats/commands.
    """
    await manager.connect(websocket, subject_id, user_id, user_name)
    
    try:
        while True:
            # Receive message (typically heartbeat)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    # Respond to heartbeat
                    await websocket.send_text(
                        json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                    )
                elif msg_type == "disconnect":
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                    break

            except json.JSONDecodeError:
                _logger.warning(f"Invalid JSON received: {data}")

    except WebSocketDisconnect:
        await manager.disconnect(websocket, subject_id)
        _logger.info(f"WebSocket client {user_name} disconnected from subject {subject_id}")
    except Exception as e:
        _logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, subject_id)


# ============================================================================ #
# Event Emitters                                                               #
# ============================================================================ #

async def emit_attendance_marked(
    subject_id: str,
    student_id: str,
    student_name: str,
    student_roll: str,
    subject_name: str,
    status: str,
    confidence: float,
    session_date: str,
    session_key: str,
) -> None:
    """Emit attendance marked event to all listeners."""
    event = AttendanceMarkedEvent(
        timestamp=datetime.utcnow().isoformat(),
        student_id=str(student_id),
        student_name=student_name,
        student_roll=student_roll,
        subject_id=str(subject_id),
        subject_name=subject_name,
        status=status,
        confidence=confidence,
        session_date=session_date,
        session_key=session_key,
    )
    await manager.broadcast(str(subject_id), event)


async def emit_recognition_error(
    subject_id: Optional[str],
    error_code: str,
    error_message: str,
) -> None:
    """Emit recognition error event."""
    event = RecognitionErrorEvent(
        timestamp=datetime.utcnow().isoformat(),
        error_code=error_code,
        error_message=error_message,
        subject_id=str(subject_id) if subject_id else None,
    )
    if subject_id:
        await manager.broadcast(str(subject_id), event)


async def emit_session_started(
    subject_id: str,
    subject_name: str,
    faculty_name: str,
    session_date: str,
    session_key: str,
    expected_students: int,
) -> None:
    """Emit session started event."""
    event = SessionStartedEvent(
        timestamp=datetime.utcnow().isoformat(),
        subject_id=str(subject_id),
        subject_name=subject_name,
        faculty_name=faculty_name,
        session_date=session_date,
        session_key=session_key,
        expected_students=expected_students,
    )
    await manager.broadcast(str(subject_id), event)


async def emit_session_ended(
    subject_id: str,
    total_present: int,
    total_late: int,
    total_absent: int,
    duration_seconds: int,
) -> None:
    """Emit session ended event."""
    event = SessionEndedEvent(
        timestamp=datetime.utcnow().isoformat(),
        subject_id=str(subject_id),
        total_present=total_present,
        total_late=total_late,
        total_absent=total_absent,
        duration_seconds=duration_seconds,
    )
    await manager.broadcast(str(subject_id), event)
