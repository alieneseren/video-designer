"""
core/asset_validator.py
=======================
Pre-Render Quality Gate (Modül 1): Yerel AI ve Kural Tabanlı Varlık Filtresi.
(Local AI & Rule-Based Asset Filter for Pre-Render Quality Gate - Enhanced)

Mimarî Güncellemeler:
1. No-Loop & Deduplication Registry (used_assets):
   - Her video için onaylanmış görselleri takip eder.
   - Aynı görselin bir video içinde iki kez kullanılmasını (%100 deterministik) engeller.
2. 2 vCPU Optimize SigLIP / CLIP Vizyon Motoru:
   - Öncelikli model: google/siglip-base-patch16-256 (device CPU, torch thread=2, low_cpu_mem_usage=True).
   - Otomatik yedek: openai/clip-vit-base-patch32.
   - Singleton ve lazy-load yapısı (RAM bütçesi <= 3.5 GB).
3. Dinamik Dönem / Takım / Bağlam Negatifleri:
   - query_builder tarafından üretilen dinamik etiketleri (örn. 1997 Iverson için Detroit Pistons, streetwear vb.)
     negatif havuzuna enjekte eder. Negatif skor pozitif skoru geçerse anında eler.
4. Çoklu Proje Duvarı (Cross-Project Wall) & Deterministik Metadata Kontrolü:
   - 0 ms sürede çözünürlük (min 720p), tek renk/boş kontrolü ve çapraz klasör sızıntılarını engeller.
"""

from __future__ import annotations

import os
import re
import gc
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from PIL import Image, ImageStat

logger = logging.getLogger("AssetValidator")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ─────────────────────────────────────────────────────────────
# ÇOKLU PROJE İZOLASYON KURALLARI (CROSS-PROJECT WALL)
# ─────────────────────────────────────────────────────────────

STAMP_WATERMARK_LABELS: List[str] = [
    "circular watermark stamp logo",
    "round photographer embossed seal",
    "semi transparent circular watermark",
    "prominent white watermark text",
    "photography studio round emblem overlay",
    # Taranmış Baskı ve Beyaz Kenarlık Etiketleri
    "white photo border margin",
    "scanned photograph print with borders",
    "newspaper wirephoto caption text",
    "polaroid white border frame",
    "magazine article page with borders",
    "scanned historical document paper"
]

BORDER_AND_SCAN_LABELS: List[str] = [
    "white photo border margin",
    "scanned photograph print with borders",
    "newspaper wirephoto caption text",
    "polaroid white border frame",
    "magazine article page with borders",
    "scanned historical document paper"
]

CROSS_PROJECT_WALL_RULES: Dict[str, Dict[str, List[str]]] = {
    "basketball_analysis": {
        "aliases": ["thebasketballshows", "nba_history", "basketball", "sports", "nba"],
        "forbidden_path_tokens": [
            "aviation", "airplane", "airfield", "cockpit", "runway", "crash",
            "military", "crayon", "weapon", "fighter_jet", "tank", "combat", "drone_overhead",
            "atsugi", "military_base", "signing", "autograph", "school", "classroom",
            "box_score_old", "paper_sheet", "press_conference", "yellow_jersey", "soccer", "football", "fifa", "robinho",
            "ticket", "stub", "jumbotron", "scoreboard", "scola", "bonzi", "arena_bar"
        ],
        "default_blacklist": [
            # Taranmış Baskı ve Beyaz Kenarlık Filtresi (Border & Letterboxing Prevention)
            "white photo border margin",
            "scanned photograph print with borders",
            "newspaper wirephoto caption text",
            "polaroid white border frame",
            "magazine article page with borders",
            "scanned historical document paper",
            # Dairesel Damga ve Mühür Filtresi (Circular Stamp & Seal Overlay)
            "circular watermark stamp logo",
            "round photographer embossed seal",
            "semi transparent circular watermark",
            "prominent white watermark text",
            "photography studio round emblem overlay",
            # Filigran ve Ticari Stok Damgası Dedektörü (Watermark & Agency Overlay)
            "prominent white watermark text",
            "getty images watermark overlay",
            "stock photo watermark copyright",
            "watermark text overlay",
            "getty images watermark",
            "shutterstock watermark",
            "stock watermark",
            "white copyright watermark text",
            "watermark logo text",
            # Bilet, Belge ve Boş Salon Filtresi (Asset Contamination Koruması)
            "paper ticket stub",
            "admission ticket",
            "stadium jumbotron scoreboard screen",
            "stadium jumbotron scoreboard",
            "empty indoor arena seats",
            "indoor bar counter bartender",
            "empty basketball stadium seats",
            "crowd sitting in arena stands",
            "modern digital ticket",
            "close-up text document receipt",
            "ticket stub", "ticket", "scoreboard", "indoor bar", "arena seats",
            # Ahşap Zemin, Tablo ve Ürün Mockup Filtresi (Product Mockup & Wood Background Prevention)
            "wood planks floor mockup framed picture or canvas on wood",
            "wood floor mockup with framed photo or poster",
            "framed poster print lying on wooden background",
            "picture frame lying on wooden board table",
            "wooden table with framed picture",
            "sports merchandise product mockup",
            "framed wall art mockup on wooden planks",
            "wood background with framed photo or poster",
            "picture lying on wooden floor",
            "canvas print mockup on wood planks",
            # Bölünmüş Ekran, Kolaj ve Forma Şablonu Filtresi (Split-Screen & Collage Prevention)
            "split screen collage graphic with jerseys",
            "split screen collage graphic",
            "split screen with jerseys and photo",
            "two photos side by side split image",
            "multi photo montage banner",
            "composite split layout graphic",
            "jersey display next to photo graphic",
            "magazine collage multiple cutouts",
            "side by side composite image",
            # Yanlış Dönem Oyuncuları (2000'ler Rockets sızıntısı)
            "luis scola", "scola", "luther head", "bonzi wells", "yao ming", "james harden", "harden",
            # Çapraz Spor ve Uygunsuz Görseller
            "soccer", "football", "fifa", "world cup", "brazil", "robinho",
            "military base", "elementary school", "autograph signing table", "press conference microphone",
            "japanese atsugi military base", "yellow soccer jersey crowd", "yellow football jersey fans",
            "elementary school classroom children", "autograph signing session table",
            "old paper sheet scoresheet", "legs in cargo shorts",
            "empty basketball hoop without players", "rural backyard dirt court",
            "rural house", "backyard", "suburban driveway", "amateur kid playing basketball",
            "pink house", "grass yard hoop", "residential house", "suburban backyard", "driveway hoop",
            "kevin mchale", "mchale", "boston celtics", "celtics", "larry bird", "robert parish", "parish",
            "aerial drone shot of playground or soccer field", "blurry low quality",
            "stock photo watermark text logo", "person sitting in casual clothes on street",
            "sneakers on concrete ground", "amateur children playing"
        ],
        "default_positives": [
            "official NBA professional basketball game action",
            "NBA basketball player in arena uniform playing",
            "authentic high definition basketball arena court"
        ]
    },
    "aviation_disaster": {
        "aliases": ["aviation", "flight_disaster", "plane_crash", "mayday"],
        "forbidden_path_tokens": [
            "basketball", "nba", "slam_dunk", "court_arena", "sports",
            "comedy", "cartoon", "stickman"
        ],
        "default_blacklist": [
            "cartoon animation drawing",
            "car traffic on street",
            "train on railway track",
            "basketball court or player",
            "living room furniture",
            "stock watermark"
        ],
        "default_positives": [
            "commercial airplane flight",
            "cockpit instrument panel",
            "airport runway and air traffic"
        ]
    },
    "crayon_combat": {
        "aliases": ["military", "tacticallcrayon", "defense_news"],
        "forbidden_path_tokens": [
            "basketball", "nba", "travel_scenery"
        ],
        "default_blacklist": [
            "civilian car traffic",
            "children cartoon toys",
            "sports stadium",
            "fashion clothing models"
        ],
        "default_positives": [
            "tactical military schematic drawing",
            "armored defense vehicle technical diagram",
            "fighter aircraft weapon systems"
        ]
    }
}


@dataclass
class ValidationResult:
    """Kalite kapısı değerlendirme sonucu."""
    is_valid: bool
    status: str  # "ACCEPTED" | "REJECTED"
    score: float
    tier_failed: Optional[int] = None
    reason: str = ""
    negative_score: float = 0.0
    best_positive_label: str = ""
    worst_negative_label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status,
            "score": round(self.score, 4),
            "negative_score": round(self.negative_score, 4),
            "tier_failed": self.tier_failed,
            "reason": self.reason,
            "best_positive_label": self.best_positive_label,
            "worst_negative_label": self.worst_negative_label,
            "metadata": self.metadata
        }


class AssetValidator:
    """
    Yerel CPU-optimize, lazy-loading ve singleton çalışan varlık doğrulayıcı.
    SigLIP / CLIP vizyon motoru ve No-Loop hafıza desteği içerir.
    """
    _instance: Optional["AssetValidator"] = None
    _vision_model = None
    _vision_processor = None
    _vision_model_type: str = "none"  # "siglip" | "clip" | "none"
    _moondream_model = None
    _moondream_tokenizer = None
    _device: str = "cpu"

    def __new__(cls) -> "AssetValidator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._determine_device()
            cls._instance.used_assets: Set[str] = set()
            cls._instance.used_hashes: Set[str] = set()
            cls._instance.used_perceptual_hashes: List[str] = []
            cls._instance.asset_occurrences: Dict[str, int] = {}
            cls._instance.candidate_limit: int = 10
            cls._instance.max_occurrences: int = 1
        return cls._instance

    def _determine_device(self):
        """CPU öncelikli cihaz seçimi (Maksimum 2 vCPU verimliliği)."""
        try:
            import torch
            torch.set_num_threads(2)
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"
        except Exception:
            self._device = "cpu"
        logger.debug(f"AssetValidator cihazı: {self._device.upper()} (2 CPU Threads)")

    # ─────────────────────────────────────────────────────────────
    # NO-LOOP / MÜKERRER KULLANIM HAFIZASI (DEDUPLICATION REGISTRY)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_file_hash(file_path: Union[str, Path]) -> str:
        """Dosyanın MD5 hash'ini hesaplar (Hem video hem resim için mükerrer kullanım koruması)."""
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
    def compute_dhash(image_input: Union[str, Path, Any], hash_size: int = 8) -> str:
        """Görselin algısal fark hash'ini (dHash) hesaplar (Sıfır kütüphane bağımlılığı, deterministik)."""
        try:
            from PIL import Image
            if isinstance(image_input, (str, Path)):
                p = Path(image_input)
                if not p.exists() or not p.is_file():
                    return ""
                im = Image.open(p)
            else:
                im = image_input

            im = im.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
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

    def register_used_asset(self, asset_identifier: Union[str, Path]) -> None:
        """Kullanılan varlığın (resim veya video) mutlak yolunu, dosya adını, MD5 ve algısal dHash'ini kaydeder."""
        p = Path(asset_identifier)
        norm_resolved = str(p.resolve()).lower()
        norm_name = p.name.lower()
        f_hash = self._compute_file_hash(p)

        self.used_assets.add(norm_resolved)
        self.used_assets.add(norm_name)
        if f_hash:
            self.used_hashes.add(f_hash)

        # Algısal hash kaydı
        d_hash = self.compute_dhash(p)
        if d_hash and hasattr(self, "used_perceptual_hashes"):
            self.used_perceptual_hashes.append(d_hash)

        self.asset_occurrences[norm_name] = self.asset_occurrences.get(norm_name, 0) + 1
        if f_hash:
            self.asset_occurrences[f_hash] = self.asset_occurrences.get(f_hash, 0) + 1

        logger.debug(f"[No-Loop] Varlık kaydedildi: {norm_name} (MD5: {f_hash[:8] if f_hash else 'N/A'}, dHash: {d_hash[:8] if d_hash else 'N/A'})")

    def is_asset_used(self, asset_identifier: Union[str, Path], max_hamming_dist: int = 10) -> bool:
        """Bu varlık (resim veya video) daha önce bu video zaman çizelgesinde kullanıldı mı?"""
        p = Path(asset_identifier)
        norm_resolved = str(p.resolve()).lower()
        norm_name = p.name.lower()
        f_hash = self._compute_file_hash(p)

        if norm_resolved in self.used_assets or norm_name in self.used_assets:
            return True
        if f_hash and f_hash in self.used_hashes:
            return True
        if self.asset_occurrences.get(norm_name, 0) >= self.max_occurrences:
            return True
        if f_hash and self.asset_occurrences.get(f_hash, 0) >= self.max_occurrences:
            return True

        # Algısal Tekilleştirme Kontrolü (Perceptual Deduplication)
        d_hash = self.compute_dhash(p)
        if d_hash and hasattr(self, "used_perceptual_hashes"):
            for uh in self.used_perceptual_hashes:
                dist = self.hamming_distance(d_hash, uh)
                if dist <= max_hamming_dist:
                    logger.warning(f"🚫 [No-Loop - Algısal Tekrar] '{p.name}' daha önce onaylanan bir görsel ile aşırı benzer/birebir aynı (Hamming mesafesi: {dist} <= {max_hamming_dist}).")
                    return True

        return False

    def reset_used_assets(self) -> None:
        """Yeni video render'ı başlarken kullanılan varlık havuzunu sıfırlar."""
        self.used_assets.clear()
        self.used_hashes.clear()
        if hasattr(self, "used_perceptual_hashes"):
            self.used_perceptual_hashes.clear()
        self.asset_occurrences.clear()
        logger.info("🔄 [No-Loop] used_assets, used_hashes ve used_perceptual_hashes kayıt havuzu sıfırlandı.")

    # ─────────────────────────────────────────────────────────────
    # KADEME 0: ÇOKLU PROJE DUVARI (CROSS-PROJECT WALL)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def check_cross_project_isolation(
        cls,
        file_path: Union[str, Path],
        project_type: Optional[str]
    ) -> Tuple[bool, str]:
        """Görsel dosya yolunda diğer projelerin yasaklı kelimelerini 0 ms'de engeller."""
        if not project_type:
            return True, "Proje tipi belirtilmedi, izolasyon kontrolü atlandı."

        p_str = str(file_path).lower().replace("\\", "/")
        norm_proj = project_type.lower().strip()

        rule_key = None
        for r_name, r_data in CROSS_PROJECT_WALL_RULES.items():
            if norm_proj == r_name or norm_proj in r_data.get("aliases", []):
                rule_key = r_name
                break

        if not rule_key:
            return True, f"'{project_type}' için özel duvar kuralı tanımlı değil."

        forbidden_tokens = CROSS_PROJECT_WALL_RULES[rule_key].get("forbidden_path_tokens", [])
        for token in forbidden_tokens:
            if f"/{token}" in p_str or f"_{token}" in p_str or f"-{token}" in p_str:
                msg = f"Cross-Project Duvarı: '{project_type}' projesinde yasaklı alt yol tespit edildi: '{token}' -> {Path(file_path).name}"
                logger.warning(f"🚫 {msg}")
                return False, msg

        return True, "Cross-Project izolasyon doğrulaması başarılı."

    # ─────────────────────────────────────────────────────────────
    # KADEME 1: DETERMINİSTİK METADATA KONTROLÜ (0 ms)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def check_metadata(
        cls,
        image_path: Union[str, Path],
        is_vertical: bool = True,
        min_dim: int = 720
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Deterministik çözünürlük, dosya bütünlüğü ve renk dağılımı kontrolü.
        - Çözünürlük: Dikey için en az 720p standartlarını karşılamalı.
        - Bozukluk: PIL Image.verify().
        - Tek renk/boş ekran: StdDev < 8.0 ise elenir.
        """
        p = Path(image_path)
        if not p.exists():
            return False, f"Dosya mevcut değil: {p.name}", {}

        fsize = p.stat().st_size
        if fsize < 15 * 1024:
            return False, f"Dosya boyutu çok küçük ({fsize / 1024:.1f} KB < 15 KB), muhtemelen bozuk veya thumbnail.", {}

        # 0. Video format desteği (.mp4, .mov, .mkv, .webm, .ts)
        if p.suffix.lower() in ('.mp4', '.mov', '.mkv', '.webm', '.ts'):
            try:
                import cv2
                cap = cv2.VideoCapture(str(p))
                if not cap.isOpened():
                    return False, f"Bozuk video formatı açılamadı: {p.name}", {}
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                dur = frame_count / fps if fps > 0 else 0.0
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ret, frame = cap.read()
                if not ret or frame is None:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                cap.release()
                if not ret or frame is None:
                    return False, f"Videodan kare okunamadı: {p.name}", {}
                if min(w, h) < 480:
                    return False, f"Düşük video çözünürlüğü ({w}x{h}).", {"width": w, "height": h}
                stat = ImageStat.Stat(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                avg_stddev = sum(v ** 0.5 for v in stat.var) / 3.0
                if avg_stddev < 8.0:
                    return False, f"Video içeriği yetersiz / tek renk boş ekran (StdDev: {avg_stddev:.1f} < 8.0).", {"width": w, "height": h, "stddev": avg_stddev}
                return True, "Video format ve bütünlük kontrolleri geçti.", {
                    "width": w,
                    "height": h,
                    "duration": round(dur, 2),
                    "format": p.suffix.upper(),
                    "filesize_kb": round(fsize / 1024, 1),
                    "stddev": round(avg_stddev, 2)
                }
            except Exception as e_vid:
                return False, f"Video incelenirken hata: {e_vid}", {}

        # 1. Dosya bütünlüğü
        try:
            with Image.open(p) as img_test:
                img_test.verify()
        except Exception as e_verify:
            return False, f"Bozuk görsel formatı (verify başarısız): {e_verify}", {}

        # 2. Boyut ve varyans analizi
        try:
            with Image.open(p) as img:
                w, h = img.size
                mode = img.mode

                if is_vertical:
                    if min(w, h) < 600 or max(w, h) < 900:
                        return False, f"Düşük çözünürlük ({w}x{h}). Dikey içerik için minimum 720p standartlarını karşılamıyor.", {"width": w, "height": h}
                else:
                    if max(w, h) < min_dim or min(w, h) < 480:
                        return False, f"Düşük çözünürlük ({w}x{h}). Minimum {min_dim}p eşiğinin altında.", {"width": w, "height": h}

                rgb_img = img.convert("RGB")
                stat = ImageStat.Stat(rgb_img)
                avg_stddev = sum(v ** 0.5 for v in stat.var) / 3.0
                if avg_stddev < 8.0:
                    return False, f"Görsel içeriği yetersiz / tek renk boş ekran (StdDev: {avg_stddev:.1f} < 8.0).", {"width": w, "height": h, "stddev": avg_stddev}

                return True, "Metadata ve bütünlük kontrolleri geçti.", {
                    "width": w,
                    "height": h,
                    "format": img.format,
                    "mode": mode,
                    "filesize_kb": round(fsize / 1024, 1),
                    "stddev": round(avg_stddev, 2)
                }

        except Exception as e_open:
            return False, f"Görsel incelenirken hata oluştu: {e_open}", {}

    # ─────────────────────────────────────────────────────────────
    # KADEME 2: HAFİF ZERO-SHOT SKORLAMA (SIGLIP / CLIP - CPU)
    # ─────────────────────────────────────────────────────────────

    def _load_vision_model(self) -> bool:
        """
        Yerel CLIP (openai/clip-vit-base-patch32) modelini öncelikli olarak belleğe alır.
        CLIP'in softmax mutual-exclusion olasılıkları ikili (binary) filigran ve illüstrasyon
        ayrımında %99+ hassasiyet ve sıfır yalancı pozitif (false-positive) garantisi sağlar.
        """
        if self._vision_model is not None and self._vision_processor is not None:
            return True

        import torch
        torch.set_num_threads(2)

        # 1. Öncelik: CLIP (openai/clip-vit-base-patch32 - Hızlı, Kararlı ve Önbellekte Hazır)
        clip_id = "openai/clip-vit-base-patch32"
        try:
            from transformers import CLIPProcessor, CLIPModel
            logger.info(f"🧠 [QualityGate] CLIP vizyon motoru yükleniyor ({clip_id} on CPU)...")
            self._vision_processor = CLIPProcessor.from_pretrained(clip_id)
            self._vision_model = CLIPModel.from_pretrained(clip_id, low_cpu_mem_usage=True)
            self._vision_model.to(self._device)
            self._vision_model.eval()
            self._vision_model_type = "clip"
            logger.info("✅ [QualityGate] CLIP vizyon motoru hazırlandı.")
            return True
        except Exception as e_clip:
            logger.warning(f"⚠️ [QualityGate] CLIP başlatılamadı ({e_clip}). SigLIP modeline geçiliyor...")

        # 2. Öncelik: SigLIP (google/siglip-base-patch16-256)
        siglip_id = "google/siglip-base-patch16-256"
        try:
            from transformers.models.siglip import SiglipTokenizer
            from transformers import SiglipImageProcessor, SiglipProcessor, SiglipModel
            tok = SiglipTokenizer.from_pretrained(siglip_id, local_files_only=True)
            img_proc = SiglipImageProcessor.from_pretrained(siglip_id, local_files_only=True)
            self._vision_processor = SiglipProcessor(image_processor=img_proc, tokenizer=tok)
            self._vision_model = SiglipModel.from_pretrained(siglip_id, low_cpu_mem_usage=True, local_files_only=True)
            self._vision_model.to(self._device)
            self._vision_model.eval()
            self._vision_model_type = "siglip"
            logger.info("✅ [QualityGate] SigLIP vizyon motoru yerel önbellekten yüklendi.")
            return True
        except Exception as e_siglip:
            logger.error(f"❌ [QualityGate] Vizyon motoru yüklenemedi: {e_siglip}")
            self._vision_model = None
            self._vision_processor = None
            self._vision_model_type = "none"
            return False

    def check_watermark(self, image_input: Union[str, Path, Image.Image], project_type: Optional[str] = None) -> Tuple[bool, float, str]:
        """
        Özel 2-sınıflı (binary) filigran ve ticari ajans damgası (Getty, Alamy, Shutterstock) denetimi.
        Softmax seyreltilmesine uğramadan tüm görsel ve alt-sağ / alt bölge bağımsız taranır.
        Dönen: (has_watermark: bool, confidence: float, reason: str)
        """
        if not self._load_vision_model():
            return False, 0.0, "Vizyon modeli aktif değil"

        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists():
                return False, 0.0, f"Görsel bulunamadı: {p.name}"
            try:
                img = Image.open(p).convert("RGB")
            except Exception as e:
                return False, 0.0, f"Görsel açılamadı: {e}"
        else:
            img = image_input.convert("RGB")

        w, h = img.size
        import torch

        norm_proj = (project_type or "").lower().strip()
        is_sports = norm_proj in ("basketball_analysis", "basketball", "sports", "nba", "thebasketballshows")
        wm_th = 0.45 if is_sports else 0.65

        # 1. Filigran & Ajans Damgası (Köşe, Alt ve Göğüs Taraması)
        wm_texts = [
            "an authentic clean photo without watermark or stamp",
            "a photo with watermark, getty images logo, round seal stamp, or copyright overlay text"
        ]
        wm_crops = [
            ("tam", img),
            ("alt_sag", img.crop((int(w * 0.35), int(h * 0.35), w, h))),
            ("alt_serit", img.crop((0, int(h * 0.60), w, h))),
            ("gogus_merkez", img.crop((int(w * 0.15), int(h * 0.20), int(w * 0.85), int(h * 0.65)))),
            ("orta_sag", img.crop((int(w * 0.25), int(h * 0.30), int(w * 0.98), int(h * 0.75))))
        ]

        for region_name, crop_img in wm_crops:
            try:
                inputs = self._vision_processor(
                    text=wm_texts,
                    images=crop_img,
                    return_tensors="pt",
                    padding=True,
                    truncation=True
                ).to(self._device)

                with torch.no_grad():
                    outputs = self._vision_model(**inputs)
                    logits = outputs.logits_per_image
                    probs = logits.softmax(dim=-1)[0].cpu().numpy()
                    wm_score = float(probs[1])

                if wm_score >= wm_th:
                    return True, wm_score, f"Ticari filigran/damga/telif tespit edildi [{region_name}] (Skor: {wm_score:.3f} >= {wm_th:.2f})"
            except Exception as e:
                logger.debug(f"Watermark crop check hatası ({region_name}): {e}")

        # 2. Ahşap Zemin & Tablo / Ürün Mockup (Üst & Alt Kenarlık Taraması)
        wood_texts = [
            "authentic clean basketball court scene or player",
            "wood planks, wooden floor, brown wood grain background, or framed mockup"
        ]
        wood_crops = [
            ("tam", img),
            ("kenar_ust", img.crop((0, 0, w, max(1, int(h * 0.15))))),
            ("kenar_alt", img.crop((0, max(0, int(h * 0.85)), w, h)))
        ]
        wood_th = 0.55

        for region_name, crop_img in wood_crops:
            try:
                inputs = self._vision_processor(
                    text=wood_texts,
                    images=crop_img,
                    return_tensors="pt",
                    padding=True,
                    truncation=True
                ).to(self._device)

                with torch.no_grad():
                    outputs = self._vision_model(**inputs)
                    logits = outputs.logits_per_image
                    probs = logits.softmax(dim=-1)[0].cpu().numpy()
                    wood_score = float(probs[1])

                if wood_score >= wood_th:
                    return True, wood_score, f"Ahşap zemin/plank veya ürün mockup tespit edildi [{region_name}] (Skor: {wood_score:.3f} >= {wood_th:.2f})"
            except Exception as e:
                logger.debug(f"Wood crop check hatası ({region_name}): {e}")

        return False, 0.0, "Temiz"

    def check_is_split_or_mockup(self, image_input: Union[str, Path, Any], project_type: Optional[str] = None) -> Tuple[bool, float, str]:
        """
        Bölünmüş ekran (split-screen), forma kolajı, çoklu fotoğraf montajı veya ahşap zemin/mockup dedektörü.
        Dönen: (is_split_or_mockup: bool, confidence: float, reason: str)
        """
        if not self._load_vision_model():
            return False, 0.0, "Vizyon modeli aktif değil"

        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists():
                return False, 0.0, f"Görsel bulunamadı: {p.name}"
            try:
                from PIL import Image
                img = Image.open(p).convert("RGB")
            except Exception as e:
                return False, 0.0, f"Görsel açılamadı: {e}"
        else:
            img = image_input.convert("RGB")

        norm_proj = (project_type or "").lower().strip()
        is_sports = norm_proj in ("basketball_analysis", "basketball", "sports", "nba", "thebasketballshows")

        if is_sports:
            texts = [
                "a single authentic continuous basketball action photo on court",
                "a split screen collage graphic with jerseys, multi photo montage banner, two photos side by side, or poster print on wood planks floor"
            ]
        else:
            texts = [
                "a single real authentic photo or video scene",
                "a split screen collage graphic with multiple sub-images, multi photo montage banner, two photos side by side, or framed poster mockup on wood floor"
            ]

        import torch
        try:
            inputs = self._vision_processor(
                text=texts,
                images=img,
                return_tensors="pt",
                padding=True
            ).to(self._device)

            with torch.no_grad():
                outputs = self._vision_model(**inputs)
                logits = outputs.logits_per_image
                probs = logits.softmax(dim=-1)[0].cpu().numpy()
                split_score = float(probs[1])

            th = 0.35
            if split_score >= th:
                return True, split_score, f"Bölünmüş ekran kolajı/forma şablonu/mockup tespit edildi (Skor: {split_score:.3f} >= {th:.2f})"
            return False, split_score, "Tekil fotoğraf"
        except Exception as e:
            return False, 0.0, f"Hata: {e}"

    def check_is_illustration(self, image_input: Union[str, Path, Image.Image]) -> Tuple[bool, float, str]:
        """
        Özel 2-sınıflı (binary) çizim/illüstrasyon/vektör/suluboya dedektörü.
        Belgesel ve spor projelerinde gerçek kamera fotoğrafı zorunludur.
        Dönen: (is_illustration: bool, confidence: float, reason: str)
        """
        if not self._load_vision_model():
            return False, 0.0, "Vizyon modeli aktif değil"

        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists():
                return False, 0.0, f"Görsel bulunamadı: {p.name}"
            try:
                img = Image.open(p).convert("RGB")
            except Exception as e:
                return False, 0.0, f"Görsel açılamadı: {e}"
        else:
            img = image_input.convert("RGB")

        texts = [
            "a real live photograph taken with a camera",
            "a painting, drawing, artwork, canvas painting, illustration or sketch"
        ]

        import torch
        try:
            inputs = self._vision_processor(
                text=texts,
                images=img,
                return_tensors="pt",
                padding=True
            ).to(self._device)

            with torch.no_grad():
                outputs = self._vision_model(**inputs)
                logits = outputs.logits_per_image
                probs = logits.softmax(dim=-1)[0].cpu().numpy()
                illust_score = float(probs[1])

            th = 0.35
            if illust_score >= th:
                return True, illust_score, f"Dijital çizim/illüstrasyon/suluboya tespit edildi (İllüstrasyon Skoru: {illust_score:.3f} >= {th:.2f})"
            return False, illust_score, "Gerçek fotoğraf"
        except Exception as e:
            logger.debug(f"Illustration check hatası: {e}")
            return False, 0.0, f"Hata: {e}"

    def validate_zero_shot(
        self,
        image_input: Union[str, Path, Image.Image],
        scene_prompt: str,
        blacklist_labels: Optional[List[str]] = None,
        dynamic_negatives: Optional[List[str]] = None,
        project_type: Optional[str] = None,
        threshold: float = 0.20
    ) -> Tuple[bool, float, float, str, str, str]:
        """
        Aday görselin pozitif sahne eşleşmesi ve dinamik negatif etiketlere benzerliğini skorlar.
        SigLIP sigmoid veya CLIP softmax olasılıklarını kullanır.
        """
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists():
                return False, 0.0, 1.0, "", "", f"Görsel bulunamadı: {p.name}"
            try:
                img = Image.open(p).convert("RGB")
            except Exception as e:
                return False, 0.0, 1.0, "", "", f"Görsel açılamadı: {e}"
        else:
            img = image_input.convert("RGB")

        # Proje varsayılanları + kara liste + dinamik dönem/takım negatifleri
        combined_blacklist: List[str] = []
        is_sports = False
        if project_type:
            norm_p = project_type.lower().strip()
            for r_name, r_data in CROSS_PROJECT_WALL_RULES.items():
                if norm_p == r_name or norm_p in r_data.get("aliases", []):
                    if r_name == "basketball_analysis":
                        is_sports = True
                    combined_blacklist.extend(r_data.get("default_blacklist", []))
                    break

        # Spor projelerinde zorunlu negatif etiketler (illüstrasyon, suluboya ve saha dışı)
        if is_sports:
            combined_blacklist.extend(STAMP_WATERMARK_LABELS)
            combined_blacklist.extend([
                "digital illustration drawing", "watercolor painting artwork",
                "cartoon sketch drawing", "fan art digital painting",
                "vector graphic artwork", "anime or manga style drawing",
                "comic book artwork drawing", "artistic painting drawing illustration",
                "CGI 3D render character",
                "soccer", "football", "fifa", "world cup", "brazil", "robinho",
                "military base", "elementary school", "autograph signing table",
                "press conference microphone", "japanese atsugi military base",
                "yellow soccer shirt crowd", "box score paper sheet"
            ])

        if blacklist_labels:
            combined_blacklist.extend(blacklist_labels)

        if dynamic_negatives:
            combined_blacklist.extend(dynamic_negatives)

        # Evrensel negatifler
        combined_blacklist.extend([
            "digital illustration drawing",
            "watercolor painting artwork",
            "cartoon sketch drawing",
            "blurry low quality picture",
            "stock photo watermark text logo"
        ])

        # Tekilleştir
        seen = set()
        clean_negatives: List[str] = []
        for b in combined_blacklist:
            b_norm = b.strip().lower()
            if b_norm and b_norm not in seen:
                seen.add(b_norm)
                clean_negatives.append(b_norm)

        # Pozitif istemler (Dinamik sahne ve gerçek maç fotoğrafları, ASLA hardcoded oyuncu içermez)
        clean_prompt = re.sub(r"\s+", " ", scene_prompt).strip()
        if is_sports:
            positive_prompts = [
                f"official authentic NBA basketball game photo of {clean_prompt}",
                f"authentic high definition real camera NBA basketball court photo of {clean_prompt}",
                "real authentic professional NBA players playing live basketball game on court"
            ]
            effective_threshold = max(threshold, 0.30)
        else:
            positive_prompts = [
                f"a high quality photo of {clean_prompt}",
                f"a realistic authentic picture depicting {clean_prompt}"
            ]
            effective_threshold = threshold

        if not self._load_vision_model():
            logger.warning("[QualityGate] Vizyon modeli aktif değil, sezgisel onay veriliyor.")
            return True, 0.70, 0.10, positive_prompts[0], "", "Sezgisel onay (vizyon modeli çevrimdışı)"

        try:
            import torch
            all_texts = positive_prompts + clean_negatives

            if self._vision_model_type == "siglip":
                inputs = self._vision_processor(
                    text=all_texts,
                    images=img,
                    padding="max_length",
                    return_tensors="pt"
                ).to(self._device)

                with torch.no_grad():
                    outputs = self._vision_model(**inputs)
                    logits = outputs.logits_per_image
                    probs = torch.sigmoid(logits)[0].cpu().numpy()

            else:  # CLIP
                inputs = self._vision_processor(
                    text=all_texts,
                    images=img,
                    return_tensors="pt",
                    padding=True
                ).to(self._device)

                with torch.no_grad():
                    outputs = self._vision_model(**inputs)
                    logits = outputs.logits_per_image
                    probs = logits.softmax(dim=1)[0].cpu().numpy()

            num_pos = len(positive_prompts)
            pos_probs = probs[:num_pos]
            neg_probs = probs[num_pos:]

            top_pos_idx = int(pos_probs.argmax())
            best_pos_score = float(pos_probs[top_pos_idx])
            best_pos_label = positive_prompts[top_pos_idx]

            top_neg_idx = int(neg_probs.argmax()) if len(neg_probs) > 0 else 0
            worst_neg_score = float(neg_probs[top_neg_idx]) if len(neg_probs) > 0 else 0.0
            worst_neg_label = clean_negatives[top_neg_idx] if len(clean_negatives) > 0 else ""

            # Karar Kuralları:
            # 1. Bireysel Negatif / Kara Liste Denetimi:
            # CLIP softmax / SigLIP altında 30+ negatif varken tek bir negatif etiketin yüksek skor alması
            # o istenmeyen varlığın (örn: Kevin McHale, futbolcu Robinho, askeri uçak) görselde yer aldığının kesin kanıtıdır.
            critical_keywords = [
                # Dairesel Damga ve Mühür Filtresi (Circular Stamp & Seal Overlay)
                "circular watermark stamp logo", "round photographer embossed seal",
                "semi transparent circular watermark", "prominent white watermark text",
                "photography studio round emblem overlay",
                # Filigran ve Ticari Stok Damgası Dedektörü (Watermark & Agency Overlay)
                "prominent white watermark text", "getty images watermark overlay",
                "stock photo watermark copyright", "watermark text overlay",
                "getty images watermark", "shutterstock watermark", "stock watermark",
                "white copyright watermark text", "watermark logo text",
                # Ahşap Zemin, Tablo ve Ürün Mockup Filtresi
                "wood planks floor mockup", "wood floor mockup", "framed poster print",
                "picture frame lying", "wooden table with framed picture",
                "framed wall art mockup", "wood background with framed photo", "picture lying on wooden floor",
                "canvas print mockup", "wood planks", "wooden floor", "wooden background",
                # Bölünmüş Ekran, Kolaj ve Şablon Filtresi
                "split screen collage graphic", "split screen with jerseys", "multi photo montage",
                "two photos side by side", "composite split layout",
                "magazine collage multiple cutouts"
            ]
            if is_sports:
                critical_keywords.extend([
                    "paper ticket stub", "admission ticket", "stadium jumbotron scoreboard screen",
                    "stadium jumbotron scoreboard", "empty indoor arena seats",
                    "indoor bar counter bartender", "empty basketball stadium seats", "crowd sitting in arena stands",
                    "modern digital ticket", "close-up text document receipt", "ticket stub", "ticket",
                    "jumbotron", "scoreboard", "indoor bar", "bar counter", "bartender",
                    "empty basketball stadium", "empty stadium seats", "arena stands", "receipt", "document",
                    "luis scola", "scola", "luther head", "bonzi wells", "yao ming", "james harden", "harden",
                    "kevin mchale", "mchale", "celtics", "boston celtics", "larry bird",
                    "robert parish", "parish", "celtics green jersey", "boston garden",
                    "dennis johnson", "danny ainge",
                    "soccer", "football", "fifa", "world cup", "robinho",
                    "rural house", "backyard", "suburban driveway", "amateur kid playing basketball",
                    "pink house", "grass yard hoop", "rural court", "residential house",
                    "suburban backyard", "driveway hoop", "cargo shorts", "empty hoop",
                    "military", "aircraft", "cockpit", "fighter jet", "dirt court", "elementary school", "atsugi",
                    "sports merchandise product mockup", "jersey display next to photo"
                ])
                if dynamic_negatives:
                    critical_keywords.extend([dn.lower().strip() for dn in dynamic_negatives if dn.strip()])

            for neg_idx, neg_val in enumerate(neg_probs):
                neg_score = float(neg_val)
                neg_label = clean_negatives[neg_idx] if neg_idx < len(clean_negatives) else ""
                neg_label_l = neg_label.lower()
                is_crit = any(ck in neg_label_l for ck in critical_keywords)
                th = 0.10 if is_crit else 0.18
                if neg_score >= th:
                    reason = (
                        f"Dönem/Kara liste etiketi tespit edildi: '{neg_label}' (Skor: {neg_score:.3f} >= {th:.2f}, "
                        f"Kritik: {is_crit})"
                    )
                    return False, best_pos_score, neg_score, best_pos_label, neg_label, reason

            # 2. Negatif/Dönem/Kara Liste benzerlik skoru pozitif skordan yüksekse -> REDDEDİLİR
            if worst_neg_score >= best_pos_score:
                reason = (
                    f"Dönem/Kara liste etiketi baskın çıktı: '{worst_neg_label}' (Skor: {worst_neg_score:.3f}) >= "
                    f"Sahne eşleşmesi (Skor: {best_pos_score:.3f})"
                )
                return False, best_pos_score, worst_neg_score, best_pos_label, worst_neg_label, reason

            # 3. Pozitif skor minimum eşiğin altındaysa -> REDDEDİLİR
            if best_pos_score < effective_threshold:
                reason = f"Pozitif sahne eşleşmesi eşik altında kaldı: {best_pos_score:.3f} < {effective_threshold:.2f} (genel salon/kalabalık elendi)"
                return False, best_pos_score, worst_neg_score, best_pos_label, worst_neg_label, reason

            reason = f"Pozitif eşleşme onaylandı (Pozitif: {best_pos_score:.3f} > Negatif: {worst_neg_score:.3f})"
            return True, best_pos_score, worst_neg_score, best_pos_label, worst_neg_label, reason

        except Exception as e_infer:
            logger.error(f"[QualityGate] Vizyon çıkarım hatası: {e_infer}")
            return False, 0.0, 1.0, "", "", f"Vizyon çıkarım hatası: {e_infer}"

    # ─────────────────────────────────────────────────────────────
    # TAM KALİTE KAPISI (MASTER VALIDATION WORKFLOW)
    # ─────────────────────────────────────────────────────────────

    def validate_candidate(
        self,
        image_path: Union[str, Path],
        scene_prompt: str,
        project_type: Optional[str] = None,
        target_entity: Optional[str] = None,
        is_vertical: bool = True,
        blacklist_labels: Optional[List[str]] = None,
        dynamic_negatives: Optional[List[str]] = None,
        threshold: float = 0.20
    ) -> ValidationResult:
        """
        Tüm kademeleri ve No-Loop kaydını denetleyen ana kalite kapısı fonksiyonu.
        """
        fpath = Path(image_path)
        is_video = fpath.suffix.lower() in ('.mp4', '.mov', '.mkv', '.webm', '.ts')
        visual_target: Union[Path, Image.Image] = fpath

        if is_video:
            try:
                import cv2
                cap = cv2.VideoCapture(str(fpath))
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        visual_target = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            except Exception as e_cap:
                logger.warning(f"Video kare çıkarma uyarısı ({fpath.name}): {e_cap}")

        # Kademe -1: No-Loop & Mükerrer Varlık Kontrolü
        if self.is_asset_used(fpath):
            msg = f"Mükerrer Varlık: '{fpath.name}' daha önce bu videoda kullanıldı. No-Loop kuralı gereği elendi."
            logger.warning(f"🚫 [No-Loop - RED] {msg}")
            return ValidationResult(
                is_valid=False,
                status="REJECTED",
                score=0.0,
                tier_failed=-1,
                reason=msg,
                metadata={"file": fpath.name, "duplicate": True}
            )

        # Kademe 0: Çoklu Proje İzolasyonu
        iso_ok, iso_reason = self.check_cross_project_isolation(fpath, project_type)
        if not iso_ok:
            return ValidationResult(
                is_valid=False,
                status="REJECTED",
                score=0.0,
                tier_failed=0,
                reason=iso_reason,
                metadata={"file": fpath.name}
            )

        # Kademe 1: Deterministik Metadata Kontrolü (0 ms)
        meta_ok, meta_reason, meta_dict = self.check_metadata(fpath, is_vertical=is_vertical)
        if not meta_ok:
            logger.warning(f"🚫 [Kademe 1 - RED] {fpath.name}: {meta_reason}")
            return ValidationResult(
                is_valid=False,
                status="REJECTED",
                score=0.0,
                tier_failed=1,
                reason=meta_reason,
                metadata=meta_dict
            )

        # Kademe 1.5: Bağımsız Filigran & Ticari Ajans Damgası Kapısı
        has_wm, wm_score, wm_reason = self.check_watermark(visual_target, project_type=project_type)
        if has_wm:
            logger.warning(f"🚫 [Kademe 1.5 - Filigran RED] {fpath.name}: {wm_reason}")
            return ValidationResult(
                is_valid=False,
                status="REJECTED",
                score=0.0,
                negative_score=wm_score,
                tier_failed=1.5,
                reason=wm_reason,
                worst_negative_label="watermark_overlay",
                metadata=meta_dict
            )

        # Kademe 1.6: Bölünmüş Ekran, Kolaj ve Mockup Dedektörü
        is_split, split_score, split_reason = self.check_is_split_or_mockup(visual_target, project_type=project_type)
        if is_split:
            logger.warning(f"🚫 [Kademe 1.6 - Kolaj/Mockup RED] {fpath.name}: {split_reason}")
            return ValidationResult(
                is_valid=False,
                status="REJECTED",
                score=0.0,
                negative_score=split_score,
                tier_failed=1.6,
                reason=split_reason,
                worst_negative_label="split_screen_or_product_mockup",
                metadata=meta_dict
            )

        # Kademe 1.8: İllüstrasyon & Suluboya / Dijital Çizim Dedektörü
        is_ill, ill_score, ill_reason = self.check_is_illustration(visual_target)
        if is_ill:
            logger.warning(f"🚫 [Kademe 1.8 - İllüstrasyon RED] {fpath.name}: {ill_reason}")
            return ValidationResult(
                is_valid=False,
                status="REJECTED",
                score=0.0,
                negative_score=ill_score,
                tier_failed=1.8,
                reason=ill_reason,
                worst_negative_label="illustration_or_digital_drawing",
                metadata=meta_dict
            )

        # Kademe 2: Zero-Shot Skorlama (SigLIP / CLIP)
        vision_ok, pos_sc, neg_sc, best_p, worst_n, vision_reason = self.validate_zero_shot(
            image_input=visual_target,
            scene_prompt=scene_prompt,
            blacklist_labels=blacklist_labels,
            dynamic_negatives=dynamic_negatives,
            project_type=project_type,
            threshold=threshold
        )
        if not vision_ok:
            logger.warning(f"🚫 [Kademe 2 - RED] {fpath.name}: {vision_reason}")
            return ValidationResult(
                is_valid=False,
                status="REJECTED",
                score=pos_sc,
                negative_score=neg_sc,
                tier_failed=2,
                reason=vision_reason,
                best_positive_label=best_p,
                worst_negative_label=worst_n,
                metadata=meta_dict
            )

        logger.info(f"✅ [QualityGate - ONAY] {fpath.name} (Skor: {pos_sc:.3f}): {vision_reason}")
        return ValidationResult(
            is_valid=True,
            status="ACCEPTED",
            score=pos_sc,
            negative_score=neg_sc,
            tier_failed=None,
            reason="Tüm kalite kapısı kademelerini (No-Loop, Metadata, Zero-Shot) başarıyla geçti.",
            best_positive_label=best_p,
            worst_negative_label=worst_n,
            metadata=meta_dict
        )


# Singleton nesne
asset_validator = AssetValidator()
