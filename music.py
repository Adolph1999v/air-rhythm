"""Instrument identities and scheduled melody pitches, independent of the camera."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    """A node's sound, short on-screen label, color, and freestyle pitch."""

    key: str
    label: str
    color: tuple[int, int, int]
    freestyle_note: int


# OpenCV uses blue, green, red (BGR) color order. Freestyle pitches belong to
# the C-major pentatonic scale so they sound pleasant together in any order.
INSTRUMENTS = (
    Instrument("keys", "KEYS", (255, 110, 40), 72),       # C5
    Instrument("bell", "BELL", (40, 210, 255), 76),      # E5
    Instrument("pluck", "PLUCK", (80, 220, 80), 79),     # G5
    Instrument("marimba", "MALLET", (220, 80, 220), 81), # A5
)

MELODY_TITLE = "Fur Elise"

# Beethoven, WoO 59: the opening right-hand pitch line only, with no bass
# accompaniment. Source: Breitkopf & Hartel (1888), typeset by Stelios Samelis
# for Mutopia and marked Public Domain in the score and its LilyPond source.
# https://www.mutopiaproject.org/ftp/BeethovenLv/WoO59/fur_Elise_WoO59/fur_Elise_WoO59-let.pdf
# This simplified arrangement omits repeats. Preview timings include rests
# after longer notes; gameplay schedules these pitches on a fixed beat clock.
# Each pair is (MIDI pitch, seconds until the next preview note).
_MELODY_STEPS = (
    (76, 0.24), (75, 0.24),                              # E5 D#5 pickup
    (76, 0.24), (75, 0.24), (76, 0.24),                 # E5 D#5 E5
    (71, 0.24), (74, 0.24), (72, 0.24), (69, 0.72),     # B4 D5 C5 A4
    (60, 0.24), (64, 0.24), (69, 0.24), (71, 0.72),     # C4 E4 A4 B4
    (64, 0.24), (68, 0.24), (71, 0.24), (72, 0.72),     # E4 G#4 B4 C5
    (64, 0.24), (76, 0.24), (75, 0.24),                 # E4 E5 D#5
    (76, 0.24), (75, 0.24), (76, 0.24),                 # E5 D#5 E5
    (71, 0.24), (74, 0.24), (72, 0.24), (69, 0.72),     # B4 D5 C5 A4
    (60, 0.24), (64, 0.24), (69, 0.24), (71, 0.72),     # C4 E4 A4 B4
    (64, 0.24), (72, 0.24), (71, 0.24), (69, 1.20),     # E4 C5 B4 A4 ending
)

MELODY_NOTES: tuple[int, ...] = tuple(pitch for pitch, _ in _MELODY_STEPS)
MELODY_STEP_SECONDS: tuple[float, ...] = tuple(
    duration for _, duration in _MELODY_STEPS
)
ALL_PITCHES: tuple[int, ...] = tuple(
    sorted(set(MELODY_NOTES) | {instrument.freestyle_note for instrument in INSTRUMENTS})
)
