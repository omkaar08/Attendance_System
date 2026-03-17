import { useMemo, useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ImagePlus, Search, UploadCloud, Users2, Building2, Mail } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import { facultyApi, getErrorMessage, recognitionApi, studentsApi, managementApi } from '../lib/api'
import { fileToDataUrl, toApiBase64 } from '../lib/media'
import type { StudentSummary } from '../lib/types'
import { useAuth } from '../providers/AuthProvider'

const allowedImageTypes = ['image/jpeg', 'image/png', 'image/webp'] as const

type AllowedImageType = (typeof allowedImageTypes)[number]

export const StudentsPage = () => {
  const { role } = useAuth()
  const isAdmin = role === 'admin'
  const isHod = role === 'hod'
  const isFaculty = role === 'faculty'

  const [search, setSearch] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [processingStudentId, setProcessingStudentId] = useState<string | null>(null)

  const subjectsQuery = useQuery({
    queryKey: ['faculty-subjects'],
    queryFn: facultyApi.subjects,
    enabled: isFaculty,
  })

  const departmentsQuery = useQuery({
    queryKey: ['departments-faculty-list'],
    queryFn: managementApi.listDepartments,
    enabled: isAdmin || isHod,
  })

  const facultyQuery = useQuery({
    queryKey: ['faculty-list', departmentId],
    queryFn: () =>
      managementApi.listFaculty({
        department_id: departmentId || undefined,
      }),
    enabled: isAdmin || isHod,
  })

  const studentsQuery = useQuery({
    queryKey: ['students-list', search, subjectId],
    queryFn: () =>
      studentsApi.list({
        search: search || undefined,
        subject_id: subjectId || undefined,
        limit: 120,
      }),
    enabled: isFaculty,
  })

  const students = studentsQuery.data?.items ?? []
  const allFaculty = facultyQuery.data?.items ?? []
  const departments = departmentsQuery.data?.items ?? []

  // Filter faculty by search term locally
  const faculty = useMemo(
    () =>
      allFaculty.filter((member) =>
        search
          ? member.full_name.toLowerCase().includes(search.toLowerCase()) ||
            member.email.toLowerCase().includes(search.toLowerCase())
          : true
      ),
    [allFaculty, search]
  )

  const subjectMap = useMemo(
    () => new Map(subjectsQuery.data?.items.map((subject) => [subject.id, subject]) ?? []),
    [subjectsQuery.data?.items],
  )

  const handleUploadAndEnroll = async (student: StudentSummary, file: File) => {
    setError(null)
    setStatus(null)
    setProcessingStudentId(student.id)

    try {
      const contentType = file.type as AllowedImageType
      if (!allowedImageTypes.includes(contentType)) {
        throw new Error('Only JPG, PNG, or WEBP files are supported.')
      }

      const uploadPayload = {
        student_id: student.id,
        file_name: file.name,
        content_type: contentType,
        asset_kind: 'face-training' as const,
      }

      const signedUpload = await studentsApi.createFaceUploadUrl(uploadPayload)
      await studentsApi.uploadToSignedUrl(signedUpload.signed_upload_url, file)

      const dataUrl = await fileToDataUrl(file)
      await recognitionApi.enroll({
        student_id: student.id,
        image_base64: toApiBase64(dataUrl),
        source: 'upload',
        storage_path: signedUpload.storage_path,
      })

      setStatus(`Face image uploaded and enrolled for ${student.full_name}.`)
      await studentsQuery.refetch()
    } catch (uploadError) {
      setError(getErrorMessage(uploadError))
    } finally {
      setProcessingStudentId(null)
    }
  }

  // Faculty List View (Admin/HOD)
  if (isAdmin || isHod) {
    return (
      <section>
        <PageHeader
          eyebrow="Management"
          title={isAdmin ? "Faculty Directory" : "Department Faculty"}
          description={isAdmin ? "View and manage all faculty members across the institution." : "View and manage faculty members in your department."}
        />

        <div className="glass-panel rounded-3xl p-6 shadow-soft">
          <div className="mb-6 grid gap-3 md:grid-cols-[1fr_260px]">
            <label className="relative">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
              <input
                placeholder="Search by name or email"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-sm font-medium outline-none focus:border-brand-600"
              />
            </label>

            {isAdmin && (
              <select
                value={departmentId}
                onChange={(event) => setDepartmentId(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-medium outline-none focus:border-brand-600"
              >
                <option value="">All departments</option>
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.code} - {dept.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {status ? <p className="mb-4 rounded-xl bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">{status}</p> : null}
          {error ? <p className="mb-4 rounded-xl bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700">{error}</p> : null}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50 text-xs uppercase tracking-[0.16em] text-slate-600">
                  <th className="px-4 py-3 font-semibold">Faculty Name</th>
                  <th className="px-4 py-3 font-semibold">Email</th>
                  <th className="px-4 py-3 font-semibold">Department</th>
                  <th className="px-4 py-3 font-semibold">Subjects</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {facultyQuery.isLoading ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">Loading faculty...</td>
                  </tr>
                ) : faculty.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">No faculty found.</td>
                  </tr>
                ) : (
                  faculty.map((member) => (
                    <motion.tr
                      key={member.faculty_id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="hover:bg-slate-50/50 transition-colors"
                    >
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100">
                            <Users2 className="h-5 w-5 text-brand-700" />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900">{member.full_name}</p>
                            <p className="text-xs text-slate-500">{member.employee_code}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <Mail className="h-4 w-4 text-slate-400" />
                          <a href={`mailto:${member.email}`} className="text-brand-600 hover:underline">{member.email}</a>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-slate-400" />
                          <span className="font-medium text-slate-700">{member.department_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-slate-600">{member.assigned_subject_count} {member.assigned_subject_count === 1 ? 'subject' : 'subjects'}</td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    )
  }

  // Student Management View (Faculty)
  return (
    <section>
      <PageHeader
        eyebrow="Student Management"
        title="Students & Face Assets"
        description="Browse enrolled students, filter by subject, and upload face samples for recognition training."
      />

      <div className="glass-panel rounded-3xl p-6 shadow-soft">
        <div className="mb-6 grid gap-3 md:grid-cols-[1fr_260px]">
          <label className="relative">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
            <input
              placeholder="Search by name or roll number"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-sm font-medium outline-none focus:border-brand-600"
            />
          </label>

          <select
            value={subjectId}
            onChange={(event) => setSubjectId(event.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-medium outline-none focus:border-brand-600"
          >
            <option value="">All assigned subjects</option>
            {(subjectsQuery.data?.items ?? []).map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.code} - {subject.section}
              </option>
            ))}
          </select>
        </div>

        {status ? <div className="mb-4 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm font-medium text-emerald-700">{status}</div> : null}
        {error ? <div className="mb-4 rounded-xl bg-rose-50 border border-rose-200 px-4 py-3 text-sm font-medium text-rose-700">{error}</div> : null}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/50 text-xs uppercase tracking-[0.16em] text-slate-600">
                <th className="px-4 py-3 font-semibold">Student</th>
                <th className="px-4 py-3 font-semibold">Roll</th>
                <th className="px-4 py-3 font-semibold">Cohort</th>
                <th className="px-4 py-3 font-semibold">Subject Context</th>
                <th className="px-4 py-3 text-right font-semibold">Face Asset</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {studentsQuery.isLoading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">Loading students...</td>
                </tr>
              ) : students.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">No students found for current filter.</td>
                </tr>
              ) : (
                students.map((student) => (
                  <motion.tr
                    key={student.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="hover:bg-slate-50/50 transition-colors"
                  >
                    <td className="px-4 py-4">
                      <p className="font-semibold text-brand-900">{student.full_name}</p>
                      <p className="text-xs text-slate-500">{student.email || 'No email'}</p>
                    </td>
                    <td className="px-4 py-4 font-medium text-slate-700">{student.roll_number}</td>
                    <td className="px-4 py-4 text-slate-600">
                      S{student.semester} · Sec {student.section}
                    </td>
                    <td className="px-4 py-4 text-slate-600">
                      {subjectId && subjectMap.get(subjectId)
                        ? `${subjectMap.get(subjectId)?.code} (${subjectMap.get(subjectId)?.name})`
                        : 'Assigned faculty subjects'}
                    </td>
                    <td className="px-4 py-4 text-right">
                      <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-brand-600 hover:text-brand-700 hover:bg-brand-50">
                        {processingStudentId === student.id ? (
                          <UploadCloud className="h-4 w-4 animate-pulse" />
                        ) : (
                          <ImagePlus className="h-4 w-4" />
                        )}
                        {processingStudentId === student.id ? 'Uploading...' : 'Upload + Enroll'}
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          className="hidden"
                          disabled={processingStudentId !== null}
                          onChange={async (event) => {
                            const selected = event.target.files?.[0]
                            if (!selected) {
                              return
                            }
                            await handleUploadAndEnroll(student, selected)
                            event.currentTarget.value = ''
                          }}
                        />
                      </label>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
