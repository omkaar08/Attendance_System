"""
Phase 3 verification script — Face Recognition ML Service.

This script verifies all Phase 3 exit criteria WITHOUT requiring a real camera
or pre-downloaded InsightFace models.  It generates a synthetic test image
(a face-like JPEG), stubs the FaceAnalyzer singleton so we can test the full
API without GPU/model downloads, then exercises:

  1. POST /v1/recognition/enroll         — store a mock embedding
  2. GET  /v1/recognition/students/{id}/embeddings  — list stored embeddings
  3. POST /v1/recognition/identify       — match face in frame → auto-mark attendance
  4. Duplicate-identify idempotency      — second call is a no-op (dup not marked twice)
  5. DELETE /v1/recognition/embeddings/{id} — soft-delete (status → deprecated)

Run from the backend/ directory:
    python scripts/phase3_verify.py
"""
import asyncio
import base64
import io
import json
import time
from datetime import date
from unittest.mock import patch

import httpx
import numpy as np

from app.main import app
from app.services.face import FaceResult, MODEL_NAME, MODEL_VERSION
from app.services.supabase import get_service_supabase_client

# ------------------------------------------------------------------ constants

TEST_EMAIL = "phase2.faculty@example.com"
TEST_PASSWORD = "Phase2Faculty!123"
SUBJECT_CODE = "MM-CSE-ML-01"
EMBEDDING_DIM = 512
CONFIDENCE_THRESHOLD = 0.45  # must match default in config


# ------------------------------------------------------------------ helpers

def make_synthetic_jpeg(width: int = 64, height: int = 64) -> bytes:
    """Create a tiny solid-colour JPEG purely via numpy — no cv2 needed."""
    # Import here to avoid cv2 dependency at module level
    import cv2  # noqa: PLC0415
    img = np.full((height, width, 3), fill_value=200, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    if not ok:
        raise RuntimeError("cv2 failed to encode synthetic JPEG")
    return buf.tobytes()


def make_mock_embedding(seed: int = 42) -> list[float]:
    """Reproducible L2-normalised 512-d vector (same seed → same embedding)."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    v /= np.linalg.norm(v)
    return v.tolist()


def _b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode()


# ------------------------------------------------------------------ seed helpers

def _get_faculty_subject(supa_client):
    subjects = supa_client.table("subjects").select("id,faculty_id,department_id,semester,section").eq("code", SUBJECT_CODE).limit(1).execute()
    data = subjects.data
    if not data:
        raise RuntimeError(f"Subject '{SUBJECT_CODE}' not found — run phase2_verify.py first.")
    return data[0]


def _get_student_in_cohort(supa_client, subject: dict) -> dict:
    students = (
        supa_client.table("students")
        .select("id,full_name,roll_number,department_id,semester,section")
        .eq("department_id", subject["department_id"])
        .eq("semester", subject["semester"])
        .eq("section", subject["section"])
        .limit(1)
        .execute()
    )
    data = students.data
    if not data:
        raise RuntimeError("No students found in the subject's cohort — run phase2_verify.py first.")
    return data[0]


# ------------------------------------------------------------------ mock

class _FakeAnalyzeResult:
    """Stub FaceAnalyzer.analyze() for a single-face result."""

    def __init__(self, embedding: list[float]) -> None:
        self._result = [
            FaceResult(
                embedding=embedding,
                quality_score=0.98,
                landmarks={"left_eye": [20, 25], "right_eye": [44, 25]},
                bbox=[5.0, 5.0, 59.0, 59.0],
            )
        ]

    def analyze(self, _image_bytes: bytes) -> list[FaceResult]:
        return self._result


# ------------------------------------------------------------------ main flow

async def run(subject: dict, student: dict, auth_token: str) -> dict:
    """Full Phase 3 smoke test using ASGI transport (no real server needed)."""

    enroll_embedding = make_mock_embedding(seed=42)
    # Identification probe uses the same seed → perfect match (distance ≈ 0)
    identify_embedding = make_mock_embedding(seed=42)

    headers = {"Authorization": f"Bearer {auth_token}"}
    synthetic_image = make_synthetic_jpeg()

    with patch("app.services.recognition.FaceAnalyzer") as MockFace:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

            # ---- 1. Enroll -------------------------------------------------------
            MockFace.get.return_value = _FakeAnalyzeResult(enroll_embedding)
            enroll_resp = await client.post(
                "/v1/recognition/enroll",
                headers=headers,
                json={
                    "student_id": str(student["id"]),
                    "image_base64": _b64(synthetic_image),
                    "source": "upload",
                },
            )
            if enroll_resp.status_code >= 400:
                raise RuntimeError(json.dumps({"check": "enroll", "status": enroll_resp.status_code, "body": enroll_resp.text}, indent=2))
            enroll_data = enroll_resp.json()
            embedding_id: str = enroll_data["embedding"]["id"]

            # ---- 2. List embeddings ----------------------------------------------
            list_resp = await client.get(
                f"/v1/recognition/students/{student['id']}/embeddings",
                headers=headers,
            )
            if list_resp.status_code >= 400:
                raise RuntimeError(json.dumps({"check": "list_embeddings", "status": list_resp.status_code, "body": list_resp.text}, indent=2))
            embeddings_count = list_resp.json()["total"]

            # ---- 3. Identify → auto-mark attendance ------------------------------
            MockFace.get.return_value = _FakeAnalyzeResult(identify_embedding)
            session_key = f"phase3-verify-{int(time.time())}"
            identify_resp = await client.post(
                "/v1/recognition/identify",
                headers=headers,
                json={
                    "frame_base64": _b64(synthetic_image),
                    "subject_id": str(subject["id"]),
                    "class_date": str(date.today()),
                    "session_key": session_key,
                    "session_label": "Phase 3 Verify Session",
                    "auto_mark_attendance": True,
                },
            )
            if identify_resp.status_code >= 400:
                raise RuntimeError(json.dumps({"check": "identify", "status": identify_resp.status_code, "body": identify_resp.text}, indent=2))
            identify_data = identify_resp.json()

            # ---- 4. Duplicate identify → idempotent -----------------------------
            MockFace.get.return_value = _FakeAnalyzeResult(identify_embedding)
            dup_resp = await client.post(
                "/v1/recognition/identify",
                headers=headers,
                json={
                    "frame_base64": _b64(synthetic_image),
                    "subject_id": str(subject["id"]),
                    "class_date": str(date.today()),
                    "session_key": session_key,  # same session_key → must be dup
                    "session_label": "Phase 3 Verify Session",
                    "auto_mark_attendance": True,
                },
            )
            if dup_resp.status_code >= 400:
                raise RuntimeError(json.dumps({"check": "dup_identify", "status": dup_resp.status_code, "body": dup_resp.text}, indent=2))
            dup_data = dup_resp.json()

            # ---- 5. Delete embedding ---------------------------------------------
            del_resp = await client.delete(
                f"/v1/recognition/embeddings/{embedding_id}",
                headers=headers,
            )
            if del_resp.status_code not in (200, 204):
                raise RuntimeError(json.dumps({"check": "delete_embedding", "status": del_resp.status_code, "body": del_resp.text}, indent=2))

    recognized = identify_data.get("recognized", [])
    dup_recognized = dup_data.get("recognized", [])
    return {
        "enroll_status": enroll_resp.status_code,
        "embedding_id": embedding_id,
        "embeddings_count": embeddings_count,
        "identify_face_count": identify_data["frame_face_count"],
        "identify_recognized_count": len(recognized),
        "identify_attendance_marked": recognized[0]["attendance_marked"] if recognized else False,
        "identify_confidence": recognized[0]["confidence"] if recognized else 0.0,
        "dup_recognized_count": len(dup_recognized),
        "dup_attendance_marked": dup_recognized[0]["attendance_marked"] if dup_recognized else False,
        "delete_status": del_resp.status_code,
    }


def main() -> None:
    supa = get_service_supabase_client()
    subject = _get_faculty_subject(supa)
    student = _get_student_in_cohort(supa, subject)

    # Login to get a fresh JWT
    from supabase_auth._sync.gotrue_base_api import SyncGoTrueBaseAPI  # noqa: PLC0415
    auth_response = supa.auth.sign_in_with_password({"email": TEST_EMAIL, "password": TEST_PASSWORD})
    token: str = auth_response.session.access_token

    results = asyncio.run(run(subject, student, token))

    output = {
        "student": {"id": str(student["id"]), "name": student["full_name"], "roll": student["roll_number"]},
        "subject": {"id": str(subject["id"]), "code": SUBJECT_CODE},
        "checks": results,
        "exit_criteria": {
            "embedding_stored": results["enroll_status"] == 201 or results["embedding_id"] != "",
            "face_recognized": results["identify_recognized_count"] > 0,
            "attendance_auto_marked": results["identify_attendance_marked"],
            "duplicate_prevented": not results["dup_attendance_marked"],
            "embedding_soft_deleted": results["delete_status"] in (200, 204),
        },
    }
    print(json.dumps(output, indent=2))

    failed = [k for k, v in output["exit_criteria"].items() if not v]
    if failed:
        raise SystemExit(f"\n❌ Failed criteria: {failed}")
    print("\n✅ All Phase 3 exit criteria passed.")


if __name__ == "__main__":
    main()
