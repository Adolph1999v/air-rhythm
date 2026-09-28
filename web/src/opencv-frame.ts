import type { OpenCV } from '@opencvjs/web'

const MAX_CAMERA_WIDTH = 1280
const MAX_CAMERA_HEIGHT = 720

export function trackingFrameSize(width: number, height: number): { width: number; height: number } {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error('The camera did not provide valid frame dimensions.')
  }
  const scale = Math.min(1, MAX_CAMERA_WIDTH / width, MAX_CAMERA_HEIGHT / height)
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) }
}

/** Prepares the mirrored frame used by both MediaPipe and the live camera inset. */
export class OpenCvFrameProcessor {
  private readonly capture = document.createElement('canvas')
  private readonly captureContext = this.capture.getContext('2d', { willReadFrequently: true })
  private source: OpenCV.Mat | null = null
  private mirrored: OpenCV.Mat | null = null

  constructor(private readonly cv: typeof OpenCV, private readonly output: HTMLCanvasElement) {
    if (!this.captureContext) throw new Error('This browser cannot prepare camera frames.')
  }

  process(video: HTMLVideoElement): void {
    const { width, height } = trackingFrameSize(video.videoWidth, video.videoHeight)
    if (!this.source || !this.mirrored || this.capture.width !== width || this.capture.height !== height) {
      this.releaseMats()
      this.capture.width = width
      this.capture.height = height
      this.source = new this.cv.Mat(height, width, this.cv.CV_8UC4)
      this.mirrored = new this.cv.Mat(height, width, this.cv.CV_8UC4)
    }

    this.captureContext!.drawImage(video, 0, 0, width, height)
    const pixels = this.captureContext!.getImageData(0, 0, width, height)
    this.source.data.set(pixels.data)
    this.cv.flip(this.source, this.mirrored, 1)
    this.cv.imshow(this.output, this.mirrored)
  }

  close(): void { this.releaseMats() }

  private releaseMats(): void {
    this.source?.delete()
    this.mirrored?.delete()
    this.source = null
    this.mirrored = null
  }
}

export async function createOpenCvFrameProcessor(output: HTMLCanvasElement): Promise<OpenCvFrameProcessor> {
  try {
    // Load the large OpenCV runtime only after someone enables the camera.
    const { loadOpenCV } = await import('@opencvjs/web')
    return new OpenCvFrameProcessor(await loadOpenCV(), output)
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    throw new Error(`OpenCV.js could not load. Check the local web assets and try again. ${detail}`, { cause: error })
  }
}
