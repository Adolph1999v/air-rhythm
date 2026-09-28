"""Check camera preparation and model telemetry without opening devices."""

from types import SimpleNamespace
import unittest

import numpy as np

import app


class FakeCamera:
    def __init__(self):
        self.properties = {
            app.cv2.CAP_PROP_FRAME_WIDTH: 640.0,
            app.cv2.CAP_PROP_FRAME_HEIGHT: 480.0,
            app.cv2.CAP_PROP_FPS: 30.0,
        }
        self.set_calls = []

    def set(self, property_id, value):
        self.set_calls.append((property_id, value))
        return True

    def get(self, property_id):
        return self.properties.get(property_id, 0.0)


class AppPipelineTests(unittest.TestCase):
    def test_camera_requests_a_responsive_capture_mode(self):
        camera = FakeCamera()
        configuration = app.configure_camera_capture(camera)

        self.assertIn(
            (app.cv2.CAP_PROP_FRAME_WIDTH, float(app.CAMERA_REQUEST_WIDTH)),
            camera.set_calls,
        )
        self.assertIn(
            (app.cv2.CAP_PROP_FRAME_HEIGHT, float(app.CAMERA_REQUEST_HEIGHT)),
            camera.set_calls,
        )
        self.assertIn(
            (app.cv2.CAP_PROP_FPS, app.CAMERA_REQUEST_FPS),
            camera.set_calls,
        )
        self.assertEqual(configuration["width"], 640.0)
        self.assertEqual(configuration["height"], 480.0)
        self.assertEqual(configuration["fps"], 30.0)

    def test_camera_frames_are_downscaled_without_upscaling(self):
        large_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        small_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        resized = app.resize_frame_for_processing(large_frame)
        unchanged = app.resize_frame_for_processing(small_frame)

        self.assertEqual(resized.shape, (720, 1280, 3))
        self.assertIs(unchanged, small_frame)

    def test_handedness_score_is_not_mislabeled_as_tracking_accuracy(self):
        result = SimpleNamespace(
            handedness=[
                [SimpleNamespace(category_name="Left", score=0.93)],
                [SimpleNamespace(category_name="Right", score=1.4)],
                [],
            ]
        )
        self.assertEqual(app.handedness_confidences(result), (0.93, 1.0))


if __name__ == "__main__":
    unittest.main()
