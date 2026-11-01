"""
ass_subtitle.py
===============

ASS (Advanced SubStation Alpha) format altyazı üretici.

Neden ASS?
- MP4'e hard-burn yerine ayrı katman olarak yazılır (ffmpeg subtitles filter).
- Animasyon, font, renk, outline, position hepsi kontrol edilebilir.
- Video edit sistemi ASS üzerinden tam kontrol sağlar.

Desteklenen özellikler:
- Çoklu stil (presets): "minimal", "bold", "tiktok", "youtube-classic", "news"
- Animasyon tipleri: "none", "fade", "pop", "typewriter", "word-highlight"
- Position: "bottom", "center", "top" + manuel margin
- Alignment V4+ ASS standardı
- Kelime-kelime zamanlama (boundary'den türetilmiş)
- Otomatik font yolu keşfi (macOS, Linux, Windows)

Üretim akışı:
    captions = [(text, start_sec, end_sec), ...]
    ass = ASSWriter(width=1920, height=1080, style="tiktok", animation="word-highlight")
    ass_path = ass.write(captions, "out.ass")
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


# ──────────────────────────────────────────
# Font keşfi
# ──────────────────────────────────────────

FONT_CANDIDATES = [
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def discover_font(bold: bool = True) -> str:
    """Sistemdeki uygun fontu bulur, yoksa 'Arial' döner (ffmpeg'in bildiği isim)."""
    for fp in FONT_CANDIDATES:
        if os.path.exists(fp):
            if bold and "Bold" not in fp and "bold" not in fp.lower():
                continue
            return fp
    # Fallback: ilk bulunan
    for fp in FONT_CANDIDATES:
        if os.path.exists(fp):
            return fp
    return "Arial"


# ──────────────────────────────────────────
# Stil preset'leri
# ──────────────────────────────────────────

@dataclass
class SubtitleStyle:
    """ASS stilleri için ortak parametreler."""
    name: str
    font: str
    font_size: int
    primary_color: str        # ASS &HAABBGGRR
    secondary_color: str
    outline_color: str
    back_color: str
    outline: float
    shadow: float
    bold: bool
    italic: bool
    alignment: int           # ASS numpad: 1-3 alt, 4-6 orta, 7-9 üst
    margin_v: int
    margin_l: int
    margin_r: int


# ASS Alignment (numpad):
# 7 8 9 (top)
# 4 5 6 (middle)
# 1 2 3 (bottom)
# 2 = bottom-center
# 5 = middle-center
# 8 = top-center

PRESETS: dict[str, SubtitleStyle] = {
    "minimal": SubtitleStyle(
        name="minimal",
        font="Arial",
        font_size=44,
        primary_color="&H00FFFFFF",     # beyaz
        secondary_color="&H000000FF",   # mavi (highlight için)
        outline_color="&H00000000",
        back_color="&H00000000",
        outline=2.0,
        shadow=0.0,
        bold=False,
        italic=False,
        alignment=2,
        margin_v=80,
        margin_l=40,
        margin_r=40,
    ),
    "bold": SubtitleStyle(
        name="bold",
        font="Arial",
        font_size=56,
        primary_color="&H0000FFFF",     # sarı
        secondary_color="&H000000FF",
        outline_color="&H00000000",
        back_color="&H00000000",
        outline=4.0,
        shadow=1.0,
        bold=True,
        italic=False,
        alignment=2,
        margin_v=110,
        margin_l=40,
        margin_r=40,
    ),
    "tiktok": SubtitleStyle(
        name="tiktok",
        font="Arial",
        font_size=68,
        primary_color="&H00FFFFFF",
        secondary_color="&H0000FFFF",   # sarı highlight
        outline_color="&H00000000",
        back_color="&H00000000",
        outline=6.0,
        shadow=3.0,
        bold=True,
        italic=False,
        alignment=5,                    # 5 = Tam Orta (Middle-Center)
        margin_v=0,
        margin_l=60,
        margin_r=60,
    ),
    "youtube-classic": SubtitleStyle(
        name="youtube-classic",
        font="Arial",
        font_size=46,
        primary_color="&H00FFFFFF",
        secondary_color="&H00FFFFFF",
        outline_color="&H00000000",
        back_color="&H99000000",         # yarı saydam kara kutu
        outline=0.0,
        shadow=0.0,
        bold=False,
        italic=False,
        alignment=2,
        margin_v=60,
        margin_l=40,
        margin_r=40,
    ),
    "news": SubtitleStyle(
        name="news",
        font="Arial",
        font_size=42,
        primary_color="&H00FFFFFF",
        secondary_color="&H00FFFFFF",
        outline_color="&H00000000",
        back_color="&HCC000000",
        outline=0.0,
        shadow=0.0,
        bold=False,
        italic=False,
        alignment=5,  # orta
        margin_v=40,
        margin_l=40,
        margin_r=40,
    ),
}


# ──────────────────────────────────────────
# Animasyon tipleri
# ──────────────────────────────────────────
# "none"      → statik
# "fade"      → fade in/out (alpha animasyonu)
# "pop"       → küçükten büyüğe (scale animasyonu)
# "typewriter"→ kelime kelime yaz
# "word-highlight" → aktif kelime sarı, diğerleri beyaz

# ──────────────────────────────────────────
# ASS başlık / yardımcılar
# ──────────────────────────────────────────

def _ass_color(rgb_or_ass: str) -> str:
    """ASS rengi zaten &H.. formatında ise olduğu gibi döner."""
    if rgb_or_ass.startswith("&H"):
        return rgb_or_ass
    return f"&H00{rgb_or_ass.upper()}"


def _format_ts(seconds: float) -> str:
    """Saniyeyi ASS 'H:MM:SS.cs' (centisecond) formatına çevirir."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    cs = int(round((s - int(s)) * 100))
    s_int = int(s)
    if cs == 100:
        cs = 0
        s_int += 1
    return f"{h}:{m:02d}:{s_int:02d}.{cs:02d}"


def _escape_ass_text(text: str) -> str:
    """ASS formatı için özel karakterleri kaçışlar, imleç kaçaklarını (|) ve bilinen AI transkript hatalarını temizler."""
    t = re.sub(r"[|`_~]", "", text)
    t = re.sub(r"\bdaikon\b", "Dikembe", t, flags=re.IGNORECASE)
    t = re.sub(r"\bdaikon mutombo\b", "Dikembe Mutombo", t, flags=re.IGNORECASE)
    return t.replace("\\", "\\\\").replace("\n", "\\N").replace("\r", "")


# ──────────────────────────────────────────
# Caption modeli
# ──────────────────────────────────────────

@dataclass
class Caption:
    """Tek bir altyazı satırı."""
    text: str
    start: float          # saniye
    end: float            # saniye
    # İsteğe bağlı: kelime bazlı zamanlama
    words: list[tuple[str, float, float]] = field(default_factory=list)
    # [(word, word_start, word_end), ...]


# ──────────────────────────────────────────
# ASSWriter Sınıfı
# ──────────────────────────────────────────

class ASSWriter:
    """
    ASS altyazı dosyası üretir.

    Kullanım:
        writer = ASSWriter(width=1920, height=1080, preset="tiktok",
                           animation="word-highlight", shorts_mode=False)
        ass_path = writer.write(captions, "out.ass")
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        preset: str = "bold",
        animation: str = "fade",
        shorts_mode: bool = False,
        font_override: Optional[str] = None,
    ):
        self.width = width
        self.height = height
        self.shorts_mode = shorts_mode
        # Shorts'ta margin'leri biraz arttır
        style = PRESETS.get(preset, PRESETS["bold"])
        # dataclass kopyası
        self.style = SubtitleStyle(**{**style.__dict__})
        if font_override:
            self.style.font = font_override
        # Shorts için boyut/margin ayarı
        if shorts_mode:
            self.style.font_size = int(self.style.font_size * 1.20)
            if self.style.alignment != 5:
                self.style.margin_v = max(480, int(self.style.margin_v * 3.5))
                self.style.margin_l = max(120, int(self.style.margin_l * 3.0))
                self.style.margin_r = max(120, int(self.style.margin_r * 3.0))
            else:
                self.style.margin_v = 0
                self.style.margin_l = 60
                self.style.margin_r = 60
        self.animation = animation if animation in (
            "none", "fade", "pop", "typewriter", "word-highlight"
        ) else "fade"

    # ── Stil bloğu ───────────────────────────────────────────

    def _style_line(self) -> str:
        s = self.style
        bold = -1 if s.bold else 0
        italic = -1 if s.italic else 0
        return (
            f"Style: {s.name},{s.font},{s.font_size},"
            f"{s.primary_color},{s.secondary_color},{s.outline_color},{s.back_color},"
            f"{bold},{italic},0,0,100,100,0,0,1,{s.outline},{s.shadow},"
            f"{s.alignment},{s.margin_l},{s.margin_r},{s.margin_v},1"
        )

    def _header(self) -> str:
        return (
            "[Script Info]\n"
            "; Generated by yt-oto-video pipeline\n"
            "ScriptType: v4.00+\n"
            "WrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n"
            "YCbCr Matrix: TV.709\n"
            f"PlayResX: {self.width}\n"
            f"PlayResY: {self.height}\n"
            "\n"
            "[V4+ Styles]\n"
            f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            f"OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            f"ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            f"Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"{self._style_line()}\n"
            "\n"
            "[Events]\n"
            f"Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
            f"Effect, Text\n"
        )

    # ── Event üretimi ────────────────────────────────────────

    def _event_for_caption(self, idx: int, cap: Caption) -> str:
        start = _format_ts(cap.start)
        end = _format_ts(cap.end)
        anim = self.animation

        if anim == "none":
            text = _escape_ass_text(cap.text)
            return f"Dialogue: 0,{start},{end},{self.style.name},,0,0,0,,{text}"

        if anim == "fade":
            # \fad(duration_ms_in, duration_ms_out)
            # Toplam süreye göre 250ms in/out
            dur_ms = max(150, int((cap.end - cap.start) * 1000 / 4))
            text = _escape_ass_text(cap.text)
            return (
                f"Dialogue: 0,{start},{end},{self.style.name},,0,0,0,,"
                f"{{\\fad({dur_ms},{dur_ms})}}{text}"
            )

        if anim == "pop":
            # \fscx/fscy 0→100 pop-in, 100→0 pop-out
            # \t(tag1,tag2,...) ile zamanlı animasyon
            dur_ms = max(120, int((cap.end - cap.start) * 1000 / 5))
            text = _escape_ass_text(cap.text)
            return (
                f"Dialogue: 0,{start},{end},{self.style.name},,0,0,0,,"
                f"{{\\fscx70\\fscy70\\t(0,{dur_ms},\\fscx100\\fscy100)}}"
                f"{text}"
            )

        if anim == "typewriter":
            # Kelime kelime yaz: \t(start,start+δ,\alpha) kullanarak ardışık opacity
            return self._event_typewriter(cap)

        if anim == "word-highlight":
            # Aktif kelime renk değiştirir; \t ile tag değişimi
            return self._event_word_highlight(cap)

        return f"Dialogue: 0,{start},{end},{self.style.name},,0,0,0,,{_escape_ass_ass_text_safe(cap.text)}"  # fallback

    def _ensure_words(self, cap: Caption) -> list[tuple[str, float, float]]:
        """Caption'da words yoksa otomatik türet (eşit bölüşüm)."""
        if cap.words:
            return cap.words
        words = cap.text.split()
        if not words:
            return []
        total = cap.end - cap.start
        per = total / len(words)
        return [(w, cap.start + i * per, cap.start + (i + 1) * per) for i, w in enumerate(words)]

    def _event_typewriter(self, cap: Caption) -> str:
        words = self._ensure_words(cap)
        if not words:
            return f"Dialogue: 0,{_format_ts(cap.start)},{_format_ts(cap.end)},{self.style.name},,0,0,0,,{_escape_ass_text(cap.text)}"
        # Her kelime için ayrı Dialogue eventi, alpha 0→1 animasyonuyla
        events = []
        for w, ws, we in words:
            # Kelime gözükme süresi: 80ms
            fade = 80
            # Bu kelime görünürken sonraki kelime henüz görünmesin
            # \alpha &HFF görünmez, \alpha &H00 görünür
            # Animasyon: \fad(80, 0)
            text = _escape_ass_text(w)
            events.append(
                f"Dialogue: 0,{_format_ts(ws)},{_format_ts(we)},{self.style.name},,0,0,0,,"
                f"{{\\fad({fade},0)}}{text}"
            )
        return "\n".join(events)

    def _analyze_word_emphasis(self, word: str) -> tuple[str, int, str]:
        """
        Casper AI: Kelime duygu ve vurgu analizi.
        Döner: (ass_color, scale_percent, emoji_suffix)
        """
        import re
        w_low = word.lower()

        # 1. Şok, Ünlem ve Dramatik Vurgular (Kırmızı / Mercan rengi + %135 Pop + Şok Emojisi)
        if re.search(r'(!+|\b(valla|vallahi|delirtme|delirdin|çüş|yuh|nolur|imdat|şaka|şok|şaşırdım|asla|oha|lan|bırak|yok|hayır|yalan|eyvah)\b)', w_low):
            emoji = "😱" if "şaşır" in w_low or "şok" in w_low or "valla" in w_low else ("🔥" if "!" in w_low else "💥")
            return ("&H003333FF&", 135, emoji)  # ASS BGR format: Kırmızı/Mercan

        # 2. Para, Sayı ve Fiyat Vurguları (Neon Zümrüt Yeşili + %130 Pop + Para Emojisi)
        if re.search(r'(\b\d+([.,]\d+)?\b|\b(lira|tl|para|euro|dolar|milyon|bin|kuruş|maaş|borç|hesap)\b)', w_low):
            return ("&H0000FF00&", 130, "💸")  # ASS BGR: Parlak Yeşil

        # 3. Kahkaha ve Komedi Vurguları (Canlı Altın Sarısı + %125 Pop + Gülen Emoji)
        if re.search(r'(\b(haha|hahaha|sjsj|komik|gülme|kahkaha|şakacı|espri)\b)', w_low):
            return ("&H0000D7FF&", 125, "😂")  # ASS BGR: Altın Sarısı

        # 4. Soru ve Merak Vurguları (Elektrik Camgöbeği Cyan + %125 Pop + Düşünme Emojisi)
        if re.search(r'(\?+|\b(nasıl|neden|niye|ne|kim|nerede|kaç|gerçekten|ciddi|misin|musun|mı|mi)\b)', w_low):
            return ("&H00FFFF00&", 125, "🤔")  # ASS BGR: Cyan

        # Standart kelime (Varsayılan secondary renk)
        return (self.style.secondary_color, 115, "")

    def _event_word_highlight(self, cap: Caption) -> str:
        """
        Casper AI: Dinamik Kelime Vurgusu & Emojili Karakter Balonları Modu.
        Seslendirmede söylenen her kilit kelimeyi (valla, 200 lira, delirtme)
        anlık renk değişimi, büyüyen pop efekti ve duruma uygun emojilerle vurgular.
        """
        words = self._ensure_words(cap)
        if not words:
            return f"Dialogue: 0,{_format_ts(cap.start)},{_format_ts(cap.end)},{self.style.name},,0,0,0,,{_escape_ass_text(cap.text)}"

        events = []
        for w, ws, we in words:
            w_clean = _escape_ass_text(w).strip()
            if not w_clean:
                continue

            color, scale, emoji = self._analyze_word_emphasis(w_clean)
            display_word = f"{w_clean} {emoji}".strip() if emoji else w_clean
            dur_ms = max(60, min(180, int((we - ws) * 1000 / 3)))

            # ASS dinamik tag: Başlangıçta %100 -> dur_ms sürede %scale pop-in
            line_text = f"{{\\c{color}\\fscx100\\fscy100\\t(0,{dur_ms},\\fscx{scale}\\fscy{scale})}}{display_word}"
            events.append(
                f"Dialogue: 0,{_format_ts(ws)},{_format_ts(we)},{self.style.name},,0,0,0,,{line_text}"
            )
        return "\n".join(events)

    # ── Public API ───────────────────────────────────────────

    def write(self, captions: Iterable[Caption], output_path: str) -> str:
        """
        Caption listesini ASS dosyasına yazar ve dosya yolunu döner.
        """
        captions = list(captions)
        # Boş/geçersiz caption'ları filtrele
        captions = [
            c for c in captions
            if c.text and c.text.strip() and c.end > c.start
        ]

        header = self._header()
        events = [self._event_for_caption(i, c) for i, c in enumerate(captions)]
        content = header + "\n".join(events) + "\n"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content, encoding="utf-8")
        return output_path


def _escape_ass_ass_text_safe(text: str) -> str:
    """_escape_ass_text için alias — typing hatası koruması."""
    return _escape_ass_text(text)


# ──────────────────────────────────────────
# Yardımcı: caption listesini boundary'lerden üret
# ──────────────────────────────────────────

def captions_from_boundaries(
    boundaries: list[dict],
    split_max_words: int = 6,
) -> list[Caption]:
    """
    Edge-TTS SentenceBoundary listesinden, mevcut _split_text_and_duration
    mantığını koruyarak Caption listesi üretir.
    """
    captions: list[Caption] = []
    for b in boundaries:
        text = (b.get("text") or "").strip()
        if not text:
            continue
        start = float(b.get("offset", 0.0))
        duration = float(b.get("duration", 0.0))
        end = start + duration
        if end <= start:
            continue
        # Kelime bazlı böl
        words = text.split()
        if len(words) <= split_max_words:
            captions.append(Caption(text=text, start=start, end=end))
        else:
            # Eşit süre dilimlerine böl
            n = (len(words) + split_max_words - 1) // split_max_words
            per = duration / n
            for i in range(n):
                chunk_words = words[i * split_max_words : (i + 1) * split_max_words]
                if not chunk_words:
                    continue
                cs = start + i * per
                ce = start + (i + 1) * per if i + 1 < n else end
                captions.append(Caption(
                    text=" ".join(chunk_words),
                    start=cs,
                    end=ce,
                ))
    return captions


def captions_from_timed_words(
    words_with_times: list[tuple[str, float, float]],
    max_per_caption: int = 6,
) -> list[Caption]:
    """
    Kelime bazlı zamanlama verisi varsa (Whisper/forced alignment çıktısı gibi),
    bunları Caption'lara gruplar.
    """
    captions = []
    if not words_with_times:
        return captions
    cur: list[tuple[str, float, float]] = []
    for w, ws, we in words_with_times:
        cur.append((w, ws, we))
        if len(cur) >= max_per_caption:
            text = " ".join(c[0] for c in cur)
            captions.append(Caption(
                text=text,
                start=cur[0][1],
                end=cur[-1][2],
                words=list(cur),
            ))
            cur = []
    if cur:
        text = " ".join(c[0] for c in cur)
        captions.append(Caption(
            text=text,
            start=cur[0][1],
            end=cur[-1][2],
            words=list(cur),
        ))
    return captions
