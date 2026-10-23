"""
youtube_scheduler.py
Kanal diline ve hedef ülkesine göre akıllı YouTube yayımlama zamanlayıcısı.
Kurallar:
- Kanal dilinin ait olduğu ülkenin yerel saatinde her zaman 19:00 (19:00:00).
- Kanalda hiç planlanmış video yoksa: Bulunduğu günün ertesi günü (Yarın 19:00).
- Kanalda planlanmış video varsa: En son planlanan videonun ertesi günü 19:00.
- Hedef Kitle: Her zaman 'Çocuklara özel değil' (selfDeclaredMadeForKids = False).
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import zoneinfo
import re

LANG_TIMEZONE_MAP = {
    "tr": "Europe/Istanbul",
    "en": "America/New_York",
    "de": "Europe/Berlin",
    "fr": "Europe/Paris",
    "es": "Europe/Madrid",
    "it": "Europe/Rome",
    "pt": "America/Sao_Paulo",
    "ru": "Europe/Moscow",
    "ja": "Asia/Tokyo",
    "ko": "Asia/Seoul",
    "zh": "Asia/Shanghai",
    "ar": "Asia/Riyadh",
    "hi": "Asia/Kolkata",
    "nl": "Europe/Amsterdam",
    "pl": "Europe/Warsaw",
    "sv": "Europe/Stockholm",
    "da": "Europe/Copenhagen",
    "fi": "Europe/Helsinki",
    "no": "Europe/Oslo",
    "cs": "Europe/Prague",
    "hu": "Europe/Budapest",
    "ro": "Europe/Bucharest",
    "uk": "Europe/Kyiv",
    "el": "Europe/Athens",
    "id": "Asia/Jakarta",
    "th": "Asia/Bangkok",
    "vi": "Asia/Ho_Chi_Minh",
    "az": "Asia/Baku",
}


def get_channel_timezone(language: str) -> str:
    """Kanal diline göre hedef ülkenin saat dilimini döndürür."""
    lang_clean = (language or "tr").strip().lower()
    return LANG_TIMEZONE_MAP.get(lang_clean, "Europe/Istanbul")


def parse_date_string(date_str: str) -> datetime | None:
    """Farklı formatlardaki tarih dizgilerini parse eder."""
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    
    # 1. YYYY-MM-DD HH:MM:SS or YYYY-MM-DD HH:MM
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{1,2}))?", s)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        hour = int(match.group(4)) if match.group(4) is not None else 19
        minute = int(match.group(5)) if match.group(5) is not None else 0
        return datetime(year, month, day, hour, minute)

    # 2. DD.MM.YYYY or DD/MM/YYYY
    match = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?:[ T](\d{1,2}):(\d{1,2}))?", s)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        hour = int(match.group(4)) if match.group(4) is not None else 19
        minute = int(match.group(5)) if match.group(5) is not None else 0
        return datetime(year, month, day, hour, minute)

    return None


def get_latest_scheduled_date_from_plan(plan_rows: list[dict]) -> datetime | None:
    """Mevcut içerik planındaki en ileri yayım/yükleme tarihini bulur."""
    latest_dt = None
    for row in (plan_rows or []):
        yayim_str = row.get("yayim_tarihi") or ""
        if yayim_str:
            dt = parse_date_string(yayim_str)
            if dt:
                if latest_dt is None or dt > latest_dt:
                    latest_dt = dt
    return latest_dt


def calculate_channel_next_schedule_slot(
    channel: dict,
    plan_rows: list[dict] | None = None,
    explicit_last_date: datetime | str | None = None
) -> dict:
    """
    Kanal için akıllı yayım tarihi ve saat dilimi yuvasını hesaplar.
    
    Dönüş sözlüğü:
    - target_date_str: "YYYY-MM-DD"
    - target_time_str: "19:00"
    - target_datetime_str: "YYYY-MM-DD 19:00"
    - timezone: "Europe/Istanbul" vs.
    - made_for_kids: False
    """
    lang = (channel.get("language") or "tr").lower()
    tz_name = get_channel_timezone(lang)
    
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = zoneinfo.ZoneInfo("Europe/Istanbul")
        tz_name = "Europe/Istanbul"

    # Hedef ülkenin anlık yerel zamanı
    now_in_tz = datetime.now(tz)
    today_in_tz = now_in_tz.date()
    tomorrow_in_tz = today_in_tz + timedelta(days=1)

    latest_date = None

    # 1. Açıkça verilen son tarih varsa
    if explicit_last_date:
        if isinstance(explicit_last_date, str):
            latest_date = parse_date_string(explicit_last_date)
        elif isinstance(explicit_last_date, datetime):
            latest_date = explicit_last_date

    # 2. Plandan en son yayım tarihini al
    if not latest_date and plan_rows:
        latest_date = get_latest_scheduled_date_from_plan(plan_rows)

    # 3. Tarih kuralı:
    # - Eğer hiç tarih yoksa veya son tarih yarından eskiyse -> Yarın 19:00
    # - Eğer son tarih >= Yarın ise -> Son Tarih + 1 gün 19:00
    if not latest_date or latest_date.date() < tomorrow_in_tz:
        target_date = tomorrow_in_tz
    else:
        target_date = latest_date.date() + timedelta(days=1)

    hour = int(channel.get("schedule_hour") or 19)
    if hour == 9 and ("shorts" in str(channel.get("topic_category", "")) or "whatsapp" in str(channel.get("topic_category", "")) or "yazan" in str(channel.get("channel_id", ""))):
        hour = 19
    minute = 0
    target_date_str = target_date.strftime("%Y-%m-%d")
    target_time_str = f"{hour:02d}:{minute:02d}"
    target_datetime_str = f"{target_date_str} {target_time_str}"
    target_dt = datetime(target_date.year, target_date.month, target_date.day, hour, minute)

    return {
        "channel_id": channel.get("channel_id", ""),
        "channel_name": channel.get("name", ""),
        "language": lang,
        "timezone": tz_name,
        "target_date_str": target_date_str,
        "target_time_str": target_time_str,
        "target_datetime_str": target_datetime_str,
        "schedule_date": target_date_str,
        "schedule_time": target_time_str,
        "schedule_datetime": target_datetime_str,
        "scheduled_datetime": target_dt,
        "latest_date_str": latest_date.strftime("%Y-%m-%d %H:%M") if latest_date else None,
        "made_for_kids": False,
        "display_summary": f"{target_date_str} saat {target_time_str} ({tz_name})",
    }
