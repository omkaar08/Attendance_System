import { useEffect, useMemo, useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { BookPlus, Link2, UserPlus } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import { facultyApi, getErrorMessage, managementApi, subjectsApi } from '../lib/api'
import { useAuth } from '../providers/AuthProvider'

export const FacultyManagementPage = () => {
  const { role } = useAuth()
  const isAdmin = role === 'admin'
  const isHod = role === 'hod'

  const [departmentId, setDepartmentId] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [employeeCode, setEmployeeCode] = useState('')
  const [designation, setDesignation] = useState('Assistant Professor')

  const [subjectCode, setSubjectCode] = useState('')
  const [subjectName, setSubjectName] = useState('')
  const [subjectSemester, setSubjectSemester] = useState(1)
  const [subjectSection, setSubjectSection] = useState('A')
  const [subjectFacultyId, setSubjectFacultyId] = useState('')
  const [attendanceGraceMinutes, setAttendanceGraceMinutes] = useState(15)

  const [subjectId, setSubjectId] = useState('')
  const [facultyId, setFacultyId] = useState('')

  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isCreatingSubject, setIsCreatingSubject] = useState(false)
  const [isAssigning, setIsAssigning] = useState(false)

  const departmentsQuery = useQuery({
    queryKey: ['managed-departments'],
    queryFn: managementApi.listDepartments,
    enabled: isAdmin,
  })

  useEffect(() => {
    if (!isAdmin) {
      return
    }

    const firstDepartmentId = departmentsQuery.data?.items[0]?.id
    if (firstDepartmentId && !departmentId) {
      setDepartmentId(firstDepartmentId)
    }
  }, [departmentId, departmentsQuery.data?.items, isAdmin])

  const scopedDepartmentId = isAdmin ? departmentId : undefined

  const facultyQuery = useQuery({
    queryKey: ['managed-faculty', role, scopedDepartmentId],
    queryFn: () => managementApi.listFaculty({ department_id: scopedDepartmentId }),
  })

  const subjectsQuery = useQuery({
    queryKey: ['hod-manageable-subjects'],
    queryFn: facultyApi.subjects,
    enabled: isHod,
  })

  const departments = departmentsQuery.data?.items ?? []
  const facultyItems = facultyQuery.data?.items ?? []
  const subjectItems = subjectsQuery.data?.items ?? []

  useEffect(() => {
    if (!isHod) {
      return
    }

    if (!facultyId && facultyItems[0]?.faculty_id) {
      setFacultyId(facultyItems[0].faculty_id)
    }
    if (!subjectFacultyId && facultyItems[0]?.faculty_id) {
      setSubjectFacultyId(facultyItems[0].faculty_id)
    }
  }, [facultyId, facultyItems, isHod, subjectFacultyId])

  const roleTitle = isAdmin ? 'Faculty Provisioning' : 'Faculty & Subject Management'
  const roleDescription = isAdmin
    ? 'Admin can add faculty users and map them to departments.'
    : 'HOD can add faculty for the department, create subjects, and assign subject ownership.'

  const hodSummary = useMemo(
    () => ({
      facultyCount: facultyItems.length,
      subjectCount: subjectItems.length,
    }),
    [facultyItems.length, subjectItems.length],
  )

  const renderFacultyRows = () => {
    if (facultyQuery.isLoading) {
      return (
        <tr>
          <td colSpan={4} className="py-5 text-slate-500">Loading faculty list...</td>
        </tr>
      )
    }

    if (facultyItems.length === 0) {
      return (
        <tr>
          <td colSpan={4} className="py-5 text-slate-500">No faculty found for this scope.</td>
        </tr>
      )
    }

    return facultyItems.map((faculty) => (
      <tr key={faculty.faculty_id} className="border-b border-slate-100">
        <td className="py-3">
          <p className="font-semibold text-brand-900">{faculty.full_name}</p>
          <p className="text-xs text-slate-500">{faculty.email}</p>
        </td>
        <td className="py-3 text-slate-700">{faculty.employee_code}</td>
        <td className="py-3 text-slate-700">{faculty.designation}</td>
        <td className="py-3 text-slate-700">{faculty.assigned_subject_count}</td>
      </tr>
    ))
  }

  const handleCreateFaculty = async (event: { preventDefault(): void }) => {
    event.preventDefault()
    setError(null)
    setStatus(null)
    setIsSaving(true)

    try {
      await managementApi.createFaculty({
        full_name: fullName,
        email,
        password,
        employee_code: employeeCode,
        designation,
        department_id: scopedDepartmentId,
      })

      await facultyQuery.refetch()
      setStatus(`Faculty profile created for ${fullName}.`)
      setFullName('')
      setEmail('')
      setPassword('')
      setEmployeeCode('')
      setDesignation('Assistant Professor')
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsSaving(false)
    }
  }

  const handleCreateSubject = async (event: { preventDefault(): void }) => {
    event.preventDefault()
    if (!isHod || !subjectFacultyId) {
      return
    }

    setError(null)
    setStatus(null)
    setIsCreatingSubject(true)

    try {
      await subjectsApi.create({
        code: subjectCode.trim().toUpperCase(),
        name: subjectName.trim(),
        semester: subjectSemester,
        section: subjectSection.trim().toUpperCase(),
        faculty_id: subjectFacultyId,
        attendance_grace_minutes: attendanceGraceMinutes,
      })

      await Promise.all([subjectsQuery.refetch(), facultyQuery.refetch()])
      setStatus(`Subject ${subjectCode.toUpperCase()} created successfully.`)
      setSubjectCode('')
      setSubjectName('')
      setSubjectSemester(1)
      setSubjectSection('A')
      setAttendanceGraceMinutes(15)
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setIsCreatingSubject(false)
    }
  }

  const handleAssignSubject = async (event: { preventDefault(): void }) => {
    event.preventDefault()
    if (!isHod || !subjectId || !facultyId) {
      return
    }

    setError(null)
    setStatus(null)
    setIsAssigning(true)
    try {
      await subjectsApi.assignFaculty(subjectId, facultyId)
      await Promise.all([facultyQuery.refetch(), subjectsQuery.refetch()])
      setStatus('Subject assignment updated successfully.')
    } catch (assignError) {
      setError(getErrorMessage(assignError))
    } finally {
      setIsAssigning(false)
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Department Operations"
        title={roleTitle}
        description={roleDescription}
      />

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          <div className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-brand-700" />
            <h3 className="font-display text-xl font-semibold text-brand-900">Add Faculty</h3>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {isAdmin
              ? 'Create faculty login and map profile to selected department.'
              : 'Create faculty login directly inside your department.'}
          </p>

          <form className="mt-4 space-y-3" onSubmit={handleCreateFaculty}>
            {isAdmin ? (
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Department</span>
                <select
                  value={departmentId}
                  onChange={(event) => setDepartmentId(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                >
                  {departments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.code} · {department.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Full Name</span>
                <input
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Employee Code</span>
                <input
                  value={employeeCode}
                  onChange={(event) => setEmployeeCode(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Temporary Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>
            </div>

            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Designation</span>
              <input
                value={designation}
                onChange={(event) => setDesignation(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                required
              />
            </label>

            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex w-full items-center justify-center rounded-xl bg-brand-900 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-70"
            >
              {isSaving ? 'Creating faculty...' : 'Create Faculty'}
            </button>
          </form>

          {isHod ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white/70 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Faculty Count</p>
                <p className="mt-1 font-display text-3xl font-semibold text-brand-900">{hodSummary.facultyCount}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white/70 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Subject Count</p>
                <p className="mt-1 font-display text-3xl font-semibold text-brand-900">{hodSummary.subjectCount}</p>
              </div>
            </div>
          ) : null}
        </motion.article>

        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          {isHod ? (
            <>
              <div className="flex items-center gap-2">
                <BookPlus className="h-5 w-5 text-brand-700" />
                <h3 className="font-display text-xl font-semibold text-brand-900">Create Subject</h3>
              </div>
              <p className="mt-1 text-sm text-slate-500">Create new department subject and set initial faculty owner.</p>

              <form className="mt-4 space-y-3" onSubmit={handleCreateSubject}>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block">
                    <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Subject Code</span>
                    <input
                      value={subjectCode}
                      onChange={(event) => setSubjectCode(event.target.value.toUpperCase())}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                      required
                    />
                  </label>

                  <label className="block">
                    <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Section</span>
                    <input
                      value={subjectSection}
                      onChange={(event) => setSubjectSection(event.target.value.toUpperCase())}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                      required
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Subject Name</span>
                  <input
                    value={subjectName}
                    onChange={(event) => setSubjectName(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                    required
                  />
                </label>

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block">
                    <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Semester</span>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={subjectSemester}
                      onChange={(event) => setSubjectSemester(Number(event.target.value))}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                      required
                    />
                  </label>

                  <label className="block">
                    <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Grace Minutes</span>
                    <input
                      type="number"
                      min={0}
                      max={240}
                      value={attendanceGraceMinutes}
                      onChange={(event) => setAttendanceGraceMinutes(Number(event.target.value))}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Faculty Owner</span>
                  <select
                    value={subjectFacultyId}
                    onChange={(event) => setSubjectFacultyId(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                    required
                  >
                    <option value="">Select faculty</option>
                    {facultyItems.map((faculty) => (
                      <option key={faculty.faculty_id} value={faculty.faculty_id}>
                        {faculty.full_name} ({faculty.employee_code})
                      </option>
                    ))}
                  </select>
                </label>

                <button
                  type="submit"
                  disabled={isCreatingSubject}
                  className="inline-flex w-full items-center justify-center rounded-xl bg-brand-900 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-70"
                >
                  {isCreatingSubject ? 'Creating subject...' : 'Create Subject'}
                </button>
              </form>

              <div className="my-5 h-px bg-slate-200" />

              <div className="flex items-center gap-2">
                <Link2 className="h-5 w-5 text-brand-700" />
                <h3 className="font-display text-xl font-semibold text-brand-900">Assign Subject</h3>
              </div>
              <p className="mt-1 text-sm text-slate-500">Reassign subject ownership to another faculty in your department.</p>

              <form className="mt-4 space-y-3" onSubmit={handleAssignSubject}>
                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Subject</span>
                  <select
                    value={subjectId}
                    onChange={(event) => setSubjectId(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                    required
                  >
                    <option value="">Select subject</option>
                    {subjectItems.map((subject) => (
                      <option key={subject.id} value={subject.id}>
                        {subject.code} · Sem {subject.semester} · Sec {subject.section}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Faculty</span>
                  <select
                    value={facultyId}
                    onChange={(event) => setFacultyId(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                    required
                  >
                    <option value="">Select faculty</option>
                    {facultyItems.map((faculty) => (
                      <option key={faculty.faculty_id} value={faculty.faculty_id}>
                        {faculty.full_name} ({faculty.employee_code})
                      </option>
                    ))}
                  </select>
                </label>

                <button
                  type="submit"
                  disabled={isAssigning}
                  className="inline-flex w-full items-center justify-center rounded-xl bg-brand-900 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-70"
                >
                  {isAssigning ? 'Updating assignment...' : 'Assign Subject'}
                </button>
              </form>
            </>
          ) : (
            <>
              <h3 className="font-display text-xl font-semibold text-brand-900">Subject Ownership Policy</h3>
              <p className="mt-2 text-sm text-slate-500">
                Subject creation and faculty assignment are restricted to HOD. Admin handles departments and HOD setup, and can also provision faculty.
              </p>
            </>
          )}
        </motion.article>
      </div>

      {status ? <p className="mt-4 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{status}</p> : null}
      {error ? <p className="mt-4 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

      <div className="mt-6 glass-panel rounded-3xl p-5 shadow-soft">
        <h3 className="font-display text-lg font-semibold text-brand-900">Faculty Directory</h3>
        <p className="mt-1 text-sm text-slate-500">Department-scoped list with current subject load.</p>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-[0.16em] text-slate-500">
                <th className="py-3">Faculty</th>
                <th className="py-3">Employee Code</th>
                <th className="py-3">Designation</th>
                <th className="py-3">Subjects Assigned</th>
              </tr>
            </thead>
            <tbody>
              {renderFacultyRows()}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
