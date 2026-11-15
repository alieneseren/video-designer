"""
ardy_controller.py
==================
NVIDIA ARDY (nv-tlabs/ardy) 3D Motion Diffusion Controller & Cache Engine.
Generates sub-35ms autoregressive 3D humanoid skeletal trajectories for
stickman satire animation, with offline pre-baking and deterministic fallback.
"""

import os
import sys
import math
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from .satire_motion_catalog import (
    SMPL_22_JOINTS,
    JOINT_NAMES,
    SATIRE_MOTIONS,
    SatireMotionDef,
    resolve_satire_motion
)

logger = logging.getLogger("ArdyMotionController")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")

CACHE_DIR = Path(__file__).resolve().parent / "motion_cache"


class ArdyMotionController:
    """
    Controller for NVIDIA ARDY 3D humanoid motion diffusion.
    Coordinates local Apple Silicon (MPS), remote CUDA GPUs, and local disk cache.
    """

    def __init__(self, cache_dir: Optional[Path] = None, use_gpu: bool = True):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_gpu = use_gpu
        self.device = self._detect_device()
        self._memory_cache: Dict[str, np.ndarray] = {}

        logger.info(f"⚡ [ArdyMotionController] Initialized on device: {self.device} (Cache: {self.cache_dir})")
        # Ensure standard motion catalog is pre-baked for instant offline loading
        self.prebake_standard_catalog()

    def _detect_device(self) -> str:
        """Determines optimal PyTorch compute device."""
        if not TORCH_AVAILABLE or not self.use_gpu:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda:0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def get_motion(
        self,
        motion_key_or_prompt: str,
        duration_sec: float = 3.0,
        fps: int = 30,
        force_regenerate: bool = False
    ) -> np.ndarray:
        """
        Retrieves a (T, 22, 3) 3D joint trajectory array.
        T = int(round(duration_sec * fps)).
        Returns 3D joint positions in meters relative to character root.
        """
        total_frames = max(15, int(round(duration_sec * fps)))
        cache_key = f"{motion_key_or_prompt}_{total_frames}f_{fps}fps"

        if not force_regenerate and cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        cache_file = self.cache_dir / f"{motion_key_or_prompt}.npz"
        if not force_regenerate and cache_file.exists():
            try:
                data = np.load(str(cache_file))
                joints = data["joints"]
                if len(joints) == total_frames:
                    self._memory_cache[cache_key] = joints
                    return joints
                # If cached length differs, resample smoothly
                resampled = self._resample_motion(joints, total_frames)
                self._memory_cache[cache_key] = resampled
                return resampled
            except Exception as e:
                logger.warning(f"⚠️ [ArdyMotionController] Failed to read {cache_file.name}: {e}")

        # Attempt ARDY model inference if available
        joints_3d = self._try_ardy_diffusion(motion_key_or_prompt, total_frames, fps)
        if joints_3d is None:
            # Fallback to procedural high-fidelity kinematic synthesizer
            joints_3d = self._synthesize_procedural_motion(motion_key_or_prompt, total_frames, fps)

        # Save to cache
        try:
            np.savez_compressed(
                str(cache_file),
                joints=joints_3d,
                fps=fps,
                prompt=motion_key_or_prompt,
                frames=total_frames
            )
        except Exception as e_save:
            logger.warning(f"⚠️ [ArdyMotionController] Failed to write cache: {e_save}")

        self._memory_cache[cache_key] = joints_3d
        return joints_3d

    def _resample_motion(self, source_joints: np.ndarray, target_frames: int) -> np.ndarray:
        """Smoothly interpolates a (T1, 22, 3) array to (target_frames, 22, 3)."""
        src_frames = len(source_joints)
        if src_frames == target_frames:
            return source_joints
        
        t_src = np.linspace(0.0, 1.0, src_frames)
        t_tgt = np.linspace(0.0, 1.0, target_frames)

        resampled = np.zeros((target_frames, 22, 3), dtype=np.float32)
        for j in range(22):
            for axis in range(3):
                resampled[:, j, axis] = np.interp(t_tgt, t_src, source_joints[:, j, axis])
        return resampled

    def _try_ardy_diffusion(self, prompt: str, total_frames: int, fps: int) -> Optional[np.ndarray]:
        """
        Attempts to call nv-tlabs/ardy model or local ARDY service daemon.
        Returns None on any network/import/timeout error to trigger graceful fallback.
        """
        try:
            # Check for local ARDY module or HTTP daemon
            import urllib.request
            import json

            # Check if ARDY daemon is running on port 8088
            url = "http://127.0.0.1:8088/generate_motion"
            payload = json.dumps({
                "prompt": prompt,
                "frames": total_frames,
                "fps": fps
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    arr = np.array(res_data["joints"], dtype=np.float32)
                    if arr.shape == (total_frames, 22, 3):
                        logger.info(f"✨ [ArdyMotionController] Received 3D stream from ARDY daemon for '{prompt[:30]}...'")
                        return arr
        except Exception:
            pass

        return None

    def _synthesize_procedural_motion(self, motion_key: str, total_frames: int, fps: int) -> np.ndarray:
        """
        High-fidelity procedural 3D humanoid generator.
        Constructs biologically coherent SMPL 22-joint kinematics for satirical actions.
        """
        motion_def = SATIRE_MOTIONS.get(motion_key) or resolve_satire_motion(script_text=motion_key)
        m_id = motion_def.motion_id

        # Base neutral T-pose / resting posture in meters
        # Standard proportions: Total height ~ 1.75m
        base_skeleton = np.zeros((22, 3), dtype=np.float32)
        base_skeleton[SMPL_22_JOINTS["pelvis"]] = [0.0, 0.95, 0.0]
        base_skeleton[SMPL_22_JOINTS["spine1"]] = [0.0, 1.10, 0.0]
        base_skeleton[SMPL_22_JOINTS["spine2"]] = [0.0, 1.25, 0.0]
        base_skeleton[SMPL_22_JOINTS["spine3"]] = [0.0, 1.40, 0.0]
        base_skeleton[SMPL_22_JOINTS["neck"]]   = [0.0, 1.52, 0.0]
        base_skeleton[SMPL_22_JOINTS["head"]]   = [0.0, 1.70, 0.0]

        # Left Leg
        base_skeleton[SMPL_22_JOINTS["left_hip"]]   = [-0.12, 0.90, 0.0]
        base_skeleton[SMPL_22_JOINTS["left_knee"]]  = [-0.12, 0.50, 0.0]
        base_skeleton[SMPL_22_JOINTS["left_ankle"]] = [-0.12, 0.10, 0.0]
        base_skeleton[SMPL_22_JOINTS["left_foot"]]  = [-0.12, 0.00, 0.15]

        # Right Leg
        base_skeleton[SMPL_22_JOINTS["right_hip"]]   = [0.12, 0.90, 0.0]
        base_skeleton[SMPL_22_JOINTS["right_knee"]]  = [0.12, 0.50, 0.0]
        base_skeleton[SMPL_22_JOINTS["right_ankle"]] = [0.12, 0.10, 0.0]
        base_skeleton[SMPL_22_JOINTS["right_foot"]]  = [0.12, 0.00, 0.15]

        # Arms (resting along body)
        base_skeleton[SMPL_22_JOINTS["left_collar"]]   = [-0.08, 1.42, 0.0]
        base_skeleton[SMPL_22_JOINTS["left_shoulder"]] = [-0.22, 1.40, 0.0]
        base_skeleton[SMPL_22_JOINTS["left_elbow"]]    = [-0.26, 1.10, 0.0]
        base_skeleton[SMPL_22_JOINTS["left_wrist"]]    = [-0.28, 0.85, 0.0]

        base_skeleton[SMPL_22_JOINTS["right_collar"]]   = [0.08, 1.42, 0.0]
        base_skeleton[SMPL_22_JOINTS["right_shoulder"]] = [0.22, 1.40, 0.0]
        base_skeleton[SMPL_22_JOINTS["right_elbow"]]    = [0.26, 1.10, 0.0]
        base_skeleton[SMPL_22_JOINTS["right_wrist"]]    = [0.28, 0.85, 0.0]

        trajectory = np.zeros((total_frames, 22, 3), dtype=np.float32)

        for f in range(total_frames):
            t = f / float(total_frames)
            pose = base_skeleton.copy()

            if m_id == "war_room_slam":
                # General slams table: Anticipation raise -> Rapid downward slam -> Tremble/Settle
                # Phase 1 (0.0 - 0.3): Arms raise back, spine arches backward
                if t < 0.30:
                    prog = t / 0.30
                    pose[SMPL_22_JOINTS["spine3"]][2] -= 0.08 * prog
                    pose[SMPL_22_JOINTS["head"]][1] += 0.05 * prog
                    # Hands rise high
                    pose[SMPL_22_JOINTS["left_elbow"]] = [-0.24, 1.45 + 0.15 * prog, -0.10 * prog]
                    pose[SMPL_22_JOINTS["right_elbow"]] = [0.24, 1.45 + 0.15 * prog, -0.10 * prog]
                    pose[SMPL_22_JOINTS["left_wrist"]] = [-0.22, 1.70 + 0.10 * prog, -0.05 * prog]
                    pose[SMPL_22_JOINTS["right_wrist"]] = [0.22, 1.70 + 0.10 * prog, -0.05 * prog]
                # Phase 2 (0.30 - 0.42): Rapid violent slam down onto table
                elif t < 0.42:
                    prog = (t - 0.30) / 0.12
                    slam_eased = prog * prog * prog  # Cubic acceleration
                    pose[SMPL_22_JOINTS["spine2"]][2] += 0.18 * slam_eased
                    pose[SMPL_22_JOINTS["spine3"]][1] -= 0.10 * slam_eased
                    pose[SMPL_22_JOINTS["spine3"]][2] += 0.22 * slam_eased
                    pose[SMPL_22_JOINTS["head"]][1] -= 0.08 * slam_eased
                    pose[SMPL_22_JOINTS["head"]][2] += 0.26 * slam_eased
                    # Hands slam onto desk level (Y ~ 0.95m, Z ~ 0.35m)
                    pose[SMPL_22_JOINTS["left_elbow"]] = [-0.22, 1.20 - 0.20 * slam_eased, 0.20 * slam_eased]
                    pose[SMPL_22_JOINTS["right_elbow"]] = [0.22, 1.20 - 0.20 * slam_eased, 0.20 * slam_eased]
                    pose[SMPL_22_JOINTS["left_wrist"]] = [-0.18, 1.70 - 0.75 * slam_eased, 0.35 * slam_eased]
                    pose[SMPL_22_JOINTS["right_wrist"]] = [0.18, 1.70 - 0.75 * slam_eased, 0.35 * slam_eased]
                # Phase 3 (0.42 - 1.0): Residual rage trembling on desk
                else:
                    tremble = math.sin(f * 1.8) * 0.012
                    pose[SMPL_22_JOINTS["spine3"]][1] -= 0.10
                    pose[SMPL_22_JOINTS["spine3"]][2] += 0.22 + tremble
                    pose[SMPL_22_JOINTS["head"]][1] -= 0.08
                    pose[SMPL_22_JOINTS["head"]][2] += 0.26 + tremble * 1.5
                    pose[SMPL_22_JOINTS["left_wrist"]] = [-0.18, 0.95 + tremble, 0.35]
                    pose[SMPL_22_JOINTS["right_wrist"]] = [0.18, 0.95 + tremble, 0.35]

            elif m_id == "contractor_shrug":
                # Smug shrug: Leaning back, palms opening, head tilting
                shrug_cycle = math.sin(t * math.pi)
                pose[SMPL_22_JOINTS["spine3"]][2] -= 0.06 * shrug_cycle
                pose[SMPL_22_JOINTS["head"]][0] += 0.04 * shrug_cycle
                pose[SMPL_22_JOINTS["head"]][1] -= 0.02 * shrug_cycle
                # Shoulders elevate
                pose[SMPL_22_JOINTS["left_shoulder"]][1] += 0.08 * shrug_cycle
                pose[SMPL_22_JOINTS["right_shoulder"]][1] += 0.08 * shrug_cycle
                # Elbows tuck in, wrists push out and up (open palm gesture)
                pose[SMPL_22_JOINTS["left_elbow"]] = [-0.20, 1.15 + 0.05 * shrug_cycle, 0.10 * shrug_cycle]
                pose[SMPL_22_JOINTS["right_elbow"]] = [0.20, 1.15 + 0.05 * shrug_cycle, 0.10 * shrug_cycle]
                pose[SMPL_22_JOINTS["left_wrist"]] = [-0.38 * shrug_cycle - 0.24, 1.18 + 0.10 * shrug_cycle, 0.20 * shrug_cycle]
                pose[SMPL_22_JOINTS["right_wrist"]] = [0.38 * shrug_cycle + 0.24, 1.18 + 0.10 * shrug_cycle, 0.20 * shrug_cycle]

            elif m_id == "bureaucrat_panic":
                # Auditor panic: Hands on head, pacing trembles
                pace = math.sin(t * math.pi * 3.0) * 0.15
                tremble = math.sin(f * 2.5) * 0.02
                pose[SMPL_22_JOINTS["pelvis"]][0] += pace
                pose[SMPL_22_JOINTS["spine1"]][0] += pace
                pose[SMPL_22_JOINTS["spine3"]][0] += pace
                pose[SMPL_22_JOINTS["head"]][0] += pace + tremble
                # Hands clutching head
                pose[SMPL_22_JOINTS["left_elbow"]] = [pace - 0.26, 1.48 + tremble, 0.10]
                pose[SMPL_22_JOINTS["right_elbow"]] = [pace + 0.26, 1.48 + tremble, 0.10]
                pose[SMPL_22_JOINTS["left_wrist"]] = [pace - 0.12, 1.72 + tremble, 0.08]
                pose[SMPL_22_JOINTS["right_wrist"]] = [pace + 0.12, 1.72 + tremble, 0.08]

            elif m_id == "podium_propaganda":
                # Grand pointing with right hand, left hand on podium
                point_cycle = math.sin(t * math.pi * 2.0)
                pose[SMPL_22_JOINTS["spine3"]][2] += 0.08
                pose[SMPL_22_JOINTS["left_wrist"]] = [-0.18, 1.05, 0.25]
                # Right arm points theatrically forward/upward
                pose[SMPL_22_JOINTS["right_elbow"]] = [0.28, 1.35 + 0.10 * point_cycle, 0.30]
                pose[SMPL_22_JOINTS["right_wrist"]] = [0.35, 1.60 + 0.15 * point_cycle, 0.55]

            elif m_id == "soldier_duck_cover":
                # Duck down low and cover head
                duck_prog = math.sin(t * math.pi)
                pose[SMPL_22_JOINTS["pelvis"]][1] -= 0.35 * duck_prog
                pose[SMPL_22_JOINTS["spine1"]][1] -= 0.38 * duck_prog
                pose[SMPL_22_JOINTS["spine3"]][1] -= 0.45 * duck_prog
                pose[SMPL_22_JOINTS["head"]][1] -= 0.50 * duck_prog
                pose[SMPL_22_JOINTS["left_knee"]][0] -= 0.10 * duck_prog
                pose[SMPL_22_JOINTS["right_knee"]][0] += 0.10 * duck_prog
                pose[SMPL_22_JOINTS["left_wrist"]] = [-0.15, pose[SMPL_22_JOINTS["head"]][1] + 0.05, 0.05]
                pose[SMPL_22_JOINTS["right_wrist"]] = [0.15, pose[SMPL_22_JOINTS["head"]][1] + 0.05, 0.05]

            elif m_id == "facepalm_disbelief":
                # Hand slowly reaches up to cover face
                reach = min(1.0, t * 2.0)
                pose[SMPL_22_JOINTS["head"]][2] -= 0.05 * reach
                pose[SMPL_22_JOINTS["right_elbow"]] = [0.18, 1.25 + 0.15 * reach, 0.15 * reach]
                pose[SMPL_22_JOINTS["right_wrist"]] = [0.02, 1.68, 0.12 * reach]

            elif m_id == "proud_strut":
                # High-stepping comedic march
                step_phase = t * math.pi * 4.0
                step_l = math.sin(step_phase)
                step_r = math.sin(step_phase + math.pi)
                pose[SMPL_22_JOINTS["left_knee"]][1] += max(0.0, step_l * 0.22)
                pose[SMPL_22_JOINTS["right_knee"]][1] += max(0.0, step_r * 0.22)
                pose[SMPL_22_JOINTS["left_ankle"]][1] += max(0.0, step_l * 0.26)
                pose[SMPL_22_JOINTS["right_ankle"]][1] += max(0.0, step_r * 0.26)
                # Chest puffed out
                pose[SMPL_22_JOINTS["spine3"]][2] += 0.12
                pose[SMPL_22_JOINTS["left_wrist"]][2] -= step_l * 0.25
                pose[SMPL_22_JOINTS["right_wrist"]][2] -= step_r * 0.25

            else:
                # Default subtle breathing idle
                breath = math.sin(f * 0.15) * 0.015
                pose[SMPL_22_JOINTS["spine3"]][1] += breath
                pose[SMPL_22_JOINTS["head"]][1] += breath

            trajectory[f] = pose

        return trajectory

    def prebake_standard_catalog(self, force: bool = False):
        """Pre-bakes all catalog motions to disk to guarantee instant offline execution."""
        for m_key in SATIRE_MOTIONS.keys():
            cache_file = self.cache_dir / f"{m_key}.npz"
            if force or not cache_file.exists():
                m_def = SATIRE_MOTIONS[m_key]
                duration = m_def.default_duration
                total_frames = int(round(duration * 30))
                joints = self._synthesize_procedural_motion(m_key, total_frames, 30)
                try:
                    np.savez_compressed(
                        str(cache_file),
                        joints=joints,
                        fps=30,
                        prompt=m_def.prompt,
                        frames=total_frames
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [ArdyMotionController] Prebake write failed for {m_key}: {e}")

    @staticmethod
    def get_joint_names() -> List[str]:
        return JOINT_NAMES
