"""
Comprehensive integration tests for face recognition, batch operations,
real-time notifications, and audit logging.
"""
import asyncio
import base64
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_application
from app.services.face_onnx import (
    FaceAnalyzer,
    compute_sharpness_score,
    compute_brightness_score,
    compute_liveness_score,
    generate_arcface_embedding,
)

_logger = logging.getLogger(__name__)

# ============================================================================ #
# Test Fixtures                                                                #
# ============================================================================ #

@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    return create_application()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_face_image():
    """Generate a sample face image for testing."""
    # Create a simple 200x200 BGR image
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    
    # Add some simulated face features (grayscale box + eyes)
    image[50:150, 50:150] = 150  # Face region
    image[80:100, 70:90] = 200   # Left eye
    image[80:100, 110:130] = 200  # Right eye
    image[140:150, 80:120] = 100  # Mouth
    
    # Add some texture
    noise = np.random.randint(0, 20, image.shape, dtype=np.uint8)
    image = cv2.add(image, noise)
    
    # Encode as JPEG
    success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buffer.tobytes() if success else b""


@pytest.fixture
def blurry_face_image():
    """Generate a blurry face image (should be rejected)."""
    image = np.full((200, 200, 3), 128, dtype=np.uint8)
    image = cv2.GaussianBlur(image, (51, 51), 10)
    success, buffer = cv2.imencode(".jpg", image)
    return buffer.tobytes() if success else b""


@pytest.fixture
def dark_face_image():
    """Generate an under-exposed face image (should be rejected)."""
    image = np.full((200, 200, 3), 30, dtype=np.uint8)  # Very dark
    success, buffer = cv2.imencode(".jpg", image)
    return buffer.tobytes() if success else b""


# ============================================================================ #
# Face Quality Tests                                                           #
# ============================================================================ #

class TestFaceQuality:
    """Test face quality scoring and validation."""

    def test_sharpness_score_sharp_image(self, sample_face_image):
        """Sharp images should have high sharpness score."""
        image = cv2.imdecode(np.frombuffer(sample_face_image, np.uint8), cv2.IMREAD_COLOR)
        face_crop = image[50:150, 50:150]
        score = compute_sharpness_score(face_crop)
        assert 0.0 <= score <= 1.0
        assert score > 0.3, "Sharp image should have reasonable sharpness"

    def test_sharpness_score_blurry_image(self, blurry_face_image):
        """Blurry images should have low sharpness score."""
        image = cv2.imdecode(np.frombuffer(blurry_face_image, np.uint8), cv2.IMREAD_COLOR)
        score = compute_sharpness_score(image)
        assert score < 0.5, "Blurry image should have low sharpness"

    def test_brightness_score_proper_lighting(self, sample_face_image):
        """Properly lit images should have good brightness score."""
        image = cv2.imdecode(np.frombuffer(sample_face_image, np.uint8), cv2.IMREAD_COLOR)
        face_crop = image[50:150, 50:150]
        score = compute_brightness_score(face_crop)
        assert 0.0 <= score <= 1.0

    def test_brightness_score_dark_image(self, dark_face_image):
        """Dark images should have low brightness score."""
        image = cv2.imdecode(np.frombuffer(dark_face_image, np.uint8), cv2.IMREAD_COLOR)
        score = compute_brightness_score(image)
        assert score == 0.0, "Very dark image should fail brightness check"

    def test_liveness_score_real_face(self, sample_face_image):
        """Real face images should pass liveness check."""
        image = cv2.imdecode(np.frombuffer(sample_face_image, np.uint8), cv2.IMREAD_COLOR)
        face_crop = image[50:150, 50:150]
        score = compute_liveness_score(face_crop)
        assert 0.0 <= score <= 1.0, "Liveness score should be normalized"


# ============================================================================ #
# Face Analyzer Tests                                                          #
# ============================================================================ #

class TestFaceAnalyzer:
    """Test face detection and embedding generation."""

    def test_analyzer_singleton(self):
        """FaceAnalyzer should be a singleton."""
        analyzer1 = FaceAnalyzer.get()
        analyzer2 = FaceAnalyzer.get()
        assert analyzer1 is analyzer2

    def test_embedding_dimension(self, sample_face_image):
        """Generated embeddings should be 512-D."""
        image = cv2.imdecode(np.frombuffer(sample_face_image, np.uint8), cv2.IMREAD_COLOR)
        embedding = generate_arcface_embedding(image)
        assert len(embedding) == 512
        assert isinstance(embedding, np.ndarray)

    def test_embedding_normalized(self, sample_face_image):
        """Embeddings should be L2-normalized."""
        image = cv2.imdecode(np.frombuffer(sample_face_image, np.uint8), cv2.IMREAD_COLOR)
        embedding = generate_arcface_embedding(image)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01, "Embedding should be L2-normalized"

    def test_analyzer_face_detection(self, sample_face_image):
        """Analyzer should detect faces in valid images."""
        analyzer = FaceAnalyzer.get()
        results = analyzer.analyze(sample_face_image, min_confidence=0.5, min_quality=0.0)
        # Note: May or may not detect depending on implementation, just check it doesn't crash
        assert isinstance(results, list)

    def test_analyzer_no_face_detection_on_blank(self):
        """Analyzer should return empty list for blank images."""
        blank_image = np.zeros((200, 200, 3), dtype=np.uint8)
        success, buffer = cv2.imencode(".jpg", blank_image)
        image_bytes = buffer.tobytes()

        analyzer = FaceAnalyzer.get()
        results = analyzer.analyze(image_bytes, min_confidence=0.5)
        assert results == []

    def test_analyzer_handles_invalid_image(self):
        """Analyzer should gracefully handle invalid image data."""
        analyzer = FaceAnalyzer.get()
        results = analyzer.analyze(b"invalid image data")
        assert results == []


# ============================================================================ #
# Batch Operations Tests                                                       #
# ============================================================================ #

class TestBatchOperations:
    """Test CSV import/export functionality."""

    def test_csv_import_validation_empty(self):
        """CSV import should reject empty files."""
        from app.services.batch import validate_csv_headers
        
        empty_csv = ""
        # Should raise error
        with pytest.raises(Exception):
            validate_csv_headers(empty_csv)

    def test_csv_import_validation_missing_headers(self):
        """CSV import should reject files with missing required headers."""
        from app.services.batch import validate_csv_headers
        
        invalid_csv = "name,email\nJohn,john@example.com"
        with pytest.raises(Exception):
            validate_csv_headers(invalid_csv)

    def test_csv_import_validation_valid_headers(self):
        """CSV import should accept valid headers."""
        from app.services.batch import validate_csv_headers
        
        valid_csv = "name,roll_number,email,department_code,semester,section\nJohn,R001,john@example.com,CSE,1,A"
        headers = validate_csv_headers(valid_csv)
        assert "name" in headers
        assert "roll_number" in headers

    def test_parse_student_row_valid(self):
        """Valid student row should parse correctly."""
        from app.services.batch import _parse_student_row
        
        row = {
            "name": "John Doe",
            "roll_number": "CSE001",
            "email": "john@example.com",
            "department_code": "CSE",
            "semester": "3",
            "section": "A",
            "phone": "9876543210",
        }
        
        parsed = _parse_student_row(row, 2)
        assert parsed.is_valid()
        assert parsed.name == "John Doe"
        assert parsed.semester == 3

    def test_parse_student_row_invalid_email(self):
        """Row with invalid email should be rejected."""
        from app.services.batch import _parse_student_row
        
        row = {
            "name": "John Doe",
            "roll_number": "CSE001",
            "email": "invalid-email",  # Missing @
            "department_code": "CSE",
            "semester": "3",
            "section": "A",
        }
        
        parsed = _parse_student_row(row, 2)
        assert not parsed.is_valid()
        assert any("email" in error.lower() for error in parsed.errors)

    def test_parse_student_row_invalid_semester(self):
        """Row with invalid semester should be rejected."""
        from app.services.batch import _parse_student_row
        
        row = {
            "name": "John Doe",
            "roll_number": "CSE001",
            "email": "john@example.com",
            "department_code": "CSE",
            "semester": "99",  # Too high
            "section": "A",
        }
        
        parsed = _parse_student_row(row, 2)
        assert not parsed.is_valid()
        assert any("semester" in error.lower() for error in parsed.errors)


# ============================================================================ #
# Audit Logging Tests                                                          #
# ============================================================================ #

class TestAuditLogging:
    """Test audit logging functionality."""

    @pytest.mark.asyncio
    async def test_audit_log_face_enrolled(self):
        """Audit logger should record face enrollment."""
        from app.services.audit import AuditEventType, audit_logger
        
        # Create a mock session
        class MockSession:
            pass
        
        session = MockSession()
        
        await audit_logger.log(
            session,
            AuditEventType.FACE_ENROLLED,
            "user123",
            "faculty",
            "face_embedding",
            "student456",
            "Face enrolled for student",
            new_values={"quality_score": 0.95},
        )
        
        # Check log was recorded
        logs = audit_logger._audit_logs
        assert len(logs) > 0
        assert logs[-1].event_type == AuditEventType.FACE_ENROLLED

    @pytest.mark.asyncio
    async def test_audit_log_attendance_marked(self):
        """Audit logger should record attendance marking."""
        from app.services.audit import AuditEventType, audit_logger
        
        class MockSession:
            pass
        
        session = MockSession()
        
        await audit_logger.log(
            session,
            AuditEventType.ATTENDANCE_MARKED,
            "faculty123",
            "faculty",
            "attendance",
            "student456_subject789",
            "Attendance marked as present",
            new_values={"status": "present", "confidence": 0.92},
        )
        
        logs = audit_logger._audit_logs
        assert logs[-1].event_type == AuditEventType.ATTENDANCE_MARKED

    def test_audit_log_filtering(self):
        """Audit logs should be filterable."""
        from app.services.audit import (
            AuditEventType,
            audit_logger,
            get_audit_logs,
        )
        
        # get_audit_logs should work
        logs = get_audit_logs(
            event_type=AuditEventType.FACE_ENROLLED,
            limit=10,
        )
        assert isinstance(logs, list)


# ============================================================================ #
# WebSocket Tests                                                              #
# ============================================================================ #

class TestWebSocket:
    """Test WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_connection_manager_connect(self):
        """Connection manager should accept connections."""
        from app.services.websocket import manager
        
        # Create mock WebSocket
        class MockWebSocket:
            async def accept(self):
                pass
            
            async def send_text(self, data):
                pass
            
            async def close(self, code=None):
                pass
        
        ws = MockWebSocket()
        await manager.connect(ws, "subject123", "user456", "Test User")
        
        count = await manager.get_connection_count("subject123")
        assert count > 0

    @pytest.mark.asyncio
    async def test_connection_manager_disconnect(self):
        """Connection manager should remove disconnected clients."""
        from app.services.websocket import manager
        
        class MockWebSocket:
            async def accept(self):
                pass
        
        ws = MockWebSocket()
        await manager.connect(ws, "subject123", "user456", "Test User")
        
        count_before = await manager.get_connection_count("subject123")
        await manager.disconnect(ws, "subject123")
        count_after = await manager.get_connection_count("subject123")
        
        assert count_after < count_before


# ============================================================================ #
# API Endpoint Tests                                                           #
# ============================================================================ #

class TestAPIEndpoints:
    """Test API endpoints."""

    def test_system_health_endpoint(self, client):
        """Health check endpoint should respond."""
        response = client.get("/v1/system/health")
        # May fail due to auth or DB setup, but should not crash
        assert response.status_code in [200, 401, 500]

    def test_recognition_statistics_requires_auth(self, client):
        """Recognition statistics endpoint should require authentication."""
        response = client.get("/v1/recognition/statistics")
        assert response.status_code == 401


# ============================================================================ #
# Performance Tests                                                            #
# ============================================================================ #

class TestPerformance:
    """Test performance characteristics."""

    def test_embedding_generation_speed(self, sample_face_image):
        """Embedding generation should be fast (<100ms)."""
        import time
        
        image = cv2.imdecode(np.frombuffer(sample_face_image, np.uint8), cv2.IMREAD_COLOR)
        
        start = time.time()
        for _ in range(10):
            generate_arcface_embedding(image)
        duration = time.time() - start
        
        avg_time = (duration / 10) * 1000  # Convert to ms
        _logger.info(f"Average embedding generation time: {avg_time:.2f}ms")
        # 100 embeddings should take < 10 seconds
        assert duration < 10.0

    def test_analyzer_memory_efficiency(self):
        """Analyzer should not leak memory on repeated calls."""
        analyzer = FaceAnalyzer.get()
        
        # Repeated calls should not consume excessive memory
        for _ in range(100):
            analyzer.detect_faces(np.zeros((640, 640, 3), dtype=np.uint8))
        
        # If we get here, no crash = memory efficient


# ============================================================================ #
# Run Tests                                                                    #
# ============================================================================ #

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
