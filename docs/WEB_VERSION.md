# Browser Version

Air Rhythm runs as a standalone browser game as well as a Python desktop app. Both use the same HTML/CSS/Canvas interface, song chart, note visuals, and interaction rules. The browser version is currently a local preview; it has not been hosted publicly.

## What runs where

| Part | Desktop app | Browser version |
| --- | --- | --- |
| Camera | Python OpenCV captures frames | The browser camera API (`getUserMedia`) supplies video |
| Frame preparation | OpenCV bounds, mirrors, and converts frames | Canvas bounds oversized frames; OpenCV.js mirrors them |
| Hand landmarks | MediaPipe Hand Landmarker in Python | MediaPipe Hand Landmarker in browser WebAssembly |
| Game and scoring | Python logic | TypeScript implementation checked against the Python song data |
| Interface | Shared HTML/CSS/Canvas inside a native pywebview window | The same interface in a browser tab |
| Sound | NumPy-prepared tones played with sounddevice | Locally synthesized tones played with Web Audio |

The browser does **not** call a Python server. It uses the same checked-in pretrained [hand model](../models/hand_landmarker.task), packaged into the web build. MediaPipe estimates 21 landmarks on each of up to two hands; Air Rhythm's filtering, motion, collision, beat clock, and scoring logic turn those landmarks into hits. This project did not train the MediaPipe model.

## Camera-to-sound path

1. The browser asks permission for camera video. The app requests 1280×720 at 30 FPS, but the camera may supply a different mode.
2. A small offscreen Canvas limits frames larger than 1280×720. OpenCV.js mirrors each frame before local MediaPipe inference.
3. The index fingertips steer the virtual sticks. All detected fingertips can catch a note; the path between camera updates is checked to reduce missed fast contacts.
4. A time-based clock moves the notes independently of display frame rate. Touch plays a note; downward or forward movement can add a small bonus.
5. Web Audio synthesizes the note locally. Canvas draws the person-free stage, virtual sticks, and camera inset with a visible hand skeleton.

The browser and desktop use the same opening melody and four-sound free play. A [Python parity test](../tests/test_web_music_parity.py) checks the browser's checked-in music data against [music.py](../music.py). The interfaces share [markup and wording](../web/src/interface.ts), [styles](../web/src/style.css), and the [stage renderer](../web/src/stage.ts); the separate Python and TypeScript game engines are **not** the same code.

## Run and test locally

For prerequisites and a complete setup path with or without Make, use [Getting Started](GETTING_STARTED.md). For browser-only setup from the repository root:

```sh
make web-requirements
make web
```

Without Make:

```sh
cd web
npm ci
npm run dev
```

Open the local address printed by Vite and allow camera access. Choose **Start song challenge** or **Free play**. Click **Stop camera** to release the stream. The playable page needs localhost or HTTPS for camera permission. From the repository root, `make test-web` runs browser unit tests and `make build-web` checks the production build; without Make, run `npm test` and `npm run build` inside `web/`.

## Privacy and current limits

Camera frames, landmarks, and synthesized audio are processed on the visitor's device; the game does not upload or save a camera recording. The main stage never displays the whole camera frame. The live-input inset **does** show the camera and skeleton. Unlike the desktop app, the browser does not yet offer the `P` hands-only or skeleton-only privacy modes, the `D` technical overlay, or the `B` benchmark recorder.

OpenCV.js is loaded only after camera access begins, and its matrices are released when the camera stops or its size changes. Its browser bundle is large, so first-load time and hit responsiveness still need real-device measurement. Live-camera testing in Chrome, Safari, and on phones is required before public hosting; a passing build or synthetic-camera check cannot establish real-camera performance. The current desktop [performance study](PERFORMANCE_STUDY.md) must not be presented as a browser benchmark.

The code entry points are [web/src/main.ts](../web/src/main.ts) for the browser and [web/src/desktop.ts](../web/src/desktop.ts) for the native window.
