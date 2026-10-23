"""
character_rag.py
Karakter ve Kanal Evreni Hafızası (Lore & Memory RAG).
Kanal bazlı tekrarlayan karakterleri, geçmiş hikaye arklarını ve olayları
SQLite + TF-IDF semantik benzerlik ile hafızada tutar ve senaryo motoruna enjekte eder.
"""

from __future__ import annotations
import os
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Proje veri dizini
_BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = _BASE_DIR / "data"
DB_PATH = DATA_DIR / "character_rag.db"


def _get_db() -> sqlite3.Connection:
    """Veritabanı bağlantısı açar ve tabloları oluşturur."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Gerekli tabloları başlatır."""
    with _get_db() as conn:
        cursor = conn.cursor()
        # 1. Karakterler Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL DEFAULT 'global',
                name TEXT NOT NULL,
                role_type TEXT NOT NULL DEFAULT 'amca',
                age INTEGER NOT NULL DEFAULT 45,
                gender TEXT NOT NULL DEFAULT 'male',
                avatar_prompt TEXT,
                personality TEXT,
                catchphrases TEXT, -- JSON Array
                quirks TEXT,
                relationships TEXT,
                is_recurring INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Hikaye ve Olay Hafızası (Lore Memories)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS story_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL DEFAULT 'global',
                title TEXT NOT NULL,
                topic TEXT,
                summary TEXT NOT NULL,
                characters_involved TEXT, -- JSON Array
                key_events TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Otomatik Tablo Güncelleme (Migration: voice_id & pitch_settings)
        cursor.execute("PRAGMA table_info(characters)")
        existing_cols = [c[1] for c in cursor.fetchall()]
        if "voice_id" not in existing_cols:
            cursor.execute("ALTER TABLE characters ADD COLUMN voice_id TEXT DEFAULT ''")
        if "pitch_settings" not in existing_cols:
            cursor.execute("ALTER TABLE characters ADD COLUMN pitch_settings TEXT DEFAULT ''")
        if "avatar_emotions" not in existing_cols:
            cursor.execute("ALTER TABLE characters ADD COLUMN avatar_emotions TEXT DEFAULT '{}'")

        conn.commit()


# Başlangıçta tabloları hazırla
init_db()


class CharacterRAGManager:
    """Karakter ve hikaye evreni RAG yöneticisi."""

    @staticmethod
    def list_characters(channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Kanal veya global karakterleri listeler."""
        with _get_db() as conn:
            cursor = conn.cursor()
            if channel_id and channel_id != "global":
                cursor.execute("""
                    SELECT * FROM characters 
                    WHERE channel_id = ? OR channel_id = 'global'
                    ORDER BY id ASC
                """, (channel_id,))
            else:
                cursor.execute("SELECT * FROM characters ORDER BY id ASC")
            
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["catchphrases"] = json.loads(d["catchphrases"]) if d["catchphrases"] else []
                except Exception:
                    d["catchphrases"] = [d["catchphrases"]] if d["catchphrases"] else []
                try:
                    d["avatar_emotions"] = json.loads(d["avatar_emotions"]) if d.get("avatar_emotions") else {}
                except Exception:
                    d["avatar_emotions"] = {}
                result.append(d)
            return result

    @staticmethod
    def get_character(char_id: int) -> Optional[Dict[str, Any]]:
        """Tek bir karakteri getirir."""
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["catchphrases"] = json.loads(d["catchphrases"]) if d["catchphrases"] else []
            except Exception:
                d["catchphrases"] = [d["catchphrases"]] if d["catchphrases"] else []
            try:
                d["avatar_emotions"] = json.loads(d["avatar_emotions"]) if d.get("avatar_emotions") else {}
            except Exception:
                d["avatar_emotions"] = {}
            return d

    @staticmethod
    def upsert_character(data: Dict[str, Any]) -> int:
        """Karakter ekler veya günceller."""
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Karakter adı zorunludur.")

        channel_id = data.get("channel_id") or "global"
        role_type = data.get("role_type") or "amca"
        age = int(data.get("age") or 45)
        gender = data.get("gender") or ("female" if "teyze" in name.lower() or "anne" in name.lower() else "male")
        avatar_prompt = data.get("avatar_prompt") or ""
        personality = data.get("personality") or ""
        catchphrases = data.get("catchphrases") or []
        if isinstance(catchphrases, list):
            catchphrases_str = json.dumps(catchphrases, ensure_ascii=False)
        else:
            catchphrases_str = json.dumps([str(catchphrases)], ensure_ascii=False)
        quirks = data.get("quirks") or ""
        relationships = data.get("relationships") or ""
        voice_id = data.get("voice_id") or ""
        pitch_settings = data.get("pitch_settings") or ""
        if isinstance(pitch_settings, dict):
            pitch_settings_str = json.dumps(pitch_settings, ensure_ascii=False)
        else:
            pitch_settings_str = str(pitch_settings or "")

        avatar_emotions = data.get("avatar_emotions") or {}
        if isinstance(avatar_emotions, dict):
            avatar_emotions_str = json.dumps(avatar_emotions, ensure_ascii=False)
        else:
            avatar_emotions_str = str(avatar_emotions or "{}")

        # Otomatik demografik ses ve ton eşleme
        if not voice_id:
            if gender == "female":
                voice_id = "tr-TR-EmelNeural"
                if not pitch_settings_str:
                    pitch_settings_str = json.dumps({"pitch": "+2Hz", "rate": "+0%", "gender": "female"}, ensure_ascii=False)
            else:
                voice_id = "tr-TR-AhmetNeural"
                if not pitch_settings_str:
                    pitch_settings_str = json.dumps({"pitch": "-4Hz" if age >= 40 else "+0Hz", "rate": "-2%", "gender": "male"}, ensure_ascii=False)

        char_id = data.get("id")

        with _get_db() as conn:
            cursor = conn.cursor()
            if char_id:
                cursor.execute("""
                    UPDATE characters SET
                        channel_id = ?, name = ?, role_type = ?, age = ?, gender = ?,
                        avatar_prompt = ?, personality = ?, catchphrases = ?,
                        quirks = ?, relationships = ?, voice_id = ?, pitch_settings = ?,
                        avatar_emotions = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (channel_id, name, role_type, age, gender, avatar_prompt,
                      personality, catchphrases_str, quirks, relationships,
                      voice_id, pitch_settings_str, avatar_emotions_str, char_id))
                return char_id
            else:
                cursor.execute("""
                    INSERT INTO characters (
                        channel_id, name, role_type, age, gender,
                        avatar_prompt, personality, catchphrases, quirks, relationships,
                        voice_id, pitch_settings, avatar_emotions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (channel_id, name, role_type, age, gender, avatar_prompt,
                      personality, catchphrases_str, quirks, relationships,
                      voice_id, pitch_settings_str, avatar_emotions_str))
                conn.commit()
                return cursor.lastrowid

    @staticmethod
    def get_voice_for_character(name: str, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Casper AI: Karakter RAG ile TTS Ses Eşleme.
        Karakter adına göre atanmış sabit ses klonunu (voice_id) ve ton ayarlarını (pitch/rate) döner.
        """
        chars = CharacterRAGManager.list_characters(channel_id=channel_id)
        name_clean = (name or "").strip().lower()
        for c in chars:
            c_name = (c.get("name") or "").lower()
            if c_name and (c_name in name_clean or name_clean in c_name):
                p_settings = {}
                if c.get("pitch_settings"):
                    try:
                        p_settings = json.loads(c["pitch_settings"]) if isinstance(c["pitch_settings"], str) else c["pitch_settings"]
                    except Exception:
                        pass
                gender = c.get("gender", "male")
                default_voice = "tr-TR-EmelNeural" if gender == "female" else "tr-TR-AhmetNeural"
                return {
                    "character_name": c.get("name"),
                    "voice_id": c.get("voice_id") or default_voice,
                    "pitch_settings": p_settings,
                    "gender": gender
                }

        # Bulunamadıysa demografik analizle eşle
        is_female = any(k in name_clean for k in ("kadın", "kiz", "teyze", "anne", "abla", "fatma", "ayşe", "zeynep", "merve"))
        is_elderly = any(k in name_clean for k in ("amca", "dede", "dayı", "hakkı", "hüseyin", "baba"))
        return {
            "character_name": name,
            "voice_id": "tr-TR-EmelNeural" if is_female else "tr-TR-AhmetNeural",
            "pitch_settings": {"pitch": "+2Hz", "rate": "+0%"} if is_female else {"pitch": "-4Hz" if is_elderly else "+0Hz", "rate": "-2%"},
            "gender": "female" if is_female else "male"
        }

    @staticmethod
    def get_emotion_avatars_for_character(name: str, channel_id: Optional[str] = None) -> Dict[str, str]:
        """
        Casper AI: Karakter Duygu Durumuna Göre Dinamik Avatar İfadeleri (Face-Swap / Emotion).
        Karakterin 'normal', 'shock' (şok/kızgın), 'happy' (gülen) avatar varyasyonlarını döner.
        """
        base_avatars = _BASE_DIR / "config" / "assets" / "whatsapp" / "assets" / "avatars"
        chars = CharacterRAGManager.list_characters(channel_id=channel_id)
        name_clean = (name or "").strip().lower()

        char_match = None
        for c in chars:
            c_name = (c.get("name") or "").lower()
            if c_name and (c_name in name_clean or name_clean in c_name):
                char_match = c
                break

        if char_match and char_match.get("avatar_emotions"):
            emos = char_match["avatar_emotions"]
            if isinstance(emos, dict) and emos.get("normal"):
                return emos

        # Demografik ve rol bazlı akıllı avatar eşleme
        is_female = (char_match.get("gender") == "female") if char_match else any(
            k in name_clean for k in ("kadın", "kiz", "teyze", "anne", "abla", "fatma", "ayşe", "mami", "mom")
        )
        is_elderly = any(k in name_clean for k in ("amca", "dede", "dayı", "baba", "hacı", "yönetici", "usta", "halil"))

        if is_female:
            base_norm = str(base_avatars / ("mom.jpg" if is_elderly else "girl.jpg"))
            base_shock = str(base_avatars / "troll.png") if (base_avatars / "troll.png").exists() else base_norm
            base_happy = str(base_avatars / ("girl.jpg" if is_elderly else "mom.jpg"))
        else:
            base_norm = str(base_avatars / ("dad.jpg" if is_elderly else "boy.jpg"))
            base_shock = str(base_avatars / "troll.png") if (base_avatars / "troll.png").exists() else base_norm
            base_happy = str(base_avatars / ("boy.jpg" if is_elderly else "dad.jpg"))

        return {
            "normal": base_norm,
            "shock": base_shock,
            "happy": base_happy
        }

    @staticmethod
    def get_avatar_for_emotion(name: str, emotion: str, channel_id: Optional[str] = None) -> str:
        """Karakter adı ve duyguya ('normal', 'shock', 'happy') göre uygun avatar dosya yolunu döner."""
        avatars = CharacterRAGManager.get_emotion_avatars_for_character(name, channel_id=channel_id)
        emo_key = (emotion or "normal").lower()
        if emo_key in ("angry", "shock", "surprised", "kızgın", "şok"):
            return avatars.get("shock") or avatars.get("normal")
        elif emo_key in ("happy", "laugh", "neşeli", "komik", "gülen"):
            return avatars.get("happy") or avatars.get("normal")
        return avatars.get("normal") or avatars.get("shock")

    @staticmethod
    def delete_character(char_id: int) -> bool:
        """Karakteri siler."""
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM characters WHERE id = ?", (char_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def list_memories(channel_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Kanalın geçmiş olay ve hikaye hafızasını listeler."""
        with _get_db() as conn:
            cursor = conn.cursor()
            if channel_id and channel_id != "global":
                cursor.execute("""
                    SELECT * FROM story_memories 
                    WHERE channel_id = ? OR channel_id = 'global'
                    ORDER BY id DESC LIMIT ?
                """, (channel_id, limit))
            else:
                cursor.execute("SELECT * FROM story_memories ORDER BY id DESC LIMIT ?", (limit,))
            
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["characters_involved"] = json.loads(d["characters_involved"]) if d["characters_involved"] else []
                except Exception:
                    d["characters_involved"] = [d["characters_involved"]] if d["characters_involved"] else []
                result.append(d)
            return result

    @staticmethod
    def add_memory(
        channel_id: str,
        title: str,
        summary: str,
        topic: str = "",
        characters_involved: Optional[List[str]] = None,
        key_events: str = ""
    ) -> int:
        """Yeni bir hikaye hafızası ekler."""
        chars_json = json.dumps(characters_involved or [], ensure_ascii=False)
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO story_memories (
                    channel_id, title, topic, summary, characters_involved, key_events
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (channel_id or "global", title, topic, summary, chars_json, key_events))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def delete_memory(memory_id: int) -> bool:
        """Hikaye hafızasını siler."""
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM story_memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def seed_defaults(channel_id: str = "global"):
        """Efsanevi Türk mizah ve apartman karakterlerini tohumlar."""
        default_characters = [
            {
                "name": "Hüseyin Amca",
                "role_type": "amca",
                "age": 68,
                "gender": "male",
                "avatar_prompt": "A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish man named Hüseyin Amca, authentic elderly uncle figure, realistic weathered wrinkled face, receding gray and white hair, neat gray mustache, warm wise grandfatherly expression, authentic Turkish senior citizen, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid authentic photography, strictly NO young person, NO teenager, NO modern teen selfie",
                "personality": "Huysuz, eski kafalı, çay tiryakisi, teknolojiye ve robot süpürgelere şüpheyle bakan, 'bizim zamanımızda' lafını dilinden düşürmeyen ama zor durumda herkesin yardımına koşan vefakar apartman büyüğü.",
                "catchphrases": [
                    "Çay koyun geliyorum!",
                    "Ya sabır, delirtmeyin insanı!",
                    "Bizim zamanımızda halı balkondan çırpılırdı, robot mu vardı?",
                    "Bana akıl öğretmeyin, ben sizin yaşınız kadar demlik eskittim."
                ],
                "quirks": "Sabah 6'da balkonu sular, WhatsApp'ta sesli mesaj yerine sürekli arar, teknoloji bozulunca 'fişini çekip taktınız mı' der.",
                "relationships": "Yönetici Halil Bey ile sürekli aidat ve gürültü tartışması yaşar. Fatma Teyze'nin böreklerini sever ama dedikodusuna kızar."
            },
            {
                "name": "Yönetici Halil Bey",
                "role_type": "ev_sahibi",
                "age": 52,
                "gender": "male",
                "avatar_prompt": "A realistic casual smartphone photo portrait of a mature 52-year-old middle-aged Turkish apartment manager man named Halil Bey, wearing a slightly worn polo shirt, serious strict bureaucrat expression, slight graying receding hair and trimmed mustache, square 1:1 aspect ratio, natural lighting, authentic WhatsApp profile avatar",
                "personality": "Kuralcı, takıntılı, apartman grubunda sürekli BÜYÜK HARFLE yazan, aidat gecikmesine tahammülü olmayan, asansörün 4 kişiden fazla binilmesine takık yönetici.",
                "catchphrases": [
                    "DEĞERLİ SAKİNLER LÜTFEN ASANSÖRE ÇÖP BIRAKMAYALIM!",
                    "Aidatları ayın 5'ine kadar yatırmayanların ismi panoya asılacaktır.",
                    "Kamera kayıtlarını tek tek inceliyorum!",
                    "Apartman huzurunu bozan hakkında yasal işlem başlatırım."
                ],
                "quirks": "Grupta her cümlesine 'ÖNEMLİ DUYURU' diye başlar, kapı önüne ayakkabı konulmasına tahammül edemez.",
                "relationships": "Hüseyin Amca'nın laf sokmalarından bıkmıştır, Kanka Burak'ın gece yarısı sipariş getiren kuryelerine kızar."
            },
            {
                "name": "Fatma Teyze",
                "role_type": "teyze",
                "age": 65,
                "gender": "female",
                "avatar_prompt": "A realistic candid phone camera portrait photo of an elderly 65-year-old senior Turkish woman named Fatma Teyze, authentic elderly aunt figure, gentle wrinkled weathered face, wearing a modest traditional headscarf with floral patterns, warm maternal gaze with a hint of mischievous curiosity, square 1:1 aspect ratio, close-up face portrait, natural ambient lighting, candid authentic photography, strictly NO young person, NO teenager, NO modern teen selfie",
                "personality": "Apartmandaki ve mahalledeki her olaydan anında haberdar olan, balkonda nöbet tutan, halı çırpmayı milli spor sayan, lafı gediğine oturtan dedikodu ustası.",
                "catchphrases": [
                    "Aaa benim halım kuru temizlemedeydi bir kere!",
                    "Gözümle görmesem inanmam ama dün gece 3'te kim girdi o kapıdan?",
                    "Senin o gelin adayı pek bir kibirliydi evladım...",
                    "Nazar değmesin diye bir şey demiyorum ama..."
                ],
                "quirks": "Halıyı tam alt komşu balkona çamaşır astığında çırpar, 'haberim yoktu' der. Herkese börek ikram ederken laf çakar.",
                "relationships": "Hüseyin Amca'ya akranı gibi takılır, Yönetici Halil'in açıklarını yüzüne vurur."
            },
            {
                "name": "Kasap Halil",
                "role_type": "esnaf",
                "age": 48,
                "gender": "male",
                "avatar_prompt": "A realistic casual smartphone photo portrait of a mature 48-year-old Turkish butcher named Kasap Halil, robust build, thick dark mustache, friendly candid smile, wearing a traditional white butcher apron, square 1:1 aspect ratio, natural lighting, authentic WhatsApp profile avatar",
                "personality": "Tok sesli, esnaf felsefesi yapan, ete zam geldikçe müşteriye dert yanan, her duruma 'çiçek yerine kıyma alsaydın' mantığıyla yaklaşan pratik zekalı kasap.",
                "catchphrases": [
                    "Ete zam gelmedi abi, dananın psikolojisi bozuldu yem pahalı!",
                    "Çiçek solup gidecek, kıyma alsaydın köfte yapıp yerdiniz!",
                    "Bu antrikot lokum lokum, padişah sofrasına layık.",
                    "Veresiye defterini kapattım diyorum ama kıyamıyorum yine."
                ],
                "quirks": "Her soruna et ve protein üzerinden çözüm bulur, gramajı asla tam tutturamaz '100 gram fazla koydum helal et' der.",
                "relationships": "Tüm apartmanın et tedarikçisi. Hüseyin Amca ile tavla oynar."
            },
            {
                "name": "Kanka Burak",
                "role_type": "kanka",
                "age": 24,
                "gender": "male",
                "avatar_prompt": "A realistic casual smartphone selfie profile photo of a 24-year-old young adult Turkish man named Burak, modern messy casual haircut, cheeky confident smile, casual t-shirt, square 1:1 aspect ratio, close-up face portrait, natural ambient lighting, candid authentic photography",
                "personality": "Sürekli borç isteyen veya halı sahaya son dakika adam arayan, bahane üretme şampiyonu, troll espriler yapan, rahatına aşırı düşkün genç.",
                "catchphrases": [
                    "Kanka acil 200 lira atar mısın akşama IBAN'ına geçiyorum (geçmedi).",
                    "Halı sahada kaleci eksik, eldivenleri getirdim koş!",
                    "Bro olay bildiğin gibi değil, ben de mağdurum...",
                    "Valla uyuyakalmışım kanka alarm çalmamış."
                ],
                "quirks": "Halı sahada topu hep auta atar, borç isteyeceği zaman mesajı 'Kankam benim bee' diye başlatır.",
                "relationships": "Yönetici Halil'in korkulu rüyası, Hüseyin Amca'nın 'bu gençlik nereye gidiyor' dediği tipik örnek."
            }
        ]

        with _get_db() as conn:
            cursor = conn.cursor()
            for char in default_characters:
                # İsme göre var mı bak
                cursor.execute("SELECT id FROM characters WHERE name = ? AND channel_id = ?", (char["name"], channel_id))
                exists = cursor.fetchone()
                if not exists:
                    cursor.execute("""
                        INSERT INTO characters (
                            channel_id, name, role_type, age, gender,
                            avatar_prompt, personality, catchphrases, quirks, relationships
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        channel_id,
                        char["name"],
                        char["role_type"],
                        char["age"],
                        char["gender"],
                        char["avatar_prompt"],
                        char["personality"],
                        json.dumps(char["catchphrases"], ensure_ascii=False),
                        char["quirks"],
                        char["relationships"]
                    ))
            conn.commit()

        # Örnek geçmiş hafıza (lore)
        default_memories = [
            {
                "title": "Balkondan Düşen Robot Süpürge Krizi",
                "topic": "robot süpürge kavgası halı silkeleme",
                "summary": "Fatma Teyze halı silkelerken 4. kattaki robot süpürge balkondan aşağı uçtu. Yönetici Halil apartman grubunda faili aradı, Hüseyin Amca robotun süpürülmekten bıkıp intihar ettiğini iddia etti.",
                "characters_involved": ["Hüseyin Amca", "Yönetici Halil Bey", "Fatma Teyze"],
                "key_events": "Robot süpürge pert oldu, Halil Bey kamera kaydı baktı, Hüseyin Amca süpürgenin fişini balkon demirine astı."
            },
            {
                "title": "Çiçek Yerine Kıyma Faciası",
                "topic": "yıldönümü hediye çiçek et",
                "summary": "Kasap Halil'in aklına uyup eşine evlilik yıldönümünde çiçek yerine 2 kilo dana kıyma götüren koca kapıda kaldı. WhatsApp grubunda apartmandan acil sığınacak kanepe aradı.",
                "characters_involved": ["Kasap Halil", "Kanka Burak", "Hüseyin Amca"],
                "key_events": "Hüseyin Amca 'kıymayı bana getirin köfte yapalım' dedi, Burak 'kanka çiğ köfte partisi verelim' diye gaz verdi."
            }
        ]

        with _get_db() as conn:
            cursor = conn.cursor()
            for mem in default_memories:
                cursor.execute("SELECT id FROM story_memories WHERE title = ? AND channel_id = ?", (mem["title"], channel_id))
                exists = cursor.fetchone()
                if not exists:
                    cursor.execute("""
                        INSERT INTO story_memories (
                            channel_id, title, topic, summary, characters_involved, key_events
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        channel_id,
                        mem["title"],
                        mem["topic"],
                        mem["summary"],
                        json.dumps(mem["characters_involved"], ensure_ascii=False),
                        mem["key_events"]
                    ))
            conn.commit()


    # ═══════════════════════════════════════════════════════════════
    # RETRIEVAL (Arama ve Prompt Enjeksiyonu)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def retrieve_relevant_lore(
        cls,
        channel_id: str,
        topic: str,
        top_k_characters: int = 2,
        top_k_memories: int = 2
    ) -> Dict[str, Any]:
        """
        Verilen konu başlığına göre en alakalı karakterleri ve geçmiş olay hafızasını bulur.
        """
        all_chars = cls.list_characters(channel_id)
        if not all_chars:
            # Karakter yoksa varsayılanları tohumla
            cls.seed_defaults(channel_id)
            all_chars = cls.list_characters(channel_id)

        clean_topic = (topic or "").lower()
        topic_words = set(re.findall(r"\w+", clean_topic))

        # 1. Karakter Eşleştirme (İsim veya unvan eşleşmesi)
        matched_chars = []
        for char in all_chars:
            score = 0
            char_name_lower = char["name"].lower()
            char_name_words = set(re.findall(r"\w+", char_name_lower))

            # Doğrudan isim geçiyorsa en yüksek puan
            if any(w in topic_words for w in char_name_words if len(w) > 2):
                score += 10
            # Rol türü geçiyorsa puan
            if char.get("role_type") and char["role_type"].lower() in clean_topic:
                score += 4
            # İlgi alanları veya huyları eşleşiyorsa
            quirks = (char.get("quirks") or "").lower()
            if any(w in quirks for w in topic_words if len(w) > 3):
                score += 2

            if score > 0:
                matched_chars.append((score, char))

        matched_chars.sort(key=lambda x: x[0], reverse=True)
        selected_chars = [c[1] for c in matched_chars[:top_k_characters]]

        # Eğer konuda hiçbir karakter adı geçmiyorsa, en popüler/tekrarlayan 1 karakteri dahil et
        if not selected_chars and all_chars:
            selected_chars = [all_chars[0]]  # Hüseyin Amca default

        # 2. Hikaye Hafızası Eşleştirme (TF-IDF Benzerliği veya Kelime Kesişimi)
        all_memories = cls.list_memories(channel_id, limit=30)
        selected_memories = []

        if all_memories:
            try:
                # scikit-learn ile TF-IDF Cosine Similarity
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity

                corpus = [
                    f"{m['title']} {m['topic']} {m['summary']} {m.get('key_events', '')}"
                    for m in all_memories
                ]
                vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
                tfidf_matrix = vectorizer.fit_transform(corpus)
                query_vec = vectorizer.transform([topic])

                sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
                ranked_indices = sims.argsort()[::-1]

                for idx in ranked_indices[:top_k_memories]:
                    if sims[idx] > 0.05:  # Belirli bir alaka eşiği
                        selected_memories.append(all_memories[idx])
            except Exception:
                # Fallback: Basit kelime kesişimi
                scored_mems = []
                for m in all_memories:
                    m_text = f"{m['title']} {m['topic']} {m['summary']} {m.get('key_events', '')}".lower()
                    overlap = sum(1 for w in topic_words if len(w) > 3 and w in m_text)
                    if overlap > 0:
                        scored_mems.append((overlap, m))
                scored_mems.sort(key=lambda x: x[0], reverse=True)
                selected_memories = [m[1] for m in scored_mems[:top_k_memories]]

        # Casper AI: Eğer konu bazlı eşleşen hafıza yetersizse, en son 2 geçmiş bölümü organik dizi devamlılığı için ekle
        if len(selected_memories) < top_k_memories and all_memories:
            for m in all_memories:
                if m not in selected_memories:
                    selected_memories.append(m)
                if len(selected_memories) >= top_k_memories:
                    break

        return {
            "characters": selected_chars,
            "memories": selected_memories
        }

    @classmethod
    def get_prompt_context(cls, channel_id: str, topic: str) -> str:
        """
        Senaryo yazma promptuna doğrudan eklenecek zengin RAG bağlam metnini üretir.
        Casper AI: Önceki Bölümden Kalan Olaylar & Universe Lore sürekliliğini enjekte eder.
        """
        lore = cls.retrieve_relevant_lore(channel_id, topic)
        chars = lore.get("characters", [])
        mems = lore.get("memories", [])

        if not chars and not mems:
            return ""

        context_lines = [
            "\n═══════════════════════════════════════════════════════════",
            "📚 KANAL EVRENİ VE KARAKTER HAFIZASI (LORE & CONTINUITY RAG):",
            "Bu kanalda izleyicinin yakından tanıdığı devam eden bir karakter evreni vardır.",
            "Aşağıdaki karakter kimliklerine, yaşlarına, konuşma tarzlarına ve geçmiş olaylara MUTLAKA SADIK KAL:"
        ]

        if chars:
            context_lines.append("\n🎭 KANALIN DEVAM EDEN KARAKTERLERİ:")
            for c in chars:
                c_name = c["name"]
                c_age = c["age"]
                c_personality = c.get("personality", "")
                c_quirks = c.get("quirks", "")
                c_phrases = c.get("catchphrases", [])
                c_avatar = c.get("avatar_prompt", "")

                line = f"- {c_name} (Yaş: {c_age}):"
                if c_personality:
                    line += f" Kişilik: {c_personality}."
                if c_quirks:
                    line += f" Huyları/Tavrı: {c_quirks}."
                if c_phrases and isinstance(c_phrases, list):
                    sample_phrases = ' / '.join([f'"{p}"' for p in c_phrases[:3]])
                    line += f" Sık Kullandığı Replikler: {sample_phrases}."
                if c_avatar:
                    line += f" [Profil Görsel Promptu: '{c_avatar}']"
                context_lines.append(line)

        if mems:
            context_lines.append("\n📖 ÖNCEKİ BÖLÜMLERDEN KALAN OLAYLAR (UNIVERSE LORE & ORGANİK DİZİ ETKİSİ):")
            for m in mems:
                m_title = m["title"]
                m_summary = m["summary"]
                m_events = m.get("key_events", "")
                context_lines.append(f"- Geçmiş Olay: \"{m_title}\" -> {m_summary}")
                if m_events:
                    context_lines.append(f"  (Detay: {m_events})")

            context_lines.append(
                "* KESİN KURAL (LORE CONTINUITY): Karakterler diyaloğun bir yerinde (özellikle 3. veya 4. mesajda) "
                "yukarıdaki geçmiş olaylara organik bir gönderme, laf sokma veya şaka yapmalıdır "
                "(ör. 'Sen önce geçen günkü robot süpürge olayını açıkla!', 'Hala borcunu vermedin unuttum sanma!'). "
                "Bu durum izleyicide birbiriyle bağlantılı gerçek bir evren hissi (Universe Lore) ve organik dizi etkisi oluşturur."
            )

        context_lines.append("═══════════════════════════════════════════════════════════\n")
        return "\n".join(context_lines)

    @classmethod
    def record_story_from_script(cls, channel_id: str, script: Dict[str, Any]):
        """
        Üretilen başarılı bir senaryoyu otomatik olarak hafızaya (story_memories) kaydeder.
        Böylece sistem her video üretiminde kendi hafızasını otomatik genişletir.
        """
        if not isinstance(script, dict):
            return

        title = script.get("title") or "Bilinmeyen Bölüm"
        contact_name = script.get("contact_name") or "Bilinmeyen"
        topic = script.get("topic") or title
        messages = script.get("messages") or []

        # Katılımcıları çıkar
        participants = set()
        if contact_name:
            # Emojileri temizle
            clean_c = re.sub(r"[^\w\s]", "", contact_name).strip()
            if clean_c:
                participants.add(clean_c)

        for m in messages:
            s_name = m.get("sender_name")
            if s_name:
                clean_s = re.sub(r"[^\w\s]", "", s_name).strip()
                if clean_s:
                    participants.add(clean_s)

        # Özet çıkar (ilk 2 mesaj ve son mesaj)
        summary_parts = []
        if messages:
            summary_parts.append(f"Açılış: {messages[0].get('text', '')}")
            if len(messages) > 1:
                summary_parts.append(f"Gelişme: {messages[1].get('text', '')}")
            summary_parts.append(f"Sonuç: {messages[-1].get('text', '')}")
        summary = " | ".join(summary_parts) if summary_parts else script.get("narration", "")

        cls.add_memory(
            channel_id=channel_id or "global",
            title=title,
            summary=summary,
            topic=topic,
            characters_involved=list(participants),
            key_events=f"Sonuç: {messages[-1].get('text', '')}" if messages else ""
        )
        print(f"[RAG] Yeni hikaye evren hafızasına işlendi: '{title}' ({len(participants)} karakter)")


# Kolay fonksiyon çağrıları
def get_rag_context_for_prompt(channel_id: str, topic: str) -> str:
    return CharacterRAGManager.get_prompt_context(channel_id, topic)

def record_story_from_script(channel_id: str, script: Dict[str, Any]):
    CharacterRAGManager.record_story_from_script(channel_id, script)
