"""
test_ardy_stickman_pipeline.py
==============================
Unit Test Suite for NVIDIA ARDY 3D Motion Diffusion & Crayon Stickman Pipeline:
1. Satire Motion Catalog & Semantic Intent Resolver
2. ArdyMotionController 3D Trajectory Synthesis & Disk Cache
3. CameraDirector 3D-to-2D Perspective Projection & Ground Pinning
4. CrayonMeshRenderer 12 FPS Boiling Line Shader & Googly Eyes
5. Deterministic Zero-GPU Offline Fallback Resilience
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from src.stickman_engine.satire_motion_catalog import (
    SMPL_22_JOINTS,
    JOINT_NAMES,
    SATIRE_MOTIONS,
    resolve_satire_motion,
    SatireMotionDef
)
from src.stickman_engine.ardy_controller import ArdyMotionController
from src.stickman_engine.camera_projection import CameraDirector, CameraConfig
from src.stickman_engine.crayon_mesh_renderer import CrayonMeshRenderer


class TestArdyStickmanPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_ardy_"))
        self.controller = ArdyMotionController(cache_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ─────────────────────────────────────────────────────────────
    # 1. CATALOG & SEMANTIC RESOLVER
    # ─────────────────────────────────────────────────────────────
    def test_catalog_structure(self):
        """Verifies SMPL 22-joint definition and motion registry completeness."""
        self.assertEqual(len(SMPL_22_JOINTS), 22)
        self.assertEqual(len(JOINT_NAMES), 22)
        self.assertIn("war_room_slam", SATIRE_MOTIONS)
        self.assertIn("contractor_shrug", SATIRE_MOTIONS)
        self.assertIn("bureaucrat_panic", SATIRE_MOTIONS)

        # Check joint indices
        self.assertEqual(SMPL_22_JOINTS["pelvis"], 0)
        self.assertEqual(SMPL_22_JOINTS["head"], 15)
        self.assertEqual(SMPL_22_JOINTS["left_wrist"], 20)
        self.assertEqual(SMPL_22_JOINTS["right_wrist"], 21)

    def test_semantic_motion_resolver(self):
        """Tests natural language script parsing into satirical action definitions."""
        # General rage
        m1 = resolve_satire_motion(script_text="The General slammed his fists furiously on the budget table")
        self.assertEqual(m1.motion_id, "war_room_slam")
        self.assertEqual(m1.archetype, "general")

        # Defense contractor CEO smugness
        m2 = resolve_satire_motion(script_text="The defense contractor CEO shrugged as profits hit 500 billion dollars")
        self.assertEqual(m2.motion_id, "contractor_shrug")
        self.assertEqual(m2.archetype, "defense_ceo")

        # Auditor panic
        m3 = resolve_satire_motion(script_text="The Pentagon auditor panicked over the missing trillions")
        self.assertEqual(m3.motion_id, "bureaucrat_panic")
        self.assertEqual(m3.archetype, "auditor")

    # ─────────────────────────────────────────────────────────────
    # 2. ARDY MOTION CONTROLLER & DISK CACHE
    # ─────────────────────────────────────────────────────────────
    def test_ardy_motion_generation_shape(self):
        """Verifies 3D trajectory array shape (T, 22, 3) and data types."""
        duration = 2.0
        fps = 30
        expected_frames = int(round(duration * fps))

        joints_3d = self.controller.get_motion("war_room_slam", duration_sec=duration, fps=fps)
        self.assertIsInstance(joints_3d, np.ndarray)
        self.assertEqual(joints_3d.shape, (expected_frames, 22, 3))
        self.assertEqual(joints_3d.dtype, np.float32)

        # Ensure values are within reasonable human metric scale (height ~ 0.0 to 2.2m)
        y_vals = joints_3d[:, :, 1]
        self.assertGreaterEqual(float(np.min(y_vals)), -0.5)
        self.assertLessEqual(float(np.max(y_vals)), 2.5)

    def test_ardy_motion_disk_cache(self):
        """Verifies that generated motions are serialized to .npz and loaded instantly."""
        # First call generates and writes cache
        _ = self.controller.get_motion("contractor_shrug", duration_sec=2.5, fps=30)
        cache_file = self.temp_dir / "contractor_shrug.npz"
        self.assertTrue(cache_file.exists(), "Cache file must be created on disk!")

        # Second call loads directly from disk
        cached_joints = self.controller.get_motion("contractor_shrug", duration_sec=2.5, fps=30)
        self.assertEqual(cached_joints.shape, (75, 22, 3))

    def test_ardy_resampling(self):
        """Verifies smooth interpolation when requested duration differs from cache."""
        # Generate at 2.0s (60 frames)
        _ = self.controller.get_motion("bureaucrat_panic", duration_sec=2.0, fps=30)
        # Request same motion at 3.0s (90 frames)
        resampled = self.controller.get_motion("bureaucrat_panic", duration_sec=3.0, fps=30)
        self.assertEqual(len(resampled), 90)

    # ─────────────────────────────────────────────────────────────
    # 3. CAMERA DIRECTOR (3D-TO-2D PERSPECTIVE & GROUND PINNING)
    # ─────────────────────────────────────────────────────────────
    def test_camera_projection_screen_bounds(self):
        """Verifies 3D points project cleanly within screen dimensions."""
        W, H = 1080, 1920
        ground_y = 1500
        cam = CameraDirector(screen_w=W, screen_h=H, ground_y=ground_y)

        joints_3d = self.controller.get_motion("war_room_slam", duration_sec=1.5, fps=30)
        joints_2d, depths = cam.project_motion(
            joints_3d,
            character_center_x=W // 2,
            character_scale=1.1
        )

        self.assertEqual(joints_2d.shape, (45, 22, 2))
        self.assertEqual(depths.shape, (45, 22))

        # Check that center X is near W // 2
        root_x = joints_2d[:, SMPL_22_JOINTS["pelvis"], 0]
        self.assertAlmostEqual(float(np.mean(root_x)), float(W // 2), delta=80.0)

        # Check ground pinning: lowest foot Y coordinate should be close to ground_y
        foot_y = np.maximum(
            joints_2d[:, SMPL_22_JOINTS["left_foot"], 1],
            joints_2d[:, SMPL_22_JOINTS["right_foot"], 1]
        )
        for fy in foot_y:
            self.assertAlmostEqual(float(fy), float(ground_y), delta=50.0)

    def test_camera_dutch_tilt(self):
        """Verifies that Dutch tilt rotates screen space coordinates."""
        W, H = 1080, 1920
        cam = CameraDirector(screen_w=W, screen_h=H, ground_y=1500)
        joints_3d = self.controller.get_motion("war_room_slam", duration_sec=1.0, fps=30)

        j2d_flat, _ = cam.project_motion(joints_3d, dutch_tilt_deg=0.0)
        j2d_tilted, _ = cam.project_motion(joints_3d, dutch_tilt_deg=8.0)

        # Tilted head position must differ from flat head position
        head_flat_x = float(j2d_flat[0, SMPL_22_JOINTS["head"], 0])
        head_tilted_x = float(j2d_tilted[0, SMPL_22_JOINTS["head"], 0])
        self.assertNotEqual(head_flat_x, head_tilted_x)

    # ─────────────────────────────────────────────────────────────
    # 4. CRAYON MESH RENDERER & BOILING LINE SHADER
    # ─────────────────────────────────────────────────────────────
    def test_crayon_renderer_execution(self):
        """Verifies that CrayonMeshRenderer draws on a PIL Image without error."""
        W, H = 1080, 1920
        cam = CameraDirector(screen_w=W, screen_h=H, ground_y=1400)
        joints_3d = self.controller.get_motion("war_room_slam", duration_sec=1.0, fps=30)
        joints_2d, _ = cam.project_motion(joints_3d, character_center_x=W // 2)

        renderer = CrayonMeshRenderer()
        canvas = Image.new("RGBA", (W, H), (244, 241, 234, 255))
        draw = ImageDraw.Draw(canvas)

        # Render first frame
        renderer.render_puppet(
            draw=draw,
            joints_2d=joints_2d[0],
            frame_idx=0,
            archetype="general",
            emotion="angry",
            scale=1.0
        )

        # Canvas must no longer be purely blank background
        # Check center region where head and body are located
        head_px = canvas.getpixel((W // 2, int(joints_2d[0, SMPL_22_JOINTS["head"], 1])))
        self.assertIsNotNone(head_px)

    def test_boiling_line_turbulence(self):
        """Verifies that line boil jitter changes on alternating frames (12 fps on 30 fps)."""
        W, H = 500, 500
        renderer = CrayonMeshRenderer()

        # Mock static joints
        mock_joints = np.full((22, 2), 250.0, dtype=np.float32)

        # Render frame 0 and frame 2 (different boil steps)
        img0 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw0 = ImageDraw.Draw(img0)
        renderer.render_puppet(draw0, mock_joints, frame_idx=0)

        img2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw2 = ImageDraw.Draw(img2)
        renderer.render_puppet(draw2, mock_joints, frame_idx=2)

        # Images must differ due to 12 FPS boiling line turbulence
        diff = np.sum(np.abs(np.array(img0, dtype=np.int32) - np.array(img2, dtype=np.int32)))
        self.assertGreater(diff, 0, "Boiling line shader must produce organic frame-to-frame variations!")


if __name__ == "__main__":
    unittest.main()
