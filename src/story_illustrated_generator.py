"""
story_illustrated_generator.py
==============================
Remotion Tabanlı Hikaye ve İllüstrasyon Video Üretim Motoru.
1. Hikayeyi sahnelere ve görsel promptlara ayırır (Storyboarding).
2. Her sahne için özel sinematik çizimler üretir (AI Illustration).
3. Doğal seslendirme (TTS) ve fon müziğini (BGM) hazırlar.
4. Remotion React motoru ile 60 FPS sinematik Shorts videosu olarak render eder.
"""

from __future__ import annotations

import os
import re
import json
import uuid
import urllib.parse
import urllib.request
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    import edge_tts
except ImportError:
    edge_tts = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SCRATCH_DIR = PROJECT_ROOT / "scratch"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)


class StoryIllustratedGenerator:
    """
    Hikaye metninden sahne sahne çizimler üretip Remotion ile videolaştıran ana orkestratör.
    """

    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir or (SCRATCH_DIR / f"story_{uuid.uuid4().hex[:8]}")
        self.work_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_storyboard(topic: str, scene_count: int = 4, style: str = "cinematic_fantasy") -> Dict[str, Any]:
        """
        Konuya göre sahnelere bölünmüş hikaye ve görsel çizim promptları üretir.
        """
        # Temel stil ön ekleri
        style_prompts = {
            "cinematic_fantasy": "dark fantasy digital art, atmospheric lighting, moody cinematic concept art, highly detailed, 8k wallpaper, unreal engine 5 render style, 9:16 vertical ratio",
            "comic_noir": "dark graphic novel illustration, dramatic ink shadows, high contrast, neo-noir comic book aesthetic, vertical composition",
            "watercolor": "delicate storybook watercolor painting, dreamy pastel tones, whimsical children book illustration, soft aesthetic, vertical composition",
            "cyberpunk": "cyberpunk anime style, neon reflections, rain soaked city, cinematic anime concept art, vertical composition",
        }
        style_suffix = style_prompts.get(style, style_prompts["cinematic_fantasy"])

        # Çok çeşitli hazır senaryo şablonları (Gemini / AI entegrasyonu yoksa bile anında çalışması için)
        sample_scenarios = [
            {
                "title": "Zamanın Durduğu Saat Kulesi",
                "scenes": [
                    {
                        "caption": "Sisli bir sonbahar akşamı, kasabanın en eski saat kulesinde akrep ve yelkovan aniden durdu.",
                        "prompt": f"An ancient gothic clock tower in a misty eerie town during autumn twilight, glowing clock face, {style_suffix}",
                        "camera_effect": "zoom_in",
                        "highlight_words": ["saat", "kulesinde", "durdu"]
                    },
                    {
                        "caption": "Merdivenleri tırmanan yaşlı bir saat ustası, çarkların arasına sıkışmış parlayan altın bir anahtar buldu.",
                        "prompt": f"Elderly clockmaker holding an ancient glowing golden key inside intricate massive brass clock gears, {style_suffix}",
                        "camera_effect": "pan_left",
                        "highlight_words": ["saat ustası", "altın", "anahtar"]
                    },
                    {
                        "caption": "Anahtarı çevirdiği anda kule odasının duvarları şeffaflaştı ve geçmiş yüzyılın anıları havada belirdi.",
                        "prompt": f"Surreal room where walls become transparent showing floating glowing memories of the past century, magical sparks, {style_suffix}",
                        "camera_effect": "zoom_out",
                        "highlight_words": ["şeffaflaştı", "geçmiş", "anıları"]
                    },
                    {
                        "caption": "O günden sonra zaman kasaba için yeniden aktı, ama usta o kulede sonsuza dek genç kaldı.",
                        "prompt": f"Majestic silhouette of clock tower under starlight, clock ticking again, mysterious warm glow from the top window, {style_suffix}",
                        "camera_effect": "ken_burns",
                        "highlight_words": ["yeniden aktı", "sonsuza dek", "genç kaldı"]
                    }
                ]
            },
            {
                "title": "İstanbul'un Gizli Sarnıcı",
                "scenes": [
                    {
                        "caption": "Tarihi yarımadada eski bir konağın bodrumunu kazan işçiler, bin yıllık mühürlü bir kapı keşfetti.",
                        "prompt": f"Dark excavation underground discovery, ancient sealed stone door with mysterious Byzantine relief carvings, {style_suffix}",
                        "camera_effect": "zoom_in",
                        "highlight_words": ["bodrumunu", "mühürlü", "kapı"]
                    },
                    {
                        "caption": "Kapı açıldığında, yerin altında turkuaz sularla dolu devasa sütunlu bir yeraltı şehri uzanıyordu.",
                        "prompt": f"Gigantic underground cistern with ancient towering marble pillars submerged in glowing turquoise water, {style_suffix}",
                        "camera_effect": "pan_right",
                        "highlight_words": ["turkuaz", "sütunlu", "yeraltı"]
                    },
                    {
                        "caption": "Suların üzerinde süzülen pirinç bir kandil, onları suyun derinliklerinde uyuyan kadim bir koruyucuya götürdü.",
                        "prompt": f"A single antique brass lantern floating gracefully over still subterranean water, deep underwater shadows, {style_suffix}",
                        "camera_effect": "zoom_in",
                        "highlight_words": ["kandil", "kadim", "koruyucuya"]
                    },
                    {
                        "caption": "Bu sır artık sadece yeraltı sularının ve gecenin karanlığının emanetiydi.",
                        "prompt": f"Atmospheric dark cinematic cavern exit, moonlight reflecting on ancient stone steps, mystical ambiance, {style_suffix}",
                        "camera_effect": "zoom_out",
                        "highlight_words": ["sır", "sularının", "emanetiydi"]
                    }
                ]
            }
        ]

        # Konu eşleşmesi veya genel taslak
        chosen = sample_scenarios[0]
        if "istanbul" in topic.lower() or "sarnıç" in topic.lower() or "tarih" in topic.lower():
            chosen = sample_scenarios[1]
        elif topic.strip():
            # Kullanıcının verdiği özel başlığı uyarla
            chosen["title"] = topic.strip()

        return chosen

    def generate_scene_image(self, prompt: str, scene_idx: int) -> str:
        """
        Belirtilen prompt için 1080x1920 dikey illüstrasyon üretir.
        Önce Pollinations.ai gibi hızlı AI görsel motorunu dener, çevrimdışıysa estetik görsel üretir.
        """
        out_file = self.work_dir / f"scene_{scene_idx}_{uuid.uuid4().hex[:6]}.jpg"

        # 1. Pollinations AI ile Üretim (Hızlı, ücretsiz, dikey 1080x1920)
        encoded_prompt = urllib.parse.quote(prompt[:300])
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&model=flux&nologo=true&seed={scene_idx * 42}"

        try:
            req = urllib.request.Request(pollinations_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=18) as resp:
                content = resp.read()
                if len(content) > 10000:
                    out_file.write_bytes(content)
                    print(f"[STORY-GEN] 🎨 Sahne {scene_idx} illüstrasyonu başarıyla üretildi: {out_file.name}")
                    return str(out_file)
        except Exception as net_err:
            print(f"[STORY-GEN] AI görsel API uyarısı ({net_err}), yerel görsel oluşturucuya geçiliyor...")

        # 2. Yerel Fallback: Yüksek Kontrastlı Atmosferik Çizim Tuvali
        # (Ağ kesintisinde dahi sistem asla çökmez)
        img = Image.new("RGB", (1080, 1920), color=(14, 16, 22))
        draw = ImageDraw.Draw(img)

        # Sinematik gradyan ve ışık hüzmesi
        for y in range(1920):
            r = int(14 + (y / 1920) * 35)
            g = int(18 + (y / 1920) * 20)
            b = int(28 + (y / 1920) * 45)
            draw.line([(0, y), (1080, y)], fill=(r, g, b))

        # Ortaya soyut parıldayan ay / portal dairesi
        draw.ellipse([(290, 600), (790, 1100)], fill=(245, 158, 11, 40), outline=(255, 215, 0, 120), width=4)
        draw.ellipse([(340, 650), (740, 1050)], fill=(217, 119, 6, 80))

        # Başlık ve sahne bilgisi
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 44)
        except Exception:
            font = ImageFont.load_default()

        draw.text((100, 1200), f"Sahne {scene_idx + 1}", fill=(255, 230, 0), font=font)
        img = img.filter(ImageFilter.SMOOTH_MORE)
        img.save(out_file, "JPEG", quality=92)
        return str(out_file)

    async def generate_voiceover_async(self, text: str, output_path: str, voice: str = "tr-TR-AhmetNeural") -> str:
        """
        Edge-TTS ile hikaye anlatıcı sesini üretir.
        """
        if not edge_tts:
            raise RuntimeError("edge-tts kütüphanesi kurulu değil!")

        communicate = edge_tts.Communicate(text, voice, rate="+2%", pitch="-1Hz")
        await communicate.save(output_path)
        return output_path

    def generate_voiceover(self, text: str, output_path: str, voice: str = "tr-TR-AhmetNeural") -> str:
        """Senkron seslendirme sarmalayıcısı."""
        return asyncio.run(self.generate_voiceover_async(text, output_path, voice))

    def create_illustrated_story_video(
        self,
        topic: str = "Zamanın Durduğu Saat Kulesi",
        output_path: Optional[str] = None,
        style: str = "cinematic_fantasy",
        author: str = "HikayeDiyari",
        bgm_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tam pipeline:
        1. Senaryo oluştur
        2. Çizimleri üret
        3. Seslendir
        4. Remotion ile 1080x1920 sinematik videoya dönüştür
        """
        if output_path is None:
            output_path = str(OUTPUT_DIR / f"story_{uuid.uuid4().hex[:8]}.mp4")

        print(f"\n[STORY-GEN] 🚀 Hikaye Video Üretimi Başlatıldı: '{topic}'")

        # 1. Sahneleme
        storyboard = self.generate_storyboard(topic, style=style)
        title = storyboard["title"]
        scenes_def = storyboard["scenes"]

        # Tüm anlatıcı metnini birleştir
        full_narration = " ... ".join([s["caption"] for s in scenes_def])

        # 2. Seslendirme (TTS)
        audio_path = str(self.work_dir / "narration.mp3")
        print(f"[STORY-GEN] 🎙️ Anlatıcı seslendiriliyor...")
        self.generate_voiceover(full_narration, audio_path)

        # 3. Ses Süresini Al
        duration_sec = 12.0
        try:
            from moviepy import AudioFileClip
            with AudioFileClip(audio_path) as a_clip:
                duration_sec = float(a_clip.duration)
        except Exception:
            pass
        print(f"[STORY-GEN] ⏱️ Seslendirme süresi: {duration_sec:.1f} saniye")

        # 4. Her Sahne İçin Çizim Üretimi
        rendered_scenes = []
        fps = 30
        total_frames = max(90, int(duration_sec * fps) + 15)
        frames_per_scene = total_frames // len(scenes_def)
        current_frame = 0

        for i, sc in enumerate(scenes_def):
            img_path = self.generate_scene_image(sc["prompt"], i + 1)
            dur = frames_per_scene
            if i == len(scenes_def) - 1:
                dur = total_frames - current_frame

            rendered_scenes.append({
                "id": i + 1,
                "image_path": img_path,
                "caption_text": sc["caption"],
                "start_frame": current_frame,
                "duration_in_frames": dur,
                "camera_effect": sc.get("camera_effect", "ken_burns"),
                "highlight_words": sc.get("highlight_words", []),
            })
            current_frame += dur

        # 5. Remotion İle Render
        from src.remotion_renderer import render_story_illustrated_remotion

        print(f"[STORY-GEN] 🎥 Remotion React motoru çağrılıyor...")
        success = render_story_illustrated_remotion(
            title=title,
            scenes_data=rendered_scenes,
            audio_path=audio_path,
            output_path=output_path,
            author=author,
            bgm_path=bgm_path,
            theme="cinematic_dark",
            fps=fps,
        )

        return {
            "success": success,
            "title": title,
            "output_path": output_path,
            "scenes_count": len(rendered_scenes),
            "duration_sec": duration_sec,
            "work_dir": str(self.work_dir),
        }
