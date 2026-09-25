"""Reusable OpenCV interface components for Air Rhythm.

The functions in this file only draw on a frame.  They do not open a camera,
run a hand model, or play audio, which keeps the visual layer easy to reuse
and test.
"""

from collections.abc import Mapping, Sequence
import math
from typing import Any

import cv2


# OpenCV colours use blue, green, red (BGR) order.
INK = (5, 3, 2)
TEXT_SHADOW = (20, 13, 8)
PANEL = (18, 12, 5)
PANEL_LIGHT = (56, 43, 30)
WHITE = (255, 248, 245)
MUTED = (197, 182, 168)
CYAN = (255, 228, 97)
BLUE = (255, 137, 44)
MAGENTA = (229, 72, 255)
GREEN = (112, 246, 104)
GOLD = (122, 224, 255)
RED = (90, 95, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX

DEFAULT_CONTROLS = (
    ("SPACE", "Start / replay"),
    ("1 / 2", "Challenge / free play"),
    ("R", "Restart current mode"),
    ("B", "Start / save benchmark"),
    ("P", "Input inset privacy"),
    ("M", "Mute"),
    ("D", "CV / ML details"),
    ("T / ESC", "Return to title"),
    ("Q", "Quit"),
)


def _frame_size(frame) -> tuple[int, int]:
    """Return width and height, with a clear error for an unusable frame."""
    if frame is None or not hasattr(frame, "shape") or len(frame.shape) < 2:
        raise ValueError("frame must be an OpenCV image")
    height, width = frame.shape[:2]
    if width < 1 or height < 1:
        raise ValueError("frame must contain at least one pixel")
    return width, height


def _ui_scale(frame) -> float:
    """Scale spacing and text for both 4:3 and 16:9 camera frames."""
    width, height = _frame_size(frame)
    return max(0.32, min(1.6, min(width / 1280.0, height / 720.0)))


def _clamp01(value: float) -> float:
    """Keep a progress value inside 0 to 1, including invalid numbers."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return max(0.0, min(1.0, number))


def _safe_int(value: Any, default: int = 0) -> int:
    """Turn a display value into an integer without breaking the UI."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return int(number) if math.isfinite(number) else default


def _clip_rect(
    frame,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Clip a rectangle to the visible image and preserve point order."""
    width, height = _frame_size(frame)
    left, right = sorted((int(top_left[0]), int(bottom_right[0])))
    top, bottom = sorted((int(top_left[1]), int(bottom_right[1])))
    left = max(0, min(width - 1, left))
    right = max(left, min(width - 1, right))
    top = max(0, min(height - 1, top))
    bottom = max(top, min(height - 1, bottom))
    return left, top, right, bottom


def _filled_round_rect(
    image,
    rect: tuple[int, int, int, int],
    color: tuple[int, int, int],
    radius: int,
) -> None:
    """Draw a filled rounded rectangle using basic OpenCV shapes."""
    left, top, right, bottom = rect
    radius = max(0, min(int(radius), (right - left) // 2, (bottom - top) // 2))
    if radius <= 1:
        cv2.rectangle(image, (left, top), (right, bottom), color, -1)
        return
    cv2.rectangle(image, (left + radius, top), (right - radius, bottom), color, -1)
    cv2.rectangle(image, (left, top + radius), (right, bottom - radius), color, -1)
    for center in (
        (left + radius, top + radius),
        (right - radius, top + radius),
        (left + radius, bottom - radius),
        (right - radius, bottom - radius),
    ):
        cv2.circle(image, center, radius, color, -1, cv2.LINE_AA)


def _outline_round_rect(
    image,
    rect: tuple[int, int, int, int],
    color: tuple[int, int, int],
    radius: int,
) -> None:
    """Outline a rounded card like the browser interface."""
    left, top, right, bottom = rect
    radius = max(0, min(radius, (right - left) // 2, (bottom - top) // 2))
    if radius <= 1:
        cv2.rectangle(image, (left, top), (right, bottom), color, 1, cv2.LINE_AA)
        return
    cv2.line(image, (left + radius, top), (right - radius, top), color, 1, cv2.LINE_AA)
    cv2.line(image, (left + radius, bottom), (right - radius, bottom), color, 1, cv2.LINE_AA)
    cv2.line(image, (left, top + radius), (left, bottom - radius), color, 1, cv2.LINE_AA)
    cv2.line(image, (right, top + radius), (right, bottom - radius), color, 1, cv2.LINE_AA)
    for center, start in (
        ((left + radius, top + radius), 180),
        ((right - radius, top + radius), 270),
        ((right - radius, bottom - radius), 0),
        ((left + radius, bottom - radius), 90),
    ):
        cv2.ellipse(image, center, (radius, radius), 0, start, start + 90, color, 1, cv2.LINE_AA)


def fit_text_scale(
    text: str,
    max_width: int,
    preferred_scale: float,
    min_scale: float = 0.2,
    thickness: int = 1,
    font: int = FONT,
) -> float:
    """Return the largest useful text scale that fits a given width."""
    preferred = max(float(min_scale), float(preferred_scale))
    available = max(1, int(max_width))
    measured = cv2.getTextSize(str(text), font, preferred, max(1, thickness))[0][0]
    if measured <= available:
        return preferred
    return max(float(min_scale), preferred * available / max(1, measured))


def _ellipsize(
    text: str,
    max_width: int,
    scale: float,
    thickness: int,
    font: int,
) -> str:
    """Shorten text only when scaling alone cannot fit it."""
    result = str(text)
    if cv2.getTextSize(result, font, scale, thickness)[0][0] <= max_width:
        return result
    suffix = "..."
    while result and cv2.getTextSize(
        result + suffix, font, scale, thickness
    )[0][0] > max_width:
        result = result[:-1]
    return result + suffix if result else ""


def draw_text(
    frame,
    text: str,
    position: tuple[int, int],
    scale: float = 0.6,
    color: tuple[int, int, int] = WHITE,
    thickness: int = 1,
    *,
    align: str = "left",
    max_width: int | None = None,
    min_scale: float = 0.2,
    outline: bool = True,
    font: int = FONT,
) -> tuple[int, int, int, int]:
    """Draw fitted, outlined text and return its visible bounding box.

    ``position`` is the text baseline.  Alignment may be ``left``, ``center``,
    or ``right``.  The dark outline keeps words readable over camera footage.
    """
    width, height = _frame_size(frame)
    if align not in {"left", "center", "right"}:
        raise ValueError("align must be left, center, or right")

    value = str(text)
    chosen_scale = max(float(min_scale), float(scale))
    if max_width is not None:
        chosen_scale = fit_text_scale(
            value, max_width, chosen_scale, min_scale, thickness, font
        )
        value = _ellipsize(value, max(1, max_width), chosen_scale, thickness, font)
    (text_width, text_height), baseline = cv2.getTextSize(
        value, font, chosen_scale, max(1, thickness)
    )
    x, y = int(position[0]), int(position[1])
    if align == "center":
        x -= text_width // 2
    elif align == "right":
        x -= text_width
    x = max(0, min(max(0, width - text_width - 1), x))
    y = max(text_height + 1, min(height - max(1, baseline) - 1, y))

    # A border around tiny one-pixel glyphs looks like a duplicate character.
    # Small labels already sit on glass panels, so reserve the border for
    # prominent text that is thick enough to carry it cleanly.
    use_outline = outline and thickness >= 2
    if use_outline:
        cv2.putText(
            frame,
            value,
            (x, y),
            font,
            chosen_scale,
            TEXT_SHADOW,
            max(2, thickness + 1),
            cv2.LINE_AA,
        )
    cv2.putText(
        frame,
        value,
        (x, y),
        font,
        chosen_scale,
        color,
        max(1, thickness),
        cv2.LINE_AA,
    )
    return x, y - text_height, text_width, text_height + baseline


def draw_glass_panel(
    frame,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    *,
    accent: tuple[int, int, int] | None = CYAN,
    alpha: float = 0.78,
    radius: int | None = None,
) -> Any:
    """Draw a restrained glass surface for the generated performance stage."""
    rect = _clip_rect(frame, top_left, bottom_right)
    scale = _ui_scale(frame)
    corner_radius = max(2, int(14 * scale)) if radius is None else max(0, radius)
    overlay = frame.copy()
    _filled_round_rect(overlay, rect, PANEL, corner_radius)
    opacity = _clamp01(alpha)
    cv2.addWeighted(overlay, opacity, frame, 1.0 - opacity, 0, frame)
    left, top, right, bottom = rect
    border_color = accent if accent is not None else PANEL_LIGHT
    _outline_round_rect(frame, rect, border_color, corner_radius)
    return frame


def draw_glow_circle(
    frame,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int] = CYAN,
    pulse: float = 0.0,
) -> Any:
    """Draw a soft neon ring for countdowns and interactive highlights."""
    width, height = _frame_size(frame)
    radius = max(1, int(radius))
    pulse = _clamp01(pulse)
    center_x, center_y = int(center[0]), int(center[1])
    largest_extra = int(14 * (0.7 + pulse))
    outer_radius = radius + largest_extra + 8
    left = max(0, center_x - outer_radius)
    right = min(width, center_x + outer_radius + 1)
    top = max(0, center_y - outer_radius)
    bottom = min(height, center_y + outer_radius + 1)
    if left >= right or top >= bottom:
        return frame

    roi = frame[top:bottom, left:right]
    local_center = (center_x - left, center_y - top)
    for extra, opacity in ((14, 0.08), (8, 0.13), (3, 0.22)):
        overlay = roi.copy()
        cv2.circle(
            overlay,
            local_center,
            radius + int(extra * (0.7 + pulse)),
            color,
            max(2, extra // 2),
            cv2.LINE_AA,
        )
        cv2.addWeighted(overlay, opacity, roi, 1.0 - opacity, 0, roi)
    cv2.circle(frame, (center_x, center_y), radius, color, 2, cv2.LINE_AA)
    return frame


def draw_brand_badge(
    frame,
    subtitle: str = "AI HAND-TRACKED MUSIC",
    tech: str = "OpenCV + MediaPipe",
) -> Any:
    """Draw a compact project badge with its computer-vision technology."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    margin = max(5, int(18 * scale))
    panel_width = min(width - margin * 2, max(int(245 * scale), int(width * 0.25)))
    panel_height = min(height - margin * 2, max(int(56 * scale), 34))
    right = margin + max(1, panel_width)
    bottom = margin + max(1, panel_height)
    draw_glass_panel(frame, (margin, margin), (right, bottom), accent=CYAN, alpha=0.72)
    text_x = margin + max(7, int(13 * scale))
    first_y = margin + max(14, int(22 * scale))
    available = max(20, panel_width - max(14, int(25 * scale)))
    draw_text(
        frame, subtitle, (text_x, first_y), max(0.39, 0.58 * scale),
        CYAN, 1, max_width=available, min_scale=0.18,
    )
    second_y = min(bottom - 5, first_y + max(13, int(21 * scale)))
    draw_text(
        frame, tech, (text_x, second_y), max(0.32, 0.46 * scale),
        MUTED, 1, max_width=available, min_scale=0.16,
    )
    return frame


def _draw_background_tint(frame, opacity: float = 0.62) -> None:
    """Dim the stage with a neutral black overlay."""
    width, height = _frame_size(frame)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width - 1, height - 1), INK, -1)
    cv2.addWeighted(overlay, _clamp01(opacity), frame, 1.0 - _clamp01(opacity), 0, frame)


def _draw_shell(
    frame,
    hands: int,
    privacy_label: str,
    sound_label: str,
    controls: str,
) -> None:
    """Keep the desktop top bar and footer aligned with the browser stage."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    margin = max(8, int(30 * scale))
    brand_y = margin + max(13, int(17 * scale))
    mark_x = margin + max(5, int(7 * scale))
    mark_y = brand_y - max(5, int(6 * scale))
    arm = max(4, int(8 * scale))
    cv2.line(frame, (mark_x - arm, mark_y), (mark_x + arm, mark_y), CYAN, 2, cv2.LINE_AA)
    cv2.line(frame, (mark_x, mark_y - arm), (mark_x, mark_y + arm), CYAN, 2, cv2.LINE_AA)
    draw_text(
        frame, "AIR RHYTHM", (margin + max(20, int(29 * scale)), brand_y),
        max(0.33, 0.57 * scale), WHITE, 2,
        max_width=max(55, int(width * 0.25)), min_scale=0.20,
        font=cv2.FONT_HERSHEY_DUPLEX,
    )
    if width >= 700:
        draw_text(
            frame, "DESKTOP", (margin + max(175, int(205 * scale)), brand_y),
            max(0.20, 0.32 * scale), MUTED, 1,
            max_width=max(45, int(width * 0.11)), min_scale=0.14,
        )
        status = (
            f"INPUT {str(privacy_label).upper()}  |  "
            f"HANDS {max(0, _safe_int(hands))}/2  |  {str(sound_label).upper()}"
        )
        draw_text(
            frame, status, (width - margin, brand_y),
            max(0.20, 0.33 * scale), MUTED, 1, align="right",
            max_width=max(70, int(width * 0.43)), min_scale=0.14,
        )
    footer_y = height - max(8, int(20 * scale))
    cv2.line(
        frame, (margin, footer_y - max(14, int(20 * scale))),
        (width - margin, footer_y - max(14, int(20 * scale))),
        PANEL_LIGHT, 1, cv2.LINE_AA,
    )
    draw_text(
        frame, controls, (margin, footer_y), max(0.20, 0.32 * scale),
        MUTED, 1, max_width=max(45, int(width * 0.58)), min_scale=0.14,
    )


def draw_title_screen(
    frame,
    hand_count: int,
    privacy_label: str,
    sound_label: str,
    current_time: float,
    ready_progress: float | None = None,
) -> Any:
    """Draw the desktop menu in the browser's black-sky visual language."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    center_x = width // 2
    margin = max(8, int(30 * scale))
    _draw_background_tint(frame, 0.08)
    _draw_shell(
        frame, hand_count, privacy_label, sound_label,
        "1 CHALLENGE   2 FREE PLAY   H HELP   D TECHNICAL VIEW   Q QUIT",
    )

    draw_text(
        frame, "CAMERA READY  /  CHOOSE YOUR SET",
        (center_x, int(height * 0.28)), max(0.25, 0.46 * scale),
        CYAN, 1, align="center", max_width=max(60, int(width * 0.70)),
        min_scale=0.17,
    )
    heading = "MAKE THE MUSIC MOVE."
    draw_text(
        frame, heading, (center_x, int(height * 0.40)),
        fit_text_scale(
            heading, max(90, int(width * 0.82)), max(0.8, 2.25 * scale),
            0.40, max(2, int(3 * scale)), cv2.FONT_HERSHEY_DUPLEX,
        ),
        WHITE, max(2, int(3 * scale)), align="center",
        max_width=max(90, int(width * 0.82)), font=cv2.FONT_HERSHEY_DUPLEX,
    )
    draw_text(
        frame, "Touch falling circles with a fingertip.",
        (center_x, int(height * 0.49)), max(0.27, 0.51 * scale),
        MUTED, 1, align="center", max_width=max(70, int(width * 0.72)),
        min_scale=0.16,
    )
    draw_text(
        frame, "Move down or toward the camera for a stronger hit.",
        (center_x, int(height * 0.54)), max(0.26, 0.47 * scale),
        MUTED, 1, align="center", max_width=max(70, int(width * 0.72)),
        min_scale=0.16,
    )
    draw_text(
        frame, "BRING BOTH HANDS INTO CAMERA VIEW",
        (center_x, int(height * 0.59)), max(0.24, 0.38 * scale),
        WHITE, 1, align="center", max_width=max(60, int(width * 0.60)),
        min_scale=0.16,
    )

    progress = None if ready_progress is None else _clamp01(ready_progress)
    ready = progress is None or progress >= 1.0
    button_height = max(28, int(52 * scale))
    button_gap = max(6, int(12 * scale))
    primary_width = max(130, int(305 * scale))
    secondary_width = max(88, int(135 * scale))
    total_width = min(width - margin * 2, primary_width + secondary_width + button_gap)
    primary_width = min(primary_width, total_width - button_gap - secondary_width)
    button_left = max(margin, center_x - total_width // 2)
    button_top = int(height * 0.64)
    primary = (button_left, button_top, button_left + primary_width, button_top + button_height)
    _filled_round_rect(frame, primary, CYAN if ready else GOLD, max(6, int(12 * scale)))
    _outline_round_rect(frame, primary, WHITE if ready else GOLD, max(6, int(12 * scale)))
    draw_text(
        frame, "SPACE  START SONG" if ready else "PREPARING INPUT",
        ((primary[0] + primary[2]) // 2, button_top + button_height // 2 + max(4, int(6 * scale))),
        max(0.22, 0.44 * scale), TEXT_SHADOW, 2, align="center",
        max_width=max(40, primary_width - 14), min_scale=0.16,
    )
    secondary_left = primary[2] + button_gap
    secondary = (
        secondary_left, button_top, secondary_left + secondary_width,
        button_top + button_height,
    )
    _filled_round_rect(frame, secondary, PANEL, max(6, int(12 * scale)))
    _outline_round_rect(frame, secondary, PANEL_LIGHT, max(6, int(12 * scale)))
    draw_text(
        frame, "2  FREE PLAY",
        ((secondary[0] + secondary[2]) // 2, button_top + button_height // 2 + max(4, int(6 * scale))),
        max(0.20, 0.39 * scale), WHITE, 1, align="center",
        max_width=max(30, secondary_width - 10), min_scale=0.15,
    )
    if progress is not None and not ready:
        _draw_progress_bar(
            frame, primary[0] + 8, primary[3] - 5,
            primary[2] - 8, primary[3] - 3, progress,
        )

    draw_text(
        frame, "A short, hand-played version of Fur Elise",
        (center_x, int(height * 0.76)), max(0.22, 0.36 * scale),
        MUTED, 1, align="center", max_width=max(70, int(width * 0.67)),
        min_scale=0.15,
    )
    if width >= 1000:
        draw_text(
            frame, "MediaPipe pretrained landmarks + custom gesture / collision logic",
            (center_x, int(height * 0.82)), max(0.20, 0.32 * scale),
            MUTED, 1, align="center", max_width=max(90, int(width * 0.55)),
            min_scale=0.15,
        )
    return frame


def _draw_progress_bar(
    frame,
    left: int,
    top: int,
    right: int,
    bottom: int,
    progress: float,
) -> None:
    """Draw a clamped song progress line."""
    progress = _clamp01(progress)
    cv2.rectangle(frame, (left, top), (right, bottom), PANEL_LIGHT, -1, cv2.LINE_AA)
    filled_right = left + round((right - left) * progress)
    if filled_right > left:
        cv2.rectangle(frame, (left, top), (filled_right, bottom), CYAN, -1, cv2.LINE_AA)


def draw_game_hud(
    frame,
    hands: int,
    score: int,
    combo: int,
    progress: float,
    hits: int,
    misses: int,
    mode_label: str,
    song_label: str,
    privacy_label: str,
    sound_label: str,
    debug_info: Mapping[str, Any] | None = None,
) -> Any:
    """Draw the browser-style compact HUD at the upper left of the stage."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    margin = max(8, int(30 * scale))
    _draw_shell(
        frame, hands, privacy_label, sound_label,
        "1 CHALLENGE   2 FREE PLAY   H HELP   M MUTE   T MENU   B BENCHMARK",
    )
    left = margin
    top = max(margin + max(28, int(42 * scale)), int(height * 0.11))
    card_width = min(width - margin * 2, int(width * 0.43), int(440 * max(0.75, scale)))
    right = min(width - margin, left + max(170, card_width))
    bottom = min(height - margin, top + max(86, int(158 * scale)))
    draw_glass_panel(
        frame, (left, top), (right, bottom), accent=None,
        alpha=0.88, radius=max(8, int(16 * scale)),
    )
    pad = max(8, int(16 * scale))
    inside_left = left + pad
    inside_right = right - pad
    available = max(45, inside_right - inside_left)
    header_y = top + max(15, int(22 * scale))
    draw_text(
        frame, str(mode_label).upper(), (inside_left, header_y),
        max(0.22, 0.39 * scale), CYAN, 1,
        max_width=max(40, int(available * 0.42)), min_scale=0.15,
    )
    draw_text(
        frame, str(song_label).upper(), (inside_right, header_y),
        max(0.22, 0.39 * scale), WHITE, 1, align="right",
        max_width=max(40, int(available * 0.53)), min_scale=0.15,
    )

    stats = (
        ("SCORE", f"{max(0, _safe_int(score)):,}"),
        ("COMBO", str(max(0, _safe_int(combo)))),
        ("HITS", str(max(0, _safe_int(hits)))),
        ("MISSES", str(max(0, _safe_int(misses)))),
    )
    column_width = available / 4
    label_y = top + max(30, int(53 * scale))
    value_y = top + max(49, int(80 * scale))
    for index, (label, value) in enumerate(stats):
        x = round(inside_left + index * column_width)
        draw_text(
            frame, label, (x, label_y), max(0.19, 0.30 * scale),
            MUTED, 1, max_width=max(25, int(column_width - 6)), min_scale=0.13,
        )
        draw_text(
            frame, value, (x, value_y), max(0.33, 0.72 * scale),
            WHITE, max(1, int(2 * scale)),
            max_width=max(25, int(column_width - 6)), min_scale=0.17,
        )

    progress_top = top + max(58, int(103 * scale))
    _draw_progress_bar(
        frame, inside_left, progress_top, inside_right,
        progress_top + max(2, int(4 * scale)), progress,
    )
    guide_y = min(bottom - max(7, int(12 * scale)), progress_top + max(16, int(25 * scale)))
    draw_text(
        frame, "Touch circles with a fingertip. Follow note order for the best score.",
        (inside_left, guide_y), max(0.19, 0.31 * scale),
        MUTED, 1, max_width=available, min_scale=0.13,
    )

    if debug_info is not None:
        combined_debug = dict(debug_info)
        combined_debug.setdefault("hands", hands)
        draw_debug_overlay(
            frame, combined_debug,
            top_offset=bottom + max(6, int(12 * scale)),
        )
    return frame


def draw_countdown(
    frame,
    value: str | int,
    progress: float = 0.0,
    current_time: float = 0.0,
) -> Any:
    """Show a large browser-style countdown without a target-like ring."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    text = str(value).strip()
    if not text:
        return frame
    color = GREEN if text.upper().startswith("GO") else WHITE
    chosen = fit_text_scale(
        text, max(30, int(width * 0.55)), max(1.4, 5.2 * scale),
        0.55, max(3, int(5 * scale)), cv2.FONT_HERSHEY_DUPLEX,
    )
    thickness = max(3, int(5 * scale))
    (text_width, text_height), _ = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_DUPLEX, chosen, thickness,
    )
    center_x = width // 2
    baseline_y = int(height * 0.46) + text_height // 2
    origin = (max(0, center_x - text_width // 2), baseline_y)
    glow = frame.copy()
    cv2.putText(
        glow, text, origin, cv2.FONT_HERSHEY_DUPLEX, chosen,
        CYAN if color == WHITE else GREEN, thickness + max(5, int(15 * scale)),
        cv2.LINE_AA,
    )
    cv2.addWeighted(glow, 0.20, frame, 0.80, 0, frame)
    cv2.putText(
        frame, text, origin, cv2.FONT_HERSHEY_DUPLEX, chosen,
        color, thickness, cv2.LINE_AA,
    )
    return frame


def draw_tracking_warning(
    frame,
    inset_bounds: tuple[int, int, int, int],
) -> Any:
    """Place the same wrist-framing hint above the live camera inset."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    _, inset_top, inset_right, _ = inset_bounds
    margin = max(5, int(12 * scale))
    card_width = min(width - margin * 2, max(int(305 * scale), int(width * 0.26)))
    card_height = max(43, int(62 * scale))
    bottom = max(margin + card_height, inset_top - max(5, int(10 * scale)))
    left = max(margin, inset_right - card_width)
    right = min(width - margin, left + card_width)
    top = max(margin, bottom - card_height)
    draw_glass_panel(
        frame, (left, top), (right, bottom),
        accent=GOLD, alpha=0.96, radius=max(5, int(11 * scale)),
    )
    icon_x = left + max(12, int(18 * scale))
    icon_y = (top + bottom) // 2
    icon_radius = max(7, int(11 * scale))
    cv2.circle(frame, (icon_x, icon_y), icon_radius, GOLD, -1, cv2.LINE_AA)
    draw_text(
        frame, "!", (icon_x, icon_y + max(4, int(5 * scale))),
        max(0.24, 0.43 * scale), TEXT_SHADOW, 2, align="center",
        max_width=icon_radius * 2, min_scale=0.20,
    )
    message_x = left + max(28, int(36 * scale))
    message_width = max(30, right - message_x - max(5, int(9 * scale)))
    for line, baseline in (
        ("Keep your whole hand and wrist", icon_y - max(2, int(4 * scale))),
        ("visible in the camera.", icon_y + max(9, int(13 * scale))),
    ):
        draw_text(
            frame, line, (message_x, baseline),
            max(0.29, 0.39 * scale), GOLD, 1,
            max_width=message_width, min_scale=0.22,
        )
    return frame


def draw_benchmark_status(
    frame,
    summary: Mapping[str, Any] | None = None,
    *,
    notice: str | None = None,
) -> Any:
    """Draw a compact recording badge without exposing camera information."""
    info = dict(summary or {})
    active = bool(info.get("active"))
    if not active and not notice:
        return frame

    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    margin = max(5, int(14 * scale))
    panel_width = min(
        width - margin * 2,
        max(160, int(300 * scale)),
    )
    panel_height = max(28, int((78 if active else 42) * scale))
    top = max(margin, int(height * 0.12))
    bottom = min(height - margin, top + panel_height)
    right = min(width - margin, margin + panel_width)
    accent = RED if active else GREEN
    draw_glass_panel(
        frame,
        (margin, top),
        (right, bottom),
        accent=accent,
        alpha=0.68,
        radius=max(8, int(18 * scale)),
    )

    text_left = margin + max(9, int(16 * scale))
    text_width = max(30, right - text_left - max(7, int(12 * scale)))
    first_y = top + max(14, int(24 * scale))
    if not active:
        draw_text(
            frame,
            str(notice),
            (text_left, first_y),
            max(0.23, 0.39 * scale),
            accent,
            1,
            max_width=text_width,
            min_scale=0.15,
        )
        return frame

    elapsed = max(0.0, float(info.get("elapsed_seconds", 0.0) or 0.0))
    frames = max(0, _safe_int(info.get("frames", 0)))
    draw_text(
        frame,
        f"BENCHMARK REC  {elapsed:05.1f}s  |  {frames} FRAMES",
        (text_left, first_y),
        max(0.22, 0.38 * scale),
        RED,
        1,
        max_width=text_width,
        min_scale=0.14,
    )
    average_fps = info.get("average_fps")
    fps_text = (
        "--"
        if not isinstance(average_fps, (int, float)) or not math.isfinite(average_fps)
        else f"{average_fps:.1f}"
    )
    second_y = min(bottom - 5, first_y + max(13, int(22 * scale)))
    draw_text(
        frame,
        f"AVG {fps_text} FPS  |  SLOW {max(0, _safe_int(info.get('slow_frames')))}  |  "
        f"DROP~ {max(0, _safe_int(info.get('estimated_dropped_frames')))}  |  "
        f"AUDIO {max(0, _safe_int(info.get('audio_samples')))}",
        (text_left, second_y),
        max(0.18, 0.31 * scale),
        MUTED,
        1,
        max_width=text_width,
        min_scale=0.12,
    )
    return frame


def draw_results(
    frame,
    *,
    score: int,
    completion: float,
    rank: str,
    perfect: int,
    great: int,
    good: int,
    misses: int,
    max_combo: int,
    basic_hits: int = 0,
    song_label: str = "Song challenge",
    replay_hint: str = "Press R to replay",
    hand_count: int = 0,
    privacy_label: str = "Camera",
    sound_label: str = "Sound on",
) -> Any:
    """Draw the browser's open, centered end-of-song summary."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    center_x = width // 2
    _draw_background_tint(frame, 0.16)
    _draw_shell(
        frame, hand_count, privacy_label, sound_label,
        "R / SPACE REPLAY   T TITLE   H HELP   Q QUIT",
    )
    try:
        completion_value = float(completion)
    except (TypeError, ValueError):
        completion_value = 0.0
    if not math.isfinite(completion_value):
        completion_value = 0.0
    completion_value = max(0.0, min(100.0, completion_value))

    draw_text(
        frame, "SONG COMPLETE", (center_x, int(height * 0.28)),
        max(0.28, 0.48 * scale), CYAN, 1, align="center",
        max_width=max(60, int(width * 0.66)), min_scale=0.17,
    )
    rank_text = f"RANK {str(rank).upper()[:3] or '-'}"
    draw_text(
        frame, rank_text, (center_x, int(height * 0.43)),
        fit_text_scale(
            rank_text, max(70, int(width * 0.68)),
            max(1.0, 2.8 * scale), 0.42, max(2, int(4 * scale)),
            cv2.FONT_HERSHEY_DUPLEX,
        ),
        WHITE, max(2, int(4 * scale)), align="center",
        max_width=max(70, int(width * 0.68)), font=cv2.FONT_HERSHEY_DUPLEX,
    )
    draw_text(
        frame, f"{max(0, _safe_int(score)):,} POINTS",
        (center_x, int(height * 0.52)), max(0.46, 0.90 * scale),
        CYAN, max(1, int(2 * scale)), align="center",
        max_width=max(55, int(width * 0.64)), min_scale=0.22,
    )
    caught = sum(max(0, _safe_int(value)) for value in (perfect, great, good, basic_hits))
    detail = (
        f"{caught} CIRCLES CAUGHT  |  {completion_value:.0f}% COMPLETION  |  "
        f"BEST COMBO {max(0, _safe_int(max_combo))}"
    )
    draw_text(
        frame, detail, (center_x, int(height * 0.60)),
        max(0.22, 0.38 * scale), MUTED, 1, align="center",
        max_width=max(70, int(width * 0.76)), min_scale=0.15,
    )
    draw_text(
        frame,
        f"PERFECT {max(0, _safe_int(perfect))}   GREAT {max(0, _safe_int(great))}   "
        f"GOOD {max(0, _safe_int(good))}   MISS {max(0, _safe_int(misses))}",
        (center_x, int(height * 0.65)),
        max(0.20, 0.33 * scale), GOLD, 1, align="center",
        max_width=max(70, int(width * 0.74)), min_scale=0.14,
    )

    button_height = max(27, int(51 * scale))
    button_top = int(height * 0.72)
    primary_width = max(130, int(250 * scale))
    secondary_width = max(95, int(150 * scale))
    gap = max(6, int(12 * scale))
    left = max(5, center_x - (primary_width + secondary_width + gap) // 2)
    primary = (left, button_top, left + primary_width, button_top + button_height)
    secondary = (
        primary[2] + gap, button_top,
        min(width - 5, primary[2] + gap + secondary_width),
        button_top + button_height,
    )
    _filled_round_rect(frame, primary, CYAN, max(6, int(12 * scale)))
    _outline_round_rect(frame, primary, WHITE, max(6, int(12 * scale)))
    draw_text(
        frame, "R / SPACE  PLAY AGAIN",
        ((primary[0] + primary[2]) // 2, button_top + button_height // 2 + max(4, int(6 * scale))),
        max(0.22, 0.40 * scale), TEXT_SHADOW, 2, align="center",
        max_width=max(30, primary_width - 10), min_scale=0.15,
    )
    _filled_round_rect(frame, secondary, PANEL, max(6, int(12 * scale)))
    _outline_round_rect(frame, secondary, PANEL_LIGHT, max(6, int(12 * scale)))
    draw_text(
        frame, "T  BACK TO MENU",
        ((secondary[0] + secondary[2]) // 2, button_top + button_height // 2 + max(4, int(6 * scale))),
        max(0.20, 0.34 * scale), WHITE, 1, align="center",
        max_width=max(30, secondary[2] - secondary[0] - 10), min_scale=0.15,
    )
    return frame


def draw_help_overlay(
    frame,
    controls: Sequence[tuple[str, str]] = DEFAULT_CONTROLS,
) -> Any:
    """Draw a compact control guide that pauses the active round safely."""
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    _draw_background_tint(frame, 0.66)
    left = max(5, int(width * 0.23))
    right = min(width - 6, int(width * 0.77))
    top = max(5, int(height * 0.15))
    bottom = min(height - 6, int(height * 0.85))
    draw_glass_panel(
        frame,
        (left, top),
        (right, bottom),
        accent=None,
        alpha=0.94,
        radius=max(12, int(26 * scale)),
    )
    center_x = width // 2
    available = max(25, right - left - max(20, int(50 * scale)))
    heading_y = top + max(20, int(40 * scale))
    draw_text(
        frame, "PAUSED / HOW TO PLAY", (center_x, heading_y), max(0.37, 0.66 * scale),
        CYAN, max(1, int(2 * scale)), align="center", max_width=available, min_scale=0.22,
    )
    guide_y = heading_y + max(18, int(32 * scale))
    draw_text(
        frame, "Show both hands; hit falling circles with your index fingertips.",
        (center_x, guide_y), max(0.29, 0.48 * scale), WHITE, 1,
        align="center", max_width=available, min_scale=0.18,
    )

    rows = list(controls)[:9]
    if rows:
        content_top = guide_y + max(18, int(48 * scale))
        content_bottom = bottom - max(21, int(42 * scale))
        use_two_columns = right - left >= 500 and bottom - top >= 350
        column_count = 2 if use_two_columns else 1
        rows_per_column = math.ceil(len(rows) / column_count)
        inner_left = left + max(12, int(40 * scale))
        inner_right = right - max(12, int(40 * scale))
        column_gap = max(8, int(24 * scale)) if use_two_columns else 0
        column_width = max(
            1,
            (inner_right - inner_left - column_gap * (column_count - 1))
            // column_count,
        )
        row_gap = max(18, min(max(23, int(58 * scale)), max(18, (content_bottom - content_top) // rows_per_column)))
        row_scale = max(0.24, 0.40 * scale)
        for index, item in enumerate(rows):
            try:
                key, action = item
            except (TypeError, ValueError):
                continue
            column = index // rows_per_column
            row = index % rows_per_column
            column_left = inner_left + column * (column_width + column_gap)
            column_right = min(inner_right, column_left + column_width)
            y = min(content_bottom, content_top + row * row_gap)
            key_x = column_left + max(7, int(13 * scale))
            action_x = column_left + max(58, int(100 * scale))
            draw_text(
                frame, str(key), (key_x, y), row_scale, CYAN, 1,
                max_width=max(25, action_x - key_x - 8), min_scale=0.14,
            )
            draw_text(
                frame, str(action), (action_x, y), row_scale, WHITE, 1,
                max_width=max(30, column_right - action_x - 10), min_scale=0.16,
            )
            if row < rows_per_column - 1:
                cv2.line(
                    frame,
                    (column_left, min(content_bottom, y + max(7, int(13 * scale)))),
                    (column_right, min(content_bottom, y + max(7, int(13 * scale)))),
                    PANEL_LIGHT,
                    1,
                    cv2.LINE_AA,
                )
    draw_text(
        frame, "H  RESUME PERFORMANCE", (center_x, bottom - max(7, int(18 * scale))),
        max(0.27, 0.44 * scale), CYAN, 1, align="center",
        max_width=available, min_scale=0.17,
    )
    return frame


def _format_confidence(value: Any) -> str | None:
    """Format a model confidence value when one is available."""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        numbers = []
        for item in value:
            try:
                number = float(item)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                numbers.append(number)
        if not numbers:
            return None
        value = sum(numbers) / len(numbers)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    percentage = number * 100.0 if 0.0 <= number <= 1.0 else number
    return f"{max(0.0, min(100.0, percentage)):.0f}%"


def draw_debug_overlay(
    frame,
    debug_info: Mapping[str, Any] | None = None,
    *,
    top_offset: int | None = None,
) -> Any:
    """Show truthful computer-vision details for a portfolio recording.

    MediaPipe supplies a pretrained hand-landmark model.  OpenCV handles the
    camera image and rendering.  Air Rhythm's own rules measure landmark
    motion and check a fingertip path against each circle.
    """
    info = dict(debug_info or {})
    width, height = _frame_size(frame)
    scale = _ui_scale(frame)
    margin = max(5, int(14 * scale))
    panel_width = min(width - margin * 2, max(145, int(280 * scale)))
    left = width - margin - panel_width
    top = max(margin, int(top_offset) if top_offset is not None else margin)
    line_gap = max(12, int(26 * scale))
    confidence = _format_confidence(info.get("confidence"))
    detected_hands = max(
        0, _safe_int(info.get("hands", info.get("hand_count", 0)))
    )
    landmark_count = max(
        0,
        _safe_int(
            info.get(
                "landmarks",
                info.get("landmark_count", detected_hands * 21),
            )
        ),
    )
    lines = [
        ("CV / ML PIPELINE", CYAN),
        (f"FPS  {info.get('fps', '--')}", WHITE),
        (f"Hands  {detected_hands}/2", WHITE),
        (f"Landmarks  {landmark_count}", WHITE),
    ]
    if confidence is not None:
        lines.append((f"Mean hand-class confidence  {confidence}", GREEN))
    if info.get("capture_ms") is not None:
        lines.append((f"Background camera read  {info['capture_ms']} ms", WHITE))
    if info.get("camera_wait_ms") is not None:
        lines.append((f"Main-loop camera wait  {info['camera_wait_ms']} ms", WHITE))
    if info.get("preprocessing_ms") is not None:
        lines.append((f"Camera preparation  {info['preprocessing_ms']} ms", WHITE))
    if info.get("inference_ms") is not None:
        lines.append((f"Inference  {info['inference_ms']} ms", WHITE))
    if info.get("update_ms") is not None:
        lines.append((f"Game update  {info['update_ms']} ms", WHITE))
    if info.get("render_ms") is not None:
        lines.append((f"Rendering  {info['render_ms']} ms", WHITE))
    if info.get("frame_ms") is not None:
        lines.append((f"Frame pipeline  {info['frame_ms']} ms", WHITE))
    if info.get("gesture"):
        lines.append((f"Motion rule  {info['gesture']}", GOLD))
    lines.extend(
        (
            ("MediaPipe: pretrained landmark model", MUTED),
            ("OpenCV: camera capture + rendering", MUTED),
            ("App logic: fingertip path collision", MUTED),
        )
    )
    panel_height = min(
        height - top - margin,
        max(30, max(37, int(24 * scale)) + line_gap * len(lines)),
    )
    if panel_height <= 3:
        return frame
    bottom = top + panel_height
    draw_glass_panel(frame, (left, top), (width - margin, bottom), accent=CYAN, alpha=0.72)
    text_x = left + max(8, int(14 * scale))
    available = max(20, width - margin - text_x - max(6, int(10 * scale)))
    first_y = top + max(13, int(22 * scale))
    for index, (line, color) in enumerate(lines):
        y = first_y + index * line_gap
        if y > bottom - 5:
            break
        draw_text(
            frame, line, (text_x, y), max(0.24, 0.42 * scale), color, 1,
            max_width=available, min_scale=0.15,
        )
    return frame


__all__ = [
    "BLUE",
    "CYAN",
    "DEFAULT_CONTROLS",
    "FONT",
    "GOLD",
    "GREEN",
    "INK",
    "MAGENTA",
    "MUTED",
    "PANEL",
    "PANEL_LIGHT",
    "RED",
    "TEXT_SHADOW",
    "WHITE",
    "draw_brand_badge",
    "draw_benchmark_status",
    "draw_countdown",
    "draw_debug_overlay",
    "draw_game_hud",
    "draw_glass_panel",
    "draw_glow_circle",
    "draw_help_overlay",
    "draw_results",
    "draw_text",
    "draw_tracking_warning",
    "draw_title_screen",
    "fit_text_scale",
]
