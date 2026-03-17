# VisionAttend System - Role-Based Features & Permissions

**Date:** March 17, 2026  
**Version:** Phase 7 - Production Ready

---

## Role Overview

The VisionAttend system has **3 user roles** with different levels of access and capabilities:

1. **FACULTY** - Classroom instructor
2. **HOD** - Head of Department
3. **ADMIN** - System administrator

---

## 🎓 FACULTY (Instructor) Features

### Authentication & Profile
- ✅ Login with email and password
- ✅ View own profile information
- ✅ JWT token-based session management

### Student Management
- ✅ View students in assigned subjects
- ✅ Register new students in their subjects
- ✅ Search students by name, roll number, email
- ✅ Filter students by department, semester, section
- ✅ Upload face images for students
- ✅ Create face upload URLs for students

### Face Recognition & Attendance
- ✅ Enroll student faces (capture and store embeddings)
- ✅ Mark attendance using face recognition
- ✅ Identify multiple faces in a frame
- ✅ Auto-mark attendance when faces are recognized
- ✅ View face embeddings for students
- ✅ Delete/remove face embeddings from storage
- ✅ Quality metrics for enrolled faces:
  - Sharpness score
  - Brightness score
  - Liveness score (anti-spoofing)
  - Overall quality percentage

### Subject Management
- ✅ View assigned subjects
- ✅ List students for each subject
- ✅ Filter by semester and section

### Attendance Management
- ✅ Mark attendance for students in their subject
- ✅ View attendance report for their subjects
- ✅ Check low attendance alerts (students below 75%)
- ✅ Set custom attendance threshold (default 75%)
- ✅ Set minimum sessions threshold
- ✅ Filter attendance by date range, subject, department, student, section

### Analytics & Reporting
- ✅ View analytics overview (total students, faculty, avg attendance)
- ✅ Generate daily attendance reports
- ✅ Generate monthly attendance reports
- ✅ Generate subject-wise reports
- ✅ Generate student reports
- ✅ Download reports in structured format
- ✅ Filter reports by date range, subject, department

### Real-Time Features
- ✅ WebSocket connection for real-time attendance updates
- ✅ Live notification when face is recognized
- ✅ Session start/end notifications

### NOT Allowed for Faculty
- ❌ Create departments
- ❌ Create subjects (HOD only)
- ❌ Assign faculty to subjects (HOD only)
- ❌ Create/delete other faculty
- ❌ Assign HOD
- ❌ Import bulk students via CSV
- ❌ View audit logs
- ❌ Perform system cleanup
- ❌ Manage system settings

---

## 👔 HOD (Head of Department) Features

### All FACULTY Features PLUS:

### Subject Creation & Management
- ✅ Create new subjects for department
- ✅ Assign faculty to subjects
- ✅ View all subjects in department
- ✅ Subject code, name, and semester management

### Faculty Management
- ✅ View faculty list in department
- ✅ Create new faculty members
- ✅ Assign faculty to subjects
- ✅ Send invitations to faculty

### Student Management (Extended)
- ✅ Register students in department
- ✅ Bulk import students from CSV
- ✅ CSV format validation:
  - Required fields: name, roll_number, email, department_code, semester, section
  - Optional fields: phone
  - Automatic email format validation
  - Semester range validation (1-8)
  - Duplicate prevention
- ✅ View import results and error log
- ✅ Export department students to CSV
- ✅ Student filtering by department (scoped to their department)

### Department Management
- ✅ View department information
- ✅ View faculty assignments
- ✅ View students in department
- ✅ Generate department-level reports

### Analytics & Reporting (Extended)
- ✅ Department-wise attendance performance reports
- ✅ Faculty workload analysis
- ✅ Low attendance alerts for department
- ✅ All attendance reports filtered to their department

### Query Capabilities
- ✅ Query students with department scope
- ✅ Query faculty in their department
- ✅ Query attendance within department
- ✅ Generate reports for department only

### NOT Allowed for HOD
- ❌ Create departments
- ❌ Delete departments
- ❌ Assign HOD to other departments
- ❌ Create other faculty outside their department scoping
- ❌ View system-wide audit logs
- ❌ Perform system cleanup
- ❌ Create admin accounts
- ❌ Access other departments' data

---

## 👨‍💼 ADMIN (System Administrator) Features

### All FACULTY + HOD Features PLUS:

### System Management
- ✅ Full system access (no scoping)
- ✅ View all departments
- ✅ Create new departments
- ✅ Delete departments
- ✅ View all faculty
- ✅ Create faculty accounts
- ✅ View all students
- ✅ Manage all subjects

### Department Management (Full Control)
- ✅ Create departments
- ✅ Delete departments
- ✅ Assign HODs to departments
- ✅ View all departments globally

### Faculty Management (Full Control)
- ✅ Create faculty accounts
- ✅ View all faculty globally
- ✅ Assign faculty to subjects
- ✅ Manage role assignments

### Student Management (Full Control)
- ✅ Register students in any department
- ✅ Bulk import students globally
- ✅ Bulk export students (globally or filtered)
- ✅ CSV validation and processing
- ✅ View all students
- ✅ No department scoping - see everything

### Attendance Management (Full Control)
- ✅ Mark attendance for any student
- ✅ View global attendance reports
- ✅ Generate reports for all students/departments/subjects
- ✅ No scope limitations

### Analytics & Reporting (Global)
- ✅ Institution-level analytics
- ✅ Total students across institution
- ✅ Total faculty across institution
- ✅ System-wide average attendance
- ✅ All types of reports with global access
- ✅ No data restrictions

### Audit & Compliance
- ✅ View complete audit logs
- ✅ Filter audit logs by:
  - Actor (who performed action)
  - Event type (login, enrollment, etc.)
  - Resource type
  - Severity level (INFO, WARNING, CRITICAL)
  - Date range
- ✅ Track all system operations
- ✅ Security event monitoring

### System Maintenance
- ✅ Perform system cleanup operations
- ✅ Remove old embeddings (90-day retention policy)
- ✅ Trigger garbage collection
- ✅ Maintenance tasks
- ✅ System health check
- ✅ Check WebSocket connection count

### API Documentation
- ✅ Full access to Swagger UI
- ✅ All endpoints visible and documentedable
- ✅ OpenAPI schema access

---

## 📊 Feature Comparison Matrix

| Feature | Faculty | HOD | Admin |
|---------|---------|-----|-------|
| **Authentication** | | | |
| Login | ✅ | ✅ | ✅ |
| View Profile | ✅ | ✅ | ✅ |
| **Student Management** | | | |
| View Students | ✅ (scoped) | ✅ (dept) | ✅ (all) |
| Register Students | ✅ (scoped) | ✅ (dept) | ✅ (all) |
| Bulk Import CSV | ❌ | ✅ | ✅ |
| Bulk Export CSV | ❌ | ✅ (dept) | ✅ (all) |
| Upload Face | ✅ | ✅ | ✅ |
| **Subject Management** | | | |
| View Subjects | ✅ (assigned) | ✅ (dept) | ✅ (all) |
| Create Subjects | ❌ | ✅ | ✅ |
| Assign Faculty | ❌ | ✅ | ✅ |
| **Face Recognition** | | | |
| Enroll Faces | ✅ | ✅ | ✅ |
| Identify Faces | ✅ | ✅ | ✅ |
| Mark Attendance | ✅ | ✅ | ✅ |
| View Embeddings | ✅ | ✅ | ✅ |
| Delete Embeddings | ✅ | ✅ | ✅ |
| **Reporting** | | | |
| Attendance Reports | ✅ (scoped) | ✅ (dept) | ✅ (all) |
| Daily Reports | ✅ | ✅ | ✅ |
| Monthly Reports | ✅ | ✅ | ✅ |
| Subject Reports | ✅ | ✅ | ✅ |
| Student Reports | ✅ | ✅ | ✅ |
| Department Reports | ❌ | ✅ | ✅ |
| **Analytics** | | | |
| Overview Metrics | ✅ | ✅ | ✅ |
| Scoped Analytics | ✅ | ✅ (dept) | ✅ (all) |
| Low Attendance Alerts | ✅ | ✅ | ✅ |
| **Audit & Compliance** | | | |
| View Audit Logs | ❌ | ❌ | ✅ |
| Compliance Reports | ❌ | ❌ | ✅ |
| **System Administration** | | | |
| Create Departments | ❌ | ❌ | ✅ |
| Delete Departments | ❌ | ❌ | ✅ |
| Assign HOD | ❌ | ❌ | ✅ |
| Create Faculty | ❌ | ✅ | ✅ |
| System Cleanup | ❌ | ❌ | ✅ |
| System Health Check | ❌ | ❌ | ✅ |
| **Real-Time Features** | | | |
| WebSocket Notifications | ✅ | ✅ | ✅ |
| Live Updates | ✅ | ✅ | ✅ |

---

## 🔐 Data Access Scoping

### FACULTY Access Scope
```
What can see/access:
├── Own profile
├── Assigned subjects (only)
├── Students enrolled in their subjects
├── Attendance records for their subjects
├── Analytics for their subjects
└── Reports for their subjects

Cannot see:
├── Other faculty's subjects
├── Other departments' data
├── System-wide statistics
└── Audit logs
```

### HOD Access Scope
```
What can see/access:
├── Department profile
├── All faculty in department
├── All subjects in department
├── All students in department
├── Attendance for department
├── Analytics for department
├── Reports for department
└── Faculty assignments

Cannot see:
├── Other departments' data
├── System-wide audit logs
├── System configuration
└── Other HODs' departments
```

### ADMIN Access Scope
```
What can see/access:
├── ALL departments
├── ALL faculty (any department)
├── ALL students (any department)
├── ALL subjects (any department)
├── ALL attendance records
├── System-wide analytics
├── ALL reports (any filter)
├── Complete audit logs
└── System configuration/maintenance

No restrictions on:
├── Data access
├── Query filters
├── Scoping
└── Administrative operations
```

---

## 🎯 Common Use Cases by Role

### FACULTY - Daily Tasks
```
1. Login to system
2. View assigned subjects
3. See enrolled students
4. Capture student face images
5. Mark attendance using face recognition
6. Check low attendance alerts
7. Generate attendance report
8. Download for records
```

### HOD - Monthly Tasks
```
1. Login as HOD
2. Create new subjects for semester
3. Assign faculty to subjects
4. Bulk import students (semester start)
5. View department analytics
6. Check faculty workload
7. Generate department report
8. Monitor attendance trends
```

### ADMIN - Maintenance
```
1. Login as Admin
2. Create new departments
3. Assign HODs
4. Monitor system health
5. Perform cleanup operations
6. View audit logs
7. Check for security events
8. Generate system report
```

---

## API Endpoints by Role

### FACULTY Endpoints (20+ endpoints)
```
PUT /auth/login
GET /auth/me
GET /v1/subjects/faculty
GET /v1/students
POST /v1/students/register
POST /v1/students/upload-face
POST /v1/recognition/enroll
POST /v1/recognition/identify
GET /v1/recognition/students/{id}/embeddings
DELETE /v1/recognition/embeddings/{id}
POST /v1/attendance/mark
GET /v1/attendance/report
GET /v1/attendance/alerts/low
GET /v1/analytics/overview
GET /v1/reports/daily
GET /v1/reports/monthly
GET /v1/reports/subject
GET /v1/reports/student
WS /v1/ws/attendance/{subject}/{user}
GET /health
```

### HOD Extra Endpoints (8+ additional)
```
(All FACULTY endpoints)
PLUS:
POST /v1/subjects (create)
POST /v1/subjects/{id}/assign-faculty
GET /v1/management/faculty
POST /v1/management/faculty
GET /v1/management/departments
POST /v1/students/import-csv
GET /v1/students/export-csv
GET /v1/reports/department
```

### ADMIN Extra Endpoints (6+ additional)
```
(All FACULTY + HOD endpoints)
PLUS:
POST /v1/management/departments (create)
DELETE /v1/management/departments/{id}
POST /v1/management/departments/{id}/hod
GET /v1/audit/logs
POST /v1/system/cleanup
GET /v1/system/health (full info)
```

---

## 🔑 Authentication Token Scopes

Each role gets a JWT token with scope information:

### FACULTY Token
```json
{
  "role": "faculty",
  "user_id": "uuid",
  "faculty_id": "uuid",
  "department_id": null,
  "scope": "faculty_only"
}
```

### HOD Token
```json
{
  "role": "hod",
  "user_id": "uuid",
  "faculty_id": "uuid",
  "department_id": "uuid",
  "scope": "department"
}
```

### ADMIN Token
```json
{
  "role": "admin",
  "user_id": "uuid",
  "faculty_id": null,
  "department_id": null,
  "scope": "admin"
}
```

---

## ✅ Permission Enforcement

All permissions are enforced at:

1. **API Layer** - `require_roles()` dependency
   - Checks user role before executing endpoint
   - Returns 403 Forbidden if unauthorized

2. **Service Layer** - Business logic checks
   - Validates scoping (department, subject, student)
   - Checks data ownership

3. **Database Layer** - Row-Level Security (RLS)
   - Supabase RLS policies
   - Prevents data leakage
   - Enforces scoping at DB level

---

## Summary

| Role | Main Purpose | Key Abilities |
|------|--------------|---------------|
| **FACULTY** | Mark attendance via face recognition | Enroll faces, Mark attendance, View reports (own subjects) |
| **HOD** | Manage department operations | Create subjects, Manage faculty, Bulk import students |
| **ADMIN** | System oversight and maintenance | All operations, Audit logs, System maintenance |

---

**System Version:** Phase 7 - Production Ready  
**Last Updated:** March 17, 2026
