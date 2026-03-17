import { useEffect, useMemo, useRef, useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Camera, CameraOff, RefreshCcw } from 'lucide-react'

import { PageHeader } from '../components/ui/PageHeader'
import { facultyApi, getErrorMessage, recognitionApi } from '../lib/api'
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
import type { RecognizedFace } from '../lib/types'

interface OverlayBox {
  x: number
  y: number
  width: number
  height: number
}

interface RecognitionEvent extends RecognizedFace {
  captured_at: string
}

type BrowserFaceDetector = {
  detect: (source: HTMLVideoElement) => Promise<Array<{ boundingBox: DOMRectReadOnly }>>
}

type WindowWithFaceDetector = Window & {
  FaceDetector?: new (options?: { maxDetectedFaces?: number; fastMode?: boolean }) => BrowserFaceDetector
}

const todayIso = (): string => new Date().toISOString().slice(0, 10)

export const MarkAttendancePage = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const cameraStream = useRef<MediaStream | null>(null)
  const detectorRef = useRef<BrowserFaceDetector | null>(null)
  const recognizerBusy = useRef(false)

  const [cameraDevices, setCameraDevices] = useState<CameraDevice[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState(() => getSavedCameraDeviceId())
  const [subjectId, setSubjectId] = useState('')
  const [classDate, setClassDate] = useState(todayIso())
  const [sessionKey, setSessionKey] = useState(`period-${new Date().getHours() || 1}`)
  const [sessionLabel, setSessionLabel] = useState('Live Session')

  const [isCameraOn, setIsCameraOn] = useState(false)
  const [isAutoScanOn, setIsAutoScanOn] = useState(false)
  const [boxes, setBoxes] = useState<OverlayBox[]>([])
  const [events, setEvents] = useState<RecognitionEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('Camera is idle.')

  const subjectsQuery = useQuery({
    queryKey: ['faculty-subjects'],
    queryFn: facultyApi.subjects,
  })

  const selectedSubject = useMemo(
    () => subjectsQuery.data?.items.find((item) => item.id === subjectId) ?? null,
    [subjectId, subjectsQuery.data?.items],
  )

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
      const { stream, activeDeviceId } = await openVideoStream('environment', preferredCameraId)

      cameraStream.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      const devices = await listCameraDevices()
      setCameraDevices(devices)

      const nextCameraId = pickPreferredCameraDevice(devices, activeDeviceId || preferredCameraId)
      const activeCameraLabel = devices.find((device) => device.deviceId === nextCameraId)?.label
      setSelectedCameraId(nextCameraId)
      if (nextCameraId) {
        saveCameraDeviceId(nextCameraId)
      }

      const faceDetectorCtor = (globalThis as unknown as WindowWithFaceDetector).FaceDetector
      detectorRef.current = faceDetectorCtor
        ? new faceDetectorCtor({ maxDetectedFaces: 10, fastMode: true })
        : null

      if (!detectorRef.current) {
        setBoxes([{ x: 31, y: 20, width: 38, height: 56 }])
      }

      setIsCameraOn(true)
      setError(null)
      setStatus(
        activeCameraLabel
          ? `${activeCameraLabel} started. Begin live scanning when ready.`
          : 'Camera started. Begin live scanning when ready.',
      )
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
    setIsAutoScanOn(false)
    setBoxes([])
    setStatus('Camera stopped.')
  }

  useEffect(() => {
    if (!isCameraOn || !detectorRef.current || !videoRef.current) {
      return
    }

    let cancelled = false
    let frameCount = 0

    const detectLoop = async () => {
      if (cancelled || !videoRef.current || !detectorRef.current) {
        return
      }

      frameCount += 1
      if (frameCount % 12 === 0 && videoRef.current.videoWidth > 0) {
          const video = videoRef.current
        try {
            const result = await detectorRef.current.detect(video)
            const { videoWidth: w, videoHeight: h } = video
            const mapped = result.map((face) => ({
              x: (face.boundingBox.x / w) * 100,
              y: (face.boundingBox.y / h) * 100,
              width: (face.boundingBox.width / w) * 100,
              height: (face.boundingBox.height / h) * 100,
            }))
          setBoxes(mapped)
        } catch {
          setBoxes([])
        }
      }

      requestAnimationFrame(detectLoop)
    }

    requestAnimationFrame(detectLoop)
    return () => {
      cancelled = true
    }
  }, [isCameraOn])

  useEffect(() => {
    if (!isAutoScanOn || !isCameraOn || !videoRef.current || !subjectId) {
      return
    }

    const interval = setInterval(async () => {
      if (!videoRef.current || recognizerBusy.current) {
        return
      }

      recognizerBusy.current = true
      try {
        const frameBlob = await captureVideoFrame(videoRef.current)
        const frameDataUrl = await fileToDataUrl(frameBlob)

        const response = await recognitionApi.identify({
          frame_base64: toApiBase64(frameDataUrl),
          subject_id: subjectId,
          class_date: classDate,
          session_key: sessionKey,
          session_label: sessionLabel,
          auto_mark_attendance: true,
        })

        if (response.recognized.length > 0) {
          const now = new Date().toISOString()
          const eventBatch: RecognitionEvent[] = response.recognized.map((entry) => ({
            ...entry,
            captured_at: now,
          }))
          setEvents((previous) => [...eventBatch, ...previous].slice(0, 35))
          setStatus(`${response.recognized.length} face(s) recognized in latest scan.`)
        } else {
          setStatus(`Scanning... ${response.frame_face_count} face(s) detected, no confident match yet.`)
        }
      } catch (scanError) {
        setError(getErrorMessage(scanError))
      } finally {
        recognizerBusy.current = false
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [isAutoScanOn, isCameraOn, subjectId, classDate, sessionKey, sessionLabel])

  return (
    <section>
      <PageHeader
        eyebrow="Attendance Console"
        title="Mark Attendance with Live Camera"
        description="Stream a class feed, visualize detected faces, and auto-mark attendance for recognized students in the selected subject session."
      />

      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-3xl p-5 shadow-soft"
        >
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Subject</span>
              <select
                value={subjectId}
                onChange={(event) => setSubjectId(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
              >
                <option value="">Select subject</option>
                {(subjectsQuery.data?.items ?? []).map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.code} · Sem {subject.semester} · Sec {subject.section}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Class Date</span>
              <input
                type="date"
                value={classDate}
                onChange={(event) => setClassDate(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
              />
            </label>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Session Key</span>
              <input
                value={sessionKey}
                onChange={(event) => setSessionKey(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Session Label</span>
              <input
                value={sessionLabel}
                onChange={(event) => setSessionLabel(event.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-brand-600"
              />
            </label>
          </div>

          <label className="mt-3 block">
            <span className="mb-1 block text-xs uppercase tracking-[0.16em] text-slate-500">Camera Source</span>
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
              Select the external webcam you want to use for live recognition. If labels are generic, start the camera once and switch it again.
            </p>
          </label>

          <div className="relative mt-4 overflow-hidden rounded-2xl bg-slate-900">
            <video ref={videoRef} autoPlay playsInline muted className="h-[420px] w-full object-cover" />

            <div className="pointer-events-none absolute inset-0">
              {boxes.map((box, index) => (
                <div
                  key={`${box.x}-${box.y}-${index}`}
                  className="absolute rounded-xl border-2 border-emerald-400 shadow-[0_0_0_3px_rgba(16,185,129,0.2)]"
                  style={{
                    left: `${box.x}%`,
                    top: `${box.y}%`,
                    width: `${box.width}%`,
                    height: `${box.height}%`,
                  }}
                />
              ))}
            </div>

            {isCameraOn ? null : (
              <div className="absolute inset-0 grid place-items-center bg-slate-900/75 text-sm text-slate-200">
                Start camera to begin live attendance
              </div>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {isCameraOn ? (
              <button
                type="button"
                onClick={stopCamera}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
              >
                <CameraOff className="h-4 w-4" /> Stop Camera
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void startCamera()}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
              >
                <Camera className="h-4 w-4" /> Start Camera
              </button>
            )}

            <button
              type="button"
              onClick={() => setIsAutoScanOn((value) => !value)}
              disabled={!isCameraOn || !selectedSubject}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              <RefreshCcw className={`h-4 w-4 ${isAutoScanOn ? 'animate-spin' : ''}`} />
              {isAutoScanOn ? 'Stop Live Scan' : 'Start Live Scan'}
            </button>
          </div>

          <p className="mt-3 text-sm text-slate-600">{status}</p>
          {error ? <p className="mt-2 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        </motion.article>

        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="glass-panel rounded-3xl p-5 shadow-soft"
        >
          <h3 className="font-display text-xl font-semibold text-brand-900">Recognition Feed</h3>
          <p className="mt-1 text-sm text-slate-500">Attendance confirmations appear as soon as matches are detected.</p>

          <div className="mt-4 rounded-2xl bg-white/75 p-4 text-sm text-slate-600">
            <p>
              Active subject:{' '}
              <span className="font-semibold text-brand-900">
                {selectedSubject ? `${selectedSubject.code} · ${selectedSubject.name}` : 'Not selected'}
              </span>
            </p>
            <p className="mt-1">Session: {sessionLabel || 'Untitled'} ({sessionKey})</p>
          </div>

          <div className="mt-4 max-h-[500px] space-y-2 overflow-auto pr-1">
            {events.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-300 px-3 py-5 text-center text-sm text-slate-500">
                No recognition events yet.
              </p>
            ) : (
              events.map((event, index) => (
                <div key={`${event.student_id}-${event.captured_at}-${index}`} className="rounded-2xl border border-slate-200 bg-white/85 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-brand-900">{event.full_name}</p>
                      <p className="text-xs text-slate-500">{event.roll_number}</p>
                    </div>
                    <span
                      className={[
                        'rounded-full px-2 py-1 text-xs font-semibold',
                        event.attendance_marked
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-amber-100 text-amber-700',
                      ].join(' ')}
                    >
                      {event.attendance_marked ? 'Marked' : 'Already Marked'}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Confidence {(event.confidence * 100).toFixed(1)}% · {new Date(event.captured_at).toLocaleTimeString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </motion.article>
      </div>
    </section>
  )
}
