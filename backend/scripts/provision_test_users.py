import asyncio
import json
from dataclasses import dataclass
from typing import Any

import asyncpg
import httpx

from app.core.config import get_settings

DEPARTMENT_CODE = "VIS-CSE"
DEPARTMENT_NAME = "VisionAttend Computer Science"
FACULTY_SUBJECT_CODE = "VIS-AI-601"
FACULTY_SUBJECT_NAME = "Applied AI Systems"
HOD_SUBJECT_CODE = "VIS-OPS-801"
HOD_SUBJECT_NAME = "Academic Operations Lab"

ADMIN_EMAIL = "admin@visionattend.com"
ADMIN_PASSWORD = "VisionAttendAdmin!123"
HOD_EMAIL = "hod@visionattend.com"
HOD_PASSWORD = "VisionAttendHOD!123"
FACULTY_EMAIL = "faculty@visionattend.com"
FACULTY_PASSWORD = "VisionAttendFaculty!123"


@dataclass
class ProvisionedUser:
    email: str
    password: str
    user_id: str
    role: str
    department_id: str | None = None
    faculty_id: str | None = None
    subject_id: str | None = None
    subject_code: str | None = None


def to_asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


class AuthAdminClient:
    def __init__(self, *, base_url: str, service_role_key: str) -> None:
        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/auth/v1",
            headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
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

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        for user in self.list_users():
            if user.get("email") == email:
                return user
        return None

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/admin/users", body=payload)

    def update_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", f"/admin/users/{user_id}", body=payload)


def ensure_auth_user(
    auth_admin: AuthAdminClient,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str,
    department_id: str | None,
) -> dict[str, Any]:
    existing = auth_admin.find_user_by_email(email)
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"full_name": full_name},
        "app_metadata": {"role": role, "department_id": department_id},
    }

    if existing is None:
        try:
            return auth_admin.create_user(payload)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 422:
                raise
            existing = auth_admin.find_user_by_email(email)
            if existing is None:
                raise

    return auth_admin.update_user(existing["id"], payload)


async def ensure_department(conn: asyncpg.Connection) -> asyncpg.Record:
    existing = await conn.fetchrow(
        "select id, code, name, hod_user_id from public.departments where code = $1",
        DEPARTMENT_CODE,
    )
    if existing:
        return existing

    return await conn.fetchrow(
        """
        insert into public.departments (code, name)
        values ($1, $2)
        returning id, code, name, hod_user_id
        """,
        DEPARTMENT_CODE,
        DEPARTMENT_NAME,
    )


async def ensure_public_user(
    conn: asyncpg.Connection,
    *,
    user_id: str,
    full_name: str,
    email: str,
    role: str,
    department_id: str | None,
) -> None:
    await conn.execute(
        """
        insert into public.users (id, full_name, email, role, department_id, is_active)
        values ($1, $2, $3, $4::public.app_role, $5, true)
        on conflict (id) do update
        set full_name = excluded.full_name,
            email = excluded.email,
            role = excluded.role,
            department_id = excluded.department_id,
            is_active = true,
            updated_at = now()
        """,
        user_id,
        full_name,
        email,
        role,
        department_id,
    )


async def ensure_faculty(
    conn: asyncpg.Connection,
    *,
    user_id: str,
    department_id: str,
    employee_code: str,
    designation: str,
) -> asyncpg.Record:
    existing = await conn.fetchrow(
        "select id, user_id, department_id from public.faculty where user_id = $1",
        user_id,
    )
    if not existing:
        existing = await conn.fetchrow(
            "select id, user_id, department_id from public.faculty where employee_code = $1",
            employee_code,
        )
    if existing:
        return await conn.fetchrow(
            """
            update public.faculty
            set user_id = $2,
                department_id = $3,
                employee_code = $4,
                designation = $5,
                updated_at = now()
            where id = $1
            returning id, user_id, department_id
            """,
            existing["id"],
            user_id,
            department_id,
            employee_code,
            designation,
        )

    return await conn.fetchrow(
        """
        insert into public.faculty (user_id, department_id, employee_code, designation)
        values ($1, $2, $3, $4)
        returning id, user_id, department_id
        """,
        user_id,
        department_id,
        employee_code,
        designation,
    )


async def ensure_hod_assignment(conn: asyncpg.Connection, *, department_id: str, hod_user_id: str) -> None:
    await conn.execute(
        "update public.departments set hod_user_id = $2, updated_at = now() where id = $1",
        department_id,
        hod_user_id,
    )


async def ensure_subject(
    conn: asyncpg.Connection,
    *,
    department_id: str,
    faculty_id: str,
    code: str,
    name: str,
    semester: int,
    section: str,
) -> asyncpg.Record:
    existing = await conn.fetchrow(
        """
        select id, faculty_id
        from public.subjects
        where department_id = $1 and code = $2 and semester = $3 and section = $4
        """,
        department_id,
        code,
        semester,
        section,
    )
    if existing:
        return await conn.fetchrow(
            """
            update public.subjects
            set name = $2,
                faculty_id = $3,
                attendance_grace_minutes = 15,
                is_active = true,
                updated_at = now()
            where id = $1
            returning id, code, name, faculty_id
            """,
            existing["id"],
            name,
            faculty_id,
        )

    return await conn.fetchrow(
        """
        insert into public.subjects (code, name, department_id, faculty_id, semester, section, attendance_grace_minutes, is_active)
        values ($1, $2, $3, $4, $5, $6, 15, true)
        returning id, code, name, faculty_id
        """,
        code,
        name,
        department_id,
        faculty_id,
        semester,
        section,
    )


async def provision() -> dict[str, Any]:
    settings = get_settings()
    conn = await asyncpg.connect(to_asyncpg_dsn(settings.database_url))
    auth_admin = AuthAdminClient(
        base_url=str(settings.supabase_url),
        service_role_key=settings.supabase_service_role_key.get_secret_value(),
    )

    try:
        department = await ensure_department(conn)
        department_id = str(department["id"])

        admin_auth = ensure_auth_user(
            auth_admin,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            full_name=\"VisionAttend Admin\",
            role="admin",
            department_id=None,
        )
        admin_user_id = admin_auth["id"]
        await ensure_public_user(
            conn,
            user_id=admin_user_id,
            full_name=\"VisionAttend Admin\",
            email=ADMIN_EMAIL,
            role="admin",
            department_id=None,
        )

        hod_auth = ensure_auth_user(
            auth_admin,
            email=HOD_EMAIL,
            password=HOD_PASSWORD,
            full_name="Aarav Mehta",
            role="hod",
            department_id=department_id,
        )
        hod_user_id = hod_auth["id"]
        await ensure_public_user(
            conn,
            user_id=hod_user_id,
            full_name="Aarav Mehta",
            email=HOD_EMAIL,
            role="hod",
            department_id=department_id,
        )
        hod_faculty = await ensure_faculty(
            conn,
            user_id=hod_user_id,
            department_id=department_id,
            employee_code="ATT-HOD-001",
            designation="Head of Department",
        )
        await ensure_hod_assignment(conn, department_id=department_id, hod_user_id=hod_user_id)
        hod_subject = await ensure_subject(
            conn,
            department_id=department_id,
            faculty_id=str(hod_faculty["id"]),
            code=HOD_SUBJECT_CODE,
            name=HOD_SUBJECT_NAME,
            semester=8,
            section="A",
        )

        faculty_auth = ensure_auth_user(
            auth_admin,
            email=FACULTY_EMAIL,
            password=FACULTY_PASSWORD,
            full_name="Riya Sen",
            role="faculty",
            department_id=department_id,
        )
        faculty_user_id = faculty_auth["id"]
        await ensure_public_user(
            conn,
            user_id=faculty_user_id,
            full_name="Riya Sen",
            email=FACULTY_EMAIL,
            role="faculty",
            department_id=department_id,
        )
        faculty_profile = await ensure_faculty(
            conn,
            user_id=faculty_user_id,
            department_id=department_id,
            employee_code="ATT-FAC-001",
            designation="Assistant Professor",
        )
        faculty_subject = await ensure_subject(
            conn,
            department_id=department_id,
            faculty_id=str(faculty_profile["id"]),
            code=FACULTY_SUBJECT_CODE,
            name=FACULTY_SUBJECT_NAME,
            semester=6,
            section="A",
        )

        return {
            "system_name": "VisionAttend Platform",
            "department": {
                "id": department_id,
                "code": DEPARTMENT_CODE,
                "name": DEPARTMENT_NAME,
            },
            "users": {
                "admin": ProvisionedUser(
                    email=ADMIN_EMAIL,
                    password=ADMIN_PASSWORD,
                    user_id=admin_user_id,
                    role="admin",
                ).__dict__,
                "hod": ProvisionedUser(
                    email=HOD_EMAIL,
                    password=HOD_PASSWORD,
                    user_id=hod_user_id,
                    role="hod",
                    department_id=department_id,
                    faculty_id=str(hod_faculty["id"]),
                    subject_id=str(hod_subject["id"]),
                    subject_code=HOD_SUBJECT_CODE,
                ).__dict__,
                "faculty": ProvisionedUser(
                    email=FACULTY_EMAIL,
                    password=FACULTY_PASSWORD,
                    user_id=faculty_user_id,
                    role="faculty",
                    department_id=department_id,
                    faculty_id=str(faculty_profile["id"]),
                    subject_id=str(faculty_subject["id"]),
                    subject_code=FACULTY_SUBJECT_CODE,
                ).__dict__,
            },
        }
    finally:
        auth_admin.close()
        await conn.close()


def main() -> None:
    output = asyncio.run(provision())
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
