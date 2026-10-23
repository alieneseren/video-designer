"""Test get_group_gemini_prompt endpoint and prompt generation across different categories."""
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from channel_manager import ChannelManager
from content_planner import ContentPlanner
from settings_manager import SettingsManager
from server import get_group_gemini_prompt

def test_group_gemini_prompt():
    mgr = ChannelManager()
    groups = mgr.all_groups()
    assert len(groups) > 0, "En az bir grup olmalıdır."
    
    for group in groups:
        group_id = group["id"]
        settings_mgr = SettingsManager()
        output_dir = settings_mgr.get("output_dir", "output")
        grp_dir = Path(output_dir) / "groups" / group_id
        planner = ContentPlanner(grp_dir)
        items = planner.get_plan()
        if not items:
            continue
        
        row_id = items[0]["id"]
        
        # Test original category
        res = get_group_gemini_prompt(group_id, str(row_id))
        assert res["success"] is True
        assert "prompt" in res
        assert len(res["prompt"]) > 100
        assert "Task:" in res["prompt"]
        print(f"✓ get_group_gemini_prompt ({group.get('topic_category')}) başarıyla çalıştı! [Grup: {group_id}]")
        
        # Test category branching: whatsapp_stories, reddit_stories, generic fallback
        for cat in ["whatsapp_stories", "reddit_stories", "space_science"]:
            with patch.object(ChannelManager, 'get_group') as mock_grp:
                g_copy = dict(group)
                g_copy["topic_category"] = cat
                mock_grp.return_value = g_copy
                res_cat = get_group_gemini_prompt(group_id, str(row_id))
                assert res_cat["success"] is True
                assert "prompt" in res_cat
                assert len(res_cat["prompt"]) > 100
                print(f"  ✓ Kategori dalı '{cat}' sorunsuz prompt üretti.")

if __name__ == "__main__":
    test_group_gemini_prompt()
    print("ALL GROUP PROMPT TESTS PASSED!")
