# Security Model

## Security Objectives

1. Authenticate every human actor through Supabase Auth.
2. Authorize every operation by role, department, and subject ownership.
3. Prevent unauthorized access to images, embeddings, analytics, and reports.
4. Protect attendance integrity against duplicates, spoofing attempts, and direct database abuse.
5. Preserve an audit trail for every sensitive action.

## Identity And Authentication

- Supabase Auth is the system of record for identities.
- FastAPI validates Supabase JWTs on every protected request.
- The backend never stores raw passwords.
- Tokens must include `sub`, `email`, and expiration claims.
- Session refresh is handled by Supabase Auth clients.

## Authorization Layers

### Layer 1: Frontend Route Guards

- Hide pages and actions the current role cannot use.
- Treat client checks as UX only, never as the final security boundary.

### Layer 2: FastAPI Authorization

- Validate JWT on every request.
- Resolve the user profile from `public.users`.
- Enforce role checks with dependencies such as `require_admin`, `require_hod`, and `require_subject_owner`.
- Reject cross-department operations unless the user is admin.

### Layer 3: Supabase Row-Level Security

RLS is the database enforcement layer for direct reads, realtime subscriptions, and defense in depth.

## Role Access Matrix

| Resource | Admin | HOD | Faculty |
| --- | --- | --- | --- |
| Users | Global read/write | Department read | Self read |
| Departments | Global read/write | Own department read | Own department read |
| Faculty | Global read/write | Department read/write | Self read |
| Subjects | Global read/write | Department read/write | Assigned subjects read |
| Students | Global read/write | Department read | Department cohort read for assigned subjects |
| Attendance | Global read/write | Department read/write | Assigned-subject read/write |
| Face embeddings | Global read/write | Department read | Write for registered students in owned subject cohort |
| Storage objects | Signed access | Signed access within department scope | Signed access within owned student scope |

## RLS Strategy By Table

### public.users

- Self read by `auth.uid() = id`
- Admin full access
- HOD read access for users in the same department

### public.departments

- Admin full access
- HOD and faculty read their own department row

### public.faculty

- Admin full access
- HOD manage faculty inside their department
- Faculty read only their own row

### public.subjects

- Admin full access
- HOD manage subjects inside their department
- Faculty read only subjects assigned to their faculty profile

### public.students

- Admin full access
- HOD read all students in their department
- Faculty read and register students only for the cohorts they are responsible for

### public.attendance

- Admin full access
- HOD read and correct attendance for their department
- Faculty insert and read attendance only for their assigned subjects

### public.face_embeddings

- No direct browser access to vectors
- Admin and backend service can read embeddings
- Faculty and HOD may trigger embedding creation through FastAPI only

## Storage Security

- Buckets remain private.
- The browser uploads images only through short-lived signed URLs.
- Public URLs are not used for student face images.
- Object paths follow a predictable but access-controlled pattern:

```text
students/{student_id}/raw/{uuid}.jpg
students/{student_id}/processed/{uuid}.jpg
reports/{department_id}/{year}/{month}/{file_name}
```

- FastAPI validates object ownership before generating signed URLs.

## Attendance Integrity Controls

1. Unique constraint on `student_id + subject_id + class_date + session_key`
2. Subject ownership check before attendance write
3. Configurable confidence threshold per model version
4. Low-confidence matches returned for review instead of auto-write
5. Transactional insert to avoid partial success inconsistencies
6. Request tracing with request ID and actor ID

## API Security Controls

- JWT verification on every protected endpoint
- Role-based dependency injection in FastAPI
- Rate limits on login, recognition, and signed upload URL creation
- Request body size limits on face image payloads
- MIME type allowlist for image uploads
- Optional antivirus or image sanitizer on uploaded objects
- Structured audit logging for subject assignments, student registration, embedding creation, and attendance edits

## ML And Recognition Security

- Only cropped face images are sent to recognition; raw video is not persisted.
- Embedding generation runs in a trusted backend environment.
- Model version is stored with each embedding and attendance event.
- Embeddings are versioned so model upgrades do not silently corrupt historical behavior.
- Anti-spoofing and liveness detection are deferred to later phases, but the API contract must allow them to be inserted before attendance acceptance.

## Operational Security

- Secrets stored in environment variables and deployment secret stores only
- Separate keys for frontend public clients and backend service operations
- HTTPS required in all deployed environments
- Production logs must redact tokens, raw images, and embeddings
- Database backups and storage lifecycle rules must be enabled before production launch

## Phase 2 Implementation Notes

1. Enable RLS on all application tables before exposing any client-side queries.
2. Keep pgvector access behind the backend service.
3. Use service-role credentials only inside the backend and never in the browser.
4. Add rate limiting middleware before the recognition endpoints go live.