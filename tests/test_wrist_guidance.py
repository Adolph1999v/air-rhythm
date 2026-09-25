"""Camera-free checks for the desktop wrist-framing notice."""

from types import SimpleNamespace
import unittest

from wrist_guidance import WristVisibilityMonitor


class NamedHand(list):
    def __init__(self, identity: str, wrist_y: float):
        super().__init__([SimpleNamespace(y=wrist_y)])
        self.identity = identity


class WristVisibilityTests(unittest.TestCase):
    def test_warning_appears_clears_and_repeats(self):
        monitor = WristVisibilityMonitor()
        self.assertFalse(monitor.update([NamedHand("Left", 0.5)], 1.0))
        self.assertFalse(monitor.update([NamedHand("Left", 0.91)], 1.03))
        self.assertTrue(monitor.update([NamedHand("Left", 0.92)], 1.06))
        self.assertTrue(monitor.update([NamedHand("Left", 0.7)], 1.09))
        self.assertFalse(monitor.update([NamedHand("Left", 0.7)], 1.12))
        self.assertFalse(monitor.update([NamedHand("Left", 0.92)], 1.15))
        self.assertTrue(monitor.update([NamedHand("Left", 0.92)], 1.18))

    def test_low_hand_dropout_keeps_warning_until_safe_return(self):
        monitor = WristVisibilityMonitor()
        self.assertFalse(monitor.update([NamedHand("Left", 0.8)], 1.0))
        self.assertFalse(monitor.update([], 1.08))
        self.assertTrue(monitor.update([], 1.13))
        self.assertFalse(monitor.update([NamedHand("Left", 0.5)], 1.16))

    def test_either_wrist_can_trigger_but_missing_notice_eventually_expires(self):
        monitor = WristVisibilityMonitor()
        hands = [NamedHand("Left", 0.5), NamedHand("Right", 0.93)]
        monitor.update(hands, 1.0)
        self.assertTrue(monitor.update(hands, 1.03))
        self.assertTrue(monitor.update([], 1.5))
        self.assertFalse(monitor.update([], 3.1))


if __name__ == "__main__":
    unittest.main()
