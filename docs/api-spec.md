# API Specification

## API Conventions

- Base path: `/v1`
- Authentication: Supabase JWT in `Authorization: Bearer <token>`
- Content type: `application/json` unless uploading directly to signed storage URLs
- Time format: ISO 8601 UTC timestamps
- Idempotency: attendance writes are protected by a unique database constraint and should also accept an optional `Idempotency-Key` header

## Auth Strategy

Supabase Auth is the primary authentication system. The web frontend should authenticate directly with Supabase. If a unified backend entry point is required, `POST /v1/auth/login` can proxy to Supabase Auth without introducing a second credential store.

## Standard Error Response

```json
{
  "error": {
    "code": "attendance_duplicate",
    "message": "Attendance already exists for this student and session.",
    "details": {
      "student_id": "uuid",
      "subject_id": "uuid",
      "class_date": "2026-03-14",
      "session_key": "period-1"
    }
  }
}
```

## Endpoint Summary

| Method | Path | Purpose | Roles |
| --- | --- | --- | --- |
| POST | `/v1/auth/login` | Optional backend pass-through to Supabase Auth | Public |
| GET | `/v1/auth/me` | Resolve current profile and permissions | Admin, HOD, Faculty |
| GET | `/v1/faculty/subjects` | List subjects assigned to the active faculty user | Faculty, HOD |
| POST | `/v1/subjects/{subject_id}/assign-faculty` | Assign or reassign a subject to a faculty profile | Admin, HOD |
| POST | `/v1/students/register` | Create a student profile | Faculty, HOD |
| GET | `/v1/students` | List students filtered by department, semester, section, subject | Admin, HOD, Faculty |
| POST | `/v1/students/{student_id}/upload-face-url` | Create a signed upload URL for a face sample | Faculty, HOD |
| POST | `/v1/students/{student_id}/generate-embedding` | Generate embeddings from uploaded images | Faculty, HOD |
| POST | `/v1/recognition/identify` | Identify multiple faces for an attendance session | Faculty, HOD |
| POST | `/v1/attendance/mark` | Persist accepted attendance matches | Faculty, HOD |
| GET | `/v1/attendance/report` | Query attendance records and aggregates | Admin, HOD, Faculty |
| GET | `/v1/analytics/overview` | Dashboard KPIs | Admin, HOD, Faculty |
| GET | `/v1/analytics/trend` | Attendance trend series | Admin, HOD, Faculty |
| GET | `/v1/analytics/subjects` | Subject-wise attendance analytics | Admin, HOD, Faculty |
| GET | `/v1/reports/export` | Export CSV, Excel, or PDF reports | Admin, HOD, Faculty |

## Detailed Contracts

### POST /v1/auth/login

Used only if the frontend does not call Supabase Auth directly.

Request:

```json
{
  "email": "faculty@example.edu",
  "password": "secret"
}
```

Response:

```json
{
  "access_token": "jwt",
  "refresh_token": "refresh-token",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "role": "faculty",
    "department_id": "uuid"
  }
}
```

### GET /v1/auth/me

Response:

```json
{
  "id": "uuid",
  "full_name": "Dr. Asha Rao",
  "email": "faculty@example.edu",
  "role": "hod",
  "department_id": "uuid",
  "faculty_profile_id": "uuid"
}
```

### GET /v1/faculty/subjects

Query parameters:

- `semester` optional
- `section` optional
- `active_only` default `true`

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "code": "CSE-402",
      "name": "Machine Learning",
      "department_id": "uuid",
      "semester": 6,
      "section": "A",
      "faculty_id": "uuid",
      "is_active": true
    }
  ]
}
```

### POST /v1/subjects/{subject_id}/assign-faculty

Request:

```json
{
  "faculty_id": "uuid"
}
```

Business rules:

- Subject and faculty must belong to the same department.
- Only admin or the HOD of that department may assign.

### POST /v1/students/register

Request:

```json
{
  "full_name": "Rahul Kumar",
  "roll_number": "CSE23A014",
  "department_id": "uuid",
  "semester": 6,
  "section": "A",
  "batch_year": 2023,
  "email": "rahul@example.edu"
}
```

Response:

```json
{
  "id": "uuid",
  "full_name": "Rahul Kumar",
  "roll_number": "CSE23A014",
  "image_url": null,
  "created_at": "2026-03-14T10:15:00Z"
}
```

### GET /v1/students

Query parameters:

- `department_id` optional for admin
- `semester` optional
- `section` optional
- `subject_id` optional
- `search` optional
- `limit` default `50`
- `cursor` optional

### POST /v1/students/{student_id}/upload-face-url

Request:

```json
{
  "content_type": "image/jpeg",
  "file_name": "capture-01.jpg"
}
```

Response:

```json
{
  "storage_path": "students/uuid/raw/capture-01.jpg",
  "signed_upload_url": "https://...",
  "expires_in": 300
}
```

### POST /v1/students/{student_id}/generate-embedding

Request:

```json
{
  "images": [
    {
      "storage_path": "students/uuid/raw/capture-01.jpg",
      "sample_source": "camera"
    }
  ],
  "set_primary": true
}
```

Response:

```json
{
  "student_id": "uuid",
  "processed": 5,
  "accepted": 4,
  "rejected": 1,
  "primary_embedding_id": "uuid"
}
```

### POST /v1/recognition/identify

Purpose: submit multiple detected faces from one browser frame.

Request:

```json
{
  "subject_id": "uuid",
  "class_date": "2026-03-14",
  "session_key": "period-1",
  "session_label": "Period 1",
  "faces": [
    {
      "face_id": "frame-face-1",
      "image_base64": "...",
      "bounding_box": {
        "x": 101,
        "y": 42,
        "width": 144,
        "height": 144
      },
      "landmarks": {
        "left_eye": [120, 80],
        "right_eye": [180, 81],
        "nose_tip": [150, 110]
      }
    }
  ]
}
```

Response:

```json
{
  "matches": [
    {
      "face_id": "frame-face-1",
      "student_id": "uuid",
      "student_name": "Rahul Kumar",
      "confidence_score": 0.9412,
      "decision": "accepted"
    }
  ],
  "unmatched": [],
  "duplicates": []
}
```

### POST /v1/attendance/mark

Request:

```json
{
  "subject_id": "uuid",
  "class_date": "2026-03-14",
  "session_key": "period-1",
  "session_label": "Period 1",
  "entries": [
    {
      "student_id": "uuid",
      "confidence_score": 0.9412,
      "recognition_metadata": {
        "face_id": "frame-face-1",
        "model_version": "arcface-r100-v1"
      }
    }
  ]
}
```

Rules:

- The caller must own the subject or be the HOD of the subject department.
- Duplicate rows are rejected by the database unique constraint.
- Each insert stores `marked_by_user_id`, `faculty_id`, `confidence_score`, and `captured_at`.

### GET /v1/attendance/report

Query parameters:

- `subject_id` optional
- `department_id` optional for admin
- `student_id` optional
- `from_date` required
- `to_date` required
- `section` optional
- `format` optional: `json`, `csv`, `xlsx`, `pdf`

### GET /v1/analytics/overview

Response:

```json
{
  "total_students": 540,
  "total_faculty": 28,
  "total_subjects": 62,
  "today_attendance_percent": 91.2,
  "average_attendance_percent": 86.7
}
```

### GET /v1/analytics/trend

Response:

```json
{
  "points": [
    {
      "date": "2026-03-01",
      "attendance_percent": 88.2
    }
  ]
}
```

### GET /v1/analytics/subjects

Response:

```json
{
  "items": [
    {
      "subject_id": "uuid",
      "subject_name": "Machine Learning",
      "attendance_percent": 89.5
    }
  ]
}
```

### GET /v1/reports/export

Query parameters:

- `type` required: `daily`, `monthly`, `subject`, `student`, `department`
- `format` required: `csv`, `xlsx`, `pdf`
- `subject_id` optional
- `student_id` optional
- `department_id` optional
- `from_date` required
- `to_date` required

Response:

```json
{
  "file_name": "attendance-report-2026-03.pdf",
  "signed_download_url": "https://...",
  "expires_in": 600
}
```

## API Notes For Phase 2

1. All endpoints should be versioned under `/v1`.
2. Pydantic models must validate semester ranges, UUIDs, content types, and confidence values.
3. Attendance endpoints should be wrapped in database transactions.
4. Recognition should be separated from attendance persistence so low-confidence faces can be reviewed before insertion.