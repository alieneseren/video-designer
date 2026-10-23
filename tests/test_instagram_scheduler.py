from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import server
from instagram_scheduler import InstagramScheduleStore


class InstagramSchedulerTests(unittest.TestCase):
    def test_create_schedule_only_queues_and_cancel_removes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            video_dir = base / "ig_channel" / "yuklenecek" / "sample_video"
            video_dir.mkdir(parents=True)
            (video_dir / "final.mp4").write_bytes(b"test-video")
            store = InstagramScheduleStore(base / "schedules.json")
            channel = {
                "channel_id": "ig_channel",
                "name": "Test channel",
                "language": "tr",
                "instagram": True,
                "instagram_username": "test.reels",
            }
            original_settings = server.settings_mgr
            settings = {"output_dir": str(base)}
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": settings.get(key, default))
            future = datetime.now(ZoneInfo("Europe/Istanbul")) + timedelta(days=2)
            payload = server.InstagramScheduleRequest(
                folder="ig_channel/yuklenecek/sample_video",
                scheduled_date=future.strftime("%Y-%m-%d"),
                scheduled_time=future.strftime("%H:%M"),
                caption="Scheduled test",
            )
            try:
                with patch.object(server, "ChannelManager") as manager_cls, \
                     patch.object(server, "instagram_schedule_store", store):
                    manager_cls.return_value.get_channel.return_value = channel
                    result = server.create_instagram_schedule(payload)
                    self.assertTrue(result["success"])
                    self.assertEqual(result["schedule"]["status"], "scheduled")
                    self.assertEqual(len(store.list("ig_channel")), 1)
                    self.assertEqual(result["schedule"]["video_path"], str((video_dir / "final.mp4").resolve()))
                    with self.assertRaises(server.HTTPException) as duplicate:
                        server.create_instagram_schedule(payload)
                    self.assertEqual(duplicate.exception.status_code, 409)
                    self.assertTrue(server.cancel_instagram_schedule(result["schedule"]["id"])["success"])
                    self.assertEqual(store.list(), [])
            finally:
                server.settings_mgr = original_settings

    def test_due_schedule_is_claimed_and_completed_by_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            video_dir = base / "ig_channel" / "video"
            video_dir.mkdir(parents=True)
            video_path = video_dir / "final.mp4"
            video_path.write_bytes(b"video")
            store = InstagramScheduleStore(base / "schedules.json")
            entry = store.create({
                "channel_id": "ig_channel",
                "instagram_username": "test.reels",
                "folder": "ig_channel/video",
                "video_path": str(video_path),
                "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            })
            original_settings = server.settings_mgr
            server.settings_mgr = SimpleNamespace(get=lambda key, default="": str(base) if key == "output_dir" else default)
            try:
                with patch.object(server, "instagram_schedule_store", store):
                    claim_result = server.claim_due_instagram_schedule()
                    self.assertEqual(claim_result["schedule"]["id"], entry["id"])
                    self.assertEqual(claim_result["schedule"]["status"], "publishing")
                    result = server.finish_instagram_schedule(
                        entry["id"],
                        server.InstagramScheduleResult(success=True),
                    )
                    self.assertEqual(result["status"], "published")
                    self.assertEqual(store.list()[0]["status"], "published")
                    metadata = json.loads((video_dir / "video_info.json").read_text(encoding="utf-8"))
                    self.assertTrue(metadata["uploaded_instagram"])
            finally:
                server.settings_mgr = original_settings

    def test_uncertain_share_result_stops_automatic_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InstagramScheduleStore(Path(tmp) / "schedules.json")
            entry = store.create({
                "channel_id": "ig_channel",
                "folder": "ig_channel/video",
                "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            })
            store.claim_due()
            with patch.object(server, "instagram_schedule_store", store):
                result = server.finish_instagram_schedule(
                    entry["id"],
                    server.InstagramScheduleResult(success=False, error="No confirmation", uncertain=True),
                )
            self.assertEqual(result["status"], "needs_review")
            self.assertEqual(store.list()[0]["status"], "needs_review")

    def test_queue_claims_only_scheduled_items_that_are_due(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InstagramScheduleStore(Path(tmp) / "schedules.json")
            future = datetime.now(ZoneInfo("UTC")) + timedelta(days=1)
            entry = store.create(
                {
                    "channel_id": "ig_channel",
                    "folder": "ig_channel/video",
                    "scheduled_at": future.isoformat(),
                }
            )
            self.assertIsNone(store.claim_due())
            claimed = store.claim_due(future + timedelta(seconds=1))
            self.assertEqual(claimed["id"], entry["id"])
            self.assertEqual(claimed["status"], "publishing")
            self.assertEqual(claimed["attempts"], 1)


if __name__ == "__main__":
    unittest.main()
