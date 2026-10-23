"""
video_editor.py
===============

İki aşamalı video kompozisyon motoru.

NEDEN İKİ AŞAMALI?
- Önce altyazısız base video üretilir (görsel sahneleri + ses).
- Sonra ffmpeg ile ASS altyazı, BGM, watermark, intro/outro eklenir.
- Bu ayrım, "caption değişince görsel değişiyor" sorununu kökten çözer:
  caption artık görselin parçası değil, ayrı bir video katmanı.
- Ayrıca ffmpeg çok daha hızlı subtitle/watermark overlay yapar (yeniden encode yok).

KATMANLAR (sırayla):
  1. intro_clip (opsiyonel) — başlangıç tanıtımı
  2. base video (görsel sahneleri + ana ses)
  3. outro_clip (opsiyonel) — kapanış
  4. BGM (opsiyonel) — arka plan müziği, sesin altına karışır
  5. Watermark (opsiyonel) — logo / kanal adı
  6. ASS altyazı — son katman (her zaman)

GEÇİŞ EFEKTLERİ:
  - Sadece görsel sahneler arasında (gerçek görsel değişimlerinde) uygulanır.
  - "none", "fade", "slide", "zoom", "kenburns"
  - "kenburns" → aynı görsel içinde subtle zoom (artık sahte geçiş yok)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from moviepy import (
    VideoClip, ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, VideoFileClip, CompositeAudioClip
)

SFX_DIR = Path(__file__).resolve().parent.parent / "config" / "assets" / "sfx"

def ensure_aviation_sfx():
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    sfx_sources = {
        "cabin_hum.mp3": "https://www.youtube.com/watch?v=Jm_t3C1GZ-4",
        "master_warning.mp3": "https://www.youtube.com/watch?v=71_kR0aU1Wk",
        "gpws_pullup.mp3": "https://www.youtube.com/watch?v=nsw51Z619uQ",
        "tire_screech.mp3": "https://www.youtube.com/watch?v=f0hN0V83lro",
        "sirens.mp3": "https://www.youtube.com/watch?v=1F2l4Cg1gW4"
    }
    project_root = Path(__file__).resolve().parent.parent
    yt_dlp_bin = project_root / ".venv" / "bin" / "yt-dlp"
    if not yt_dlp_bin.exists():
        yt_dlp_bin = "yt-dlp"
        
    for name, url in sfx_sources.items():
        out_file = SFX_DIR / name
        if not out_file.exists():
            print(f"[SFX-DOWNLOAD] Havacılık ses efekti indiriliyor: {name}...")
            cmd = [
                str(yt_dlp_bin),
                url,
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "5",
                "-o", str(SFX_DIR / name.replace(".mp3", ".%(ext)s"))
            ]
            try:
                import subprocess
                subprocess.run(cmd, capture_output=True, timeout=120)
                if out_file.exists():
                    print(f"[SFX-DOWNLOAD] Başarıyla indirildi: {name}")
            except Exception as e:
                print(f"[SFX-DOWNLOAD] İndirme hatası ({name}): {e}")


# ──────────────────────────────────────────
# Yapılandırma dataclass'ları
# ──────────────────────────────────────────

@dataclass
class VisualGroup:
    """
    Aynı görseli paylaşan ardışık caption'ların oluşturduğu sahne.
    """
    image_path: str
    duration: float            # toplam sahne süresi
    caption_text: str          # uzun caption (debug / ileride genişletme)
    captions: list = field(default_factory=list)
    emotion: str = "neutral"
    # [(text, start_in_group, end_in_group), ...] — saniye cinsinden, group içinde 0-based


@dataclass
class EditConfig:
    """Video edit ayarları."""
    transition: str = "fade"           # none | fade | slide | zoom | kenburns
    transition_dur: float = 0.5
    kenburns_intensity: float = 0.04   # 0.0 - 0.10 arası
    fps: int = 24
    width: int = 1920
    height: int = 1080
    shorts_mode: bool = False
    # Gelişmiş
    bgm_path: Optional[str] = None
    bgm_volume: float = 0.15           # 0.0 - 1.0
    watermark_path: Optional[str] = None
    watermark_text: Optional[str] = None
    watermark_position: str = "top-right"  # top-left|top-right|bottom-left|bottom-right
    intro_clip_path: Optional[str] = None
    outro_clip_path: Optional[str] = None
    # Subtitle
    subtitle_preset: str = "bold"
    subtitle_animation: str = "fade"
    censor_logo_path: Optional[str] = None
    censor_faces: bool = False
    is_aviation: bool = False
    liveatc_path: Optional[str] = None
    # Yerel I2V Animasyonu
    enable_i2v: bool = False
    i2v_model_quality: str = "distilled_q4"
    i2v_fps_multiplier: int = 4
    # Casper AI: YouTube Shorts Optimizasyonları (Batch 3)
    normalize_audio_loudness: bool = True  # EBU R128 (-14 LUFS) ses standardı
    hook_intro_effect: bool = True         # İlk 1.5s %105 -> %100 thumb-stop zoom-in

    def __post_init__(self):
        """
        Ayarlar settings_manager'dan string olarak gelir ("0.04", "0.5", "0.15").
        Matematiksel/format işlemlerinde sorun çıkarmaması için burada float'a çeviriyoruz.
        Boş string'leri default'a düşürüyoruz.
        """
        # Sayısal alanlar — string gelebilir
        def _to_float(v, default):
            if v is None or v == "":
                return default
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        self.transition_dur = _to_float(self.transition_dur, 0.5)
        self.kenburns_intensity = _to_float(self.kenburns_intensity, 0.04)
        self.bgm_volume = _to_float(self.bgm_volume, 0.15)
        self.fps = int(_to_float(self.fps, 24))
        self.width = int(_to_float(self.width, 1920))
        self.height = int(_to_float(self.height, 1080))

        # String alanlar — None/boş ise default
        if not self.transition:
            self.transition = "fade"
        if not self.watermark_position:
            self.watermark_position = "top-right"
        if not self.subtitle_preset:
            self.subtitle_preset = "bold"
        if not self.subtitle_animation:
            self.subtitle_animation = "fade"

        if isinstance(self.normalize_audio_loudness, str):
            self.normalize_audio_loudness = self.normalize_audio_loudness.lower() in ("true", "1", "yes")
        if isinstance(self.hook_intro_effect, str):
            self.hook_intro_effect = self.hook_intro_effect.lower() in ("true", "1", "yes")


# ──────────────────────────────────────────
# Caption gruplama
# ──────────────────────────────────────────

def group_captions_by_image(
    segments: list[dict],
    min_group_dur: float = 0.4,
) -> list[VisualGroup]:
    """
    Caption segmentlerini image_path'e göre gruplar.

    Kural: Ardışık, AYNI image_path'e sahip segmentler tek bir VisualGroup olur.
    Görsel değişimi olan yerlerde yeni grup başlar (geçiş efekti burada uygulanır).
    min_group_dur: çok kısa grupları komşusuyla birleştirir.
    """
    if not segments:
        return []

    # Önce: küçük grupları komşusuyla birleştir
    merged: list[dict] = []
    for seg in segments:
        if (
            merged
            and merged[-1]["image_path"] == seg["image_path"]
            and merged[-1]["duration"] < min_group_dur
        ):
            merged[-1]["text"] = merged[-1]["text"] + " " + seg["text"]
            merged[-1]["duration"] += seg["duration"]
        else:
            merged.append(dict(seg))

    # Şimdi: image_path'e göre grupla
    groups: list[VisualGroup] = []
    cur_img = None
    cur_captions: list[tuple[str, float, float]] = []
    cur_dur = 0.0
    cur_text_parts: list[str] = []
    cur_emotion = "neutral"

    def _flush():
        nonlocal cur_img, cur_captions, cur_dur, cur_text_parts, cur_emotion
        if cur_img is not None and cur_dur > 0:
            groups.append(VisualGroup(
                image_path=cur_img,
                duration=cur_dur,
                caption_text=" ".join(cur_text_parts).strip(),
                captions=list(cur_captions),
                emotion=cur_emotion
            ))
        cur_img = None
        cur_captions = []
        cur_dur = 0.0
        cur_text_parts = []
        cur_emotion = "neutral"

    for seg in merged:
        img = seg.get("image_path", "") or ""
        text = (seg.get("text") or "").strip()
        dur = float(seg.get("duration", 0.0))
        emo = seg.get("emotion", "neutral")
        if dur <= 0.01:
            continue
        if img != cur_img and cur_img is not None:
            _flush()
        if cur_img is None:
            cur_img = img
            cur_emotion = emo
        cur_captions.append((text, cur_dur, cur_dur + dur))
        cur_text_parts.append(text)
        cur_dur += dur
    _flush()

    return groups


def segments_to_caption_events(
    groups: list[VisualGroup],
) -> list[dict]:
    """
    VisualGroup listesini ASS için mutlak zamanlamaya çevirir.
    Dönüş: [{"text", "start", "end"}, ...]
    """
    events = []
    t = 0.0
    for g in groups:
        for txt, s_in, e_in in g.captions:
            if not txt:
                continue
            events.append({
                "text": txt,
                "start": t + s_in,
                "end": t + e_in,
            })
        t += g.duration
    return events


# ──────────────────────────────────────────
# Görsel hazırlama
# ──────────────────────────────────────────

class ImageScaler:
    """Görseli hedef boyuta fill-crop veya blurred-fit ile ölçekler."""

    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height

    def prepare(self, image_path: str) -> np.ndarray:
        try:
            img = Image.open(image_path).convert("RGB")
        except Exception:
            return np.full((self.H, self.W, 3), (5, 5, 30), dtype=np.uint8)

        # Eğer Shorts (dikey) ve resim Yatay (Landscape) ise, blurred-fit uygula
        if self.W < self.H and img.width > img.height:
            src_ratio = img.width / img.height
            tgt_ratio = self.W / self.H
            
            # 1. Arka plan: fill-crop + ağır bulanıklık (blur)
            if src_ratio > tgt_ratio:
                bg_h = self.H
                bg_w = int(bg_h * src_ratio)
            else:
                bg_w = self.W
                bg_h = int(bg_w / src_ratio)
                
            bg_img = img.resize((bg_w, bg_h), Image.LANCZOS)
            bg_left = (bg_w - self.W) // 2
            bg_top = (bg_h - self.H) // 2
            bg_img = bg_img.crop((bg_left, bg_top, bg_left + self.W, bg_top + self.H))
            bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=30))
            
            # 2. Ön plan: fit-width (genişliğe sığdır, boyu orantılı)
            fg_w = self.W
            fg_h = int(fg_w / src_ratio)
            fg_img = img.resize((fg_w, fg_h), Image.LANCZOS)
            
            # 3. Birleştir: ön planı dikeyde ortala
            fg_top = (self.H - fg_h) // 2
            bg_img.paste(fg_img, (0, fg_top))
            return np.array(bg_img)
            
        else:
            # Standart fill-crop
            src_ratio = img.width / img.height
            tgt_ratio = self.W / self.H
            if src_ratio > tgt_ratio:
                new_h = self.H
                new_w = int(new_h * src_ratio)
            else:
                new_w = self.W
                new_h = int(new_w / src_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - self.W) // 2
            top = (new_h - self.H) // 2
            img = img.crop((left, top, left + self.W, top + self.H))
            return np.array(img)


# ──────────────────────────────────────────
# Geçiş klipleri (görsel sahneleri arası)
# ──────────────────────────────────────────

_depth_estimator = None

def get_depth_estimator():
    global _depth_estimator
    if _depth_estimator is None:
        print("[PARALLAX] Loading Depth Estimation model (Intel/dpt-hybrid-midas)...")
        from transformers import pipeline
        import torch
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        _depth_estimator = pipeline("depth-estimation", model="Intel/dpt-hybrid-midas", device=device)
        print(f"[PARALLAX] Model loaded on device: {device}")
    return _depth_estimator


def _clip_parallax(
    frame: np.ndarray,
    duration: float,
    W: int = 1920,
    H: int = 1080,
    max_shift: float = 0.06,
) -> VideoClip:
    """
    SMOOTH PADDED-CROP PARALLAX — deformasyon yok, cisimler asla bozulmaz.

    ESKİ YAKLAŞIMIN SORUNU:
        cv2.remap her pikseli bağımsız kaydırıyordu. Depth estimation modeli
        uçak gibi uniform objelerin farklı bölgelerine farklı derinlik ataması
        yaptığı için gövdenin parçaları farklı hızlarda kayarak cisim deforme
        oluyordu (büzüşme/dağılma artefaktı).

    YENİ YAKLAŞIM:
        1. Görüntü padded boyuta scale edilir (marj + kenar payı).
        2. Her frame'de yalnızca integer crop offseti (x0, y0) değişir.
        3. Derinlik haritası SADECE hareket hızı için kullanılır, warp için DEĞİL.
        4. ease_in_out eğrisi → sinematik, doğal başlangıç/bitiş.
        5. WARP YOK → cisim asla deforme olmaz.
    """
    try:
        estimator = get_depth_estimator()
        pil_img = Image.fromarray(frame)

        # Derinlik tahmini — yalnızca ortalama değer hesabı için
        result = estimator(pil_img)
        depth_pil = result["depth"].resize((W, H), Image.BILINEAR)
        depth_map = np.array(depth_pil).astype(np.float32)
        d_min, d_max = depth_map.min(), depth_map.max()
        if d_max > d_min:
            depth_norm = (depth_map - d_min) / (d_max - d_min)
        else:
            depth_norm = np.zeros_like(depth_map)

    except Exception as e:
        print(f"[PARALLAX] Hata oluştu, Ken Burns efektine geri dönülüyor: {e}")
        return _clip_kenburns(frame, duration, W=W, H=H)

    # Kayma bütçesi (piksel)
    total_px_x = int(max_shift * W)
    total_px_y = int(max_shift * H)

    # Padded boyut — her yöne crop payı kadar ekstra kenar
    pad_x = total_px_x + 4
    pad_y = total_px_y + 4
    padded_W = W + 2 * pad_x
    padded_H = H + 2 * pad_y

    # Yüksek kaliteli ölçekleme — bir kez yapılır, her frame için değil
    pil_padded = pil_img.resize((padded_W, padded_H), Image.LANCZOS)
    padded_arr = np.array(pil_padded)   # uint8 (padded_H, padded_W, 3)

    # Hareket yönü: görselden deterministik 4 yön
    direction_seed = int(np.sum(frame[:10, :10])) % 4

    # Derinlik ortalaması → hız çarpanı [0.55, 1.0]
    # Derin (uzak) sahne yavaş kayar, sığ (yakın) sahne hızlı kayar
    mean_depth = float(np.mean(depth_norm))
    speed_factor = 0.55 + 0.45 * mean_depth

    def ease_in_out(t: float, d: float) -> float:
        """Smoothstep: başlangıç ve bitiş yumuşak, orta lineer."""
        p = min(1.0, t / max(d, 0.001))
        return p * p * (3.0 - 2.0 * p)

    def make_frame(t):
        progress = ease_in_out(t, duration)   # [0, 1]

        if direction_seed == 0:
            # Sol → Sağ
            x0 = pad_x + int(progress * total_px_x * speed_factor)
            y0 = pad_y
        elif direction_seed == 1:
            # Yukarı → Aşağı
            x0 = pad_x
            y0 = pad_y + int(progress * total_px_y * speed_factor)
        elif direction_seed == 2:
            # Sağ → Sol
            x0 = pad_x + int((1.0 - progress) * total_px_x * speed_factor)
            y0 = pad_y
        else:
            # Aşağı → Yukarı
            x0 = pad_x
            y0 = pad_y + int((1.0 - progress) * total_px_y * speed_factor)

        # Güvenlik klampı
        x0 = max(0, min(x0, padded_W - W))
        y0 = max(0, min(y0, padded_H - H))

        # Integer-slice crop — WARP YOK, deformasyon YOK
        return padded_arr[y0: y0 + H, x0: x0 + W]

    return VideoClip(make_frame, duration=duration)



def _clip_none(frame: np.ndarray, duration: float) -> VideoClip:
    return ImageClip(frame).with_duration(duration)


def _clip_kenburns(
    frame: np.ndarray,
    duration: float,
    intensity: float = 0.04,
    W: int = 1920,
    H: int = 1080,
) -> VideoClip:
    """Subtle Ken Burns: aynı görsel içinde yavaş zoom (caption değişimleri için ideal)."""
    pil_img = Image.fromarray(frame)

    def make_frame(t):
        # 0 → intensity zoom
        scale = 1.0 + intensity * (t / max(duration, 0.001))
        new_w = max(W, int(W * scale))
        new_h = max(H, int(H * scale))
        resized = pil_img.resize((new_w, new_h), Image.BILINEAR)
        x = (new_w - W) // 2
        y = (new_h - H) // 2
        return np.array(resized.crop((x, y, x + W, y + H)))

    return VideoClip(make_frame, duration=duration)


def _clip_fade(
    frame_curr: np.ndarray,
    frame_next: np.ndarray,
    duration: float,
    td: float,
) -> VideoClip:
    fc = frame_curr.astype(np.float32)
    fn = frame_next.astype(np.float32)
    td = min(td, duration * 0.4)

    def make_frame(t):
        if t >= duration - td and td > 0:
            alpha = min(1.0, (t - (duration - td)) / td)
            return (fc * (1.0 - alpha) + fn * alpha).astype(np.uint8)
        return frame_curr

    return VideoClip(make_frame, duration=duration)


def _clip_slide(
    frame_curr: np.ndarray,
    frame_next: np.ndarray,
    duration: float,
    td: float,
    W: int,
    H: int,
) -> VideoClip:
    td = min(td, duration * 0.4)

    def make_frame(t):
        if t < duration - td:
            return frame_curr
        progress = min(1.0, (t - (duration - td)) / max(td, 0.001))
        offset = int(W * progress)
        canvas = np.empty((H, W, 3), dtype=np.uint8)
        visible_curr = W - offset
        if visible_curr > 0:
            canvas[:, :visible_curr] = frame_curr[:, offset:offset + visible_curr]
        if offset > 0:
            canvas[:, visible_curr:] = frame_next[:, :offset]
        return canvas

    return VideoClip(make_frame, duration=duration)


def apply_hook_intro_zoom(
    clip: VideoClip,
    hook_duration: float = 1.5,
    start_scale: float = 1.05,
) -> VideoClip:
    """
    Casper AI: YouTube Shorts İlk 1.5 Saniye Hook Zoom Efekti (Thumb-Stop).
    İlk `hook_duration` saniyede %105'ten %100'e yumuşak zoom-in uygulayarak
    kullanıcının parmak kaydırmasını önler ve izlenme süresini artırır.
    """
    w, h = clip.size

    def hook_frame(get_frame, t):
        frame = get_frame(t)
        if t >= hook_duration:
            return frame
        progress = max(0.0, min(1.0, t / max(hook_duration, 0.001)))
        scale = start_scale - (start_scale - 1.0) * progress
        frame_arr = np.asarray(frame, dtype=np.uint8)
        pil_img = Image.fromarray(frame_arr)
        new_w = max(w, int(round(w * scale)))
        new_h = max(h, int(round(h * scale)))
        resized = pil_img.resize((new_w, new_h), Image.BILINEAR)
        x = (new_w - w) // 2
        y = (new_h - h) // 2
        return np.array(resized.crop((x, y, x + w, y + h)), dtype=np.uint8)

    return clip.transform(hook_frame)


# ──────────────────────────────────────────
# Watermark
# ──────────────────────────────────────────

def make_watermark_overlay(
    text: Optional[str],
    image_path: Optional[str],
    duration: float,
    width: int,
    height: int,
    position: str = "top-right",
) -> Optional[VideoClip]:
    """
    Watermark olarak ya hazır bir PNG ya da metin render'ı.
    Şeffaf PNG, küçük boyut, köşede konumlandırılır.
    """
    if not text and not image_path:
        return None

    margin = max(20, int(min(width, height) * 0.02))
    wm_w = max(120, int(width * 0.12))
    wm_h = max(40, int(height * 0.06))

    layer = Image.new("RGBA", (wm_w, wm_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path).convert("RGBA")
            img.thumbnail((wm_w, wm_h), Image.LANCZOS)
            x = (wm_w - img.width) // 2
            y = (wm_h - img.height) // 2
            layer.paste(img, (x, y), img)
        except Exception:
            pass

    if text:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 28)
        except Exception:
            font = ImageFont.load_default()
        # Yarı saydam arka plan
        draw.rectangle([(0, 0), (wm_w, wm_h)], fill=(0, 0, 0, 100))
        bb = draw.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        draw.text(((wm_w - tw) / 2, (wm_h - th) / 2 - 4), text, font=font, fill=(255, 255, 255, 220))

    arr = np.array(layer)

    def make_frame(t):
        return arr

    clip = VideoClip(make_frame, duration=duration).with_duration(duration)

    if position == "top-left":
        x, y = margin, margin
    elif position == "top-right":
        x, y = width - wm_w - margin, margin
    elif position == "bottom-left":
        x, y = margin, height - wm_h - margin
    elif position == "bottom-center":
        x, y = (width - wm_w) // 2, height - wm_h - margin
    else:  # bottom-right
        x, y = width - wm_w - margin, height - wm_h - margin

    clip = clip.with_position((x, y))
    return clip


# ──────────────────────────────────────────
# ffmpeg bulucu
# ──────────────────────────────────────────

def find_ffmpeg(require_subtitles: bool = False) -> str:
    """Sistemde ffmpeg yolunu bulur. libass/subtitles desteği olan binary'leri önceliklendirir."""
    candidates = []

    # 1. imageio_ffmpeg paketi (libass/subtitles desteği yerleşiktir)
    try:
        import imageio_ffmpeg
        imgio_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if imgio_exe and os.path.exists(imgio_exe):
            candidates.append(imgio_exe)
    except Exception:
        pass

    # 2. Sistem ffmpeg ikilileri
    candidates.extend([
        shutil.which("ffmpeg"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        "C:/ffmpeg/bin/ffmpeg.exe",
    ])

    valid = []
    for c in candidates:
        if c and os.path.exists(c) and c not in valid:
            valid.append(c)

    if not valid:
        raise FileNotFoundError(
            "ffmpeg bulunamadı. Lütfen ffmpeg'i kurun (macOS: brew install ffmpeg, "
            "Linux: apt install ffmpeg, Windows: ffmpeg.org)."
        )

    # subtitles filtresini destekleyen ilk ffmpeg'i önceliklendir
    for c in valid:
        try:
            res = subprocess.run([c, "-filters"], capture_output=True, text=True, timeout=5)
            if "subtitles" in res.stdout:
                return c
        except Exception:
            continue

    return valid[0]


def get_ffmpeg_version() -> str:
    try:
        ffmpeg = find_ffmpeg()
        out = subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True, text=True, timeout=5
        )
        return out.stdout.splitlines()[0] if out.stdout else "unknown"
    except Exception as e:
        return f"unavailable ({e})"


def get_hardware_accelerated_encoder_args(target_bitrate: str = "8000k") -> list[str]:
    """
    Casper AI: Apple Silicon (M1/M2/M3/M4) VideoToolbox Donanım Hızlandırıcı Tespiti.
    macOS üzerinde h264_videotoolbox enkoderini devreye sokarak video render süresini 3-5 kat hızlandırır.
    Linux/Windows veya desteklenmeyen ortamlarda standart libx264 kullanır.
    """
    import platform
    if platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64"):
        return ["-c:v", "h264_videotoolbox", "-b:v", target_bitrate, "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p"]



# ──────────────────────────────────────────
# Base video oluşturma (altyazısız, ses dahil)
# ──────────────────────────────────────────

class BaseVideoBuilder:
    """
    VisualGroup listesinden altyazısız base video oluşturur.
    Geçişler SADECE gerçek görsel değişimlerinde uygulanır (caption kaynaklı değil).
    """

    def __init__(self, config: EditConfig):
        self.config = config
        self.scaler = ImageScaler(config.width, config.height)

    def build(
        self,
        groups: list[VisualGroup],
        audio_path: str,
        output_path: str,
    ) -> bool:
        if not groups:
            print("[EDITOR] Görsel grubu yok, base video oluşturulamadı.")
            return False

        print(f"[EDITOR] {len(groups)} görsel sahnesi, toplam süre ~{sum(g.duration for g in groups):.1f}s")
        print(f"[EDITOR] Geçiş: {self.config.transition} | Ken Burns: {self.config.kenburns_intensity:.0%}")

        # NASA Logo Censor initialization
        censor_logo_path = self.config.censor_logo_path
        censor_processor = None
        if censor_logo_path and os.path.exists(censor_logo_path):
            try:
                from censor_processor import NASALogoCensor
                censor_processor = NASALogoCensor()
                print(f"[EDITOR] NASA Logo Censor initialized with logo: {censor_logo_path}")
            except Exception as e:
                print(f"[EDITOR] Failed to initialize NASA Logo Censor: {e}")

        # Klipleri oluştur
        clips = []
        W, H = self.config.width, self.config.height
        transition = self.config.transition
        td = self.config.transition_dur

        for i, g in enumerate(groups):
            duration = g.duration
            path = g.image_path
            
            # Check if it is a video file
            is_vid = False
            if path:
                ext = Path(path).suffix.lower()
                if ext in ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'):
                    is_vid = True
            
            if is_vid:
                try:
                    print(f"[EDITOR] Video klip hazırlanıyor: {os.path.basename(path)} | Süre: {duration:.1f}s")
                    clip = VideoFileClip(path).without_audio()
                    
                    # Aspect-ratio scale
                    clip_w, clip_h = clip.size
                    if W < H and clip_w > clip_h:
                        # Blurred-fit for landscape video on vertical frame
                        from PIL import ImageFilter, Image
                        def blur_frame(get_frame, t):
                            frame = get_frame(t)
                            pil_img = Image.fromarray(frame)
                            blurred = pil_img.filter(ImageFilter.GaussianBlur(30))
                            return np.array(blurred)

                        # 1. Background (fill-crop and blur)
                        scale_bg = max(W / clip_w, H / clip_h)
                        bg_w = int(clip_w * scale_bg)
                        bg_h = int(clip_h * scale_bg)
                        bg_clip = clip.resized((bg_w, bg_h))
                        bg_x = (bg_w - W) // 2
                        bg_y = (bg_h - H) // 2
                        bg_clip = bg_clip.cropped(x1=bg_x, y1=bg_y, width=W, height=H)
                        bg_clip = bg_clip.transform(blur_frame)

                        # 2. Foreground (fit-width, centered vertically)
                        scale_fg = W / clip_w
                        fg_w = W
                        fg_h = int(clip_h * scale_fg)
                        fg_clip = clip.resized((fg_w, fg_h))
                        fg_y = (H - fg_h) // 2
                        fg_clip = fg_clip.with_position(("center", fg_y))

                        # 3. Combine
                        clip = CompositeVideoClip([bg_clip, fg_clip], size=(W, H))
                    else:
                        # Standard fill-crop
                        scale = max(W / clip_w, H / clip_h)
                        new_w = int(clip_w * scale)
                        new_h = int(clip_h * scale)
                        clip = clip.resized((new_w, new_h))
                        x_offset = (new_w - W) // 2
                        y_offset = (new_h - H) // 2
                        clip = clip.cropped(x1=x_offset, y1=y_offset, width=W, height=H)
                    
                    # Loop or truncate duration
                    if clip.duration < duration:
                        try:
                            clip = clip.loop(duration=duration)
                        except Exception:
                            # Loop manually by duplicating and concatenating
                            num_loops = int(np.ceil(duration / clip.duration))
                            clip = concatenate_videoclips([clip] * num_loops).subclipped(0, duration)
                    else:
                        # Skip first 3 seconds if long enough to avoid intro logo screens, otherwise center it
                        if clip.duration >= duration + 4.0:
                            start_time = 3.0
                        else:
                            start_time = max(0.0, (clip.duration - duration) / 2)
                        clip = clip.subclipped(start_time, start_time + duration)
                    
                    if censor_processor:
                        print(f"[EDITOR] NASA Logo Censor applied to video clip: {os.path.basename(path)}")
                        clip = clip.fl_image(lambda frame: censor_processor.process_frame(frame, censor_logo_path))
                        
                except Exception as e:
                    print(f"[EDITOR] Video klip yükleme hatası: {e}. Görsel yedek denenecek.")
                    is_vid = False
            
            if not is_vid:
                # Normal image processing
                arr = self.scaler.prepare(path)
                if censor_processor:
                    arr = censor_processor.process_frame(arr, censor_logo_path)
                curr = arr
                next_arr = None
                
                if i + 1 < len(groups):
                    next_path = groups[i + 1].image_path
                    next_ext = Path(next_path).suffix.lower() if next_path else ""
                    if next_ext not in ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'):
                        try:
                            next_arr = self.scaler.prepare(next_path)
                            if censor_processor:
                                next_arr = censor_processor.process_frame(next_arr, censor_logo_path)
                        except Exception:
                            pass
                
                if transition == "parallax":
                    clip = _clip_parallax(curr, duration, W, H)
                elif transition == "kenburns":
                    clip = _clip_kenburns(curr, duration, self.config.kenburns_intensity, W, H)
                elif transition == "zoom":
                    clip = _clip_kenburns(curr, duration, max(self.config.kenburns_intensity, 0.05), W, H)
                elif transition == "slide" and next_arr is not None:
                    clip = _clip_slide(curr, next_arr, duration, td, W, H)
                elif transition == "fade" and next_arr is not None:
                    clip = _clip_fade(curr, next_arr, duration, td)
                else:
                    clip = _clip_none(curr, duration)
            
            clips.append(clip)
        video = concatenate_videoclips(clips, method="chain")

        # Casper AI: YouTube Shorts İlk 1.5 Saniye Hook Zoom Efekti (Thumb-Stop)
        if getattr(self.config, "hook_intro_effect", True) and video.duration >= 2.0:
            try:
                print("[EDITOR] 🎯 YouTube Shorts Hook efekti devrede (İlk 1.5s %105 -> %100 zoom-in)...")
                video = apply_hook_intro_zoom(video, hook_duration=1.5, start_scale=1.05)
            except Exception as hook_err:
                print(f"[EDITOR] Hook zoom efekti uygulanamadı (orijinal klip korunuyor): {hook_err}")

        # Ses ekle
        try:
            audio = AudioFileClip(audio_path)
            if audio.duration > video.duration:
                # Video sesden kısa kalmışsa sesi ASLA kesme! Son video karesini uzatarak videoyu sese eşitle
                pad_dur = audio.duration - video.duration
                if clips:
                    last_clip = clips[-1]
                    clips[-1] = last_clip.with_duration(last_clip.duration + pad_dur)
                    video = concatenate_videoclips(clips, method="chain")
            elif audio.duration < video.duration - 0.1:
                # Sessizlik ile doldur
                from moviepy import concatenate_audioclips, AudioClip
                pad_dur = video.duration - audio.duration
                silence = AudioClip(lambda t: 0, duration=pad_dur, fps=44100)
                audio = concatenate_audioclips([audio, silence])

            extra_audio_clips = []

            # Havacılık kanalı için ses efektleri (SFX) ekle
            if self.config.is_aviation:
                ensure_aviation_sfx()
                import moviepy.audio.fx as afx
                
                # 1) Kabin Uğultusu (Continuous hum)
                cabin_path = SFX_DIR / "cabin_hum.mp3"
                if cabin_path.exists():
                    try:
                        cabin_clip = AudioFileClip(str(cabin_path))
                        if cabin_clip.duration < video.duration:
                            num_loops = int(np.ceil(video.duration / cabin_clip.duration))
                            from moviepy import concatenate_audioclips
                            cabin_clip = concatenate_audioclips([cabin_clip] * num_loops)
                        cabin_clip = cabin_clip.subclipped(0, video.duration)
                        cabin_clip = cabin_clip.with_effects([afx.MultiplyVolume(0.06)])
                        extra_audio_clips.append(cabin_clip)
                    except Exception as ex:
                        print(f"[EDITOR-SFX] Kabin uğultusu eklenemedi: {ex}")

                # 2) Sahnelerin duygularına göre efekt yerleşimi
                current_time = 0.0
                for g in groups:
                    emotion = g.emotion.lower() if hasattr(g, "emotion") else "neutral"
                    duration = g.duration
                    
                    if emotion != "neutral":
                        sfx_file = None
                        if emotion == "excited":
                            sfx_file = "gpws_pullup.mp3"
                        elif emotion in ("dramatic", "mysterious"):
                            sfx_file = "master_warning.mp3"
                        elif emotion == "sad":
                            sfx_file = "sirens.mp3"
                        elif emotion == "happy":
                            sfx_file = "tire_screech.mp3"
                            
                        if sfx_file:
                            sfx_path = SFX_DIR / sfx_file
                            if sfx_path.exists():
                                try:
                                    sfx_clip = AudioFileClip(str(sfx_path))
                                    sfx_clip = sfx_clip.subclipped(0, min(duration, sfx_clip.duration))
                                    sfx_clip = sfx_clip.with_start(current_time)
                                    sfx_vol = 0.15 if sfx_file in ("gpws_pullup.mp3", "master_warning.mp3") else 0.08
                                    sfx_clip = sfx_clip.with_effects([afx.MultiplyVolume(sfx_vol)])
                                    extra_audio_clips.append(sfx_clip)
                                except Exception as ex:
                                    print(f"[EDITOR-SFX] Efekt eklenemedi ({sfx_file}): {ex}")
                                    
                    current_time += duration

                # 3) Gerçek LiveATC telsiz kaydını (varsa) ekle
                if self.config.liveatc_path and os.path.exists(self.config.liveatc_path):
                    try:
                        liveatc_clip = AudioFileClip(self.config.liveatc_path)
                        crisis_start = None
                        current_time = 0.0
                        for g in groups:
                            if g.emotion.lower() in ("dramatic", "excited", "mysterious"):
                                crisis_start = current_time
                                break
                            current_time += g.duration
                            
                        if crisis_start is None:
                            crisis_start = video.duration / 2.0
                            
                        if crisis_start < video.duration:
                            atc_dur = video.duration - crisis_start
                            if liveatc_clip.duration < atc_dur:
                                num_loops = int(np.ceil(atc_dur / liveatc_clip.duration))
                                from moviepy import concatenate_audioclips
                                liveatc_clip = concatenate_audioclips([liveatc_clip] * num_loops)
                            liveatc_clip = liveatc_clip.subclipped(0, atc_dur)
                            liveatc_clip = liveatc_clip.with_start(crisis_start)
                            liveatc_clip = liveatc_clip.with_effects([afx.MultiplyVolume(0.12)])
                            extra_audio_clips.append(liveatc_clip)
                            print(f"[EDITOR-SFX] Gerçek LiveATC telsiz kaydı kriz anında ({crisis_start:.1f}s) başlayacak şekilde mikslendi.")
                    except Exception as ex:
                        print(f"[EDITOR-SFX] LiveATC telsiz kaydı mikslenemedi: {ex}")

            # Arka Plan Müziği (BGM) - Tüm kanal türleri için güvenli ve doğrudan miksleme
            if self.config.bgm_path and os.path.exists(self.config.bgm_path):
                try:
                    import moviepy.audio.fx as afx
                    try:
                        bgm_vol = float(self.config.bgm_volume) if self.config.bgm_volume not in (None, "") else 0.25
                    except (ValueError, TypeError):
                        bgm_vol = 0.25
                    bgm_vol = max(0.0, min(1.0, bgm_vol))
                    bgm_clip = AudioFileClip(self.config.bgm_path)
                    target_dur = video.duration if video.duration else (audio.duration if audio.duration else 60.0)
                    bgm_clip = bgm_clip.with_effects([afx.AudioLoop(duration=target_dur), afx.MultiplyVolume(bgm_vol)])
                    extra_audio_clips.append(bgm_clip)
                    print(f"[EDITOR-BGM] Arka plan müziği base videoya mikslendi: {os.path.basename(self.config.bgm_path)} (Ses: {bgm_vol:.2f})")
                except Exception as bgm_ex:
                    print(f"[EDITOR-BGM] BGM mikslenirken hata: {bgm_ex}")
            
            if extra_audio_clips:
                audio = CompositeAudioClip([audio] + extra_audio_clips)

            video = video.with_audio(audio)
        except Exception as e:
            print(f"[EDITOR] Ses eklenemedi: {e}")

        # Watermark (composition)
        wm_overlay = make_watermark_overlay(
            text=self.config.watermark_text,
            image_path=self.config.watermark_path,
            duration=video.duration,
            width=W,
            height=H,
            position=self.config.watermark_position,
        )
        if wm_overlay is not None:
            video = CompositeVideoClip([video, wm_overlay])

        # Yaz
        import platform
        is_apple_silicon = platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64")
        codec_name = "h264_videotoolbox" if is_apple_silicon else "libx264"

        write_kwargs = dict(
            fps=self.config.fps,
            codec=codec_name,
            audio_codec="aac",
            logger=None,
            pixel_format="yuv420p",
        )
        if not is_apple_silicon:
            write_kwargs["preset"] = "fast"
        if self.config.shorts_mode:
            write_kwargs["ffmpeg_params"] = ["-vf", "setsar=1"]

        video.write_videofile(output_path, **write_kwargs)
        print(f"[EDITOR] Base video yazıldı ({codec_name}) → {output_path}")
        return True


# ──────────────────────────────────────────
# Ses Normalizasyonu (EBU R128) & Subtitle Burn
# ──────────────────────────────────────────

def normalize_audio_ebur128(
    input_path: str,
    output_path: str,
    target_i: float = -14.0,
    lra: float = 7.0,
    tp: float = -1.5,
) -> bool:
    """
    Casper AI: EBU R128 (-14 LUFS) ses seviyesi normalizasyonu.
    YouTube Shorts ve yayın standartlarına göre ses patlamalarını engeller, kısık diyalogları dengeler.
    """
    ffmpeg = find_ffmpeg()
    filter_str = f"loudnorm=I={target_i}:LRA={lra}:tp={tp}"
    ext = Path(input_path).suffix.lower()
    is_video = ext in (".mp4", ".mov", ".mkv", ".avi", ".webm")

    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-af", filter_str,
    ]
    if is_video:
        cmd.extend(["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"])
    else:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    cmd.append(output_path)

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return res.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        print(f"[EBU-R128] Ses normalizasyon hatası: {e}")
        return False


class SubtitleBurner:
    """
    ffmpeg subtitles filter kullanarak ASS altyazıyı base video üzerine yazar.
    Opsiyonel olarak BGM de ekler ve EBU R128 ses seviyesi normalizasyonu uygular.
    """

    def __init__(self, config: EditConfig):
        self.config = config
        self.ffmpeg = find_ffmpeg()

    def burn(
        self,
        base_video: str,
        ass_path: str,
        output_path: str,
        normalize_loudness: Optional[bool] = None,
    ) -> bool:
        """
        Base video + ASS → final video.
        Casper AI: normalize_loudness True ise EBU R128 (-14 LUFS) ses seviyesi normalizasyonu uygular.
        """
        if not os.path.exists(base_video):
            print(f"[BURN] Base video bulunamadı: {base_video}")
            return False
        if not os.path.exists(ass_path):
            print(f"[BURN] ASS dosyası bulunamadı: {ass_path}")
            return False

        # ASS yolundaki ' : ve \ escape et (ffmpeg filter syntax)
        ass_escaped = ass_path.replace("\\", "/").replace("'", r"\'").replace(":", r"\:")

        # subtitles filter'ı
        vf = f"subtitles='{ass_escaped}'"

        tmp_output = output_path
        same_file = os.path.abspath(base_video) == os.path.abspath(output_path)
        if same_file:
            tmp_output = str(Path(output_path).parent / f"burn_tmp_{int(time.time())}.mp4")

        if normalize_loudness is None:
            normalize_loudness = getattr(self.config, "normalize_audio_loudness", True)

        audio_args = (
            ["-af", "loudnorm=I=-14:LRA=7:tp=-1.5", "-c:a", "aac", "-b:a", "192k"]
            if normalize_loudness
            else ["-c:a", "copy"]
        )

        enc_args = get_hardware_accelerated_encoder_args("8000k")
        cmd = [
            self.ffmpeg, "-y",
            "-i", base_video,
            "-vf", vf,
            *enc_args,
            *audio_args,
            tmp_output,
        ]

        print(f"[BURN] ffmpeg subtitles filter uygulanıyor (Motor: {self.ffmpeg})...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                print(f"[BURN] Hata: {result.stderr[-1000:]}")
                if same_file and os.path.exists(tmp_output):
                    try:
                        os.remove(tmp_output)
                    except Exception:
                        pass
                return False

            if same_file:
                shutil.move(tmp_output, output_path)

            print(f"[BURN] Final video yazıldı → {output_path}")
            return True
        except subprocess.TimeoutExpired:
            print("[BURN] Zaman aşımı (600s).")
            if same_file and os.path.exists(tmp_output):
                try:
                    os.remove(tmp_output)
                except Exception:
                    pass
            return False
        except Exception as e:
            print(f"[BURN] Hata: {e}")
            if same_file and os.path.exists(tmp_output):
                try:
                    os.remove(tmp_output)
                except Exception:
                    pass
            return False

    def _standardize_clip(
        self,
        input_path: str,
        output_path: str,
        target_w: int,
        target_h: int,
        target_fps: int,
    ) -> bool:
        """
        Giriş klibini belirtilen çözünürlük, FPS ve standart AAC stereo (44100Hz)
        ses biçimine dönüştürür. Ses yoksa sessiz ses ekler.
        """
        if not os.path.exists(input_path):
            return False

        has_audio = False
        try:
            from moviepy import VideoFileClip as VFC
            clip = VFC(input_path)
            has_audio = (clip.audio is not None)
            clip.close()
        except Exception:
            has_audio = False

        vf = (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,fps={target_fps}"
        )

        enc_args = get_hardware_accelerated_encoder_args("6000k")
        if has_audio:
            cmd = [
                self.ffmpeg, "-y",
                "-i", input_path,
                "-vf", vf,
                *enc_args,
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                output_path
            ]
        else:
            # Sessiz ses kanalı üret
            cmd = [
                self.ffmpeg, "-y",
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-i", input_path,
                "-filter_complex", f"[1:v]{vf}[v]",
                "-map", "[v]",
                "-map", "0:a",
                *enc_args,
                "-c:a", "aac",
                "-shortest",
                output_path
            ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"[STANDARDIZE] Hata ({input_path}): {result.stderr[-1000:]}")
                return False
            return True
        except Exception as e:
            print(f"[STANDARDIZE] Hata ({input_path}): {e}")
            return False

    def concat_with_intro_outro(
        self,
        intro_path: Optional[str],
        main_path: str,
        outro_path: Optional[str],
        output_path: str,
    ) -> bool:
        """
        İntro + ana video + outro'yu arka arkaya birleştirir.
        Klipleri önce ana videonun çözünürlük/fps değerlerine göre standartlaştırır.
        """
        try:
            from moviepy import VideoFileClip as VFC
            main_clip = VFC(main_path)
            target_w = main_clip.width
            target_h = main_clip.height
            target_fps = int(round(main_clip.fps)) if main_clip.fps else 24
            main_clip.close()
        except Exception:
            target_w = self.config.width or 1080
            target_h = self.config.height or 1920
            target_fps = self.config.fps or 24

        temp_files_to_clean = []
        parts = []

        try:
            # 1. Intro standartlaştır
            if intro_path and os.path.exists(intro_path):
                temp_intro = main_path + ".temp_intro.mp4"
                print(f"[CONCAT] Intro standartlaştırılıyor: {intro_path}")
                if self._standardize_clip(intro_path, temp_intro, target_w, target_h, target_fps):
                    parts.append(temp_intro)
                    temp_files_to_clean.append(temp_intro)
                else:
                    print("[CONCAT] Intro standartlaştırılamadı, atlanıyor.")

            # 2. Ana video standartlaştır (ses/video formatlarını tam uyuşturmak için)
            temp_main = main_path + ".temp_main.mp4"
            print(f"[CONCAT] Ana video standartlaştırılıyor: {main_path}")
            if self._standardize_clip(main_path, temp_main, target_w, target_h, target_fps):
                parts.append(temp_main)
                temp_files_to_clean.append(temp_main)
            else:
                print("[CONCAT] Ana video standartlaştırılamadı! Orijinal dosya kullanılacak.")
                parts.append(main_path)

            # 3. Outro standartlaştır
            if outro_path and os.path.exists(outro_path):
                temp_outro = main_path + ".temp_outro.mp4"
                print(f"[CONCAT] Outro standartlaştırılıyor: {outro_path}")
                if self._standardize_clip(outro_path, temp_outro, target_w, target_h, target_fps):
                    parts.append(temp_outro)
                    temp_files_to_clean.append(temp_outro)
                else:
                    print("[CONCAT] Outro standartlaştırılamadı, atlanıyor.")

            if len(parts) == 1:
                shutil.copy(parts[0], output_path)
                return True

            # ffmpeg concat demuxer
            list_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            )
            try:
                for p in parts:
                    abs_p = os.path.abspath(p)
                    list_file.write(f"file '{abs_p}'\n")
                list_file.close()

                cmd = [
                    self.ffmpeg, "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file.name,
                    "-c", "copy",
                    output_path,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    print(f"[CONCAT] Hata: {result.stderr[-1000:]}")
                    return False
                return True
            finally:
                try:
                    os.unlink(list_file.name)
                except Exception:
                    pass
        finally:
            for tf in temp_files_to_clean:
                try:
                    if os.path.exists(tf):
                        os.unlink(tf)
                except Exception:
                    pass


# ──────────────────────────────────────────
# Üst düzey facade
# ──────────────────────────────────────────

class VideoEditor:
    """
    Yüksek seviye edit facade.
    1. Caption gruplama
    2. Base video oluşturma
    3. ASS subtitle üretimi
    4. ffmpeg ile subtitle burn + BGM
    5. İntro/outro ekleme
    """

    def __init__(self, config: EditConfig):
        self.config = config
        self.base_builder = BaseVideoBuilder(config)
        self.burner = SubtitleBurner(config)

    def compose(
        self,
        segments: list[dict],
        audio_path: str,
        output_path: str,
        work_dir: str,
    ) -> dict:
        """
        Tam pipeline.

        segments: [{"text", "duration", "image_path"}, ...] (VideoGenerator'dan gelen)
        audio_path: TTS mp3/wav
        output_path: final video yolu
        work_dir: çalışma klasörü
        """
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        log = {"groups": 0, "captions": 0, "ass_path": None, "base_path": None}

        # 1) Gruplama — asıl sorunun çözümü
        groups = group_captions_by_image(segments)
        log["groups"] = len(groups)
        log["captions"] = sum(len(g.captions) for g in groups)
        print(f"[EDITOR] {len(groups)} görsel sahnesi, {log['captions']} caption")
        for i, g in enumerate(groups):
            print(f"  [Sahne {i}] {g.duration:.1f}s | {len(g.captions)} caption | img={os.path.basename(g.image_path) if g.image_path else 'blank'}")

        if not groups:
            return {**log, "success": False, "error": "Boş sahne listesi"}

        # Ses dosyasının gerçek süresini al ve son grubun süresini sese tam eşitle
        try:
            from moviepy import AudioFileClip
            with AudioFileClip(audio_path) as a_clip:
                audio_dur = a_clip.duration
            total_groups_dur = sum(g.duration for g in groups)
            if audio_dur > total_groups_dur:
                pad = audio_dur - total_groups_dur
                groups[-1].duration += pad
                print(f"[EDITOR] Son görsel sahnesi {pad:.2f}s uzatılarak tam ses süresine ({audio_dur:.2f}s) eşitlendi.")
        except Exception as e:
            print(f"[EDITOR] Ses süresi hizalama uyarısı: {e}")

        # 2) Base video (altyazısız, watermark opsiyonel)
        base_path = str(Path(work_dir) / "base.mp4")
        ok = self.base_builder.build(groups, audio_path, base_path)
        if not ok:
            return {**log, "success": False, "error": "Base video oluşturulamadı"}
        log["base_path"] = base_path

        # 3) ASS altyazı üretimi
        from ass_subtitle import ASSWriter, captions_from_boundaries
        # VisualGroup'lardan mutlak zamanlı caption event'leri
        events = segments_to_caption_events(groups)
        boundaries_like = [{"text": e["text"], "offset": e["start"], "duration": e["end"] - e["start"]} for e in events]
        captions = captions_from_boundaries(boundaries_like, split_max_words=99)
        # split_max_words=99 çünkü caption'lar zaten 6 kelimelik parçalar

        ass_path = str(Path(work_dir) / "subs.ass")
        ass_writer = ASSWriter(
            width=self.config.width,
            height=self.config.height,
            preset=self.config.subtitle_preset,
            animation=self.config.subtitle_animation,
            shorts_mode=self.config.shorts_mode,
        )
        ass_writer.write(captions, ass_path)
        log["ass_path"] = ass_path
        print(f"[EDITOR] ASS altyazı → {ass_path} ({len(captions)} satır)")

        # 4) ffmpeg burn
        ok = self.burner.burn(base_path, ass_path, output_path)
        if not ok:
            # Fallback: base'i kopyala
            shutil.copy(base_path, output_path)
            print("[EDITOR] Subtitle burn başarısız, altyazısız base kullanıldı.")
            return {**log, "success": True, "fallback": True, "output": output_path}

        # 5) İntro/outro birleştirme
        if self.config.intro_clip_path or self.config.outro_clip_path:
            tmp_out = str(Path(work_dir) / "final_concat.mp4")
            ok = self.burner.concat_with_intro_outro(
                self.config.intro_clip_path, output_path, self.config.outro_clip_path, tmp_out
            )
            if ok:
                shutil.move(tmp_out, output_path)

        return {**log, "success": True, "output": output_path}


# ──────────────────────────────────────────
# Otomatik Clickbait Thumbnail Derleyici
# ──────────────────────────────────────────

def generate_clickbait_thumbnail(
    video_path: str,
    output_path: Optional[str] = None,
    custom_title: Optional[str] = None,
    sample_count: int = 5,
) -> str:
    """
    Casper AI: Otomatik Clickbait Thumbnail & Merak Metni Derleyici.
    1. Videodan en yüksek kontrast ve renk dinamizmine sahip dramatik sahne karesini seçer.
    2. YouTube Shorts / Video standartlarında çarpıcı sarı/kırmızı merak başlık rozeti basar.
    3. Hazır thumbnail dosya yolunu döndürür.
    """
    video_p = Path(video_path).resolve()
    if not video_p.exists():
        raise FileNotFoundError(f"Video bulunamadı: {video_path}")

    if output_path is None:
        output_path = str(video_p.with_name(f"{video_p.stem}_thumbnail.jpg"))

    ffmpeg = find_ffmpeg()

    # 1. Video süresini öğren
    duration = 5.0
    try:
        from moviepy import VideoFileClip
        with VideoFileClip(str(video_p)) as vclip:
            duration = max(1.0, float(vclip.duration))
    except Exception:
        pass

    # 2. Farklı zamanlardan aday kareler çıkar ve en yüksek kontrastlı olanı bul
    sample_timestamps = [
        min(duration * 0.1, 1.0),
        min(duration * 0.25, 3.0),
        min(duration * 0.5, 6.0),
        min(duration * 0.75, 10.0),
    ]
    if duration > 15:
        sample_timestamps.append(min(duration * 0.85, 20.0))

    best_frame_img: Optional[Image.Image] = None
    best_contrast_score = -1.0

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, ts in enumerate(sample_timestamps[:sample_count]):
            candidate_path = Path(tmpdir) / f"frame_{idx}.jpg"
            cmd = [
                ffmpeg, "-y",
                "-ss", f"{ts:.2f}",
                "-i", str(video_p),
                "-vframes", "1",
                "-q:v", "2",
                str(candidate_path),
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=10)
                if candidate_path.exists():
                    img = Image.open(candidate_path).convert("RGB")
                    # Kontrast skoru: standart sapma
                    arr = np.array(img.convert("L"), dtype=np.float32)
                    score = float(np.std(arr))
                    if score > best_contrast_score:
                        best_contrast_score = score
                        best_frame_img = img.copy()
            except Exception:
                continue

    if best_frame_img is None:
        # Fallback: estetik koyu renkli tuval
        best_frame_img = Image.new("RGB", (1080, 1920), color=(18, 18, 22))

    # 3. Başlık metnini belirle
    badge_text = "ŞOK EDEN ANLAR!"
    if custom_title:
        clean_title = re.sub(r"[#@][\w_]+", "", custom_title).strip()
        words = clean_title.split()
        if len(words) > 4:
            badge_text = " ".join(words[:4]).upper()
        elif words:
            badge_text = clean_title.upper()

    # 4. Pillow ile yüksek kontrastlı estetik badge çiz
    img_w, img_h = best_frame_img.size
    draw = ImageDraw.Draw(best_frame_img)

    # Font yükleme
    font_size = max(26, int(img_w * 0.052))
    font = None
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for fc in font_candidates:
        if os.path.exists(fc):
            try:
                font = ImageFont.truetype(fc, font_size)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), badge_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Pozisyon: Üst üçte bir veya orta-üst alan
    pad_x = 28
    pad_y = 16
    box_w = text_w + pad_x * 2
    box_h = text_h + pad_y * 2
    box_x = (img_w - box_w) // 2
    box_y = int(img_h * 0.20)

    # Arka plan kutusu (Koyu bordo / Siyah kontrast arka plan ve sarı/neon kenarlık)
    draw.rounded_rectangle(
        [(box_x - 4, box_y - 4), (box_x + box_w + 4, box_y + box_h + 4)],
        radius=14,
        fill=(220, 20, 60),  # Crimson Red dış vurgu
    )
    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=12,
        fill=(10, 10, 15),   # Koyu gece siyahı
    )

    # Parlak sarı yazı (#FFE600)
    text_x = box_x + pad_x
    text_y = box_y + pad_y - 2
    draw.text((text_x, text_y), badge_text, font=font, fill=(255, 230, 0))

    best_frame_img.save(output_path, "JPEG", quality=95)
    print(f"[THUMBNAIL] 📸 Clickbait thumbnail üretildi: {output_path} (Badge: '{badge_text}')")
    return output_path
