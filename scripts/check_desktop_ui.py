"""Exercise the native shared UI with synthetic input and silent audio.

Run from the repository root: .venv/bin/python scripts/check_desktop_ui.py
Optional --screenshots saves temporary UI images under benchmark_reports/ui_check/.
"""

import argparse
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import webview

import app
from desktop_window import DesktopSession, ensure_desktop_assets


class CameraFixture:
    def __init__(self):
        self.frame = np.full((720, 1280, 3), (27, 20, 13), dtype=np.uint8)
        cv2.putText(self.frame, "CAMERA-FREE UI CHECK", (200, 380), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (220, 235, 245), 2)

    def isOpened(self): return True
    def set(self, *_args): return True
    def get(self, key):
        return {cv2.CAP_PROP_FRAME_WIDTH: 1280, cv2.CAP_PROP_FRAME_HEIGHT: 720, cv2.CAP_PROP_FPS: 30}.get(key, 0)
    def read(self):
        time.sleep(1 / 30)
        return True, self.frame
    def release(self): pass


def save_snapshot(window, name):
    from AppKit import NSBitmapImageRep, NSBitmapImageFileTypePNG
    from PyObjCTools import AppHelper

    destination = ROOT / "benchmark_reports" / "ui_check" / f"desktop-{name}.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    done = threading.Event()
    errors = []

    def captured(image, error):
        try:
            if error or image is None:
                raise RuntimeError(str(error))
            bitmap = NSBitmapImageRep.imageRepWithData_(image.TIFFRepresentation())
            data = bitmap.representationUsingType_properties_(NSBitmapImageFileTypePNG, {})
            if not data.writeToFile_atomically_(str(destination), True):
                raise RuntimeError("Could not save native screenshot")
        except Exception as exception:
            errors.append(exception)
        finally:
            done.set()

    AppHelper.callAfter(lambda: window.native.contentView().takeSnapshotWithConfiguration_completionHandler_(None, captured))
    if not done.wait(5) or errors:
        raise RuntimeError(f"Native screenshot failed: {errors}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()
    page = ensure_desktop_assets()
    session = DesktopSession(app.main)
    window = webview.create_window("Air Rhythm — UI check", str(page), js_api=session, width=1440, height=930, background_color="#020305", on_top=True)
    session._window = window
    window.events.closing += session._closing
    window.events.closed += session._closed
    failures = []

    def check():
        from AppKit import NSApplication
        from PyObjCTools import AppHelper

        window.show()
        AppHelper.callAfter(lambda: NSApplication.sharedApplication().activateIgnoringOtherApps_(True))

        def wait_for(expression, timeout=20):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if window.evaluate_js(expression):
                    return
                time.sleep(0.05)
            raise AssertionError(f"Timed out: {expression}")

        def click(selector):
            window.evaluate_js(f"document.querySelector({json.dumps(selector)}).click()")

        def screenshot(name):
            if args.screenshots:
                save_snapshot(window, name)

        try:
            wait_for("Boolean(window.pywebview?.api && document.querySelector('#start-button'))")
            wait_for("!document.hidden")
            window.evaluate_js("window.uiErrors=[]; window.addEventListener('error', e=>uiErrors.push(e.message)); window.addEventListener('unhandledrejection', e=>uiErrors.push(String(e.reason)))")
            screenshot("welcome")
            click("#start-button")
            wait_for("document.querySelector('.experience').dataset.mode === 'live'")
            wait_for("document.querySelector('#input-preview').width > 0")
            assert window.evaluate_js("document.querySelector('#menu h1').textContent") == "Make the music move."
            screenshot("menu")
            print("Native menu, camera bridge, and shared wording: OK", flush=True)
            click("#challenge-button")
            wait_for("document.querySelector('.experience').dataset.screen === 'challenge'")
            wait_for("!document.querySelector('#countdown').hidden")
            screenshot("countdown")
            click("#help-button")
            wait_for("!document.querySelector('#help').hidden")
            screenshot("help")
            click("#resume-button")
            wait_for("document.querySelector('#help').hidden")
            wait_for("document.querySelector('#countdown').hidden")
            time.sleep(0.5)
            screenshot("game")
            click("#mute-button")
            wait_for("document.querySelector('#sound-badge').textContent === 'SOUND MUTED'")
            window.resize(1100, 740)
            wait_for("innerWidth === 1100")
            screenshot("resized")
            deadline = time.monotonic() + 3
            while session._size()[0] != 1100 and time.monotonic() < deadline:
                time.sleep(0.05)
            assert session._size()[0] == 1100, f"Backend viewport: {session._size()}"
            print("Countdown, help/resume, mute, and resize: OK", flush=True)
            click("#menu-button")
            wait_for("document.querySelector('.experience').dataset.screen === 'menu'")
            click("#free-button")
            wait_for("document.querySelector('.experience').dataset.screen === 'free'")
            screenshot("free")
            click("#stop-button")
            wait_for("document.querySelector('.experience').dataset.mode === 'idle'")
            click("#start-button")
            wait_for("document.querySelector('.experience').dataset.mode === 'live'")
            print("Free play, stop camera, and restart camera: OK", flush=True)
            print(json.dumps(window.evaluate_js("({width:innerWidth,height:innerHeight,pixelRatio:devicePixelRatio,titleFont:getComputedStyle(document.querySelector('#menu h1')).fontFamily})")), flush=True)
        except Exception as error:
            failures.append(error)
            print(f"UI CHECK FAILED: {error}", flush=True)
            print("Backend status:", session._sequence, session._latest.get("mode"), session._latest.get("message"), flush=True)
            print("Backend countdown/help/hidden:",
                  (session._latest.get("snapshot") or {}).get("countdown"),
                  (session._latest.get("snapshot") or {}).get("help"), session._is_hidden(), flush=True)
            print("Window errors:", window.evaluate_js("window.uiErrors"), flush=True)
            print("Visible state:", window.evaluate_js("({mode:document.querySelector('.experience').dataset.mode,message:document.querySelector('#welcome-message').textContent,countdown:document.querySelector('#countdown').textContent,hidden:document.hidden,help:!document.querySelector('#help').hidden})"), flush=True)
        finally:
            session._request_close()

    audio = Mock(enabled=True, muted=False, error_message=None)
    audio.set_muted.side_effect = lambda muted: setattr(audio, "muted", muted)
    detector = Mock()
    detector.detect_for_video.return_value = SimpleNamespace(hand_landmarks=[], handedness=[])
    with (
        patch("app.cv2.VideoCapture", side_effect=lambda *_: CameraFixture()),
        patch("app.AudioEngine", return_value=audio),
        patch("app.create_hand_landmarker") as create_model,
    ):
        create_model.return_value.__enter__.return_value = detector
        webview.start(check, private_mode=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
