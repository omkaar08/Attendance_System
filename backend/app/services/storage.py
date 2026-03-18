from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.core.security import Principal
from app.db.models import Student
from app.schemas.students import FaceUploadRequest, FaceUploadResponse
from app.services.subjects import faculty_can_manage_cohort
from app.services.supabase import get_service_supabase_client


def _resolve_signed_upload_url(raw_url: str | None, *, settings, bucket: str, storage_path: str, token: str | None) -> str | None:
    if raw_url:
        if raw_url.startswith(("http://", "https://")):
            return raw_url

        base_url = str(settings.supabase_url).rstrip("/")
        if raw_url.startswith("/storage/"):
            return f"{base_url}{raw_url}"
        if raw_url.startswith("/object/"):
            return f"{base_url}/storage/v1{raw_url}"
        return f"{base_url}/storage/v1/{raw_url.lstrip('/')}"

    if token:
        base_url = str(settings.supabase_url).rstrip("/")
        encoded_path = quote(storage_path, safe="/")
        return f"{base_url}/storage/v1/object/upload/sign/{bucket}/{encoded_path}?token={token}"

    return None


def _create_signed_upload_url_via_http(*, bucket: str, storage_path: str, settings) -> dict:
    encoded_path = quote(storage_path, safe="/")
    service_key = settings.supabase_service_role_key.get_secret_value()
    endpoint = f"{str(settings.supabase_url).rstrip('/')}/storage/v1/object/upload/sign/{bucket}/{encoded_path}"

    with httpx.Client(http2=False, timeout=15.0) as client:
        response = client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            json={"upsert": False},
        )
        response.raise_for_status()
        return response.json()


def _ensure_bucket_exists(*, bucket: str) -> None:
    """Best-effort bucket bootstrap for production drift scenarios."""
    client = get_service_supabase_client()
    try:
        existing = {
            item["name"] if isinstance(item, dict) else getattr(item, "name", "")
            for item in client.storage.list_buckets()
        }
        if bucket in existing:
            return

        mime_types = ["image/jpeg", "image/png", "image/webp"]
        file_size_limit = 8 * 1024 * 1024 if "face" in bucket else 5 * 1024 * 1024
        client.storage.create_bucket(
            bucket,
            options={
                "public": False,
                "allowed_mime_types": mime_types,
                "file_size_limit": file_size_limit,
            },
        )
    except Exception:
        # Signing may still succeed even if listing/creation fails for transient reasons.
        return


async def create_face_upload_url(
    *,
    session: AsyncSession,
    principal: Principal,
    payload: FaceUploadRequest,
) -> FaceUploadResponse:
    student = (await session.execute(select(Student).where(Student.id == payload.student_id))).scalar_one_or_none()
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
        raise ApplicationError(status_code=403, code="student_forbidden", message="You cannot upload for this student.")

    settings = get_settings()
    bucket = (
        settings.supabase_student_images_bucket
        if payload.asset_kind == "student-image"
        else settings.supabase_face_training_bucket
    )
    safe_name = Path(payload.file_name).name
    storage_path = f"students/{student.id}/{'raw' if payload.asset_kind == 'face-training' else 'profile'}/{safe_name}"

    result = None
    client_error = None
    for _ in range(2):
        try:
            result = get_service_supabase_client().storage.from_(bucket).create_signed_upload_url(storage_path)
            client_error = None
            break
        except Exception as exc:  # noqa: BLE001
            client_error = exc

    # Bucket might not exist in newly provisioned environments; create it and retry once.
    if result is None:
        _ensure_bucket_exists(bucket=bucket)
        try:
            result = get_service_supabase_client().storage.from_(bucket).create_signed_upload_url(storage_path)
            client_error = None
        except Exception as exc:  # noqa: BLE001
            client_error = exc

    if result is None:
        try:
            result = _create_signed_upload_url_via_http(bucket=bucket, storage_path=storage_path, settings=settings)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text if exc.response is not None else ""
            raise ApplicationError(
                status_code=502,
                code="storage_sign_failed",
                message="Could not create signed upload URL.",
                details={
                    "bucket": bucket,
                    "upstream_status": exc.response.status_code if exc.response is not None else None,
                    "upstream_body": body[:400],
                    "hint": "Check SUPABASE_SERVICE_ROLE_KEY and bucket configuration.",
                },
            ) from (client_error or exc)
        except Exception as exc:
            raise ApplicationError(
                status_code=502,
                code="storage_sign_failed",
                message="Could not create signed upload URL.",
                details={
                    "bucket": bucket,
                    "hint": "Check SUPABASE_SERVICE_ROLE_KEY and bucket configuration.",
                },
            ) from (client_error or exc)

    raw_signed_upload_url = None
    token = None
    if isinstance(result, dict):
        raw_signed_upload_url = (
            result.get("signedURL")
            or result.get("signedUrl")
            or result.get("signed_url")
            or result.get("url")
        )
        token = result.get("token")
    else:
        raw_signed_upload_url = (
            getattr(result, "signedURL", None)
            or getattr(result, "signedUrl", None)
            or getattr(result, "signed_url", None)
            or getattr(result, "url", None)
        )
        token = getattr(result, "token", None)

    signed_upload_url = _resolve_signed_upload_url(
        raw_signed_upload_url,
        settings=settings,
        bucket=bucket,
        storage_path=storage_path,
        token=token,
    )

    if signed_upload_url is None:
        raise ApplicationError(status_code=502, code="storage_sign_failed", message="Signed upload URL missing.")

    return FaceUploadResponse(
        bucket=bucket,
        storage_path=storage_path,
        signed_upload_url=signed_upload_url,
        token=token,
        expires_in=settings.signed_upload_url_ttl_seconds,
        created_at=datetime.now(timezone.utc),
    )