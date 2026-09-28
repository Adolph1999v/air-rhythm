"""Native window for the shared web interface, backed by the Python CV loop.

The bridge keeps only the latest snapshot. Camera pixels are sent to the local
window as an inset-sized JPEG; no camera frames or landmarks are written to disk.
"""

from __future__ import annotations

import base64
import math
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from typing import Callable

import cv2


ROOT = Path(__file__).resolve().parent
COMMAND_KEYS = {
    "challenge": ord("1"), "free": ord("2"), "restart": ord("r"),
    "menu": ord("t"), "help": ord("h"), "mute": ord("m"),
    "privacy": ord("p"), "debug": ord("d"), "benchmark": ord("b"),
}


def ensure_desktop_assets() -> Path:
    """Build shared local assets when source files changed since the last build."""
    web = ROOT / "web"
    page = web / "dist" / "desktop.html"
    sources = list((web / "src").rglob("*")) + [
        web / "index.html", web / "desktop.html", web / "vite.config.ts",
        web / "package.json", web / "package-lock.json",
    ]
    newest_source = max(path.stat().st_mtime for path in sources if path.is_file())
    if page.is_file() and page.stat().st_mtime >= newest_source:
        return page
    npm = shutil.which("npm")
    if npm is None or not (web / "node_modules").is_dir():
        raise RuntimeError(
            "The desktop interface needs its local web build. Install Node.js, "
            "then run 'cd web', 'npm ci', and 'npm run build' once."
        )
    print("Building the shared Air Rhythm interface…")
    subprocess.run([npm, "run", "build"], cwd=web, check=True, timeout=120)
    return page


def serialize_hands(hands) -> list[dict]:
    """Copy stabilized landmarks into the renderer's normalized coordinates."""
    return [
        {
            "identity": str(getattr(hand, "identity", f"Hand-{index}")),
            "label": str(getattr(hand, "identity", f"Hand-{index}")),
            "landmarks": [
                {"x": float(point.x), "y": float(point.y), "z": float(point.z)}
                for point in hand
            ],
        }
        for index, hand in enumerate(hands)
    ]


def make_snapshot(
    *, screen, game_mode, rhythm_round, nodes, effects, active_hands, visible_hands,
    width, height, now, presentation_time, hit_count, miss_count, show_help,
    wrist_warning, audio, debug_info, show_debug, benchmark_info, benchmark_notice,
    privacy_label,
) -> dict:
    """Describe the Python game without running a second game in JavaScript."""
    screen_name = {"TITLE": "menu", "RESULTS": "results"}.get(
        screen.value, "challenge" if game_mode == "challenge" else "free"
    )
    score = rhythm_round.score
    challenge = game_mode == "challenge"
    color = lambda bgr: "#{:02x}{:02x}{:02x}".format(*reversed(bgr))
    scene_nodes = []
    for node in nodes:
        item = {
            "xRatio": node.x / width, "yRatio": node.y / height,
            "fallPerSecond": node.speed / height,
            "color": color(node.color), "instrument": node.instrument,
            "pitch": node.midi_note or 0,
        }
        if node.chart_index is not None:
            item["event"] = {"index": node.chart_index}
        scene_nodes.append(item)
    return {
        "clock": now,
        "screen": screen_name,
        "help": show_help,
        "wristWarning": wrist_warning,
        "countdown": rhythm_round.countdown_remaining(presentation_time) if challenge else 0,
        "hands": serialize_hands(visible_hands),
        "activeHands": serialize_hands(active_hands),
        "handCount": len(active_hands),
        "sound": "SOUND UNAVAILABLE" if not audio.enabled else "SOUND MUTED" if audio.muted else "SOUND READY",
        "muted": bool(audio.muted),
        "privacy": privacy_label,
        "scene": {
            "nodes": scene_nodes,
            "nextUnresolvedIndex": rhythm_round.next_unresolved_index if challenge else None,
            "effects": [
                {
                    "xRatio": effect.position[0] / width,
                    "yRatio": effect.position[1] / height,
                    "color": color(effect.color), "label": effect.rating,
                    "detail": effect.detail or "", "at": effect.started_at,
                }
                for effect in effects
            ],
        },
        "stats": {
            "screen": screen_name, "score": score.score if challenge else hit_count * 100,
            "combo": score.combo if challenge else 0,
            "hits": hit_count, "misses": miss_count,
            "resolved": rhythm_round.resolved_count, "total": len(rhythm_round.chart),
            "progress": rhythm_round.progress_at(presentation_time) if challenge else 0,
            "rank": score.rank, "completion": score.completion_accuracy,
            "timing": score.timing_accuracy, "maxCombo": score.max_combo,
        },
        "debug": debug_info if show_debug else None,
        "benchmark": benchmark_info,
        "benchmarkNotice": benchmark_notice,
    }


class DesktopSession:
    """Small, thread-safe API exposed only to the bundled desktop page."""

    def __init__(self, run_backend: Callable) -> None:
        self._run_backend = run_backend
        self._condition = threading.Condition()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._commands: queue.Queue[int] = queue.Queue(maxsize=32)
        self._viewport = (1280, 800)
        self._hidden = False
        self._sequence = 0
        self._latest: dict = {"mode": "idle", "message": "Camera is off. This app does not record or upload camera frames."}
        self._window = None
        self._closing_started = False
        self._ready_to_close = False

    def start(self) -> None:
        with self._condition:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._commands = queue.Queue(maxsize=32)
            self._set_locked({"mode": "starting", "message": "Waiting for camera and hand tracking…"})
            self._thread = threading.Thread(target=self._run, name="air-rhythm-cv", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._condition:
            if self._thread is not None and self._thread.is_alive():
                self._set_locked({"mode": "starting", "message": "Stopping camera…"})

    def command(self, action: str) -> None:
        if action == "quit":
            self._request_close()
            return
        key = COMMAND_KEYS.get(action)
        if key is None:
            raise ValueError("Unknown desktop control")
        try:
            self._commands.put_nowait(key)
        except queue.Full:
            pass

    def viewport(self, width: float, height: float) -> None:
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (width, height)):
            raise ValueError("Viewport dimensions must be finite numbers")
        with self._condition:
            self._viewport = (max(320, min(8192, round(width))), max(240, min(8192, round(height))))

    def visibility(self, hidden: bool) -> None:
        with self._condition:
            self._hidden = bool(hidden)

    def frame(self, after: int = -1) -> dict | None:
        """One in-flight request waits for fresh data; old frames never queue."""
        with self._condition:
            self._condition.wait_for(lambda: self._sequence > after, timeout=0.1)
            if self._sequence <= after:
                return None
            return {"sequence": self._sequence, **self._latest}

    def _set_locked(self, state: dict) -> None:
        self._latest = state
        self._sequence += 1
        self._condition.notify_all()

    def _run(self) -> None:
        error = None
        try:
            self._run_backend(presentation=self)
        except Exception as exception:
            error = str(exception)
            print(f"Air Rhythm: {error}")
        finally:
            with self._condition:
                self._set_locked({
                    "mode": "error" if error else "idle",
                    "message": error or "Camera stopped. You can start it again.",
                })

    def _publish(self, snapshot: dict, preview) -> None:
        # The native HTML text stays at display resolution. Only camera pixels
        # are resized, to a maximum of 960px for the high-density live inset.
        if preview.shape[1] > 960:
            height = max(1, round(preview.shape[0] * 960 / preview.shape[1]))
            preview = cv2.resize(preview, (960, height), interpolation=cv2.INTER_AREA)
        success, encoded = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not success:
            raise RuntimeError("Could not prepare the camera inset")
        with self._condition:
            if self._stop_event.is_set():
                return
            self._set_locked({
                "mode": "live", "snapshot": snapshot,
                "preview": "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii"),
            })

    def _read_key(self) -> int:
        try:
            return self._commands.get_nowait()
        except queue.Empty:
            return -1

    def _size(self) -> tuple[int, int]:
        with self._condition:
            return self._viewport

    def _is_hidden(self) -> bool:
        with self._condition:
            return self._hidden

    def _closed(self) -> None:
        self.stop()
        if self._thread is not None:
            self._thread.join(timeout=3)

    def _closing(self):
        # Let an in-flight JS bridge call return while the native event loop
        # still exists. Closing WKWebView first can strand its callback thread.
        if self._ready_to_close or not self._window.events.loaded.is_set():
            self.stop()
            return None
        if not self._closing_started:
            self._closing_started = True
            threading.Thread(target=self._finish_close, name="air-rhythm-close", daemon=True).start()
        return False

    def _request_close(self) -> None:
        if self._window is None:
            self.stop()
        elif self._closing() is not False:
            self._window.destroy()

    def _finish_close(self) -> None:
        try:
            self._window.evaluate_js("window.dispatchEvent(new Event('air-rhythm-closing')); true")
            self.stop()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if self._window.evaluate_js("document.documentElement.dataset.bridgeIdle === 'true'"):
                    break
                time.sleep(0.02)
        finally:
            self._ready_to_close = True
            self._window.destroy()


def launch_desktop(run_backend: Callable) -> None:
    """Start the native UI on the main thread, with CV on its own worker."""
    import webview

    page = ensure_desktop_assets()
    session = DesktopSession(run_backend)
    window = webview.create_window(
        "Air Rhythm", str(page), js_api=session,
        width=1280, height=820, min_size=(640, 480), background_color="#020305",
    )
    session._window = window
    window.events.closing += session._closing
    window.events.closed += session._closed
    webview.start(private_mode=True)
