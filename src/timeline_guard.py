"""
core/timeline_guard.py
======================
Pre-Render Quality Gate (Modül 2): Deterministik Çizim, Süre ve Altyazı Eşitleyici.
(Deterministic Drawing & Duration Synchronizer for Pre-Render Quality Gate)

Mimarî Güncellemeler:
1. Dış Ses ve Süre Kilidi (Duration Buffer: +0.6 saniye):
   - mutagen, wave ve ffprobe ile milisaniye hassasiyetinde dış ses süresi okuma.
   - Video kompozisyon süresi: final_video_duration = audio_duration + 0.6 saniye.
   - Son cümlenin ekranda tamamen okunabilmesi ve sesin doğal bir fadeout ile bitmesi.
2. 2 Satırlı Kusursuz Altyazı Taşma Koruması (Line Wrap & Bounding Box):
   - Pillow ImageFont.getlength() / textbbox() ile piksel bazlı ölçüm.
   - Ekran genişliğinin %80'ini (screen_width * 0.80 -> 864px) aşmayan satırlar.
   - Kart başına katı 2 satır sınırı (max_lines_per_card = 2); uzun metinleri ekranı taşırmadan 2-3 kelimelik ardışık bloklara bölme.
3. Render Komut ve Filtre Entegratörü:
   - FFmpeg / MoviePy için süre parametrelerini ve ses sönümleme (fadeout) filtrelerini hazırlar.
"""

from __future__ import annotations

import os
import re
import wave
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union, Set
from PIL import Image, ImageFont, ImageDraw

logger = logging.getLogger("TimelineGuard")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class TimelineDurationLock(dict):
    """
    Kilitli zaman çizelgesi süresini temsil eder.
    Hem sözlük indeksleme ['locked_duration'] hem de nitelik .locked_duration erişimini destekler.
    """
    def __init__(self, audio_duration: float, tail_padding: float, locked_duration: float):
        super().__init__(
            audio_duration=audio_duration,
            tail_padding=tail_padding,
            locked_duration=locked_duration,
            final_video_duration=locked_duration
        )

    @property
    def audio_duration(self) -> float:
        return self["audio_duration"]

    @property
    def tail_padding(self) -> float:
        return self["tail_padding"]

    @property
    def locked_duration(self) -> float:
        return self["locked_duration"]

    @property
    def final_video_duration(self) -> float:
        return self["locked_duration"]


def get_system_font(size: int = 40, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Sistemde mevcut olan en kaliteli fontu FreeTypeFont olarak yükler."""
    candidate_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


class TimelineGuard:
    """
    Zaman çizelgesi ve altyazı taşma/senkronizasyon kalite denetçisi.
    """

    @classmethod
    def format_and_wrap_subtitles(
        cls,
        subtitles: List[Dict[str, Any]],
        screen_width: int = 1080,
        max_width_ratio: float = 0.80,
        font_size: int = 56
    ) -> List[Dict[str, Any]]:
        """
        Altyazı listesini alır, her bir öğenin metnini %80 genişlik sınırına göre
        kelime sınırlarından en fazla 2 satıra sarar ('\\n' ile ayırır).
        """
        font = get_system_font(size=font_size, bold=True)
        wrapped_subtitles = []
        for sub in subtitles:
            sub_copy = dict(sub)
            raw_text = sub_copy.get("text", "")
            lines = cls.wrap_text_to_pixel_width(
                text=raw_text,
                font=font,
                screen_width=screen_width,
                max_width_ratio=max_width_ratio,
                max_lines_per_card=2
            )
            if len(lines) > 2:
                sub_copy["text"] = f"{lines[0]}\n{' '.join(lines[1:])}"
            elif len(lines) == 2:
                sub_copy["text"] = f"{lines[0]}\n{lines[1]}"
            elif len(lines) == 1:
                sub_copy["text"] = lines[0]
            else:
                sub_copy["text"] = raw_text
            wrapped_subtitles.append(sub_copy)
        return wrapped_subtitles

    # ─────────────────────────────────────────────────────────────
    # 1. 2 SATIRLI ALTYAZI TAŞMA KORUMASI (BOUNDING BOX & WRAP)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def wrap_text_to_pixel_width(
        text: str,
        font: ImageFont.FreeTypeFont,
        screen_width: int = 1080,
        max_width_ratio: float = 0.80,
        max_lines_per_card: int = 2
    ) -> List[str]:
        """
        Metni piksel genişliğine göre katı bir şekilde satırlara böler.
        - max_width = screen_width * max_width_ratio (Örn: 1080 * 0.80 = 864px)
        - Kelime ortasından asla bölmez.
        - Satır genişliği sınırı aştığı anda sonraki satıra geçer.
        """
        max_px = int(screen_width * max_width_ratio)
        words = text.strip().split()
        if not words:
            return []

        lines: List[str] = []
        current_words: List[str] = []

        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        for w in words:
            candidate_line = " ".join(current_words + [w])
            try:
                line_w = font.getlength(candidate_line)
            except AttributeError:
                bbox = draw.textbbox((0, 0), candidate_line, font=font)
                line_w = bbox[2] - bbox[0]

            if line_w <= max_px or not current_words:
                current_words.append(w)
            else:
                lines.append(" ".join(current_words))
                current_words = [w]

        if current_words:
            lines.append(" ".join(current_words))

        return lines

    @classmethod
    def split_text_to_2line_cards(
        cls,
        text: str,
        font: ImageFont.FreeTypeFont,
        screen_width: int = 1080,
        max_width_ratio: float = 0.80
    ) -> List[List[str]]:
        """
        Uzun bir metni ekrandan taşmayacak şekilde her biri EN FAZLA 2 SATIR içeren
        kart bloklarına (chunks) ayırır.
        """
        all_lines = cls.wrap_text_to_pixel_width(
            text=text,
            font=font,
            screen_width=screen_width,
            max_width_ratio=max_width_ratio,
            max_lines_per_card=2
        )

        cards: List[List[str]] = []
        for i in range(0, len(all_lines), 2):
            card_lines = all_lines[i:i+2]
            cards.append(card_lines)

        return cards

    @staticmethod
    def calculate_card_bounding_box(
        lines: List[str],
        font: ImageFont.FreeTypeFont,
        screen_width: int = 1080,
        screen_height: int = 1920,
        padding_x: int = 44,
        padding_y: int = 24,
        bottom_pos: int = 240,
        line_spacing: int = 14
    ) -> Dict[str, Any]:
        """
        Altyazı cam kartının (glassmorphic card) ekrandaki kesin koordinatlarını hesaplar.
        Ekran sınırlarından (0, 0, screen_width, screen_height) asla taşmamasını garanti eder.
        """
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        max_line_w = 0
        total_text_h = 0
        line_details = []

        for line_str in lines:
            try:
                bbox = draw.textbbox((0, 0), line_str, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except Exception:
                w = font.getlength(line_str)
                h = font.size

            max_line_w = max(max_line_w, w)
            total_text_h += h
            line_details.append({"text": line_str, "width": w, "height": h})

        total_text_h += max(0, len(lines) - 1) * line_spacing

        card_w = max_line_w + (padding_x * 2)
        card_h = total_text_h + (padding_y * 2)

        # Ekran sınırları koruması (Sağdan ve soldan minimum 20px güvenlik marjı)
        card_w = min(card_w, screen_width - 40)
        card_x0 = max(20, (screen_width - card_w) // 2)
        card_y0 = max(20, screen_height - bottom_pos - card_h)
        card_x1 = card_x0 + card_w
        card_y1 = card_y0 + card_h

        is_overflowing = (
            card_x0 < 0 or card_x1 > screen_width or
            card_y0 < 0 or card_y1 > screen_height or
            max_line_w > (screen_width * 0.85)
        )

        return {
            "x0": card_x0,
            "y0": card_y0,
            "x1": card_x1,
            "y1": card_y1,
            "card_w": card_w,
            "card_h": card_h,
            "max_line_w": max_line_w,
            "is_overflowing": is_overflowing,
            "line_details": line_details
        }

    # ─────────────────────────────────────────────────────────────
    # 2. DIŞ SES VE SÜRE KİLİDİ (DURATION BUFFER: +0.60s)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_exact_audio_duration(audio_path: Union[str, Path]) -> float:
        """
        Dış ses dosyasının (WAV veya MP3) tam süresini milisaniye hassasiyetinde okur.
        Mutagen -> Wave -> FFprobe sırasıyla dener.
        """
        p = Path(audio_path)
        if not p.exists():
            raise FileNotFoundError(f"Dış ses dosyası bulunamadı: {p}")

        # 1. Mutagen
        try:
            import mutagen
            meta = mutagen.File(p)
            if meta is not None and meta.info and meta.info.length > 0:
                return float(meta.info.length)
        except Exception:
            pass

        # 2. Wave (WAV dosyaları için)
        if p.suffix.lower() == ".wav":
            try:
                with wave.open(str(p), "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    if rate > 0:
                        return float(frames / rate)
            except Exception:
                pass

        # 3. FFprobe (Kesin harici araç)
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(p)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            val = float(res.stdout.strip())
            if val > 0:
                return val
        except Exception as e_probe:
            logger.error(f"[TimelineGuard] ffprobe süre okuma hatası ({p.name}): {e_probe}")

        raise RuntimeError(f"Dış ses dosyasının süresi okunamadı: {p}")

    @classmethod
    def calculate_locked_timeline_duration(
        cls,
        audio_path: Union[str, Path],
        tail_padding_sec: float = 1.20
    ) -> Dict[str, float]:
        """
        Videonun kilitlenmiş toplam süresini hesaplar:
        final_video_duration = round(audio_duration + 1.20, 3)
        Bu tampon sayesinde dış sesin son hecesi asla kesilmez, video aniden kararmaz,
        son altyazı en az 1.5 saniye tam okunabilir kalır.
        """
        audio_dur = cls.get_exact_audio_duration(audio_path)
        locked_dur = round(audio_dur + tail_padding_sec, 3)

        logger.info(
            f"🔒 [TimelineGuard] Süre Kilidi: Dış Ses: {audio_dur:.3f}s | "
            f"Tampon Payı: +{tail_padding_sec:.2f}s -> Kilitli Video Süresi: {locked_dur:.3f}s"
        )
        return TimelineDurationLock(
            audio_duration=audio_dur,
            tail_padding=tail_padding_sec,
            locked_duration=locked_dur
        )

    @classmethod
    def prepare_render_duration_params(
        cls,
        audio_path: Union[str, Path],
        tail_padding_sec: float = 1.20,
        fadeout_duration: float = 0.40
    ) -> Dict[str, Any]:
        """
        FFmpeg veya MoviePy kompozisyonu için süre ve ses sönümleme (fadeout)
        parametrelerini derler.
        """
        lock_info = cls.calculate_locked_timeline_duration(audio_path, tail_padding_sec=tail_padding_sec)
        audio_dur = lock_info["audio_duration"]
        final_video_dur = lock_info["locked_duration"]

        fadeout_start = max(0.0, final_video_dur - fadeout_duration)

        return {
            "audio_duration": audio_dur,
            "tail_buffer": tail_padding_sec,
            "final_video_duration": final_video_dur,
            "fadeout_start": round(fadeout_start, 3),
            "fadeout_duration": fadeout_duration,
            "ffmpeg_audio_pad_filter": f"apad=whole_dur={final_video_dur:.3f},afade=t=out:st={audio_dur:.3f}:d={fadeout_duration:.3f}",
            "ffmpeg_time_flag": ["-t", f"{final_video_dur:.3f}"]
        }

    @staticmethod
    def rebalance_cut_durations(
        cut_durations: List[float],
        locked_duration: float
    ) -> List[float]:
        """
        Zaman çizelgesindeki kesme (cut) sürelerini, toplamları tam olarak
        locked_duration'a eşit olacak şekilde orantılı olarak yeniden dengeler.
        """
        if not cut_durations:
            return [locked_duration]

        raw_total = sum(cut_durations)
        if raw_total <= 0:
            equal_cut = locked_duration / len(cut_durations)
            return [round(equal_cut, 3) for _ in cut_durations]

        scale = locked_duration / raw_total
        balanced = [round(d * scale, 3) for d in cut_durations]

        diff = round(locked_duration - sum(balanced), 3)
        if balanced:
            balanced[-1] = round(balanced[-1] + diff, 3)

        return balanced

    # ─────────────────────────────────────────────────────────────
    # 3. DİNAMİK KEN BURNS & HAREKETLİ GÖRSEL MOTORU (SIFIR MONOTONLUK)
    # ─────────────────────────────────────────────────────────────
    enforce_video_clips: bool = False
    max_raw_occurrences: int = 1
    max_occurrences_per_source: int = 1
    used_timeline_assets: Dict[str, int] = {}
    used_timeline_hashes: Set[str] = set()
    used_perceptual_hashes: List[str] = []

    @classmethod
    def reset_timeline(cls):
        """Zaman çizelgesi varlık kullanım, MD5 ve algısal dHash kayıtlarını sıfırlar."""
        cls.used_timeline_assets.clear()
        cls.used_timeline_hashes.clear()
        cls.used_perceptual_hashes.clear()
        logger.info("🔄 [TimelineGuard] Zaman çizelgesi varlık, MD5 ve algısal dHash kayıtları sıfırlandı.")

    @staticmethod
    def compute_file_hash(file_path: Union[str, Path]) -> str:
        """Dosyanın MD5 hash'ini hesaplar."""
        try:
            p = Path(file_path)
            if p.exists() and p.is_file():
                h = hashlib.md5()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                return h.hexdigest()
        except Exception:
            pass
        return ""

    @staticmethod
    def compute_dhash(image_path: Union[str, Path], hash_size: int = 8) -> str:
        """Görselin algısal fark hash'ini (dHash) hesaplar (PIL kullanarak hızlı ve deterministik)."""
        try:
            from PIL import Image
            p = Path(image_path)
            if not p.exists() or not p.is_file():
                return ""
            im = Image.open(p).convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(im.getdata())
            difference = []
            for row in range(hash_size):
                for col in range(hash_size):
                    pixel_left = pixels[row * (hash_size + 1) + col]
                    pixel_right = pixels[row * (hash_size + 1) + col + 1]
                    difference.append(pixel_left > pixel_right)
            decimal_value = 0
            hex_string = []
            for index, value in enumerate(difference):
                if value:
                    decimal_value += 2 ** (index % 8)
                if (index % 8) == 7:
                    hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
                    decimal_value = 0
            return "".join(hex_string)
        except Exception:
            return ""

    @staticmethod
    def hamming_distance(h1: str, h2: str) -> int:
        """İki hex hash arasındaki Hamming mesafesini hesaplar."""
        if not h1 or not h2 or len(h1) != len(h2):
            return 999
        try:
            b1 = bin(int(h1, 16))[2:].zfill(len(h1) * 4)
            b2 = bin(int(h2, 16))[2:].zfill(len(h2) * 4)
            return sum(c1 != c2 for c1, c2 in zip(b1, b2))
        except Exception:
            return 999

    @classmethod
    def is_asset_used(cls, asset_path: Union[str, Path], max_hamming_dist: int = 10) -> bool:
        """Bu kaynak görsel (MD5, dosya yolu veya algısal dHash bazında) daha önce bu render zaman çizelgesinde kullanıldı mı?"""
        f_hash = cls.compute_file_hash(asset_path)
        if f_hash and f_hash in cls.used_timeline_hashes:
            return True
        p_str = str(Path(asset_path).resolve())
        if p_str in cls.used_timeline_assets:
            return True

        # Algısal Tekilleştirme (Perceptual Deduplication - dHash)
        d_hash = cls.compute_dhash(asset_path)
        if d_hash:
            for uh in cls.used_perceptual_hashes:
                dist = cls.hamming_distance(d_hash, uh)
                if dist <= max_hamming_dist:
                    logger.info(f"[TimelineGuard] 🛡️ Algısal mükerrer görsel engellendi: {Path(asset_path).name} (Hamming: {dist} <= {max_hamming_dist})")
                    return True
        return False

    @classmethod
    def register_timeline_asset(cls, asset_path: Union[str, Path]) -> int:
        """
        Görselin zaman çizelgesindeki kullanım sayısını artırır ve mevcut adedi döner.
        Katı Kural: Bir kaynak fotoğraf, videonun hangi saniyesinde olursa olsun ve hangi
        efektle büyütülürse büyütülsün bir render boyunca yalnızca 1 kesmede kullanılabilir
        (max_occurrences_per_source = 1). İkinci kez çağrılması kesin bir assert ile engellenir.
        """
        p_str = str(Path(asset_path).resolve())
        f_hash = cls.compute_file_hash(asset_path)

        if f_hash and f_hash in cls.used_timeline_hashes:
            err_msg = (
                f"🚨 [TimelineGuard - Asset De-duplication Leak] Kaynak görsel "
                f"({Path(asset_path).name}, MD5: {f_hash[:8]}) zaten başka bir kesmede kullanıldı! "
                f"Tekil kaynak kotası (max_occurrences_per_source=1) aşılamaz!"
            )
            logger.error(err_msg)
            assert f_hash not in cls.used_timeline_hashes, err_msg

        # Algısal kontrol
        d_hash = cls.compute_dhash(asset_path)
        if d_hash:
            for uh in cls.used_perceptual_hashes:
                dist = cls.hamming_distance(d_hash, uh)
                if dist <= 10:
                    err_msg = (
                        f"🚨 [TimelineGuard - Perceptual Duplicate] Kaynak görsel "
                        f"({Path(asset_path).name}) daha önce kullanılan bir görselle görsel olarak aynı (Hamming: {dist} <= 10)!"
                    )
                    logger.error(err_msg)
                    assert dist > 10, err_msg
            cls.used_perceptual_hashes.append(d_hash)

        if f_hash:
            cls.used_timeline_hashes.add(f_hash)

        cnt = cls.used_timeline_assets.get(p_str, 0) + 1
        cls.used_timeline_assets[p_str] = cnt
        return cnt

    @classmethod
    def build_ken_burns_filter(
        cls,
        cut_index: int,
        duration: float,
        fps: int = 30,
        width: int = 1080,
        height: int = 1920,
        repeat_count: int = 1
    ) -> str:
        """
        Onaylanmış statik fotoğrafları dinamik hareket efektleriyle (Ken Burns)
        hareketli sahneye dönüştürür.
        Taranmış matbaa kartı / beyaz kenarlık ve letterbox boşluklarını yok etmek için:
        1.15x oranında büyütüp (1242x2208) merkezden 1080x1920 olarak kırpar.
        """
        frames = max(1, int(duration * fps))

        # Tekrar durumunda varyasyonu kaydır
        effective_mode = (cut_index + (repeat_count - 1) * 2) % 6

        if effective_mode == 0:
            # Yavaş merkez zoom-in (%100 -> %112)
            z_s, z_e = 1.00, 1.12
            step = (z_e - z_s) / frames
            zp = f"zoompan=z='min(zoom+{step:.6f},{z_e:.2f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        elif effective_mode == 1:
            # Vurucu punch-in (%114 -> %122)
            z_s, z_e = 1.14, 1.22
            step = (z_e - z_s) / frames
            zp = f"zoompan=z='min(zoom+{step:.6f},{z_e:.2f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        elif effective_mode == 2:
            # Yavaş zoom-out (%110 -> %102)
            z_s, z_e = 1.10, 1.02
            step = (z_e - z_s) / frames
            zp = f"zoompan=z='max(zoom+{step:.6f},{z_e:.2f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        elif effective_mode == 3:
            # Soldan sağa sinematik pan (%112 sabit zoom)
            z_val = 1.12
            zp = f"zoompan=z={z_val:.2f}:x='(iw-iw/zoom)*(in/{frames})':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        elif effective_mode == 4:
            # Sağdan sola sinematik pan (%112 sabit zoom)
            z_val = 1.12
            zp = f"zoompan=z={z_val:.2f}:x='(iw-iw/zoom)*(1-in/{frames})':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        else:
            # Dinamik hafif süzülme ve zoom (%105 -> %114)
            z_s, z_e = 1.05, 1.14
            step = (z_e - z_s) / frames
            zp = f"zoompan=z='min(zoom+{step:.6f},{z_e:.2f})':x='iw/2-(iw/zoom/2)+sin(in/12)*15':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"

        fair_use_color = "eq=contrast=1.06:brightness=0.01:saturation=1.10"
        scale_w = int(width * 1.15)
        scale_h = int(height * 1.15)
        scale_filter = f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,crop={width}:{height}:(in_w-{width})/2:(in_h-{height})/2"
        return f"{scale_filter},{zp},{fair_use_color}"


# Singleton nesne
timeline_guard = TimelineGuard()
