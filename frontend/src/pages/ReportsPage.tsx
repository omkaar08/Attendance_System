import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Download, Loader2, FileText } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import {
  attendanceApi,
  facultyApi,
  getErrorMessage,
  managementApi,
  reportsApi,
} from '../lib/api'
import type { AttendanceReportItem, SubjectReportRow } from '../lib/types'
import { useAuth } from '../providers/AuthProvider'
import { downloadCsv, downloadExcel, downloadPdf, downloadSubjectCsv, downloadSubjectExcel, downloadSubjectPdf } from '../lib/reportExport'

const getIso = (d: Date) => d.toISOString().slice(0, 10)

// Deduplicate attendance records - keep highest confidence for same student/subject/date
const deduplicateRecords = (records: AttendanceReportItem[]): AttendanceReportItem[] => {
  const dedupMap = new Map<string, AttendanceReportItem>()
  
  records.forEach((record) => {
    const key = `${record.student_id}-${record.subject_id}-${record.class_date}`
    const existing = dedupMap.get(key)
    
    // Keep record with highest confidence score
    if (!existing || record.confidence_score > existing.confidence_score) {
      dedupMap.set(key, record)
    }
  })
  
  return Array.from(dedupMap.values())
}

export const ReportsPage = () => {
  const { role } = useAuth()
  const isAdmin = role === 'admin'
  const isHod = role === 'hod'
  const isFaculty = role === 'faculty'

  const today = new Date()
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)

  const [fromDate, setFromDate] = useState(getIso(firstOfMonth))
  const [toDate, setToDate] = useState(getIso(today))
  const [departmentId, setDepartmentId] = useState('')
  const [subjectId, setSubjectId] = useState('')

  const [reportData, setReportData] = useState<AttendanceReportItem[] | null>(null)
  const [subjectReportData, setSubjectReportData] = useState<SubjectReportRow[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch subjects - all roles can see subjects
  const subjectsQuery = useQuery({
    queryKey: ['subjects-report', role],
    queryFn: async () => {
      if (isFaculty || isHod) {
        return facultyApi.subjects()
      }
      return { items: [] }
    },
  })
  const subjects = subjectsQuery.data?.items ?? []

  // Fetch departments for admin
  const departmentsQuery = useQuery({
    queryKey: ['departments-report'],
    queryFn: managementApi.listDepartments,
    enabled: isAdmin,
  })
  const departments = departmentsQuery.data?.items ?? []

  // Clear subject when department changes (for admin)
  const handleDepartmentChange = (newDeptId: string) => {
    setDepartmentId(newDeptId)
    setSubjectId('')
  }

  // Generate report
  const handleGenerate = async () => {
    setIsLoading(true)
    setError(null)
    setReportData(null)
    setSubjectReportData(null)
    
    try {
      const params = {
        from_date: fromDate,
        to_date: toDate,
        subject_id: subjectId || undefined,
        department_id: isAdmin ? (departmentId || undefined) : undefined,
      }
      
      // For admin with department but no specific subject: show subject summary
      if (isAdmin && departmentId && !subjectId) {
        const resp = await reportsApi.subject(params)
        setSubjectReportData(resp.items)
      } else {
        // Show individual attendance records
        const resp = await attendanceApi.report(params)
        const dedupedData = deduplicateRecords(resp.items)
        setReportData(dedupedData)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsLoading(false)
    }
  }

  // Download report
  const handleDownload = async (format: 'csv' | 'xlsx' | 'pdf') => {
    const stamp = `${fromDate}_to_${toDate}`
    
    if (subjectReportData) {
      try {
        if (format === 'csv') downloadSubjectCsv(subjectReportData, `subject_attendance_${stamp}.csv`)
        if (format === 'xlsx') await downloadSubjectExcel(subjectReportData, `subject_attendance_${stamp}.xlsx`)
        if (format === 'pdf') await downloadSubjectPdf(subjectReportData, `subject_attendance_${stamp}.pdf`)
      } catch (err) {
        setError(getErrorMessage(err))
      }
    } else if (reportData) {
      try {
        if (format === 'csv') downloadCsv(reportData, `attendance_${stamp}.csv`)
        if (format === 'xlsx') await downloadExcel(reportData, `attendance_${stamp}.xlsx`)
        if (format === 'pdf') await downloadPdf(reportData, `attendance_${stamp}.pdf`)
      } catch (err) {
        setError(getErrorMessage(err))
      }
    }
  }

  const hasData = reportData && reportData.length > 0
  const hasSubjectData = subjectReportData && subjectReportData.length > 0
  const maxRows = 100

  return (
    <section>
      <PageHeader
        eyebrow="Reporting"
        title="Attendance Reports"
        description="Generate and download attendance reports based on your role and filters."
      />

      {/* Filters Panel */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel mb-6 rounded-2xl p-6 shadow-soft"
      >
        <h3 className="mb-4 font-display text-sm font-semibold uppercase tracking-[0.12em] text-slate-700">
          Report Filters
        </h3>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Date Range */}
          <label className="flex flex-col gap-1.5">
            <span className="text-xs uppercase tracking-[0.12em] text-slate-600">From Date</span>
            <input
              type="date"
              value={fromDate}
              max={toDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs uppercase tracking-[0.12em] text-slate-600">To Date</span>
            <input
              type="date"
              value={toDate}
              min={fromDate}
              onChange={(e) => setToDate(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </label>

          {/* Department selector - Admin only */}
          {isAdmin && (
            <label className="flex flex-col gap-1.5">
              <span className="text-xs uppercase tracking-[0.12em] text-slate-600">Department</span>
              <select
                value={departmentId}
                onChange={(e) => handleDepartmentChange(e.target.value)}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                <option value="">All Departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} · {d.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {/* Subject selector - all roles */}
          {subjects.length > 0 && (
            <label className="flex flex-col gap-1.5">
              <span className="text-xs uppercase tracking-[0.12em] text-slate-600">Subject</span>
              <select
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-medium text-slate-900 outline-none transition focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              >
                <option value="">All Subjects</option>
                {subjects.map((s: { id: string; code: string; name: string }) => (
                  <option key={s.id} value={s.id}>
                    {s.code} · {s.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {/* Generate Button */}
        <div className="mt-5 flex justify-start">
          <button
            onClick={handleGenerate}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-xl bg-brand-900 px-6 py-2.5 text-sm font-semibold text-white shadow-md transition-all hover:bg-brand-950 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Generating…
              </>
            ) : (
              <>
                <FileText size={16} />
                Generate Report
              </>
            )}
          </button>
        </div>
      </motion.div>

      {/* Error Message */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 text-sm font-medium text-red-800 backdrop-blur"
        >
          {error}
        </motion.div>
      )}

      {/* Report Content */}
      {hasSubjectData ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel overflow-hidden rounded-2xl shadow-soft"
        >
          {/* Header with Download Options */}
          <div className="border-b border-slate-200 bg-gradient-to-br from-slate-50 to-white px-6 py-4">
            <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h3 className="font-display text-lg font-semibold text-brand-900">
                  Department Subject Report
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Average attendance per subject from {fromDate} to {toDate}
                </p>
              </div>

              {/* Download Buttons */}
              <div className="flex flex-wrap gap-2">
                {(['csv', 'xlsx', 'pdf'] as const).map((format) => (
                  <button
                    key={format}
                    onClick={() => void handleDownload(format)}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 shadow-sm transition-all hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                  >
                    <Download size={13} />
                    {format.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50">
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Subject Code
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Subject Name
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Faculty
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Semester
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Section
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Sessions
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Attendance %
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {subjectReportData.map((row) => (
                  <tr key={row.subject_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-3 font-semibold text-slate-900">{row.subject_code}</td>
                    <td className="px-6 py-3 font-medium text-slate-900">{row.subject_name}</td>
                    <td className="px-6 py-3 text-slate-600">{row.faculty_name}</td>
                    <td className="px-6 py-3 text-slate-600">Sem {row.semester}</td>
                    <td className="px-6 py-3 text-slate-600">{row.section}</td>
                    <td className="px-6 py-3 text-slate-600">{row.total_records}</td>
                    <td className="px-6 py-3">
                      <span className="inline-flex rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800">
                        {row.attendance_percent.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      ) : hasData ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel overflow-hidden rounded-2xl shadow-soft"
        >
          {/* Header with Download Options */}
          <div className="border-b border-slate-200 bg-gradient-to-br from-slate-50 to-white px-6 py-4">
            <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h3 className="font-display text-lg font-semibold text-brand-900">
                  Report Results
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Showing {Math.min(maxRows, reportData.length)} of {reportData.length} records
                </p>
              </div>

              {/* Download Buttons */}
              <div className="flex flex-wrap gap-2">
                {(['csv', 'xlsx', 'pdf'] as const).map((format) => (
                  <button
                    key={format}
                    onClick={() => void handleDownload(format)}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 shadow-sm transition-all hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                  >
                    <Download size={13} />
                    {format.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50">
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Date
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Session
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Subject
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Roll
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Student
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Status
                  </th>
                  <th className="px-6 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                    Conf %
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {reportData.slice(0, maxRows).map((row, idx) => (
                  <tr
                    key={row.id || idx}
                    className="hover:bg-slate-50/50 transition-colors"
                  >
                    <td className="px-6 py-3 font-medium text-slate-900">
                      {row.class_date}
                    </td>
                    <td className="px-6 py-3 text-slate-600">
                      {row.session_label}
                    </td>
                    <td className="px-6 py-3 font-semibold text-brand-900">
                      {row.subject_name}
                    </td>
                    <td className="px-6 py-3 text-slate-600">
                      {row.roll_number}
                    </td>
                    <td className="px-6 py-3 font-medium text-slate-900">
                      {row.student_name}
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                          row.status === 'present'
                            ? 'bg-emerald-100 text-emerald-800'
                            : row.status === 'late'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-slate-600">
                      {Math.round(row.confidence_score * 100)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Info */}
          {reportData.length > maxRows && (
            <div className="border-t border-slate-200 bg-slate-50/50 px-6 py-3 text-xs text-slate-500">
              Showing {maxRows} of {reportData.length} records. Download the report to see all data.
            </div>
          )}
        </motion.div>
      ) : isLoading ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/50 py-20"
        >
          <Loader2 size={40} className="mb-3 animate-spin text-brand-600" />
          <p className="text-sm font-medium text-slate-600">Generating your report…</p>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-white/50 py-20"
        >
          <FileText size={40} className="mb-3 text-slate-300" />
          <p className="text-sm font-semibold text-slate-600">No report generated yet</p>
          <p className="mt-1 text-xs text-slate-500">
            Set filters and click "Generate Report" to view attendance data.
          </p>
        </motion.div>
      )}
    </section>
  )
}
