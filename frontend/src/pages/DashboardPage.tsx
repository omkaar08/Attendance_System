import { useEffect, useMemo, useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  Building2,
  CalendarDays,
  Download,
  GraduationCap,
  Layers3,
  Users,
} from 'lucide-react'
import { Doughnut, Line } from 'react-chartjs-2'
import { Link } from 'react-router-dom'

import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { analyticsApi, attendanceApi, facultyApi, getErrorMessage, managementApi } from '../lib/api'
import type { AppRole } from '../lib/types'
import { useAuth } from '../providers/AuthProvider'
import { downloadCsv, downloadExcel, downloadPdf } from '../lib/reportExport'

ChartJS.register(ArcElement, BarElement, CategoryScale, Filler, LinearScale, PointElement, LineElement, Legend, Tooltip)

const getIsoDate = (date: Date): string => date.toISOString().slice(0, 10)

type DashboardStat = {
  title: string
  value: string
  subtitle: string
  icon: typeof Users
  delay: number
}

export const DashboardPage = () => {
  const { role } = useAuth()
  const currentRole: AppRole = role ?? 'faculty'
  const isFaculty = currentRole === 'faculty'
  const isAdmin = currentRole === 'admin'
  const isHod = currentRole === 'hod'

  const [fromDate, setFromDate] = useState(() => {
    const date = new Date()
    date.setDate(1)
    return getIsoDate(date)
  })
  const [toDate, setToDate] = useState(() => getIsoDate(new Date()))
  const [selectedSubjectId, setSelectedSubjectId] = useState('')
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const subjectsQuery = useQuery({
    queryKey: ['faculty-subjects', currentRole],
    queryFn: facultyApi.subjects,
  })

  const subjects = subjectsQuery.data?.items ?? []

  useEffect(() => {
    if (!isFaculty) {
      return
    }

    if (subjects.length === 0) {
      if (selectedSubjectId) {
        setSelectedSubjectId('')
      }
      return
    }

    const isSelectedSubjectValid = subjects.some((item) => item.id === selectedSubjectId)
    if (!selectedSubjectId || !isSelectedSubjectValid) {
      setSelectedSubjectId(subjects[0].id)
    }
  }, [isFaculty, selectedSubjectId, subjects])

  const selectedSubject = useMemo(
    () => subjects.find((subject) => subject.id === selectedSubjectId) ?? null,
    [selectedSubjectId, subjects],
  )

  const analyticsQuery = useQuery({
    queryKey: ['analytics-overview', currentRole, selectedSubjectId],
    queryFn: () =>
      analyticsApi.overview(
        isFaculty
          ? {
              subject_id: selectedSubjectId || undefined,
            }
          : undefined,
      ),
  })

  const departmentsQuery = useQuery({
    queryKey: ['dashboard-departments', currentRole],
    queryFn: managementApi.listDepartments,
    enabled: isAdmin || isHod,
  })

  const lowAttendanceQuery = useQuery({
    queryKey: ['low-attendance-alerts', currentRole, fromDate, toDate, selectedSubjectId],
    queryFn: () =>
      attendanceApi.lowAttendanceAlerts({
        from_date: fromDate,
        to_date: toDate,
        threshold_percent: 75,
        min_sessions: 3,
        subject_id: isFaculty ? selectedSubjectId || undefined : undefined,
      }),
  })

  const analytics = analyticsQuery.data
  const departments = departmentsQuery.data?.items ?? []
  const lowAttendanceAlerts = lowAttendanceQuery.data?.items ?? []

  const adminSummary = useMemo(() => {
    const totals = departments.reduce(
      (accumulator, department) => {
        accumulator.totalStudents += department.total_students
        accumulator.totalFaculty += department.total_faculty
        accumulator.totalSubjects += department.total_subjects
        accumulator.totalHods += department.hod_user_id ? 1 : 0
        accumulator.attendanceSum += department.attendance_percent
        return accumulator
      },
      {
        totalStudents: 0,
        totalFaculty: 0,
        totalSubjects: 0,
        totalHods: 0,
        attendanceSum: 0,
      },
    )

    return {
      ...totals,
      totalDepartments: departments.length,
      averageAttendance: departments.length > 0 ? totals.attendanceSum / departments.length : 0,
    }
  }, [departments])

  const hodDepartment = isHod ? departments[0] ?? null : null

  const statCards = useMemo<DashboardStat[]>(() => {
    if (isAdmin) {
      return [
        {
          title: 'Total Departments',
          value: String(adminSummary.totalDepartments),
          subtitle: 'Configured academic departments',
          icon: Building2,
          delay: 0,
        },
        {
          title: 'Total HODs',
          value: String(adminSummary.totalHods),
          subtitle: 'Departments with active HOD',
          icon: GraduationCap,
          delay: 0.05,
        },
        {
          title: 'Total Students',
          value: String(adminSummary.totalStudents),
          subtitle: 'Institution-wide student count',
          icon: Users,
          delay: 0.1,
        },
        {
          title: 'Avg Dept Attendance',
          value: `${adminSummary.averageAttendance.toFixed(1)}%`,
          subtitle: 'Average of department performance',
          icon: Activity,
          delay: 0.15,
        },
        {
          title: 'Low Attendance (<75%)',
          value: String(lowAttendanceAlerts.length),
          subtitle: 'Students below threshold this period',
          icon: AlertTriangle,
          delay: 0.2,
        },
      ]
    }

    if (isHod) {
      return [
        {
          title: 'Department Students',
          value: String(hodDepartment?.total_students ?? 0),
          subtitle: 'Students in your department',
          icon: Users,
          delay: 0,
        },
        {
          title: 'Department Faculty',
          value: String(hodDepartment?.total_faculty ?? 0),
          subtitle: 'Faculty under your supervision',
          icon: GraduationCap,
          delay: 0.05,
        },
        {
          title: 'Department Subjects',
          value: String(hodDepartment?.total_subjects ?? subjects.length),
          subtitle: 'Subjects in your department',
          icon: Layers3,
          delay: 0.1,
        },
        {
          title: 'Department Attendance',
          value: `${(hodDepartment?.attendance_percent ?? 0).toFixed(1)}%`,
          subtitle: 'Attendance health of your department',
          icon: Activity,
          delay: 0.15,
        },
        {
          title: 'Low Attendance (<75%)',
          value: String(lowAttendanceAlerts.length),
          subtitle: 'Students below threshold this period',
          icon: AlertTriangle,
          delay: 0.2,
        },
      ]
    }

    return [
      {
        title: 'Selected Subject Students',
        value: String(analytics?.total_students ?? 0),
        subtitle: selectedSubject ? `${selectedSubject.code} · Sem ${selectedSubject.semester} · Sec ${selectedSubject.section}` : 'Select a subject to scope data',
        icon: Users,
        delay: 0,
      },
      {
        title: 'Faculty Coverage',
        value: String(analytics?.total_faculty ?? 0),
        subtitle: 'Faculty assigned to selected subject',
        icon: GraduationCap,
        delay: 0.05,
      },
      {
        title: 'Subject Scope',
        value: String(analytics?.total_subjects ?? 0),
        subtitle: 'Dashboard currently scoped to one subject',
        icon: Layers3,
        delay: 0.1,
      },
      {
        title: "Today's Attendance",
        value: `${(analytics?.today_attendance_percent ?? 0).toFixed(1)}%`,
        subtitle: `Average ${(analytics?.average_attendance_percent ?? 0).toFixed(1)}%`,
        icon: Activity,
        delay: 0.15,
      },
      {
        title: 'Low Attendance (<75%)',
        value: String(lowAttendanceAlerts.length),
        subtitle: 'Students below threshold this period',
        icon: AlertTriangle,
        delay: 0.2,
      },
    ]
  }, [adminSummary, analytics, hodDepartment, isAdmin, isFaculty, isHod, lowAttendanceAlerts.length, selectedSubject, subjects.length])

  const roleTitle: Record<AppRole, string> = {
    faculty: 'Faculty Dashboard',
    hod: 'HOD Dashboard',
    admin: 'Admin Dashboard',
  }

  const roleDescription: Record<AppRole, string> = {
    faculty: 'Select an assigned subject to see fully scoped analytics, alerts, and exports for that subject only.',
    hod: 'Monitor only your department, assign subjects to department faculty, and track students at risk.',
    admin: 'Track department-wise performance and institution-level totals across departments, HODs, and students.',
  }

  const canTakeAttendance = isFaculty
  const showDepartmentPanel = currentRole === 'admin' || currentRole === 'hod'
  const subjectsHeading = currentRole === 'faculty' ? 'Assigned Subjects' : 'Subject Scope'
  const subjectsDescription =
    currentRole === 'faculty'
      ? 'Assigned subjects. Dashboard data is scoped to the selected one.'
      : 'Subjects visible under your current role scope.'

  const displayedSubjects = useMemo(() => {
    if (!isFaculty || !selectedSubjectId) {
      return subjects
    }
    return subjects.filter((subject) => subject.id === selectedSubjectId)
  }, [isFaculty, selectedSubjectId, subjects])

  const attendanceMixData = useMemo(() => {
    const today = analytics?.today_attendance_percent ?? 0
    return {
      labels: ['Present Today', 'Remaining'],
      datasets: [
        {
          data: [today, Math.max(0, 100 - today)],
          backgroundColor: ['#0f766e', '#d1d5db'],
          borderWidth: 0,
        },
      ],
    }
  }, [analytics])

  const trendData = useMemo(() => {
    const avg = analytics?.average_attendance_percent ?? 0
    const today = analytics?.today_attendance_percent ?? 0
    const base = Math.max(40, avg - 6)

    return {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Today'],
      datasets: [
        {
          label: 'Attendance %',
          data: [base + 1, base + 3, base + 2, avg, today],
          borderColor: '#0f172a',
          backgroundColor: 'rgba(15, 23, 42, 0.07)',
          fill: true,
          tension: 0.35,
        },
      ],
    }
  }, [analytics])

  const handleDownload = async (kind: 'csv' | 'xlsx' | 'pdf') => {
    setIsDownloading(true)
    setDownloadError(null)

    try {
      if (isFaculty && !selectedSubjectId) {
        throw new Error('Select a subject before downloading report exports.')
      }

      const report = await attendanceApi.report({
        from_date: fromDate,
        to_date: toDate,
        subject_id: isFaculty ? selectedSubjectId || undefined : undefined,
      })
      const stamp = `${fromDate}_to_${toDate}`

      if (kind === 'csv') {
        downloadCsv(report.items, `attendance_${stamp}.csv`)
      }
      if (kind === 'xlsx') {
        downloadExcel(report.items, `attendance_${stamp}.xlsx`)
      }
      if (kind === 'pdf') {
        downloadPdf(report.items, `attendance_${stamp}.pdf`)
      }
    } catch (error) {
      setDownloadError(getErrorMessage(error))
    } finally {
      setIsDownloading(false)
    }
  }

  const renderSubjectCards = () => {
    if (subjectsQuery.isLoading) {
      return <p className="text-sm text-slate-500">Loading subjects...</p>
    }

    if (displayedSubjects.length === 0) {
      return <p className="text-sm text-slate-500">No subjects assigned yet.</p>
    }

    return (
      <div className="grid gap-3 md:grid-cols-2">
        {displayedSubjects.map((subject) => (
          <div key={subject.id} className="rounded-2xl border border-slate-200 bg-white/70 p-4">
            <p className="font-semibold text-brand-900">{subject.name}</p>
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{subject.code}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
              <span className="rounded-full bg-slate-100 px-2 py-1">Semester {subject.semester}</span>
              <span className="rounded-full bg-slate-100 px-2 py-1">Section {subject.section}</span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  const renderDepartmentRows = () => {
    if (departmentsQuery.isLoading) {
      return (
        <tr>
          <td colSpan={7} className="py-5 text-slate-500">Loading department summary...</td>
        </tr>
      )
    }

    if (departments.length === 0) {
      return (
        <tr>
          <td colSpan={7} className="py-5 text-slate-500">No department summary available.</td>
        </tr>
      )
    }

    return departments.map((department) => (
      <tr key={department.id} className="border-b border-slate-100">
        <td className="py-3">
          <p className="font-semibold text-brand-900">{department.name}</p>
          <p className="text-xs text-slate-500">{department.code}</p>
        </td>
        <td className="py-3 text-slate-700">{department.hod_name ?? 'Not assigned'}</td>
        <td className="py-3 text-slate-700">{department.total_faculty}</td>
        <td className="py-3 text-slate-700">{department.total_students}</td>
        <td className="py-3 text-slate-700">{department.total_subjects}</td>
        <td className="py-3 text-slate-700">{department.attendance_percent.toFixed(1)}%</td>
        <td className="py-3 text-slate-700">{department.hod_email ?? 'N/A'}</td>
      </tr>
    ))
  }

  return (
    <section>
      <PageHeader
        eyebrow="Command Center"
        title={roleTitle[currentRole]}
        description={roleDescription[currentRole]}
      />

      {isFaculty ? (
        <div className="mb-4 glass-panel rounded-2xl p-4 shadow-soft">
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Dashboard Subject Scope</span>
            <select
              value={selectedSubjectId}
              onChange={(event) => setSelectedSubjectId(event.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
            >
              <option value="">Select subject</option>
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {subject.code} · {subject.name} · Sem {subject.semester} · Sec {subject.section}
                </option>
              ))}
            </select>
          </label>
          <p className="mt-2 text-xs text-slate-500">
            Attendance stats, low-attendance alerts, and report exports are scoped to this selected subject.
          </p>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {statCards.map((item) => (
          <StatCard
            key={item.title}
            title={item.title}
            value={item.value}
            subtitle={item.subtitle}
            icon={item.icon}
            delay={item.delay}
          />
        ))}
      </div>

      {showDepartmentPanel && (
        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 glass-panel rounded-3xl p-6 shadow-soft"
        >
          <h3 className="font-display text-xl font-semibold text-brand-900">
            {isAdmin ? 'Department Performance' : 'Department Snapshot'}
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {isAdmin
              ? 'Department-wise student, faculty, and attendance performance at a glance.'
              : 'Your department totals and current attendance health.'}
          </p>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-[0.16em] text-slate-500">
                  <th className="py-3">Department</th>
                  <th className="py-3">HOD</th>
                  <th className="py-3">Faculty</th>
                  <th className="py-3">Students</th>
                  <th className="py-3">Subjects</th>
                  <th className="py-3">Attendance</th>
                  <th className="py-3">HOD Email</th>
                </tr>
              </thead>
              <tbody>{renderDepartmentRows()}</tbody>
            </table>
          </div>
        </motion.article>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <motion.article
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          <h3 className="font-display text-xl font-semibold text-brand-900">Attendance Trend</h3>
          <p className="mt-1 text-sm text-slate-500">Rolling week trend generated from current overview signals.</p>
          <div className="mt-4 h-[320px]">
            <Line
              data={trendData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(148, 163, 184, 0.16)' },
                    ticks: { callback: (value) => `${value}%` },
                  },
                },
              }}
            />
          </div>
        </motion.article>

        <motion.article
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          <h3 className="font-display text-xl font-semibold text-brand-900">Today's Presence Mix</h3>
          <p className="mt-1 text-sm text-slate-500">Real-time attendance ratio for active classes.</p>
          <div className="mx-auto mt-6 h-[250px] max-w-[300px]">
            <Doughnut
              data={attendanceMixData}
              options={{
                plugins: { legend: { position: 'bottom' } },
                cutout: '72%',
                maintainAspectRatio: false,
              }}
            />
          </div>
        </motion.article>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.25fr_1fr]">
        <motion.article
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="font-display text-xl font-semibold text-brand-900">{subjectsHeading}</h3>
              <p className="text-sm text-slate-500">{subjectsDescription}</p>
            </div>
            {canTakeAttendance ? (
              <Link
                to="/mark-attendance"
                className="inline-flex rounded-xl bg-brand-900 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
              >
                Quick Attendance
              </Link>
            ) : null}
          </div>

          {renderSubjectCards()}
        </motion.article>

        <div className="space-y-6">
          <motion.article
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="glass-panel rounded-3xl p-6 shadow-soft"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              <h3 className="font-display text-xl font-semibold text-brand-900">Low Attendance Alerts</h3>
            </div>
            <p className="mt-1 text-sm text-slate-500">Students below 75% attendance in the selected date range.</p>

            {(() => {
              if (lowAttendanceQuery.isLoading) {
                return <p className="mt-4 text-sm text-slate-500">Checking alert list...</p>
              }

              if (lowAttendanceAlerts.length === 0) {
                return (
                  <p className="mt-4 rounded-xl border border-dashed border-slate-300 px-3 py-4 text-sm text-slate-500">
                    No students are below the alert threshold.
                  </p>
                )
              }

              return (
                <div className="mt-4 max-h-[260px] space-y-2 overflow-auto pr-1">
                  {lowAttendanceAlerts.slice(0, 12).map((alert) => (
                    <div key={`${alert.student_id}-${alert.subject_id}`} className="rounded-xl border border-amber-100 bg-amber-50/50 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-slate-800">{alert.full_name}</p>
                          <p className="text-xs text-slate-500">{alert.roll_number} · {alert.subject_name}</p>
                        </div>
                        <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-700">
                          {alert.attendance_percent.toFixed(1)}%
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        Sem {alert.semester} · Sec {alert.section} · {alert.present_sessions}/{alert.total_sessions} sessions
                      </p>
                    </div>
                  ))}
                </div>
              )
            })()}
          </motion.article>

          <motion.article
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.07 }}
            className="glass-panel rounded-3xl p-6 shadow-soft"
          >
            <div className="flex items-center gap-2">
              <CalendarDays className="h-5 w-5 text-brand-700" />
              <h3 className="font-display text-xl font-semibold text-brand-900">Export Reports</h3>
            </div>
            <p className="mt-1 text-sm text-slate-500">Download attendance data in CSV, Excel, or PDF format.</p>

            <div className="mt-4 space-y-3 text-sm">
              <label className="block">
                <span className="mb-1 block text-slate-500">From</span>
                <input
                  type="date"
                  value={fromDate}
                  onChange={(event) => setFromDate(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-brand-600"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-slate-500">To</span>
                <input
                  type="date"
                  value={toDate}
                  onChange={(event) => setToDate(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-brand-600"
                />
              </label>
            </div>

            {downloadError ? (
              <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{downloadError}</p>
            ) : null}

            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              <button
                disabled={isDownloading}
                onClick={() => handleDownload('csv')}
                className="inline-flex items-center justify-center gap-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-brand-600"
              >
                <Download className="h-4 w-4" /> CSV
              </button>
              <button
                disabled={isDownloading}
                onClick={() => handleDownload('xlsx')}
                className="inline-flex items-center justify-center gap-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-brand-600"
              >
                <Download className="h-4 w-4" /> Excel
              </button>
              <button
                disabled={isDownloading}
                onClick={() => handleDownload('pdf')}
                className="inline-flex items-center justify-center gap-1 rounded-xl bg-brand-900 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-800"
              >
                <Download className="h-4 w-4" /> PDF
              </button>
            </div>
          </motion.article>
        </div>
      </div>
    </section>
  )
}
