from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt
from jwt import PyJWKClient

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.db.models import AppRole


@dataclass(slots=True)
class Principal:
    user_id: UUID
    full_name: str
    email: str
    role: AppRole
    department_id: UUID | None
    faculty_id: UUID | None
    claims: dict


@lru_cache
def _get_jwk_client() -> PyJWKClient:
    settings = get_settings()
    return PyJWKClient(settings.resolved_supabase_jwks_url)


def verify_supabase_jwt(token: str) -> dict:
    settings = get_settings()

    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            issuer=f"{str(settings.supabase_url).rstrip('/')}/auth/v1",
            options={"require": ["exp", "sub"], "verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApplicationError(status_code=401, code="token_expired", message="Token has expired.") from exc
    except jwt.PyJWTError as public_key_error:
        if settings.supabase_jwt_secret:
            try:
                return jwt.decode(
                    token,
                    settings.supabase_jwt_secret.get_secret_value(),
                    algorithms=["HS256"],
                    issuer=f"{str(settings.supabase_url).rstrip('/')}/auth/v1",
                    options={"require": ["exp", "sub"], "verify_aud": False},
                )
            except jwt.ExpiredSignatureError as exc:
                raise ApplicationError(status_code=401, code="token_expired", message="Token has expired.") from exc
            except jwt.PyJWTError as shared_secret_error:
                raise ApplicationError(
                    status_code=401,
                    code="invalid_token",
                    message="Token verification failed.",
                ) from shared_secret_error
        raise ApplicationError(status_code=401, code="invalid_token", message="Token verification failed.") from public_key_error