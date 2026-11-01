import asyncio
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from video_generator import (
    VideoGenerator,
    AudioGenerator,
    _scene_word_ranges,
    _truncate_scenes_to_word_limit,
)


class VideoSceneSyncTests(unittest.TestCase):
    def test_build_segments_preserves_tts_pause_at_scene_boundary(self):
        generator = VideoGenerator.__new__(VideoGenerator)
        boundaries = [
            {"text": "The first scene ends.", "offset": 0.0, "duration": 1.0, "image_path": "scene-0.jpg"},
            {"text": "The second scene starts.", "offset": 1.5, "duration": 0.8, "image_path": "scene-1.jpg"},
        ]

        segments = generator._build_segments(
            boundaries=boundaries,
            real_duration=2.5,
            is_story_mode=False,
            images=[],
            scene_images={},
            work_dir=Path("."),
            keywords=[],
            composer_w=1080,
            composer_h=1920,
        )

        self.assertEqual([segment["image_path"] for segment in segments], ["scene-0.jpg", "scene-1.jpg"])
        self.assertAlmostEqual(segments[0]["duration"], 1.5)
        self.assertAlmostEqual(segments[1]["duration"], 1.0)
        self.assertAlmostEqual(sum(segment["duration"] for segment in segments), 2.5)

    def test_scene_word_ranges_follow_the_script_order(self):
        scenes = [
            {"narration": "One two three."},
            {"narration": "Four five."},
        ]
        self.assertEqual(_scene_word_ranges(scenes), [(0, 3), (3, 5)])

    def test_short_truncation_keeps_visual_scenes_aligned_to_spoken_text(self):
        scenes = [
            {"narration": "One two three.", "image_prompt": "first scene"},
            {"narration": "Four five six.", "image_prompt": "second scene"},
        ]

        truncated = _truncate_scenes_to_word_limit(scenes, 4)

        self.assertEqual(len(truncated), 2)
        self.assertEqual(truncated[0]["narration"], "One two three.")
        self.assertEqual(truncated[1]["narration"], "Four.")
        self.assertEqual(truncated[1]["image_prompt"], "second scene")

    def test_edge_tts_synthesizes_scene_audio_with_explicit_scene_ids(self):
        class FakeCommunicate:
            def __init__(self, text, voice):
                self.text = text

            async def stream(self):
                yield {"type": "audio", "data": b"audio"}
                yield {
                    "type": "SentenceBoundary",
                    "text": self.text,
                    "offset": 0,
                    "duration": 8_000_000,
                }

        class FakeAudioClip:
            def __init__(self, _path):
                self.duration = 1.0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        class FakeWatermarker:
            @staticmethod
            def embed(*_args, **_kwargs):
                return True

        generator = AudioGenerator.__new__(AudioGenerator)
        generator.settings = SimpleNamespace(
            get=lambda key, default=None: "edge-tts" if key == "tts_engine" else default
        )
        scenes = [
            {"narration": "First scene."},
            {"narration": "Second scene."},
        ]
        with patch("video_generator.edge_tts.Communicate", FakeCommunicate), \
             patch("video_generator.AudioFileClip", FakeAudioClip), \
             patch(
                 "video_generator.subprocess.run",
                 side_effect=lambda command, **_kwargs: (
                     Path(command[-1]).write_bytes(b"joined-audio")
                     and subprocess.CompletedProcess(command, 0, "", "")
                 ),
             ) as run_ffmpeg, \
             patch.dict(sys.modules, {
                 "audio_watermark": SimpleNamespace(AudioWatermarker=FakeWatermarker)
             }), \
             tempfile.TemporaryDirectory() as tmp:
                output_path = str(Path(tmp) / "narration.mp3")
                ok, boundaries = asyncio.run(
                    generator.generate("First scene. Second scene.", "en", output_path, scenes=scenes)
                )

        self.assertTrue(ok)
        self.assertEqual([boundary["scene_idx"] for boundary in boundaries], [0, 1])
        self.assertEqual([boundary["offset"] for boundary in boundaries], [0.0, 1.0])
        self.assertTrue(any("-filter_complex" in call.args[0] for call in run_ffmpeg.call_args_list))


if __name__ == "__main__":
    unittest.main()
