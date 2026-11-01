from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from video_voiceover import (
    VideoVoiceoverManager,
    build_mux_command,
    build_timeline_audio_command,
)


class VideoVoiceoverTests(unittest.TestCase):
    def test_shorter_voice_replaces_audio_and_keeps_video_stream(self):
        command = build_mux_command(
            "ffmpeg", "source.mp4", "voice.wav", "output.mp4", 30.0, 20.0
        )
        self.assertIn("0:v:0", command)
        self.assertIn("1:a:0", command)
        self.assertIn("-c:v", command)
        self.assertEqual(command[command.index("-c:v") + 1], "copy")
        self.assertIn("apad=whole_dur=30.000", command)
        self.assertNotIn("0:a:0", command)
        self.assertIn("0:s?", command)
        self.assertIn("mov_text", command)

    def test_longer_voice_extends_video_without_truncating_speech(self):
        command = build_mux_command(
            "ffmpeg", "source.mp4", "voice.wav", "output.mp4", 20.0, 28.0
        )
        self.assertIn("tpad=stop_mode=clone:stop_duration=8.000", command)
        self.assertIn("libx264", command)
        self.assertIn("28.000", command)
        self.assertIn("0:s?", command)
        self.assertIn("mov_text", command)

    def test_timeline_audio_uses_transcription_boundaries_and_speeds_up_long_segments(self):
        command = build_timeline_audio_command(
            "ffmpeg",
            [
                {
                    "audio_path": "first.wav",
                    "start": 2.0,
                    "end": 4.0,
                    "audio_duration": 3.0,
                },
                {
                    "audio_path": "second.wav",
                    "start": 5.0,
                    "end": 7.0,
                    "audio_duration": 1.5,
                },
            ],
            "timeline.wav",
            10.0,
        )
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("atempo=1.500000", filters)
        self.assertIn("adelay=delays=2000:all=1", filters)
        self.assertIn("adelay=delays=5000:all=1", filters)
        self.assertIn("apad=whole_dur=10.000000", filters)
        self.assertIn("-map", command)
        self.assertIn("[out]", command)

    def test_subtitle_sidecars_are_copied_with_the_voiceover_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "source.mp4"
            source.write_bytes(b"video")
            subtitle = folder / "subtitles.srt"
            subtitle.write_text("subtitle data", encoding="utf-8")
            output = folder / "source_voice_clone.mp4"

            copied = VideoVoiceoverManager._copy_subtitle_sidecars(source, output)

            output_subtitle = folder / "source_voice_clone.srt"
            self.assertEqual(copied, [str(output_subtitle)])
            self.assertEqual(output_subtitle.read_text(encoding="utf-8"), "subtitle data")
            self.assertEqual(subtitle.read_text(encoding="utf-8"), "subtitle data")

    def test_voiceover_uses_selected_clone_and_preserves_original_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "final.mp4"
            source.write_bytes(b"original video")
            voice_prompt = folder / "voice.pt"
            voice_prompt.write_bytes(b"voice profile")
            output_path = folder / "final_voice_clone-1.mp4"
            manager = VideoVoiceoverManager()
            manager._jobs.clear()
            manager._jobs["test-job"] = {"job_id": "test-job", "status": "queued"}

            class FakeWhisper:
                def __init__(self, *args, **kwargs):
                    pass

                def transcribe(self, *args, **kwargs):
                    return iter([
                        SimpleNamespace(text=" A test sentence. ", start=0.5, end=2.5),
                        SimpleNamespace(text=" Another sentence.", start=4.0, end=6.0),
                    ]), SimpleNamespace(language="en")

            class FakeGenerator:
                calls = []

                def generate(self, *, text, lang, output_path, audio_prompt_path, require_audio_prompt):
                    self.calls.append((text, lang, audio_prompt_path, require_audio_prompt))
                    Path(output_path).write_bytes(b"w" * 2000)
                    return True, []

            generator = FakeGenerator()
            modules = {
                "faster_whisper": SimpleNamespace(WhisperModel=FakeWhisper),
                "chatterbox.mtl_tts": SimpleNamespace(SUPPORTED_LANGUAGES={"en": "English"}),
                "chatterbox_generator": SimpleNamespace(
                    ChatterboxAudioGenerator=lambda: generator
                ),
            }

            def fake_run(command, **kwargs):
                if "-show_entries" in command:
                    media_path = command[-1]
                    duration = (
                        "20.0" if media_path == str(source)
                        else "4.0" if "segment_" in media_path
                        else "20.0"
                    )
                    return SimpleNamespace(stdout=duration)
                Path(command[-1]).write_bytes(b"v" * 20000)
                return SimpleNamespace(stdout="")

            with patch.dict(sys.modules, modules), \
                 patch("video_voiceover.shutil.which", side_effect=lambda name: name), \
                 patch("video_voiceover.subprocess.run", side_effect=fake_run):
                manager._run_job("test-job", source, "clone-1", "Test Clone", voice_prompt)

            job = manager.get_job("test-job")
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["result"]["video_path"], str(output_path))
            self.assertEqual(generator.calls, [
                ("A test sentence.", "en", str(voice_prompt), True),
                ("Another sentence.", "en", str(voice_prompt), True),
            ])
            self.assertEqual(job["result"]["aligned_segments"], 2)
            self.assertEqual(source.read_bytes(), b"original video")
            self.assertTrue(output_path.is_file())


if __name__ == "__main__":
    unittest.main()
