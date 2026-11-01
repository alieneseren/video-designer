"""
story_animation_engine.py
=========================
Kodla Sıfırdan Çizilen Sinematik Prosedürel Hikaye Animasyon Motoru.
Referans: Instagram Reel @meraklisinaa.tv ("AURORA - Son Işık", "Tüm görseller ve animasyonlar kodla, sıfırdan çizildi").

Özellikler:
1. 1080x1920 dikey 9:16 formatında, 30 FPS / 60 FPS sinematik uzay & hikaye tuvali.
2. Prosedürel derin uzay gradyanı, parıldayan dinamik yıldız tarlası (starfield) ve kozmik parçacıklar.
3. Kodla çizilen vektörel uzay gemisi (Aurora), güneş panelleri, parıldayan roket egzoz ateşi ve ışık hüzmeleri.
4. "A U R O R A" tarzı geniş harf aralıklı altın/beyaz sinematik başlık, bölüm etiketi ve kanca (hook) sorusu.
5. Hedef kanal diline (tr, en, de, es vb.) tam uyumlu Edge-TTS seslendirme.
6. Kelime/cümle zamanlamalı sinematik parlayan altyazılar.
7. Hikayeyi otomatik olarak 45-55 saniyelik "Part 1", "Part 2" shorts bölümlerine bölme.
8. Şeffaf abone ol/beğen CTA bindirmesi ile tam entegrasyon.
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    import edge_tts
    import asyncio
except ImportError:
    edge_tts = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "config" / "assets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class StoryAnimationEngine:
    def __init__(self, width: int = 1080, height: int = 1920, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self._init_fonts()

    def _init_fonts(self):
        """Sistemdeki mevcut estetik yazı tiplerini belirler."""
        candidates_title = [
            "/System/Library/Fonts/Supplemental/Didot.ttc",
            "/System/Library/Fonts/Supplemental/Baskerville.ttc",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ]
        candidates_sans = [
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

        self.font_title_path = None
        for p in candidates_title:
            if Path(p).exists():
                self.font_title_path = p
                break

        self.font_sans_path = None
        for p in candidates_sans:
            if Path(p).exists():
                self.font_sans_path = p
                break

    def get_font(self, size: int, is_serif: bool = False):
        p = self.font_title_path if is_serif else self.font_sans_path
        if p:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
        return ImageFont.load_default()

    async def generate_narration_async(self, text: str, output_path: str, lang: str = "tr") -> str:
        """Kanal diline göre uygun seslendiriciyi çalıştırır (Edge-TTS -> gTTS -> macOS say fallback)."""
        lang_code = (lang or "tr").lower()[:2]

        # 1. Aşama: Edge-TTS dene
        if edge_tts:
            voice_map = {
                "tr": "tr-TR-AhmetNeural",
                "en": "en-US-ChristopherNeural",
                "de": "de-DE-ConradNeural",
                "es": "es-ES-AlvaroNeural",
                "fr": "fr-FR-HenriNeural",
                "it": "it-IT-DiegoNeural",
                "pt": "pt-BR-AntonioNeural",
                "ar": "ar-SA-HamedNeural",
                "ru": "ru-RU-DmitryNeural",
            }
            voice = voice_map.get(lang_code, "en-US-ChristopherNeural")
            try:
                communicate = edge_tts.Communicate(text, voice, rate="+2%", pitch="-1Hz")
                await communicate.save(output_path)
                if Path(output_path).exists() and Path(output_path).stat().st_size > 500:
                    return output_path
            except Exception as edge_err:
                print(f"[STORY-ENGINE] ⚠️ Edge-TTS uyarısı ({edge_err}), gTTS alternatifine geçiliyor...")

        # 2. Aşama: gTTS (Google Translate TTS) Fallback
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang=lang_code)
            tts.save(output_path)
            if Path(output_path).exists() and Path(output_path).stat().st_size > 500:
                print(f"[STORY-ENGINE] ✓ gTTS ile seslendirme başarıyla tamamlandı.")
                return output_path
        except Exception as gtts_err:
            print(f"[STORY-ENGINE] ⚠️ gTTS uyarısı ({gtts_err}), yerel sisteme geçiliyor...")

        # 3. Aşama: macOS 'say' veya FFmpeg ses sentezi
        try:
            aiff_temp = f"{output_path}.aiff"
            subprocess.run(["say", text, "-o", aiff_temp], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["ffmpeg", "-y", "-i", aiff_temp, output_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if Path(aiff_temp).exists():
                Path(aiff_temp).unlink()
            if Path(output_path).exists():
                print(f"[STORY-ENGINE] ✓ macOS yerel seslendirici ile ses üretildi.")
                return output_path
        except Exception:
            pass

        # 4. Aşama: Tam acil durum (sessiz audio)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "10", "-q:a", "9", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path

    def generate_narration(self, text: str, output_path: str, lang: str = "tr") -> str:
        return asyncio.run(self.generate_narration_async(text, output_path, lang))

    def get_audio_duration(self, audio_path: str) -> float:
        """ffprobe ile ses dosyasının tam süresini ölçer."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            return 30.0

    def draw_procedural_background(self, frame_idx: int, stars: List[Dict[str, Any]]) -> np.ndarray:
        """
        Derin uzay indigo-siyah gradyanı ve yanıp sönen yıldız tarlası (starfield).
        """
        w, h = self.width, self.height
        # 1. Sinematik dikey gradyan
        # Üst: Çok koyu lacivert/siyah (#030712), Alt: Hafif mor/lacivert ışıma (#0a1128)
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Hızlı gradyan matrisi
        y_ratios = np.linspace(0, 1, h)[:, None]
        canvas[:, :, 0] = np.clip(16 + y_ratios * 24, 0, 255).astype(np.uint8)  # B
        canvas[:, :, 1] = np.clip(7 + y_ratios * 12, 0, 255).astype(np.uint8)   # G
        canvas[:, :, 2] = np.clip(4 + y_ratios * 8, 0, 255).astype(np.uint8)    # R

        # 2. Yıldızları çiz (yanıp sönme + ufak dikey kayma efekti)
        for s in stars:
            sx = int(s["x"])
            # Hafif yukarı yavaş süzülme
            sy = int((s["y"] - frame_idx * s["speed"]) % h)
            phase = (frame_idx * 0.08 + s["phase"]) % (2 * math.pi)
            brightness = 0.5 + 0.5 * math.sin(phase)
            star_val = int(s["base_val"] * (0.4 + 0.6 * brightness))
            r = s["radius"]

            if r <= 1:
                cv2.circle(canvas, (sx, sy), 1, (star_val, star_val, star_val), -1)
            else:
                # Parlayan yıldız halkası
                glow_val = int(star_val * 0.4)
                cv2.circle(canvas, (sx, sy), r + 1, (glow_val, glow_val, glow_val), -1)
                cv2.circle(canvas, (sx, sy), r, (star_val, star_val, star_val), -1)

        return canvas

    def detect_visual_theme(self, series_title: str = "", genre: str = "", prompt: str = "") -> str:
        """
        Hikayenin türüne, konusuna ve sahne yönergesine göre en uygun
        prosedürel vektörel çizim temasını otomatik belirler.
        """
        combined = f"{series_title} {genre} {prompt}".lower()

        # 1. Uzay / Bilimkurgu / Roket
        if any(k in combined for k in ["uzay", "space", "gemisi", "astronot", "galaksi", "roket", "starship", "nebula", "sektör", "aurora", "beacon"]):
            if any(k in combined for k in ["gezegen", "planet", "yörünge", "halka"]):
                return "celestial_planet"
            return "spaceship"

        # 2. Masal / Peri Masalı / Çocuk / Orman / Fener / Gece / Köy
        if any(k in combined for k in ["masal", "fairy", "peri", "fable", "orman", "fener", "lantern", "gece", "köy", "çocuk", "uyku", "ateş", "kandil"]):
            return "lantern"

        # 3. Kule / Saat / Şato / Gotik / Dedektiflik / Tarih / Efsane
        if any(k in combined for k in ["kule", "saat", "clock", "tower", "şato", "kale", "gothic", "castle", "tarih", "antika", "vampir", "sarnıç"]):
            return "gothic_spire"

        # 4. Büyü / Portal / Kadim Sır / Tapınak / Geçit
        if any(k in combined for k in ["portal", "büyü", "magic", "vortex", "kadim", "tapınak", "geçit", "boyut", "sır", "kapı"]):
            return "mystic_portal"

        # Varsayılan tür haritası
        genre_map = {
            "sci_fi_mystery": "spaceship",
            "dark_mystery": "gothic_spire",
            "ancient_myth": "mystic_portal",
            "fantasy_fable": "lantern",
            "psychological": "gothic_spire",
        }
        return genre_map.get(genre, "lantern")

    def draw_ancient_lantern(self, canvas: np.ndarray, frame_idx: int, center_x: int, center_y: int):
        """Masallar, efsaneler ve fantastik hikayeler için sallanan kadim fener ve parlayan ateşböcekleri."""
        sway = math.sin(frame_idx * 0.05) * 8
        lx = int(center_x + sway)
        ly = center_y + int(math.cos(frame_idx * 0.03) * 4)

        # 1. Askı zinciri
        cv2.line(canvas, (center_x, 0), (lx, ly - 80), (120, 100, 70), 2)

        # 2. Fener üst kubbesi
        cv2.ellipse(canvas, (lx, ly - 80), (45, 18), 0, 180, 360, (140, 115, 80), -1)

        # 3. Sıcak alev ışıması (Radial glow)
        flicker = 1.0 + 0.08 * math.sin(frame_idx * 0.2)
        for r_glow in range(120, 10, -12):
            alpha = int(45 * (1.0 - r_glow / 120.0) * flicker)
            cv2.circle(canvas, (lx, ly - 20), int(r_glow * flicker), (15, int(120 * alpha / 45), int(240 * alpha / 45)), -1)

        # 4. Fener camı ve kafesi
        pts = np.array([[lx - 40, ly - 80], [lx + 40, ly - 80], [lx + 30, ly + 40], [lx - 30, ly + 40]], np.int32)
        cv2.fillPoly(canvas, [pts], (20, 28, 40))

        # 5. İç alev çekirdeği
        cv2.ellipse(canvas, (lx, ly - 20), (10, 22), 0, 0, 360, (200, 240, 255), -1)
        cv2.ellipse(canvas, (lx, ly - 20), (6, 14), 0, 0, 360, (255, 255, 255), -1)

        # Pirinç parmaklıklar
        cv2.line(canvas, (lx - 40, ly - 80), (lx - 30, ly + 40), (180, 150, 90), 2)
        cv2.line(canvas, (lx + 40, ly - 80), (lx + 30, ly + 40), (180, 150, 90), 2)
        cv2.line(canvas, (lx, ly - 80), (lx, ly + 40), (180, 150, 90), 2)
        cv2.rectangle(canvas, (lx - 34, ly + 40), (lx + 34, ly + 55), (140, 115, 80), -1)

        # 6. Uçuşan sihirli ateşböcekleri / kıvılcımlar
        for i in range(14):
            fx = int(center_x + math.sin(frame_idx * 0.04 + i) * 160 + math.cos(i * 1.5) * 40)
            fy = int(center_y - 20 + math.cos(frame_idx * 0.03 + i * 2) * 120)
            fr = 2 if i % 3 == 0 else 1
            cv2.circle(canvas, (fx, fy), fr + 2, (10, 80, 160), -1)
            cv2.circle(canvas, (fx, fy), fr, (100, 230, 255), -1)

    def draw_gothic_spire_moon(self, canvas: np.ndarray, frame_idx: int, center_x: int, center_y: int):
        """Karanlık sırlar, saat kulesi, gotik efsaneler için dev ay ve kule silueti."""
        # 1. Dev parlak ay
        moon_x = center_x
        moon_y = center_y - 60
        moon_r = 140
        # Ay ışıması
        for mr in range(moon_r + 50, moon_r, -10):
            cv2.circle(canvas, (moon_x, moon_y), mr, (20, 25, 40), -1)
        # Ay gövdesi
        cv2.circle(canvas, (moon_x, moon_y), moon_r, (230, 235, 245), -1)
        # Krater detayları
        cv2.circle(canvas, (moon_x - 45, moon_y - 30), 22, (205, 210, 225), -1)
        cv2.circle(canvas, (moon_x + 35, moon_y + 40), 28, (210, 215, 228), -1)

        # 2. Gotik kule silueti (ön planda siyah/koyu antrasit)
        tower_top_y = moon_y - 120
        spire_pts = np.array([
            [center_x, tower_top_y],
            [center_x - 35, tower_top_y + 110],
            [center_x + 35, tower_top_y + 110],
        ], np.int32)
        cv2.fillPoly(canvas, [spire_pts], (12, 14, 20))

        # Kule gövdesi
        cv2.rectangle(canvas, (center_x - 45, tower_top_y + 110), (center_x + 45, tower_top_y + 360), (12, 14, 20), -1)

        # Kule saat dairesi (parlayan sarı/amber)
        clock_y = tower_top_y + 160
        cv2.circle(canvas, (center_x, clock_y), 24, (30, 180, 240), -1)
        cv2.circle(canvas, (center_x, clock_y), 24, (180, 220, 255), 2)
        # Akrep ve yelkovan
        cv2.line(canvas, (center_x, clock_y), (center_x + 10, clock_y - 8), (15, 20, 30), 2)
        cv2.line(canvas, (center_x, clock_y), (center_x - 4, clock_y + 12), (15, 20, 30), 2)

        # Kemerli pencereler
        cv2.rectangle(canvas, (center_x - 22, clock_y + 45), (center_x - 8, clock_y + 90), (30, 160, 220), -1)
        cv2.rectangle(canvas, (center_x + 8, clock_y + 45), (center_x + 22, clock_y + 90), (30, 160, 220), -1)

    def draw_mystic_portal(self, canvas: np.ndarray, frame_idx: int, center_x: int, center_y: int):
        """Kadim mitoloji, büyülü geçitler ve sırlar için dönen sihirli portal."""
        hover_y = center_y + int(math.sin(frame_idx * 0.06) * 6)

        # 1. Dış enerji dalgaları
        for ring_idx in range(4):
            r = 90 + ring_idx * 28 + int(math.sin(frame_idx * 0.1 + ring_idx) * 6)
            rot_angle = frame_idx * (2.5 if ring_idx % 2 == 0 else -2.5)
            cv2.ellipse(canvas, (center_x, hover_y), (r, int(r * 0.55)), rot_angle, 0, 360, (220, 140, 40), 2)

        # 2. Portal çekirdek ışıması
        for r_core in range(80, 10, -10):
            alpha = int(40 * (1.0 - r_core / 80.0))
            cv2.circle(canvas, (center_x, hover_y), r_core, (int(250 * alpha / 40), int(180 * alpha / 40), 60), -1)

        cv2.circle(canvas, (center_x, hover_y), 24, (255, 250, 220), -1)

        # 3. Dışa saçılan enerji kıvılcımları
        for k in range(12):
            ang = (frame_idx * 0.08 + k * (math.pi / 6))
            dist = 90 + (k * 13 + frame_idx * 3) % 110
            sp_x = int(center_x + math.cos(ang) * dist)
            sp_y = int(hover_y + math.sin(ang) * dist * 0.6)
            cv2.circle(canvas, (sp_x, sp_y), 2, (255, 200, 120), -1)

    def draw_celestial_planet(self, canvas: np.ndarray, frame_idx: int, center_x: int, center_y: int):
        """Gezegenler, kozmos ve derin uzay hikayeleri için halkalı gezegen motifi."""
        px = center_x
        py = center_y + int(math.sin(frame_idx * 0.05) * 7)

        # Gezegen atmosfer halesi
        for r_halo in range(130, 80, -8):
            cv2.circle(canvas, (px, py), r_halo, (70, 45, 18), -1)

        # Gezegen gövdesi
        cv2.circle(canvas, (px, py), 80, (200, 140, 60), -1)
        # Gölgeli kısım (3D küre etkisi)
        cv2.circle(canvas, (px - 22, py - 18), 70, (240, 180, 90), -1)

        # Gezegen halkası (arkası kesik elips)
        ring_tilt = 25
        cv2.ellipse(canvas, (px, py), (180, 34), ring_tilt, 190, 350, (180, 150, 110), 3)
        cv2.ellipse(canvas, (px, py), (180, 34), ring_tilt, 10, 170, (240, 210, 160), 4)

    def draw_spaceship_aurora(self, canvas: np.ndarray, frame_idx: int, center_x: int, center_y: int):
        """Bilimkurgu hikayeleri için kodla çizilen minimalist uzay aracı ve roket alevi."""
        # Hafif sinüs dalgası ile süzülme (levitation)
        hover_y = center_y + int(math.sin(frame_idx * 0.08) * 8)
        hover_x = center_x + int(math.cos(frame_idx * 0.04) * 3)

        # 1. Roket İtki Alevi ve Işıma (Glow)
        flame_len = 50 + int(random.uniform(0, 16)) + int(math.sin(frame_idx * 0.25) * 8)
        flame_w = 16

        # Çok katmanlı alev ışıması
        # Dış sıcak sarı/turuncu parlama
        flame_pt1 = (hover_x - flame_w, hover_y + 35)
        flame_pt2 = (hover_x + flame_w, hover_y + 35)
        flame_pt3 = (hover_x, hover_y + 35 + flame_len)
        cv2.fillPoly(canvas, [np.array([flame_pt1, flame_pt2, flame_pt3], np.int32)], (30, 160, 255))  # Turuncu/Sarı (BGR)

        # İç beyaz/mavi çekirdek alev
        core_pt1 = (hover_x - 7, hover_y + 35)
        core_pt2 = (hover_x + 7, hover_y + 35)
        core_pt3 = (hover_x, hover_y + 35 + int(flame_len * 0.65))
        cv2.fillPoly(canvas, [np.array([core_pt1, core_pt2, core_pt3], np.int32)], (255, 240, 200))

        # Egzozdan çıkan kıvılcım parçacıkları
        for _ in range(4):
            spark_x = hover_x + random.randint(-10, 10)
            spark_y = hover_y + 35 + flame_len + random.randint(5, 45)
            spark_r = random.randint(1, 2)
            cv2.circle(canvas, (spark_x, spark_y), spark_r, (180, 220, 255), -1)

        # 2. Güneş Paneli Kanatları (Cyan/Mavi ızgaralı)
        panel_w = 110
        panel_h = 24
        panel_y = hover_y - 2

        # Sol Panel
        left_panel_x = hover_x - 22 - panel_w
        cv2.rectangle(canvas, (left_panel_x, panel_y), (hover_x - 22, panel_y + panel_h), (90, 75, 40), -1)
        cv2.rectangle(canvas, (left_panel_x, panel_y), (hover_x - 22, panel_y + panel_h), (180, 150, 90), 1)
        # Izgara çizgileri
        for gx in range(left_panel_x + 22, hover_x - 22, 22):
            cv2.line(canvas, (gx, panel_y), (gx, panel_y + panel_h), (140, 110, 60), 1)

        # Sağ Panel
        right_panel_x = hover_x + 22
        cv2.rectangle(canvas, (right_panel_x, panel_y), (right_panel_x + panel_w, panel_y + panel_h), (90, 75, 40), -1)
        cv2.rectangle(canvas, (right_panel_x, panel_y), (right_panel_x + panel_w, panel_y + panel_h), (180, 150, 90), 1)
        for gx in range(right_panel_x + 22, right_panel_x + panel_w, 22):
            cv2.line(canvas, (gx, panel_y), (gx, panel_y + panel_h), (140, 110, 60), 1)

        # 3. Ana Gövde (Beyaz/Gümüş kapsül)
        hull_w = 34
        hull_h = 75
        hull_top = hover_y - 45
        hull_bottom = hover_y + 35

        # Silindirik gövde
        cv2.rectangle(canvas, (hover_x - hull_w // 2, hull_top + 15), (hover_x + hull_w // 2, hull_bottom), (240, 240, 245), -1)
        # Burun konisi (kubbe)
        cv2.ellipse(canvas, (hover_x, hull_top + 15), (hull_w // 2, 18), 0, 180, 360, (245, 245, 250), -1)
        # Gövde konturu
        cv2.rectangle(canvas, (hover_x - hull_w // 2, hull_top + 15), (hover_x + hull_w // 2, hull_bottom), (180, 180, 190), 1)
        cv2.ellipse(canvas, (hover_x, hull_top + 15), (hull_w // 2, 18), 0, 180, 360, (180, 180, 190), 1)

        # Kokpit / gözlem penceresi
        cv2.circle(canvas, (hover_x, hull_top + 28), 5, (80, 60, 40), -1)
        cv2.circle(canvas, (hover_x, hull_top + 28), 5, (220, 200, 160), 1)

    def draw_cinematic_overlay(
        self,
        pil_img: Image.Image,
        series_title: str,
        part_num: int,
        hook_text: str,
        current_caption: str,
        frame_idx: int,
        total_frames: int,
        total_parts: int = 1,
        target_lang: str = "tr",
    ) -> Image.Image:
        """
        Ekranın üst, orta ve altındaki şık sinematik tipografiyi çizer.
        """
        draw = ImageDraw.Draw(pil_img)
        w, h = self.width, self.height

        # 1. ÜST SERİ BAŞLIĞI: Herhangi bir hikaye başlığı (Akıllı Harf Aralığı & Otomatik Sığdırma)
        title_clean = series_title.upper().strip()
        max_title_w = w - 160  # 920px

        # Kısa başlıklarda geniş harf aralığı, uzun başlıklarda zarif kompakt tipografi
        if len(title_clean) <= 12:
            spaced_title = "  ".join(list(title_clean))
        elif len(title_clean) <= 20:
            spaced_title = " ".join(list(title_clean))
        else:
            spaced_title = title_clean

        font_size = 40
        font_title = self.get_font(font_size, is_serif=True)
        bbox = draw.textbbox((0, 0), spaced_title, font=font_title)
        tw = bbox[2] - bbox[0]

        # Başlık genişliği sınıra sığana kadar font puntosunu otomatik ölçekle
        while tw > max_title_w and font_size > 20:
            font_size -= 2
            font_title = self.get_font(font_size, is_serif=True)
            bbox = draw.textbbox((0, 0), spaced_title, font=font_title)
            tw = bbox[2] - bbox[0]

        tx = (w - tw) // 2
        ty = int(h * 0.42)

        # Başlık gölgesi ve metni
        draw.text((tx + 2, ty + 2), spaced_title, font=font_title, fill=(0, 0, 0, 220))
        draw.text((tx, ty), spaced_title, font=font_title, fill=(255, 255, 255, 245))

        # Altın/Bronz İnce Çizgi
        line_y = ty + font_size + 16
        line_w = min(tw + 40, 380)
        lx1 = (w - line_w) // 2
        lx2 = lx1 + line_w
        draw.line([(lx1, line_y), (lx2, line_y)], fill=(212, 175, 55, 220), width=2)

        # Bölüm Etiketi: "B Ö L Ü M   1 / 3" veya son bölüm için "F İ N A L"
        if total_parts > 1:
            if part_num >= total_parts:
                part_tag = f"B Ö L Ü M   {part_num}   //   F İ N A L" if target_lang == "tr" else f"P A R T   {part_num}   //   F I N A L"
            else:
                part_tag = f"B Ö L Ü M   {part_num}  /  {total_parts}" if target_lang == "tr" else f"P A R T   {part_num}  /  {total_parts}"
        else:
            part_tag = "H İ K A Y E" if target_lang == "tr" else "S T O R Y"

        font_part = self.get_font(19, is_serif=False)
        p_bbox = draw.textbbox((0, 0), part_tag, font=font_part)
        pw = p_bbox[2] - p_bbox[0]
        px = (w - pw) // 2
        py = line_y + 12
        draw.text((px, py), part_tag, font=font_part, fill=(200, 190, 160, 210))

        # 2. ORTA KANCA (HOOK) SORUSU (Otomatik Ölçekleme)
        if hook_text:
            font_size_hook = 32
            font_hook = self.get_font(font_size_hook, is_serif=True)
            h_bbox = draw.textbbox((0, 0), hook_text, font=font_hook)
            hw = h_bbox[2] - h_bbox[0]

            while hw > max_title_w and font_size_hook > 18:
                font_size_hook -= 2
                font_hook = self.get_font(font_size_hook, is_serif=True)
                h_bbox = draw.textbbox((0, 0), hook_text, font=font_hook)
                hw = h_bbox[2] - h_bbox[0]

            hx = (w - hw) // 2
            hy = py + 44
            draw.text((hx + 1, hy + 2), hook_text, font=font_hook, fill=(0, 0, 0, 220))
            draw.text((hx, hy), hook_text, font=font_hook, fill=(245, 245, 250, 240))

        # 3. ALT DİNAMİK ALTYAZI (Subtitle Pill)
        if current_caption:
            font_sub = self.get_font(32, is_serif=False)
            # Metni satırlara böl (max 38 karakter)
            words = current_caption.split()
            lines = []
            curr_line = []
            curr_len = 0
            for word in words:
                if curr_len + len(word) + 1 > 36:
                    lines.append(" ".join(curr_line))
                    curr_line = [word]
                    curr_len = len(word)
                else:
                    curr_line.append(word)
                    curr_len += len(word) + 1
            if curr_line:
                lines.append(" ".join(curr_line))

            sub_y = int(h * 0.76)
            line_height = 44
            for i, line_str in enumerate(lines):
                s_bbox = draw.textbbox((0, 0), line_str, font=font_sub)
                sw = s_bbox[2] - s_bbox[0]
                sx = (w - sw) // 2
                sy = sub_y + (i * line_height)

                # Yarı saydam siyah hap (pill) arka plan
                pad_x = 18
                pad_y = 6
                pill_rect = [sx - pad_x, sy - pad_y, sx + sw + pad_x, sy + line_height - pad_y]
                draw.rectangle(pill_rect, fill=(10, 15, 25, 175), outline=(212, 175, 55, 60), width=1)

                # Metin
                draw.text((sx + 1, sy + 1), line_str, font=font_sub, fill=(0, 0, 0, 240))
                draw.text((sx, sy), line_str, font=font_sub, fill=(255, 255, 255, 255))

        # 4. Kapanışta Cliffhanger veya Final CTA Bildirimi (Son 4 saniye)
        remaining_sec = (total_frames - frame_idx) / self.fps
        if remaining_sec <= 4.0:
            if part_num < total_parts:
                cta_text = f"BÖLÜM {part_num + 1} İÇİN TAKİPTE KALIN" if target_lang == "tr" else f"FOLLOW FOR PART {part_num + 1}"
            else:
                cta_text = "FİNAL // İZLEDİĞİNİZ İÇİN TEŞEKKÜRLER" if target_lang == "tr" else "THE END // THANKS FOR WATCHING"
            font_cta = self.get_font(24, is_serif=False)
            c_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
            cw = c_bbox[2] - c_bbox[0]
            cx = (w - cw) // 2
            cy = int(h * 0.88)

            alpha = int(min(1.0, (4.0 - remaining_sec) * 1.5) * 255)
            draw.rectangle([cx - 24, cy - 8, cx + cw + 24, cy + 38], fill=(220, 38, 38, alpha))
            draw.text((cx, cy), cta_text, font=font_cta, fill=(255, 255, 255, alpha))

        return pil_img

    def render_episode(
        self,
        series_title: str,
        part_num: int,
        total_parts: int,
        hook: str,
        scenes: List[Dict[str, Any]],
        output_mp4: str,
        target_lang: str = "tr",
        bgm_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tek bir Shorts bölümünü sıfırdan kodla çizer ve MP4 olarak kaydeder.
        """
        work_dir = Path(tempfile.mkdtemp(prefix="story_ep_"))
        print(f"\n[STORY-ENGINE] 🎬 Bölüm Render Başlatıldı: {series_title} // Part {part_num}")

        # 1. Seslendirme Metnini Derle
        full_narration = " ".join([sc.get("narration", "") for sc in scenes]).strip()
        if not full_narration:
            full_narration = hook or series_title

        # Kapanışa cliffhanger fısıltısı ekle (yalnızca final öncesi bölümler için)
        if part_num < total_parts:
            cliffhanger_tail = f" Bölüm {part_num + 1} için takipte kalın..." if target_lang == "tr" else f" Follow for Part {part_num + 1}..."
            full_narration += cliffhanger_tail

        # 2. TTS Seslendirme
        voice_mp3 = str(work_dir / "voice.mp3")
        print(f"[STORY-ENGINE] 🎙️ Seslendiriliyor ({target_lang})...")
        self.generate_narration(full_narration, voice_mp3, lang=target_lang)
        audio_dur = self.get_audio_duration(voice_mp3)
        print(f"[STORY-ENGINE] ⏱️ Ses süresi: {audio_dur:.1f} saniye")

        # Toplam kare sayısı
        total_frames = max(90, int((audio_dur + 0.8) * self.fps))
        frames_per_scene = total_frames // max(1, len(scenes))

        # 3. Yıldız Tarlası Oluştur (280 adet parlayan yıldız)
        random.seed(42 + part_num)
        stars = []
        for _ in range(280):
            stars.append({
                "x": random.randint(0, self.width),
                "y": random.randint(0, self.height),
                "radius": 1 if random.random() > 0.12 else 2,
                "base_val": random.randint(140, 255),
                "speed": random.uniform(0.15, 0.6),
                "phase": random.uniform(0, 2 * math.pi),
            })

        # Hikaye konusuna ve sahnelerine göre görsel temayı otomatik tespit et (fener, kule, portal, gezegen veya uzay)
        all_scene_prompts = " ".join([sc.get("image_prompt", "") + " " + sc.get("caption", "") + " " + sc.get("narration", "") for sc in scenes])
        theme = self.detect_visual_theme(series_title=series_title, prompt=all_scene_prompts)
        print(f"[STORY-ENGINE] 🎨 Prosedürel Görsel Tema: '{theme}' (Hikaye: '{series_title}')")

        # 4. Kare Kare Video Yazıcı
        raw_video_path = str(work_dir / "raw_video.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(raw_video_path, fourcc, self.fps, (self.width, self.height))

        subject_center_x = self.width // 2
        subject_center_y = int(self.height * 0.65)

        for f_idx in range(total_frames):
            # A. Arka plan atmosfer gradyanı ve parıldayan yıldızlar/parçacıklar
            canvas = self.draw_procedural_background(f_idx, stars)

            # B. Kodla çizilen prosedürel görsel motif (fener, kule, portal, gezegen veya uzay gemisi)
            if theme == "lantern":
                self.draw_ancient_lantern(canvas, f_idx, subject_center_x, subject_center_y)
            elif theme == "gothic_spire":
                self.draw_gothic_spire_moon(canvas, f_idx, subject_center_x, subject_center_y)
            elif theme == "mystic_portal":
                self.draw_mystic_portal(canvas, f_idx, subject_center_x, subject_center_y)
            elif theme == "celestial_planet":
                self.draw_celestial_planet(canvas, f_idx, subject_center_x, subject_center_y)
            else:
                self.draw_spaceship_aurora(canvas, f_idx, subject_center_x, subject_center_y)

            # C. PIL Katmanına Çevirip Tipografiyi Ekle
            # Hangi sahnedeyiz?
            sc_idx = min(len(scenes) - 1, f_idx // frames_per_scene)
            curr_caption = scenes[sc_idx].get("caption") or scenes[sc_idx].get("narration") or ""

            pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
            pil_img = self.draw_cinematic_overlay(
                pil_img=pil_img,
                series_title=series_title,
                part_num=part_num,
                hook_text=hook,
                current_caption=curr_caption,
                frame_idx=f_idx,
                total_frames=total_frames,
                total_parts=total_parts,
                target_lang=target_lang,
            )

            # D. Geri OpenCV formatına çevir ve kareyi yaz
            frame_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)

        writer.release()
        print(f"[STORY-ENGINE] 🎥 Video kareleri render edildi ({total_frames} kare)")

        # 5. FFmpeg ile Ses ve Fon Müziğini Birleştir
        final_mp4 = Path(output_mp4)
        final_mp4.parent.mkdir(parents=True, exist_ok=True)

        # Varsayılan BGM seçimi
        chosen_bgm = bgm_path
        if not chosen_bgm:
            bgm_candidates = list((PROJECT_ROOT / "config" / "bgm").glob("*.mp3")) + list(
                (PROJECT_ROOT / "config" / "assets").glob("*.mp3")
            )
            if bgm_candidates:
                chosen_bgm = str(bgm_candidates[0])

        if chosen_bgm and Path(chosen_bgm).exists():
            # Voice + BGM miksajı
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", raw_video_path,
                "-i", voice_mp3,
                "-stream_loop", "-1", "-i", chosen_bgm,
                "-filter_complex",
                "[1:a]volume=1.0[v_aud];[2:a]volume=0.15[bgm];[v_aud][bgm]amix=inputs=2:duration=first[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest",
                str(final_mp4),
            ]
        else:
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", raw_video_path,
                "-i", voice_mp3,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                str(final_mp4),
            ]

        subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        # 6. Universal Sosyal CTA Bindirmesi Uygula
        try:
            from social_cta_overlay import apply_social_cta_overlay
            cta_out = str(work_dir / "cta_final.mp4")
            ok = apply_social_cta_overlay(
                input_video=str(final_mp4),
                output_video=cta_out,
                language=target_lang,
                show_at_start=True,
                show_at_end=True
            )
            if ok and Path(cta_out).exists():
                import shutil
                shutil.move(cta_out, str(final_mp4))
                print(f"[STORY-ENGINE] ✓ Şeffaf Abone Ol / Beğen CTA animasyonu uygulandı.")
        except Exception as cta_err:
            print(f"[STORY-ENGINE] ⚠️ CTA bindirmesi atlandı: {cta_err}")

        # Temizlik
        try:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass

        print(f"[STORY-ENGINE] 🚀 Bölüm tamamlandı: {final_mp4.name}")
        return {
            "success": True,
            "output_path": str(final_mp4),
            "part_num": part_num,
            "duration_sec": audio_dur,
        }

    def render_all_parts_for_story(
        self,
        story_id: str,
        channel_id: str,
        bgm_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Bir hikaye taslağındaki tüm Part'ları sırayla render eder.
        """
        from story_manager import StoryManager
        sm = StoryManager()
        story = sm.get_story(story_id)
        if not story:
            raise ValueError(f"Hikaye bulunamadı: {story_id}")

        developed = story.get("developed_story") or {}
        parts = developed.get("parts") or [
            {
                "part_number": 1,
                "part_title": story.get("title"),
                "scenes": developed.get("scenes") or [
                    {"scene_num": 1, "narration": story.get("raw_text", ""), "caption": story.get("title", "")}
                ],
                "hook": developed.get("hook", story.get("title")),
            }
        ]

        total_parts = len(parts)
        results = []
        target_lang = story.get("target_language", "tr")
        series_title = story.get("title") or "Hikaye"

        ch_out_dir = OUTPUT_DIR / channel_id
        ch_out_dir.mkdir(parents=True, exist_ok=True)

        for p in parts:
            p_num = p.get("part_number", 1)
            hook = p.get("hook") or story.get("title")
            scenes = p.get("scenes", [])
            ep_filename = f"{channel_id}_{story_id}_part{p_num}.mp4"
            out_file = str(ch_out_dir / ep_filename)

            res = self.render_episode(
                series_title=series_title,
                part_num=p_num,
                total_parts=total_parts,
                hook=hook,
                scenes=scenes,
                output_mp4=out_file,
                target_lang=target_lang,
                bgm_path=bgm_path,
            )
            results.append(res)

        return results
