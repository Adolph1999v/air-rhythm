"""Camera-framing guidance based on visible hand wrist landmarks."""

from dataclasses import dataclass
import math


WRIST_WARNING_Y = 0.88
WRIST_CLEAR_Y = 0.82
LOW_WRIST_Y = 0.78
DROPOUT_WARNING_SECONDS = 0.12
MISSING_HAND_SECONDS = 2.0


@dataclass
class _Observation:
    last_seen: float
    low: bool = False
    warning: bool = False
    near_edge_frames: int = 0
    clear_frames: int = 0


class WristVisibilityMonitor:
    """Warn when a wrist nears the lower edge or vanishes from a low pose.

    This is a framing hint, not proof that MediaPipe can see the entire wrist.
    """

    def __init__(self) -> None:
        self._observations: dict[str, _Observation] = {}

    def update(self, hands, now: float) -> bool:
        seen: set[str] = set()
        for index, hand in enumerate(hands):
            identity = str(getattr(hand, "identity", None) or f"Hand-{index}")
            seen.add(identity)
            observation = self._observations.setdefault(identity, _Observation(now))
            observation.last_seen = now
            try:
                wrist_y = float(hand[0].y)
            except (AttributeError, IndexError, TypeError, ValueError):
                wrist_y = math.nan
            valid = math.isfinite(wrist_y)
            observation.low = valid and wrist_y >= LOW_WRIST_Y
            near_edge = not valid or wrist_y >= (
                WRIST_CLEAR_Y if observation.warning else WRIST_WARNING_Y
            )
            if near_edge:
                observation.near_edge_frames += 1
                observation.clear_frames = 0
                if observation.near_edge_frames >= 2:
                    observation.warning = True
            else:
                observation.clear_frames += 1
                observation.near_edge_frames = 0
                if observation.clear_frames >= 2:
                    observation.warning = False

        for identity, observation in list(self._observations.items()):
            if identity in seen:
                continue
            missing_for = now - observation.last_seen
            if missing_for > MISSING_HAND_SECONDS:
                del self._observations[identity]
            elif observation.low and missing_for >= DROPOUT_WARNING_SECONDS:
                observation.warning = True
        return any(observation.warning for observation in self._observations.values())

    def reset(self) -> None:
        self._observations.clear()
