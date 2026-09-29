# Technical Overview

Air Rhythm uses a pretrained hand-landmark model inside an original real-time interaction pipeline. The rhythm-game format gives viewers a visible way to inspect tracking, motion, collision, timing, and response.

## Technology roles

| Component | Role in this project |
| --- | --- |
| Python | Desktop application, game state, timing, and tests |
| OpenCV | Camera access, frame preparation, privacy masks, and inset image encoding |
| OpenCV.js | Browser camera-frame mirroring before MediaPipe inference and the live-input inset |
| MediaPipe Hand Landmarker | Pretrained model that estimates 21 landmarks for up to two hands in video mode |
| NumPy | Landmark and image calculations plus generated audio waveforms |
| sounddevice | Output-only audio stream that plays and mixes prepared tones |
| HTML/CSS + TypeScript + Canvas | One shared interface and stage renderer for desktop and web |
| pywebview | Native desktop window and local Python-to-JavaScript bridge |

The local model file is `models/hand_landmarker.task`. It is supplied by MediaPipe and was **not trained by this project**. Air Rhythm's camera pipeline, landmark stabilisation, hand identity, fingertip motion, collision checks, beat scheduling, synthesized audio, privacy views, interface, and measurements are application code built around its output. A custom temporal gesture classifier is planned separately in [Future Plan](FUTURE_PLAN.md).

## From camera to sound on desktop

The path below describes the Python desktop app. The [Browser Version](WEB_VERSION.md) follows the same interaction pattern with its own camera, tracking, game, and audio implementations.

```text
Webcam frame
    → background worker keeps the latest complete frame
    → OpenCV limits size, mirrors the image, and converts BGR to RGB
    → MediaPipe Hand Landmarker estimates hand landmarks
    → adaptive filter smooths poses and preserves Left/Right identity
    → fingertips and their between-frame paths meet falling circles
    → the song clock grades contact time and updates the score
    → a hit requests a prepared tone from the audio engine
    → Python sends the latest game state, landmarks, and camera inset to the native window
    → the shared HTML/CSS/Canvas interface draws the stage, sticks, HUD, and skeleton
```

### Camera and display sizing

The app asks the camera for 1280×720 at 30 FPS, but camera drivers can ignore those requests. If a camera sends larger frames, OpenCV scales them to fit within 1280×720 while preserving aspect ratio. Smaller frames are processed at their native size. For example, 3840×2160 becomes 1280×720 if the camera actually supplies 4K, whereas 640×480 stays 640×480.

The desktop's native window uses the same HTML, CSS, and Canvas code as the browser. Text and controls are rendered at the screen's pixel density. Canvas adapts to the available area, with the same rendering pixel budget in both versions. The camera's resolution no longer sets the quality of the whole interface. Resizing updates Python's collision coordinates and note geometry as well as the view. In the standalone browser, the browser camera API supplies video, an offscreen Canvas caps oversized frames, and OpenCV.js mirrors the pixels before MediaPipe sees them. The local OpenCV runtime is loaded only after camera access begins.

The 30 FPS request is neither a hard cap nor a guarantee: a driver may deliver frames faster or slower, and the app processes fresh frames as they arrive. Falling-note motion and song scheduling use elapsed time so their intended speed does not depend on frame count. Low FPS can still make movement look less smooth or cause quick gestures to be missed.

### Keeping interaction responsive

`camera_capture.py` reads frames on a background worker. The game uses the newest complete frame rather than queueing old frames, allowing camera waiting to overlap inference and rendering. This change was the largest measured performance improvement; the full before-and-after evidence is in the [Performance Study](PERFORMANCE_STUDY.md).

`hand_stabilizer.py` uses adaptive landmark smoothing. Small stationary changes are filtered more strongly; faster intentional planar or depth motion receives less smoothing. Persistent Left/Right identities keep stick colours and movement histories attached to the right hand when MediaPipe reverses its result order. A lost hand's last stick pose may stay visible for up to 140 ms to reduce flicker, but stale poses cannot trigger collisions. Some vibration can remain when a hand is partly outside the camera view.

The collision system checks all fingertips and the path between each fingertip's previous and current positions. The rendered index-finger point is the virtual stick's tip; smaller markers show the other active contact points. The song clock gives each circle a scheduled beat and keeps its vertical movement time-based. Touch is sufficient for a hit; downward or forward movement can add a small bonus. Detailed scoring rules are in the [Play Guide](PLAY_GUIDE.md).

### One interface, two runtimes

`web/src/interface.ts`, `style.css`, and `stage.ts` supply the markup, wording, presentation rules, and graphics for both versions. The desktop loads their local build in a [pywebview native window](https://pywebview.flowrl.com/). Its Python worker owns camera capture, MediaPipe inference, filtering, collision, score, and sound. The window receives only the newest state and an inset-sized JPEG through the local bridge. It does not run a second hand model or game engine.

The standalone browser uses OpenCV.js, MediaPipe/WebAssembly, TypeScript gameplay, and Web Audio around those same interface components. In the desktop window, known note velocity fills the gaps between camera updates; extrapolation stops after 100 ms if updates stall. Hand positions are never extrapolated for collision. The desktop loads bundled local interface files; the browser runs on localhost or the public HTTPS site. Neither version uploads or saves camera images. [Browser Version](WEB_VERSION.md) explains the different runtimes in more detail.

### Audio and music

`music.py` contains a simplified pitch sequence and preview timings for the opening of *Für Elise*. `rhythm_game.py` turns the pitches into scheduled challenge circles. A hit plays the pitch attached to its circle; misses are silent. In free play, four instruments use fixed pitches instead of progressing through the melody.

`audio_engine.py` uses NumPy to prepare short waveforms at startup. At a hit, the camera loop requests one of those ready sounds. A separate sounddevice callback mixes simultaneous and ringing notes through an output-only stream; the microphone is not used. The application synthesises its own audio and includes no song recording. The music source and player-facing explanation are in the [Play Guide](PLAY_GUIDE.md).

### Privacy and technical evidence

The main stage is generated from scratch and never copies camera pixels. In the desktop app, a lower-right inset can show the normal camera, an approximate hands-only mask, or a skeleton-only view. The hands-only mask is based on landmarks and cannot guarantee pixel-perfect privacy if a hand overlaps a face or object. The browser currently offers only the normal camera inset. The [Play Guide](PLAY_GUIDE.md) explains the desktop modes.

In the desktop app, press `D` for the optional technical overlay: live FPS, camera-read and camera-wait times, preparation, MediaPipe inference, game update, rendering, complete-frame time, detected hands, landmark count, and mean handedness-classification confidence when available. That confidence is not overall tracking accuracy.

Press `B` in the desktop app to start and stop a benchmark. It writes JSON and Markdown reports to the repository-local, ignored `benchmark_reports/` directory. Reports contain timings, counts, resolutions, and environment details, but no camera images or hand-landmark coordinates. Raw reports are temporary; the maintained comparison is in the [Performance Study](PERFORMANCE_STUDY.md). Its frame-start-to-audio-request figure measures a software path, not the sound arriving at a speaker.

For the shared desktop window, `rendering_ms` measures Python snapshot and camera-inset preparation; it excludes the native browser's paint time. The historical OpenCV-drawn measurements in the study had a different boundary and must not be compared as if the renderers were identical. The old renderer was removed from the supported runtime.

## Code map

| Path | Responsibility |
| --- | --- |
| `app.py` | Main camera loop and integration |
| `desktop_window.py` | Native window lifecycle, latest-state bridge, and shared asset build |
| `web/src/interface.ts` | Shared screens, wording, controls, and status display |
| `web/src/stage.ts` | Shared starfield, notes, sticks, and hand skeleton rendering |
| `web/src/opencv-frame.ts` | Browser OpenCV.js frame preparation and matrix lifecycle |
| `web/src/desktop.ts` | Desktop presentation of authoritative Python state |
| `camera_capture.py` | Background latest-frame reader |
| `hand_stabilizer.py` | Adaptive landmark filtering and stable identities |
| `privacy.py` | Hands-only and skeleton-only inset rendering |
| `rhythm_game.py` | Song clock, grades, score, and round state |
| `music.py` | Instruments and melody note data |
| `audio_engine.py` | Prepared tones and background audio mixing |
| `performance_benchmark.py` | Privacy-safe measurements and report generation |
| `tests/` | Camera-free application and component checks |

The command for running the tests and the app is in [Getting Started](GETTING_STARTED.md).
