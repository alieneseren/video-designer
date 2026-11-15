"""
Basketball Engine 2.0 - Core Contracts & Verification Rules
============================================================
Zero Loop & Deterministic Timeline Kuralları:
- Her kesme (cut) kesinlikle benzersiz bir varlık (media_path) içermek zorundadır.
- Modulo (%) veya başa sarma döngüsü fiziksel olarak yasaklanmıştır.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional


class MediaType(str, Enum):
    VIDEO_CLIP = "video_clip"
    KEN_BURNS_PHOTO = "ken_burns_photo"


@dataclass
class BasketballCut:
    cut_index: int
    start_time: float
    end_time: float
    duration: float
    media_path: str
    media_type: MediaType
    target_subject: str
    action_notes: str = ""

    def validate(self):
        p = Path(self.media_path)
        if not p.exists():
            raise FileNotFoundError(f"Kesme #{self.cut_index} için dosya bulunamadı: {self.media_path}")
        if p.stat().st_size < 10000:
            raise ValueError(f"Kesme #{self.cut_index} dosyası çok küçük/geçersiz: {self.media_path}")


@dataclass
class BasketballRenderSpec:
    job_id: str
    channel_id: str
    topic: str
    athlete_name: str
    audio_path: str
    sentence_boundaries: List[Dict[str, Any]]
    cuts: List[BasketballCut]
    category_badge_text: str = "SPORTS SCIENCE"
    category_badge_duration: float = 4.0  # Tam 4. saniyede fade-out ile kaybolur
    cta_display_duration: float = 2.0

    def validate_strict_zero_loop(self):
        """
        ZORUNLU KONTROL: Tekillik ve Döngüsüzlük Denetimi
        Tüm kesmelerin varlık yolları (media_path) benzersiz olmak zorundadır.
        """
        used_paths = [c.media_path for c in self.cuts]
        unique_paths = set(used_paths)
        if len(unique_paths) != len(used_paths):
            duplicates = [p for p in unique_paths if used_paths.count(p) > 1]
            raise ValueError(
                f"🚨 [Zero Loop Violation] Varlık tekrarı tespit edildi! "
                f"Toplam kesme: {len(used_paths)}, Tekil varlık: {len(unique_paths)}. "
                f"Tekrar eden dosyalar: {duplicates}"
            )

        for cut in self.cuts:
            cut.validate()
