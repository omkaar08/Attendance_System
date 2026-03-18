import json
from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_ignore_empty=True, extra="ignore")

    app_name: str = "visionattend-backend"
    app_env: str = "development"
    api_v1_prefix: str = "/v1"
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    database_url: str
    supabase_url: AnyHttpUrl
    supabase_anon_key: SecretStr
    supabase_service_role_key: SecretStr
    supabase_jwt_secret: SecretStr | None = None
    supabase_jwks_url: AnyHttpUrl | None = None
    supabase_student_images_bucket: str = "student-images"
    supabase_face_training_bucket: str = "face-training-images"
    supabase_reports_bucket: str = "reports"
    attendance_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    signed_upload_url_ttl_seconds: int = Field(default=7200, ge=60, le=7200)

    # Face recognition ML settings
    face_model_name: str = "buffalo_sc"
    face_recognition_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    face_min_quality_score: float = Field(default=0.30, ge=0.0, le=1.0)
    face_max_embeddings_per_student: int = Field(default=10, ge=1, le=50)
    face_model_warmup: bool = False  # set True in production to pre-load model on startup
    enable_extended_api: bool = False

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []

            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]

            return [item.strip().strip('"').strip("'") for item in stripped.split(",") if item.strip()]
        return value

    @property
    def local_dev_cors_origin_regex(self) -> str | None:
        if self.app_env.lower() != "development":
            return None
        return r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @property
    def allowed_origins(self) -> list[str]:
        return self.backend_cors_origins

    @property
    def resolved_supabase_jwks_url(self) -> str:
        if self.supabase_jwks_url:
            return str(self.supabase_jwks_url)
        return f"{str(self.supabase_url).rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()