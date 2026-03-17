import { useEffect, useMemo, useRef, useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Camera, CameraOff, Save, Trash2, Upload } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import { facultyApi, getErrorMessage, recognitionApi, studentsApi } from '../lib/api'
import {
  captureVideoFrame,
  fileToDataUrl,
  getSavedCameraDeviceId,
  listCameraDevices,
  openVideoStream,
  pickPreferredCameraDevice,
  saveCameraDeviceId,
  stopVideoStream,
  toApiBase64,
} from '../lib/media'
import type { CameraDevice } from '../lib/media'
import type { StudentRegisterRequest, StudentSummary, SubjectSummary } from '../lib/types'

const allowedImageTypes = ['image/jpeg', 'image/png', 'image/webp'] as const
const ALL_SUBJECTS_OPTION = '__all_subjects__'

type AllowedImageType = (typeof allowedImageTypes)[number]

type CohortOption = {
  key: string
  department_id: string
  semester: number
  section: string
  subjectCount: number
}

const getCohortKey = (departmentId: string, semester: number, section: string): string =>
  `${departmentId}::${semester}::${section.toUpperCase()}`

const resolveSubject = (subjects: SubjectSummary[], subjectId: string): SubjectSummary | null =>
  subjects.find((subject) => subject.id === subjectId) ?? null

export const RegisterStudentPage = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const cameraStream = useRef<MediaStream | null>(null)

  const [cameraDevices, setCameraDevices] = useState<CameraDevice[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState(() => getSavedCameraDeviceId())
  const [subjectId, setSubjectId] = useState('')
  const [selectedCohortKey, setSelectedCohortKey] = useState('')
  const [fullName, setFullName] = useState('')
  const [rollNumber, setRollNumber] = useState('')
  const [batchYear, setBatchYear] = useState(new Date().getFullYear())
  const [email, setEmail] = useState('')

  const [createdStudent, setCreatedStudent] = useState<StudentSummary | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isCameraOn, setIsCameraOn] = useState(false)
  const [isUploadingFace, setIsUploadingFace] = useState(false)

  const subjectsQuery = useQuery({
    queryKey: ['faculty-subjects'],
    queryFn: facultyApi.subjects,
  })

  const embeddingsQuery = useQuery({
    queryKey: ['student-embeddings', createdStudent?.id],
    queryFn: () => recognitionApi.listEmbeddings(createdStudent?.id ?? ''),
    enabled: Boolean(createdStudent?.id),
  })

  const subjects = subjectsQuery.data?.items ?? []
  const isAllSubjectsMode = subjectId === ALL_SUBJECTS_OPTION
  const subject = resolveSubject(subjects, subjectId)

  const cohortOptions = useMemo<CohortOption[]>(() => {
    const map = new Map<string, CohortOption>()

    for (const item of subjects) {
      const key = getCohortKey(item.department_id, item.semester, item.section)
      const existing = map.get(key)
      if (existing) {
        existing.subjectCount += 1
        continue
      }

      map.set(key, {
        key,
        department_id: item.department_id,
        semester: item.semester,
        section: item.section,
        subjectCount: 1,
      })
    }

    return Array.from(map.values()).sort((a, b) => {
      if (a.semester !== b.semester) {
        return a.semester - b.semester
      }
      return a.section.localeCompare(b.section)
    })
  }, [subjects])

  useEffect(() => {
    if (isAllSubjectsMode) {
      const isCohortValid = cohortOptions.some((item) => item.key === selectedCohortKey)
      if (!isCohortValid) {
        setSelectedCohortKey(cohortOptions[0]?.key ?? '')
      }
      return
    }

    if (subject) {
      setSelectedCohortKey(getCohortKey(subject.department_id, subject.semester, subject.section))
    }
  }, [cohortOptions, isAllSubjectsMode, selectedCohortKey, subject])

  const selectedCohort = useMemo<CohortOption | null>(() => {
    if (isAllSubjectsMode) {
      return cohortOptions.find((item) => item.key === selectedCohortKey) ?? null
    }

    if (!subject) {
      return null
    }

    return {
      key: getCohortKey(subject.department_id, subject.semester, subject.section),
      department_id: subject.department_id,
      semester: subject.semester,
      section: subject.section,
      subjectCount: 1,
    }
  }, [cohortOptions, isAllSubjectsMode, selectedCohortKey, subject])

  useEffect(() => {
    let active = true

    const syncCameraDevices = async () => {
      try {
        const devices = await listCameraDevices()
        if (!active) {
          return
        }

        setCameraDevices(devices)
        setSelectedCameraId((current) => {
          const nextCameraId = pickPreferredCameraDevice(devices, current || getSavedCameraDeviceId())
          if (nextCameraId) {
            saveCameraDeviceId(nextCameraId)
          }
          return nextCameraId
        })
      } catch {
        if (active) {
          setCameraDevices([])
        }
      }
    }

    void syncCameraDevices()

    const mediaDevices = navigator.mediaDevices
    if (!mediaDevices?.addEventListener) {
      return () => {
        active = false
      }
    }

    const handleDeviceChange = () => {
      void syncCameraDevices()
    }

    mediaDevices.addEventListener('devicechange', handleDeviceChange)
    return () => {
      active = false
      mediaDevices.removeEventListener('devicechange', handleDeviceChange)
    }
  }, [])

  useEffect(() => () => stopVideoStream(cameraStream.current), [])

  const startCamera = async (preferredCameraId = selectedCameraId) => {
    try {
      stopVideoStream(cameraStream.current)
      const { stream, activeDeviceId } = await openVideoStream('user', preferredCameraId)
      cameraStream.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      const devices = await listCameraDevices()
      setCameraDevices(devices)

      const nextCameraId = pickPreferredCameraDevice(devices, activeDeviceId || preferredCameraId)
      setSelectedCameraId(nextCameraId)
      if (nextCameraId) {
        saveCameraDeviceId(nextCameraId)
      }

      setIsCameraOn(true)
      setError(null)
    } catch (cameraError) {
      setError(getErrorMessage(cameraError))
    }
  }

  const stopCamera = () => {
    stopVideoStream(cameraStream.current)
    cameraStream.current = null
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsCameraOn(false)
  }

  const uploadAndEnrollFace = async (student: StudentSummary, file: Blob, fileName: string, source: 'camera' | 'upload') => {
    setIsUploadingFace(true)
    setStatus(null)
    setError(null)

    try {
      const contentType = (file.type || 'image/jpeg') as AllowedImageType
      if (!allowedImageTypes.includes(contentType)) {
        throw new Error('Only JPG, PNG, or WEBP files are supported.')
      }

      const upload = await studentsApi.createFaceUploadUrl({
        student_id: student.id,
        file_name: fileName,
        content_type: contentType,
        asset_kind: 'face-training',
      })

      await studentsApi.uploadToSignedUrl(upload.signed_upload_url, file)
      const dataUrl = await fileToDataUrl(file)

      await recognitionApi.enroll({
        student_id: student.id,
        image_base64: toApiBase64(dataUrl),
        source,
        storage_path: upload.storage_path,
      })

      setStatus(`Face sample enrolled successfully for ${student.full_name}.`)
      await embeddingsQuery.refetch()
    } catch (uploadError) {
      setError(getErrorMessage(uploadError))
    } finally {
      setIsUploadingFace(false)
    }
  }

  const onCaptureFace = async () => {
    if (!createdStudent || !videoRef.current) {
      return
    }

    try {
      const frameBlob = await captureVideoFrame(videoRef.current)
      await uploadAndEnrollFace(
        createdStudent,
        frameBlob,
        `${createdStudent.roll_number}_camera_${Date.now()}.jpg`,
        'camera',
      )
    } catch (captureError) {
      setError(getErrorMessage(captureError))
    }
  }

  const onUploadFace = async (file: File) => {
    if (!createdStudent) {
      return
    }
    await uploadAndEnrollFace(createdStudent, file, file.name, 'upload')
  }

  const onDeleteEmbedding = async (embeddingId: string) => {
    setError(null)
    try {
      await recognitionApi.deleteEmbedding(embeddingId)
      await embeddingsQuery.refetch()
      setStatus('Embedding deprecated successfully.')
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    }
  }

  const handleRegister = async (event: { preventDefault(): void }) => {
    event.preventDefault()
    setError(null)
    setStatus(null)

    if (!selectedCohort) {
      setError(
        isAllSubjectsMode
          ? 'Please select a cohort for all-subject registration.'
          : 'Please select a subject before registering a student.',
      )
      return
    }

    const payload: StudentRegisterRequest = {
      full_name: fullName,
      roll_number: rollNumber,
      department_id: selectedCohort.department_id,
      semester: selectedCohort.semester,
      section: selectedCohort.section,
      batch_year: Number(batchYear),
      email: email || undefined,
    }

    setIsSaving(true)

    try {
      const student = await studentsApi.register(payload)
      setCreatedStudent(student)
      if (isAllSubjectsMode) {
        setStatus(
          `Student ${student.full_name} registered for all subjects in Sem ${selectedCohort.semester} Sec ${selectedCohort.section}. Add face samples now.`,
        )
      } else {
        setStatus(`Student ${student.full_name} registered. Add face samples now.`)
      }
      setFullName('')
      setRollNumber('')
      setEmail('')
    } catch (registerError) {
      setError(getErrorMessage(registerError))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Admissions"
        title="Register Student"
        description="Create a student profile and immediately capture or upload face samples for recognition readiness."
      />

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          <h3 className="font-display text-xl font-semibold text-brand-900">Student Profile</h3>
          <p className="mt-1 text-sm text-slate-500">Register by subject or use all-subject mode for the full cohort.</p>

          <form className="mt-5 space-y-4" onSubmit={handleRegister}>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Subject</span>
              <select
                value={subjectId}
                onChange={(event) => setSubjectId(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                required
              >
                <option value="">Select subject</option>
                <option value={ALL_SUBJECTS_OPTION}>All subjects (cohort-wide)</option>
                {subjects.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} · Sem {item.semester} · Sec {item.section}
                  </option>
                ))}
              </select>
            </label>

            {isAllSubjectsMode ? (
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Cohort for All Subjects</span>
                <select
                  value={selectedCohortKey}
                  onChange={(event) => setSelectedCohortKey(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                >
                  {cohortOptions.map((item) => (
                    <option key={item.key} value={item.key}>
                      Sem {item.semester} · Sec {item.section} · {item.subjectCount} subjects
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-xs text-slate-500">
                  Student will be available for attendance in every subject under the selected semester and section.
                </p>
              </label>
            ) : null}

            <div className="grid gap-4 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Full Name</span>
                <input
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Roll Number</span>
                <input
                  value={rollNumber}
                  onChange={(event) => setRollNumber(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Batch Year</span>
                <input
                  type="number"
                  value={batchYear}
                  onChange={(event) => setBatchYear(Number(event.target.value))}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Email (optional)</span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
                />
              </label>
            </div>

            {status ? <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{status}</p> : null}
            {error ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-900 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-70"
            >
              <Save className="h-4 w-4" />
              {isSaving ? 'Registering...' : 'Register Student'}
            </button>
          </form>
        </motion.article>

        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="glass-panel rounded-3xl p-6 shadow-soft"
        >
          <h3 className="font-display text-xl font-semibold text-brand-900">Face Capture & Enrollment</h3>
          <p className="mt-1 text-sm text-slate-500">
            {createdStudent
              ? `Adding embeddings for ${createdStudent.full_name}`
              : 'Register a student first to activate camera capture and uploads.'}
          </p>

          <label className="mt-4 block">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Camera Source</span>
            <select
              value={selectedCameraId}
              onChange={(event) => {
                const nextCameraId = event.target.value
                setSelectedCameraId(nextCameraId)
                saveCameraDeviceId(nextCameraId)
                if (isCameraOn) {
                  void startCamera(nextCameraId)
                }
              }}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
            >
              <option value="">Default camera</option>
              {cameraDevices.map((device) => (
                <option key={device.deviceId || device.label} value={device.deviceId}>
                  {device.label}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-500">
              Select your external webcam here. If labels are generic, start the camera once and then switch to the webcam.
            </p>
          </label>

          <div className="relative mt-4 overflow-hidden rounded-2xl bg-slate-900">
            <video ref={videoRef} autoPlay playsInline muted className="h-[260px] w-full object-cover" />
            {isCameraOn ? null : (
              <div className="absolute inset-0 grid place-items-center bg-slate-900/75 text-sm text-slate-200">
                Camera is off
              </div>
            )}
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {isCameraOn ? (
              <button
                type="button"
                onClick={stopCamera}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
              >
                <CameraOff className="h-4 w-4" /> Stop Camera
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void startCamera()}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
              >
                <Camera className="h-4 w-4" /> Start Camera
              </button>
            )}

            <button
              type="button"
              disabled={!isCameraOn || !createdStudent || isUploadingFace}
              onClick={onCaptureFace}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {isUploadingFace ? 'Capturing...' : 'Capture & Enroll'}
            </button>
          </div>

          <label className="mt-3 inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-slate-400 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:border-brand-600">
            <Upload className="h-4 w-4" /> Upload image & enroll
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={!createdStudent || isUploadingFace}
              onChange={async (event) => {
                const file = event.target.files?.[0]
                if (!file) {
                  return
                }
                await onUploadFace(file)
                event.currentTarget.value = ''
              }}
            />
          </label>

          <div className="mt-5">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Embeddings</p>
            {(() => {
              if (embeddingsQuery.isLoading) return <p className="mt-2 text-sm text-slate-500">Loading embeddings...</p>
              if ((embeddingsQuery.data?.items.length ?? 0) === 0) return <p className="mt-2 text-sm text-slate-500">No embeddings yet.</p>
              return (
                <div className="mt-2 max-h-[220px] space-y-2 overflow-auto pr-1">
                  {embeddingsQuery.data?.items.map((embedding) => (
                    <div key={embedding.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-sm">
                      <div>
                        <p className="font-semibold text-slate-700">{embedding.sample_source}</p>
                        <p className="text-xs text-slate-500">
                          quality {(embedding.quality_score * 100).toFixed(1)}% · {embedding.status}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => onDeleteEmbedding(embedding.id)}
                        className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Deprecate
                      </button>
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>
        </motion.article>
      </div>
    </section>
  )
}
