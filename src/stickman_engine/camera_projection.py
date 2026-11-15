"""
camera_projection.py
====================
Avant-Garde Camera Director & 3D-to-2D Perspective Projection Engine.
Projects 3D humanoid skeletal joint trajectories into screen-space coordinates
with support for Dutch tilts, punch-in zooms, dynamic camera shakes, and ground alignment.
"""

import math
from dataclasses import dataclass
from typing import Tuple, List, Optional
import numpy as np


@dataclass
class CameraConfig:
    """Configurable cinematic camera parameters."""
    fov_deg: float = 45.0
    cam_pos: Tuple[float, float, float] = (0.0, 1.15, 2.75)
    cam_target: Tuple[float, float, float] = (0.0, 0.95, 0.0)
    dutch_tilt_deg: float = 0.0
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0


class CameraDirector:
    """
    Transforms 3D world joints J(t) ∈ R^(22 x 3) into screen-space pixel coordinates
    with cinematic camera dynamics (Dutch tilt, zoom punch-in, ground alignment).
    """

    def __init__(
        self,
        screen_w: int = 1080,
        screen_h: int = 1920,
        ground_y: int = 1420,
        config: Optional[CameraConfig] = None
    ):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.ground_y = ground_y
        self.cfg = config or CameraConfig()

    def project_motion(
        self,
        joints_3d: np.ndarray,
        character_center_x: Optional[int] = None,
        character_scale: float = 1.0,
        dutch_tilt_deg: Optional[float] = None,
        punch_in_zoom: Optional[float] = None,
        camera_shake_px: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Projects (T, 22, 3) 3D joints to (T, 22, 2) screen pixel coordinates.
        Returns:
            projected_2d: np.ndarray of shape (T, 22, 2) [X, Y] in pixels.
            depths: np.ndarray of shape (T, 22) [Z depth in camera space].
        """
        T, num_joints, _ = joints_3d.shape
        out_2d = np.zeros((T, num_joints, 2), dtype=np.float32)
        out_depth = np.zeros((T, num_joints), dtype=np.float32)

        cx = character_center_x if character_center_x is not None else (self.screen_w // 2)
        tilt = dutch_tilt_deg if dutch_tilt_deg is not None else self.cfg.dutch_tilt_deg
        zoom = (punch_in_zoom if punch_in_zoom is not None else self.cfg.zoom) * character_scale

        fov_rad = math.radians(self.cfg.fov_deg)
        focal_length = (self.screen_w / 2.0) / math.tan(fov_rad / 2.0)

        cam_x, cam_y, cam_z = self.cfg.cam_pos
        tgt_x, tgt_y, tgt_z = self.cfg.cam_target

        # Camera Forward vector
        fwd = np.array([tgt_x - cam_x, tgt_y - cam_y, tgt_z - cam_z], dtype=np.float32)
        fwd_norm = np.linalg.norm(fwd)
        fwd = fwd / (fwd_norm if fwd_norm > 1e-5 else 1.0)

        # Global Up
        up_global = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        # Right vector
        right = np.cross(fwd, up_global)
        r_norm = np.linalg.norm(right)
        right = right / (r_norm if r_norm > 1e-5 else 1.0)

        # Camera Up vector
        up = np.cross(right, fwd)

        # Apply Dutch Tilt (Roll rotation around forward axis)
        if abs(tilt) > 0.01:
            tilt_rad = math.radians(tilt)
            cos_t = math.cos(tilt_rad)
            sin_t = math.sin(tilt_rad)
            right_tilted = right * cos_t + up * sin_t
            up_tilted = -right * sin_t + up * cos_t
            right = right_tilted
            up = up_tilted

        # World-to-Camera Rotation Matrix (3x3)
        # [ right_x, right_y, right_z ]
        # [ up_x,    up_y,    up_z    ]
        # [ fwd_x,   fwd_y,   fwd_z   ]
        R_cam = np.vstack([right, up, fwd])

        # Find reference ground foot height across sequence for deterministic ground-pinning
        # SMPL joint 10: left_foot, joint 11: right_foot
        min_foot_y_world = float(np.min(joints_3d[:, [10, 11], 1]))

        for f in range(T):
            frame_joints = joints_3d[f]  # (22, 3)

            # Center relative to sequence root and ground offset
            world_pts = frame_joints.copy()
            # Ground pinning: Shift character so minimum foot touches ground reference
            ground_offset = min_foot_y_world
            world_pts[:, 1] -= ground_offset

            # Translate to camera origin
            trans = world_pts - np.array([cam_x, cam_y, cam_z], dtype=np.float32)

            # Rotate into camera frame
            cam_pts = np.dot(trans, R_cam.T)  # (22, 3) -> [X_c, Y_c, Z_c]

            # Perspective division: x_proj = X_c * (f / Z_c), y_proj = -Y_c * (f / Z_c)
            z_c = cam_pts[:, 2]
            z_c_safe = np.maximum(z_c, 0.1)

            proj_x = (cam_pts[:, 0] / z_c_safe) * focal_length * zoom
            proj_y = -(cam_pts[:, 1] / z_c_safe) * focal_length * zoom

            # Apply camera shake if present
            shake_x = 0.0
            shake_y = 0.0
            if camera_shake_px > 0.01:
                shake_x = math.sin(f * 2.3) * camera_shake_px
                shake_y = math.cos(f * 1.7) * (camera_shake_px * 0.7)

            # Map to screen pixels:
            # Deterministic ground pinning: Align lowest foot joint exactly to target ground_y
            lowest_foot_proj_y = max(float(proj_y[10]), float(proj_y[11]))
            y_shift = self.ground_y - lowest_foot_proj_y

            screen_x = cx + proj_x + shake_x
            screen_y = proj_y + y_shift + shake_y

            out_2d[f, :, 0] = screen_x
            out_2d[f, :, 1] = screen_y
            out_depth[f, :] = z_c

        return out_2d, out_depth
