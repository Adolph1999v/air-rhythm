import { describe, expect, it } from 'vitest'
import { trackingReminder, type ScreenState } from '../src/interface'

const playing = (handCount: number): ScreenState => ({
  mode: 'live', screen: 'challenge', help: false, handCount, countdown: 3,
})

describe('detected-hand reminder', () => {
  it('appears as soon as a round countdown starts without two hands', () => {
    expect(trackingReminder(playing(0))).toBe('Bring both hands into the camera view.')
    expect(trackingReminder(playing(1))).toBe('One hand detected. Bring your other hand into the camera view.')
  })

  it('disappears with two hands and returns whenever a hand leaves view', () => {
    expect([0, 1, 2, 1, 2, 0].map(count => trackingReminder(playing(count)) === null))
      .toEqual([false, false, true, false, true, false])
  })

  it('works in free play but stays hidden outside active play', () => {
    expect(trackingReminder({ ...playing(1), screen: 'free', countdown: 0 })).not.toBeNull()
    expect(trackingReminder({ ...playing(0), screen: 'menu' })).toBeNull()
    expect(trackingReminder({ ...playing(0), screen: 'results' })).toBeNull()
    expect(trackingReminder({ ...playing(0), help: true })).toBeNull()
    expect(trackingReminder({ ...playing(0), mode: 'idle' })).toBeNull()
  })
})
