"""
test_puppet_walk.py
===================
Prototyping the authentic Crayon Capital volumetric puppet rig walk cycle.
"""

import math
import random
from typing import Tuple, Optional, Dict, Any, List
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

def draw_capsule_segment(
    draw: ImageDraw.Draw,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    radius: float,
    fill_color: Tuple[int, ...],
    border_color: Tuple[int, ...] = (15, 23, 42),
    stroke_w: int = 5
):
    """Draws a volumetric 2D cartoon limb segment with thick borders and round caps."""
    # Outer stroke
    draw.line([p1, p2], fill=border_color, width=int(2 * radius + stroke_w * 2))
    draw.ellipse([(p1[0] - radius - stroke_w, p1[1] - radius - stroke_w), (p1[0] + radius + stroke_w, p1[1] + radius + stroke_w)], fill=border_color)
    draw.ellipse([(p2[0] - radius - stroke_w, p2[1] - radius - stroke_w), (p2[0] + radius + stroke_w, p2[1] + radius + stroke_w)], fill=border_color)
    # Inner fill
    draw.line([p1, p2], fill=fill_color, width=int(2 * radius))
    draw.ellipse([(p1[0] - radius, p1[1] - radius), (p1[0] + radius, p1[1] + radius)], fill=fill_color)
    draw.ellipse([(p2[0] - radius, p2[1] - radius), (p2[0] + radius, p2[1] + radius)], fill=fill_color)

def draw_crayon_shoe(
    draw: ImageDraw.Draw,
    ankle: Tuple[float, float],
    foot_rot_deg: float,
    facing_right: bool = True,
    shoe_type: str = "sneaker", # 'sneaker', 'dress'
    scale: float = 1.0,
):
    ax, ay = ankle
    dir_m = 1.0 if facing_right else -1.0
    rad = math.radians(foot_rot_deg)

    cos_r = math.cos(rad) * dir_m
    sin_r = math.sin(rad)

    # Foot geometry from ankle
    heel_x = ax - 16.0 * scale * cos_r
    heel_y = ay + 16.0 * scale * sin_r
    toe_x = ax + 36.0 * scale * cos_r
    toe_y = ay - 36.0 * scale * sin_r

    # Sole thickness & sole line
    sole_th = int(7 * scale)
    sole_col = (255, 255, 255) if shoe_type == "sneaker" else (20, 20, 25)
    border_col = (15, 23, 42)

    # Sole polygon
    draw.line([(heel_x, heel_y + 3), (toe_x, toe_y + 3)], fill=border_col, width=sole_th + 4)
    draw.line([(heel_x, heel_y + 3), (toe_x, toe_y + 3)], fill=sole_col, width=sole_th)

    # Upper shoe
    upper_col = (248, 250, 252) if shoe_type == "sneaker" else (30, 41, 59)
    poly = [
        (heel_x - 3 * scale * cos_r, heel_y - 12 * scale),
        (ax, ay - 10 * scale),
        (toe_x - 10 * scale * cos_r, toe_y - 14 * scale),
        (toe_x, toe_y),
        (heel_x, heel_y),
    ]
    draw.polygon(poly, fill=upper_col, outline=border_col)
    draw.line([poly[0], poly[1]], fill=border_col, width=int(4 * scale))
    draw.line([poly[1], poly[2]], fill=border_col, width=int(4 * scale))
    draw.line([poly[2], poly[3]], fill=border_col, width=int(4 * scale))

    # Sneaker detail / laces
    if shoe_type == "sneaker":
        draw.line([(ax - 2 * scale * dir_m, ay - 4 * scale), (ax + 12 * scale * dir_m, ay - 6 * scale)], fill=(234, 88, 12), width=int(3 * scale))

def render_sample_pose(archetype: str = "tech_founder", walk_phase: float = 0.0, output_name: str = "sample_founder.png"):
    w, h = 600, 800
    img = Image.new("RGBA", (w, h), (245, 247, 250, 255))
    draw = ImageDraw.Draw(img)

    scale = 1.0
    ground_y = 680.0
    cx = 300.0

    # 4-phase zero-slip kinematics
    # Double-bounce pelvis
    hip_bounce = -abs(math.sin(walk_phase * 2.0 * math.pi)) * (14.0 * scale)
    torso_tilt_deg = 3.5 + math.sin(walk_phase * 2.0 * math.pi) * 2.0

    thigh_l = 92.0 * scale
    shin_l = 96.0 * scale
    stride = 72.0 * scale
    step_lift = 44.0 * scale

    hip_x = cx
    hip_y = ground_y - (thigh_l + shin_l - 12.0 * scale) + hip_bounce

    # Leg 1 (Front, phase 0..1)
    p1 = walk_phase % 1.0
    if p1 < 0.5: # Stance
        t_st = p1 / 0.5
        f1_x = hip_x + (stride - t_st * 2.0 * stride)
        f1_y = ground_y
        if t_st < 0.15:
            f1_rot = -22.0 * (1.0 - t_st / 0.15)
        elif t_st > 0.35:
            f1_rot = 38.0 * ((t_st - 0.35) / 0.15)
        else:
            f1_rot = 0.0
    else: # Swing
        sw = (p1 - 0.5) / 0.5
        f1_x = hip_x + (-stride + sw * 2.0 * stride)
        f1_y = ground_y - math.sin(sw * math.pi) * step_lift
        f1_rot = 18.0 * (1.0 - sw) - 18.0 * sw

    # Leg 2 (Back, offset 0.5)
    p2 = (walk_phase + 0.5) % 1.0
    if p2 < 0.5:
        t_st = p2 / 0.5
        f2_x = hip_x + (stride - t_st * 2.0 * stride)
        f2_y = ground_y
        if t_st < 0.15:
            f2_rot = -22.0 * (1.0 - t_st / 0.15)
        elif t_st > 0.35:
            f2_rot = 38.0 * ((t_st - 0.35) / 0.15)
        else:
            f2_rot = 0.0
    else:
        sw = (p2 - 0.5) / 0.5
        f2_x = hip_x + (-stride + sw * 2.0 * stride)
        f2_y = ground_y - math.sin(sw * math.pi) * step_lift
        f2_rot = 18.0 * (1.0 - sw) - 18.0 * sw

    # Colors per archetype
    if archetype == "tech_founder":
        pants_col = (30, 41, 59) # Dark jeans
        shirt_col = (15, 23, 42) # Black turtleneck
        shoe_type = "sneaker"
    elif archetype == "wall_street_trader":
        pants_col = (51, 65, 85) # Slate trousers
        shirt_col = (248, 250, 252) # White shirt
        shoe_type = "dress"
    elif archetype == "defense_ceo":
        pants_col = (15, 23, 42) # Black suit pants
        shirt_col = (15, 23, 42) # Black suit jacket
        shoe_type = "dress"
    else:
        pants_col = (214, 180, 142) # Khaki
        shirt_col = (226, 232, 240) # Gray hoodie
        shoe_type = "sneaker"

    # Solve Knees
    k1 = solve_ik((hip_x - 8, hip_y), (f1_x, f1_y), thigh_l, shin_l, bend_positive=True)
    k2 = solve_ik((hip_x + 8, hip_y), (f2_x, f2_y), thigh_l, shin_l, bend_positive=True)

    # 1. Soft Dynamic Ground Shadow
    sw_w = int(140 * scale)
    sw_h = int(22 * scale)
    draw.ellipse([(hip_x - sw_w // 2, int(ground_y) - 6), (hip_x + sw_w // 2, int(ground_y) + sw_h - 6)], fill=(0, 0, 0, 80))

    # 2. Back Leg (Leg 2)
    h2 = (hip_x + 8, hip_y)
    draw_capsule_segment(draw, h2, k2, 18 * scale, pants_col, stroke_w=4)
    draw_capsule_segment(draw, k2, (f2_x, f2_y), 15 * scale, pants_col, stroke_w=4)
    draw_crayon_shoe(draw, (f2_x, f2_y), f2_rot, facing_right=True, shoe_type=shoe_type, scale=scale)

    # 3. Torso
    torso_h = 145.0 * scale
    torso_w = 78.0 * scale
    torso_top = hip_y - torso_h
    t_box = [(hip_x - torso_w // 2, torso_top), (hip_x + torso_w // 2, hip_y)]
    draw.rounded_rectangle(t_box, radius=int(24 * scale), fill=shirt_col, outline=(15, 23, 42), width=int(5 * scale))

    # Turtleneck collar
    if archetype == "tech_founder":
        draw.rounded_rectangle([(hip_x - 22 * scale, torso_top - 12 * scale), (hip_x + 22 * scale, torso_top + 10 * scale)], radius=int(6 * scale), fill=shirt_col, outline=(15, 23, 42), width=int(4 * scale))
    elif archetype == "wall_street_trader":
        # Red suspenders
        draw.line([(hip_x - 24 * scale, torso_top + 6 * scale), (hip_x - 20 * scale, hip_y)], fill=(220, 38, 38), width=int(8 * scale))
        draw.line([(hip_x + 16 * scale, torso_top + 6 * scale), (hip_x + 20 * scale, hip_y)], fill=(220, 38, 38), width=int(8 * scale))

    # 4. Front Leg (Leg 1)
    h1 = (hip_x - 8, hip_y)
    draw_capsule_segment(draw, h1, k1, 20 * scale, pants_col, stroke_w=4)
    draw_capsule_segment(draw, k1, (f1_x, f1_y), 16 * scale, pants_col, stroke_w=4)
    draw_crayon_shoe(draw, (f1_x, f1_y), f1_rot, facing_right=True, shoe_type=shoe_type, scale=scale)

    # 5. Head & Face (with slight head lag)
    head_lag_bounce = -abs(math.sin((walk_phase - 0.08) * 2.0 * math.pi)) * (12.0 * scale)
    head_r = 54.0 * scale
    head_cy = torso_top - head_r + 14 * scale + head_lag_bounce
    head_cx = hip_x + 4 * scale

    # Neck
    draw.line([(head_cx, torso_top - 5), (head_cx, torso_top + 10)], fill=(253, 230, 216), width=int(18 * scale))

    # Head ellipse
    draw.ellipse([(head_cx - head_r, head_cy - head_r), (head_cx + head_r, head_cy + head_r)], fill=(253, 230, 216), outline=(15, 23, 42), width=int(5 * scale))

    # Styled side-swept hair
    draw.polygon([
        (head_cx - 48 * scale, head_cy - 12 * scale),
        (head_cx - 42 * scale, head_cy - 48 * scale),
        (head_cx - 15 * scale, head_cy - 58 * scale),
        (head_cx + 25 * scale, head_cy - 54 * scale),
        (head_cx + 52 * scale, head_cy - 20 * scale),
        (head_cx + 28 * scale, head_cy - 38 * scale),
        (head_cx - 10 * scale, head_cy - 42 * scale),
        (head_cx - 36 * scale, head_cy - 28 * scale),
    ], fill=(69, 39, 23), outline=(15, 23, 42))

    # Big Expressive Cartoon Eyes
    eye_x = head_cx + 18 * scale
    eye_y = head_cy - 2 * scale
    # Left eye
    draw.ellipse([(eye_x - 26 * scale, eye_y - 14 * scale), (eye_x - 6 * scale, eye_y + 14 * scale)], fill=(255, 255, 255), outline=(15, 23, 42), width=int(3.5 * scale))
    draw.ellipse([(eye_x - 19 * scale, eye_y - 6 * scale), (eye_x - 9 * scale, eye_y + 8 * scale)], fill=(15, 23, 42))
    draw.ellipse([(eye_x - 17 * scale, eye_y - 4 * scale), (eye_x - 13 * scale, eye_y)], fill=(255, 255, 255)) # Specular glint
    # Right eye
    draw.ellipse([(eye_x - 2 * scale, eye_y - 14 * scale), (eye_x + 18 * scale, eye_y + 14 * scale)], fill=(255, 255, 255), outline=(15, 23, 42), width=int(3.5 * scale))
    draw.ellipse([(eye_x + 5 * scale, eye_y - 6 * scale), (eye_x + 15 * scale, eye_y + 8 * scale)], fill=(15, 23, 42))
    draw.ellipse([(eye_x + 7 * scale, eye_y - 4 * scale), (eye_x + 11 * scale, eye_y)], fill=(255, 255, 255))

    # Eyebrows
    draw.arc([(eye_x - 28 * scale, eye_y - 28 * scale), (eye_x - 6 * scale, eye_y - 10 * scale)], 200, 350, fill=(15, 23, 42), width=int(3.5 * scale))
    draw.arc([(eye_x - 4 * scale, eye_y - 28 * scale), (eye_x + 18 * scale, eye_y - 10 * scale)], 200, 350, fill=(15, 23, 42), width=int(3.5 * scale))

    # Round hipster glasses for tech founder
    if archetype == "tech_founder":
        draw.ellipse([(eye_x - 29 * scale, eye_y - 16 * scale), (eye_x - 3 * scale, eye_y + 16 * scale)], outline=(15, 23, 42), width=int(4 * scale))
        draw.ellipse([(eye_x - 5 * scale, eye_y - 16 * scale), (eye_x + 21 * scale, eye_y + 16 * scale)], outline=(15, 23, 42), width=int(4 * scale))
        draw.line([(eye_x - 3 * scale, eye_y), (eye_x - 5 * scale, eye_y)], fill=(15, 23, 42), width=int(4 * scale))

    # Smile / Talking mouth
    draw.arc([(eye_x - 14 * scale, eye_y + 10 * scale), (eye_x + 14 * scale, eye_y + 26 * scale)], 20, 160, fill=(15, 23, 42), width=int(4 * scale))

    # 6. Arms & Natural Counter-Swing
    arm_swing = math.sin(walk_phase * 2.0 * math.pi) * (52.0 * scale)
    sh_pt = (hip_x - 6.0 * scale, torso_top + 28.0 * scale)
    wr_pt = (hip_x - arm_swing, hip_y - 16.0 * scale)
    el_pt = solve_ik(sh_pt, wr_pt, 60.0 * scale, 58.0 * scale, bend_positive=False)

    draw_capsule_segment(draw, sh_pt, el_pt, 16 * scale, shirt_col, stroke_w=4)
    draw_capsule_segment(draw, el_pt, wr_pt, 14 * scale, shirt_col, stroke_w=4)
    # Hand
    draw.ellipse([(wr_pt[0] - 12 * scale, wr_pt[1] - 12 * scale), (wr_pt[0] + 12 * scale, wr_pt[1] + 12 * scale)], fill=(253, 230, 216), outline=(15, 23, 42), width=int(4 * scale))

    out_path = f"output/stickman_demos/{output_name}"
    img.save(out_path)
    print(f"Sample pose saved: {out_path}")

if __name__ == "__main__":
    render_sample_pose(archetype="tech_founder", walk_phase=0.15, output_name="sample_founder_contact.png")
    render_sample_pose(archetype="tech_founder", walk_phase=0.40, output_name="sample_founder_passing.png")
    render_sample_pose(archetype="wall_street_trader", walk_phase=0.15, output_name="sample_trader_contact.png")
