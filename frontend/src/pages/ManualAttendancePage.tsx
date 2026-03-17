import { useState, useMemo } from 'react'

import { useMutation, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { CheckCircle2, Check, X, Clock } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import { attendanceApi, facultyApi, studentsApi, getErrorMessage } from '../lib/api'
import type { StudentSummary } from '../lib/types'

const todayIso = (): string => new Date().toISOString().slice(0, 10)

export const ManualAttendancePage = () => {
  const [subjectId, setSubjectId] = useState('')
  const [classDate, setClassDate] = useState(todayIso())
  const [sessionLabel, setSessionLabel] = useState('Manual Entry')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStudents, setSelectedStudents] = useState<Map<string, 'present' | 'absent' | 'late'>>(new Map())
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)

  const subjectsQuery = useQuery({
    queryKey: ['faculty-subjects'],
    queryFn: facultyApi.subjects,
  })

  const studentsQuery = useQuery({
    queryKey: ['students-list', subjectId],
    queryFn: async () => {
      if (!subjectId) return { items: [] }
      return studentsApi.list({ subject_id: subjectId })
    },
    enabled: !!subjectId,
  })

  const selectedSubject = useMemo(
    () => subjectsQuery.data?.items.find((item) => item.id === subjectId) ?? null,
    [subjectId, subjectsQuery.data?.items],
  )

  const filteredStudents = useMemo(() => {
    if (!studentsQuery.data?.items) return []
    if (!searchQuery.trim()) return studentsQuery.data.items
    const query = searchQuery.toLowerCase()
    return (studentsQuery.data.items as StudentSummary[]).filter(
      (s) => s.full_name.toLowerCase().includes(query) || s.roll_number.toLowerCase().includes(query),
    )
  }, [studentsQuery.data?.items, searchQuery])

  const markAttendanceMutation = useMutation({
    mutationFn: async (entries: Array<{ student_id: string; status: 'present' | 'absent' | 'late' }>) => {
      const results = await Promise.all(
        entries.map((entry) =>
          attendanceApi.markManual({
            subject_id: subjectId,
            student_id: entry.student_id,
            class_date: classDate,
            status: entry.status,
            session_label: sessionLabel,
          }),
        ),
      )
      return results
    },
  })

  const handleToggleAttendance = (studentId: string, status: 'present' | 'absent' | 'late') => {
    const newMap = new Map(selectedStudents)
    if (newMap.get(studentId) === status) {
      newMap.delete(studentId)
    } else {
      newMap.set(studentId, status)
    }
    setSelectedStudents(newMap)
  }

  const handleClearAll = () => {
    setSelectedStudents(new Map())
    setSubmitError(null)
    setSubmitSuccess(null)
  }

  const handleSubmit = async () => {
    setSubmitError(null)
    setSubmitSuccess(null)

    if (selectedStudents.size === 0) {
      setSubmitError('Please mark attendance for at least one student.')
      return
    }

    const entries = Array.from(selectedStudents.entries()).map(([studentId, status]) => ({
      student_id: studentId,
      status,
    }))

    try {
      await markAttendanceMutation.mutateAsync(entries)
      setSubmitSuccess(`Successfully marked attendance for ${entries.length} student(s).`)
      setSelectedStudents(new Map())
      setSearchQuery('')
    } catch (error) {
      setSubmitError(getErrorMessage(error))
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Attendance Console"
        title="Manual Attendance Marking"
        description="Manually mark attendance for students in your selected subject. Use this when facial recognition is unavailable or as a backup."
      />

      <div className="grid gap-6">
        {/* Subject & Date Selection */}
        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          <h3 className="font-display text-xl font-semibold text-brand-900">Session Details</h3>
          <p className="mt-1 text-sm text-slate-500">Select the subject and date for manual attendance marking.</p>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Subject</span>
              <select
                value={subjectId}
                onChange={(e) => {
                  setSubjectId(e.target.value)
                  setSelectedStudents(new Map())
                  setSearchQuery('')
                }}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Select a subject</option>
                {(subjectsQuery.data?.items ?? []).map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.code} · Sem {subject.semester} · Sec {subject.section}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Class Date</span>
              <input
                type="date"
                value={classDate}
                onChange={(e) => setClassDate(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>

          <label className="mt-4 block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Session Label</span>
            <input
              type="text"
              value={sessionLabel}
              onChange={(e) => setSessionLabel(e.target.value)}
              placeholder="e.g., Theory Class, Lab Session"
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          {selectedSubject && (
            <div className="mt-4 rounded-xl bg-brand-50 border border-brand-200 p-3">
              <p className="text-sm font-medium text-brand-900">
                Selected: {selectedSubject.code} · {selectedSubject.name}
              </p>
              <p className="text-xs text-brand-700 mt-1">
                Semester {selectedSubject.semester}, Section {selectedSubject.section}
              </p>
            </div>
          )}
        </motion.article>

        {/* Student List */}
        {subjectId && (
          <motion.article
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="glass-panel rounded-3xl p-6 shadow-soft"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-display text-xl font-semibold text-brand-900">Mark Students</h3>
                <p className="mt-1 text-sm text-slate-500">
                  {filteredStudents.length} student(s) available
                  {selectedStudents.size > 0 && ` · ${selectedStudents.size} marked`}
                </p>
              </div>
              {selectedStudents.size > 0 && (
                <button
                  onClick={handleClearAll}
                  className="px-3 py-2 text-xs font-semibold text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  Clear All
                </button>
              )}
            </div>

            {/* Search */}
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name or roll number..."
              className="mt-4 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
            />

            {/* Students List */}
            <div className="mt-4 space-y-2 max-h-[600px] overflow-y-auto">
              {studentsQuery.isLoading ? (
                <div className="text-center py-8 text-slate-500">Loading students...</div>
              ) : filteredStudents.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  {searchQuery ? 'No students match your search.' : 'No students in this subject.'}
                </div>
              ) : (
                filteredStudents.map((student) => {
                  const status = selectedStudents.get(student.id)
                  return (
                    <div
                      key={student.id}
                      className={`rounded-xl border p-3 transition-all ${
                        status
                          ? 'border-brand-400 bg-brand-50'
                          : 'border-slate-300 bg-white hover:border-brand-300'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex-1">
                          <p className="font-medium text-slate-900">{student.full_name}</p>
                          <p className="text-xs text-slate-500">{student.roll_number}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleToggleAttendance(student.id, 'present')}
                            className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1 ${
                              status === 'present'
                                ? 'bg-emerald-600 text-white'
                                : 'border border-slate-300 text-slate-600 hover:border-emerald-500 hover:text-emerald-600'
                            }`}
                          >
                            <Check className="h-4 w-4" /> Present
                          </button>
                          <button
                            onClick={() => handleToggleAttendance(student.id, 'absent')}
                            className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1 ${
                              status === 'absent'
                                ? 'bg-rose-600 text-white'
                                : 'border border-slate-300 text-slate-600 hover:border-rose-500 hover:text-rose-600'
                            }`}
                          >
                            <X className="h-4 w-4" /> Absent
                          </button>
                          <button
                            onClick={() => handleToggleAttendance(student.id, 'late')}
                            className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-1 ${
                              status === 'late'
                                ? 'bg-amber-600 text-white'
                                : 'border border-slate-300 text-slate-600 hover:border-amber-500 hover:text-amber-600'
                            }`}
                          >
                            <Clock className="h-4 w-4" /> Late
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>

            {/* Status Messages */}
            {submitError && (
              <div className="mt-4 rounded-xl bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
                {submitError}
              </div>
            )}
            {submitSuccess && (
              <div className="mt-4 rounded-xl bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-700 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" /> {submitSuccess}
              </div>
            )}

            {/* Submit Button */}
            {selectedStudents.size > 0 && (
              <motion.button
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={handleSubmit}
                disabled={markAttendanceMutation.isPending}
                className="mt-4 w-full py-3 font-semibold rounded-xl bg-brand-900 text-white hover:bg-brand-800 disabled:opacity-60 transition-all"
              >
                {markAttendanceMutation.isPending
                  ? 'Submitting...'
                  : `Mark Attendance for ${selectedStudents.size} Student(s)`}
              </motion.button>
            )}
          </motion.article>
        )}
      </div>
    </section>
  )
}
