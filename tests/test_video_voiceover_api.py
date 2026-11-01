from __future__ import annotations

import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from starlette.datastructures import UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import server


class VideoVoiceoverApiTests(unittest.TestCase):
    def test_uploaded_video_is_saved_inside_voiceover_import_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "output"
            original_settings = server.settings_mgr
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": str(root) if key == "output_dir" else default)
            upload = UploadFile(filename="../My video.MOV", file=BytesIO(b"video-bytes"))
            try:
                result = server.upload_video_for_voiceover(upload)
                saved_path = Path(result["video_path"])
                self.assertEqual(saved_path.parent.resolve(), (root / "_voiceover_uploads").resolve())
                self.assertEqual(saved_path.suffix, ".mov")
                self.assertEqual(saved_path.read_bytes(), b"video-bytes")
                self.assertEqual(result["filename"], "My video.MOV")
            finally:
                server.settings_mgr = original_settings

    def test_unsupported_upload_extension_is_rejected(self):
        upload = UploadFile(filename="not-a-video.txt", file=BytesIO(b"data"))
        with self.assertRaises(server.HTTPException) as error:
            server.upload_video_for_voiceover(upload)
        self.assertEqual(error.exception.status_code, 400)
        upload.file.close()

    def test_empty_uploaded_video_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "output"
            original_settings = server.settings_mgr
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": str(root) if key == "output_dir" else default)
            upload = UploadFile(filename="empty.mp4", file=BytesIO())
            try:
                with self.assertRaises(server.HTTPException) as error:
                    server.upload_video_for_voiceover(upload)
                self.assertEqual(error.exception.status_code, 400)
                self.assertEqual(list((root / "_voiceover_uploads").iterdir()), [])
            finally:
                server.settings_mgr = original_settings

    def test_selected_chatterbox_clone_is_accepted_without_rvc_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "channel" / "final.mov"
            video.parent.mkdir()
            video.write_bytes(b"video")
            prompt = root / "voice.pt"
            prompt.write_bytes(b"prompt")
            original_settings = server.settings_mgr
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": str(root) if key == "output_dir" else default)

            class FakeCloneManager:
                def get_clone(self, clone_id):
                    self.selected_clone_id = clone_id
                    return {"id": clone_id, "name": "My voice", "voice_pt_path": str(prompt)}

            class FakeVoiceoverManager:
                def start_job(self, **kwargs):
                    self.job = kwargs
                    return "voiceover-test-job"

            clone_manager = FakeCloneManager()
            voiceover_manager = FakeVoiceoverManager()
            modules = {
                "voice_clone_manager": SimpleNamespace(VoiceCloneManager=lambda: clone_manager),
                "video_voiceover": SimpleNamespace(VideoVoiceoverManager=lambda: voiceover_manager),
            }
            try:
                with patch.dict(sys.modules, modules):
                    result = server.start_video_voiceover(
                        server.VideoVoiceoverRequest(video_path=str(video), clone_id="clone-123")
                    )
                self.assertEqual(result["job_id"], "voiceover-test-job")
                self.assertEqual(clone_manager.selected_clone_id, "clone-123")
                self.assertEqual(voiceover_manager.job["voice_prompt_path"], prompt)
            finally:
                server.settings_mgr = original_settings

    def test_video_path_outside_output_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "output"
            root.mkdir()
            outside_video = Path(tmp) / "private.mp4"
            outside_video.write_bytes(b"video")
            original_settings = server.settings_mgr
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": str(root) if key == "output_dir" else default)
            try:
                with self.assertRaises(server.HTTPException) as error:
                    server.start_video_voiceover(
                        server.VideoVoiceoverRequest(video_path=str(outside_video), clone_id="clone-123")
                    )
                self.assertEqual(error.exception.status_code, 400)
            finally:
                server.settings_mgr = original_settings

    def test_completed_voiceover_is_streamed_from_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "final_voice_clone.mp4"
            output.write_bytes(b"voiced video")
            original_settings = server.settings_mgr
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": str(root) if key == "output_dir" else default)
            modules = {
                "video_voiceover": SimpleNamespace(
                    VideoVoiceoverManager=lambda: SimpleNamespace(
                        get_job=lambda job_id: {
                            "status": "completed",
                            "result": {"video_path": str(output)},
                        }
                    )
                )
            }
            try:
                with patch.dict(sys.modules, modules):
                    response = server.get_video_voiceover_output("voiceover-test-job")
                self.assertEqual(Path(response.path).resolve(), output.resolve())
            finally:
                server.settings_mgr = original_settings

    def test_voiceover_result_outside_output_folder_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "output"
            root.mkdir()
            outside_output = Path(tmp) / "private.mp4"
            outside_output.write_bytes(b"private")
            original_settings = server.settings_mgr
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": str(root) if key == "output_dir" else default)
            modules = {
                "video_voiceover": SimpleNamespace(
                    VideoVoiceoverManager=lambda: SimpleNamespace(
                        get_job=lambda job_id: {
                            "status": "completed",
                            "result": {"video_path": str(outside_output)},
                        }
                    )
                )
            }
            try:
                with patch.dict(sys.modules, modules):
                    with self.assertRaises(server.HTTPException) as error:
                        server.get_video_voiceover_output("voiceover-test-job")
                self.assertEqual(error.exception.status_code, 400)
            finally:
                server.settings_mgr = original_settings


if __name__ == "__main__":
    unittest.main()
