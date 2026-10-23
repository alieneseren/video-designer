"""
tests/test_casper_batch3_features.py
Tests for Casper AI Batch 3 approved features & deduplication engine:
1. Universe Lore & Character Continuity (CharacterRAGManager & ScriptWriter)
2. EBU R128 Audio Loudness Normalization (video_editor.py & SubtitleBurner)
3. Clickbait Thumbnail Generator (video_editor.py & YouTubeUploaderAPI)
4. Hook Intro Zoom (apply_hook_intro_zoom & hyperframes_renderer.py)
5. Casper Deduplication Engine & DB Integrity
"""

import os
import sys
import tempfile
import numpy as np
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_casper_advisor_deduplication():
    from src.casper_advisor import CasperAdvisor, _normalize_title
    
    # Test title normalization
    t1 = "Kanal Karakterleri Arası Çapraz İlişki & Hikaye Devamlılığı (Universe Lore)"
    t2 = "kanal karakterleri arasi capraz iliski & hikaye devamliligi (universe lore) [v2]"
    norm1 = _normalize_title(t1)
    norm2 = _normalize_title(t2)
    assert "kanal" in norm1 and "karakterleri" in norm1
    
    CasperAdvisor.cleanup_duplicates()
    
    ideas = CasperAdvisor.list_ideas()
    seen = set()
    for idea in ideas:
        norm = _normalize_title(idea["title"])
        assert norm not in seen, f"Duplicate found in database: {idea['title']}"
        seen.add(norm)


def test_universe_lore_in_character_rag_and_script_writer():
    from src.character_rag import CharacterRAGManager
    
    rag = CharacterRAGManager()
    channel_id = "test_channel_lore"
    
    # Store some lore memories
    rag.add_memory(
        channel_id=channel_id,
        title="200 TL Borç Meselesi",
        summary="Ahmet dün Mehmet'e 200 TL borç verdi ve hala geri alamadı.",
        characters_involved=["Ahmet", "Mehmet"],
        key_events="200 TL borç"
    )
    
    lore = rag.retrieve_relevant_lore(channel_id, "Ahmet ile Mehmet borç tartışması", top_k_memories=2)
    memories = lore.get("memories", [])
    assert len(memories) >= 1
    assert any("200 TL" in m.get("summary", "") for m in memories)
    
    prompt_ctx = rag.get_prompt_context(channel_id, topic="Ahmet ve Mehmet buluşması")
    assert "UNIVERSE LORE" in prompt_ctx
    assert "200 TL borç" in prompt_ctx


def test_ebu_r128_loudness_normalizer():
    from src.video_editor import EditConfig, SubtitleBurner, normalize_audio_ebur128
    
    config = EditConfig(normalize_audio_loudness=True)
    assert config.normalize_audio_loudness is True
    
    burner = SubtitleBurner(config)
    assert burner is not None
    assert callable(normalize_audio_ebur128)


def test_clickbait_thumbnail_generator():
    from src.video_editor import generate_clickbait_thumbnail
    from moviepy import ColorClip
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a tiny 2-second test video
        test_video_path = str(Path(tmpdir) / "test_vid.mp4")
        clip = ColorClip((720, 1280), color=(100, 50, 150), duration=2.0)
        clip.write_videofile(test_video_path, fps=15, logger=None)
        clip.close()
        
        thumb_path = str(Path(tmpdir) / "out_thumb.jpg")
        generated = generate_clickbait_thumbnail(
            video_path=test_video_path,
            output_path=thumb_path,
            custom_title="BUNU KİMSE BEKLEMİYORDU #shorts",
            sample_count=2,
        )
        
        assert Path(generated).exists()
        assert Path(generated).stat().st_size > 1000
        
        with Image.open(generated) as img:
            assert img.width == 720
            assert img.height == 1280


def test_hook_intro_zoom_effect():
    from src.video_editor import apply_hook_intro_zoom
    from moviepy import ColorClip
    
    clip = ColorClip((200, 200), color=(255, 0, 0), duration=2.0)
    zoomed = apply_hook_intro_zoom(clip, hook_duration=1.0, start_scale=1.05)
    
    frame_0 = zoomed.get_frame(0.0)
    frame_end = zoomed.get_frame(1.5)
    
    assert frame_0.shape == (200, 200, 3)
    assert frame_end.shape == (200, 200, 3)
    clip.close()
    zoomed.close()


def test_hyperframes_hook_zoom_export():
    from src.hyperframes_renderer import apply_hook_zoom_filter
    assert callable(apply_hook_zoom_filter)


if __name__ == "__main__":
    print("Testing Casper Advisor Deduplication...")
    test_casper_advisor_deduplication()
    print("✓ Casper Advisor Deduplication passed.")

    print("Testing Universe Lore in Character RAG & Script Writer...")
    test_universe_lore_in_character_rag_and_script_writer()
    print("✓ Universe Lore passed.")

    print("Testing EBU R128 Loudness Normalizer...")
    test_ebu_r128_loudness_normalizer()
    print("✓ EBU R128 Loudness Normalizer passed.")

    print("Testing Clickbait Thumbnail Generator...")
    test_clickbait_thumbnail_generator()
    print("✓ Clickbait Thumbnail Generator passed.")

    print("Testing Hook Intro Zoom Effect...")
    test_hook_intro_zoom_effect()
    print("✓ Hook Intro Zoom Effect passed.")

    print("Testing HyperFrames Hook Zoom Export...")
    test_hyperframes_hook_zoom_export()
    print("✓ HyperFrames Hook Zoom Export passed.")

    print("\n🎉 ALL BATCH 3 TESTS PASSED SUCCESSFULLY!")

