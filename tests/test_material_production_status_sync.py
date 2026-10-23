import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import material_status_sync


class FakeMaterialsManager:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.updated = []

    def _resolve_target(self, channel_id):
        return False, channel_id, self.output_dir / channel_id

    def update_material_status(self, channel_id, material_id, status):
        self.updated.append((channel_id, material_id, status))
        return True


def test_remote_completed_video_updates_material_status():
    manager = FakeMaterialsManager(tempfile.gettempdir())
    material = {
        "id": "mat_test",
        "material_id": "mat_test",
        "channel_id": "tacticallcrayon",
        "row_id": "4",
        "status": "in_cloud_queue",
    }
    remote_runner = MagicMock()
    remote_runner.list_server_videos.return_value = [
        {
            "channel_id": "tacticallcrayon",
            "job_id": "exec_mat_test",
            "row_id": "4",
        }
    ]
    remote_runner.get_queue_status.return_value = {}
    planner = MagicMock()

    with patch("remote_runner.RemoteRunner", return_value=remote_runner), patch(
        "browser_uploader.find_planned_video_folder", return_value=None
    ), patch("content_planner.ContentPlanner", return_value=planner):
        material_status_sync.sync_materials_with_generated_videos(manager, [material])

    assert material["status"] == "produced"
    assert manager.updated == [("tacticallcrayon", "mat_test", "produced")]
    planner.mark_as_produced.assert_called_once_with("4")


def test_cloud_queue_job_without_final_video_remains_queued():
    manager = FakeMaterialsManager(tempfile.gettempdir())
    material = {
        "id": "mat_pending",
        "material_id": "mat_pending",
        "channel_id": "tacticallcrayon",
        "row_id": "5",
        "status": "in_cloud_queue",
    }
    remote_runner = MagicMock()
    remote_runner.list_server_videos.return_value = []
    remote_runner.get_queue_status.return_value = {}

    with patch("remote_runner.RemoteRunner", return_value=remote_runner), patch(
        "browser_uploader.find_planned_video_folder", return_value=None
    ):
        material_status_sync.sync_materials_with_generated_videos(manager, [material])

    assert material["status"] == "in_cloud_queue"
    assert manager.updated == []


def test_active_cloud_job_is_not_marked_produced_from_an_older_local_video():
    manager = FakeMaterialsManager(tempfile.gettempdir())
    material = {
        "id": "mat_active",
        "material_id": "mat_active",
        "channel_id": "tacticallcrayon",
        "row_id": "6",
        "status": "in_cloud_queue",
    }
    remote_runner = MagicMock()
    remote_runner.list_server_videos.return_value = []
    remote_runner.get_queue_status.return_value = {
        "current_job": "exec_mat_active",
        "queue_files": [],
    }

    with patch("remote_runner.RemoteRunner", return_value=remote_runner), patch(
        "browser_uploader.find_planned_video_folder", return_value={"video_path": "old-final.mp4"}
    ):
        material_status_sync.sync_materials_with_generated_videos(manager, [material])

    assert material["status"] == "in_cloud_queue"
    assert manager.updated == []


def test_find_planned_video_supports_final_video_filename():
    from browser_uploader import find_planned_video_folder

    with tempfile.TemporaryDirectory(prefix="produced-video-status-") as temp:
        output = Path(temp)
        video_dir = output / "tacticallcrayon" / "yuklenecek" / "completed-job"
        video_dir.mkdir(parents=True)
        (video_dir / "final_video.mp4").write_bytes(b"video")
        (video_dir / "metadata.json").write_text('{"plan_id": "4"}', encoding="utf-8")

        found = find_planned_video_folder(
            "tacticallcrayon",
            "4",
            output_base_dir=str(output),
        )
        assert found is not None
        assert found["video_path"] == str(video_dir / "final_video.mp4")


if __name__ == "__main__":
    test_remote_completed_video_updates_material_status()
    test_cloud_queue_job_without_final_video_remains_queued()
    test_active_cloud_job_is_not_marked_produced_from_an_older_local_video()
    test_find_planned_video_supports_final_video_filename()
    print("MATERIAL PRODUCTION STATUS TESTS PASSED")
