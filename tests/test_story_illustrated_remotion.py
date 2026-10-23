"""
tests/test_story_illustrated_remotion.py
Unit and integration test for Remotion Story Illustrated Video Pipeline.
"""

import os
import sys
import tempfile
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_story_illustrated_generation():
    from src.story_illustrated_generator import StoryIllustratedGenerator
    from src.remotion_renderer import is_remotion_available, render_story_illustrated_remotion
    
    assert is_remotion_available(), "Remotion ortamı hazır olmalıdır"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        
        # 1. Test Storyboard
        gen = StoryIllustratedGenerator(work_dir=tmp_p)
        sb = gen.generate_storyboard("Zamanın Durduğu Saat Kulesi")
        assert sb["title"] is not None
        assert len(sb["scenes"]) >= 2
        
        # 2. Test Sahne Görselleri Üretimi
        img_1 = tmp_p / "scene_1.jpg"
        img_2 = tmp_p / "scene_2.jpg"
        
        im1 = Image.new("RGB", (720, 1280), color=(25, 30, 45))
        im1.save(img_1, "JPEG")
        im2 = Image.new("RGB", (720, 1280), color=(45, 20, 30))
        im2.save(img_2, "JPEG")
        
        # 3. Test Ses Dosyası
        audio_file = tmp_p / "test_audio.mp3"
        # 3 saniyelik sessiz ses veya TTS
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "3",
            "-q:a", "9",
            str(audio_file)
        ]
        import subprocess
        subprocess.run(cmd, capture_output=True)
        assert audio_file.exists()
        
        # 4. Remotion Render
        out_video = tmp_p / "test_story_output.mp4"
        scenes = [
            {
                "id": 1,
                "image_path": str(img_1),
                "caption_text": "Gece yarısı saat kulesi aniden durdu.",
                "start_frame": 0,
                "duration_in_frames": 45,
                "camera_effect": "zoom_in",
            },
            {
                "id": 2,
                "image_path": str(img_2),
                "caption_text": "Usta elindeki parlayan anahtarla kapıyı araladı.",
                "start_frame": 45,
                "duration_in_frames": 45,
                "camera_effect": "pan_left",
            }
        ]
        
        print("Remotion Story Illustrated render testi başlatılıyor...")
        ok = render_story_illustrated_remotion(
            title="TEST SAAT KULESİ",
            scenes_data=scenes,
            audio_path=str(audio_file),
            output_path=str(out_video),
            theme="cinematic_dark",
            fps=30
        )
        
        assert ok, "Remotion render işlemi başarılı olmalı"
        assert out_video.exists(), "MP4 video dosyası oluşmalıdır"
        assert out_video.stat().st_size > 10000, "MP4 dosyası boş olmamalıdır"
        print(f"✓ Test Başarılı! Oluşan video: {out_video} ({out_video.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    test_story_illustrated_generation()
    print("\n🎉 REMOTION STORY ILLUSTRATED PIPELINE TEST PASSED!")
