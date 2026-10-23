import math
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont

def solve_ik(p1: Tuple[float, float], p2: Tuple[float, float], l1: float, l2: float, bend_positive: bool = True) -> Tuple[float, float]:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.hypot(dx, dy)
    dist = min(max(dist, 1e-4), l1 + l2 - 1e-3)
    base_angle = math.atan2(dy, dx)
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist)
    cos_a = max(-1.0, min(1.0, cos_a))
    angle_a = math.acos(cos_a)
    knee_angle = base_angle + (angle_a if bend_positive else -angle_a)
    kx = p1[0] + l1 * math.cos(knee_angle)
    ky = p1[1] + l1 * math.sin(knee_angle)
    return (kx, ky)

def draw_capsule_segment(draw: ImageDraw.Draw, p1: Tuple[float, float], p2: Tuple[float, float], radius: float, fill_color: Tuple[int, ...], border_color: Tuple[int, ...], stroke_w: int = 5):
    # Outer border
    draw.line([p1, p2], fill=border_color, width=int(2 * radius + stroke_w * 2))
    draw.ellipse([(p1[0] - radius - stroke_w, p1[1] - radius - stroke_w), (p1[0] + radius + stroke_w, p1[1] + radius + stroke_w)], fill=border_color)
    draw.ellipse([(p2[0] - radius - stroke_w, p2[1] - radius - stroke_w), (p2[0] + radius + stroke_w, p2[1] + radius + stroke_w)], fill=border_color)
    # Inner fill
    draw.line([p1, p2], fill=fill_color, width=int(2 * radius))
    draw.ellipse([(p1[0] - radius, p1[1] - radius), (p1[0] + radius, p1[1] + radius)], fill=fill_color)
    draw.ellipse([(p2[0] - radius, p2[1] - radius), (p2[0] + radius, p2[1] + radius)], fill=fill_color)

def test_rig():
    img = Image.new("RGBA", (800, 900), (245, 247, 250, 255))
    draw = ImageDraw.Draw(img)

    # Test drawing a volumetric character leg & torso
    hip = (400, 450)
    ankle = (480, 750)
    knee = solve_ik(hip, ankle, 150, 150, bend_positive=True)

    draw_capsule_segment(draw, hip, knee, 18, (30, 41, 59), (15, 23, 42), stroke_w=4)
    draw_capsule_segment(draw, knee, ankle, 15, (30, 41, 59), (15, 23, 42), stroke_w=4)

    img.save("output/stickman_demos/test_capsule_leg.png")
    print("Test capsule leg saved.")

if __name__ == "__main__":
    test_rig()
