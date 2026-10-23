import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from remote_runner import RemoteRunner


def test_crayon_queue_does_not_embed_unused_local_audio():
    with tempfile.TemporaryDirectory(prefix="crayon-queue-test-") as temp:
        material_dir = Path(temp)
        audio_file = material_dir / "scene_0_audio.wav"
        audio_file.write_bytes(b"local audio that the remote Crayon renderer regenerates" * 100_000)

        runner = RemoteRunner()
        uploaded_payloads = []
        ssh_commands = []

        def fake_scp(command, **kwargs):
            payload_path = Path(command[-2])
            uploaded_payloads.append(json.loads(payload_path.read_text(encoding="utf-8")))
            return subprocess.CompletedProcess(command, 0, "", "")

        def fake_ssh(command, timeout=25):
            ssh_commands.append(command)
            if command.startswith("python3 -c "):
                return 0, json.dumps({"verified": ["exec_test_crayon_material.json"]}), ""
            return 0, "ok", ""

        item = {
            "material_id": "test_crayon_material",
            "channel_id": "tacticallcrayon",
            "row_id": "1",
            "title": "A documented design trade-off",
            "script": {
                "title": "A documented design trade-off",
                "scenes": [{"chapter": "Cold open", "narration": "The first verified detail changes the story."}],
            },
            "folder_path": str(material_dir),
        }

        with patch("remote_runner.subprocess.run", side_effect=fake_scp), patch.object(
            runner, "_run_ssh_cmd", side_effect=fake_ssh
        ), patch.object(runner, "_remote_tts_options", return_value={}):
            result = runner.dispatch_batch_to_cloud_queue([item])

        assert result["success"] is True
        assert len(uploaded_payloads) == 1
        assert uploaded_payloads[0]["custom_audios"] == {}
        assert len(json.dumps(uploaded_payloads[0])) < audio_file.stat().st_size
        assert any(".incoming/" in command for command in ssh_commands)
        verification = next(command for command in ssh_commands if command.startswith("python3 -c "))
        assert "json.load" in verification
        assert "os.replace" in verification


if __name__ == "__main__":
    test_crayon_queue_does_not_embed_unused_local_audio()
    print("REMOTE CRAYON QUEUE TEST PASSED")
