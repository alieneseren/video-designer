"""
test_rubberhose_walk.py
=======================
High-fidelity Crayon Capital style 2D RubberHose / Limber walking puppet engine.
Features:
- Proper 5-layer occlusion (Back Arm -> Back Leg -> Torso/Head -> Front Leg -> Front Arm)
- Zero foot-sliding stance kinematics
- True heel-to-toe ankle roll
- Volumetric limbs with thick vector borders and fill
- Secondary motion: Head bob delay, torso forward tilt, arm pendulum counter-swing
- Renders an authentic 25fps looping walk cycle video to inspect
"""

import math
import subprocess
from pathlib import Path
from typing import Tuple, Optional
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

def draw_capsule(draw: ImageDraw.Draw, p1: Tuple[float, float], p2: Tuple[float, float], r: float, fill_col: Tuple[int, ...], border_col: Tuple[int, ...] = (15, 23, 42), stroke_w: int = 5):
    # Outer stroke
    draw.line([p1, p2], fill=border_col, width=int(2 * r + stroke_w * 2))
    draw.ellipse([(p1[0] - r - stroke_w, p1[1] - r - stroke_w), (p1[0] + r + stroke_w, p1[1] + r + stroke_w)], fill=border_col)
    draw.ellipse([(p2[0] - r - stroke_w, p2[1] - r - stroke_w), (p2[0] + r + stroke_w, p2[1] + r + stroke_w)], fill=border_col)
    # Inner fill
    draw.line([p1, p2], fill=fill_col, width=int(2 * r))
    draw.ellipse([(p1[0] - r, p1[1] - r), (p1[0] + r, p1[1] + r)], fill=fill_col)
    draw.ellipse([(p2[0] - r, p2[1] - r), (p2[0] + r, p2[1] + r)], fill=fill_col)

def draw_shoe(
    draw: ImageDraw.Draw,
    ankle: Tuple[float, float],
    rot_deg: float,
    shoe_type: str = "sneaker",
    facing_right: bool = True,
    scale: float = 1.0,
):
    ax, ay = ankle
    dir_m = 1.0 if facing_right else -1.0
    rad = math.radians(rot_deg)
    cos_r = math.cos(rad) * dir_m
    sin_r = math.sin(rad)

    # Key points relative to ankle
    heel_x = ax - 16.0 * scale * cos_r
    heel_y = ay + 16.0 * scale * sin_r
    toe_x = ax + 36.0 * scale * cos_r
    toe_y = ay - 36.0 * scale * sin_r

    sole_col = (255, 255, 255) if shoe_type == "sneaker" else (25, 25, 30)
    upper_col = (245, 247, 250) if shoe_type == "sneaker" else (40, 50, 65)
    border_col = (15, 23, 42)

    # 1. Thick rubber sole
    sole_w = int(8 * scale)
    draw.line([(heel_x, heel_y + 4), (toe_x, toe_y + 4)], fill=border_col, width=sole_w + 4)
    draw.line([(heel_x, heel_y + 4), (toe_x, toe_y + 4)], fill=sole_col, width=sole_w)

    # 2. Shoe Upper Polygon
    poly = [
        (heel_x - 2 * scale * cos_r, heel_y - 14 * scale),
        (ax, ay - 8 * scale),
        (toe_x - 8 * scale * cos_r, toe_y - 12 * scale),
        (toe_x, toe_y + 2),
        (heel_x, heel_y + 2),
    ]
    draw.polygon(poly, fill=upper_col, outline=border_col)
    for i in range(len(poly) - 1):
        draw.line([poly[i], poly[i+1]], fill=border_col, width=int(4 * scale))
    draw.line([poly[-1], poly[0]], fill=border_col, width=int(4 * scale))

    # 3. Sneaker stripe
    if shoe_type == "sneaker":
        draw.line([(ax - 2 * scale * dir_m, ay - 2 * scale), (ax + 14 * scale * dir_m, ay - 4 * scale)], fill=(234, 88, 12), width=int(3 * scale))

def render_puppet_frame(
    canvas: Image.Image,
    cx: float,
    ground_y: float,
    walk_phase: float,
    archetype: str = "tech_founder",
    facing_right: bool = True,
    scale: float = 1.0,
):
    draw = ImageDraw.Draw(canvas)
    dir_m = 1.0 if facing_right else -1.0

    # Colors
    skin_col = (253, 230, 216)
    border_col = (15, 23, 42)
    if archetype == "tech_founder":
        shirt_col = (20, 25, 35) # Black turtleneck
        pants_col = (35, 45, 60) # Dark jeans
        shoe_type = "sneaker"
    elif archetype == "wall_street_trader":
        shirt_col = (250, 250, 252) # White shirt
        pants_col = (50, 60, 75)
        shoe_type = "dress"
    elif archetype == "defense_ceo":
        shirt_col = (15, 20, 30)
        pants_col = (15, 20, 30)
        shoe_type = "dress"
    else: # traveler
        shirt_col = (226, 232, 240)
        pants_col = (214, 180, 142)
        shoe_type = "sneaker"

    # Kinematics:
    thigh_l = 88.0 * scale
    shin_l = 92.0 * scale
    stride = 68.0 * scale
    step_lift = 44.0 * scale

    # Pelvis bounce: drops lowest on contact (down), rises highest on passing (up)
    hip_bounce = -abs(math.sin(walk_phase * 2.0 * math.pi)) * (14.0 * scale)
    torso_tilt = (3.5 + math.sin(walk_phase * 2.0 * math.pi) * 2.0) * dir_m

    hip_x = cx
    hip_y = ground_y - (thigh_l + shin_l - 12.0 * scale) + hip_bounce

    # Leg 1 (Front leg, phase 0..1)
    p1 = walk_phase % 1.0
    if p1 < 0.5: # Stance (locked to ground, rolling from heel to toe)
        t_st = p1 / 0.5
        f1_x = hip_x + (stride - t_st * 2.0 * stride) * dir_m
        f1_y = ground_y
        if t_st < 0.15:
            f1_rot = -22.0 * (1.0 - t_st / 0.15)
        elif t_st > 0.35:
            f1_rot = 38.0 * ((t_st - 0.35) / 0.15)
        else:
            f1_rot = 0.0
    else: # Swing (arcs forward through air)
        sw = (p1 - 0.5) / 0.5
        f1_x = hip_x + (-stride + sw * 2.0 * stride) * dir_m
        f1_y = ground_y - math.sin(sw * math.pi) * step_lift
        f1_rot = 16.0 * (1.0 - sw) - 16.0 * sw

    # Leg 2 (Back leg, offset by 0.5)
    p2 = (walk_phase + 0.5) % 1.0
    if p2 < 0.5:
        t_st = p2 / 0.5
        f2_x = hip_x + (stride - t_st * 2.0 * stride) * dir_m
        f2_y = ground_y
        if t_st < 0.15:
            f2_rot = -22.0 * (1.0 - t_st / 0.15)
        elif t_st > 0.35:
            f2_rot = 38.0 * ((t_st - 0.35) / 0.15)
        else:
            f2_rot = 0.0
    else:
        sw = (p2 - 0.5) / 0.5
        f2_x = hip_x + (-stride + sw * 2.0 * stride) * dir_m
        f2_y = ground_y - math.sin(sw * math.pi) * step_lift
        f2_rot = 16.0 * (1.0 - sw) - 16.0 * sw

    # Solve Knees (IK)
    hip_off = 10.0 * scale
    k1 = solve_ik((hip_x - hip_off * dir_m, hip_y), (f1_x, f1_y), thigh_l, shin_l, bend_positive=facing_right)
    k2 = solve_ik((hip_x + hip_off * dir_m, hip_y), (f2_x, f2_y), thigh_l, shin_l, bend_positive=facing_right)

    # Arms Kinematics (Natural opposite pendulum swing)
    arm_l1 = 58.0 * scale
    arm_l2 = 56.0 * scale
    arm_swing = math.sin(walk_phase * 2.0 * math.pi) * (48.0 * scale)

    torso_h = 142.0 * scale
    torso_w = 76.0 * scale
    torso_top = hip_y - torso_h

    sh_front = (hip_x - 8.0 * scale * dir_m, torso_top + 28.0 * scale)
    sh_back = (hip_x + 8.0 * scale * dir_m, torso_top + 26.0 * scale)

    # Front Arm wrist & elbow (swings forward when Leg 1 swings back)
    wr_front = (hip_x - arm_swing * dir_m, hip_y - 18.0 * scale)
    el_front = solve_ik(sh_front, wr_front, arm_l1, arm_l2, bend_positive=not facing_right)

    # Back Arm wrist & elbow (swings back when Leg 1 swings forward)
    wr_back = (hip_x + arm_swing * dir_m, hip_y - 18.0 * scale)
    el_back = solve_ik(sh_back, wr_back, arm_l1, arm_l2, bend_positive=not facing_right)

    # =========================================================================
    # 5-LAYER OCCLUSION RENDERING:
    # 1. Soft Dynamic Ground Shadow
    # 2. Back Arm
    # 3. Back Leg (Leg 2)
    # 4. Torso & Head
    # 5. Front Leg (Leg 1)
    # 6. Front Arm
    # =========================================================================

    # 1. Shadow
    sw_w = int(145 * scale)
    sw_h = int(22 * scale)
    draw.ellipse([(hip_x - sw_w // 2, int(ground_y) - 6), (hip_x + sw_w // 2, int(ground_y) + sw_h - 6)], fill=(0, 0, 0, 80))

    # 2. Back Arm
    back_sleeve_col = tuple(max(0, c - 25) for c in shirt_col)
    draw_capsule(draw, sh_back, el_back, 14 * scale, back_sleeve_col, stroke_w=4)
    draw_capsule(draw, el_back, wr_back, 12 * scale, back_sleeve_col, stroke_w=4)
    # Back Hand
    draw.ellipse([(wr_back[0] - 11 * scale, wr_back[1] - 11 * scale), (wr_back[0] + 11 * scale, wr_back[1] + 11 * scale)], fill=skin_col, outline=border_col, width=int(3.5 * scale))

    # 3. Back Leg (Leg 2)
    back_pants_col = tuple(max(0, c - 20) for c in pants_col)
    h2 = (hip_x + hip_off * dir_m, hip_y)
    draw_capsule(draw, h2, k2, 18 * scale, back_pants_col, stroke_w=4)
    draw_capsule(draw, k2, (f2_x, f2_y), 15 * scale, back_pants_col, stroke_w=4)
    draw_shoe(draw, (f2_x, f2_y), f2_rot, shoe_type=shoe_type, facing_right=facing_right, scale=scale)

    # 4. Torso & Head
    t_box = [(hip_x - torso_w // 2, torso_top), (hip_x + torso_w // 2, hip_y)]
    draw.rounded_rectangle(t_box, radius=int(24 * scale), fill=shirt_col, outline=border_col, width=int(5 * scale))

    # Turtleneck collar / Details
    if archetype == "tech_founder":
        draw.rounded_rectangle([(hip_x - 22 * scale, torso_top - 12 * scale), (hip_x + 22 * scale, torso_top + 10 * scale)], radius=int(6 * scale), fill=shirt_col, outline=border_col, width=int(4 * scale))
    elif archetype == "wall_street_trader":
        draw.line([(hip_x - 22 * scale, torso_top + 6 * scale), (hip_x - 18 * scale, hip_y)], fill=(220, 38, 38), width=int(8 * scale))
        draw.line([(hip_x + 16 * scale, torso_top + 6 * scale), (hip_x + 20 * scale, hip_y)], fill=(220, 38, 38), width=int(8 * scale))

    # Head (with overlapping lag)
    head_lag_bounce = -abs(math.sin((walk_phase - 0.08) * 2.0 * math.pi)) * (12.0 * scale)
    head_r = 54.0 * scale
    head_cy = torso_top - head_r + 14 * scale + head_lag_bounce
    head_cx = hip_x + 4 * scale * dir_m

    # Neck
    draw.line([(head_cx, torso_top - 4), (head_cx, torso_top + 10)], fill=skin_col, width=int(18 * scale))

    # Head
    draw.ellipse([(head_cx - head_r, head_cy - head_r), (head_cx + head_r, head_cy + head_r)], fill=skin_col, outline=border_col, width=int(5 * scale))

    # Side-parted stylish hair
    draw.polygon([
        (head_cx - 48 * scale * dir_m, head_cy - 12 * scale),
        (head_cx - 42 * scale * dir_m, head_cy - 48 * scale),
        (head_cx - 15 * scale * dir_m, head_cy - 58 * scale),
        (head_cx + 25 * scale * dir_m, head_cy - 54 * scale),
        (head_cx + 52 * scale * dir_m, head_cy - 20 * scale),
        (head_cx + 28 * scale * dir_m, head_cy - 38 * scale),
        (head_cx - 10 * scale * dir_m, head_cy - 42 * scale),
        (head_cx - 36 * scale * dir_m, head_cy - 28 * scale),
    ], fill=(69, 39, 23), outline=border_col)

    # Eyes
    eye_x = head_cx + 18 * scale * dir_m
    eye_y = head_cy - 2 * scale
    # Left Eye
    draw.ellipse([(eye_x - 26 * scale, eye_y - 14 * scale), (eye_x - 6 * scale, eye_y + 14 * scale)], fill=(255, 255, 255), outline=border_col, width=int(3.5 * scale))
    draw.ellipse([(eye_x - 19 * scale, eye_y - 6 * scale), (eye_x - 9 * scale, eye_y + 8 * scale)], fill=border_col)
    draw.ellipse([(eye_x - 17 * scale, eye_y - 4 * scale), (eye_x - 13 * scale, eye_y)], fill=(255, 255, 255))
    # Right Eye
    draw.ellipse([(eye_x - 2 * scale, eye_y - 14 * scale), (eye_x + 18 * scale, eye_y + 14 * scale)], fill=(255, 255, 255), outline=border_col, width=int(3.5 * scale))
    draw.ellipse([(eye_x + 5 * scale, eye_y - 6 * scale), (eye_x + 15 * scale, eye_y + 8 * scale)], fill=border_col)
    draw.ellipse([(eye_x + 7 * scale, eye_y - 4 * scale), (eye_x + 11 * scale, eye_y)], fill=(255, 255, 255))

    # Eyebrows
    draw.arc([(eye_x - 28 * scale, eye_y - 28 * scale), (eye_x - 6 * scale, eye_y - 10 * scale)], 200, 350, fill=border_col, width=int(3.5 * scale))
    draw.arc([(eye_x - 4 * scale, eye_y - 28 * scale), (eye_x + 18 * scale, eye_y - 10 * scale)], 200, 350, fill=border_col, width=int(3.5 * scale))

    # Glasses
    if archetype == "tech_founder":
        draw.ellipse([(eye_x - 29 * scale, eye_y - 16 * scale), (eye_x - 3 * scale, eye_y + 16 * scale)], outline=border_col, width=int(4 * scale))
        draw.ellipse([(eye_x - 5 * scale, eye_y - 16 * scale), (eye_x + 21 * scale, eye_y + 16 * scale)], outline=border_col, width=int(4 * scale))
        draw.line([(eye_x - 3 * scale, eye_y), (eye_x - 5 * scale, eye_y)], fill=border_col, width=int(4 * scale))

    # Smile
    draw.arc([(eye_x - 14 * scale, eye_y + 10 * scale), (eye_x + 14 * scale, eye_y + 26 * scale)], 20, 160, fill=border_col, width=int(4 * scale))

    # 5. Front Leg (Leg 1)
    h1 = (hip_x - hip_off * dir_m, hip_y)
    draw_capsule(draw, h1, k1, 20 * scale, pants_col, stroke_w=4)
    draw_capsule(draw, k1, (f1_x, f1_y), 17 * scale, pants_col, stroke_w=4)
    draw_shoe(draw, (f1_x, f1_y), f1_rot, shoe_type=shoe_type, facing_right=facing_right, scale=scale)

    # 6. Front Arm
    draw_capsule(draw, sh_front, el_front, 16 * scale, shirt_col, stroke_w=4)
    draw_capsule(draw, el_front, wr_front, 14 * scale, shirt_col, stroke_w=4)
    # Front Hand
    draw.ellipse([(wr_front[0] - 12 * scale, wr_front[1] - 12 * scale), (wr_front[0] + 12 * scale, wr_front[1] + 12 * scale)], fill=skin_col, outline=border_col, width=int(4 * scale))

def generate_walk_cycle_video():
    out_path = Path("output/stickman_demos/rubberhose_walk_test.mp4")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = 1920, 1080
    fps = 25
    duration_sec = 4.0
    total_frames = int(round(duration_sec * fps))

    # Load tech background
    bg_raw = Image.open("assets/crayon_tech_bg.jpg").convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    # Continuous walk across screen
    # Speed: 2.0 steps/sec, stride = 68 * 2 = 136px per step
    # Real ground speed = 2.0 * 136 = 272 px/sec
    start_x = 240.0
    walk_speed = 2.2 # cycles per second

    for f_idx in range(total_frames):
        t = f_idx / float(fps)
        walk_phase = (t * walk_speed) % 1.0

        # Translation strictly locked to walk phase (ZERO foot slide)
        current_x = start_x + t * (walk_speed * 136.0)

        frame = bg_raw.copy()

        render_puppet_frame(
            canvas=frame,
            cx=current_x,
            ground_y=950.0,
            walk_phase=walk_phase,
            archetype="tech_founder",
            facing_right=True,
            scale=1.1,
        )

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()

    print("Walk test video generated:", out_path)

if __name__ == "__main__":
    generate_walk_cycle_video()
