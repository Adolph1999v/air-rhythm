import { describe, expect, it } from 'vitest'
import { sceneBetweenFrames, type DesktopScene } from '../src/desktop-state'

describe('desktop note rendering between camera frames', () => {
  const scene: DesktopScene = {
    nodes: [{ xRatio: 0.5, yRatio: 0.4, fallPerSecond: 0.28, instrument: 'keys', pitch: 76, color: '#2c89ff' }],
    effects: [], nextUnresolvedIndex: null,
  }
  it('keeps the Python fall speed at a higher display refresh rate', () => {
    const frame = sceneBetweenFrames(scene, 1 / 60, false)
    expect(frame.nodes[0].yRatio).toBeCloseTo(0.4 + 0.28 / 60)
    expect(scene.nodes[0].yRatio).toBe(0.4)
  })
  it('limits motion if the Python connection stalls', () => {
    expect(sceneBetweenFrames(scene, 5, false).nodes[0].yRatio).toBeCloseTo(0.428)
  })
  it('holds notes still while paused', () => {
    expect(sceneBetweenFrames(scene, 0.1, true).nodes[0].yRatio).toBe(0.4)
  })
})
