"""Check the shared-window bridge without opening a camera or native window."""

import json
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

import app
from desktop_window import DesktopSession
from rhythm_game import RhythmRound


class DesktopWindowTests(unittest.TestCase):
    def test_python_loop_publishes_shared_ui_and_responds_to_controls(self):
        camera = Mock()
        camera.isOpened.return_value = True
        camera.get.return_value = 30
        camera.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        audio = Mock(enabled=True, muted=False, error_message=None)
        detector = Mock()
        detector.detect_for_video.return_value = SimpleNamespace(hand_landmarks=[], handedness=[])
        snapshots = []
        presentation = DesktopSession(lambda **_kwargs: None)
        keys = iter((ord("1"), ord("h"), ord("q")))

        def publish(snapshot, preview):
            self.assertEqual(preview.shape, (480, 640, 3))
            json.dumps(snapshot, allow_nan=False)
            snapshots.append(snapshot)

        with (
            patch("app.cv2.VideoCapture", return_value=camera),
            patch("app.AudioEngine", return_value=audio),
            patch("app.create_hand_landmarker") as create_model,
            patch("app.cv2.namedWindow") as old_window,
            patch("app.cv2.imshow") as old_display,
            patch.object(presentation, "_publish", side_effect=publish),
            patch.object(presentation, "_read_key", side_effect=lambda: next(keys)),
            patch("app.time.monotonic", return_value=100),
        ):
            create_model.return_value.__enter__.return_value = detector
            app.main(presentation=presentation)

        self.assertEqual([item["screen"] for item in snapshots], ["menu", "challenge", "challenge"])
        self.assertFalse(snapshots[1]["help"])
        self.assertTrue(snapshots[2]["help"])
        self.assertEqual(snapshots[1]["countdown"], 3)
        self.assertEqual(snapshots[1]["scene"]["nodes"], [])
        old_window.assert_not_called()
        old_display.assert_not_called()
        camera.release.assert_called_once()
        audio.close.assert_called_once()

    def test_resize_preserves_normalized_geometry_and_updates_fall_speed(self):
        round_ = RhythmRound(started_at=0)
        node = app.create_challenge_node(round_.chart[0], round_, 1280, 800, 4, [])
        old_x_ratio = node.x / 1280
        effects = [app.HitEffect((640, 400), (255, 0, 0), 4, "HIT")]
        app.resize_stage_geometry([node], effects, (1280, 800), (1728, 1000), 2)
        self.assertAlmostEqual(node.x / 1728, old_x_ratio)
        self.assertEqual(node.radius, app.node_radius_for_frame(1728, 1000))
        self.assertAlmostEqual(node.speed, (300 - node.radius) / 2)
        self.assertEqual(effects[0].position, (864, 500))
        # Resizing does not change the scheduled beat or the chart identity.
        self.assertEqual(node.target_time, round_.target_time(round_.chart[0]))
        self.assertEqual(node.chart_index, 0)

    def test_benchmark_command_saves_a_privacy_safe_report(self):
        camera = Mock()
        camera.isOpened.return_value = True
        camera.get.return_value = 30
        camera.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        audio = Mock(enabled=True, muted=False, error_message=None)
        detector = Mock()
        detector.detect_for_video.return_value = SimpleNamespace(hand_landmarks=[], handedness=[])
        presentation = DesktopSession(lambda **_kwargs: None)
        keys = iter((ord("b"), ord("b"), ord("q")))

        with (
            patch("app.cv2.VideoCapture", return_value=camera),
            patch("app.AudioEngine", return_value=audio),
            patch("app.create_hand_landmarker") as create_model,
            patch.object(presentation, "_read_key", side_effect=lambda: next(keys)),
            patch("app.save_benchmark_report", return_value=(Path("report.json"), Path("report.md"))) as save_report,
            patch("app.time.monotonic", return_value=100),
        ):
            create_model.return_value.__enter__.return_value = detector
            app.main(presentation=presentation)

        save_report.assert_called_once()
        report = save_report.call_args.args[0]
        self.assertEqual(report["frame_count"], 1)
        self.assertEqual(report["metadata"]["renderer"], "Shared HTML/CSS/Canvas")
        self.assertFalse(report["privacy"]["camera_images_saved"])
        self.assertFalse(report["privacy"]["landmark_coordinates_saved"])

    def test_bridge_keeps_only_latest_frame_and_validates_viewport(self):
        session = DesktopSession(lambda **_kwargs: None)
        preview = np.zeros((900, 1600, 3), dtype=np.uint8)
        session._publish({"clock": 1}, preview)
        session._publish({"clock": 2}, preview)
        frame = session.frame(-1)
        self.assertEqual(frame["snapshot"]["clock"], 2)
        self.assertTrue(frame["preview"].startswith("data:image/jpeg;base64,"))
        session.viewport(1728, 1000)
        self.assertEqual(session._size(), (1728, 1000))
        with self.assertRaises(ValueError):
            session.viewport(float("nan"), 1000)
        session.stop()
        session._publish({"clock": 3}, preview)
        self.assertIsNone(session.frame(frame["sequence"]))

    def test_camera_worker_can_stop_and_restart(self):
        starts = []
        entered = threading.Event()

        def backend(presentation):
            starts.append(1)
            entered.set()
            presentation._stop_event.wait(1)

        session = DesktopSession(backend)
        for _ in range(2):
            entered.clear()
            session.start()
            self.assertTrue(entered.wait(1))
            session.start()  # A double click must not start another camera worker.
            session.stop()
            session._thread.join(1)
            self.assertFalse(session._thread.is_alive())
            self.assertEqual(session.frame(-1)["mode"], "idle")
        self.assertEqual(len(starts), 2)


if __name__ == "__main__":
    unittest.main()
