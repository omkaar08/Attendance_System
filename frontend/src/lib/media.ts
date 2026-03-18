export interface CameraDevice {
  deviceId: string
  label: string
}

const cameraStorageKey = 'visionattend.camera.deviceId'
const externalCameraPattern = /(usb|webcam|external|brio|logitech)/i
const integratedCameraPattern = /(integrated|built-in|facetime|front)/i

const getDefaultVideoConstraints = (): MediaTrackConstraints => ({
  width: { ideal: 1280 },
  height: { ideal: 720 },
})

const getVideoConstraints = (
  facingMode: 'user' | 'environment',
  deviceId = '',
): MediaTrackConstraints => {
  if (deviceId) {
    return {
      ...getDefaultVideoConstraints(),
      deviceId: { exact: deviceId },
    }
  }

  return {
    ...getDefaultVideoConstraints(),
    facingMode,
  }
}

const scoreCameraDevice = (device: CameraDevice): number => {
  let score = device.label ? 1 : 0

  if (externalCameraPattern.test(device.label)) {
    score += 3
  }

  if (integratedCameraPattern.test(device.label)) {
    score -= 2
  }

  return score
}

export const getSavedCameraDeviceId = (): string => {
  if (!('localStorage' in globalThis)) {
    return ''
  }

  return globalThis.localStorage.getItem(cameraStorageKey) ?? ''
}

export const saveCameraDeviceId = (deviceId: string): void => {
  if (!('localStorage' in globalThis)) {
    return
  }

  if (!deviceId) {
    globalThis.localStorage.removeItem(cameraStorageKey)
    return
  }

  globalThis.localStorage.setItem(cameraStorageKey, deviceId)
}

export const listCameraDevices = async (): Promise<CameraDevice[]> => {
  if (!navigator.mediaDevices?.enumerateDevices) {
    return []
  }

  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices
    .filter((device) => device.kind === 'videoinput')
    .map((device, index) => ({
      deviceId: device.deviceId,
      label: device.label || `Camera ${index + 1}`,
    }))
}

export const pickPreferredCameraDevice = (devices: CameraDevice[], currentDeviceId = ''): string => {
  if (currentDeviceId && devices.some((device) => device.deviceId === currentDeviceId)) {
    return currentDeviceId
  }

  const preferred = [...devices].sort((left, right) => scoreCameraDevice(right) - scoreCameraDevice(left))[0]
  return preferred?.deviceId ?? ''
}

export const openVideoStream = async (
  facingMode: 'user' | 'environment',
  deviceId = '',
): Promise<{ stream: MediaStream; activeDeviceId: string }> => {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Camera access is not available in this browser.')
  }

  const requestStream = (preferredDeviceId = '') =>
    navigator.mediaDevices.getUserMedia({
      video: getVideoConstraints(facingMode, preferredDeviceId),
      audio: false,
    })

  try {
    const stream = await requestStream(deviceId)
    const activeDeviceId = stream.getVideoTracks()[0]?.getSettings().deviceId ?? deviceId
    return { stream, activeDeviceId }
  } catch (error) {
    if (!deviceId) {
      throw error
    }

    const stream = await requestStream()
    const activeDeviceId = stream.getVideoTracks()[0]?.getSettings().deviceId ?? ''
    return { stream, activeDeviceId }
  }
}

export const fileToDataUrl = (file: Blob): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result !== 'string') {
        reject(new Error('Failed to read image file.'))
        return
      }

      resolve(reader.result)
    }
    reader.onerror = () => reject(new Error('Failed to read image file.'))
    reader.readAsDataURL(file)
  })

export const toApiBase64 = (dataUrl: string): string => dataUrl

export const captureVideoFrame = async (video: HTMLVideoElement): Promise<Blob> => {
  if (!video.videoWidth || !video.videoHeight) {
    throw new Error('Camera frame is not ready yet.')
  }

  // Keep live-scan payloads small for slower mobile networks and free-tier backends.
  const maxDimension = 960
  const scale = Math.min(1, maxDimension / Math.max(video.videoWidth, video.videoHeight))
  const targetWidth = Math.max(1, Math.round(video.videoWidth * scale))
  const targetHeight = Math.max(1, Math.round(video.videoHeight * scale))

  const canvas = document.createElement('canvas')
  canvas.width = targetWidth
  canvas.height = targetHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Could not capture frame from camera.')
  }

  ctx.drawImage(video, 0, 0, targetWidth, targetHeight)

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('Failed to encode captured frame.'))
          return
        }
        resolve(blob)
      },
      'image/jpeg',
      0.75,
    )
  })
}

export const stopVideoStream = (stream: MediaStream | null): void => {
  stream?.getTracks().forEach((track) => track.stop())
}
