"""
Turkish Text Normalization & Number-to-Words Engine
===================================================
Converts digits, decimals, ordinals, time, percentages, currencies,
and common abbreviations into natural, phonetically accurate Turkish text
to prevent TTS / Chatterbox pronunciation glitches.
"""

import re
from typing import Optional

ONES = ['', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz']
TENS = ['', 'on', 'yirmi', 'otuz', 'kırk', 'elli', 'altmış', 'yetmiş', 'seksen', 'doksan']

ORDINALS_MAP = {
    'sıfır': 'sıfırıncı',
    'bir': 'birinci',
    'iki': 'ikinci',
    'üç': 'üçüncü',
    'dört': 'dördüncü',
    'beş': 'beşinci',
    'altı': 'altıncı',
    'yedi': 'yedinci',
    'sekiz': 'sekizinci',
    'dokuz': 'dokuzuncu',
    'on': 'onuncu',
    'yirmi': 'yirminci',
    'otuz': 'otuzuncu',
    'kırk': 'kırkıncı',
    'elli': 'ellinci',
    'altmış': 'altmışıncı',
    'yetmiş': 'yetmişinci',
    'seksen': 'sekseninci',
    'doksan': 'doksanıncı',
    'yüz': 'yüzüncü',
    'bin': 'bininci',
    'milyon': 'milyonuncu',
    'milyar': 'milyaruncu',
}


def int_to_words_tr(n: int) -> str:
    """Tam sayıları Türkçe okunuşlarına çevirir."""
    if n == 0:
        return "sıfır"
    if n < 0:
        return "eksi " + int_to_words_tr(-n)

    def chunk_to_words(c: int) -> str:
        parts = []
        h = c // 100
        t = (c % 100) // 10
        o = c % 10
        if h == 1:
            parts.append("yüz")
        elif h > 1:
            parts.append(ONES[h] + " yüz")
        if t > 0:
            parts.append(TENS[t])
        if o > 0:
            parts.append(ONES[o])
        return " ".join(parts)

    parts = []

    # Trilyon
    trillions = n // 1_000_000_000_000
    if trillions > 0:
        if trillions == 1:
            parts.append("bir trilyon")
        else:
            parts.append(chunk_to_words(trillions) + " trilyon")
        n %= 1_000_000_000_000

    # Milyar
    billions = n // 1_000_000_000
    if billions > 0:
        if billions == 1:
            parts.append("bir milyar")
        else:
            parts.append(chunk_to_words(billions) + " milyar")
        n %= 1_000_000_000

    # Milyon
    millions = n // 1_000_000
    if millions > 0:
        if millions == 1:
            parts.append("bir milyon")
        else:
            parts.append(chunk_to_words(millions) + " milyon")
        n %= 1_000_000

    # Bin (1000 için 'bir bin' denmez, sadece 'bin' denir)
    thousands = n // 1_000
    if thousands > 0:
        if thousands == 1:
            parts.append("bin")
        else:
            parts.append(chunk_to_words(thousands) + " bin")
        n %= 1_000

    # 1 - 999 arası
    if n > 0:
        parts.append(chunk_to_words(n))

    return " ".join(parts).strip()


def ordinal_to_words_tr(n: int) -> str:
    """Sıra sayılarını (1. -> birinci, 2. -> ikinci vb.) Türkçe okunuşlarına çevirir."""
    base_words = int_to_words_tr(n).split()
    if not base_words:
        return "sıfırıncı"
    last_word = base_words[-1]
    if last_word in ORDINALS_MAP:
        base_words[-1] = ORDINALS_MAP[last_word]
    else:
        last_char = last_word[-1]
        vowels = [ch for ch in last_word if ch in 'aeıioöuü']
        last_vowel = vowels[-1] if vowels else 'i'
        if last_char in 'aeıioöuü':
            if last_vowel in 'aı': base_words[-1] += 'ncı'
            elif last_vowel in 'ei': base_words[-1] += 'nci'
            elif last_vowel in 'ou': base_words[-1] += 'ncu'
            elif last_vowel in 'öü': base_words[-1] += 'ncü'
        else:
            if last_vowel in 'aı': base_words[-1] += 'ıncı'
            elif last_vowel in 'ei': base_words[-1] += 'inci'
            elif last_vowel in 'ou': base_words[-1] += 'uncu'
            elif last_vowel in 'öü': base_words[-1] += 'üncü'
    return " ".join(base_words)


def decimal_to_words_tr(num_str: str) -> str:
    """Ondalıklı sayıları Türkçe konuşma diline çevirir (1.5 -> bir buçuk)."""
    s = num_str.replace(",", ".")
    if "." not in s:
        try:
            return int_to_words_tr(int(s))
        except ValueError:
            return s
    whole_s, dec_s = s.split(".", 1)
    whole = int(whole_s) if whole_s else 0
    if dec_s == "5":
        if whole == 0:
            return "sıfır virgül beş"
        elif whole == 1:
            return "bir buçuk"
        else:
            return f"{int_to_words_tr(whole)} buçuk"
    try:
        dec_val = int(dec_s)
        return f"{int_to_words_tr(whole)} virgül {int_to_words_tr(dec_val)}"
    except ValueError:
        return s


def normalize_turkish_tts_text(text: str) -> str:
    """
    Türkçe seslendirme (TTS / Chatterbox) öncesi metni doğallaştırır:
    - Yılları ve sayıları yazıya döker (2026 -> iki bin yirmi altı)
    - Kesme işaretli ekleri bağlar (2026'da -> iki bin yirmi altıda)
    - Saatleri okur (14:30 -> on dört otuz)
    - Yüzdeleri dönüştürür (%50 -> yüzde elli)
    - Yaygın kısaltmaları açar (vb. -> ve benzeri, dk -> dakika)
    - Para ve ölçü birimlerini seslendirir (100 TL -> yüz Türk lirası, 5 kg -> beş kilo)
    - Noktalı sıra sayılarını çözer (3. kat -> üçüncü kat)
    """
    if not text:
        return ""

    res = text

    # 0. Türkçe Harf ve Kelime Bitişmesi Düzeltmeleri (Büyük I -> ı, İ -> i)
    # Python varsayılan Unicode lower() işleminde 'I' harfi 'i'ye döner.
    # Bu durum 'SIKIŞTIM' -> 'sikiştim' gibi telaffuz ve anlam kayması/argo hatalarına yol açar.
    # Bitişik yazılan şifre/mors kelimelerini ('AŞAĞIDASIKIŞTIM') ve 'SIKIŞ*' türevlerini kesin olarak koruruz:
    res = re.sub(r'\bAŞAĞIDA\s*SIKIŞTIM\b', 'aşağıda sıkıştım', res, flags=re.IGNORECASE)
    res = re.sub(r'AŞAĞIDASIKIŞTIM', 'aşağıda sıkıştım', res, flags=re.IGNORECASE)
    res = re.sub(r'aşağıdasıkıştım', 'aşağıda sıkıştım', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSIKIŞTIM\b', 'sıkıştım', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSIKIŞTI\b', 'sıkıştı', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSIKIŞTIK\b', 'sıkıştık', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSIKIŞAN\b', 'sıkışan', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSIKIŞMIŞ\b', 'sıkışmış', res, flags=re.IGNORECASE)

    # Genel büyük harfli Türkçe kelimelerde 'I' harfinin yanlışlıkla 'i'ye dönmesini önle:
    def fix_turkish_uppercase_i(match):
        word = match.group(0)
        if 'I' in word:
            return word.replace('I', 'ı').replace('İ', 'i').lower()
        return word

    res = re.sub(r'\b[A-ZÇĞİÖŞÜ]{2,}\b', fix_turkish_uppercase_i, res)

    # 1. Kısaltmalar
    abbrev_map = [
        (r'\bvb\.', 've benzeri'),
        (r'\bvs\.', 've saire'),
        (r'\bbkz\.', 'bakınız'),
        (r'\bör\.', 'örneğin'),
        (r'\bNo[:.]?\s*(\d+)', r'numara \1'),
        (r'\bkm/s\b', 'kilometre bölü saat'),
        (r'\bkm/h\b', 'kilometre bölü saat'),
        (r'\bm²\b', 'metrekare'),
        (r'\bm³\b', 'metreküp'),
    ]
    for pattern, replacement in abbrev_map:
        res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)

    # 2. Saatler + ekler: 14:30'da -> on dört otuzda, 09:05 -> dokuz sıfır beş
    def repl_time_suffix(m):
        hh = int(m.group(1))
        mm = int(m.group(2))
        suf = (m.group(3) or '').lower()
        h_str = int_to_words_tr(hh)
        if mm == 0:
            m_str = ''
        elif mm < 10:
            m_str = f"sıfır {int_to_words_tr(mm)}"
        elif mm == 30:
            m_str = "otuz"
        else:
            m_str = int_to_words_tr(mm)
        base = f"{h_str} {m_str}".strip()
        if suf:
            words = base.split()
            words[-1] = words[-1] + suf
            return " ".join(words)
        return base
    res = re.sub(r'\b([01]?\d|2[0-3]):([0-5]\d)(?:[\'’]([a-zA-ZçğıöşüÇĞİÖŞÜ]+))?\b', repl_time_suffix, res)

    # 3. Yüzdeler: %50, % 25, %1.5
    res = re.sub(r'%\s*(\d+(?:[.,]\d+)?)', lambda m: 'yüzde ' + decimal_to_words_tr(m.group(1).strip()), res)

    # 4. Para Birimleri: 100 TL, 50₺, $50, 50$, 50€
    res = re.sub(r'(\d+(?:[.,]\d+)?)\s*(?:TL|tl|₺)', r'\1 Türk lirası', res)
    res = re.sub(r'(?:₺)\s*(\d+(?:[.,]\d+)?)', r'\1 Türk lirası', res)
    res = re.sub(r'[\$]\s*(\d+(?:[.,]\d+)?)', r'\1 dolar', res)
    res = re.sub(r'(\d+(?:[.,]\d+)?)\s*[\$]', r'\1 dolar', res)
    res = re.sub(r'[€]\s*(\d+(?:[.,]\d+)?)', r'\1 euro', res)
    res = re.sub(r'(\d+(?:[.,]\d+)?)\s*[€]', r'\1 euro', res)

    # 5. Ölçü Birimleri
    unit_map = [
        (r'\b(\d+(?:[.,]\d+)?)\s*kg\b', r'\1 kilo'),
        (r'\b(\d+(?:[.,]\d+)?)\s*gr?\b', r'\1 gram'),
        (r'\b(\d+(?:[.,]\d+)?)\s*km\b', r'\1 kilometre'),
        (r'\b(\d+(?:[.,]\d+)?)\s*m\b', r'\1 metre'),
        (r'\b(\d+(?:[.,]\d+)?)\s*cm\b', r'\1 santimetre'),
        (r'\b(\d+(?:[.,]\d+)?)\s*mm\b', r'\1 milimetre'),
        (r'\b(\d+(?:[.,]\d+)?)\s*(?:dk|dak)\.?\b', r'\1 dakika'),
        (r'\b(\d+(?:[.,]\d+)?)\s*(?:sn|san)\.?\b', r'\1 saniye'),
    ]
    for pattern, replacement in unit_map:
        res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)

    # 6. Kesme işaretli sayılar: 2026'da, 2026'ya, 1990'larda, 10'da, 5'inci
    def repl_num_suffix(m):
        try:
            num = int(m.group(1))
            suffix = m.group(2).lower()
            if suffix in ('inci', 'nci', 'ıncı', 'ncı', 'uncu', 'ncu', 'üncü', 'ncü'):
                return ordinal_to_words_tr(num)
            words = int_to_words_tr(num).split()
            if words:
                words[-1] = words[-1] + suffix
                return " ".join(words)
        except Exception:
            pass
        return m.group(0)
    res = re.sub(r'\b(\d+)[\'’]([a-zA-ZçğıöşüÇĞİÖŞÜ]+)\b', repl_num_suffix, res)

    # 7. Sıra sayıları (Noktalı): 3. kat, 1. bölüm, 21. yüzyıl
    def repl_ordinal(m):
        try:
            num = int(m.group(1))
            return ordinal_to_words_tr(num) + ' '
        except Exception:
            return m.group(0)
    res = re.sub(r'\b(\d+)\.\s+(?=[a-zA-ZçğıöşüÇĞİÖŞÜ])', repl_ordinal, res)

    # 8. Binlik ayraçlı büyük sayılar: 10.000, 100.000, 1.000.000
    res = re.sub(r'\b(\d{1,3}(?:\.\d{3})+)\b', lambda m: int_to_words_tr(int(m.group(1).replace('.', ''))), res)

    # 9. Ondalıklı sayılar: 1.5, 2.5, 0.5, 3,14
    res = re.sub(r'\b\d+[.,]\d+\b', lambda m: decimal_to_words_tr(m.group(0)), res)

    # 10. Kalan tüm tam sayılar: 2026, 100, 5, vb.
    res = re.sub(r'\b\d+\b', lambda m: int_to_words_tr(int(m.group(0))), res)

    # 11. Boşlukları düzenle
    res = re.sub(r'\s+', ' ', res).strip()

    return res
