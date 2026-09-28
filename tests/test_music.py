"""Checks the scheduled melody and sound bank's pitch coverage."""

import unittest

from music import (
    ALL_PITCHES,
    INSTRUMENTS,
    MELODY_NOTES,
    MELODY_STEP_SECONDS,
)


class MusicDataTests(unittest.TestCase):
    def test_scheduled_melody_matches_the_simplified_phrase(self):
        phrase = MELODY_NOTES
        self.assertEqual(phrase[:9], (76, 75, 76, 75, 76, 71, 74, 72, 69))
        self.assertEqual(phrase[-4:], (64, 72, 71, 69))

    def test_preloaded_pitches_cover_both_modes_and_preview_timings(self):
        self.assertTrue(set(MELODY_NOTES).issubset(ALL_PITCHES))
        self.assertTrue(all(item.freestyle_note in ALL_PITCHES for item in INSTRUMENTS))
        self.assertEqual(len(MELODY_NOTES), len(MELODY_STEP_SECONDS))
        self.assertTrue(all(seconds > 0 for seconds in MELODY_STEP_SECONDS))

if __name__ == "__main__":
    unittest.main()
