import axios, { AxiosError } from 'axios'
import type {
  AnalyticsOverviewResponse,
  AttendanceReportResponse,
  CurrentUserResponse,
  DailyReportResponse,
  DepartmentCreateRequest,
  DepartmentListResponse,
  DepartmentReportResponse,
  EmbeddingListResponse,
  EnrollRequest,
  EnrollResponse,
  ErrorEnvelope,
  FacultyCreateRequest,
  FacultyListResponse,
  FaceUploadRequest,
  FaceUploadResponse,
  HodCreateRequest,
  LowAttendanceAlertResponse,
  IdentifyRequest,
  IdentifyResponse,
  LoginRequest,
  LoginResponse,
  MonthlyReportResponse,
  StudentListResponse,
  SubjectReportResponse,
  StudentRegisterRequest,
  StudentReportResponse,
  StudentSummary,
  SubjectCreateRequest,
  SubjectListResponse,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/v1'

let authToken: string | null = null

export const setAuthToken = (token: string | null): void => {
  authToken = token
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`
  }
  return config
})

export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const body = (error as AxiosError<ErrorEnvelope>).response?.data
    if (body?.error?.message) {
      return body.error.message
    }
    if (!error.response) {
      return 'Cannot reach the backend API. Start FastAPI on http://127.0.0.1:8000 and try again.'
    }
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Unknown error occurred.'
}

export const authApi = {
  login: async (payload: LoginRequest): Promise<LoginResponse> => {
    const { data } = await api.post<LoginResponse>('/auth/login', payload)
    return data
  },
  me: async (): Promise<CurrentUserResponse> => {
    const { data } = await api.get<CurrentUserResponse>('/auth/me')
    return data
  },
}

export const facultyApi = {
  subjects: async (): Promise<SubjectListResponse> => {
    const { data } = await api.get<SubjectListResponse>('/faculty/subjects')
    return data
  },
}

export const subjectsApi = {
  create: async (payload: SubjectCreateRequest) => {
    const { data } = await api.post('/subjects', payload)
    return data
  },

  assignFaculty: async (subjectId: string, facultyId: string): Promise<void> => {
    await api.post(`/subjects/${subjectId}/assign-faculty`, { faculty_id: facultyId })
  },
}

export const studentsApi = {
  list: async (params?: {
    subject_id?: string
    search?: string
    semester?: number
    section?: string
    limit?: number
  }): Promise<StudentListResponse> => {
    const { data } = await api.get<StudentListResponse>('/students', { params })
    return data
  },

  register: async (payload: StudentRegisterRequest): Promise<StudentSummary> => {
    const { data } = await api.post<StudentSummary>('/students/register', payload)
    return data
  },

  createFaceUploadUrl: async (payload: FaceUploadRequest): Promise<FaceUploadResponse> => {
    const { data } = await api.post<FaceUploadResponse>('/students/upload-face', payload)
    return data
  },

  uploadToSignedUrl: async (signedUrl: string, file: Blob): Promise<void> => {
    const response = await fetch(signedUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
      },
      body: file,
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Image upload failed: ${response.status} ${text}`)
    }
  },
}

export const recognitionApi = {
  enroll: async (payload: EnrollRequest): Promise<EnrollResponse> => {
    const { data } = await api.post<EnrollResponse>('/recognition/enroll', payload)
    return data
  },

  identify: async (payload: IdentifyRequest): Promise<IdentifyResponse> => {
    const { data } = await api.post<IdentifyResponse>('/recognition/identify', payload)
    return data
  },

  listEmbeddings: async (studentId: string): Promise<EmbeddingListResponse> => {
    const { data } = await api.get<EmbeddingListResponse>(`/recognition/students/${studentId}/embeddings`)
    return data
  },

  deleteEmbedding: async (embeddingId: string): Promise<void> => {
    await api.delete(`/recognition/embeddings/${embeddingId}`)
  },
}

export const analyticsApi = {
  overview: async (params?: { department_id?: string; subject_id?: string }): Promise<AnalyticsOverviewResponse> => {
    const { data } = await api.get<AnalyticsOverviewResponse>('/analytics/overview', { params })
    return data
  },

  subjectAttendance: async (params?: { department_id?: string }) => {
    const { data } = await api.get('/analytics/subject-attendance', { params })
    return data
  },
}

export const attendanceApi = {
  report: async (params: {
    from_date: string
    to_date: string
    subject_id?: string
    section?: string
  }): Promise<AttendanceReportResponse> => {
    const { data } = await api.get<AttendanceReportResponse>('/attendance/report', { params })
    return data
  },

  markManual: async (payload: {
    subject_id: string
    student_id: string
    class_date: string
    status: 'present' | 'absent' | 'late'
    session_label?: string
  }) => {
    const { data } = await api.post('/attendance/mark-manual', payload)
    return data
  },

  lowAttendanceAlerts: async (params: {
    from_date: string
    to_date: string
    threshold_percent?: number
    min_sessions?: number
    subject_id?: string
    department_id?: string
  }): Promise<LowAttendanceAlertResponse> => {
    const { data } = await api.get<LowAttendanceAlertResponse>('/attendance/alerts/low', { params })
    return data
  },
}

export const managementApi = {
  listDepartments: async (): Promise<DepartmentListResponse> => {
    const { data } = await api.get<DepartmentListResponse>('/management/departments')
    return data
  },

  createDepartment: async (payload: DepartmentCreateRequest) => {
    const { data } = await api.post('/management/departments', payload)
    return data
  },

  deleteDepartment: async (departmentId: string): Promise<void> => {
    await api.delete(`/management/departments/${departmentId}`)
  },

  createOrAssignHod: async (departmentId: string, payload: HodCreateRequest) => {
    const { data } = await api.post(`/management/departments/${departmentId}/hod`, payload)
    return data
  },

  listFaculty: async (params?: { department_id?: string }): Promise<FacultyListResponse> => {
    const { data } = await api.get<FacultyListResponse>('/management/faculty', { params })
    return data
  },

  createFaculty: async (payload: FacultyCreateRequest) => {
    const { data } = await api.post('/management/faculty', payload)
    return data
  },
}

export const reportsApi = {
  daily: async (params: {
    from_date: string
    to_date: string
    subject_id?: string
    department_id?: string
  }): Promise<DailyReportResponse> => {
    const { data } = await api.get<DailyReportResponse>('/reports/daily', { params })
    return data
  },

  monthly: async (params: {
    from_date: string
    to_date: string
    subject_id?: string
    department_id?: string
  }): Promise<MonthlyReportResponse> => {
    const { data } = await api.get<MonthlyReportResponse>('/reports/monthly', { params })
    return data
  },

  subject: async (params: {
    from_date: string
    to_date: string
    subject_id?: string
    department_id?: string
  }): Promise<SubjectReportResponse> => {
    const { data } = await api.get<SubjectReportResponse>('/reports/subject', { params })
    return data
  },

  student: async (params: {
    from_date: string
    to_date: string
    subject_id?: string
    student_id?: string
    department_id?: string
  }): Promise<StudentReportResponse> => {
    const { data } = await api.get<StudentReportResponse>('/reports/student', { params })
    return data
  },

  department: async (params: {
    from_date: string
    to_date: string
    department_id?: string
  }): Promise<DepartmentReportResponse> => {
    const { data } = await api.get<DepartmentReportResponse>('/reports/department', { params })
    return data
  },
}
