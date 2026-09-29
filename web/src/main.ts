import { attachCamera, cameraErrorMessage, CameraFrameGate, requestCameraStream, stopCamera } from './camera'
import { BrowserAudio } from './audio'
import { RhythmGame } from './game'
import { FingertipMotionTracker, HandStabilizer, WristVisibilityMonitor, type FingertipMotion } from './hands'
import { drawInputPreview, StageRenderer } from './stage'
import { createHandTracker, trackedHandsFrom, type TrackedHand } from './tracking'
import { createOpenCvFrameProcessor, type OpenCvFrameProcessor } from './opencv-frame'
import type { HandLandmarker } from '@mediapipe/tasks-vision'
import { mountInterface, requiredElement, messageForHands, renderScreen, renderGameStats } from './interface'
import './style.css'

mountInterface('web')

type Mode = 'idle' | 'starting' | 'live' | 'error'
const experience = requiredElement<HTMLElement>('.experience')
const inputPreview = requiredElement<HTMLCanvasElement>('#input-preview')
const video = requiredElement<HTMLVideoElement>('#camera-source')
const startButton = requiredElement<HTMLButtonElement>('#start-button')
const stopButton = requiredElement<HTMLButtonElement>('#stop-button')
const muteButton = requiredElement<HTMLButtonElement>('#mute-button')
const helpButton = requiredElement<HTMLButtonElement>('#help-button')
const restartButton = requiredElement<HTMLButtonElement>('#restart-button')
const menuButton = requiredElement<HTMLButtonElement>('#menu-button')
const cameraBadge = requiredElement<HTMLElement>('#camera-badge')
const modelBadge = requiredElement<HTMLElement>('#model-badge')
const soundBadge = requiredElement<HTMLElement>('#sound-badge')
const handCount = requiredElement<HTMLElement>('#hand-count')
const cameraPlaceholder = requiredElement<HTMLElement>('#camera-placeholder')
const welcomeMessage = requiredElement<HTMLElement>('#welcome-message')
const liveMessage = requiredElement<HTMLElement>('#live-message')
const compactViewport = window.matchMedia(
  '(max-width: 760px), (max-width: 1024px) and (max-height: 600px) and (orientation: landscape)',
)
const game = new RhythmGame(Math.random, compactViewport.matches)
const stage = new StageRenderer(requiredElement<HTMLCanvasElement>('#stage'), compactViewport.matches)
const stabilizer = new HandStabilizer()
const wristMonitor = new WristVisibilityMonitor()
const motionTracker = new FingertipMotionTracker()
const cameraFrames = new CameraFrameGate()
const mirroredFrame = document.createElement('canvas')

let stream: MediaStream | null = null
let tracker: HandLandmarker | null = null
let frameProcessor: OpenCvFrameProcessor | null = null
let audioContext: AudioContext | null = null
let audio: BrowserAudio | null = null
let activeHands: TrackedHand[] = []
let sessionId = 0
let shownHandCount = -1
let helpOpen = false
let wristWarningActive = false
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

function syncCompactViewport(): void {
  experience.classList.toggle('mobile-layout', compactViewport.matches)
  document.body.classList.toggle('mobile-body', compactViewport.matches)
  game.setMobileLayout(compactViewport.matches)
  stage.setMobileLayout(compactViewport.matches)
}
syncCompactViewport()
compactViewport.addEventListener('change', syncCompactViewport)

function nowSeconds(): number { return performance.now() / 1000 }
function setMessage(message: string): void { welcomeMessage.textContent = message; liveMessage.textContent = message }

function updateScreen(now = nowSeconds()): void {
  renderScreen({
    mode: experience.dataset.mode as Mode,
    screen: game.screen,
    help: helpOpen,
    wristWarning: wristWarningActive,
    countdown: game.round?.countdownRemaining(now) ?? 0,
  })
}

function setMode(mode: Mode): void {
  experience.dataset.mode = mode
  startButton.disabled = mode === 'starting'
  stopButton.hidden = mode !== 'starting' && mode !== 'live'
  updateScreen()
}

function setHandCount(count: number): void {
  if (count === shownHandCount) return
  shownHandCount = count
  handCount.textContent = `HANDS ${count}/2`
  setMessage(messageForHands(count))
}

function endSession(message: string, mode: Mode = 'idle'): void {
  sessionId += 1
  tracker?.close(); tracker = null
  frameProcessor?.close(); frameProcessor = null
  cameraFrames.stop()
  stopCamera(video, stream); stream = null
  audio?.stopAll(); audio = null
  if (audioContext) void audioContext.close().catch(() => {})
  audioContext = null
  activeHands = []
  stabilizer.reset(); wristMonitor.reset(); motionTracker.reset(); game.toMenu()
  helpOpen = false; shownHandCount = -1; wristWarningActive = false
  inputPreview.getContext('2d')?.clearRect(0, 0, inputPreview.width, inputPreview.height)
  cameraPlaceholder.hidden = false
  cameraBadge.textContent = 'CAMERA OFF'
  modelBadge.textContent = 'MODEL IDLE'
  soundBadge.textContent = 'SOUND OFF'
  handCount.textContent = 'HANDS 0/2'
  setMode(mode); setMessage(message)
}

function beginAudio(token: number): void {
  if (typeof AudioContext === 'undefined') { soundBadge.textContent = 'SOUND UNAVAILABLE'; return }
  try {
    const context = new AudioContext()
    audioContext = context
    audio = new BrowserAudio(context)
    soundBadge.textContent = 'SOUND STARTING'
    void context.resume().then(() => {
      if (token === sessionId) soundBadge.textContent = context.state === 'running' ? 'SOUND READY' : 'SOUND BLOCKED'
    }).catch(() => { if (token === sessionId) soundBadge.textContent = 'SOUND BLOCKED' })
  } catch { soundBadge.textContent = 'SOUND UNAVAILABLE' }
}

async function startSession(): Promise<void> {
  if (experience.dataset.mode === 'starting' || experience.dataset.mode === 'live') return
  const token = ++sessionId
  setMode('starting'); setMessage('Waiting for camera permission…'); beginAudio(token)
  try {
    const requestedStream = await requestCameraStream()
    if (token !== sessionId) { stopCamera(video, requestedStream); return }
    stream = requestedStream
    await attachCamera(video, requestedStream)
    if (token !== sessionId) return
    cameraFrames.start(video, nowSeconds())
    requestedStream.getVideoTracks()[0]?.addEventListener('ended', () => {
      if (token === sessionId) endSession('The camera disconnected. Reconnect it and try again.', 'error')
    }, { once: true })
    cameraBadge.textContent = 'CAMERA LIVE'
    cameraPlaceholder.hidden = true
    modelBadge.textContent = 'VISION LOADING'
    setMessage('Camera is ready. Loading OpenCV and the local hand model…')
    const loadedProcessor = await createOpenCvFrameProcessor(mirroredFrame)
    if (token !== sessionId) { loadedProcessor.close(); return }
    frameProcessor = loadedProcessor
    modelBadge.textContent = 'MODEL LOADING'
    const loadedTracker = await createHandTracker()
    if (token !== sessionId) { loadedTracker.close(); return }
    tracker = loadedTracker
    modelBadge.textContent = 'MODEL READY'
    setMode('live'); setHandCount(0)
  } catch (error) {
    if (token !== sessionId) return
    console.error('Air Rhythm web session could not start:', error)
    endSession(cameraErrorMessage(error), 'error')
  }
}

function startGame(mode: 'challenge' | 'free'): void {
  if (experience.dataset.mode !== 'live') return
  helpOpen = false
  audio?.stopAll()
  audio?.prepare(mode)
  if (audioContext?.state === 'suspended') void audioContext.resume().then(() => {
    soundBadge.textContent = audioContext?.state === 'running' ? 'SOUND READY' : 'SOUND BLOCKED'
  })
  motionTracker.reset()
  if (mode === 'challenge') game.startChallenge(nowSeconds())
  else game.startFree(nowSeconds())
  updateScreen()
}

function returnToMenu(): void {
  if (experience.dataset.mode !== 'live') return
  helpOpen = false
  audio?.stopAll()
  game.toMenu()
  updateScreen()
}

function toggleHelp(): void {
  if (experience.dataset.mode !== 'live' || game.screen === 'menu') return
  helpOpen = !helpOpen
  game.setPaused(helpOpen || document.hidden, nowSeconds())
  if (helpOpen) audio?.stopAll()
  updateScreen()
}

function toggleMute(): void {
  if (!audio) return
  audio.setMuted(!audio.muted)
  soundBadge.textContent = audio.muted ? 'SOUND MUTED' : 'SOUND READY'
  muteButton.textContent = audio.muted ? 'Unmute' : 'Mute'
}

function updateHud(now: number): void {
  const score = game.round?.score
  const free = game.screen === 'free'
  renderGameStats({
    screen: game.screen,
    score: free ? game.freeHits * 100 : score?.score ?? 0,
    combo: free ? 0 : score?.combo ?? 0,
    hits: free ? game.freeHits : score?.totalHits ?? 0,
    misses: free ? game.freeMisses : score?.misses ?? 0,
    resolved: game.round?.resolvedCount ?? 0,
    total: game.round?.chart.length ?? 0,
    progress: game.round?.progressAt(now) ?? 0,
    rank: score?.rank ?? 'C',
    completion: score?.completionAccuracy ?? 0,
    timing: score?.timingAccuracy ?? 0,
    maxCombo: score?.maxCombo ?? 0,
  })
}

function animationFrame(timeMs: number): void {
  const now = timeMs / 1000
  const { width, height } = stage.size()
  let motions: FingertipMotion[] = []
  if (stream && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && video.videoWidth > 0 &&
      cameraFrames.consume(now)) {
    try {
      frameProcessor?.process(video)
      if (tracker) {
        activeHands = stabilizer.update(trackedHandsFrom(tracker.detectForVideo(mirroredFrame, timeMs)), now)
        wristWarningActive = wristMonitor.update(activeHands, now)
        setHandCount(activeHands.length)
        if (game.screen === 'challenge' || game.screen === 'free') {
          motions = motionTracker.update(activeHands, now, width, height)
        }
      }
      drawInputPreview(inputPreview, mirroredFrame, activeHands)
    } catch (error) {
      console.error('Hand tracking stopped:', error)
      endSession('Hand tracking stopped unexpectedly. Please try again.', 'error')
    }
  }
  const hits = game.update(now, width, height, motions)
  audio?.playHits(hits)
  updateHud(now)
  updateScreen(now)
  stage.render(stabilizer.visibleAt(now), timeMs, {
    nodes: game.nodes, effects: game.effects,
    nextUnresolvedIndex: game.round?.nextUnresolvedIndex ?? null,
  }, reducedMotion.matches)
  requestAnimationFrame(animationFrame)
}

startButton.addEventListener('click', () => { void startSession() })
stopButton.addEventListener('click', () => endSession('Camera stopped. You can start it again.'))
requiredElement<HTMLButtonElement>('#challenge-button').addEventListener('click', () => startGame('challenge'))
requiredElement<HTMLButtonElement>('#free-button').addEventListener('click', () => startGame('free'))
requiredElement<HTMLButtonElement>('#retry-button').addEventListener('click', () => startGame('challenge'))
requiredElement<HTMLButtonElement>('#results-menu-button').addEventListener('click', returnToMenu)
requiredElement<HTMLButtonElement>('#resume-button').addEventListener('click', toggleHelp)
helpButton.addEventListener('click', toggleHelp)
muteButton.addEventListener('click', toggleMute)
restartButton.addEventListener('click', () => startGame(game.screen === 'free' ? 'free' : 'challenge'))
menuButton.addEventListener('click', returnToMenu)
window.addEventListener('keydown', event => {
  if (experience.dataset.mode !== 'live' || event.repeat || event.metaKey || event.ctrlKey || event.altKey) return
  const key = event.key.toLowerCase()
  if (['1', '2', 'r', 't', 'escape', 'h', 'm', ' '].includes(key)) event.preventDefault()
  if (key === '1' || key === ' ') startGame('challenge')
  else if (key === '2') startGame('free')
  else if (key === 'r') startGame(game.screen === 'free' ? 'free' : 'challenge')
  else if (key === 't' || key === 'escape') returnToMenu()
  else if (key === 'h') toggleHelp()
  else if (key === 'm') toggleMute()
})
document.addEventListener('visibilitychange', () => {
  game.setPaused(helpOpen || document.hidden, nowSeconds())
  if (document.hidden) audio?.stopAll()
})
window.addEventListener('pagehide', () => endSession('Camera stopped.'))
requestAnimationFrame(animationFrame)
