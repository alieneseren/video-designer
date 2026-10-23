"""
tests/test_category_presets.py
Tests for automated category-based channel preset configuration.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.channel_manager import ChannelManager, get_category_preset, normalize_category_name


def test_category_normalization():
    assert normalize_category_name("whatsapp") == "whatsapp_stories"
    assert normalize_category_name("reddit") == "reddit_stories"
    assert normalize_category_name("blackbox") == "aviation"
    assert normalize_category_name("muzik") == "music"
    assert normalize_category_name("uzay") == "space"
    print("✓ normalize_category_name başarıyla doğrulandı!")


def test_category_presets_retrieval():
    wp_preset = get_category_preset("whatsapp_stories", language="tr", channel_name="YazanYazana")
    assert wp_preset["shorts_mode"] is True
    assert wp_preset["schedule_hour"] == 19
    assert wp_preset["edit_options"]["video_duration"] == "40"
    assert wp_preset["edit_options"]["youtube_category"] == "comedy"

    reddit_preset = get_category_preset("reddit_stories", language="en", channel_name="RedditChronicles")
    assert reddit_preset["shorts_mode"] is True
    assert reddit_preset["schedule_hour"] == 19
    assert reddit_preset["edit_options"]["video_duration"] == "48"
    assert reddit_preset["edit_options"]["youtube_category"] == "entertainment"

    aviation_preset = get_category_preset("aviation", language="en")
    assert aviation_preset["shorts_mode"] is False
    assert aviation_preset["edit_options"]["video_duration"] == "300"
    print("✓ get_category_preset başarıyla doğrulandı!")


def test_apply_category_preset_live():
    mgr = ChannelManager()
    ch = mgr.get_channel("tr1_reddithikayeleri")
    assert ch is not None
    assert ch["shorts_mode"] is True
    assert ch["schedule_hour"] == 19
    assert ch["edit_options"]["video_duration"] == "48"
    assert ch["edit_options"]["normalize_audio_loudness"] is True
    assert ch["edit_options"]["hook_intro_effect"] is True
    print("✓ Canlı kanal kategori ayarları doğrulandı!")


if __name__ == "__main__":
    test_category_normalization()
    test_category_presets_retrieval()
    test_apply_category_preset_live()
    print("ALL CATEGORY PRESET TESTS PASSED!")
