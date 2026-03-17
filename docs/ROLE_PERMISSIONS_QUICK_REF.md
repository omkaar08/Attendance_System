# Role Permissions - Quick Reference

## 🎓 FACULTY (Instructor)

### What Faculty Can Do:
```
✅ Login & manage profile
✅ View students in assigned subjects
✅ Register new students
✅ Enroll student faces (capture & store)
✅ Mark attendance using face recognition
✅ Identify multiple faces in camera frame
✅ View & delete face embeddings
✅ Generate attendance reports
✅ Generate daily/monthly/subject/student reports
✅ View low attendance alerts
✅ Access analytics for their subjects
✅ Real-time WebSocket notifications
```

### What Faculty CANNOT Do:
```
❌ Create subjects
❌ Assign faculty to subjects
❌ Bulk import/export students
❌ View other departments
❌ Create faculty accounts
❌ View system audit logs
❌ Perform system maintenance
❌ Access all departments' data
❌ Create/delete departments
```

### Faculty Access Level: **SCOPED** (Assigned Subjects Only)

---

## 👔 HOD (Head of Department)

### All FACULTY Features PLUS:

```
✅ Create new subjects for department
✅ Assign faculty to subjects
✅ View all faculty in department
✅ Create faculty accounts
✅ Bulk import students from CSV
✅ Bulk export students to CSV
✅ CSV validation & error tracking
✅ View department analytics
✅ Generate department-level reports
✅ Monitor faculty workload
✅ View all students in department
```

### What HOD CANNOT Do:
```
❌ Create departments
❌ Delete departments
❌ Assign HOD roles
❌ View other departments' data
❌ Create admin accounts
❌ View system audit logs
❌ Perform system cleanup
❌ Access system configuration
❌ View institution-wide admin functions
```

### HOD Access Level: **DEPARTMENT SCOPED**

---

## 👨‍💼 ADMIN (System Administrator)

### All FACULTY + HOD Features PLUS:

```
✅ Full system access (NO SCOPING)
✅ Create departments
✅ Delete departments
✅ Assign HODs to departments
✅ View all faculty globally
✅ Create faculty accounts
✅ Manage all subjects
✅ View all students
✅ Bulk import students globally
✅ Bulk export all students
✅ View complete audit logs
✅ Filter audit by actor/event/severity
✅ Perform system cleanup
✅ Check system health
✅ Manage WebSocket connections
✅ Institution-level analytics
✅ ALL reports (any combination)
✅ NO departmental restrictions
✅ Complete data access
```

### What ADMIN CAN See:
```
✅ All departments
✅ All faculty
✅ All students
✅ All attendance
✅ All subjects
✅ All reports
✅ System configuration
✅ Audit trail
✅ Security events
✅ System metrics
```

### Admin Access Level: **UNRESTRICTED GLOBAL ACCESS**

---

## 📋 Feature Comparison

| Feature | Faculty | HOD | Admin |
|---------|:-------:|:---:|:-----:|
| Login | ✅ | ✅ | ✅ |
| View Students | ✅* | ✅* | ✅ |
| Register Students | ✅* | ✅* | ✅ |
| Mark Attendance | ✅* | ✅ | ✅ |
| View Reports | ✅* | ✅* | ✅ |
| Create Subjects | ❌ | ✅ | ✅ |
| Assign Faculty | ❌ | ✅ | ✅ |
| Bulk Import | ❌ | ✅ | ✅ |
| Create Faculty | ❌ | ✅ | ✅ |
| Create Department | ❌ | ❌ | ✅ |
| View Audit Logs | ❌ | ❌ | ✅ |
| System Cleanup | ❌ | ❌ | ✅ |

*\*Limited to department/subject scope*

---

## 🔐 Data Access Model

```
FACULTY:
├─ Own subjects
├─ Students in own subjects
├─ Attendance for own subjects
└─ Reports for own subjects
   (Cannot see other departments)

HOD:
├─ Department subjects
├─ Department students
├─ Department attendance
├─ Department faculty
└─ Department reports
   (Cannot see other departments)

ADMIN:
├─ All departments ←━━━━━━━┓
├─ All subjects         ║
├─ All students         ║ NO RESTRICTIONS
├─ All faculty          ║ FULL ACCESS
├─ All attendance       ║
├─ All reports       ←━━┛
└─ System configuration
```

---

## 💼 Typical Workflows

### FACULTY Workflow (Daily)
```
1. Login
2. Open "Mark Attendance"
3. Select Subject
4. Open Camera
5. Recognize Faces
6. Confirm Attendance
7. View Report (Optional)
```

### HOD Workflow (Semester)
```
1. Login
2. Create Subjects
3. Assign Faculty
4. Bulk Import Students (CSV)
5. Review Departments
6. Monitor Attendance
7. Generate Reports
```

### ADMIN Workflow (Setup & Maintenance)
```
1. Login
2. Create Departments
3. Assign HODs
4. System Configuration
5. Monitor Audit Logs
6. Cleanup Old Data
7. Check System Health
```

---

## 🎯 Key Differences at a Glance

| Aspect | Faculty | HOD | Admin |
|--------|---------|-----|-------|
| Primary Role | Mark attendance | Manage department | System oversight |
| Data Scope | Subject-level | Department-level | Institution-wide |
| Can Create Users | No | Yes (Faculty) | Yes (All) |
| Can Create Subjects | No | Yes | Yes |
| Can Import Bulk | No | Yes | Yes |
| View Audit Logs | No | No | Yes |
| System Maintenance | No | No | Yes |
| Access Level | **Narrow** | **Medium** | **Unlimited** |

---

## 🚀 Permission Rules

### Faculty Rules:
- Can only access their assigned subjects
- Can only see students in their subjects
- Cannot create or manage other users
- Cannot access other departments

### HOD Rules:
- Can access all department data
- Cannot access other departments
- Can create faculty (in their dept)
- Cannot create HOD or Admin

### Admin Rules:
- Can access EVERYTHING
- No scoping limitations
- Can create any role
- Can access audit logs

---

**System Version:** Phase 7 - Production Ready  
**Generated:** March 17, 2026  
**See Full Details:** `docs/ROLE_BASED_FEATURES.md`
