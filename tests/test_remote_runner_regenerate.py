from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from remote_runner import RemoteRunner


class RemoteRunnerRegenerateTests(unittest.TestCase):
    def setUp(self):
        self.runner = RemoteRunner(
            host="example.invalid",
            user="ubuntu",
            key_path="/tmp/unused-key",
            remote_dir="/srv/remote-worker",
        )

    def test_regeneration_requeues_only_the_selected_video_without_auto_upload(self):
        self.runner._run_ssh_cmd = Mock(side_effect=[
            (0, json.dumps({
                "success": True,
                "job_id": "job-1_refresh_20261029_ab12cd",
                "channel_id": "channel-1",
                "source_job_id": "job-1",
            }), ""),
            (0, "queue started", ""),
        ])

        result = self.runner.regenerate_server_video("channel-1", "job-1")

        self.assertTrue(result["success"])
        self.assertEqual(result["source_job_id"], "job-1")
        self.assertEqual(self.runner._run_ssh_cmd.call_count, 2)
        enqueue_command = self.runner._run_ssh_cmd.call_args_list[0].args[0]
        self.assertIn("regenerated_from_job_id", enqueue_command)
        self.assertIn('payload["youtube_upload"] = False', enqueue_command)
        self.assertIn("final_video.mp4", enqueue_command)
        self.assertIn("queue_path", enqueue_command)
        self.assertIn("Bu video için yeniden üretim zaten kuyrukta.", enqueue_command)

    def test_regeneration_rejects_unsafe_path_identifiers(self):
        with self.assertRaises(ValueError):
            self.runner.regenerate_server_video("../channel", "job-1")
        self.runner._run_ssh_cmd = Mock()
        self.assertFalse(self.runner._run_ssh_cmd.called)

    def test_regeneration_reports_missing_source_payload(self):
        self.runner._run_ssh_cmd = Mock(return_value=(
            2,
            json.dumps({
                "success": False,
                "message": "Bu videonun üretim materyali sunucuda bulunamadı.",
            }),
            "",
        ))

        with self.assertRaisesRegex(RuntimeError, "üretim materyali"):
            self.runner.regenerate_server_video("channel-1", "job-1")

        self.assertEqual(self.runner._run_ssh_cmd.call_count, 1)


if __name__ == "__main__":
    unittest.main()
