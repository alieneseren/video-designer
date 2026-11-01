"""
video_generator.py
==================
Senaryo → Ses → Görsel → Video pipeline.

v3 Yenilikler — kritik düzeltme + gelişmiş video edit sistemi:
  - Subtitle artık frame'e bake EDİLMİYOR; ASS altyazı katmanı olarak
    base video üzerine ffmpeg ile bindiriliyor (iki aşamalı pipeline).
  - Aynı görseli paylaşan ardışık caption'lar tek "görsel sahnesi" olarak
    gruplanıyor → caption değişimleri için SAHTE GEÇİŞ efekti üretilmiyor.
  - Yeni src.video_editor modülü: BaseVideoBuilder + SubtitleBurner +
    ASSWriter + EditConfig.
  - Subtitle presets: minimal / bold / tiktok / youtube-classic / news.
  - Animasyonlar: none / fade / pop / typewriter / word-highlight.
  - Opsiyonel: BGM, watermark, intro/outro.

Bu refactor geriye dönük uyumlu: eski VideoComposer.compose() hala çağrılabilir
ancak önerilen yol VideoGenerator.run() içinden yeni pipeline'a geçmektir.
"""

from __future__ import annotations
import os
import re
import json
import asyncio
import requests
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
import subprocess

import edge_tts
import numpy as np
from moviepy import (
    VideoClip, ImageClip, AudioFileClip, concatenate_videoclips,
)

from PIL import Image, ImageDraw, ImageFont


def remove_gemini_watermark(image_path: str):
    """
    Gemini'ın ürettiği görsellerdeki 'Imagined with Gemini' filigranını temizler.
    Sağ alt köşede yer alan filigran bölgesi komşu piksellerle doldurulur.
    Önce cv2 inpainting, hata durumunda PIL patch kopyalama kullanır.
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"cv2.imread başarısız: {image_path}")

        h, w = img.shape[:2]

        # Gemini filigranı sağ alt köşede — bölgeyi biraz geniş tut
        # Y: son %18, X: son %45 → "Imagined with Gemini" yazısını tamamen kapsar
        mask = np.zeros((h, w), dtype=np.uint8)
        y1 = int(h * 0.82)
        x1 = int(w * 0.55)
        mask[y1:h, x1:w] = 255

        # Telea inpainting: filigranı çevre piksellere göre doldurur
        dst = cv2.inpaint(img, mask, inpaintRadius=9, flags=cv2.INPAINT_TELEA)
        cv2.imwrite(image_path, dst, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[WATERMARK] Gemini filigranı temizlendi (cv2): {image_path}")
        return True

    except Exception as e:
        print(f"[WATERMARK] cv2 hatası, PIL fallback deneniyor: {e}")
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(image_path).convert("RGB")
            arr = np.array(img)
            h, w = arr.shape[:2]

            y1 = int(h * 0.82)
            x1 = int(w * 0.55)

            # Filigran bölgesini üstündeki piksellerin kopyasıyla doldur
            # Yükseklik kadar üst satırı al (kopyalanacak referans bölge)
            region_h = h - y1
            src_y1 = max(0, y1 - region_h)
            src_region = arr[src_y1:y1, x1:w].copy()

            # Kaynak bölge yeterince yüksek değilse tekrarla
            if src_region.shape[0] < region_h:
                repeat_times = (region_h // max(src_region.shape[0], 1)) + 1
                src_region = np.tile(src_region, (repeat_times, 1, 1))

            arr[y1:h, x1:w] = src_region[:region_h, :w - x1, :]

            Image.fromarray(arr).save(image_path, "JPEG", quality=95)
            print(f"[WATERMARK] Gemini filigranı temizlendi (PIL patch): {image_path}")
            return True
        except Exception as e2:
            print(f"[WATERMARK] PIL fallback hatası: {e2}")
            return False


# ──────────────────────────────────────────
# EDGE TTS — Dil → Ses eşlemesi
# ──────────────────────────────────────────

VOICE_MAP = {
    "tr": "tr-TR-AhmetNeural",
    "en": "en-US-GuyNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "es": "es-ES-AlvaroNeural",
    "it": "it-IT-ElsaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ar": "ar-SA-HamedNeural",
    "hi": "hi-IN-SwaraNeural",
    "nl": "nl-NL-ColetteNeural",
    "pl": "pl-PL-ZofiaNeural",
    "sv": "sv-SE-SofieNeural",
    "da": "da-DK-ChristelNeural",
    "fi": "fi-FI-NooraNeural",
    "no": "nb-NO-PernilleNeural",
    "cs": "cs-CZ-VlastaNeural",
    "hu": "hu-HU-NoemiNeural",
    "ro": "ro-RO-AlinaNeural",
    "uk": "uk-UA-PolinaNeural",
    "el": "el-GR-AthinaNeural",
    "id": "id-ID-GadisNeural",
    "ms": "ms-MY-YasminNeural",
    "th": "th-TH-PremwadeeNeural",
    "vi": "vi-VN-HoaiMyNeural",
}

# Shorts max süresi (saniye)
SHORTS_MAX_DURATION = 59

# Ortalama konuşma hızı (kelime/saniye) — edge-tts için yaklaşık
AVG_WORDS_PER_SEC = 2.6


def _truncate_scenes_to_word_limit(scenes: list[dict], word_limit: int) -> list[dict]:
    remaining = max(0, word_limit)
    truncated = []
    for scene in scenes:
        text = str(scene.get("narration") or "").strip()
        words = text.split()
        if not words or remaining <= 0:
            break
        if len(words) <= remaining:
            truncated.append(dict(scene))
            remaining -= len(words)
            continue

        kept_text = " ".join(words[:remaining])
        last_sentence_end = max(kept_text.rfind("."), kept_text.rfind("!"), kept_text.rfind("?"))
        if last_sentence_end > 0:
            kept_text = kept_text[:last_sentence_end + 1]
        else:
            kept_text += "."
        truncated.append({**scene, "narration": kept_text})
        break
    return truncated


def _scene_word_ranges(scenes: list[dict]) -> list[tuple[int, int]]:
    ranges = []
    cursor = 0
    for scene in scenes:
        count = len(str(scene.get("narration") or "").split())
        ranges.append((cursor, cursor + count))
        cursor += count
    return ranges


def estimate_subtitle_segments(
    narration: str,
    n_segments: int,
    total_duration: float,
) -> list[str]:
    """
    Narration metnini n_segments zaman dilimine böler.
    """
    if not narration.strip() or n_segments <= 0:
        return [""] * max(n_segments, 1)

    sentences = re.split(r'(?<=[.!?])\s+', narration.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [""] * n_segments

    word_counts = [len(s.split()) for s in sentences]
    total_words = sum(word_counts)
    if total_words == 0:
        return [""] * n_segments

    cumulative = 0.0
    sent_intervals = []
    for wc, sent in zip(word_counts, sentences):
        ratio = wc / total_words
        t_s = cumulative
        t_e = cumulative + ratio
        sent_intervals.append((t_s, t_e, sent))
        cumulative = t_e

    seg_dur_ratio = 1.0 / n_segments
    segments = []

    for seg_idx in range(n_segments):
        seg_s = seg_idx * seg_dur_ratio
        seg_e = (seg_idx + 1) * seg_dur_ratio

        collected = []
        for t_s, t_e, sent in sent_intervals:
            overlap_s = max(t_s, seg_s)
            overlap_e = min(t_e, seg_e)
            if overlap_e > overlap_s:
                sent_span = t_e - t_s
                if sent_span == 0:
                    continue
                overlap_ratio = (overlap_e - overlap_s) / sent_span
                if overlap_ratio >= 0.40:
                    collected.append(sent)

        if not collected:
            mid = (seg_s + seg_e) / 2
            closest = min(sent_intervals, key=lambda x: abs((x[0] + x[1]) / 2 - mid))
            collected = [closest[2]]

        text = " ".join(collected)
        if len(text) > 200:
            sents_here = re.split(r'(?<=[.!?])\s+', text)
            text = " ".join(sents_here[-2:]) if len(sents_here) > 1 else sents_here[-1]
        segments.append(text.strip())

    return segments


# ──────────────────────────────────────────
# NASA görsel kaynağı
# ──────────────────────────────────────────

class NASAImageFetcher:
    BASE_URL = "https://images-api.nasa.gov"
    APOD_URL = "https://api.nasa.gov/planetary/apod"

    def __init__(self, api_key: str = "DEMO_KEY"):
        self.api_key = api_key

    def is_nasa_owned(self, item: dict) -> bool:
        data_list = item.get("data", [])
        if not data_list:
            return False
        data = data_list[0]
        
        center = data.get("center", "").upper()
        secondary_creator = data.get("secondary_creator", "").upper()
        photographer = data.get("photographer", "").upper()
        description = data.get("description", "").upper()
        title = data.get("title", "").upper()
        
        # 1. Kaynağı NASA dışı olan ajans/şirketlerin (ESA, JAXA, SpaceX) elenmesi
        exclude_identifiers = {
            "ESA", "EUROPEAN SPACE AGENCY", "JAXA", "JAPAN AEROSPACE", "SPACEX", "JAPANESE AEROSPACE"
        }
        for ex_ident in exclude_identifiers:
            if (ex_ident in center or 
                ex_ident in secondary_creator or 
                ex_ident in photographer or 
                ex_ident in description or 
                ex_ident in title):
                print(f"[NASA Check] Medya elendi: {title} ({ex_ident} kaynaklı)")
                return False
                
        # 2. Ofis, idari bina, logo, jenerik veya alakasız kurumsal görsellerin elenmesi
        office_keywords = {
            "BUILDING", "OFFICE", "HEADQUARTERS", "HQ", "CONFERENCE", 
            "CLASSROOM", "FACILITY", "EXTERIOR", "AUDITORIUM", 
            "MUSEUM", "EXHIBIT", "PRESS BRIEFING", "BRIEFING", 
            "RIBBON CUTTING", "CEREMONY", "ADMINISTRATION", "ADMINISTRATIVE",
            "HALLWAY", "LOBBY", "PORTRAIT", "EMPLOYEE", "STAFF",
            "SHAKING HANDS", "GROUP PHOTO", "AWARDS", "AWARD", "PRESS CONFERENCE",
            "LOGO", "BUMPER", "IDENT", "MEATBALL", "WORM LOGO", "TITLE CARD", "CREDITS", "NASA LOGO"
        }
        for off_key in office_keywords:
            if (off_key in title or 
                off_key in description or 
                any(off_key in str(kw).upper() for kw in data.get("keywords", []))):
                print(f"[NASA Check] Medya elendi: {title} ({off_key} konulu kurumsal/ofis görseli)")
                return False

        # 3. NASA sahipliği doğrulaması
        # Resmi NASA görsel veritabanında arandığı için, dışlama listesinde değilse varsayılan olarak kabul edilir.
        return True

    def search_images(self, query: str, count: int = 5) -> list[str]:
        try:
            r = requests.get(
                f"{self.BASE_URL}/search",
                params={"q": query, "media_type": "image"},
                timeout=10,
            )
            items = r.json().get("collection", {}).get("items", [])
            urls = []
            for item in items:
                if self.is_nasa_owned(item):
                    links = item.get("links", [])
                    if links:
                        urls.append(links[0]["href"])
                        if len(urls) >= count:
                            break
            return urls
        except Exception as e:
            print(f"[NASA] Arama hatası: {e}")
            return []

    def search_videos(self, query: str, count: int = 3) -> list[str]:
        """NASA API'sinden video araması yapar ve video dosya linklerini (genellikle mp4) döner."""
        try:
            r = requests.get(
                f"{self.BASE_URL}/search",
                params={"q": query, "media_type": "video"},
                timeout=10,
            )
            items = r.json().get("collection", {}).get("items", [])
            video_urls = []
            for item in items:
                if not self.is_nasa_owned(item):
                    continue
                # Video varlıklarının dosya linkleri listesini (collection.json) çek
                href = item.get("href")
                if href:
                    res_files = requests.get(href, timeout=5)
                    files_list = res_files.json()
                    # MP4 formatındaki en yüksek kaliteli dosyaları seç
                    mp4_links = [f for f in files_list if isinstance(f, str) and (
                        f.endswith("orig.mp4") or f.endswith("~large.mp4") or f.endswith("~medium.mp4") or f.endswith(".mp4")
                    )]
                    if mp4_links:
                        # Tercihen sıkıştırılmış web formatları (medium, large, mobile) seçilir.
                        # orig.mp4 çok büyük boyutlu (gigabaytlarca) olabildiği için en son tercih edilir.
                        chosen = None
                        for suffix in ["~medium.mp4", "~large.mp4", "~mobile.mp4"]:
                            match = [link for link in mp4_links if link.endswith(suffix)]
                            if match:
                                chosen = match[0]
                                break
                        if not chosen:
                            chosen = mp4_links[0]
                        video_urls.append(chosen)
                        if len(video_urls) >= count:
                            break
            return video_urls
        except Exception as e:
            print(f"[NASA Video] Arama hatası: {e}")
            return []

    def get_apod(self) -> dict:
        try:
            r = requests.get(
                self.APOD_URL,
                params={"api_key": self.api_key},
                timeout=10,
            )
            data = r.json()
            explanation = data.get("explanation", "").upper()
            copyright_info = data.get("copyright", "").upper()
            title = data.get("title", "").upper()
            
            exclude_identifiers = {
                "ESA", "EUROPEAN SPACE AGENCY", "JAXA", "JAPAN AEROSPACE", "SPACEX", "JAPANESE AEROSPACE"
            }
            for ex_ident in exclude_identifiers:
                if ex_ident in explanation or ex_ident in copyright_info or ex_ident in title:
                    print(f"[NASA APOD] Kaynak NASA dışı ({ex_ident}) olduğu için APOD elendi.")
                    return {}
            return data
        except Exception as e:
            print(f"[NASA APOD] Hata: {e}")
            return {}

    def download_image(self, url: str, dest: str) -> bool:
        try:
            r = requests.get(url, timeout=15, stream=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"[NASA] İndirme hatası: {e}")
            return False


# ──────────────────────────────────────────
# Ses üretici
# ──────────────────────────────────────────

class AudioGenerator:
    def __init__(self):
        try:
            from settings_manager import SettingsManager
        except ImportError:
            from src.settings_manager import SettingsManager
        self.settings = SettingsManager()

    async def generate(self, text: str, lang: str, output_path: str, scenes: list[dict] = None) -> tuple[bool, list[dict]]:
        # Akıllı Dil Doğrulaması (Kanal dili 'tr' kalsa bile metin İngilizce/Almanca ise otomatik düzeltir)
        try:
            from langdetect import detect
            det_lang = detect(text[:600])
            if det_lang in ["en", "de", "fr", "es", "it", "ru", "ar", "ja", "tr"] and det_lang != lang.lower().strip():
                print(f"[TTS] 🌐 Metin dili '{det_lang}' olarak tespit edildi (seçili: '{lang}'). '{det_lang}' motoruna geçiriliyor.")
                lang = det_lang
        except Exception:
            pass

        if lang.lower().strip() == "tr":
            try:
                from text_normalizer import normalize_turkish_tts_text
            except ImportError:
                from src.text_normalizer import normalize_turkish_tts_text
            text = normalize_turkish_tts_text(text)

        engine = self.settings.get("tts_engine", "edge-tts")
        ref_voice = self.settings.get("chatterbox_voice", "")

        if engine == "chatterbox":
            try:
                from chatterbox_generator import ChatterboxAudioGenerator
            except ImportError:
                from src.chatterbox_generator import ChatterboxAudioGenerator
            generator = ChatterboxAudioGenerator()
            wav_path = output_path
            if wav_path.endswith(".mp3"):
                wav_path = wav_path.replace(".mp3", ".wav")
            ok, boundaries = generator.generate(
                text=text,
                lang=lang,
                output_path=wav_path,
                audio_prompt_path=ref_voice if ref_voice else None,
                scenes=scenes
            )
            if ok:
                rvc_pth = self.settings.get("rvc_pth_path")
                rvc_idx = self.settings.get("rvc_index_path")
                pitch = int(self.settings.get("rvc_pitch", 0) or 0)
                if rvc_pth and rvc_idx and os.path.exists(rvc_pth) and os.path.exists(rvc_idx) and os.path.exists(wav_path):
                    try:
                        from voice_clone_manager import VoiceCloneManager
                        temp_rvc = wav_path + ".rvc.wav"
                        if VoiceCloneManager.run_rvc_inference(wav_path, temp_rvc, rvc_pth, rvc_idx, pitch=pitch):
                            shutil.move(temp_rvc, wav_path)
                            print(f"[RVC] 🎙️ Sese Applio RVC modeli başarıyla giydirildi (pitch={pitch}) → {wav_path}")
                    except Exception as rvc_err:
                        print(f"[RVC] Uyarı: RVC dönüşüm hatası ({rvc_err}), taban ses kullanılıyor.")

                # Ultrasonik Telif Filigranı Mühürleme
                if os.path.exists(wav_path):
                    try:
                        from audio_watermark import AudioWatermarker
                        AudioWatermarker.embed(wav_path, signature="ALIENES!")
                    except Exception as wm_err:
                        print(f"[WATERMARK] Filigran ekleme uyarısı: {wm_err}")

            return ok, boundaries
        else:
            pitch = int(self.settings.get("rvc_pitch", 0) or 0)
            voice = VOICE_MAP.get(lang, "en-US-GuyNeural")
            boundaries = []
            try:
                scene_texts = [
                    (idx, str(scene.get("narration") or "").strip())
                    for idx, scene in enumerate(scenes or [])
                    if str(scene.get("narration") or "").strip()
                ]
                use_scene_audio = (
                    len(scene_texts) > 1
                    and len(scene_texts) == len(scenes or [])
                )
                if use_scene_audio:
                    scene_audio_paths = []
                    scene_offset = 0.0
                    with tempfile.TemporaryDirectory(
                        prefix=".tts-scenes-", dir=str(Path(output_path).parent)
                    ) as temp_dir:
                        for scene_idx, scene_text in scene_texts:
                            scene_path = str(Path(temp_dir) / f"scene_{scene_idx:04d}.mp3")
                            scene_boundaries = []
                            communicate = edge_tts.Communicate(scene_text, voice)
                            with open(scene_path, "wb") as f:
                                async for chunk in communicate.stream():
                                    if chunk["type"] == "audio":
                                        f.write(chunk["data"])
                                    elif chunk["type"] == "SentenceBoundary":
                                        scene_boundaries.append({
                                            "text": chunk["text"],
                                            "offset": chunk["offset"] / 10000000.0,
                                            "duration": chunk["duration"] / 10000000.0,
                                            "scene_idx": scene_idx,
                                        })
                            with AudioFileClip(scene_path) as scene_audio:
                                scene_duration = scene_audio.duration
                            if scene_duration <= 0:
                                raise RuntimeError(f"TTS sahne {scene_idx} için ses süresi ölçülemedi.")
                            if not scene_boundaries:
                                scene_boundaries = [{
                                    "text": scene_text,
                                    "offset": 0.0,
                                    "duration": scene_duration,
                                    "scene_idx": scene_idx,
                                }]
                            for boundary in scene_boundaries:
                                boundary["offset"] += scene_offset
                            boundaries.extend(scene_boundaries)
                            scene_audio_paths.append(scene_path)
                            scene_offset += scene_duration

                        if len(scene_audio_paths) == 1:
                            shutil.copyfile(scene_audio_paths[0], output_path)
                        else:
                            command = ["ffmpeg", "-y"]
                            for scene_path in scene_audio_paths:
                                command.extend(["-i", scene_path])
                            audio_inputs = "".join(f"[{idx}:a:0]" for idx in range(len(scene_audio_paths)))
                            command.extend([
                                "-filter_complex",
                                f"{audio_inputs}concat=n={len(scene_audio_paths)}:v=0:a=1[aout]",
                                "-map", "[aout]",
                                "-c:a", "libmp3lame",
                                "-q:a", "2",
                                output_path,
                            ])
                            result = subprocess.run(command, capture_output=True, text=True)
                            if result.returncode != 0:
                                raise RuntimeError(f"Sahne sesleri birleştirilemedi: {result.stderr[-1200:]}")
                            if not Path(output_path).is_file() or Path(output_path).stat().st_size == 0:
                                raise RuntimeError("Sahne sesleri birleştirildi ancak ses dosyası oluşturulamadı.")
                else:
                    communicate = edge_tts.Communicate(text, voice)
                    with open(output_path, "wb") as f:
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                            elif chunk["type"] == "SentenceBoundary":
                                boundaries.append({
                                    "text": chunk["text"],
                                    "offset": chunk["offset"] / 10000000.0,
                                    "duration": chunk["duration"] / 10000000.0
                                })

                # RVC (Applio) Post-Processing for Edge-TTS
                rvc_pth = self.settings.get("rvc_pth_path")
                rvc_idx = self.settings.get("rvc_index_path")
                if rvc_pth and rvc_idx and os.path.exists(rvc_pth) and os.path.exists(rvc_idx) and os.path.exists(output_path):
                    try:
                        from voice_clone_manager import VoiceCloneManager
                        temp_rvc = output_path + ".rvc.wav"
                        if VoiceCloneManager.run_rvc_inference(output_path, temp_rvc, rvc_pth, rvc_idx, pitch=pitch):
                            shutil.move(temp_rvc, output_path)
                            print(f"[RVC] 🎙️ Edge-TTS sesine Applio RVC modeli başarıyla giydirildi (pitch={pitch}) → {output_path}")
                    except Exception as rvc_err:
                        print(f"[RVC] Uyarı: RVC dönüşüm hatası ({rvc_err})")

                # Ultrasonik Telif Filigranı Mühürleme
                if os.path.exists(output_path):
                    try:
                        from audio_watermark import AudioWatermarker
                        AudioWatermarker.embed(output_path, signature="ALIENES!")
                    except Exception as wm_err:
                        print(f"[WATERMARK] Filigran ekleme uyarısı: {wm_err}")

                print(f"[TTS] Ses üretildi → {output_path} | {len(boundaries)} cümle sınırı yakalandı")
                return True, boundaries
            except Exception as e:
                print(f"[TTS] Hata: {e}")
                return False, []

    def generate_sync(self, text: str, lang: str, output_path: str, scenes: list[dict] = None) -> tuple[bool, list[dict]]:
        res = asyncio.run(self.generate(text, lang, output_path, scenes))
        if os.path.exists(output_path):
            try:
                from audio_watermark import AudioWatermarker
                AudioWatermarker.embed(output_path, signature="ALIENES!")
            except Exception:
                pass
        return res


# ──────────────────────────────────────────
# Legacy VideoComposer — geriye dönük uyumluluk
# ──────────────────────────────────────────

class VideoComposer:
    """
    Eski tek-aşamalı kompozisyon. Yeni projeler için VideoEditor (iki aşamalı)
    tercih edilmeli, ancak bu sınıf geriye dönük uyumluluk için korunuyor.
    """
    LANDSCAPE_W, LANDSCAPE_H = 1920, 1080
    PORTRAIT_W,  PORTRAIT_H  = 1080, 1920
    FPS = 24
    TRANSITION_DUR = 0.5

    def __init__(self, shorts_mode: bool = False):
        self.shorts_mode = shorts_mode
        self.WIDTH  = self.PORTRAIT_W  if shorts_mode else self.LANDSCAPE_W
        self.HEIGHT = self.PORTRAIT_H  if shorts_mode else self.LANDSCAPE_H

    @staticmethod
    def _load_font(size: int):
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "Arial.ttf",
            "DejaVuSans.ttf",
        ]
        for fp in candidates:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap_text(text: str, font, max_width: int) -> list[str]:
        lines, current = [], []
        for word in text.split():
            test = " ".join(current + [word])
            bb = font.getbbox(test)
            if (bb[2] - bb[0]) <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        return lines or [""]

    def _prepare_base_image(self, image_path: str) -> np.ndarray:
        try:
            img = Image.open(image_path).convert("RGB")
            src_ratio = img.width / img.height
            tgt_ratio = self.WIDTH / self.HEIGHT
            if src_ratio > tgt_ratio:
                new_h = self.HEIGHT
                new_w = int(new_h * src_ratio)
            else:
                new_w = self.WIDTH
                new_h = int(new_w / src_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - self.WIDTH) // 2
            top  = (new_h - self.HEIGHT) // 2
            img  = img.crop((left, top, left + self.WIDTH, top + self.HEIGHT))
        except Exception:
            img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (5, 5, 30))
        return np.array(img)

    def _make_frame_array(self, image_path: str, subtitle: str = "") -> np.ndarray:
        """Legacy: görsel + altyazı tek bir frame'e bake."""
        base = self._prepare_base_image(image_path)
        if not subtitle:
            return base
        img = Image.fromarray(base).convert("RGBA")
        band_h = 240 if self.shorts_mode else 180
        overlay = Image.new("RGBA", (self.WIDTH, band_h), (0, 0, 0, 185))
        img.paste(overlay, (0, self.HEIGHT - band_h), overlay)
        img = img.convert("RGB")
        font_size = 54 if self.shorts_mode else 42
        font = self._load_font(font_size)
        max_w = self.WIDTH - 140
        lines = self._wrap_text(subtitle, font, max_w)
        line_h = font_size + 10
        total_h = len(lines) * line_h
        center_y = self.HEIGHT - band_h // 2 - total_h // 2
        draw = ImageDraw.Draw(img)
        for i, line in enumerate(lines):
            bb = font.getbbox(line)
            lw = bb[2] - bb[0]
            x = (self.WIDTH - lw) / 2
            y = center_y + i * line_h
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, -2), (0, 2), (-2, 0), (2, 0)]:
                draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 230))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        return np.array(img)

    # ── Legacy geçiş klipleri (caption bake ile kullanılır) ──
    def _clip_none(self, frame, duration):
        return ImageClip(frame).with_duration(duration)

    def _clip_fade(self, fc, fn, duration):
        td = min(self.TRANSITION_DUR, duration * 0.4)
        fc = fc.astype(np.float32)
        fn = fn.astype(np.float32)
        def mf(t):
            if t >= duration - td and td > 0:
                alpha = min(1.0, (t - (duration - td)) / td)
                return (fc * (1.0 - alpha) + fn * alpha).astype(np.uint8)
            return fc.astype(np.uint8)
        return VideoClip(mf, duration=duration)

    def _clip_zoom(self, frame, duration):
        W, H = self.WIDTH, self.HEIGHT
        pil = Image.fromarray(frame)
        def mf(t):
            scale = 1.0 + 0.05 * (t / max(duration, 0.001))
            new_w = max(W, int(W * scale))
            new_h = max(H, int(H * scale))
            resized = pil.resize((new_w, new_h), Image.BILINEAR)
            x = (new_w - W) // 2
            y = (new_h - H) // 2
            return np.array(resized.crop((x, y, x + W, y + H)))
        return VideoClip(mf, duration=duration)

    def _clip_slide(self, fc, fn, duration):
        W, H = self.WIDTH, self.HEIGHT
        td = min(self.TRANSITION_DUR, duration * 0.4)
        def mf(t):
            if t < duration - td:
                return fc
            progress = min(1.0, (t - (duration - td)) / max(td, 0.001))
            offset = int(W * progress)
            canvas = np.empty((H, W, 3), dtype=np.uint8)
            vis = W - offset
            if vis > 0:
                canvas[:, :vis] = fc[:, offset:offset + vis]
            if offset > 0:
                canvas[:, vis:] = fn[:, :offset]
            return canvas
        return VideoClip(mf, duration=duration)

    def compose(
        self,
        audio_path: str,
        output_path: str,
        segments: list[dict],
        transition: str = "fade",
    ) -> bool:
        """Legacy compose — yeni projelerde VideoEditor tercih edilmeli."""
        try:
            audio = AudioFileClip(audio_path)
            total_dur = audio.duration
            if self.shorts_mode and total_dur > SHORTS_MAX_DURATION:
                total_dur = SHORTS_MAX_DURATION
                audio = audio.subclipped(0, total_dur)

            print(f"[VIDEO/legacy] {len(segments)} segment | toplam süre={total_dur:.1f}s | geçiş: {transition}")
            frames = [self._make_frame_array(s["image_path"], s.get("text", "")) for s in segments]
            clips = []
            for i, frame in enumerate(frames):
                nf = frames[i + 1] if i + 1 < len(frames) else frame
                dur = segments[i]["duration"]
                if transition == "zoom":
                    clip = self._clip_zoom(frame, dur)
                elif transition == "slide":
                    clip = self._clip_slide(frame, nf, dur)
                elif transition == "fade":
                    clip = self._clip_fade(frame, nf, dur)
                else:
                    clip = self._clip_none(frame, dur)
                clips.append(clip)
            video = concatenate_videoclips(clips, method="chain")
            video = video.with_audio(audio)
            write_kwargs = dict(
                fps=self.FPS, codec="libx264", audio_codec="aac",
                logger=None, preset="fast", pixel_format="yuv420p",
            )
            if self.shorts_mode:
                write_kwargs["ffmpeg_params"] = ["-vf", "setsar=1"]
            video.write_videofile(output_path, **write_kwargs)
            return True
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[VIDEO/legacy] Hata: {e}")
            return False


# ──────────────────────────────────────────
# VideoGenerator — yeni pipeline
# ──────────────────────────────────────────

class VideoGenerator:
    """
    Tam pipeline: senaryo → ses → görsel → video (v3, iki aşamalı).

    Yeni davranış:
      - Caption'lar image_path'e göre gruplanır (caption kaynaklı sahte geçiş yok).
      - Base video altyazısız üretilir.
      - ASS altyazı ayrı katman olarak ffmpeg ile bindirilir.
      - Opsiyonel BGM, watermark, intro/outro.
    """

    def __init__(self, nasa_api_key: str = "DEMO_KEY"):
        self.nasa = NASAImageFetcher(nasa_api_key)
        self.tts  = AudioGenerator()

    def _censor_faces(self, image_path: str):
        try:
            import cv2
            import os
            
            if not os.path.exists(image_path):
                return
                
            img = cv2.imread(image_path)
            if img is None:
                return
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Load cascades
            face_cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            profile_cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_profileface.xml")
            
            faces = []
            if os.path.exists(face_cascade_path):
                face_cascade = cv2.CascadeClassifier(face_cascade_path)
                found_faces = face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                if len(found_faces) > 0:
                    faces.extend(list(found_faces))
                
            if os.path.exists(profile_cascade_path):
                profile_cascade = cv2.CascadeClassifier(profile_cascade_path)
                found_profiles = profile_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                if len(found_profiles) > 0:
                    faces.extend(list(found_profiles))
                
            if len(faces) > 0:
                print(f"[CENSOR] Görselde {len(faces)} adet insan yüzü tespit edildi, sansürleniyor: {image_path}")
                for (x, y, w, h) in faces:
                    face_roi = img[y:y+h, x:x+w]
                    # Gaussian blur kernel size (must be positive and odd)
                    ksize = int(w / 2.5) | 1
                    if ksize < 3:
                        ksize = 3
                    blurred = cv2.GaussianBlur(face_roi, (ksize, ksize), 30)
                    img[y:y+h, x:x+w] = blurred
                    
                cv2.imwrite(image_path, img)
        except Exception as e:
            print(f"[CENSOR] Hata oluştu: {e}")

    def _censor_custom_areas(self, image_path: str):
        # User request: Resimlerdeki sansür (blur) kaldırıldı.
        return

    def download_liveatc_chat(self, topic: str, work_dir: Path, script: dict = None) -> str | None:
        import time
        import requests
        work_dir = Path(work_dir)
        out_file = work_dir / "liveatc_chat.mp3"
        
        if out_file.exists():
            return str(out_file)

        # 1. Doğrudan archive.liveatc.net adresinden indirmeyi dene (parametreler geçerliyse)
        if script:
            icao = script.get("liveatc_icao")
            freq = script.get("liveatc_freq_type")
            dt_utc = script.get("liveatc_datetime_utc")

            if icao and freq and dt_utc and "unknown" not in (str(icao).lower(), str(freq).lower(), str(dt_utc).lower()):
                icao_lower = str(icao).lower().strip()
                icao_upper = icao_lower.upper()
                freq_clean = str(freq).strip()
                dt_clean = str(dt_utc).strip()

                # URL şablonu oluştur (örn: https://archive.liveatc.net/kjfk/KJFK-Twr-Jul-09-2026-1200Z.mp3)
                url = f"https://archive.liveatc.net/{icao_lower}/{icao_upper}-{freq_clean}-{dt_clean}Z.mp3"
                print(f"[LIVEATC] archive.liveatc.net üzerinden doğrudan telsiz kaydı indiriliyor: {url}")

                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.liveatc.net/"
                }

                # Saygılı bekleme (IP ban riskini azaltmak için)
                time.sleep(1.5)

                try:
                    r = requests.get(url, headers=headers, timeout=20, stream=True)
                    if r.status_code == 200:
                        with open(out_file, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        print(f"[LIVEATC] Doğrudan LiveATC arşivi başarıyla indirildi: {out_file}")
                        return str(out_file)
                    else:
                        print(f"[LIVEATC] Doğrudan indirme HTTP hatası: {r.status_code} (YouTube aramasına geçiliyor...)")
                except Exception as ex:
                    print(f"[LIVEATC] Doğrudan indirme sırasında hata oluştu: {ex} (YouTube aramasına geçiliyor...)")

        # 2. Fallback: yt-dlp ile YouTube araması üzerinden indir
        print(f"[LIVEATC] YouTube üzerinden '{topic}' telsiz sesleri aranıyor...")
        query = f"ytsearch1:LiveATC {topic} ATC Audio"
        
        project_root = Path(__file__).resolve().parent.parent
        yt_dlp_bin = project_root / ".venv" / "bin" / "yt-dlp"
        if not yt_dlp_bin.exists():
            yt_dlp_bin = "yt-dlp"
            
        cmd = [
            str(yt_dlp_bin),
            query,
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "-o", str(work_dir / "liveatc_chat.%(ext)s")
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=90)
            if res.returncode == 0 and out_file.exists():
                print(f"[LIVEATC] Gerçek incident telsiz konuşması başarıyla indirildi (YouTube): {out_file}")
                return str(out_file)
        except Exception as e:
            print(f"[LIVEATC] Hata: {e}")
        return None

    @staticmethod
    def _split_text_and_duration(text: str, duration: float, max_words: int = 6) -> list[tuple[str, float]]:
        words = text.split()
        if not words:
            return []
        if len(words) <= max_words:
            return [(text, duration)]
        chunks = []
        current_chunk = []
        for w in words:
            current_chunk.append(w)
            if len(current_chunk) >= max_words:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        total_chars = sum(len(c) for c in chunks)
        res = []
        for c in chunks:
            c_dur = duration * (len(c) / total_chars) if total_chars > 0 else duration / len(chunks)
            res.append((c, c_dur))
        return res

    def _build_segments(
        self,
        boundaries: list[dict],
        real_duration: float,
        is_story_mode: bool,
        images: list[str],
        scene_images: dict,
        work_dir: Path,
        keywords: list[str],
        composer_w: int,
        composer_h: int,
    ) -> list[dict]:
        """
        Boundary'leri → segment listesi (text, duration, image_path).
        Her boundary önce 6 kelimelik alt parçalara bölünür, sonra image atanır.
        """
        ordered_boundaries = sorted(boundaries, key=lambda boundary: float(boundary.get("offset", 0.0)))
        valid_boundaries = []
        for boundary_index, b in enumerate(ordered_boundaries):
            start = max(0.0, float(b.get("offset", 0.0)))
            if start < real_duration:
                speech_end = start + max(0.0, float(b.get("duration", 0.0)))
                next_start = (
                    float(ordered_boundaries[boundary_index + 1].get("offset", real_duration))
                    if boundary_index + 1 < len(ordered_boundaries)
                    else real_duration
                )
                # Keep pauses in the timeline rather than compressing them out of the visuals.
                end = min(real_duration, max(speech_end, start, next_start))
                if end > start:
                    valid_boundaries.append({**b, "duration": end - start})

        segments = []
        for b in valid_boundaries:
            duration = b["duration"]
            if duration > 0.05:
                sub_parts = self._split_text_and_duration(b["text"], duration, max_words=6)
                img_path = b.get("image_path", "")
                for sub_text, sub_dur in sub_parts:
                    if sub_dur > 0.05:
                        segments.append({
                            "text": sub_text,
                            "duration": sub_dur,
                            "image_path": img_path,
                            "emotion": b.get("emotion", "neutral")
                        })

        if not segments:
            fallback_img = images[0] if images else ""
            segments = [{
                "text": "",
                "duration": real_duration,
                "image_path": fallback_img
            }]
        else:
            tot_seg_dur = sum(s["duration"] for s in segments)
            if tot_seg_dur < real_duration:
                segments[-1]["duration"] += (real_duration - tot_seg_dur)

        return segments

    def _resolve_reddit_bgm(self, is_reddit: bool, script: dict, edit_options: dict, narration: str, title: str, work_dir: Optional[Path] = None, duration: float = 0.0) -> Optional[str]:
        """
        Arka plan müziği çözümler:
        1. script içinde bgm_timeline varsa build_timeline_bgm_track ile telifsiz müzikleri birleştirir.
        2. Kullanıcı tarafından ayarlanmış geçerli bir yol varsa onu kullanır.
        3. Reddit hikayesi ise resmi müziği seçer.
        4. Diğer kategoriler için uygun parçayı audio_library'den seçer.
        """
        # 1. bgm_timeline kontrolü
        if isinstance(script, dict) and script.get("bgm_timeline") and work_dir and duration > 1.0:
            try:
                try:
                    import audio_library as _al
                except ImportError:
                    import src.audio_library as _al
                bgm_vol = float(edit_options.get("bgm_volume") or 0.08)
                mixed_track = _al.build_timeline_bgm_track(
                    bgm_timeline=script["bgm_timeline"],
                    total_duration=duration,
                    work_dir=Path(work_dir),
                    base_volume=bgm_vol
                )
                if mixed_track and mixed_track.is_file():
                    print(f"[VIDEO-GEN-BGM] bgm_timeline başarıyla derlendi: {mixed_track.name}")
                    return str(mixed_track)
            except Exception as bt_err:
                print(f"[VIDEO-GEN-BGM] bgm_timeline hatası: {bt_err}")

        # Kullanıcı tarafından ayarlanmış geçerli bir yol varsa onu kullan
        user_bgm = edit_options.get("bgm_path")
        if user_bgm and str(user_bgm).lower() not in ("none", "false", "") and os.path.exists(user_bgm):
            return user_bgm

        if not is_reddit:
            return user_bgm if (user_bgm and os.path.exists(user_bgm)) else None

        # Reddit hikayeleri için resmi fon müziği: Huma-Huma - From Russia With Love
        project_root = Path(__file__).resolve().parent.parent
        official_candidates = [
            project_root / "assets" / "music" / "reddit_official_bgm.mp3",
            project_root / "config" / "bgm" / "reddit_official_bgm.mp3",
            project_root / "audio_cache" / "reddit_official_bgm.mp3",
            project_root / "assets" / "music" / "lofi_storyteller.mp3",
        ]
        for cand in official_candidates:
            if cand.exists():
                print(f"[REDDIT-BGM] Resmi Reddit fon müziği (Huma-Huma - From Russia With Love) seçildi: {cand.name}")
                return str(cand)

        # audio_library modülünü kullan (fonksiyon tabanlı)
        try:
            try:
                import audio_library as _al
            except ImportError:
                import src.audio_library as _al

            track_id = "reddit_official_bgm"
            dl_dir = project_root / "assets" / "music"
            dl_dir.mkdir(parents=True, exist_ok=True)
            mp3_path = _al.download_track(track_id, dl_dir)
            if mp3_path and mp3_path.exists():
                print(f"[REDDIT-BGM] İndirilen resmi müzik: {mp3_path.name}")
                return str(mp3_path)
        except Exception as bgm_err:
            print(f"[REDDIT-BGM] audio_library hatası: {bgm_err}")

        # Son çare: herhangi bir mp3/wav dosyası ara
        try:
            import glob as _glob
            base = Path(__file__).resolve().parent.parent
            search_dirs = [
                base / "assets" / "music",
                base / "assets" / "audio",
                base / "assets",
                base / "audio_cache",
            ]
            candidates = []
            for d in search_dirs:
                if d.exists():
                    for ext in ["*.mp3", "*.wav", "*.ogg", "*.m4a"]:
                        candidates.extend(_glob.glob(str(d / ext)))
            if candidates:
                import random as _rnd
                chosen = _rnd.choice(candidates)
                print(f"[REDDIT-BGM] Yerel dosyadan müzik: {os.path.basename(chosen)}")
                return chosen
        except Exception:
            pass

        print("[REDDIT-BGM] Uygun arka plan müziği bulunamadı, BGM olmadan devam ediliyor.")
        return None

    def run(
        self,
        script: dict,
        lang: str,
        output_dir: str,
        channel_id: str,
        shorts_mode: bool = False,
        transition: str = "fade",
        edit_options: Optional[dict] = None,
        custom_images: Optional[dict] = None,
        recompose_folder: Optional[str] = None,
    ) -> dict:
        """
        Tam video üretim pipeline'ı.

        edit_options (opsiyonel):
          subtitle_preset, subtitle_animation, bgm_path, bgm_volume,
          watermark_path, watermark_text, watermark_position,
          intro_clip_path, outro_clip_path, kenburns_intensity,
          transition_dur
        """
        if recompose_folder:
            work_dir = Path(recompose_folder)
            print(f"[RECOMPOSE] Mevcut klasör kullanılıyor: {work_dir}")
        else:
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix   = "_shorts" if shorts_mode else ""

            # Count existing folders to get the sequence number
            try:
                p = Path(output_dir)
                existing_indices = []
                if p.exists():
                    for item in p.iterdir():
                        if item.is_dir():
                            parts = item.name.split("_", 1)
                            if parts[0].isdigit() and len(parts[0]) == 4:
                                existing_indices.append(int(parts[0]))
                p_yuklenen = p.parent / "yuklenen"
                if p_yuklenen.exists():
                    for item in p_yuklenen.iterdir():
                        if item.is_dir():
                            parts = item.name.split("_", 1)
                            if parts[0].isdigit() and len(parts[0]) == 4:
                                existing_indices.append(int(parts[0]))
                next_idx = max(existing_indices) + 1 if existing_indices else 1
            except Exception:
                next_idx = 1

            prefix   = f"{next_idx:04d}_"
            work_dir = Path(output_dir) / f"{prefix}{channel_id}_{ts}{suffix}"
            work_dir.mkdir(parents=True, exist_ok=True)

        edit_options = edit_options or {}

        # Determine whether face censoring is enabled
        censor_faces_val = edit_options.get("censor_faces")
        if censor_faces_val is None:
            try:
                from settings_manager import SettingsManager
            except ImportError:
                from src.settings_manager import SettingsManager
            settings = SettingsManager()
            censor_faces_val = settings.get("censor_faces", True)

        if isinstance(censor_faces_val, str):
            censor_faces_enabled = censor_faces_val.lower() in ("true", "1", "yes")
        else:
            censor_faces_enabled = bool(censor_faces_val)

        narration = script.get("narration", "")
        title     = script.get("title", "Video")
        keywords  = script.get("keywords", ["space"])
        desc      = script.get("description", "")
        tags      = script.get("tags", keywords)

        # --- Kanal kategori bilgisini önce yükle (is_reddit gerekli) ---
        try:
            from channel_manager import ChannelManager as _CM
        except ImportError:
            from src.channel_manager import ChannelManager as _CM
        try:
            _ch_cfg = _CM().get_channel(channel_id)
            topic_category = _ch_cfg.get("topic_category", "space") if _ch_cfg else "space"
        except Exception:
            topic_category = "space"

        is_story  = (topic_category == "story")
        is_reddit = (topic_category in ("reddit_stories", "reddit"))
        is_whatsapp = (topic_category in ("whatsapp_stories", "whatsapp_chat", "whatsapp")
                       or script.get("category") in ("whatsapp_stories", "whatsapp_chat", "whatsapp")
                       or bool(script.get("messages")))
        use_nasa  = (topic_category not in ("story", "travel", "aviation", "reddit_stories", "reddit", "whatsapp_stories", "whatsapp_chat", "whatsapp", "crayon_combat", "military", "military_tech", "tech_finance_essay", "crayon_capital"))

        # WhatsApp diyalog videoları: Doğrudan özel Playwright + Dual Neural TTS motoruna yönlendir
        if is_whatsapp:
            try:
                from whatsapp.generator import generate_whatsapp_video
            except ImportError:
                from src.whatsapp.generator import generate_whatsapp_video
            print(f"[GENERATOR] WhatsApp Shorts motoru devreye girdi: {work_dir}")
            return generate_whatsapp_video(
                channel_config=_ch_cfg or {"channel_id": channel_id, "name": channel_id},
                script_data=script,
                work_dir=work_dir,
                output_dir=output_dir,
                edit_options=edit_options,
                custom_images=custom_images
            )

        # Crayon Combat & Askeri/Teknoloji Hiciv & Boş Kafa / Blackbox Çöp Adam kanalları: Tam kare animasyonlu çöp adam ve infografik motoruna yönlendir
        is_crayon = (topic_category in ("crayon_combat", "military", "military_tech", "crayon_capital", "tech_finance_essay", "stickman", "copadam", "cop_adam", "boskafa", "bos_kafa", "absurd_science", "what_if", "whatif", "absurd_engineering", "aviation", "blackbox", "havacilik", "flight", "flight_disaster", "air_crash")
                     or any(k in channel_id.lower() for k in ("crayon", "stickman", "boskafa", "copadam", "tacticallcrayon", "whatif", "absurd", "simulat", "blackbox", "aviation")))
        is_crayon_combat = topic_category in ("crayon_combat", "military", "military_tech") or (
            "tacticallcrayon" in channel_id.lower()
        )
        has_crayon_material = bool(script.get("scenes")) or (
            is_crayon_combat and bool(script.get("timeline_scenes"))
        )
        if is_crayon and has_crayon_material:
            try:
                from stickman_engine.crayon_generator import generate_crayon_video
            except ImportError:
                from src.stickman_engine.crayon_generator import generate_crayon_video
            print(f"[GENERATOR] Crayon Combat Animasyonlu Çöp Adam motoru devreye girdi: {work_dir}")
            return generate_crayon_video(
                channel_config=_ch_cfg or {"channel_id": channel_id, "name": channel_id},
                script_data=script,
                work_dir=work_dir,
                output_dir=output_dir,
                edit_options=edit_options,
                custom_images=custom_images,
                lang=lang
            )

        # Sinek Beyni Biyo-AI Müzik videoları: 3-5 dk uzun klip veya Shorts
        is_music = topic_category in ("music", "muzik", "connectome", "sinek_beyni")
        if is_music:
            try:
                from connectome.generator import generate_connectome_clip
            except ImportError:
                from src.connectome.generator import generate_connectome_clip
            print(f"[GENERATOR] Sinek Beyni Biyo-AI Müzik motoru devreye girdi: {work_dir}")
            
            dur_setting = edit_options.get("music_duration") or edit_options.get("video_duration")
            if dur_setting:
                try:
                    dur_val = float(dur_setting)
                except Exception:
                    dur_val = 180.0
            else:
                dur_val = 45.0 if shorts_mode else 180.0
                
            genre_setting = edit_options.get("music_genre", "emotional")
            theme_setting = edit_options.get("music_theme", "cosmic")
            
            return generate_connectome_clip(
                output_folder=work_dir,
                duration_sec=dur_val,
                genre=genre_setting,
                theme=theme_setting,
                is_vertical=shorts_mode,
                language=lang,
                writer=None,
            )

        # Reddit hikayeleri: her zaman Shorts (9:16) modu
        if is_reddit:
            shorts_mode = True

        if topic_category in ("aviation", "reddit_stories", "reddit"):
            censor_faces_enabled = False

        # Sahneleri birleştirerek tam narration'ı oluştur
        scenes = script.get("scenes", [])
        scenes_have_complete_narration = bool(scenes) and all(
            str(scene.get("narration") or "").strip() for scene in scenes
        )
        if scenes_have_complete_narration:
            narration = " ".join(str(scene["narration"]).strip() for scene in scenes)
        elif scenes and not narration:
            narration = " ".join(s.get("narration", "") for s in scenes)

        # Shorts için kelime kısıtı — Reddit 2-3dk uzun olduğundan kapsam dışı
        if shorts_mode and not is_reddit:
            words = narration.split()
            if len(words) > 130:
                if scenes_have_complete_narration:
                    scenes = _truncate_scenes_to_word_limit(scenes, 130)
                    narration = " ".join(scene["narration"] for scene in scenes)
                else:
                    truncated = " ".join(words[:130])
                    last_punct = max(
                        truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?")
                    )
                    narration = truncated[:last_punct + 1] if last_punct > 0 else truncated + "."

        # 1) TTS
        try:
            from settings_manager import SettingsManager
        except ImportError:
            from src.settings_manager import SettingsManager
        settings = SettingsManager()
        tts_engine = settings.get("tts_engine", "edge-tts")
        audio_ext = "wav" if tts_engine == "chatterbox" else "mp3"
        audio_path = str(work_dir / f"narration.{audio_ext}")

        # Check if narration audio already exists (recompose mode)
        audio_exists = False
        for ext in ["wav", "mp3"]:
            possible_audio = work_dir / f"narration.{ext}"
            if possible_audio.exists():
                audio_path = str(possible_audio)
                audio_exists = True
                print(f"[RECOMPOSE] Mevcut ses dosyası tespit edildi: {audio_path}")
                break

        if audio_exists:
            ok = True
            
            # Try to read precise boundaries from existing subs.ass
            tts_boundaries = None
            ass_path = work_dir / "subs.ass"
            if ass_path.exists():
                try:
                    parsed_boundaries = []
                    content = ass_path.read_text(encoding="utf-8")
                    lines = content.splitlines()
                    
                    def time_str_to_seconds(t_str: str) -> float:
                        parts = t_str.split(":")
                        if len(parts) != 3:
                            return 0.0
                        h = int(parts[0])
                        m = int(parts[1])
                        s, cs = parts[2].split(".")
                        seconds = float(s) + int(cs) / 100.0
                        return h * 3600 + m * 60 + seconds

                    for line in lines:
                        if line.startswith("Dialogue:"):
                            parts = line.split(",", 9)
                            if len(parts) >= 10:
                                start_str = parts[1].strip()
                                end_str = parts[2].strip()
                                text = parts[9].strip()
                                
                                import re
                                text_clean = re.sub(r"\{[^}]*\}", "", text).strip()
                                start = time_str_to_seconds(start_str)
                                end = time_str_to_seconds(end_str)
                                duration = end - start
                                
                                parsed_boundaries.append({
                                    "text": text_clean,
                                    "offset": start,
                                    "duration": duration
                                })
                    if parsed_boundaries:
                        tts_boundaries = parsed_boundaries
                        print(f"[RECOMPOSE] subs.ass dosyasından {len(tts_boundaries)} adet senkronlu sınır başarıyla çözümlendi.")
                except Exception as ass_err:
                    print(f"[RECOMPOSE] subs.ass okuma/ayrıştırma hatası: {ass_err}")
        else:
            ok, tts_boundaries = self.tts.generate_sync(narration, lang, audio_path, scenes=scenes)
            if not ok:
                raise RuntimeError("Seslendirme üretilemedi.")

        # 2) Channel Configuration — zaten yukarıda yüklendi (is_reddit, topic_category vs.)
        # Bu blok sadece uyumluluk amacıyla bakışımı doğrular
        # (topic_category, is_reddit, use_nasa, is_story zaten ayarlandı)

        # LiveATC audio download for aviation channels
        liveatc_path = None
        if topic_category == "aviation":
            topic = script.get("topic", "")
            if topic:
                try:
                    liveatc_path = self.download_liveatc_chat(topic, work_dir, script=script)
                except Exception as e:
                    print(f"[LIVEATC] Download failed: {e}")

        # 3) Boundary'leri oluştur (gerçek ses süresi ölçülür)
        from moviepy import AudioFileClip as AFC
        audio_clip = AFC(audio_path)
        real_duration = audio_clip.duration
        audio_clip.close()

        # Calculate intro/outro duration to subtract from shorts limit
        intro_dur = 0.0
        intro_path = edit_options.get("intro_clip_path")
        if intro_path and os.path.exists(intro_path):
            try:
                from moviepy import VideoFileClip as VFC
                clip = VFC(intro_path)
                intro_dur = clip.duration
                clip.close()
            except Exception:
                pass
                
        outro_dur = 0.0
        outro_path = edit_options.get("outro_clip_path")
        if outro_path and os.path.exists(outro_path):
            try:
                from moviepy import VideoFileClip as VFC
                clip = VFC(outro_path)
                outro_dur = clip.duration
                clip.close()
            except Exception:
                pass

        max_shorts_dur = (180.0 if is_reddit else 60.0) - intro_dur - outro_dur
        if max_shorts_dur < 10.0:
            max_shorts_dur = 10.0

        if shorts_mode and real_duration > max_shorts_dur:
            real_duration = max_shorts_dur

        # Use precise timing boundaries from TTS if available, else estimate using word counts
        if tts_boundaries:
            boundaries = []
            for tb in tts_boundaries:
                offset = tb["offset"]
                duration = tb["duration"]
                if offset < real_duration:
                    if offset + duration > real_duration:
                        duration = real_duration - offset
                    boundaries.append({
                        "text": tb["text"],
                        "offset": offset,
                        "duration": duration,
                        "scene_idx": tb.get("scene_idx"),
                        "image_path": tb.get("image_path", ""),
                        "emotion": tb.get("emotion", "neutral")
                    })
            if boundaries:
                last_end = boundaries[-1]["offset"] + boundaries[-1]["duration"]
                if last_end < real_duration:
                    boundaries[-1]["duration"] += (real_duration - last_end)
        else:
            # Fallback to estimated boundaries using word counts
            if scenes:
                boundaries = []
                word_counts = [len(s.get("narration", "").split()) for s in scenes]
                total_words = sum(word_counts)
                current_offset = 0.0
                for i, scene in enumerate(scenes):
                    wc = word_counts[i]
                    dur_each = real_duration * (wc / total_words) if total_words > 0 else real_duration / len(scenes)
                    boundaries.append({
                        "text": scene.get("narration", ""),
                        "offset": current_offset,
                        "duration": dur_each
                    })
                    current_offset += dur_each
            else:
                boundaries = []
                sentences = re.split(r'(?<=[.!?])\s+', narration.strip())
                sentences = [s.strip() for s in sentences if s.strip()]
                if not sentences:
                    sentences = [narration]
                word_counts = [len(s.split()) for s in sentences]
                total_words = sum(word_counts)
                current_offset = 0.0
                for sent, wc in zip(sentences, word_counts):
                    dur_each = real_duration * (wc / total_words) if total_words > 0 else real_duration / len(sentences)
                    boundaries.append({
                        "text": sent,
                        "offset": current_offset,
                        "duration": dur_each
                    })
                    current_offset += dur_each

        # Define visual scene targets (per-scene if scenes exist, else per-boundary)
        if scenes:
            scene_targets = []
            for i, scene in enumerate(scenes):
                scene_targets.append({
                    "index": i,
                    "narration": scene.get("narration", ""),
                    "nasa_keywords": scene.get("nasa_keywords", ""),
                    "image_prompt": scene.get("image_prompt", ""),
                })
        else:
            scene_targets = []
            for i, b in enumerate(boundaries):
                scene_targets.append({
                    "index": i,
                    "narration": b.get("text", ""),
                    "nasa_keywords": keywords[i % len(keywords)] if keywords else "",
                    "image_prompt": b.get("text", "") or (keywords[0] if keywords else "space astronomy"),
                })

        # 4) Sahneler için görsel eldesi (NASA + Stable Diffusion Fallback)
        scene_images = {}
        
        import random
        video_seed = random.randint(1, 1000000)

        # Dimension selection — Reddit always 9:16 (1080x1920)
        editor_cfg_W = 1080 if (shorts_mode or is_reddit) else 1920
        editor_cfg_H = 1920 if (shorts_mode or is_reddit) else 1080

        # Reddit Hikayeleri için ASMR video ve soru kartı hazırlığı
        reddit_card_path = None
        if is_reddit:
            try:
                from reddit_card_generator import generate_reddit_card
                from asmr_manager import prepare_asmr_background

                question_text = script.get("question") or script.get("title") or narration[:120]
                sub_name = script.get("subreddit")
                author_name = script.get("author")
                upvotes_val = script.get("upvotes", "28.4k")
                reddit_card_path = str(work_dir / "reddit_card_overlay.png")

                # Kanal veya Grup ayarlarından avatar ve kullanıcı adını al
                _ch_opts = _ch_cfg.get("edit_options", {}) if _ch_cfg else {}
                reddit_avatar = edit_options.get("reddit_avatar_path") or _ch_opts.get("reddit_avatar_path") or (_ch_cfg.get("reddit_avatar_path") if _ch_cfg else None)
                custom_username = edit_options.get("reddit_username") or _ch_opts.get("reddit_username") or (_ch_cfg.get("reddit_username") if _ch_cfg else None)

                if not reddit_avatar or not custom_username:
                    try:
                        grp = _CM().get_channel_group(channel_id)
                        if grp:
                            if not reddit_avatar:
                                reddit_avatar = grp.get("reddit_avatar_path")
                            if not custom_username:
                                custom_username = grp.get("reddit_username")
                    except Exception as grp_err:
                        print(f"[REDDIT-CARD] Grup ayarları okuma hatası: {grp_err}")

                # Avatar hala yoksa kanalın logo veya filigran yolunu avatar olarak kullan
                if not reddit_avatar:
                    reddit_avatar = (
                        edit_options.get("censor_logo_path")
                        or edit_options.get("watermark_path")
                        or _ch_opts.get("censor_logo_path")
                        or _ch_opts.get("watermark_path")
                        or (_ch_cfg.get("censor_logo_path") if _ch_cfg else None)
                        or (_ch_cfg.get("watermark_path") if _ch_cfg else None)
                    )

                if reddit_avatar:
                    cand_path = Path(reddit_avatar)
                    if not cand_path.is_absolute():
                        cand_path = Path(__file__).resolve().parent.parent / cand_path
                    if cand_path.exists():
                        reddit_avatar = str(cand_path)
                    else:
                        reddit_avatar = None

                channel_lang = (_ch_cfg.get("language") if _ch_cfg else "tr") or "tr"

                ch_name = (_ch_cfg.get("name") if _ch_cfg else "") or channel_id
                import unicodedata
                tr_map = {
                    ord('ı'): 'i', ord('İ'): 'I',
                    ord('ğ'): 'g', ord('Ğ'): 'G',
                    ord('ü'): 'u', ord('Ü'): 'U',
                    ord('ş'): 's', ord('Ş'): 'S',
                    ord('ö'): 'o', ord('Ö'): 'O',
                    ord('ç'): 'c', ord('Ç'): 'C'
                }
                translated_name = ch_name.translate(tr_map)
                clean_name = unicodedata.normalize('NFKD', translated_name).encode('ASCII', 'ignore').decode('utf-8')
                clean_handle = "".join(w.capitalize() for w in clean_name.split() if w)
                clean_handle = "".join(c for c in clean_handle if c.isalnum() or c == "_")
                if not clean_handle:
                    clean_handle = channel_id

                # Subreddit ismi:
                # Kullanıcı kanal/grup ayarlarında açıkça reddit_subreddit belirtmemişse HER ZAMAN kanalın adı kullanılmalıdır.
                # AI senaryosundan dönen generic isimler (r/AITAH, r/AskReddit vb.) kanal adını ASLA ezmemelidir!
                custom_sub = edit_options.get("reddit_subreddit") or _ch_opts.get("reddit_subreddit")
                if custom_sub and str(custom_sub).strip():
                    final_subreddit = custom_sub if str(custom_sub).startswith("r/") else f"r/{custom_sub}"
                else:
                    final_subreddit = f"r/{clean_handle}"

                # Yazar / Kullanıcı ismi (u/...):
                # Özel kullanıcı adı ayarlanmışsa onu kullan, ayarlanmamışsa kanalın adını (u/{clean_handle}) kullan.
                if custom_username and str(custom_username).strip():
                    final_author = custom_username if str(custom_username).startswith("u/") else f"u/{custom_username}"
                else:
                    final_author = f"u/{clean_handle}"

                print(f"[REDDIT-CARD] Kart parametreleri: Subreddit={final_subreddit}, Author={final_author}, Avatar={reddit_avatar}, Dil={channel_lang}")

                # Kart boyutunu videonun tam genişliğine göre üret
                generate_reddit_card(
                    question=question_text,
                    output_path=reddit_card_path,
                    subreddit=final_subreddit,
                    author=final_author,
                    avatar_path=reddit_avatar,
                    language=channel_lang,
                    upvotes=upvotes_val,
                    canvas_w=editor_cfg_W,
                    canvas_h=editor_cfg_H
                )

                asmr_bg_file = str(work_dir / "asmr_background.mp4")
                prepare_asmr_background(
                    target_duration=real_duration + 10.0,
                    output_path=asmr_bg_file,
                    width=editor_cfg_W,
                    height=editor_cfg_H,
                    fps=24
                )

                # Her sahne için ASMR bölümünü kırp; sahne sürelerini boundaries'den hesapla
                cur_time = 0.0
                for target in scene_targets:
                    idx = target["index"]
                    # Scene süresini boundaries'den doğru hesapla (her sahne birden fazla TTS alt-cümlesi içerebilir)
                    dur = 0.0
                    if scenes and idx < len(scenes):
                        matching_durs = [b.get("duration", 0.0) for b in boundaries if b.get("scene_idx") == idx]
                        if matching_durs:
                            dur = sum(matching_durs)
                        elif len(boundaries) == len(scenes):
                            dur = boundaries[idx].get("duration", 0.0)
                    elif idx < len(boundaries) and len(boundaries) == len(scene_targets):
                        dur = boundaries[idx].get("duration", 0.0)

                    if dur <= 0.5:
                        dur = real_duration / max(len(scene_targets), 1)

                    if idx == len(scene_targets) - 1 and (cur_time + dur) < real_duration:
                        dur = real_duration - cur_time

                    dest_vid = str(work_dir / f"scene_{idx}.mp4")

                    if idx == 0 and reddit_card_path and os.path.exists(reddit_card_path):
                        # Sahne 0: ASMR arka plan + Reddit Soru Kartı (-loop 1 ile kart tüm sahne boyunca gösterilir)
                        cmd = [
                            "ffmpeg", "-y",
                            "-ss", f"{cur_time:.3f}",
                            "-i", asmr_bg_file,
                            "-loop", "1",
                            "-i", reddit_card_path,
                            "-t", f"{dur:.3f}",
                            "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
                            "-map", "[v]",
                            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                            "-s", f"{editor_cfg_W}x{editor_cfg_H}",
                            dest_vid
                        ]
                        result = subprocess.run(cmd, capture_output=True)
                        if result.returncode != 0 or not os.path.exists(dest_vid) or os.path.getsize(dest_vid) < 5000:
                            # Fallback: kart ölçekleme ile tekrar dene
                            cmd_scale = [
                                "ffmpeg", "-y",
                                "-ss", f"{cur_time:.3f}",
                                "-i", asmr_bg_file,
                                "-loop", "1",
                                "-i", reddit_card_path,
                                "-t", f"{dur:.3f}",
                                "-filter_complex", f"[1:v]scale={editor_cfg_W}:{editor_cfg_H}[card];[0:v][card]overlay=0:0[v]",
                                "-map", "[v]",
                                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                                "-s", f"{editor_cfg_W}x{editor_cfg_H}",
                                dest_vid
                            ]
                            subprocess.run(cmd_scale, capture_output=True)
                    else:
                        # Diğer sahneler: saf ASMR arka plan
                        cmd = [
                            "ffmpeg", "-y",
                            "-ss", f"{cur_time:.3f}",
                            "-i", asmr_bg_file,
                            "-t", f"{dur:.3f}",
                            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                            "-s", f"{editor_cfg_W}x{editor_cfg_H}",
                            dest_vid
                        ]
                        subprocess.run(cmd, capture_output=True)

                    if os.path.exists(dest_vid) and os.path.getsize(dest_vid) > 5000:
                        scene_images[idx] = dest_vid
                        print(f"[REDDIT-VIDEO] Sahne {idx} ASMR videosu hazır: {dest_vid} ({dur:.2f}s)")
                    else:
                        print(f"[REDDIT-VIDEO] Sahne {idx} ASMR videosu üretilemedi ({dest_vid})!")
                    cur_time += dur

                print(f"[REDDIT-VIDEO] {len(scene_targets)} sahnelik Reddit ASMR video dizilimi hazırlandı. Toplam süre: {real_duration:.1f}s")
            except Exception as e:
                import traceback
                print(f"[REDDIT-VIDEO] ASMR video hazırlama hatası: {e}\n{traceback.format_exc()}")

        aviation_used_media = set()

        for target in scene_targets:
            idx = target["index"]
            dest_img = str(work_dir / f"scene_{idx}.jpg")
            dest_vid = str(work_dir / f"scene_{idx}.mp4")
            image_obtained = False

            # Check if image or video already exists (recompose mode or reddit ASMR)
            if scene_images.get(idx) and os.path.exists(scene_images[idx]):
                image_obtained = True
            elif os.path.exists(dest_img):
                scene_images[idx] = dest_img
                image_obtained = True
                print(f"[RECOMPOSE] Sahne {idx} için mevcut görsel kullanılıyor: {dest_img}")
            elif os.path.exists(dest_vid):
                scene_images[idx] = dest_vid
                image_obtained = True
                print(f"[RECOMPOSE] Sahne {idx} için mevcut video kullanılıyor: {dest_vid}")

            # Gemini Web / custom images logic
            if custom_images and str(idx) in custom_images:
                img_data = custom_images[str(idx)]
                if img_data:
                    if img_data.startswith("data:image"):
                        try:
                            import base64
                            from io import BytesIO

                            header, encoded = img_data.split(",", 1)
                            data = base64.b64decode(encoded)

                            im = Image.open(BytesIO(data)).convert("RGB")
                            src_w, src_h = im.size
                            
                            # Shorts: dikey (1080x1920), Normal: yatay (1920x1080)
                            target_w = editor_cfg_W   # 1080 veya 1920
                            target_h = editor_cfg_H   # 1920 veya 1080
                            
                            src_ratio = src_w / src_h
                            tgt_ratio = target_w / target_h
                            
                            # Akıllı fill-crop: önce scale, sonra ortala
                            if src_ratio > tgt_ratio:
                                # Kaynak daha yatay: yüksekliğe göre ölçekle
                                new_h = target_h
                                new_w = int(new_h * src_ratio)
                            else:
                                # Kaynak daha dikey: genişliğe göre ölçekle
                                new_w = target_w
                                new_h = int(new_w / src_ratio)
                            
                            im = im.resize((new_w, new_h), Image.LANCZOS)
                            left = (new_w - target_w) // 2
                            top  = (new_h - target_h) // 2
                            im = im.crop((left, top, left + target_w, top + target_h))
                            im.save(dest_img, "JPEG", quality=95)
                            
                            scene_images[idx] = dest_img   # ← KRİTİK: bu eksikti
                            image_obtained = True
                            print(f"[GEMINI-WEB] Base64 görsel kaydedildi (Sahne {idx}): {dest_img} [{target_w}x{target_h}]")

                            if not shorts_mode:
                                remove_gemini_watermark(dest_img)
                        except Exception as e:
                            print(f"[GEMINI-WEB] Base64 decode hatası (Sahne {idx}): {e}")
                    elif img_data.startswith("http"):
                        try:
                            if self.nasa.download_image(img_data, dest_img):
                                # Ayrıca boyutu kırpıp 9:16 / 16:9 yapalım
                                try:
                                    im = Image.open(dest_img).convert("RGB")
                                    src_w, src_h = im.size
                                    target_w = editor_cfg_W
                                    target_h = editor_cfg_H
                                    src_ratio = src_w / src_h
                                    tgt_ratio = target_w / target_h
                                    
                                    if src_ratio > tgt_ratio:
                                        new_h = target_h
                                        new_w = int(new_h * src_ratio)
                                    else:
                                        new_w = target_w
                                        new_h = int(new_w / src_ratio)
                                    
                                    im = im.resize((new_w, new_h), Image.LANCZOS)
                                    left = (new_w - target_w) // 2
                                    top  = (new_h - target_h) // 2
                                    im = im.crop((left, top, left + target_w, top + target_h))
                                    im.save(dest_img, "JPEG", quality=95)
                                except Exception as resize_err:
                                    print(f"[GEMINI-WEB] URL görsel boyutlandırma hatası: {resize_err}")

                                scene_images[idx] = dest_img
                                image_obtained = True
                                print(f"[GEMINI-WEB] URL görsel indirildi ve kırpıldı (Sahne {idx}): {dest_img}")
                                if not shorts_mode:
                                    remove_gemini_watermark(dest_img)
                        except Exception as e:
                            print(f"[GEMINI-WEB] URL indirme hatası (Sahne {idx}): {e}")
                    elif isinstance(img_data, str) and (os.path.exists(img_data) or img_data.startswith("/") or img_data.startswith("file://")):
                        # Yerel görsel veya video yolu kullanımı
                        try:
                            file_path = img_data
                            if file_path.startswith("file://"):
                                file_path = file_path[7:]
                                
                            if file_path.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
                                import shutil
                                if os.path.exists(file_path):
                                    if file_path != dest_vid:
                                        shutil.copy2(file_path, dest_vid)
                                    scene_images[idx] = dest_vid
                                    image_obtained = True
                                    print(f"[PRE-RESEARCH] Önceden doğrulanmış video klip bağlandı (Sahne {idx}): {dest_vid}")
                            else:
                                im = Image.open(file_path).convert("RGB")
                                src_w, src_h = im.size
                                target_w = editor_cfg_W
                                target_h = editor_cfg_H
                                
                                src_ratio = src_w / src_h
                                tgt_ratio = target_w / target_h
                                
                                if src_ratio > tgt_ratio:
                                    new_h = target_h
                                    new_w = int(new_h * src_ratio)
                                else:
                                    new_w = target_w
                                    new_h = int(new_w / src_ratio)
                                    
                                im = im.resize((new_w, new_h), Image.LANCZOS)
                                left = (new_w - target_w) // 2
                                top  = (new_h - target_h) // 2
                                im = im.crop((left, top, left + target_w, top + target_h))
                                im.save(dest_img, "JPEG", quality=95)
                                
                                scene_images[idx] = dest_img
                                image_obtained = True
                                print(f"[PRE-RESEARCH] Önceden doğrulanmış görsel bağlandı (Sahne {idx}): {dest_img}")
                        except Exception as e:
                            print(f"[PRE-RESEARCH] Yerel medya yükleme hatası (Sahne {idx}): {e}")

            # Space/science channels query NASA first
            if not image_obtained and use_nasa:
                nasa_term = target.get("nasa_keywords", "").strip()
                if not nasa_term and keywords:
                    nasa_term = keywords[idx % len(keywords)]
                if nasa_term:
                    # 1. Öncelikle NASA Video araması yap
                    try:
                        dest_vid = str(work_dir / f"scene_{idx}.mp4")
                        print(f"[NASA Video] Sahne {idx} için video aranıyor: '{nasa_term}'...")
                        vid_urls = self.nasa.search_videos(nasa_term, count=3)
                        for v_url in vid_urls:
                            if self.nasa.download_image(v_url, dest_vid):
                                print(f"[NASA Video] Sahne {idx} için video başarıyla indirildi: {v_url}")
                                scene_images[idx] = dest_vid
                                image_obtained = True
                                break
                    except Exception as e:
                        print(f"[NASA Video] Sahne {idx} video arama/indirme hatası: {e}")

                    # 2. Eğer video bulunamadıysa, NASA Görsel araması yap
                    if not image_obtained:
                        try:
                            print(f"[NASA Görsel] Sahne {idx} için görsel aranıyor: '{nasa_term}'...")
                            urls = self.nasa.search_images(nasa_term, count=3)
                            for url in urls:
                                if self.nasa.download_image(url, dest_img):
                                    print(f"[NASA Görsel] Sahne {idx} için görsel başarıyla indirildi: {url}")
                                    scene_images[idx] = dest_img
                                    image_obtained = True
                                    break
                        except Exception as e:
                            print(f"[NASA Görsel] Sahne {idx} görsel arama/indirme hatası: {e}")

            # Havacılık kanalları için telifsiz gerçek video ve olay arşivi (Pixabay Video + Wikimedia Commons)
            if not image_obtained and topic_category == "aviation":
                try:
                    try:
                        from aviation_media_fetcher import get_aviation_scene_media
                    except ImportError:
                        from src.aviation_media_fetcher import get_aviation_scene_media

                    topic_title = script.get("topic") or script.get("title") or ""
                    # Sahne süresi hesabı
                    scene_dur = 5.0
                    if scenes and idx < len(scenes):
                        matching_durs = [b.get("duration", 0.0) for b in boundaries if b.get("scene_idx") == idx]
                        if matching_durs:
                            scene_dur = sum(matching_durs)
                        elif len(boundaries) == len(scenes):
                            scene_dur = boundaries[idx].get("duration", 5.0)
                    elif boundaries and idx < len(boundaries):
                        scene_dur = boundaries[idx].get("duration", 5.0)

                    media_path = get_aviation_scene_media(
                        scene_idx=idx,
                        total_scenes=len(scene_targets),
                        topic=topic_title,
                        scene_data=target,
                        work_dir=work_dir,
                        target_w=editor_cfg_W,
                        target_h=editor_cfg_H,
                        target_dur=max(3.0, scene_dur),
                        session_used=aviation_used_media
                    )
                    if media_path and os.path.exists(media_path):
                        scene_images[idx] = media_path
                        image_obtained = True
                        print(f"[AVIATION-MEDIA] Sahne {idx} için telifsiz medya bağlandı: {media_path}")
                except Exception as av_err:
                    print(f"[AVIATION-MEDIA] Medya arama hatası (Sahne {idx}): {av_err}")

            # Crayon Combat / Askeri teknoloji: Vektörel Blueprint ve Çöp Adam sahne kartı motoru
            if not image_obtained and topic_category in ("crayon_combat", "military", "military_tech", "crayon_capital"):
                try:
                    try:
                        from crayon_combat_engine import render_blueprint_spec_sheet
                    except ImportError:
                        from src.crayon_combat_engine import render_blueprint_spec_sheet

                    vehicle_name = script.get("vehicle_name") or script.get("title") or "MILITARY SPEC"
                    nickname = script.get("vehicle_nickname") or "TACTICAL HARDWARE"
                    specs = script.get("key_specs")
                    char_role = target.get("active_character") or target.get("character") or "DEFENSE_CEO"
                    speech = target.get("character_dialogue") or target.get("character_quote") or target.get("narration") or ""
                    speech_short = speech[:95] + ("..." if len(speech) > 95 else "")

                    spec_img = render_blueprint_spec_sheet(
                        vehicle_name=vehicle_name,
                        nickname=nickname,
                        specs=specs,
                        stickman_role=char_role,
                        speech_text=speech_short,
                        output_path=dest_img
                    )
                    if spec_img and os.path.exists(spec_img):
                        scene_images[idx] = spec_img
                        image_obtained = True
                        print(f"[CRAYON-COMBAT] Sahne {idx} için taktik blueprint ve çöp adam üretildi: {dest_img}")
                except Exception as cc_err:
                    print(f"[CRAYON-COMBAT] Sahne {idx} blueprint üretim hatası: {cc_err}")

            # Telifsiz Gerçek Video ve Fotoğraf Çekim Motoru (Seyahat, Basketbol ve Gerçek B-Roll İsteyen Kanallar)
            is_real_footage_category = topic_category in (
                "travel", "gezi", "letstravel", "letstraveii",
                "basketball_analysis", "basketball", "sports", "nba", "thebasketballshows"
            )
            if not image_obtained and is_real_footage_category:
                try:
                    try:
                        from real_media_fetcher import get_real_scene_media
                    except ImportError:
                        from src.real_media_fetcher import get_real_scene_media

                    topic_title = script.get("topic") or script.get("title") or ""
                    scene_dur = 5.0
                    if scenes and idx < len(scenes):
                        matching_durs = [b.get("duration", 0.0) for b in boundaries if b.get("scene_idx") == idx]
                        if matching_durs:
                            scene_dur = sum(matching_durs)
                        elif len(boundaries) == len(scenes):
                            scene_dur = boundaries[idx].get("duration", 5.0)
                    elif boundaries and idx < len(boundaries):
                        scene_dur = boundaries[idx].get("duration", 5.0)

                    real_media_path = get_real_scene_media(
                        category=topic_category,
                        scene_idx=idx,
                        total_scenes=len(scene_targets),
                        topic=topic_title,
                        scene_data=target,
                        work_dir=work_dir,
                        target_w=editor_cfg_W,
                        target_h=editor_cfg_H,
                        target_dur=max(3.0, scene_dur),
                        session_used=aviation_used_media
                    )
                    if real_media_path and os.path.exists(real_media_path):
                        scene_images[idx] = real_media_path
                        image_obtained = True
                        print(f"[REAL-MEDIA] Sahne {idx} için telifsiz gerçek medya bağlandı: {real_media_path}")
                except Exception as rm_err:
                    print(f"[REAL-MEDIA] Gerçek medya arama hatası (Sahne {idx}): {rm_err}")

            # Fallback to Stable Diffusion — Reddit, Crayon Combat, Seyahat ve Basketbol kategorisinde ASLA SD üretimi yapma
            if not image_obtained and not is_reddit and topic_category not in (
                "crayon_combat", "military", "military_tech",
                "travel", "gezi", "letstravel", "letstraveii",
                "basketball_analysis", "basketball", "sports", "nba", "thebasketballshows"
            ):
                prompt = target.get("image_prompt", "").strip()
                if not prompt:
                    prompt = keywords[0] if keywords else "space science photography"
                style_prompt = script.get("style_prompt", "")
                
                try:
                    from image_generator import LocalImageGenerator
                except ImportError:
                    from src.image_generator import LocalImageGenerator
                
                try:
                    img_gen = LocalImageGenerator.get_instance()
                    scene_seed = video_seed + idx
                    print(f"[LOCAL-SD] Sahne {idx} için görsel üretiliyor: '{prompt[:60]}' (Seed: {scene_seed})...")
                    custom_neg = ""
                    if use_nasa:
                        custom_neg = "retro, cartoon, drawing, sketch, illustration, digital painting, line art, anime, retro visuals, lowres, ugly, deformed"
                    pil_img = img_gen.generate(
                        prompt=prompt,
                        style_prompt=style_prompt,
                        negative_prompt=custom_neg,
                        seed=scene_seed,
                        width=editor_cfg_W,
                        height=editor_cfg_H,
                        steps=20
                    )
                    pil_img.save(dest_img)
                    scene_images[idx] = dest_img
                    image_obtained = True
                except Exception as e:
                    print(f"[LOCAL-SD] Görsel üretim hatası (Sahne {idx}): {e}")

            # Last resort fallback: NASA APOD
            if not image_obtained and use_nasa:
                try:
                    print(f"[FALLBACK] Sahne {idx} için APOD görseli deneniyor...")
                    apod = self.nasa.get_apod()
                    apod_url = apod.get("url", "")
                    if apod_url and "jpg" in apod_url.lower():
                        if self.nasa.download_image(apod_url, dest_img):
                            scene_images[idx] = dest_img
                            image_obtained = True
                except Exception as e:
                    print(f"[FALLBACK] APOD indirme hatası: {e}")

            if not image_obtained:
                print(f"[WARNING] Sahne {idx} için görsel elde edilemedi, boş bırakılacak.")
                scene_images[idx] = ""

            img_path_check = scene_images.get(idx, "")
            if image_obtained and img_path_check and os.path.exists(img_path_check):
                if censor_faces_enabled:
                    self._censor_faces(img_path_check)
                self._censor_custom_areas(img_path_check)


        # Check and apply cascading visual fallbacks
        def create_starfield_fallback(w: int, h: int, out_p: str):
            try:
                import numpy as np
                import cv2
                import random
                
                img = np.zeros((h, w, 3), dtype=np.uint8)
                if topic_category == "aviation":
                    # Draw a nice twilight sky gradient: Deep blue to light sky blue
                    for y in range(h):
                        r = int(10 + (30 - 10) * (y / h))
                        g = int(25 + (80 - 25) * (y / h))
                        b = int(45 + (150 - 45) * (y / h))
                        img[y, :] = [b, g, r] # BGR in OpenCV
                    # Draw some stylized clouds
                    for _ in range(8):
                        cx = random.randint(0, w)
                        cy = random.randint(int(h * 0.3), int(h * 0.8))
                        radius = random.randint(30, 80)
                        cv2.circle(img, (cx, cy), radius, (230, 220, 210), -1)
                else:
                    # Draw stars
                    img[:] = [25, 5, 5] # BGR twilight dark space
                    star_rand = random.Random(42)
                    num_stars = int((w * h) * 0.0002)
                    for _ in range(num_stars):
                        x = star_rand.randint(0, w - 1)
                        y = star_rand.randint(0, h - 1)
                        brightness = star_rand.randint(100, 255)
                        size = star_rand.choice([1, 1, 2])
                        cv2.circle(img, (x, y), size, (brightness, brightness, brightness), -1)
                
                cv2.imwrite(out_p, img)
                print(f"[FALLBACK-GEN] Created fallback image using OpenCV/BGR at {out_p}")
            except Exception as e:
                print(f"[FALLBACK-GEN] Fallback creation failed: {e}")

        last_valid = None
        first_valid = None
        for idx in range(len(scene_targets)):
            if scene_images.get(idx) and os.path.exists(scene_images[idx]):
                first_valid = scene_images[idx]
                break

        if not first_valid or not os.path.exists(first_valid):
            fallback_path = str(work_dir / "starfield_fallback.jpg")
            create_starfield_fallback(editor_cfg_W, editor_cfg_H, fallback_path)
            if os.path.exists(fallback_path):
                first_valid = fallback_path
            else:
                try:
                    fallback_img = Image.new("RGB", (editor_cfg_W, editor_cfg_H), (10, 20, 30))
                    fallback_img.save(fallback_path, "JPEG")
                    first_valid = fallback_path
                except Exception:
                    pass

        for idx in range(len(scene_targets)):
            img_p = scene_images.get(idx)
            if img_p and os.path.exists(img_p):
                last_valid = img_p
            else:
                target_fallback = last_valid if (last_valid and os.path.exists(last_valid)) else first_valid
                dest_fallback = str(work_dir / f"scene_{idx}_fallback.jpg")
                try:
                    import shutil
                    if target_fallback and os.path.exists(target_fallback):
                        shutil.copy(target_fallback, dest_fallback)
                        scene_images[idx] = dest_fallback
                        print(f"[FALLBACK] Sahne {idx} için yedek görsel kullanıldı: {target_fallback} -> {dest_fallback}")
                    else:
                        print(f"[FALLBACK] UYARI: Hedef fallback bulunamadı! Sahne {idx} boş geçilebilir.")
                except Exception as e:
                    if target_fallback:
                        scene_images[idx] = target_fallback
                    print(f"[FALLBACK] Sahne {idx} kopyalama hatası: {e}")

        # Map boundaries to scene images
        if scenes:
            scene_word_ranges = _scene_word_ranges(scenes)
            boundary_mapping = []
            current_word_offset = 0
            for b in boundaries:
                if "scene_idx" in b and isinstance(b["scene_idx"], int) and b["scene_idx"] < len(scenes):
                    boundary_mapping.append(b["scene_idx"])
                    current_word_offset += len(str(b.get("text") or "").split())
                    continue
                word_count = len(str(b.get("text") or "").split())
                if not word_count:
                    boundary_mapping.append(boundary_mapping[-1] if boundary_mapping else 0)
                    continue
                boundary_start = current_word_offset
                boundary_end = current_word_offset + word_count
                scene_overlaps = [
                    (max(0, min(boundary_end, scene_end) - max(boundary_start, scene_start)), scene_idx)
                    for scene_idx, (scene_start, scene_end) in enumerate(scene_word_ranges)
                ]
                best_scene = max(scene_overlaps, default=(0, 0))[1]
                boundary_mapping.append(best_scene)
                current_word_offset = boundary_end

        # Check if Local I2V (Image-to-Video) module is enabled
        enable_i2v_val = edit_options.get("enable_i2v", False)
        if isinstance(enable_i2v_val, str):
            enable_i2v_enabled = enable_i2v_val.lower() in ("true", "1", "yes")
        else:
            enable_i2v_enabled = bool(enable_i2v_val)

        i2v_quality = edit_options.get("i2v_model_quality", "distilled_q4") or "distilled_q4"
        try:
            i2v_fps_mult = int(edit_options.get("i2v_fps_multiplier", 4) or 4)
        except (ValueError, TypeError):
            i2v_fps_mult = 4

        W = 1080 if (shorts_mode or is_reddit) else 1920
        H = 1920 if (shorts_mode or is_reddit) else 1080
        source_scene_images = dict(scene_images)

        if enable_i2v_enabled:
            print(f"[I2V-ANIMATOR] Görsel Hareketlendirme (Yerel I2V Modülü) Aktif.")
            try:
                try:
                    from animator_service import AnimatorService
                except ImportError:
                    from src.animator_service import AnimatorService

                animator = AnimatorService.get_instance()
                valid_imgs = []
                scene_durations = []
                scene_prompts = []

                for target in scene_targets:
                    idx = target["index"]
                    img_p = scene_images.get(idx, "")
                    valid_imgs.append(img_p)

                    prompt_txt = target.get("narration") or target.get("image_prompt") or target.get("nasa_keywords") or (keywords[idx % len(keywords)] if keywords else "")
                    scene_prompts.append(prompt_txt)

                    dur = 0.0
                    if scenes:
                        for b_idx, b in enumerate(boundaries):
                            if b_idx < len(boundary_mapping) and boundary_mapping[b_idx] == idx:
                                dur += b.get("duration", 0.0)
                    else:
                        dur = boundaries[idx]["duration"] if (boundaries and idx < len(boundaries)) else 5.0

                    if dur <= 0.2:
                        dur = 5.0
                    scene_durations.append(dur)

                exec_id = edit_options.get("exec_id")

                animated_paths = animator.animate_batch(
                    image_paths=valid_imgs,
                    output_dir=str(work_dir),
                    durations=scene_durations,
                    prompts=scene_prompts,
                    exec_id=exec_id,
                    model_quality=i2v_quality,
                    fps_multiplier=i2v_fps_mult,
                    width=W,
                    height=H,
                )

                for target_idx, target in enumerate(scene_targets):
                    idx = target["index"]
                    if target_idx < len(animated_paths):
                        anim_p = animated_paths[target_idx]
                        if anim_p and os.path.exists(anim_p) and anim_p.endswith(".mp4"):
                            scene_images[idx] = anim_p
                            print(f"[I2V-ANIMATOR] Sahne {idx} ({scene_durations[target_idx]:.1f}s) hareketlendirildi → {anim_p}")
            except Exception as i2v_err:
                print(f"[I2V-ANIMATOR] Hareketlendirme hatası, durağan görseller kullanılacak: {i2v_err}")
        else:
            print("[I2V-ANIMATOR] I2V Pasif: Klasik durağan görseller kullanılıyor.")

        # Re-assign boundary image paths after optional I2V transformation
        if scenes:
            for idx, b in enumerate(boundaries):
                mapped_scene_idx = boundary_mapping[idx]
                b["image_path"] = scene_images.get(mapped_scene_idx, "")
        else:
            for idx, b in enumerate(boundaries):
                b["image_path"] = scene_images.get(idx, "")

        try:
            try:
                from visual_content_guard import visual_guard
            except ImportError:
                from src.visual_content_guard import visual_guard
            if is_reddit:
                print("[VISUAL-QA] Reddit hikâyelerinde ASMR arka planı tasarım gereği anlatımdan bağımsız; sahne semantik kontrolü uygulanmadı.")
            elif visual_guard.semantic_model_available:
                for target in scene_targets:
                    idx = target["index"]
                    asset_path = scene_images.get(idx, "")
                    if not asset_path or not os.path.exists(asset_path):
                        raise RuntimeError(f"Görsel-ses uyum kontrolü sahne {idx + 1}'de görsel bulamadı.")
                    accepted, score, reason = visual_guard.verify_scene_asset(
                        asset_path,
                        target.get("narration") or target.get("image_prompt", ""),
                        topic_category,
                        script.get("topic") or title,
                    )
                    if not accepted:
                        source_path = source_scene_images.get(idx, "")
                        if source_path and source_path != asset_path and os.path.exists(source_path):
                            source_accepted, _, source_reason = visual_guard.verify_scene_asset(
                                source_path,
                                target.get("narration") or target.get("image_prompt", ""),
                                topic_category,
                                script.get("topic") or title,
                            )
                            if source_accepted:
                                scene_images[idx] = source_path
                                print(
                                    f"[VISUAL-QA] Hareketlendirilmiş sahne {idx + 1} anlatımla uyuşmadı; "
                                    f"doğrulanmış kaynak görsele dönüldü ({source_reason})."
                                )
                                continue
                        raise RuntimeError(
                            f"Görsel-ses uyum kontrolü sahne {idx + 1}'i reddetti "
                            f"(skor {score:.2f}): {reason}. Görsel yeniden seçilmeden video oluşturulmadı."
                        )
            else:
                raise RuntimeError(
                    "Ses-görsel uyumu doğrulanamadı: CLIP modeli yüklenemedi. "
                    "Görsel uyum kontrolü olmadan video üretilmedi; internet bağlantısını ve "
                    "torch/transformers kurulumunu kontrol edip yeniden deneyin."
                )
        except RuntimeError:
            raise
        except Exception as visual_qc_error:
            raise RuntimeError(f"Son ses-görsel doğrulaması başarısız oldu: {visual_qc_error}") from visual_qc_error

        images = [scene_images.get(idx, "") for idx in range(len(scene_targets))]

        # 5) Segmentleri oluştur
        segments = self._build_segments(
            boundaries, real_duration, True, images, scene_images,
            work_dir, keywords, W, H
        )

        print(f"[SUBS] {len(segments)} segment, süre={real_duration:.1f}s")
        for idx, seg in enumerate(segments):
            print(f"  [{idx}] ({seg['duration']:.2f}s) {seg['text'][:50]}…")

        # 6) Yeni iki aşamalı pipeline: caption gruplama + base video + ASS burn
        try:
            from video_editor import EditConfig, VideoEditor
        except ImportError:
            from src.video_editor import EditConfig, VideoEditor

        # Reddit için altyazı ön ayarları: tiktok ve word-highlight
        if is_reddit:
            chosen_sub_preset = edit_options.get("subtitle_preset")
            if not chosen_sub_preset or chosen_sub_preset == "bold":
                chosen_sub_preset = "tiktok"
            chosen_sub_anim = edit_options.get("subtitle_animation")
            if not chosen_sub_anim or chosen_sub_anim == "fade":
                chosen_sub_anim = "word-highlight"
        else:
            chosen_sub_preset = edit_options.get("subtitle_preset") or "bold"
            chosen_sub_anim = edit_options.get("subtitle_animation") or "fade"

        raw_bgm_vol = edit_options.get("bgm_volume")
        try:
            resolved_bgm_vol = float(raw_bgm_vol) if raw_bgm_vol not in (None, "") else (0.35 if is_reddit else 0.20)
        except (ValueError, TypeError):
            resolved_bgm_vol = 0.35 if is_reddit else 0.20

        resolved_bgm_path = self._resolve_reddit_bgm(is_reddit, script, edit_options, narration, title, work_dir=work_dir, duration=real_duration)
        if resolved_bgm_path and "bgm_timeline_mixed" in str(resolved_bgm_path):
            resolved_bgm_vol = 1.0

        edit_cfg = EditConfig(
            transition=edit_options.get("transition") or ("none" if is_reddit else transition),
            transition_dur=edit_options.get("transition_dur", 0.5),
            kenburns_intensity=edit_options.get("kenburns_intensity", 0.04),
            fps=24,
            width=W,
            height=H,
            shorts_mode=shorts_mode,
            bgm_path=resolved_bgm_path,
            bgm_volume=resolved_bgm_vol,
            watermark_path=edit_options.get("watermark_path"),
            watermark_text=edit_options.get("watermark_text"),
            watermark_position=edit_options.get("watermark_position", "top-right"),
            intro_clip_path=edit_options.get("intro_clip_path"),
            outro_clip_path=edit_options.get("outro_clip_path"),
            subtitle_preset=chosen_sub_preset,
            subtitle_animation=chosen_sub_anim,
            censor_logo_path=edit_options.get("censor_logo_path"),
            censor_faces=censor_faces_enabled,
            is_aviation=(topic_category == "aviation"),
            liveatc_path=liveatc_path,
            enable_i2v=enable_i2v_enabled,
            i2v_model_quality=i2v_quality,
            i2v_fps_multiplier=i2v_fps_mult,
        )

        video_path = str(work_dir / "final.mp4")

        # Remotion ile Render (edit_options'ta use_remotion True ise Remotion React motoru kullanılır)
        use_remotion_opt = edit_options.get("use_remotion", False)
        if isinstance(use_remotion_opt, str):
            use_remotion_enabled = use_remotion_opt.lower() in ("true", "1", "yes")
        else:
            use_remotion_enabled = bool(use_remotion_opt)

        rendered_with_remotion = False
        if is_reddit and use_remotion_enabled:
            try:
                try:
                    from remotion_renderer import is_remotion_available, render_reddit_video_remotion
                except ImportError:
                    from src.remotion_renderer import is_remotion_available, render_reddit_video_remotion

                if is_remotion_available():
                    print(f"[REDDIT-REMOTION] Remotion 1080x1920 React render başlatılıyor...")
                    q_text = script.get("question") or title
                    sub_text = final_subreddit if 'final_subreddit' in locals() else "r/AskReddit"
                    auth_text = final_author if 'final_author' in locals() else "u/StoryTeller"
                    up_text = upvotes_val if 'upvotes_val' in locals() else "38.4k"
                    bg_file = asmr_bg_file if ('asmr_bg_file' in locals() and os.path.exists(asmr_bg_file)) else None
                    card_dur_s = 6.0
                    if boundaries and len(boundaries) > 0:
                        card_dur_s = min(max(boundaries[0].get("duration", 6.0), 3.0), 10.0)

                    rendered_with_remotion = render_reddit_video_remotion(
                        question=q_text,
                        subreddit=sub_text,
                        author=auth_text,
                        upvotes=up_text,
                        audio_path=audio_path,
                        bg_video_path=bg_file,
                        captions_data=boundaries,
                        output_path=video_path,
                        avatar_path=reddit_avatar if ('reddit_avatar' in locals() and reddit_avatar and os.path.exists(reddit_avatar)) else None,
                        bgm_path=self._resolve_reddit_bgm(is_reddit, script, edit_options, narration, title),
                        bgm_volume=resolved_bgm_vol,
                        fps=30,
                        card_duration_sec=card_dur_s,
                    )
            except Exception as r_err:
                print(f"[REDDIT-REMOTION] Remotion render hatası ({r_err}), standart video editörüne geçiliyor...")

        edit_log = {}
        if rendered_with_remotion:
            intro_clip = edit_options.get("intro_clip_path")
            outro_clip = edit_options.get("outro_clip_path")
            if intro_clip or outro_clip:
                try:
                    editor = VideoEditor(edit_cfg)
                    tmp_out = str(work_dir / "final_concat_remotion.mp4")
                    ok = editor.burner.concat_with_intro_outro(
                        intro_clip, video_path, outro_clip, tmp_out
                    )
                    if ok and os.path.exists(tmp_out):
                        shutil.move(tmp_out, video_path)
                except Exception as io_err:
                    print(f"[REDDIT-REMOTION] Intro/outro birleştirme hatası: {io_err}")

        if not rendered_with_remotion:
            editor = VideoEditor(edit_cfg)
            edit_log = editor.compose(
                segments=segments,
                audio_path=audio_path,
                output_path=video_path,
                work_dir=str(work_dir),
            )
            if not edit_log.get("success"):
                err = edit_log.get("error", "Bilinmeyen hata")
                raise RuntimeError(f"Video kompozisyon başarısız: {err}")

        # Auto-Editor post-processing if enabled
        auto_editor_val = edit_options.get("auto_editor", False)
        if isinstance(auto_editor_val, str):
            auto_editor_enabled = auto_editor_val.lower() in ("true", "1", "yes")
        else:
            auto_editor_enabled = bool(auto_editor_val)
            
        if auto_editor_enabled:
            print(f"[AUTO-EDITOR] Silence removal is enabled. Processing {video_path}...")
            project_root = Path(__file__).resolve().parent.parent
            auto_editor_bin = project_root / ".venv" / "bin" / "auto-editor"
            temp_video_path = str(work_dir / "final_cut.mp4")
            cmd = [
                str(auto_editor_bin),
                video_path,
                "--output",
                temp_video_path
            ]
            try:
                print(f"[AUTO-EDITOR] Running command: {' '.join(cmd)}")
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if res.returncode == 0 and os.path.exists(temp_video_path):
                    shutil.move(temp_video_path, video_path)
                    print("[AUTO-EDITOR] Silence removal completed successfully!")
                else:
                    print(f"[AUTO-EDITOR] Error running auto-editor: {res.stderr}")
            except Exception as ae_err:
                print(f"[AUTO-EDITOR] Failed to execute auto-editor: {ae_err}")

        # HyperFrames Kinetik Tipografi Hook (edit_options'ta aktifse videonun başına eklenir)
        enable_hf_hook = edit_options.get("enable_hyperframes_hook", False)
        if isinstance(enable_hf_hook, str):
            enable_hf_hook = enable_hf_hook.lower() in ("true", "1", "yes")
        else:
            enable_hf_hook = bool(enable_hf_hook)


        if enable_hf_hook:
            try:
                from hyperframes_renderer import is_hyperframes_available, render_kinetic_hook, prepend_hook_to_video
                if is_hyperframes_available():
                    print(f"[HYPERFRAMES] Kanal ayarı aktif: Kinetik hook üretiliyor ({title[:35]}...)...")
                    hook_badge = edit_options.get("hyperframes_hook_badge") or ("SHORTS" if shorts_mode else "YENİ VİDEO")
                    hook_out = work_dir / "hyperframes_hook.mp4"
                    sub_text = (narration.split(".")[0] if narration else desc[:70]).strip()
                    rendered_hook = render_kinetic_hook(
                        title=title,
                        subtitle=sub_text,
                        badge=hook_badge,
                        output_path=hook_out
                    )
                    if rendered_hook and rendered_hook.exists():
                        merged_target = work_dir / "final_with_hook.mp4"
                        if prepend_hook_to_video(rendered_hook, video_path, merged_target):
                            shutil.move(str(merged_target), video_path)
                            print("[HYPERFRAMES] Kinetik hook başarıyla ana videonun başına eklendi!")
            except Exception as hf_err:
                print(f"[HYPERFRAMES] Kinetik hook eklenirken hata oluştu (video korundu): {hf_err}")

        # 7) Metadata

        meta_extra = {
            "title": title,
            "description": desc,
            "tags": tags,
            "channel_id": channel_id,
            "shorts_mode": shorts_mode,
            "transition": transition,
            "resolution": f"{W}x{H}",
            "duration_sec": round(real_duration, 1),
            "segments": segments,
            "edit_options": edit_options,
            "edit_log": {
                "groups": edit_log.get("groups"),
                "captions": edit_log.get("captions"),
                "ass_path": edit_log.get("ass_path"),
                "base_path": edit_log.get("base_path"),
            }
        }
        # Var olan video_info.json varsa alanları koruyarak birleştir
        existing_vinfo = {}
        vinfo_target = work_dir / "video_info.json"
        if vinfo_target.exists():
            try:
                existing_vinfo = json.loads(vinfo_target.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing_vinfo.update(meta_extra)
        vinfo_target.write_text(
            json.dumps(existing_vinfo, ensure_ascii=False, indent=2)
        )

        return {
            "video_path": video_path,
            "title": title,
            "description": desc,
            "tags": tags,
            "shorts_mode": shorts_mode,
            "transition": transition,
            "work_dir": str(work_dir),
        }
