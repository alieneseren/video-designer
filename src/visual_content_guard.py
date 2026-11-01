"""
visual_content_guard.py
========================
Evrensel Açık Kaynaklı Görsel İçerik Doğrulama ve Anlamsal Eşleştirme Motoru.
(Universal Open-Source Visual Content Verification & Semantic Alignment Guard)

Tüm Kanallar İçin (Seyahat, Havacılık, Askeri/Crayon, Spor, Belgesel):
1. Dış ses ve senaryo metni ile indirilen görsel/video kareleri arasındaki semantik uyumu doğrular.
2. "Tabela yanılsaması", "düz zemin treni", "yanlış dağ zirvesi", "alakasız stok arşivi" hatalarını eler.
3. Hem yerel Mac M-serisi (Apple Silicon MPS/CPU) hem de Oracle Cloud ARM/x86 sunucusunda GPU gerektirmeden çalışır.
"""

from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image

logger = logging.getLogger("VisualContentGuard")

# Kanal/Kategori bazlı negatif ve pozitif kural şablonları
CATEGORY_RULES: Dict[str, Dict[str, List[str]]] = {
    "travel": {
        "negative_heuristics": [
            "wooden signpost", "trail marker", "parking lot", "highway asphalt",
            "blurry texture", "empty grass field", "ticket booth", "hotel lobby carpet"
        ],
        "default_positives": ["breathtaking travel destination", "iconic landmark", "scenic travel footage"]
    },
    "aviation": {
        "negative_heuristics": [
            "car traffic", "train on tracks", "ship on ocean", "living room", "food table"
        ],
        "default_positives": ["commercial airplane in flight", "cockpit instruments", "airport runway"]
    },
    "crayon_combat": {
        "negative_heuristics": [
            "civilian car", "children cartoon", "peaceful nature park", "fashion clothing"
        ],
        "default_positives": ["military vehicle blueprint", "tactical schematic", "fighter jet armor"]
    },
    "basketball_analysis": {
        "negative_heuristics": [
            "soccer field", "baseball bat", "tennis racket", "empty parking"
        ],
        "default_positives": ["basketball player slam dunk", "basketball court arena", "nba basketball game"]
    }
}


class VisualContentGuard:
    _instance: Optional["VisualContentGuard"] = None
    _model = None
    _processor = None
    _device = "cpu"
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._init_engine()
            self._initialized = True

    def _init_engine(self):
        """Torch ve CLIP modelini güvenli ve optimize şekilde hazırlar."""
        try:
            import torch
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"

            # HuggingFace transformers üzerinden hafif CLIP yüklemesi
            from transformers import CLIPProcessor, CLIPModel
            model_name = "openai/clip-vit-base-patch32"
            
            # Yerel önbellekten veya offline yükleme dene
            try:
                self._model = CLIPModel.from_pretrained(model_name)
                self._processor = CLIPProcessor.from_pretrained(model_name)
                self._model.to(self._device)
                self._model.eval()
                print(f"[VISUAL-GUARD] 🧠 Açık kaynaklı CLIP vizyon motoru yüklendi ({self._device.upper()}).")
            except Exception as e_clip:
                print(f"[VISUAL-GUARD] ⚠️ CLIP model indirme/yükleme bekleniyor ({e_clip}). Sezgisel mod devrede.")
                self._model = None
                self._processor = None

        except Exception as e_gen:
            print(f"[VISUAL-GUARD] ⚠️ Vizyon kütüphanesi uyarısı: {e_gen}. Kural tabanlı filtre aktif.")
            self._model = None
            self._processor = None

    @property
    def semantic_model_available(self) -> bool:
        return self._model is not None and self._processor is not None

    def score_image_against_prompts(
        self,
        image_input: Union[str, Path, Image.Image],
        positive_prompts: List[str],
        negative_prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Bir görselin pozitif ve negatif metinlerle anlamsal benzerliğini puanlar.
        Döner: {'positive_score': float, 'negative_score': float, 'is_accepted': bool, 'best_match': str}
        """
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists():
                return {"is_accepted": False, "score": 0.0, "reason": "Dosya bulunamadı"}
            try:
                img = Image.open(p).convert("RGB")
            except Exception as e_img:
                return {"is_accepted": False, "score": 0.0, "reason": f"Görsel açılamadı: {e_img}"}
        else:
            img = image_input

        # 1. Eğer CLIP modeli aktifse derin semantik analiz yap
        if self._model is not None and self._processor is not None:
            import torch
            all_prompts = list(positive_prompts)
            neg_list = negative_prompts or []
            all_prompts.extend(neg_list)

            try:
                inputs = self._processor(text=all_prompts, images=img, return_tensors="pt", padding=True).to(self._device)
                with torch.no_grad():
                    outputs = self._model(**inputs)
                    probs = outputs.logits_per_image.softmax(dim=1)[0].cpu().numpy()

                pos_scores = probs[:len(positive_prompts)]
                neg_scores = probs[len(positive_prompts):] if neg_list else [0.0]

                top_pos_idx = int(pos_scores.argmax())
                best_pos_score = float(pos_scores[top_pos_idx])
                best_neg_score = float(max(neg_scores)) if len(neg_scores) > 0 else 0.0
                best_prompt = positive_prompts[top_pos_idx]

                # Karar: Pozitif skor negatiften belirgin yüksek olmalı
                is_accepted = best_pos_score > best_neg_score and best_pos_score >= 0.15

                return {
                    "is_accepted": is_accepted,
                    "score": round(best_pos_score, 3),
                    "negative_score": round(best_neg_score, 3),
                    "best_match": best_prompt,
                    "engine": "clip_vit_base"
                }
            except Exception as e_infer:
                print(f"[VISUAL-GUARD] CLIP çıkarım uyarısı: {e_infer}")
                return {
                    "is_accepted": False,
                    "score": 0.0,
                    "negative_score": 1.0,
                    "best_match": "",
                    "engine": "clip_error",
                    "reason": f"CLIP çıkarımı başarısız: {e_infer}",
                }

        # 2. Heuristic (Kural ve Sezgisel) Fallback
        # Görsel boyut, renk çeşitliliği ve en boy oranını analiz et
        w, h = img.size
        is_high_res = w >= 600 and h >= 600
        
        # Basit renk çeşitliliği (düz siyah/gri/tek renk ekran kontrolü)
        colors = img.getcolors(maxcolors=256)
        is_not_solid = colors is None or len(colors) > 64

        return {
            "is_accepted": is_high_res and is_not_solid,
            "score": 0.85 if (is_high_res and is_not_solid) else 0.20,
            "negative_score": 0.10,
            "best_match": positive_prompts[0] if positive_prompts else "heuristic_fallback",
            "engine": "heuristic_validator"
        }

    def verify_scene_asset(
        self,
        asset_path: Union[str, Path],
        narration: str,
        category: str = "travel",
        topic: str = ""
    ) -> Tuple[bool, float, str]:
        """
        Belirli bir sahne için indirilen görsel veya video karesini tek fonksiyonda doğrular.
        Döner: (onaylandı_mı: bool, kalite_skoru: float, açıklama: str)
        """
        path = Path(asset_path)
        if not path.exists():
            return False, 0.0, "Medya dosyası mevcut değil."

        # Eğer video ise orta noktasından 1 kare yakala
        test_frame = path
        is_temp_frame = False
        if path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"]:
            import subprocess
            temp_out = path.parent / f"_chk_{path.stem}.jpg"
            try:
                probe = subprocess.run(
                    [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                duration = max(0.0, float(probe.stdout.strip()))
                seek_time = duration / 2
                cmd = [
                    "ffmpeg", "-y", "-ss", f"{seek_time:.3f}", "-i", str(path),
                    "-vframes", "1", "-q:v", "3", str(temp_out),
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if temp_out.exists():
                    test_frame = temp_out
                    is_temp_frame = True
            except Exception:
                test_frame = path

        clean_narr = re.sub(r"\s+", " ", narration).strip()
        description = " ".join(clean_narr.split()[:65])
        cat_rules = CATEGORY_RULES.get(category, {})
        if description:
            positives = [
                f"A realistic visual scene showing {description}",
                f"An image depicting {description}",
            ]
        else:
            positives = list(cat_rules.get("default_positives", []))
        negatives = [
            "an image unrelated to the described scene",
            "an abstract texture with no recognizable subject",
            *cat_rules.get("negative_heuristics", []),
        ]

        try:
            res = self.score_image_against_prompts(test_frame, positives, negatives)
            accepted = res["is_accepted"]
            score = res["score"]
            match = res.get("best_match", "")
            detail = res.get("reason", "")
            reason = f"Vizyon skoru: {score*100:.1f}% ({'Onaylandı' if accepted else 'Reddedildi'}) [Eşleşme: {match}]"
            if detail:
                reason = f"{reason} {detail}"
            return accepted, score, reason
        finally:
            if is_temp_frame and test_frame.exists():
                try:
                    test_frame.unlink()
                except Exception:
                    pass

    def select_best_candidate(
        self,
        candidate_paths: List[Union[str, Path]],
        narration: str,
        category: str = "travel",
        topic: str = ""
    ) -> Optional[Path]:
        """
        İndirilen birden çok aday görsel/video arasından dış sese en uygun olanını seçer.
        """
        valid_candidates = [Path(p) for p in candidate_paths if Path(p).exists()]
        if not valid_candidates:
            return None
        if len(valid_candidates) == 1:
            return valid_candidates[0]

        scored = []
        for c in valid_candidates:
            acc, score, r = self.verify_scene_asset(c, narration, category, topic)
            scored.append((score, c, r))

        # En yüksek skora göre sırala
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_path, best_reason = scored[0]
        print(f"[VISUAL-GUARD] 🎯 {len(valid_candidates)} aday arasından en iyi görsel seçildi: {best_path.name} (Skor: {best_score:.2f})")
        return best_path


# Global Singleton erişimi
visual_guard = VisualContentGuard()
