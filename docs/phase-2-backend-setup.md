# Phase 2 Backend Setup

This phase implements the production backend foundation for Supabase-backed attendance workflows.

## What Was Added

- FastAPI application scaffold in `backend/app`
- SQLAlchemy async database layer targeting Supabase PostgreSQL
- Supabase JWT verification and login proxy support
- Role-aware endpoints for subjects, students, attendance, and analytics
- Supabase signed upload URL generation for student and training images
- Database migrations for schema, auth sync, and row-level security
- Supabase bootstrap script for private storage buckets

## Backend Endpoints Implemented

- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `GET /v1/faculty/subjects`
- `POST /v1/subjects/{subject_id}/assign-faculty`
- `POST /v1/students/register`
- `POST /v1/students/upload-face`
- `POST /v1/students/{student_id}/upload-face-url`
- `GET /v1/students`
- `POST /v1/attendance/mark`
- `GET /v1/attendance/report`
- `GET /v1/analytics/overview`

## Supabase Setup Order

1. Create the Supabase project and enable PostgreSQL `pgvector`.
2. Disable public sign-up unless you intentionally support self-service onboarding.
3. Apply `database/migrations/0001_initial_schema.sql`.
4. Apply `database/migrations/0002_auth_sync_and_rls.sql`.
5. Configure auth users with trusted `app_metadata.role` and `app_metadata.department_id` values.
6. Run `backend/scripts/bootstrap_supabase.py` to create private storage buckets.

## Required Environment Variables

Set the values shown in `backend/.env.example` before running the API.

## Run The Backend

```powershell
cd backend
pip install -e .
uvicorn app.main:app --reload
```

## Important Notes

1. Attendance is session-aware through `class_date + session_key`.
2. Storage remains private; the browser only receives signed upload URLs.
3. `face_embeddings` has RLS enabled with no client-read policy, so embedding access stays behind backend service credentials.
4. Recognition endpoints and embedding generation are deferred to Phase 3.