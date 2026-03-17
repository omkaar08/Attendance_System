import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BarChart2,
  Building2,
  Calendar,
  CalendarDays,
  Download,
  FileText,
  GraduationCap,
  Loader2,
} from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import {
  attendanceApi,
  facultyApi,
  getErrorMessage,
  managementApi,
  reportsApi,
} from '../lib/api'
import type {
  AttendanceReportItem,
  DailyReportRow,
  DepartmentReportRow,
  MonthlyReportRow,
  StudentReportRow,
  SubjectReportRow,
} from '../lib/types'
import { useAuth } from '../providers/AuthProvider'

type ReportTab = 'raw' | 'daily' | 'monthly' | 'subject' | 'student' | 'department'

const tabs: Array<{ id: ReportTab; label: string; icon: typeof FileText; roles: string[] }> = [
  { id: 'raw', label: 'Raw Attendance', icon: FileText, roles: ['faculty', 'hod', 'admin'] },
  { id: 'daily', label: 'Daily Summary', icon: CalendarDays, roles: ['faculty', 'hod', 'admin'] },
  { id: 'monthly', label: 'Monthly Summary', icon: Calendar, roles: ['faculty', 'hod', 'admin'] },
  { id: 'subject', label: 'Subject Summary', icon: BarChart2, roles: ['faculty', 'hod', 'admin'] },
  { id: 'student', label: 'Student Performance', icon: GraduationCap, roles: ['faculty', 'hod', 'admin'] },
  { id: 'department', label: 'Department Overview', icon: Building2, roles: ['hod', 'admin'] },
]

const getIso = (d: Date) => d.toISOString().slice(0, 10)

export const ReportsPage = () => {
  const { role } = useAuth()
  const isAdmin = role === 'admin'

  const today = new Date()
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)

  const [activeTab, setActiveTab] = useState<ReportTab>('raw')
  const [fromDate, setFromDate] = useState(getIso(firstOfMonth))
  const [toDate, setToDate] = useState(getIso(today))
  const [subjectId, setSubjectId] = useState('')
  const [departmentId, setDepartmentId] = useState('')

  const [rawData, setRawData] = useState<AttendanceReportItem[] | null>(null)
  const [dailyData, setDailyData] = useState<DailyReportRow[] | null>(null)
  const [monthlyData, setMonthlyData] = useState<MonthlyReportRow[] | null>(null)
  const [subjectData, setSubjectData] = useState<SubjectReportRow[] | null>(null)
  const [studentData, setStudentData] = useState<StudentReportRow[] | null>(null)
  const [departmentData, setDepartmentData] = useState<DepartmentReportRow[] | null>(null)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const subjectsQuery = useQuery({
    queryKey: ['subjects-report', role],
    queryFn: facultyApi.subjects,
  })
  const subjects = subjectsQuery.data?.items ?? []

  const departmentsQuery = useQuery({
    queryKey: ['departments-report'],
    queryFn: managementApi.listDepartments,
    enabled: isAdmin,
  })
  const departments = departmentsQuery.data?.items ?? []

  const visibleTabs = tabs.filter((t) => t.roles.includes(role ?? 'faculty'))

  // ------------------------------------------------------------------ //
  // Generate                                                             //
  // ------------------------------------------------------------------ //

  const handleGenerate = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const base = {
        from_date: fromDate,
        to_date: toDate,
        subject_id: subjectId || undefined,
        department_id: departmentId || undefined,
      }
      switch (activeTab) {
        case 'raw': {
          const resp = await attendanceApi.report(base)
          setRawData(resp.items)
          break
        }
        case 'daily': {
          const resp = await reportsApi.daily(base)
          setDailyData(resp.items)
          break
        }
        case 'monthly': {
          const resp = await reportsApi.monthly(base)
          setMonthlyData(resp.items)
          break
        }
        case 'subject': {
          const resp = await reportsApi.subject(base)
          setSubjectData(resp.items)
          break
        }
        case 'student': {
          const resp = await reportsApi.student(base)
          setStudentData(resp.items)
          break
        }
        case 'department': {
          const resp = await reportsApi.department({
            from_date: fromDate,
            to_date: toDate,
            department_id: departmentId || undefined,
          })
          setDepartmentData(resp.items)
          break
        }
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  // ------------------------------------------------------------------ //
  // Download                                                             //
  // ------------------------------------------------------------------ //

  const handleDownload = async (kind: 'csv' | 'xlsx' | 'pdf') => {
    const stamp = `${fromDate}_to_${toDate}`
    try {
      const exporters = await import('../lib/reportExport')

      if (activeTab === 'raw' && rawData) {
        if (kind === 'csv') exporters.downloadCsv(rawData, `attendance_${stamp}.csv`)
        if (kind === 'xlsx') await exporters.downloadExcel(rawData, `attendance_${stamp}.xlsx`)
        if (kind === 'pdf') await exporters.downloadPdf(rawData, `attendance_${stamp}.pdf`)
      } else if (activeTab === 'daily' && dailyData) {
        if (kind === 'csv') exporters.downloadDailyCsv(dailyData, `daily_${stamp}.csv`)
        if (kind === 'xlsx') await exporters.downloadDailyExcel(dailyData, `daily_${stamp}.xlsx`)
        if (kind === 'pdf') await exporters.downloadDailyPdf(dailyData, `daily_${stamp}.pdf`)
      } else if (activeTab === 'monthly' && monthlyData) {
        if (kind === 'csv') exporters.downloadMonthlyCsv(monthlyData, `monthly_${stamp}.csv`)
        if (kind === 'xlsx') await exporters.downloadMonthlyExcel(monthlyData, `monthly_${stamp}.xlsx`)
        if (kind === 'pdf') await exporters.downloadMonthlyPdf(monthlyData, `monthly_${stamp}.pdf`)
      } else if (activeTab === 'subject' && subjectData) {
        if (kind === 'csv') exporters.downloadSubjectCsv(subjectData, `subject_${stamp}.csv`)
        if (kind === 'xlsx') await exporters.downloadSubjectExcel(subjectData, `subject_${stamp}.xlsx`)
        if (kind === 'pdf') await exporters.downloadSubjectPdf(subjectData, `subject_${stamp}.pdf`)
      } else if (activeTab === 'student' && studentData) {
        if (kind === 'csv') exporters.downloadStudentCsv(studentData, `student_${stamp}.csv`)
        if (kind === 'xlsx') await exporters.downloadStudentExcel(studentData, `student_${stamp}.xlsx`)
        if (kind === 'pdf') await exporters.downloadStudentPdf(studentData, `student_${stamp}.pdf`)
      } else if (activeTab === 'department' && departmentData) {
        if (kind === 'csv') exporters.downloadDepartmentCsv(departmentData, `department_${stamp}.csv`)
        if (kind === 'xlsx') await exporters.downloadDepartmentExcel(departmentData, `department_${stamp}.xlsx`)
        if (kind === 'pdf') await exporters.downloadDepartmentPdf(departmentData, `department_${stamp}.pdf`)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const hasData =
    (activeTab === 'raw' && rawData && rawData.length > 0) ||
    (activeTab === 'daily' && dailyData && dailyData.length > 0) ||
    (activeTab === 'monthly' && monthlyData && monthlyData.length > 0) ||
    (activeTab === 'subject' && subjectData && subjectData.length > 0) ||
    (activeTab === 'student' && studentData && studentData.length > 0) ||
    (activeTab === 'department' && departmentData && departmentData.length > 0)

  // ------------------------------------------------------------------ //
  // Table renderers                                                      //
  // ------------------------------------------------------------------ //

  const renderRawTable = () => {
    if (!rawData) return null
    if (!rawData.length) return <p className="text-sm text-slate-500">No records found for this date range.</p>
    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="pb-2 pr-4">Date</th>
              <th className="pb-2 pr-4">Session</th>
              <th className="pb-2 pr-4">Subject</th>
              <th className="pb-2 pr-4">Roll</th>
              <th className="pb-2 pr-4">Student</th>
              <th className="pb-2 pr-4">Status</th>
              <th className="pb-2">Conf %</th>
            </tr>
          </thead>
          <tbody>
            {rawData.slice(0, 100).map((row) => (
              <tr key={row.id} className="border-b border-slate-100">
                <td className="py-2 pr-4 text-slate-700">{row.class_date}</td>
                <td className="py-2 pr-4 text-slate-600">{row.session_label}</td>
                <td className="py-2 pr-4 font-medium text-brand-900">{row.subject_name}</td>
                <td className="py-2 pr-4 text-slate-600">{row.roll_number}</td>
                <td className="py-2 pr-4 text-slate-700">{row.student_name}</td>
                <td className="py-2 pr-4">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    row.status === 'present' ? 'bg-teal-100 text-teal-800' :
                    row.status === 'late' ? 'bg-amber-100 text-amber-800' :
                    'bg-red-100 text-red-800'
                  }`}>{row.status}</span>
                </td>
                <td className="py-2 text-slate-600">{Math.round(row.confidence_score * 100)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rawData.length > 100 && (
          <p className="mt-2 text-xs text-slate-400">Showing 100 of {rawData.length} rows. Download for full data.</p>
        )}
      </div>
    )
  }

  const renderDailyTable = () => {
    if (!dailyData) return null
    if (!dailyData.length) return <p className="text-sm text-slate-500">No records found for this date range.</p>
    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="pb-2 pr-4">Date</th>
              <th className="pb-2 pr-4">Total Records</th>
              <th className="pb-2 pr-4">Unique Students</th>
              <th className="pb-2 pr-4">Present</th>
              <th className="pb-2">Present %</th>
            </tr>
          </thead>
          <tbody>
            {dailyData.map((row) => (
              <tr key={row.date} className="border-b border-slate-100">
                <td className="py-2 pr-4 font-medium text-brand-900">{row.date}</td>
                <td className="py-2 pr-4 text-slate-700">{row.total_records}</td>
                <td className="py-2 pr-4 text-slate-700">{row.unique_students}</td>
                <td className="py-2 pr-4 text-slate-700">{row.present_count}</td>
                <td className="py-2">
                  <span className={`font-semibold ${row.present_percent >= 75 ? 'text-teal-700' : row.present_percent >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                    {row.present_percent}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const renderMonthlyTable = () => {
    if (!monthlyData) return null
    if (!monthlyData.length) return <p className="text-sm text-slate-500">No records found for this date range.</p>
    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="pb-2 pr-4">Month</th>
              <th className="pb-2 pr-4">Total Records</th>
              <th className="pb-2 pr-4">Unique Students</th>
              <th className="pb-2 pr-4">Present</th>
              <th className="pb-2">Present %</th>
            </tr>
          </thead>
          <tbody>
            {monthlyData.map((row) => (
              <tr key={`${row.year}-${row.month}`} className="border-b border-slate-100">
                <td className="py-2 pr-4 font-medium text-brand-900">{row.month_label}</td>
                <td className="py-2 pr-4 text-slate-700">{row.total_records}</td>
                <td className="py-2 pr-4 text-slate-700">{row.unique_students}</td>
                <td className="py-2 pr-4 text-slate-700">{row.present_count}</td>
                <td className="py-2">
                  <span className={`font-semibold ${row.present_percent >= 75 ? 'text-teal-700' : row.present_percent >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                    {row.present_percent}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const renderSubjectTable = () => {
    if (!subjectData) return null
    if (!subjectData.length) return <p className="text-sm text-slate-500">No records found for this date range.</p>
    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1000px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="pb-2 pr-4">Subject</th>
              <th className="pb-2 pr-4">Faculty</th>
              <th className="pb-2 pr-4">Department</th>
              <th className="pb-2 pr-4">Sem / Sec</th>
              <th className="pb-2 pr-4">Records</th>
              <th className="pb-2 pr-4">Students</th>
              <th className="pb-2 pr-4">Present</th>
              <th className="pb-2 pr-4">Absent</th>
              <th className="pb-2 pr-4">Late</th>
              <th className="pb-2">%</th>
            </tr>
          </thead>
          <tbody>
            {subjectData.map((row) => (
              <tr key={row.subject_id} className="border-b border-slate-100">
                <td className="py-2 pr-4">
                  <p className="font-medium text-brand-900">{row.subject_name}</p>
                  <p className="text-xs text-slate-500">{row.subject_code}</p>
                </td>
                <td className="py-2 pr-4 text-slate-700">{row.faculty_name}</td>
                <td className="py-2 pr-4 text-slate-700">{row.department_name}</td>
                <td className="py-2 pr-4 text-slate-500">S{row.semester}/{row.section}</td>
                <td className="py-2 pr-4 text-slate-700">{row.total_records}</td>
                <td className="py-2 pr-4 text-slate-700">{row.unique_students}</td>
                <td className="py-2 pr-4 text-teal-700">{row.present_count}</td>
                <td className="py-2 pr-4 text-red-600">{row.absent_count}</td>
                <td className="py-2 pr-4 text-amber-700">{row.late_count}</td>
                <td className="py-2">
                  <span className={`font-semibold ${row.attendance_percent >= 75 ? 'text-teal-700' : row.attendance_percent >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                    {row.attendance_percent}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const renderStudentTable = () => {
    if (!studentData) return null
    if (!studentData.length) return <p className="text-sm text-slate-500">No records found for this date range.</p>
    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="pb-2 pr-4">Roll</th>
              <th className="pb-2 pr-4">Student</th>
              <th className="pb-2 pr-4">Subject</th>
              <th className="pb-2 pr-4">Sem / Sec</th>
              <th className="pb-2 pr-4">Total</th>
              <th className="pb-2 pr-4">Present</th>
              <th className="pb-2 pr-4">Absent</th>
              <th className="pb-2">%</th>
            </tr>
          </thead>
          <tbody>
            {studentData.slice(0, 100).map((row, i) => (
              <tr key={`${row.student_id}-${row.subject_id}-${i}`} className="border-b border-slate-100">
                <td className="py-2 pr-4 text-slate-500">{row.roll_number}</td>
                <td className="py-2 pr-4 font-medium text-brand-900">{row.full_name}</td>
                <td className="py-2 pr-4 text-slate-700">{row.subject_name}</td>
                <td className="py-2 pr-4 text-slate-500">S{row.semester}/{row.section}</td>
                <td className="py-2 pr-4 text-slate-700">{row.total_sessions}</td>
                <td className="py-2 pr-4 text-teal-700">{row.present_count}</td>
                <td className="py-2 pr-4 text-red-600">{row.absent_count}</td>
                <td className="py-2">
                  <span className={`font-semibold ${row.attendance_percent >= 75 ? 'text-teal-700' : row.attendance_percent >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                    {row.attendance_percent}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {studentData.length > 100 && (
          <p className="mt-2 text-xs text-slate-400">Showing 100 of {studentData.length} rows. Download for full data.</p>
        )}
      </div>
    )
  }

  const renderDepartmentTable = () => {
    if (!departmentData) return null
    if (!departmentData.length) return <p className="text-sm text-slate-500">No department data found for this period.</p>
    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[800px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="pb-2 pr-4">Department</th>
              <th className="pb-2 pr-4">Students</th>
              <th className="pb-2 pr-4">Faculty</th>
              <th className="pb-2 pr-4">Subjects</th>
              <th className="pb-2 pr-4">Sessions</th>
              <th className="pb-2 pr-4">Present</th>
              <th className="pb-2">Attend %</th>
            </tr>
          </thead>
          <tbody>
            {departmentData.map((row) => (
              <tr key={row.department_id} className="border-b border-slate-100">
                <td className="py-2 pr-4">
                  <p className="font-semibold text-brand-900">{row.department_name}</p>
                  <p className="text-xs text-slate-500">{row.department_code}</p>
                </td>
                <td className="py-2 pr-4 text-slate-700">{row.total_students}</td>
                <td className="py-2 pr-4 text-slate-700">{row.total_faculty}</td>
                <td className="py-2 pr-4 text-slate-700">{row.total_subjects}</td>
                <td className="py-2 pr-4 text-slate-700">{row.total_sessions}</td>
                <td className="py-2 pr-4 text-teal-700">{row.present_count}</td>
                <td className="py-2">
                  <span className={`font-semibold ${row.attendance_percent >= 75 ? 'text-teal-700' : row.attendance_percent >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                    {row.attendance_percent}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const renderTable = () => {
    switch (activeTab) {
      case 'raw': return renderRawTable()
      case 'daily': return renderDailyTable()
      case 'monthly': return renderMonthlyTable()
      case 'subject': return renderSubjectTable()
      case 'student': return renderStudentTable()
      case 'department': return renderDepartmentTable()
    }
  }

  const changeTab = (tab: ReportTab) => {
    setActiveTab(tab)
    setError(null)
  }

  return (
    <section>
      <PageHeader
        eyebrow="Reporting"
        title="Reports"
        description="Generate and download daily, monthly, subject, student, and department attendance reports."
      />

      {/* Tab bar */}
      <div className="mb-6 flex flex-wrap gap-2 border-b border-slate-200 pb-1">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => changeTab(tab.id)}
              className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-brand-900 text-white shadow-sm'
                  : 'bg-white text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel mb-6 rounded-2xl p-5 shadow-soft"
      >
        <div className="flex flex-wrap gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-[0.14em] text-slate-500">From date</span>
            <input
              type="date"
              value={fromDate}
              max={toDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-[0.14em] text-slate-500">To date</span>
            <input
              type="date"
              value={toDate}
              min={fromDate}
              onChange={(e) => setToDate(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
            />
          </label>

          {activeTab !== 'department' && subjects.length > 0 && (
            <label className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-[0.14em] text-slate-500">Subject</span>
              <select
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
              >
                <option value="">All subjects</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.code} · {s.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {isAdmin && departments.length > 0 && (
            <label className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-[0.14em] text-slate-500">Department</span>
              <select
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-600"
              >
                <option value="">All departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} · {d.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          <div className="flex items-end">
            <button
              onClick={handleGenerate}
              disabled={isLoading}
              className="flex items-center gap-2 rounded-xl bg-brand-900 px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {isLoading ? <Loader2 size={14} className="animate-spin" /> : <BarChart2 size={14} />}
              {isLoading ? 'Generating…' : 'Generate Report'}
            </button>
          </div>
        </div>
      </motion.div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Preview table */}
      {hasData && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel mb-4 overflow-hidden rounded-2xl p-5 shadow-soft"
        >
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold text-brand-900">Preview</h3>

            {/* Download bar */}
            <div className="flex gap-2">
              {(['csv', 'xlsx', 'pdf'] as const).map((kind) => (
                <button
                  key={kind}
                  onClick={() => void handleDownload(kind)}
                  className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
                >
                  <Download size={12} />
                  {kind.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {renderTable()}
        </motion.div>
      )}

      {/* Empty state */}
      {!hasData && !isLoading && !error && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/50 py-16 text-center">
          <FileText size={36} className="mb-3 text-slate-300" />
          <p className="text-sm font-medium text-slate-600">No report generated yet</p>
          <p className="mt-1 text-xs text-slate-400">
            Select filters above and click Generate Report.
          </p>
        </div>
      )}
    </section>
  )
}
