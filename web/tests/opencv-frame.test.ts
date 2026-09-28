import { afterEach, describe, expect, it } from 'vitest'
import type { OpenCV } from '@opencvjs/web'
import { OpenCvFrameProcessor, trackingFrameSize } from '../src/opencv-frame'

describe('OpenCV camera preparation', () => {
  afterEach(() => { Reflect.deleteProperty(globalThis, 'document') })

  it('caps large cameras without enlarging smaller frames', () => {
    expect(trackingFrameSize(3840, 2160)).toEqual({ width: 1280, height: 720 })
    expect(trackingFrameSize(640, 480)).toEqual({ width: 640, height: 480 })
    expect(trackingFrameSize(1080, 1920)).toEqual({ width: 405, height: 720 })
    expect(() => trackingFrameSize(0, 720)).toThrow('valid frame dimensions')
  })

  it('mirrors the capped image and releases matrices on resize and stop', () => {
    const deleted: number[] = []
    const flipped: number[] = []
    const drawn: number[] = []
    let nextId = 0
    class FakeMat {
      readonly id = ++nextId
      readonly data: Uint8Array
      constructor(readonly rows: number, readonly cols: number) {
        this.data = new Uint8Array(rows * cols * 4)
      }
      delete(): void { deleted.push(this.id) }
    }
    const context = {
      drawImage: (..._args: unknown[]) => {},
      getImageData: (_x: number, _y: number, width: number, height: number) =>
        ({ data: new Uint8ClampedArray(width * height * 4) }),
    }
    const capture = { width: 0, height: 0, getContext: () => context }
    Object.defineProperty(globalThis, 'document', { configurable: true, value: { createElement: () => capture } })
    const cv = {
      Mat: FakeMat,
      CV_8UC4: 24,
      flip: (source: FakeMat, target: FakeMat, code: number) => {
        expect(code).toBe(1)
        expect(source.data.length).toBe(target.data.length)
        flipped.push(source.id)
      },
      imshow: (_canvas: HTMLCanvasElement, mat: FakeMat) => { drawn.push(mat.id) },
    } as unknown as typeof OpenCV
    const output = {} as HTMLCanvasElement
    const processor = new OpenCvFrameProcessor(cv, output)
    let video = { videoWidth: 640, videoHeight: 480 } as HTMLVideoElement

    processor.process(video)
    processor.process(video)
    expect(flipped).toEqual([1, 1])
    expect(drawn).toEqual([2, 2])
    video = { videoWidth: 320, videoHeight: 240 } as HTMLVideoElement
    processor.process(video)
    expect(deleted).toEqual([1, 2])
    expect(flipped).toEqual([1, 1, 3])
    processor.close()
    expect(deleted).toEqual([1, 2, 3, 4])
  })
})
