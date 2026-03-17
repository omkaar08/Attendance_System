export type AppRole = 'admin' | 'hod' | 'faculty'

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginUser {
  id: string
  role: AppRole
  department_id: string | null
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  user: LoginUser
}

export interface CurrentUserResponse {
  id: string
  full_name: string | null
  email: string
  role: AppRole
  department_id: string | null
  faculty_profile_id: string | null
}

export interface SubjectSummary {
  id: string
  code: string
  name: string
  department_id: string
  semester: number
  section: string
  faculty_id: string
  is_active: boolean
}

export interface SubjectListResponse {
  items: SubjectSummary[]
}

export interface SubjectCreateRequest {
  code: string
  name: string
  semester: number
  section: string
  faculty_id: string
  attendance_grace_minutes?: number
}

export interface StudentSummary {
  id: string
  full_name: string
  roll_number: string
  department_id: string
  semester: number
  section: string
  batch_year: number
  email: string | null
  image_url: string | null
  created_at: string
}

export interface StudentListResponse {
  items: StudentSummary[]
}

export interface StudentRegisterRequest {
  full_name: string
  roll_number: string
  department_id: string
  semester: number
  section: string
  batch_year: number
  email?: string
}

export interface FaceUploadRequest {
  student_id: string
  file_name: string
  content_type: 'image/jpeg' | 'image/png' | 'image/webp'
  asset_kind?: 'student-image' | 'face-training'
}

export interface FaceUploadResponse {
  bucket: string
  storage_path: string
  signed_upload_url: string
  token: string | null
  expires_in: number
  created_at: string
}

export interface EnrollRequest {
  student_id: string
  image_base64: string
  source?: 'camera' | 'upload' | 'imported'
  storage_path?: string
}

export interface EmbeddingMeta {
  id: string
  student_id: string
  model_name: string
  model_version: string
  sample_source: string
  quality_score: number
  is_primary: boolean
  status: string
  storage_path: string | null
  created_at: string
}

export interface EnrollResponse {
  embedding: EmbeddingMeta
  warning: string | null
}

export interface EmbeddingListResponse {
  items: EmbeddingMeta[]
  total: number
}

export interface IdentifyRequest {
  frame_base64: string
  subject_id: string
  class_date: string
  session_key: string
  session_label: string
  auto_mark_attendance: boolean
}

export interface RecognizedFace {
  student_id: string
  full_name: string
  roll_number: string
  confidence: number
  attendance_marked: boolean
  attendance_id: string | null
}

export interface IdentifyResponse {
  recognized: RecognizedFace[]
  frame_face_count: number
  unmatched_face_count: number
}

export interface AnalyticsOverviewResponse {
  total_students: number
  total_faculty: number
  total_subjects: number
  today_attendance_percent: number
  average_attendance_percent: number
}

export type AttendanceStatus = 'present' | 'late' | 'absent' | 'excused'

export interface AttendanceReportItem {
  id: string
  student_id: string
  student_name: string
  roll_number: string
  subject_id: string
  subject_name: string
  faculty_id: string
  class_date: string
  session_key: string
  session_label: string
  status: AttendanceStatus
  confidence_score: number
  captured_at: string
}

export interface AttendanceReportSummary {
  total_records: number
  present_count: number
  late_count: number
  average_confidence_score: number | null
}

export interface AttendanceReportResponse {
  items: AttendanceReportItem[]
  summary: AttendanceReportSummary
}

export interface LowAttendanceAlertItem {
  student_id: string
  full_name: string
  roll_number: string
  subject_id: string
  subject_name: string
  department_id: string
  semester: number
  section: string
  total_sessions: number
  present_sessions: number
  attendance_percent: number
}

export interface LowAttendanceAlertResponse {
  threshold_percent: number
  min_sessions: number
  items: LowAttendanceAlertItem[]
}

export interface DepartmentManagementSummary {
  id: string
  code: string
  name: string
  hod_user_id: string | null
  hod_name: string | null
  hod_email: string | null
  total_students: number
  total_faculty: number
  total_subjects: number
  attendance_percent: number
}

export interface DepartmentListResponse {
  items: DepartmentManagementSummary[]
}

export interface DepartmentCreateRequest {
  code: string
  name: string
}

export interface FacultyManagementSummary {
  faculty_id: string
  user_id: string
  full_name: string
  email: string
  employee_code: string
  designation: string
  department_id: string
  department_name: string
  assigned_subject_count: number
}

export interface FacultyListResponse {
  items: FacultyManagementSummary[]
}

export interface FacultyCreateRequest {
  full_name: string
  email: string
  password: string
  employee_code: string
  designation: string
  department_id?: string
}

export interface HodCreateRequest {
  full_name: string
  email: string
  password: string
  employee_code: string
  designation?: string
}

export interface ErrorEnvelope {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

// ------------------------------------------------------------------ //
//  Reports                                                             //
// ------------------------------------------------------------------ //

export interface DailyReportRow {
  date: string
  total_records: number
  unique_students: number
  present_count: number
  present_percent: number
}

export interface DailyReportResponse {
  items: DailyReportRow[]
  total_rows: number
}

export interface MonthlyReportRow {
  year: number
  month: number
  month_label: string
  total_records: number
  unique_students: number
  present_count: number
  present_percent: number
}

export interface MonthlyReportResponse {
  items: MonthlyReportRow[]
  total_rows: number
}

export interface SubjectReportRow {
  subject_id: string
  subject_name: string
  subject_code: string
  department_id: string
  department_name: string
  faculty_id: string
  faculty_name: string
  semester: number
  section: string
  total_records: number
  unique_students: number
  present_count: number
  absent_count: number
  late_count: number
  attendance_percent: number
}

export interface SubjectReportResponse {
  items: SubjectReportRow[]
  total_rows: number
}

export interface StudentReportRow {
  student_id: string
  full_name: string
  roll_number: string
  subject_id: string
  subject_name: string
  subject_code: string
  semester: number
  section: string
  total_sessions: number
  present_count: number
  absent_count: number
  late_count: number
  attendance_percent: number
}

export interface StudentReportResponse {
  items: StudentReportRow[]
  total_rows: number
}

export interface DepartmentReportRow {
  department_id: string
  department_name: string
  department_code: string
  total_students: number
  total_faculty: number
  total_subjects: number
  total_sessions: number
  present_count: number
  attendance_percent: number
}

export interface DepartmentReportResponse {
  items: DepartmentReportRow[]
  total_rows: number
}
