"""
content_planner.py
Kanal başına CSV içerik takvimi yönetir.
- plan_content(): AI ile toplu konu üretir, CSV'ye yazar/günceller
- get_next_unproduced(): Sıradaki üretilmemiş içeriği döndürür
- mark_as_produced(): Satırı üretildi olarak işaretler
- get_plan(): Tüm CSV içeriğini dict listesi olarak döndürür
"""

from __future__ import annotations
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union


PLAN_FILENAME = "icerik_plani.csv"

CSV_FIELDS = [
    "id", "konu", "baslik", "anahtar_kelimeler",
    "olusturulma_tarihi", "uretildi", "uretim_tarihi", "secilen_muzik", "notlar",
    "yuklendi", "yukleme_tarihi", "yayim_tarihi", "video_url"
]


class ContentPlanner:
    def __init__(self, channel_dir: Path):
        """
        channel_dir: output/<channel_id>/ klasörü (yuklenecek ve yuklenen altında değil, doğrudan kanal kök klasörü)
        """
        self.channel_dir = Path(channel_dir)
        self.channel_dir.mkdir(parents=True, exist_ok=True)
        self.plan_path = self.channel_dir / PLAN_FILENAME

    def _read_all(self) -> list[dict]:
        if not self.plan_path.exists():
            return []
        with open(self.plan_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_all(self, rows: list[dict]):
        with open(self.plan_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})

    def get_plan(self) -> list[dict]:
        """Tüm içerik planını döndürür."""
        return self._read_all()

    def add_topics(self, topics: list[dict]) -> list[dict]:
        """
        Yeni konuları mevcut CSV'ye ekler.
        topics: [{"konu": "...", "baslik": "...", "anahtar_kelimeler": ["..."]}, ...]
        Döner: Eklenen satır listesi
        """
        existing = self._read_all()
        max_id = 0
        for r in existing:
            try:
                max_id = max(max_id, int(r.get("id", 0)))
            except (ValueError, TypeError):
                pass
        next_id = max_id + 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_rows = []

        from audio_library import get_recommendation
        for topic in topics:
            keywords = topic.get("anahtar_kelimeler", topic.get("keywords", []))
            if isinstance(keywords, list):
                keywords = ", ".join(keywords)

            konu = topic.get("konu", topic.get("topic", ""))
            baslik = topic.get("baslik", topic.get("title", ""))
            rec_music = get_recommendation(konu, baslik)

            row = {
                "id": str(next_id),
                "konu": konu,
                "baslik": baslik,
                "anahtar_kelimeler": keywords,
                "olusturulma_tarihi": now,
                "uretildi": "Hayır",
                "uretim_tarihi": "",
                "secilen_muzik": rec_music,
                "notlar": topic.get("notlar", ""),
                "yuklendi": "Hayır",
                "yukleme_tarihi": "",
                "yayim_tarihi": "",
                "video_url": "",
            }
            existing.append(row)
            new_rows.append(row)
            next_id += 1

        self._write_all(existing)
        print(f"[PLANNER] {len(new_rows)} yeni konu CSV'ye eklendi: {self.plan_path}")
        return new_rows

    def get_row_by_id(self, row_id: str | int) -> dict | None:
        """Verilen id'li satırı döndürür."""
        rows = self._read_all()
        for row in rows:
            if str(row.get("id", "")).strip() == str(row_id).strip():
                return row
        return None

    def delete_topic(self, row_id: str | int) -> bool:
        """Verilen id'li satırı içerik planından tamamen siler."""
        rows = self._read_all()
        initial_len = len(rows)
        filtered_rows = [r for r in rows if str(r.get("id", "")).strip() != str(row_id).strip()]
        if len(filtered_rows) == initial_len:
            return False
        self._write_all(filtered_rows)
        return True

    def delete_topics(self, row_ids: list[str | int]) -> int:
        """Birden fazla id'li satırı içerik planından tek seferde hızlıca siler."""
        rows = self._read_all()
        initial_len = len(rows)
        row_ids_set = {str(r_id).strip() for r_id in row_ids}
        filtered_rows = [r for r in rows if str(r.get("id", "")).strip() not in row_ids_set]
        deleted_count = initial_len - len(filtered_rows)
        if deleted_count > 0:
            self._write_all(filtered_rows)
        return deleted_count

    def get_next_unproduced(self, exclude_ids: list[str | int] = None) -> dict | None:
        """
        CSV'deki ilk üretilmemiş satırı döndürür.
        exclude_ids verilmişse, o id'lere sahip satırları atlar.
        Tüm satırlar üretilmişse, exclude_ids dışındaki ilk satırdan devam eder (döngüsel plan).
        """
        exclude_set = {str(x).strip() for x in (exclude_ids or []) if str(x).strip()}
        rows = self._read_all()
        # 1. Henüz üretilmemiş satır ara
        for row in rows:
            rid = str(row.get("id", "")).strip()
            if rid in exclude_set:
                continue
            if row.get("uretildi", "Hayır").strip().lower() in ("hayır", "no", "", "false", "0"):
                return row
        # 2. Döngü fallback: Tüm satırlar üretilmişse döngüsel olarak ilk uygun satırı döndür
        for row in rows:
            rid = str(row.get("id", "")).strip()
            if rid in exclude_set:
                continue
            return row
        return None

    def update_row_status(self, row_id: str | int, status: str) -> bool:
        """
        Verilen id'li satırın 'uretildi' durumunu günceller (örn: 'Hazırlandı', 'Sunucuya Hazırlandı', 'Hazır').
        """
        rows = self._read_all()
        found = False
        for row in rows:
            if str(row.get("id", "")).strip() == str(row_id).strip():
                row["uretildi"] = status
                found = True
                break
        if found:
            self._write_all(rows)
            print(f"[PLANNER] Satır #{row_id} durumu güncellendi: {status}")
        return found

    def mark_as_produced(self, row_id: str | int) -> bool:
        """
        Verilen id'li satırı üretildi olarak işaretler.
        Döner: True (başarılı) | False (bulunamadı)
        """
        rows = self._read_all()
        found = False
        for row in rows:
            if str(row.get("id", "")).strip() == str(row_id).strip():
                row["uretildi"] = "Evet"
                row["uretim_tarihi"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                found = True
                break
        if found:
            self._write_all(rows)
            print(f"[PLANNER] Satır #{row_id} üretildi olarak işaretlendi.")
        return found

    def mark_as_uploaded(self, row_id: str | int, yayim_tarihi: str = "", video_url: str = "") -> bool:
        """
        Verilen id'li satırı yüklendi olarak işaretler ve planlanan yayım tarihini yazar.
        Döner: True (başarılı) | False (bulunamadı)
        """
        rows = self._read_all()
        found = False
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in rows:
            if str(row.get("id", "")) == str(row_id):
                row["yuklendi"] = "Evet"
                row["yukleme_tarihi"] = now
                if yayim_tarihi:
                    row["yayim_tarihi"] = yayim_tarihi
                if video_url:
                    row["video_url"] = video_url
                found = True
                break
        if found:
            self._write_all(rows)
            print(f"[PLANNER] Satır #{row_id} yüklendi olarak işaretlendi (Yayım: {yayim_tarihi}).")
        return found

    def update_music(self, row_id: str | int, track_id: str) -> bool:
        """Verilen id'li satırın seçilen müzik alanını günceller."""
        rows = self._read_all()
        found = False
        for row in rows:
            if str(row.get("id", "")) == str(row_id):
                row["secilen_muzik"] = track_id
                found = True
                break
        if found:
            self._write_all(rows)
            print(f"[PLANNER] Satır #{row_id} müziği '{track_id}' olarak güncellendi.")
        return found

    def plan_exists(self) -> bool:
        return self.plan_path.exists()

    def stats(self) -> dict:
        rows = self._read_all()
        total = len(rows)
        produced = sum(
            1 for r in rows
            if r.get("uretildi", "").strip().lower() in ("evet", "yes", "true", "1")
        )
        uploaded = sum(
            1 for r in rows
            if r.get("yuklendi", "").strip().lower() in ("evet", "yes", "true", "1")
        )
        return {
            "total": total,
            "produced": produced,
            "remaining": total - produced,
            "uploaded": uploaded
        }
