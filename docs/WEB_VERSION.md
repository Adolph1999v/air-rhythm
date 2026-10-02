# Browser Version

Air Rhythm runs as a [public browser game](https://air-rhythm.pages.dev/) as well as a Python desktop app. Both use the same HTML/CSS/Canvas interface, song chart, note visuals, and interaction rules. The browser adds a compact layout for phone-sized screens; normal desktop-sized browser windows retain the desktop presentation.

Cloudflare Pages hosts the public browser version and automatically rebuilds it after changes are pushed to GitHub's `main` branch. The Python desktop app remains a local program; it is not hosted on the website.

## What runs where

| Part | Desktop app | Browser version |
| --- | --- | --- |
| Camera | Python OpenCV captures frames | The browser camera API (`getUserMedia`) supplies video |
| Frame preparation | OpenCV bounds, mirrors, and converts frames | Canvas bounds oversized frames; OpenCV.js mirrors them |
| Hand landmarks | MediaPipe Hand Landmarker in Python | MediaPipe Hand Landmarker in browser WebAssembly |
| Game and scoring | Python logic | TypeScript implementation checked against the Python song data |
| Interface | Shared HTML/CSS/Canvas inside a native pywebview window | The same interface in a browser tab, with a compact phone layout |
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

Open the local address printed by Vite or the [hosted version](https://air-rhythm.pages.dev/) and allow camera access. Choose **Start song challenge** or **Free play**. Click **Stop camera** to release the stream. The playable page needs localhost or HTTPS for camera permission. From the repository root, `make test-web` runs browser unit tests and `make build-web` checks the production build; without Make, run `npm test` and `npm run build` inside `web/`.

## Playing on a phone

Portrait and short landscape screens use a compact score card and smaller camera inset. The active stage is kept clear of those panels: it sits between them in portrait and in a central strip in short landscape. Phone note centres follow the same stage-relative, constant-speed path in either orientation, so rotating the phone does not change when a circle reaches its scheduled beat. Pixel-per-second movement still differs because the playfields have different physical heights. The desktop-sized browser and native window keep their original note geometry.

The phone footer shows a game cue instead of keyboard shortcuts. Use the visible **Mute**, **Help**, **Restart**, and **Menu** buttons; **Stop camera** is available from the menu. For a roomier view without browser tabs, use the phone browser's **Add to Home Screen** option and launch Air Rhythm from its icon. The web app manifest requests a standalone window, but the exact browser chrome depends on the phone and browser. This remains a website, not a native mobile app, and it needs a network connection; no offline mode is promised.

## Sharing the public website

The public [entry page](../web/index.html) includes Open Graph metadata directly in its HTML, so link-preview crawlers can read the title, description, URL, and image without starting the game or requesting camera access. The preview uses a checked-in [1200×627 PNG](../web/public/social-preview.png), exported from an editable [SVG source](../web/assets/social-preview.svg). It is a branded illustration, not a camera recording. Neither asset is loaded by the gameplay interface.

Vite copies the PNG from `web/public/` into the production build. Sharing metadata uses absolute URLs for `https://air-rhythm.pages.dev/`; update the canonical URL, `og:url`, and `og:image` together if the public domain changes. When editing the SVG, export a new 1200×627 PNG to the same path and keep it below 5 MB. Browser tests check the metadata, image dimensions, and size.

After the updated build is deployed, inspect the public URL in [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/) to refresh and check the preview, then retry adding the link to profile media. LinkedIn controls the final card rendering and Projects-link acceptance; a passing local test does not verify those external results. These tags apply only to the public entry page, not `desktop.html`.

## Privacy and current limits

Camera frames, landmarks, and synthesized audio are processed on the visitor's device; the game does not upload or save a camera recording. The main stage never displays the whole camera frame. The live-input inset **does** show the camera and skeleton. Unlike the desktop app, the browser does not yet offer the `P` hands-only or skeleton-only privacy modes, the `D` technical overlay, or the `B` benchmark recorder.

OpenCV.js is loaded only after camera access begins, and its matrices are released when the camera stops or its size changes. Its browser bundle is large, so first-load time and hit responsiveness still need broader real-device measurement. The hosted site's landing page and a passing build do not establish real-camera performance on every device; the new compact phone layout still needs post-deployment testing. The current desktop [performance study](PERFORMANCE_STUDY.md) must not be presented as a browser benchmark.

The code entry points are [web/src/main.ts](../web/src/main.ts) for the browser and [web/src/desktop.ts](../web/src/desktop.ts) for the native window.
