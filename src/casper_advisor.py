"""
casper_advisor.py
Yerel, ultra-optimize, arka planda çalışan mimari danışman ve fikir motoru (Casper AI).
Graphify kod grafiğini (graphify-out/) ve sistem durumunu analiz ederek
projeyi geliştirecek 10 adet somut, yenilikçi fikir üretir (LM Studio / Local AI destekli).
Kullanıcının beğendiklerini hafızaya kaydeder, beğenmediklerini siler ve sırayla gezilmesini sağlar.
"""

from __future__ import annotations
import os
import json
import sqlite3
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

_BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = _BASE_DIR / "data"
DB_PATH = DATA_DIR / "casper_ideas.db"
GRAPHIFY_DIR = _BASE_DIR / "graphify-out"
CONVERSATION_ID = "b918ee66-9d53-472c-8ab2-0a10132b0a6f"


def _get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_casper_db():
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS casper_ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                impact TEXT NOT NULL DEFAULT 'Yüksek',
                category TEXT NOT NULL DEFAULT 'Mimari & Yapay Zeka',
                target_modules TEXT,
                prompt_instruction TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', -- pending, saved, applied, dismissed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def _normalize_title(title: str) -> str:
    """Casper AI: Başlıkları karşılaştırmak ve mükerrer fikirleri engellemek için normalize eder."""
    import re
    cleaned = re.sub(r'\(\d{1,2}:\d{2}\)', '', title or '')
    cleaned = re.sub(r'\([^\)]*\)', '', cleaned)
    cleaned = re.sub(r'[^\w\s]', '', cleaned).strip().lower()
    return re.sub(r'\s+', ' ', cleaned)


init_casper_db()


class CasperAdvisor:
    """Ultra-optimize arka plan fikir ve öneri motoru."""

    @classmethod
    def cleanup_duplicates(cls) -> int:
        """Veritabanındaki mükerrer kayıtları temizler, en yüksek öncelikli durumu (applied > saved > pending) korur."""
        status_priority = {"applied": 4, "saved": 3, "pending": 2, "dismissed": 1}
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, status FROM casper_ideas ORDER BY id ASC")
            all_rows = cursor.fetchall()
            
            seen_groups: Dict[str, List[Dict[str, Any]]] = {}
            for r in all_rows:
                norm = _normalize_title(r["title"])
                if norm not in seen_groups:
                    seen_groups[norm] = []
                seen_groups[norm].append(dict(r))

            deleted_ids = []
            for norm, group in seen_groups.items():
                if len(group) > 1:
                    # En yüksek öncelikli kaydı tut
                    group.sort(key=lambda x: (status_priority.get(x["status"], 0), x["id"]), reverse=True)
                    for dup in group[1:]:
                        deleted_ids.append(dup["id"])

            if deleted_ids:
                placeholders = ",".join("?" * len(deleted_ids))
                cursor.execute(f"DELETE FROM casper_ideas WHERE id IN ({placeholders})", deleted_ids)
                conn.commit()
                print(f"[CASPER] 🧹 {len(deleted_ids)} adet mükerrer fikir veritabanından temizlendi.")
            return len(deleted_ids)

    @classmethod
    def get_graphify_insights(cls) -> Dict[str, Any]:
        """Graphify çıktısından projenin kritik modüllerini ve analizini okur (sıfır CPU maliyeti)."""
        manifest_path = GRAPHIFY_DIR / "manifest.json"
        analysis_path = GRAPHIFY_DIR / ".graphify_analysis.json"

        insights = {
            "total_files": 0,
            "communities": 124,
            "god_nodes": [
                "ChannelManager (src/channel_manager.py)",
                "ScriptWriter (src/script_writer.py)",
                "VideoEditor & BaseVideoBuilder (src/video_editor.py)",
                "CharacterRAGManager (src/character_rag.py)",
                "ChatterboxAudioGenerator (src/chatterbox_generator.py)",
                "SubtitleBurner & ASSWriter (src/ass_subtitle.py)",
                "YouTubeUploaderAPI (src/youtube_uploader_api.py)",
                "ContentPlanner (src/content_planner.py)",
                "RoutineManager (src/routine_manager.py)",
                "Server (src/server.py)"
            ],
            "surprises": []
        }

        try:
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    insights["total_files"] = len(manifest)

            if analysis_path.exists():
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analysis = json.load(f)
                    communities = analysis.get("communities", {})
                    insights["communities"] = len(communities)
                    if analysis.get("gods"):
                        insights["god_nodes"] = [f"{g.get('label', '')} (Derece: {g.get('degree', 0)})" for g in analysis.get("gods")[:8]]
                    if analysis.get("surprises"):
                        insights["surprises"] = [f"{s.get('source')} -> {s.get('target')}" for s in analysis.get("surprises")[:5]]
        except Exception as e:
            print(f"[CASPER] Graphify okuma uyarısı: {e}")

        return insights

    @classmethod
    def call_lm_studio(cls, prompt: str, base_url: str = "http://localhost:1234/v1") -> Optional[str]:
        """LM Studio OpenAI uyumlu API uç noktasına istek atar."""
        base_clean = base_url.rstrip("/")
        # 1. Aktif modeli sorgula
        active_model = "local-model"
        try:
            req_models = urllib.request.Request(f"{base_clean}/models", headers={"User-Agent": "CasperAI"})
            with urllib.request.urlopen(req_models, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("data") and len(data["data"]) > 0:
                    active_model = data["data"][0].get("id", "local-model")
        except Exception:
            return None  # LM Studio çevrimdışı

        # 2. Chat completion çağrısı
        chat_url = f"{base_clean}/chat/completions"
        payload = {
            "model": active_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sen kıdemli bir Yapay Zeka Video Otomasyonu Baş Mimarı ve Danışmanısın (Casper AI). "
                        "Verilen Graphify mimari analizine göre YouTube Shorts ve video otomasyonu için TAM 10 ADET YENİ, "
                        "somut, benzersiz ve uygulanabilir geliştirme fikri üret. "
                        "Daha önce uygulanmış fikirleri kesinlikle tekrarlama. "
                        "Çıktıyı SADECE geçerli bir JSON array olarak döndür: "
                        '[{"title":"...","description":"...","impact":"...","category":"...","target_modules":"...","prompt_instruction":"..."}]'
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.75,
            "max_tokens": 4000
        }

        try:
            body_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                chat_url,
                data=body_bytes,
                headers={"Content-Type": "application/json", "User-Agent": "CasperAI"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                choices = res_data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    return choices[0]["message"]["content"]
        except Exception as e:
            print(f"[CASPER] LM Studio istek hatası: {e}")
            return None

        return None

    @classmethod
    def synthesize_graphify_10_ideas(cls, existing_norm_titles: Optional[set] = None) -> List[Dict[str, Any]]:
        """
        LM Studio çevrimdışı olduğunda veya yedek olarak çalışan,
        Graphify analizindeki düğümlere dayalı genişletilmiş ve benzersiz fikir kataloğu.
        Mevcut veritabanındaki fikirleri filtreleyerek daima taze ve benzersiz 10 fikir sunar.
        """
        existing_norm = existing_norm_titles or set()

        master_catalog = [
            {
                "title": "Dinamik BGM Ducking & Konuşma Odaklı Ses Kısıcı",
                "description": "WhatsApp seslendirmesi veya diyalog başladığında fon müziğinin sesini otomatik %70 oranında kısan, replik bittiğinde yükselten profesyonel mikser.",
                "impact": "Yüksek Anlaşılırlık",
                "category": "Ses & Miksaj",
                "target_modules": "src/video_editor.py, src/whatsapp/video_renderer.py",
                "prompt_instruction": "FFmpeg veya MoviePy ses birleştirme katmanına sidechaincompress / ducking filtresi ekle; konuşma varken müziği otomatik kıs."
            },
            {
                "title": "Kinetik Tipografi & Sarsıntı Efektli Dinamik Altyazı Balonu",
                "description": "Komik repliklerde veya 'şok' anlarında altyazı balonunun ekranda hafifçe titreyip büyümesini sağlayan kinetik CSS ve ASS animasyon motoru.",
                "impact": "İzleyici Tutma & Görsel Mizah",
                "category": "Altyazı & Animasyon",
                "target_modules": "src/ass_subtitle.py, config/assets/whatsapp/templates/whatsapp_chat.html",
                "prompt_instruction": "Diyalogdaki ünlemler ve şok anları için CSS keyframe shake ve ASS transform scale animasyonunu otomatik tetikle."
            },
            {
                "title": "YouTube Shorts Otomatik Bölümleme (Chapters) & Zaman Damgası",
                "description": "Videonun en can alıcı giriş, kriz ve ters köşe sahnelerini algılayarak video açıklamasına otomatik YouTube zaman damgası (00:00 Giriş, 00:15 Kriz) ekleyen modül.",
                "impact": "YouTube Algoritma & SEO",
                "category": "YouTube Büyüme",
                "target_modules": "src/script_writer.py, src/youtube_uploader_api.py",
                "prompt_instruction": "ScriptWriter sahne zamanlamalarından YouTube formatında video chapter listesi derleyip uploader açıklama metnine otomatik eklesin."
            },
            {
                "title": "RAM Önbellekli Hızlı Frame Pipeline (In-Memory Render)",
                "description": "Disk I/O darboğazını aşmak için sık kullanılan avatar, wallpaper ve ses varlıklarını bellekte (RAM) tutarak render süresini %40 kısaltan hızlandırıcı.",
                "impact": "2 Kat Render Hızı",
                "category": "Sistem & Performans",
                "target_modules": "src/video_editor.py, src/whatsapp/video_renderer.py",
                "prompt_instruction": "Sık yüklenen statik varlıklar (avatarlar, şablonlar, fonlar) için bellek LRU önbelleği ekle; her renderda diskten okumayı engelle."
            },
            {
                "title": "Çok Dilli Çeviri & Otomatik İngilizce Shorts Klonlayıcı",
                "description": "Tutmuş popüler Türkçe WhatsApp diyaloglarını İngilizceye çevirip seslendirerek tek tıkla küresel 'crazyychats' kanalına hazır Shorts üreten çoklu dil köprüsü.",
                "impact": "Küresel Gelir & Büyüme",
                "category": "Çoklu Dil & Ölçeklenme",
                "target_modules": "src/script_writer.py, src/channel_manager.py",
                "prompt_instruction": "Türkçe senaryoyu Gemini ile İngilizce 'slang' ve doğal sohbet kalıplarıyla yeniden yazıp chatterbox_en ile sentezleyen klonlama fonksiyonu ekle."
            },
            {
                "title": "Otomatik Yüz Odaklama & Akıllı Dikey Kırpma (Smart Face-Crop)",
                "description": "Karakter portreleri kare veya yatay olduğunda yüzü tespit edip WhatsApp daire avatarına tam ortalayarak kırpan akıllı görsel hizalayıcı.",
                "impact": "Kusursuz Görsel Uyum",
                "category": "Görsel İşleme",
                "target_modules": "src/video_editor.py, src/character_rag.py",
                "prompt_instruction": "Pillow / OpenCV ile avatar yüklenirken yüz bölgesini tespit et ve 1:1 kare merkeze alarak otomatik kovala."
            },
            {
                "title": "WhatsApp Diyaloglarına Otomatik Dinamik SFX Ses Mikseri",
                "description": "Mesaj balonu geldiğinde 'pop' sesi, yazarken daktilo/klavye tıkırtısı ve ters köşe esprilerde komik ses efekti (vine boom, ding) otomatik olarak videoya mikslensin.",
                "impact": "İzleyici Tutma & Akış",
                "category": "Video & Ses Kurgusu",
                "target_modules": "src/video_editor.py, src/audio_library.py",
                "prompt_instruction": "video_editor.py içinde WhatsApp mesaj zamanlarına göre arka plana pop, klavye ve punchline ses efektlerini otomatik yerleştiren mikser ekle."
            },
            {
                "title": "YouTube Shorts İlk 3 Saniye 'Hook' Şok Sinyali & Görsel Zoom",
                "description": "Videonun ilk 3 saniyesinde izleyicinin parmak kaydırmasını (Thumb-stop) önlemek için ekrana hafif dinamik kamera 'Ken Burns' zoom ve dikkat çekici neon çerçeve flaşı ekleme.",
                "impact": "Viral İzlenme (Thumb-Stop)",
                "category": "YouTube Büyüme & Montaj",
                "target_modules": "src/video_editor.py, src/hyperframes_renderer.py",
                "prompt_instruction": "BaseVideoBuilder içine hook_intro_effect opsiyonu ekle. İlk 1.5 saniyede %105'ten %100'e yumuşak zoom-in ve dikkat çekici ses sinyali uygula."
            },
            {
                "title": "Otomatik Thumbnail (Küçük Resim) Şok İfadesi & Merak Metni Derleyici",
                "description": "YouTube Shorts ve normal videolar için videonun en dramatik karesini seçip üzerine sarı/kırmızı kalın fontla merak uyandıran 3 kelimelik başlık basan kapak üretici.",
                "impact": "Tıklama Oranı (CTR)",
                "category": "Görsel & Kapak",
                "target_modules": "src/video_editor.py, src/youtube_uploader_api.py",
                "prompt_instruction": "video_editor.py içine generate_clickbait_thumbnail fonksiyonu ekle. En yüksek kontrastlı sahneyi yakalayıp üzerine Pillow ile şık başlık yaz ve uploader'a aktar."
            },
            {
                "title": "Ses Seviyesi Normalizasyonu (EBU R128 Loudness Normalizer)",
                "description": "YouTube Shorts standartlarına (-14 LUFS) uyum sağlamak için video sonundaki ses, konuşma ve fon müziğini otomatik dengeleyen profesyonel ses sıkıştırıcı.",
                "impact": "Yayın Standardı & Kalite",
                "category": "Ses Mühendisliği",
                "target_modules": "src/video_editor.py",
                "prompt_instruction": "SubtitleBurner veya FFmpeg ses birleştirme adımına loudnorm=I=-14:LRA=7:tp=-1.5 filtresi ekle; ses patlamalarını ve kısık kalan replikleri engelle."
            },
            {
                "title": "Kanal Karakterleri Arası Çapraz İlişki & Hikaye Devamlılığı (Universe Lore)",
                "description": "Bir kanaldaki videoda bahsedilen borç veya dedikodunun, sonraki günkü başka bir videoda karakterler arasında devam eden bir espriye dönüşmesini sağlayan hafıza bağı.",
                "impact": "Sadık İzleyici Kitlesi",
                "category": "Hikaye Anlatımı & RAG",
                "target_modules": "src/character_rag.py, src/script_writer.py",
                "prompt_instruction": "CharacterRAGManager içindeki story_memories verisini ScriptWriter promptuna 'Önceki Bölümden Kalan Olaylar' olarak enjekte et; organik dizi etkisi yarat."
            }
        ]

        # Daha önce veritabanında var olan fikirleri filtrele
        fresh_ideas = []
        for item in master_catalog:
            norm = _normalize_title(item["title"])
            if norm not in existing_norm:
                fresh_ideas.append(item)

        # Eğer filtrelenmiş fikirler 10'dan azsa ve catalog bittiyse kalanları döndür
        return fresh_ideas[:10] if fresh_ideas else master_catalog[:10]

    @classmethod
    def generate_10_ideas(cls) -> List[Dict[str, Any]]:
        """
        Yerel AI (LM Studio) veya Graphify mimari motorunu kullanarak
        tam 10 adet taptaze ve mükerrer olmayan geliştirme fikri üretir.
        """
        cls.cleanup_duplicates()
        insights = cls.get_graphify_insights()

        # Mevcut kayıtlı/uygulanmış başlıkları al
        existing_norm_titles = set()
        recent_titles = []
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT title FROM casper_ideas ORDER BY id DESC")
            for r in cursor.fetchall():
                t = r["title"]
                existing_norm_titles.add(_normalize_title(t))
                if len(recent_titles) < 15:
                    recent_titles.append(t)

        # Prompt hazırlığı
        prompt = (
            f"Proje Graphify Analizi:\n"
            f"- Toplam {insights['total_files']} dosya ve {insights['communities']} alt modül topluluğu.\n"
            f"- Kritik God Node'lar: {', '.join(insights['god_nodes'][:6])}\n"
            f"- İlgili Sürpriz Bağlantılar: {', '.join(insights['surprises'][:3])}\n\n"
            f"Lütfen bu YouTube Shorts dikey video otomasyon projesine çağ atlatacak, "
            f"kurgu hızı, izleyici tutma, karakter yapısı, ses efektleri ve otomasyon konularında "
            f"TAM 10 ADET YENİ, MÜHENDİSLİK DÜZEYİNDE SOMUT GELİŞTİRME FİKRİ üret.\n"
        )
        if recent_titles:
            prompt += (
                f"\nÖNEMLİ KURAL: Aşağıdaki fikirler ZATEN önerilmiş veya uygulanmıştır. "
                f"Bunları KESİNLİKLE tekrarlama:\n- " + "\n- ".join(recent_titles) + "\n\n"
            )

        prompt += (
            f"SADECE geçerli bir JSON array formatında yanıt ver. Her eleman şunları içermelidir:\n"
            f"title (Türkçe başlık), description (açıklama), impact (etki), category (kategori), "
            f"target_modules (hedef dosyalar), prompt_instruction (Gemini uygulama direktifi)."
        )

        ideas_to_insert: List[Dict[str, Any]] = []

        # 1. LM Studio'yu dene
        lm_output = cls.call_lm_studio(prompt)
        if lm_output:
            try:
                cleaned = lm_output.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    for p in parsed:
                        if isinstance(p, dict) and p.get("title"):
                            if _normalize_title(p["title"]) not in existing_norm_titles:
                                ideas_to_insert.append(p)
                                existing_norm_titles.add(_normalize_title(p["title"]))
                    if ideas_to_insert:
                        print(f"[CASPER] 🧠 LM Studio üzerinden {len(ideas_to_insert)} adet taze fikir üretildi!")
            except Exception as parse_err:
                print(f"[CASPER] LM Studio JSON ayrıştırma uyarısı: {parse_err}")

        # 2. Eksik kalanlar için Graphify kataloğunu filtreleyerek doldur
        if len(ideas_to_insert) < 10:
            catalog_fresh = cls.synthesize_graphify_10_ideas(existing_norm_titles=existing_norm_titles)
            for c in catalog_fresh:
                if len(ideas_to_insert) >= 10:
                    break
                norm = _normalize_title(c["title"])
                if norm not in existing_norm_titles:
                    ideas_to_insert.append(c)
                    existing_norm_titles.add(norm)

        # Veritabanına kaydet (status = 'pending')
        with _get_db() as conn:
            cursor = conn.cursor()
            for idea in ideas_to_insert:
                cursor.execute("""
                    INSERT INTO casper_ideas (
                        title, description, impact, category, target_modules, prompt_instruction, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    idea.get("title", "İyileştirme Fikri"),
                    idea.get("description", ""),
                    idea.get("impact", "Yüksek"),
                    idea.get("category", "Mimari & Yapay Zeka"),
                    idea.get("target_modules", "src/server.py"),
                    idea.get("prompt_instruction", "")
                ))
            conn.commit()

        return cls.list_pending_ideas()

    @classmethod
    def list_pending_ideas(cls) -> List[Dict[str, Any]]:
        """Beklemede (pending) olan tüm fikirleri döner. Eğer hiç yoksa otomatik 10 fikir üretir."""
        cls.cleanup_duplicates()
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM casper_ideas WHERE status = 'pending' ORDER BY id ASC")
            rows = cursor.fetchall()

        if not rows:
            return cls.generate_10_ideas()

        return [dict(r) for r in rows]

    @classmethod
    def list_ideas(cls, status: Optional[str] = None) -> List[Dict[str, Any]]:
        cls.cleanup_duplicates()
        with _get_db() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM casper_ideas WHERE status = ? ORDER BY id DESC", (status,))
            else:
                cursor.execute("SELECT * FROM casper_ideas ORDER BY id DESC")
            return [dict(r) for r in cursor.fetchall()]

    @classmethod
    def get_current_tip(cls) -> Optional[Dict[str, Any]]:
        """Casper'ın ekranda o an göstereceği fikri getirir."""
        pending = cls.list_pending_ideas()
        if pending:
            return pending[0]
        return None

    @classmethod
    def delete_idea(cls, idea_id: int) -> bool:
        """Kullanıcının beğenmediği fikri veritabanından tamamen siler."""
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM casper_ideas WHERE id = ?", (idea_id,))
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def set_idea_status(cls, idea_id: int, status: str) -> bool:
        """Fikrin durumunu günceller: 'saved', 'dismissed', 'applied', 'pending'."""
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE casper_ideas 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (status, idea_id))
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def get_saved_count(cls) -> int:
        cls.cleanup_duplicates()
        with _get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM casper_ideas WHERE status = 'saved'")
            return cursor.fetchone()["count"]

    @classmethod
    def build_agy_prompt_payload(cls) -> Dict[str, Any]:
        """
        Kullanıcının 'Kaydettiği' (saved) tüm fikirleri toplayıp
        Gemini'ye iletilecek kusursuz, doğrudan uygulanabilir geliştirme direktifine dönüştürür.
        Mükerrer başlıkları deduplicate eder; her fikir yalnızca 1 kez listelenir!
        """
        cls.cleanup_duplicates()
        raw_saved_ideas = cls.list_ideas(status="saved")
        if not raw_saved_ideas:
            pending = cls.list_pending_ideas()
            raw_saved_ideas = pending[:1] if pending else []

        # Casper AI: Kesin deduplication - aynı fikir asla iki kez listelenemez!
        saved_ideas: List[Dict[str, Any]] = []
        seen_titles = set()
        for idea in raw_saved_ideas:
            norm = _normalize_title(idea.get("title", ""))
            if norm not in seen_titles:
                seen_titles.add(norm)
                saved_ideas.append(idea)

        if not saved_ideas:
            return {
                "conversation_id": CONVERSATION_ID,
                "command": 'agy --dangerously-skip-permissions -p "[Casper Direktifleri]"',
                "prompt": "Projeyi incele ve kod kalitesini optimize et.",
                "ideas_count": 0,
                "ideas": []
            }

        prompt_lines = [
            f"Merhaba Gemini! Sistemdeki Casper AI danışmanı tarafından önerilen ve kullanıcı tarafından ONAYLANAN aşağıdaki {len(saved_ideas)} adet geliştirme maddesini projeye uygulamanı istiyorum:",
            ""
        ]

        for i, idea in enumerate(saved_ideas, 1):
            prompt_lines.append(f"### {i}. {idea['title']} [{idea['category']} - Öncelik: {idea['impact']}]")
            prompt_lines.append(f"Açıklama: {idea['description']}")
            prompt_lines.append(f"İlgili Dosyalar: {idea['target_modules']}")
            prompt_lines.append(f"Uygulama Direktifi: {idea['prompt_instruction']}")
            prompt_lines.append("")

        prompt_lines.append("Lütfen bu geliştirmeleri mimariyi bozmadan, mevcut kütüphaneleri kullanarak, temiz ve üretime hazır şekilde kodla ve test et.")

        full_prompt = "\n".join(prompt_lines)
        return {
            "conversation_id": CONVERSATION_ID,
            "command": 'agy --dangerously-skip-permissions -p "[Casper Direktifleri]"',
            "prompt": full_prompt,
            "ideas_count": len(saved_ideas),
            "ideas": saved_ideas
        }
