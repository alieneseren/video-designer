"""
animator.py
===========
Timeline interpolation, procedural kinematics, walk cycles, breathing,
camera shakes, and spring physics for the Stickman Video Production Engine.
"""

import math
from typing import Tuple, Optional, Callable


def easing_elastic_out(p: float) -> float:
    """Comic style bouncy overshoot entrance (0.0 -> 1.15 -> 1.0)."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    return math.sin(-13.0 * (p + 1.0) * (math.pi / 2.0)) * math.pow(2.0, -10.0 * p) + 1.0


def easing_ease_in_out(p: float) -> float:
    """Smooth cubic hermite ease."""
    p = max(0.0, min(1.0, p))
    return p * p * (3.0 - 2.0 * p)


class MotionPath:
    """Calculates coordinates and transformations over time."""

    @staticmethod
    def linear_slide(
        t: float,
        t_start: float,
        t_end: float,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        easing_fn: Callable[[float], float] = easing_ease_in_out,
    ) -> Tuple[int, int]:
        if t <= t_start:
            return start_pos
        if t >= t_end:
            return end_pos
        p = (t - t_start) / max(0.001, t_end - t_start)
        ease_p = easing_fn(p)
        x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * ease_p)
        y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * ease_p)
        return (x, y)


class StickmanTimeline:
    """Manages scene time, framerate, and procedural physical oscillations."""

    def __init__(self, duration_sec: float, fps: int = 25):
        self.duration = duration_sec
        self.fps = fps
        self.total_frames = int(round(duration_sec * fps))

    def get_time(self, frame_idx: int) -> float:
        return frame_idx / float(self.fps)

    @staticmethod
    def breathe_offset(t: float, freq: float = 1.4, amp: float = 5.0) -> float:
        """Subtle idle breathing vertical oscillation."""
        return math.sin(t * freq * math.pi * 2.0) * amp

    @staticmethod
    def walk_cycle(
        t: float,
        speed: float = 2.4,
        step_height: float = 10.0,
        tilt_amp: float = 3.5,
    ) -> Tuple[float, float, float]:
        """
        Returns (bob_y, tilt_degrees, walk_phase).
        - bob_y: vertical bouncing on each footstep.
        - tilt_degrees: gentle side-to-side body sway.
        - walk_phase: normalized 0.0 to 1.0 phase for leg/arm kinematics.
        """
        phase = (t * speed) % 1.0
        bob_y = -abs(math.sin(phase * math.pi * 2.0)) * step_height
        tilt = math.sin(phase * math.pi * 2.0) * tilt_amp
        return (bob_y, tilt, phase)

    @staticmethod
    def shock_jitter(t: float, t_trigger: float, duration: float = 0.5, amp: float = 8.0) -> Tuple[int, int]:
        """Earthquake comic vibration on sudden panic or alert."""
        if t < t_trigger or t > (t_trigger + duration):
            return (0, 0)
        progress = (t - t_trigger) / duration
        decay = 1.0 - progress
        jx = int(math.sin(t * 75.0) * amp * decay)
        jy = int(math.cos(t * 60.0) * amp * decay)
        return (jx, jy)

    @staticmethod
    def bubble_spring_scale(t: float, t_start: float = 0.4, pop_duration: float = 0.45) -> float:
        """Returns bouncy scale factor from 0.0 to 1.0 for dialogue balloons."""
        if t < t_start:
            return 0.0
        progress = (t - t_start) / max(0.01, pop_duration)
        if progress >= 1.0:
            return 1.0
        return easing_elastic_out(progress)
