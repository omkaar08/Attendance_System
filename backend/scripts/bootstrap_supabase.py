from app.core.config import get_settings
from app.services.supabase import get_service_supabase_client


def ensure_bucket(client, bucket_name: str, *, mime_types: list[str], file_size_limit: int) -> None:
    existing = {bucket["name"] if isinstance(bucket, dict) else getattr(bucket, "name") for bucket in client.storage.list_buckets()}
    if bucket_name in existing:
        return
    client.storage.create_bucket(
        bucket_name,
        options={
            "public": False,
            "allowed_mime_types": mime_types,
            "file_size_limit": file_size_limit,
        },
    )


def main() -> None:
    settings = get_settings()
    client = get_service_supabase_client()
    ensure_bucket(
        client,
        settings.supabase_student_images_bucket,
        mime_types=["image/jpeg", "image/png", "image/webp"],
        file_size_limit=5 * 1024 * 1024,
    )
    ensure_bucket(
        client,
        settings.supabase_face_training_bucket,
        mime_types=["image/jpeg", "image/png", "image/webp"],
        file_size_limit=8 * 1024 * 1024,
    )
    ensure_bucket(
        client,
        settings.supabase_reports_bucket,
        mime_types=["application/pdf", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        file_size_limit=10 * 1024 * 1024,
    )


if __name__ == "__main__":
    main()