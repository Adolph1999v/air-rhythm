import { mountInterface, requiredElement, renderScreen, renderGameStats, setText, messageForHands,
  type ScreenState, type GameStats } from './interface'
import { StageRenderer, drawInputPreview } from './stage'
import { sceneBetweenFrames, type DesktopScene } from './desktop-state'
import type { TrackedHand } from './tracking'
import './style.css'

interface Snapshot extends Omit<ScreenState, 'mode'> {
  clock: number
  hands: TrackedHand[]
  activeHands: TrackedHand[]
  sound: string
  muted: boolean
  privacy: string
  scene: DesktopScene
  stats: GameStats
  debug: Record<string, unknown> | null
  benchmark: { active?: boolean; frames?: number; elapsed_seconds?: number } | null
  benchmarkNotice: string | null
}
interface Frame {
  sequence: number
  mode: ScreenState['mode']
  snapshot?: Snapshot
  preview?: string
  message?: string
}
interface DesktopApi {
  start(): Promise<void>
  stop(): Promise<void>
  command(action: string): Promise<void>
  viewport(width: number, height: number): Promise<void>
  visibility(hidden: boolean): Promise<void>
  frame(after: number): Promise<Frame | null>
}
declare global {
  interface Window { pywebview?: { api: DesktopApi } }
}

mountInterface('desktop')
const stage = new StageRenderer(requiredElement<HTMLCanvasElement>('#stage'))
const input = requiredElement<HTMLCanvasElement>('#input-preview')
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
const diagnostics = document.createElement('aside')
diagnostics.className = 'desktop-diagnostics'
diagnostics.hidden = true
requiredElement('.experience').append(diagnostics)
const benchmarkNotice = document.createElement('div')
benchmarkNotice.className = 'desktop-benchmark'
benchmarkNotice.hidden = true
requiredElement('.experience').append(benchmarkNotice)

let api: DesktopApi | undefined
let latest: Frame = { sequence: -1, mode: 'idle' }
let receivedAt = 0
let running = true
let lastSize = ''

function syncViewport(): void {
  const { width, height } = stage.size()
  const size = `${width}x${height}`
  if (api && size !== lastSize) {
    lastSize = size
    void api.viewport(width, height)
  }
}

function showMessage(message: string): void {
  setText('#welcome-message', message)
  setText('#live-message', message)
}

function refreshFrame(frame: Frame): void {
  latest = frame
  receivedAt = performance.now() / 1000
  const state = frame.snapshot
  const live = frame.mode === 'live' && state !== undefined
  setText('#camera-badge', live ? 'CAMERA LIVE' : 'CAMERA OFF')
  setText('#model-badge', live ? 'MODEL READY' : frame.mode === 'starting' ? 'MODEL LOADING' : 'MODEL IDLE')
  setText('#sound-badge', live ? state.sound : 'SOUND OFF')
  setText('#hand-count', `HANDS ${live ? state.handCount : 0}/2`)
  setText('#mute-button', live && state.muted ? 'Unmute' : 'Mute')
  requiredElement<HTMLElement>('#camera-placeholder').hidden = live
  showMessage(live ? messageForHands(state.handCount) : frame.message ?? 'Camera is off. This app does not record or upload camera frames.')
  if (live) renderGameStats(state.stats)
  // WebKit can pause animation frames when the native window is obscured.
  // Keep controls and screen state current even while the stage is not painting.
  renderScreen({
    mode: frame.mode, screen: state?.screen ?? 'menu', help: state?.help ?? false,
    handCount: state?.handCount ?? 0, countdown: state?.countdown ?? 0,
  })
  diagnostics.hidden = !live || !state.debug
  if (live && state.debug) {
    diagnostics.textContent = `OpenCV + MediaPipe · ${state.privacy}\n` + Object.entries(state.debug)
      .map(([name, value]) => `${name.replaceAll('_', ' ')}: ${Array.isArray(value) ? value.join(', ') : value}`).join('\n')
  }
  benchmarkNotice.hidden = !live || (!state.benchmark?.active && !state.benchmarkNotice)
  benchmarkNotice.textContent = live ? state.benchmark?.active
    ? `Benchmark recording · ${state.benchmark.frames ?? 0} frames · B to save`
    : state.benchmarkNotice ?? '' : ''
  if (live && frame.preview) {
    const preview = new Image()
    preview.onload = () => {
      if (latest.sequence === frame.sequence) drawInputPreview(input, preview, state.activeHands)
    }
    preview.src = frame.preview
  } else input.getContext('2d')?.clearRect(0, 0, input.width, input.height)
}

async function pollFrames(): Promise<void> {
  while (running && api) {
    try {
      const frame = await api.frame(latest.sequence)
      if (frame && running) refreshFrame(frame)
    } catch (error) {
      document.documentElement.dataset.bridgeIdle = 'true'
      if (!running) return
      console.error('Desktop connection stopped:', error)
      refreshFrame({ sequence: latest.sequence, mode: 'error', message: 'The desktop connection stopped. Close this window and restart Air Rhythm.' })
      return
    }
  }
  document.documentElement.dataset.bridgeIdle = 'true'
}

function animationFrame(timeMs: number): void {
  if (!running) return
  syncViewport()
  const snapshot = latest.mode === 'live' ? latest.snapshot : undefined
  const age = Math.max(0, timeMs / 1000 - receivedAt)
  const scene = snapshot ? sceneBetweenFrames(snapshot.scene, age, snapshot.help) : undefined
  const renderTime = snapshot ? (snapshot.clock + Math.min(age, 0.1)) * 1000 : timeMs
  stage.render(snapshot && age <= 0.25 ? snapshot.hands : [], renderTime, scene, reducedMotion.matches)
  renderScreen({
    mode: latest.mode,
    screen: snapshot?.screen ?? 'menu',
    help: snapshot?.help ?? false,
    handCount: snapshot?.handCount ?? 0,
    countdown: Math.max(0, (snapshot?.countdown ?? 0) - (snapshot?.help ? 0 : Math.min(age, 0.1))),
  })
  if (running) requestAnimationFrame(animationFrame)
}

function send(action: string): void {
  if (!api) return
  void api.command(action).catch(error => showMessage(String(error)))
}

const actions: Record<string, string> = {
  '#challenge-button': 'challenge', '#free-button': 'free', '#retry-button': 'challenge',
  '#results-menu-button': 'menu', '#resume-button': 'help', '#help-button': 'help',
  '#mute-button': 'mute', '#restart-button': 'restart', '#menu-button': 'menu',
}
for (const [selector, action] of Object.entries(actions)) {
  requiredElement(selector).addEventListener('click', () => send(action))
}
requiredElement('#start-button').addEventListener('click', () => {
  if (!api) return
  refreshFrame({ sequence: latest.sequence, mode: 'starting', message: 'Waiting for camera and hand tracking…' })
  void api.start().catch(error => refreshFrame({ sequence: latest.sequence, mode: 'error', message: String(error) }))
})
requiredElement('#stop-button').addEventListener('click', () => { void api?.stop() })
window.addEventListener('keydown', event => {
  if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) return
  const keys: Record<string, string> = {
    '1': 'challenge', ' ': 'challenge', '2': 'free', r: 'restart', t: 'menu', escape: 'menu',
    h: 'help', m: 'mute', p: 'privacy', d: 'debug', b: 'benchmark', q: 'quit',
  }
  const action = keys[event.key.toLowerCase()]
  if (action && (latest.mode === 'live' || action === 'quit')) {
    event.preventDefault()
    send(action)
  }
})
document.addEventListener('visibilitychange', () => { if (running) void api?.visibility(document.hidden) })
window.addEventListener('resize', syncViewport)
window.addEventListener('air-rhythm-closing', () => { running = false })
window.addEventListener('pagehide', () => { running = false })

function connect(): void {
  if (api || !window.pywebview?.api) return
  api = window.pywebview.api
  void api.visibility(document.hidden)
  syncViewport()
  void pollFrames()
}
window.addEventListener('pywebviewready', connect)
connect()
requestAnimationFrame(animationFrame)
