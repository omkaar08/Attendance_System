import asyncio
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from supabase_auth.errors import AuthApiError

from app.main import app
from app.services.supabase import get_service_supabase_client


TEST_EMAIL = "phase2.faculty@example.com"
TEST_PASSWORD = "Phase2Faculty!123"
DEPARTMENT_CODE = "MM-CSE"
DEPARTMENT_NAME = "Computer Science And Engineering"
SUBJECT_CODE = "MM-CSE-ML-01"
SUBJECT_NAME = "Machine Learning"
SUBJECT_SECTION = "A"
SUBJECT_SEMESTER = 6


@dataclass
class SeedContext:
    user_id: str
    faculty_id: str
    department_id: str
    subject_id: str


def _extract_data(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if hasattr(response, "data"):
        data = response.data
        return data if isinstance(data, list) else [data]
    if isinstance(response, dict):
        data = response.get("data", response)
        return data if isinstance(data, list) else [data]
    return []


def _single_or_none(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[0] if rows else None


def ensure_department(client) -> dict[str, Any]:
    existing = _single_or_none(
        _extract_data(
            client.table("departments").select("id,code,name").eq("code", DEPARTMENT_CODE).limit(1).execute()
        )
    )
    if existing:
        return existing

    created = _single_or_none(
        _extract_data(
            client.table("departments")
            .insert({"code": DEPARTMENT_CODE, "name": DEPARTMENT_NAME})
            .execute()
        )
    )
    if not created:
        raise RuntimeError("Failed to create department.")
    return created


def _find_user_by_email(admin_client, email: str) -> Any | None:
    page = 1
    per_page = 1000
    while True:
        listed = admin_client.list_users(page=page, per_page=per_page)
        users = listed
        if users is None and isinstance(listed, dict):
            users = listed.get("users", [])
        if users is None:
            users = []
        for user in users:
            user_email = getattr(user, "email", None) if not isinstance(user, dict) else user.get("email")
            if user_email == email:
                return user
        if len(users) < per_page:
            break
        page += 1
    return None


def _user_id(user: Any) -> str:
    return getattr(user, "id", None) if not isinstance(user, dict) else user.get("id")


def ensure_auth_user(client, department_id: str) -> Any:
    admin_client = client.auth.admin
    user = _find_user_by_email(admin_client, TEST_EMAIL)
    if user is None:
        try:
            created = admin_client.create_user(
                {
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "email_confirm": True,
                    "user_metadata": {"full_name": "Phase2 Faculty"},
                    "app_metadata": {"role": "faculty", "department_id": department_id},
                }
            )
        except AuthApiError as exc:
            if "already been registered" not in str(exc):
                raise
            user = _find_user_by_email(admin_client, TEST_EMAIL)
            if user is None:
                raise
            created = None
        user = getattr(created, "user", None)
        if user is None and isinstance(created, dict):
            user = created.get("user")
        if user is None:
            user = _find_user_by_email(admin_client, TEST_EMAIL)
        if user is None:
            raise RuntimeError("Failed to resolve auth user.")
    else:
        admin_client.update_user_by_id(
            _user_id(user),
            {
                "password": TEST_PASSWORD,
                "user_metadata": {"full_name": "Phase2 Faculty"},
                "app_metadata": {"role": "faculty", "department_id": department_id},
            },
        )
    return user


def ensure_user_profile(client, user_id: str, department_id: str) -> dict[str, Any]:
    row = {
        "id": user_id,
        "full_name": "Phase2 Faculty",
        "email": TEST_EMAIL,
        "role": "faculty",
        "department_id": department_id,
        "is_active": True,
    }
    updated = _single_or_none(
        _extract_data(client.table("users").upsert(row, on_conflict="id").execute())
    )
    if not updated:
        raise RuntimeError("Failed to upsert public.users profile.")
    return updated


def ensure_faculty(client, user_id: str, department_id: str) -> dict[str, Any]:
    existing = _single_or_none(
        _extract_data(client.table("faculty").select("id,user_id,department_id").eq("user_id", user_id).limit(1).execute())
    )
    if existing:
        if existing.get("department_id") != department_id:
            updated = _single_or_none(
                _extract_data(
                    client.table("faculty")
                    .update({"department_id": department_id})
                    .eq("id", existing["id"])
                    .execute()
                )
            )
            return updated or existing
        return existing

    employee_code = f"FAC-{user_id[:8].upper()}"
    created = _single_or_none(
        _extract_data(
            client.table("faculty")
            .insert(
                {
                    "user_id": user_id,
                    "department_id": department_id,
                    "employee_code": employee_code,
                    "designation": "Assistant Professor",
                }
            )
            .execute()
        )
    )
    if not created:
        raise RuntimeError("Failed to create faculty profile.")
    return created


def ensure_subject(client, department_id: str, faculty_id: str) -> dict[str, Any]:
    existing = _single_or_none(
        _extract_data(
            client.table("subjects")
            .select("id,code,faculty_id,department_id,semester,section")
            .eq("department_id", department_id)
            .eq("code", SUBJECT_CODE)
            .eq("semester", SUBJECT_SEMESTER)
            .eq("section", SUBJECT_SECTION)
            .limit(1)
            .execute()
        )
    )
    if existing:
        if existing.get("faculty_id") != faculty_id:
            updated = _single_or_none(
                _extract_data(
                    client.table("subjects")
                    .update({"faculty_id": faculty_id})
                    .eq("id", existing["id"])
                    .execute()
                )
            )
            return updated or existing
        return existing

    created = _single_or_none(
        _extract_data(
            client.table("subjects")
            .insert(
                {
                    "code": SUBJECT_CODE,
                    "name": SUBJECT_NAME,
                    "department_id": department_id,
                    "faculty_id": faculty_id,
                    "semester": SUBJECT_SEMESTER,
                    "section": SUBJECT_SECTION,
                    "attendance_grace_minutes": 15,
                    "is_active": True,
                }
            )
            .execute()
        )
    )
    if not created:
        raise RuntimeError("Failed to create subject.")
    return created


def seed_supabase() -> SeedContext:
    client = get_service_supabase_client()

    department = ensure_department(client)
    auth_user = ensure_auth_user(client, department["id"])
    user_id = _user_id(auth_user)
    if not user_id:
        raise RuntimeError("Could not resolve auth user id.")

    ensure_user_profile(client, user_id, department["id"])
    faculty = ensure_faculty(client, user_id, department["id"])
    subject = ensure_subject(client, department["id"], faculty["id"])

    return SeedContext(
        user_id=user_id,
        faculty_id=faculty["id"],
        department_id=department["id"],
        subject_id=subject["id"],
    )


async def run_api_smoke(context: SeedContext) -> dict[str, Any]:
    def ensure_ok(response: httpx.Response, name: str, extra: dict[str, Any] | None = None) -> None:
        if response.status_code < 400:
            return
        diagnostic = {
            "check": name,
            "status_code": response.status_code,
            "response": response.text,
            "extra": extra or {},
        }
        raise RuntimeError(json.dumps(diagnostic, indent=2))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        login_response = await client.post(
            "/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        ensure_ok(login_response, "auth_login")
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        subjects_response = await client.get("/v1/faculty/subjects", headers=headers)
        ensure_ok(subjects_response, "faculty_subjects")
        subjects = subjects_response.json().get("items", [])

        unique_roll = f"MM{int(time.time())}"
        student_response = await client.post(
            "/v1/students/register",
            headers=headers,
            json={
                "full_name": "Phase2 Student",
                "roll_number": unique_roll,
                "department_id": context.department_id,
                "semester": SUBJECT_SEMESTER,
                "section": SUBJECT_SECTION,
                "batch_year": 2026,
                "email": f"{unique_roll.lower()}@example.edu",
            },
        )
        ensure_ok(student_response, "students_register")
        student = student_response.json()

        attendance_response = await client.post(
            "/v1/attendance/mark",
            headers=headers,
            json={
                "subject_id": context.subject_id,
                "class_date": str(date.today()),
                "session_key": "period-1",
                "session_label": "Period 1",
                "entries": [
                    {
                        "student_id": student["id"],
                        "confidence_score": 0.95,
                        "recognition_metadata": {"source": "phase2-verify"},
                    }
                ],
            },
        )
        ensure_ok(attendance_response, "attendance_mark")

        analytics_response = await client.get("/v1/analytics/overview", headers=headers)
        ensure_ok(analytics_response, "analytics_overview")

        report_response = await client.get(
            "/v1/attendance/report",
            headers=headers,
            params={"from_date": str(date.today()), "to_date": str(date.today())},
        )
        ensure_ok(report_response, "attendance_report")

        return {
            "login_status": login_response.status_code,
            "subjects_count": len(subjects),
            "student_id": student["id"],
            "attendance_mark_status": attendance_response.status_code,
            "attendance_accepted_count": len(attendance_response.json().get("accepted", [])),
            "analytics_status": analytics_response.status_code,
            "report_status": report_response.status_code,
            "report_records": report_response.json().get("summary", {}).get("total_records", 0),
        }


def main() -> None:
    context = seed_supabase()
    results = asyncio.run(run_api_smoke(context))
    output = {
        "seed": {
            "department_id": context.department_id,
            "faculty_user_id": context.user_id,
            "faculty_id": context.faculty_id,
            "subject_id": context.subject_id,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
        "checks": results,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()