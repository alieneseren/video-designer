import json
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from crayon_combat_engine import CURATED_CRAYON_COMBAT_TOPICS
from channel_manager import get_category_preset
from crayon_combat_engine import CRAYON_COMBAT_SYSTEM_PROMPT
from financial_documentary_engine import TECH_FINANCE_SYSTEM_PROMPT
from script_writer import _enrich_script_metadata
from stickman_engine.crayon_animation_pipeline import (
    H,
    W,
    _short_visual_phrase,
    render_crayon_kinetic_shot,
    select_scene_subshots,
    set_current_channel_id,
)
from stickman_engine.crayon_generator import _create_crayon_thumbnail


def test_tactical_crayon_duration_and_fact_safe_topics():
    channels = json.loads((PROJECT_ROOT / "config" / "channels.json").read_text(encoding="utf-8"))["channels"]
    channel = next(item for item in channels if item.get("channel_id") == "tacticallcrayon")
    assert channel["edit_options"]["video_duration"] == "420"
    preset = get_category_preset("crayon_combat", language="en", channel_name="Tactical Crayon")
    assert preset["edit_options"]["video_duration"] == "420"
    finance_preset = get_category_preset("crayon_capital", language="en")
    assert finance_preset["edit_options"]["video_duration"] == "420"
    assert all("cost" not in topic for topic in CURATED_CRAYON_COMBAT_TOPICS)
    assert all(topic.get("investigation_angle") for topic in CURATED_CRAYON_COMBAT_TOPICS)
    assert "6-8 minutes" in CRAYON_COMBAT_SYSTEM_PROMPT
    assert "6-8 minutes" in TECH_FINANCE_SYSTEM_PROMPT
    assert "4-6 seconds" in CRAYON_COMBAT_SYSTEM_PROMPT
    assert "4-6 seconds" in TECH_FINANCE_SYSTEM_PROMPT


def test_crayon_metadata_and_visual_selection():
    script = _enrich_script_metadata(
        {"title": "Combat Markings: The Detail Everyone Misses", "topic": "Combat Markings"},
        {"topic_category": "crayon_combat", "language": "en"},
    )
    assert len(script["title_variants"]) == 3
    assert all(len(option["title"]) < 75 for option in script["title_variants"])
    assert 2 <= len(script["thumbnail_text"].split()) <= 4

    set_current_channel_id("tacticallcrayon")
    try:
        shots, labels = select_scene_subshots(
            {
                "chapter": "A careful review",
                "narration": "This fictional example mentions a $54.8 billion marker only to test visual selection.",
            },
            idx=0,
            dur=20.0,
            vehicle_name="Tactical Crayon",
        )
    finally:
        set_current_channel_id("")
    assert shots == ["CRAYON_HOOK", "CRAYON_VISUAL", "CRAYON_EVIDENCE", "CRAYON_REACTION"]
    assert labels == shots

    set_current_channel_id("", "crayon_capital")
    try:
        finance_shots, finance_labels = select_scene_subshots(
            {"chapter": "Cash flow", "narration": "Follow the verified cash flow."},
            idx=0,
            dur=15.0,
            vehicle_name="A public company",
        )
    finally:
        set_current_channel_id("")
    assert len(finance_shots) == 3
    assert len(set(finance_shots)) == 3
    assert finance_labels == finance_shots
    assert _short_visual_phrase("One two three four five six seven eight", 6) == "One two three four five six"

    rendered_frames = []
    for shot_type in ("CRAYON_HOOK", "CRAYON_VISUAL", "CRAYON_EVIDENCE", "CRAYON_REACTION"):
        frame = Image.new("RGBA", (W, H), (15, 23, 42, 255))
        render_crayon_kinetic_shot(
            frame,
            ImageDraw.Draw(frame),
            {
                "chapter": "Cold open",
                "narration": "The documented surprise changes the engineering trade-off.",
                "character_dialogue": "That changes the whole argument.",
            },
            shot_type,
            1.0,
            5.0,
            Image.new("RGBA", (100, 100), (200, 50, 50, 255)),
            "crayon_combat",
        )
        rendered_frames.append(frame)
    assert all(ImageChops.difference(rendered_frames[0], frame).getbbox() for frame in rendered_frames[1:])


def test_crayon_thumbnail_is_upload_ready():
    with tempfile.TemporaryDirectory(prefix="crayon-thumbnail-test-") as temp:
        root = Path(temp)
        source = root / "source.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x123456:s=1280x720:d=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ],
            capture_output=True,
            check=True,
        )
        result = _create_crayon_thumbnail(source, root / "thumbnail.jpg", "MARKING MYSTERY")
        from PIL import Image

        with Image.open(result) as image:
            assert image.size == (1280, 720)
        assert result.stat().st_size > 1000


if __name__ == "__main__":
    test_tactical_crayon_duration_and_fact_safe_topics()
    test_crayon_metadata_and_visual_selection()
    test_crayon_thumbnail_is_upload_ready()
    print("CRAYON RETENTION TESTS PASSED")
