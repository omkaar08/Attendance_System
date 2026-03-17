import { useMemo, useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ImagePlus, Search, UploadCloud } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import { facultyApi, getErrorMessage, recognitionApi, studentsApi } from '../lib/api'
import { fileToDataUrl, toApiBase64 } from '../lib/media'
import type { StudentSummary } from '../lib/types'

const allowedImageTypes = ['image/jpeg', 'image/png', 'image/webp'] as const

type AllowedImageType = (typeof allowedImageTypes)[number]

export const StudentsPage = () => {
  const [search, setSearch] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [processingStudentId, setProcessingStudentId] = useState<string | null>(null)

  const subjectsQuery = useQuery({
    queryKey: ['faculty-subjects'],
    queryFn: facultyApi.subjects,
  })

  const studentsQuery = useQuery({
    queryKey: ['students-list', search, subjectId],
    queryFn: () =>
      studentsApi.list({
        search: search || undefined,
        subject_id: subjectId || undefined,
        limit: 120,
      }),
  })

  const students = studentsQuery.data?.items ?? []

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

  return (
    <section>
      <PageHeader
        eyebrow="Student Management"
        title="Students & Face Assets"
        description="Browse enrolled students, filter by subject, and upload face samples for recognition training."
      />

      <div className="glass-panel rounded-3xl p-5 shadow-soft">
        <div className="grid gap-3 md:grid-cols-[1fr_260px]">
          <label className="relative">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
            <input
              placeholder="Search by name or roll number"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-sm outline-none focus:border-brand-600"
            />
          </label>

          <select
            value={subjectId}
            onChange={(event) => setSubjectId(event.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
          >
            <option value="">All assigned subjects</option>
            {(subjectsQuery.data?.items ?? []).map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.code} - {subject.section}
              </option>
            ))}
          </select>
        </div>

        {status ? <p className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{status}</p> : null}
        {error ? <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-[0.16em] text-slate-500">
                <th className="py-3">Student</th>
                <th className="py-3">Roll</th>
                <th className="py-3">Cohort</th>
                <th className="py-3">Subject Context</th>
                <th className="py-3 text-right">Face Asset</th>
              </tr>
            </thead>
            <tbody>
              {studentsQuery.isLoading ? (
                <tr>
                  <td colSpan={5} className="py-6 text-slate-500">Loading students...</td>
                </tr>
              ) : students.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 text-slate-500">No students found for current filter.</td>
                </tr>
              ) : (
                students.map((student) => (
                  <motion.tr
                    key={student.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="border-b border-slate-100"
                  >
                    <td className="py-4">
                      <p className="font-semibold text-brand-900">{student.full_name}</p>
                      <p className="text-xs text-slate-500">{student.email || 'No email'}</p>
                    </td>
                    <td className="py-4 font-medium text-slate-700">{student.roll_number}</td>
                    <td className="py-4 text-slate-600">
                      Sem {student.semester} · Sec {student.section}
                    </td>
                    <td className="py-4 text-slate-600">
                      {subjectId && subjectMap.get(subjectId)
                        ? `${subjectMap.get(subjectId)?.code} (${subjectMap.get(subjectId)?.name})`
                        : 'Assigned faculty subjects'}
                    </td>
                    <td className="py-4 text-right">
                      <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-brand-600 hover:text-brand-700">
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
