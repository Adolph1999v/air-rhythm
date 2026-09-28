# Getting Started

Air Rhythm has a Python desktop app and a standalone browser version. The desktop app has been tested on an Apple Silicon Mac with Python 3.14; other desktop operating systems are not yet validated. Both versions need a webcam and speakers for play, but the unit tests need neither.

## Before you begin

| Tool | Needed for | Where to get it |
| --- | --- | --- |
| Node.js with npm (20.19.x or 22.12+) | Both versions: the desktop builds the same interface as the browser | [Official Node.js download](https://nodejs.org/en/download) |
| `uv` **or** Python 3.14 | Desktop only: creates a Python environment and installs packages | [uv installation](https://docs.astral.sh/uv/getting-started/installation/) or [Python downloads](https://www.python.org/downloads/) |
| GNU Make | Only the shorter `make …` commands below | On macOS, [Apple Command Line Tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools); or skip Make and use the manual commands |

If you already have `uv`, it can [download Python 3.14](https://docs.astral.sh/uv/guides/install-python/) when creating the environment. The repository supplies a **Makefile**, not the `make` program, Node.js, or `uv`. On macOS, `xcode-select --install` opens Apple's Command Line Tools installer if `make` is missing. An internet connection is needed to fetch dependencies on the first setup.

The commands below use a macOS/Linux-style shell. The browser-only `cd web`, `npm ci`, and `npm run dev` commands also work in Windows PowerShell, but this project has not yet validated camera/audio behaviour there. Do not assume the Python desktop app is supported on Windows or Linux.

## Get the project

Download the [GitHub repository](https://github.com/Adolph1999v/air_rhythm) as a ZIP and extract it, or clone it:

```sh
git clone https://github.com/Adolph1999v/air_rhythm.git
cd air_rhythm
```

For a ZIP, open Terminal in the extracted folder instead (usually `air_rhythm-main`). Run every remaining command from the repository root unless the instructions say to enter `web/`.

## With Make

For **both** desktop and browser, install once, then choose which to run:

```sh
make install
make app
```

Use `make web` instead of `make app` for the browser. `make install` creates `.venv`, installs the Python packages, uses `npm ci` for the web lockfile, and builds the shared interface needed by the desktop app. It does **not** install the system tools in the table above.

For **browser only**, Python is unnecessary:

```sh
make web-requirements
make web
```

`make web-requirements` is one target; `make web requirements` would be two different targets. `make doctor` checks the prerequisites for the **full** setup and the local hand model. `make help` lists the other commands. `make verify` builds the interface and runs both unit-test suites without opening the camera.

## Without Make

You can run the exact underlying commands directly. Choose the browser-only or desktop route below; return to the repository root before switching routes. The browser-only route requires Node.js and npm, but not Python:

```sh
cd web
npm ci
npm run dev
```

Open the localhost address printed by Vite. Stop the development server with `Ctrl+C`.

For the **desktop app**, first create its Python environment from the repository root. Choose **one** of these two options:

```sh
# If uv is installed; it can obtain Python 3.14.
uv venv .venv --python 3.14 --allow-existing
uv pip install --python .venv/bin/python -r requirements.txt
```

```sh
# If Python 3.14 is installed but uv is not.
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

If `.venv` already exists, check `.venv/bin/python --version` first. Reuse it only if it is Python 3.14; then repeat only its dependency-install command. If it is a different version, move that environment aside and create a fresh one so packages are not mixed. The model is already checked in at [models/hand_landmarker.task](../models/hand_landmarker.task).

Then build the desktop's shared interface and start the app:

```sh
cd web
npm ci
npm run build
cd ..
.venv/bin/python app.py
```

After this initial build, the desktop launcher rebuilds the interface if its source files change. It still uses Python, OpenCV, MediaPipe, and sounddevice for the camera, game, and audio.

## Playing and checking the setup

Click **Enable camera & tracking** and grant camera access. In the browser, the page must be on localhost or HTTPS. On macOS, allow Camera access for the app that launched Python, such as Terminal or your editor. Choose **Start song challenge** or **Free play**, bring your hands into view, and touch falling circles. See the [Play Guide](PLAY_GUIDE.md) for controls and scoring.

With Make, `make tests` runs Python and browser unit tests, while `make verify` also checks the production web build. `make sound-test` plays the short melody without opening the camera. Without Make, run the checks for the version you installed. For the desktop, from the repository root:

```sh
.venv/bin/python -m unittest discover -s tests
```

For the browser, from the repository root:

```sh
cd web
npm test
npm run build
```

The optional macOS native-window check is `.venv/bin/python scripts/check_desktop_ui.py` from the repository root. It uses synthetic camera frames and silent audio; it is separate from the unit suites because it opens a window. Keep that window in the foreground while the check runs, since the app pauses when its window is hidden.

## If something goes wrong

- **`make` is missing:** Install Apple's Command Line Tools on macOS, or use the no-Make commands above.
- **Node.js, npm, or Python is missing:** Install the applicable tool from the official links above, then rerun the setup. `make install` cannot install those system tools.
- **Camera does not open:** Check webcam access under **System Settings → Privacy & Security → Camera** on macOS. Close other apps using the camera, then restart.
- **No sound:** Check the output device. Restart the app after changing devices. Bluetooth audio may add noticeable delay; the microphone is not used.
- **Hand tracking is unstable near an edge:** Keep the whole palm and wrist in view and improve lighting. Partial hands and motion blur reduce landmark quality.
- **The browser build shows an optional `fsevents` script or large-chunk warning:** These are non-fatal if the build finishes successfully. Do not approve install scripts without reviewing them.
- **The desktop interface build is missing:** From `web/`, run `npm ci` and `npm run build`, or rerun `make install`.

The browser-specific architecture and current limitations are in [Browser Version](WEB_VERSION.md); the implementation and measurements are in [Technical Overview](TECHNICAL_OVERVIEW.md) and [Performance Study](PERFORMANCE_STUDY.md).
