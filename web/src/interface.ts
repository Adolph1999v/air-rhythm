/** Shared markup and presentation rules for both browser and desktop windows. */
export function requiredElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector)
  if (!element) throw new Error(`The page is missing ${selector}.`)
  return element
}

export function mountInterface(platform: 'web' | 'desktop'): void {
  requiredElement<HTMLElement>('#app').innerHTML = `
  <section class="experience" data-mode="idle" data-screen="welcome">
    <canvas id="stage" class="stage" aria-label="Black starfield with falling notes and virtual drumsticks controlled by your hands"></canvas>
    <header class="topbar">
      <div class="brand"><span class="brand-icon" aria-hidden="true">✦</span><span>AIR RHYTHM</span><span class="brand-tag">WEB</span></div>
      <div class="top-actions">
        <span id="camera-badge" class="badge">CAMERA OFF</span>
        <span id="model-badge" class="badge">MODEL IDLE</span>
        <span id="sound-badge" class="badge">SOUND OFF</span>
        <button id="mute-button" class="quiet-button" type="button" hidden>Mute</button>
        <button id="help-button" class="quiet-button" type="button" hidden>Help</button>
        <button id="restart-button" class="quiet-button" type="button" hidden>Restart</button>
        <button id="menu-button" class="quiet-button" type="button" hidden>Menu</button>
        <button id="stop-button" class="quiet-button" type="button" hidden>Stop camera</button>
      </div>
    </header>
    <div id="welcome" class="welcome">
      <p class="eyebrow">LIVE RHYTHM STAGE · COMPUTER VISION</p>
      <h1>Play with your hands.</h1>
      <p class="intro-copy">Bring both hands into the camera view. The index fingertips steer virtual sticks; any fingertip can catch a falling note. Camera pixels stay in the live-input inset.</p>
      <button id="start-button" class="start-button" type="button">Enable camera &amp; tracking <span aria-hidden="true">↗</span></button>
      <p id="welcome-message" class="message" role="status" aria-live="polite">Camera is off. This app does not record or upload camera frames.</p>
      <p class="mobile-install-tip">For more room, use your browser's Add to Home Screen option and open Air Rhythm from its icon.</p>
    </div>
    <div id="menu" class="menu-panel" hidden>
      <p class="eyebrow">CAMERA READY · CHOOSE YOUR SET</p>
      <h1>Make the music move.</h1>
      <p class="intro-copy">Touch the falling circles with a fingertip. Move down or toward the camera for a stronger hit. Use both hands for the full melody.</p>
      <div class="menu-actions">
        <button id="challenge-button" class="start-button" type="button">Start song challenge <span aria-hidden="true">↗</span></button>
        <button id="free-button" class="secondary-button" type="button">Free play</button>
      </div>
      <p class="menu-caption">A short, hand-played version of Für Elise · 35 notes · no upload or recording</p>
    </div>
    <div id="hud" class="game-hud" hidden>
      <div class="hud-title"><span id="mode-name">SONG CHALLENGE</span><strong id="song-name">FÜR ELISE</strong><span id="note-progress">01 / 35</span></div>
      <div class="hud-values"><span>SCORE <strong id="score-value">0</strong></span><span>COMBO <strong id="combo-value">0</strong></span><span>HITS <strong id="hits-value">0</strong></span><span>MISSES <strong id="misses-value">0</strong></span></div>
      <div class="progress-track"><div id="progress-fill"></div></div>
      <p id="game-guide">Bring both hands into view. Touch circles with a fingertip; follow the note order for the best score.</p>
    </div>
    <div id="countdown" class="countdown" hidden aria-live="off"></div>
    <div id="results" class="results-panel" hidden>
      <p class="eyebrow">SONG COMPLETE</p>
      <h1 id="result-rank">RANK S</h1>
      <p id="result-score" class="result-score">0 POINTS</p>
      <p id="result-detail" class="result-detail"></p>
      <div class="menu-actions"><button id="retry-button" class="start-button" type="button">Play again <span aria-hidden="true">↗</span></button><button id="results-menu-button" class="secondary-button" type="button">Back to menu</button></div>
    </div>
    <div id="help" class="help-panel" hidden>
      <p class="eyebrow">PAUSED · HOW TO PLAY</p>
      <h2>Play with your index fingertips.</h2>
      <p>Bring both hands into the camera inset. The index fingertips steer the sticks. Any visible fingertip can touch a circle at any height until it leaves the bottom.</p>
      <p>In the song challenge, play circles in numbered order. A circle you touch out of order still sounds and scores a basic hit, but loses its timing bonus. Moving down or toward the camera adds a small movement bonus; a simple touch still works.</p>
      <p class="help-keys">1 Challenge · 2 Free play · R Restart · T Menu · H Help · M Mute</p>
      <p class="help-touch">Use the buttons at the top to mute, restart, or return to the menu. You can stop the camera from the menu.</p>
      <button id="resume-button" class="start-button" type="button">Resume <span aria-hidden="true">↗</span></button>
    </div>
    <aside class="input-panel" aria-label="Live camera input">
      <div id="tracking-warning" class="tracking-warning" role="status" aria-live="polite" hidden><span aria-hidden="true">!</span><span>Keep your whole hand and wrist visible in the camera.</span></div>
      <div class="input-heading"><span><span class="live-dot" aria-hidden="true"></span> LIVE INPUT</span><span id="hand-count">HANDS 0/2</span></div>
      <div class="input-frame"><canvas id="input-preview" aria-label="Mirrored camera view with detected hand skeletons"></canvas><div id="camera-placeholder" class="camera-placeholder">Camera preview appears here</div></div>
    </aside>
    <footer class="footer"><p id="live-message" aria-live="polite">Camera is off. This app does not record or upload camera frames.</p><p class="shortcut-hints">1 CHALLENGE · 2 FREE PLAY · H HELP · M MUTE · T MENU</p><p id="mobile-hint" class="mobile-hint"></p></footer>
    <video id="camera-source" autoplay muted playsinline hidden></video>
  </section>
`
  requiredElement<HTMLElement>('.brand-tag').textContent = platform.toUpperCase()
}

export function setText(selector: string, value: string): void {
  const element = requiredElement<HTMLElement>(selector)
  if (element.textContent !== value) element.textContent = value
}

export function messageForHands(count: number): string {
  if (count === 2) return 'Two hands detected. Move your index fingertips to steer the sticks.'
  if (count === 1) return 'One hand detected. Bring your other hand into the camera view.'
  return 'Tracking is live. Bring both hands into the camera view.'
}

export interface ScreenState {
  mode: 'idle' | 'starting' | 'live' | 'error'
  screen: 'menu' | 'challenge' | 'free' | 'results'
  help: boolean
  wristWarning: boolean
  countdown: number
}

export function renderScreen(state: ScreenState): void {
  const live = state.mode === 'live'
  const screen = live ? state.screen : 'welcome'
  const experience = requiredElement<HTMLElement>('.experience')
  experience.dataset.mode = state.mode
  experience.dataset.screen = screen
  const visibility: Record<string, boolean> = {
    '#welcome': !live,
    '#menu': live && screen === 'menu' && !state.help,
    '#hud': live && (screen === 'challenge' || screen === 'free'),
    '#results': live && screen === 'results' && !state.help,
    '#help': live && state.help,
    '#tracking-warning': live && !state.help && (screen === 'challenge' || screen === 'free') && state.wristWarning,
    '#help-button': live && screen !== 'menu',
    '#restart-button': live && (screen === 'challenge' || screen === 'free'),
    '#menu-button': live && screen !== 'menu',
    '#mute-button': live,
    '#stop-button': state.mode === 'starting' || live,
    '#countdown': live && screen === 'challenge' && !state.help && state.countdown > 0,
  }
  for (const [selector, visible] of Object.entries(visibility)) {
    requiredElement<HTMLElement>(selector).hidden = !visible
  }
  requiredElement<HTMLButtonElement>('#start-button').disabled = state.mode === 'starting'
  if (state.countdown > 0) setText('#countdown', String(Math.ceil(state.countdown)))
  setText('#mobile-hint', screen === 'challenge'
    ? 'Gold edge = next note · Touch any visible circle'
    : 'Touch any falling circle to make music')
}

export interface GameStats {
  screen: ScreenState['screen']
  score: number
  combo: number
  hits: number
  misses: number
  resolved: number
  total: number
  progress: number
  rank: string
  completion: number
  timing: number
  maxCombo: number
}

export function renderGameStats(stats: GameStats): void {
  if (stats.screen === 'challenge' || stats.screen === 'free') {
    const challenge = stats.screen === 'challenge'
    setText('#mode-name', challenge ? 'SONG CHALLENGE' : 'FREE PLAY')
    setText('#song-name', challenge ? 'FÜR ELISE' : 'FOUR-INSTRUMENT FREE PLAY')
    setText('#score-value', stats.score.toLocaleString())
    setText('#combo-value', String(stats.combo))
    setText('#hits-value', String(stats.hits))
    setText('#misses-value', String(stats.misses))
    setText('#note-progress', challenge
      ? `${String(Math.min(stats.resolved + 1, stats.total)).padStart(2, '0')} / ${stats.total}`
      : 'NO TIME LIMIT')
    requiredElement<HTMLElement>('#progress-fill').style.width = `${stats.progress * 100}%`
  } else if (stats.screen === 'results') {
    setText('#result-rank', `RANK ${stats.rank}`)
    setText('#result-score', `${stats.score.toLocaleString()} POINTS`)
    setText('#result-detail', `${stats.hits} / ${stats.total} circles caught · ${stats.completion.toFixed(0)}% completion · ${stats.timing.toFixed(0)}% timing accuracy · best combo ${stats.maxCombo}`)
  }
}
