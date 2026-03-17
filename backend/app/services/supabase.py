from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


def get_public_supabase_client() -> Client:
    settings = get_settings()
    return create_client(
        str(settings.supabase_url),
        settings.supabase_anon_key.get_secret_value(),
    )


@lru_cache
def get_service_supabase_client() -> Client:
    settings = get_settings()
    return create_client(
        str(settings.supabase_url),
        settings.supabase_service_role_key.get_secret_value(),
    )