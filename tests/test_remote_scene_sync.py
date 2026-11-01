import base64
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


WORKER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "remote_server" / "server_worker.py"
sys.modules.setdefault("edge_tts", ModuleType("edge_tts"))
SPEC = importlib.util.spec_from_file_location("remote_server_worker_for_tests", WORKER_PATH)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class RemoteSceneSyncTests(unittest.TestCase):
    def test_scene_audio_detection_keeps_legacy_single_track_compatible(self):
        self.assertTrue(worker._has_per_scene_audio({"scene_0": "audio"}, 3))
        self.assertTrue(worker._has_per_scene_audio({"0": "audio", "1": "audio"}, 3))
        self.assertFalse(worker._has_per_scene_audio({"0": "audio"}, 3))
        self.assertEqual(worker._get_scene_audio_payload({"scene_1": "scene", "1": "numeric"}, 1), "scene")

    def test_legacy_full_track_scene_cuts_follow_narration_length(self):
        scenes = [
            {"narration": "Short scene."},
            {"narration": "This scene contains considerably more spoken words."},
        ]
        durations = worker._allocate_legacy_scene_durations(scenes, 12.0)
        self.assertAlmostEqual(sum(durations), 12.0)
        self.assertLess(durations[0], durations[1])

    def test_general_renderer_uses_each_audio_duration_for_its_scene(self):
        scenes = [
            {"narration": "First scene narration."},
            {"narration": "Second scene narration."},
        ]
        custom_audios = {
            f"scene_{index}": "data:audio/wav;base64," + base64.b64encode(b"audio").decode()
            for index in range(2)
        }
        job_data = {
            "channel_config": {"language": "en", "shorts_mode": True},
            "script_data": {"title": "Scene sync", "scenes": scenes},
            "custom_audios": custom_audios,
            "tts_engine": "edge",
        }

        commands = []

        def fake_ffmpeg(command, **_kwargs):
            commands.append(command)
            Path(command[-1]).write_bytes(b"rendered")

        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            with patch.object(worker, "ensure_localized_script", side_effect=lambda script, _lang: script), \
                 patch.object(worker, "_probe_scene_audio_duration", side_effect=[1.25, 2.5]), \
                 patch.object(worker.subprocess, "run", side_effect=fake_ffmpeg):
                output = worker.render_general_job(job_data, work_dir)

        scene_commands = [
            command for command in commands
            if command[-1].endswith(".mp4") and "general_scene_video_" in command[-1]
        ]
        self.assertEqual(output.name, "final_video.mp4")
        self.assertEqual(len(scene_commands), 2)
        self.assertEqual(
            [scene_commands[0][scene_commands[0].index("-t") + 1], scene_commands[1][scene_commands[1].index("-t") + 1]],
            ["1.250000", "2.500000"],
        )
        self.assertTrue(any(str(value).endswith("general_scene_0.mp3") for value in scene_commands[0]))
        self.assertTrue(any(str(value).endswith("general_scene_1.mp3") for value in scene_commands[1]))


if __name__ == "__main__":
    unittest.main()
