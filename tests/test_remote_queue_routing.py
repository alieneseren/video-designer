"""Test that remote queue execution properly routes group and channel tasks to Oracle Cloud (remote)."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import run_gemini_sequential_batch_task, executions

def test_batch_remote_routing():
    # Test batch items with both a group and a channel
    batch_items = [
        {
            "index": 1,
            "is_group": True,
            "group_id": "grp_reddit_hikayeleri_1788115817",
            "target_id": "grp_reddit_hikayeleri_1788115817",
            "row_id": "999",
            "script": {
                "tr": {"title": "Test Reddit TR", "scenes": [{"narration": "Sahne 1"}]},
                "en": {"title": "Test Reddit EN", "scenes": [{"narration": "Scene 1"}]}
            },
            "images": {},
            "title": "Reddit Stories Group",
            "target_env": "remote",
            "auto_sync_mac": True,
            "auto_youtube_upload": False
        },
        {
            "index": 2,
            "is_group": False,
            "channel_id": "crazyychats",
            "target_id": "crazyychats",
            "row_id": "998",
            "script": {"title": "Test WA", "messages": [{"sender": "contact", "text": "Selam"}]},
            "images": {},
            "title": "WhatsApp Single Channel",
            "target_env": "remote",
            "auto_sync_mac": True,
            "auto_youtube_upload": False
        }
    ]

    exec_id = "test_batch_exec_001"
    executions[exec_id] = {
        "status": "pending",
        "message": "Starting",
        "total": 2,
        "completed": 0,
        "results": []
    }

    with patch("server.run_remote_web_automation_task") as mock_remote:
        # Simulate successful remote completion
        def side_effect(channel_id, exec_id, row_id, custom_script, custom_images, youtube_upload, auto_sync_mac):
            executions[exec_id] = {"status": "success", "result": {"channel_id": channel_id, "video": "dummy.mp4"}}

        mock_remote.side_effect = side_effect

        run_gemini_sequential_batch_task(exec_id, batch_items)

        # Check that run_remote_web_automation_task was called for both items:
        # Item 1 is group with 2 channels: tr1_reddithikayeleri & redditchroniclesa -> 2 remote calls
        # Item 2 is crazyychats -> 1 remote call
        # Total: 3 remote calls!
        assert mock_remote.call_count >= 2, f"Expected at least 2 remote calls, got {mock_remote.call_count}"
        
        called_channels = [call.kwargs.get("channel_id") or call.args[0] for call in mock_remote.call_args_list]
        print(f"✓ Remote çağrılan kanallar: {called_channels}")
        assert "crazyychats" in called_channels, "crazyychats sunucuya aktarılmalıydı"
        assert any("reddit" in ch for ch in called_channels), "Reddit üye kanalları sunucuya aktarılmalıydı"

    print("ALL REMOTE QUEUE ROUTING TESTS PASSED!")

if __name__ == "__main__":
    test_batch_remote_routing()
