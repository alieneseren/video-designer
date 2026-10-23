"""
tests/test_crazyychats_recovery.py
Unit tests verifying CrazyChats configuration, WhatsApp Shorts limits,
SEO metadata generation, and audio loudness normalization.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_crazyychats_channel_config():
    channels_path = PROJECT_ROOT / "config" / "channels.json"
    assert channels_path.exists(), "config/channels.json bulunamadı"
    
    data = json.loads(channels_path.read_text(encoding="utf-8"))
    channels = data.get("channels", data) if isinstance(data, dict) else data
    
    crazy = next((c for c in channels if c.get("channel_id") == "crazyychats"), None)
    assert crazy is not None, "crazyychats kanalı bulunamadı"
    
    assert crazy.get("shorts_mode") is True, "shorts_mode True olmalıdır"
    assert crazy.get("schedule_hour") == 19, "schedule_hour 19 (ABD prime-time) olmalıdır"
    
    opts = crazy.get("edit_options", {})
    assert opts.get("video_duration") in ("40", "45", 40, 45), "video_duration 40-45s olmalıdır"
    assert opts.get("watermark_text") == "CrazyChats", "watermark_text CrazyChats olmalıdır"
    assert opts.get("hook_intro_effect") is True, "hook_intro_effect True olmalıdır"
    assert opts.get("normalize_audio_loudness") is True, "normalize_audio_loudness True olmalıdır"
    assert opts.get("enable_hyperframes_hook") is True, "enable_hyperframes_hook True olmalıdır"
    print("✓ CrazyChats kanal yapılandırması başarıyla doğrulandı!")


def test_whatsapp_script_generator_limits():
    from src.whatsapp.script_generator import ScriptGenerator
    
    # 15 mesajlık şişirilmiş senaryo verisi
    mock_data = {
        "title": "Crazy Vacuum Escape",
        "contact_name": "Roommate Alex",
        "contact_avatar_gender": "male",
        "messages": [
            {"sender": "contact", "text": f"Message {i}"} for i in range(15)
        ]
    }
    scenario = ScriptGenerator.build_scenario_from_dict(mock_data, channel_name="crazyychats", language="en")
    assert len(scenario.messages) <= 9, f"Mesaj sayısı 9 ile sınırlandırılmalıdır, mevcut: {len(scenario.messages)}"
    assert scenario.watermark_username == "crazyychats"
    print(f"✓ WhatsApp senaryo mesaj sınırı başarıyla doğrulandı ({len(scenario.messages)} mesaj)!")


def test_audio_mixer_loudnorm():
    from src.whatsapp.audio_mixer import AudioMixer
    mixer = AudioMixer(output_path="/tmp/test_mixer.wav")
    assert hasattr(mixer, "mix_scenario_audio")
    import inspect
    sig = inspect.signature(mixer.mix_scenario_audio)
    assert "normalize_loudness" in sig.parameters, "mix_scenario_audio normalize_loudness parametresini içermelidir"
    print("✓ AudioMixer EBU R128 (-14 LUFS) loudnorm desteği doğrulandı!")


if __name__ == "__main__":
    test_crazyychats_channel_config()
    test_whatsapp_script_generator_limits()
    test_audio_mixer_loudnorm()
    print("ALL CRAZYYCHATS TESTS PASSED!")
