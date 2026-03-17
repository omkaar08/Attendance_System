"""
Cleanup script to delete all non-admin test data while preserving all functionality.
This keeps only the admin user for fresh testing from scratch.

Usage:
    python -m scripts.cleanup_test_data
"""

import asyncio
import httpx
from typing import Any

import asyncpg
from app.core.config import get_settings


def to_asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


class AuthAdminClient:
    def __init__(self, *, base_url: str, service_role_key: str) -> None:
        service_role_key_str = str(service_role_key)
        self._client = httpx.Client(
            base_url=f"{str(base_url).rstrip('/')}/auth/v1",
            headers={
                "apikey": service_role_key_str,
                "Authorization": f"Bearer {service_role_key_str}",
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json",
            },
            timeout=30.0,
            http2=False,
        )

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> Any:
        response = self._client.request(method, path, params=params, json=body)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    def list_users(self) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        page = 1
        per_page = 1000
        while True:
            payload = self._request("GET", "/admin/users", params={"page": page, "per_page": per_page})
            page_users = payload.get("users", []) if isinstance(payload, dict) else payload
            users.extend(page_users)
            if len(page_users) < per_page:
                break
            page += 1
        return users

    def delete_user(self, user_id: str) -> None:
        self._request("DELETE", f"/admin/users/{user_id}")


async def cleanup_database(conn: asyncpg.Connection) -> None:
    """Delete all test data while preserving schema and admin user."""
    
    print("Starting database cleanup...")
    
    # Get list of existing tables to avoid errors
    existing_tables = await conn.fetch(
        """
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
        """
    )
    table_names = {row['table_name'] for row in existing_tables}
    
    # 1. Delete all attendance records
    if 'attendance' in table_names:
        print("  - Deleting attendance records...")
        deleted = await conn.execute("DELETE FROM public.attendance")
        print(f"    Deleted {deleted.split()[1]} attendance records" if isinstance(deleted, str) else f"    Deleted {deleted} attendance records")
    
    # 2. Delete all face embeddings (must be before face_samples due to FK)
    if 'face_embeddings' in table_names:
        print("  - Deleting face embeddings...")
        deleted = await conn.execute("DELETE FROM public.face_embeddings")
        print(f"    Deleted {deleted.split()[1]} face embedding records" if isinstance(deleted, str) else f"    Deleted {deleted} face embedding records")
    
    # 3. Delete all face samples (if table exists)
    if 'face_samples' in table_names:
        print("  - Deleting face samples...")
        deleted = await conn.execute("DELETE FROM public.face_samples")
        print(f"    Deleted {deleted.split()[1]} face sample records" if isinstance(deleted, str) else f"    Deleted {deleted} face sample records")
    
    # 4. Delete all student-subject enrollments (if table exists)
    if 'student_subject_enrollment' in table_names:
        print("  - Deleting student-subject enrollments...")
        deleted = await conn.execute("DELETE FROM public.student_subject_enrollment")
        print(f"    Deleted {deleted.split()[1]} enrollment records" if isinstance(deleted, str) else f"    Deleted {deleted} enrollment records")
    
    # 5. Delete all students
    if 'students' in table_names:
        print("  - Deleting students...")
        deleted = await conn.execute("DELETE FROM public.students")
        print(f"    Deleted {deleted.split()[1]} student records" if isinstance(deleted, str) else f"    Deleted {deleted} student records")
    
    # 6. Delete all subjects
    if 'subjects' in table_names:
        print("  - Deleting subjects...")
        deleted = await conn.execute("DELETE FROM public.subjects")
        print(f"    Deleted {deleted.split()[1]} subject records" if isinstance(deleted, str) else f"    Deleted {deleted} subject records")
    
    # 7. Delete all faculty
    if 'faculty' in table_names:
        print("  - Deleting faculty...")
        deleted = await conn.execute("DELETE FROM public.faculty")
        print(f"    Deleted {deleted.split()[1]} faculty records" if isinstance(deleted, str) else f"    Deleted {deleted} faculty records")
    
    # 8. Delete all non-admin users from public.users table
    if 'users' in table_names:
        print("  - Deleting non-admin users from public.users...")
        deleted = await conn.execute("DELETE FROM public.users WHERE role != 'admin'")
        print(f"    Deleted {deleted.split()[1]} user records" if isinstance(deleted, str) else f"    Deleted {deleted} user records")
    
    # 9. Remove HOD assignments from departments (before deleting departments)
    if 'departments' in table_names:
        print("  - Removing HOD assignments from departments...")
        updated = await conn.execute("UPDATE public.departments SET hod_user_id = NULL")
        print(f"    Updated {updated.split()[1]} department records" if isinstance(updated, str) else f"    Updated {updated} department records")
    
    # 10. Remove department assignments from users
    if 'users' in table_names:
        print("  - Removing department assignments from users...")
        updated = await conn.execute("UPDATE public.users SET department_id = NULL WHERE role = 'admin'")
        print(f"    Updated {updated.split()[1]} user records" if isinstance(updated, str) else f"    Updated {updated} user records")
    
    # 11. Delete all departments
    if 'departments' in table_names:
        print("  - Deleting all departments...")
        deleted = await conn.execute("DELETE FROM public.departments")
        print(f"    Deleted {deleted.split()[1]} department records" if isinstance(deleted, str) else f"    Deleted {deleted} department records")
    
    print("\n✓ Database cleanup completed successfully!")


async def cleanup_auth(auth_admin: AuthAdminClient) -> None:
    """Delete all non-admin users from Supabase Auth."""
    
    print("\nCleaning up Supabase Auth users...")
    
    ADMIN_EMAIL = "admin@visionattend.com"
    auth_users = auth_admin.list_users()
    
    deleted_count = 0
    for auth_user in auth_users:
        email = auth_user.get("email", "")
        user_id = auth_user.get("id")
        
        # Skip admin user
        if email == ADMIN_EMAIL:
            print(f"  - Keeping admin user: {email}")
            continue
        
        try:
            auth_admin.delete_user(user_id)
            print(f"  - Deleted auth user: {email}")
            deleted_count += 1
        except Exception as e:
            print(f"  - Error deleting {email}: {e}")
    
    print(f"\n✓ Deleted {deleted_count} auth users")


async def main() -> None:
    settings = get_settings()
    
    # Connect to database
    conn = await asyncpg.connect(to_asyncpg_dsn(settings.database_url))
    
    try:
        # Cleanup database
        await cleanup_database(conn)
        
        # Cleanup auth users (with error handling)
        auth_admin = AuthAdminClient(
            base_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
        )
        
        try:
            await cleanup_auth(auth_admin)
        except Exception as e:
            print(f"\n⚠ Auth cleanup skipped: {e}")
            print("  (You can delete test users manually from Supabase dashboard)")
        finally:
            auth_admin.close()
        
        print("\n" + "="*60)
        print("✓ CLEANUP COMPLETE!")
        print("="*60)
        print("\nYour system is ready for fresh end-to-end testing:")
        print("1. All departments deleted")
        print("2. All HODs, Faculty, Students, Subjects deleted")
        print("3. Admin user is still available")
        print("4. All functionality preserved - ready to rebuild from scratch")
        print("\nNext steps:")
        print("1. Login as admin@visionattend.com / VisionAttendAdmin!123")
        print("2. Create departments")
        print("3. Assign HODs to departments")
        print("4. Login as HOD to create faculty and subjects")
        print("5. Login as faculty to add students and test detection")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
