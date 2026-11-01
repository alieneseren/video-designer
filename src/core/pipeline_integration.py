"""
core/pipeline_integration.py
============================
Pre-Render Quality Gate (Modül 3): Retry Döngüsü, Aday Havuzu ve İş Akışı Entegrasyonu.
(Retry Loop, Candidate Pool Expansion & Pipeline Integration)

Mimarî Güncellemeler:
1. Genişletilmiş Aday Havuzu (Candidate Pool Expansion: 8-10 Aday):
   - Her sahne için en az 8-10 aday denenerek havuzun erken tükenmesi önlenir.
2. No-Loop Takibi & Kaydı:
   - Onaylanan her görsel asset_validator.register_used_asset ile kaydedilir.
   - Tekrarlanan görseller No-Loop kuralı ile anında elenir.
3. Dinamik Negatif Etiket Desteği:
   - query_builder tarafından sağlanan dinamik negatifler doğrulayıcıya aktarılır.
4. Deterministik Güvenli Fallback:
   - Tüm adaylar elenirse ASLA eski görsellere dönülmez; estetik degrade/arşiv arka planı devreye girer.
5. Süre Tamponu Entegrasyonu (+0.60s):
   - Dış ses süresi + 0.60s olarak kilitlenir.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable, Union
from PIL import Image, ImageDraw

try:
    from core.asset_validator import asset_validator, ValidationResult
except ImportError:
    from src.core.asset_validator import asset_validator, ValidationResult

try:
    from core.timeline_guard import timeline_guard
except ImportError:
    from src.core.timeline_guard import timeline_guard

try:
    from core.query_builder import query_builder
except ImportError:
    from src.core.query_builder import query_builder

logger = logging.getLogger("PipelineIntegration")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class PipelineIntegration:
    """
    Kalite kapısı ile video üretim boru hattı arasındaki köprü ve retry orkestratörü.
    """

    # ─────────────────────────────────────────────────────────────
    # 1. DETERMINİSTİK GÜVENLİ FALLBACK ÜRETİCİ
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def generate_safe_fallback_background(
        output_path: Union[str, Path],
        project_type: str = "basketball_analysis",
        scene_idx: int = 0,
        width: int = 1080,
        height: int = 1920
    ) -> Path:
        """
        Tüm adaylar reddedildiğinde devreye giren yüksek çözünürlüklü estetik degrade arkaplan.
        Asla rastgele/alakasız stok görsel veya loop kullanılmasını engeller.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGB", (width, height), (11, 17, 32))
        draw = ImageDraw.Draw(img)

        # Proje tipine göre zarif degrade paleti
        proj = (project_type or "").lower()
        if any(k in proj for k in ["basketball", "nba", "thebasketballshows", "sports"]):
            # Gece mavisi -> Koyu odun kömürü, altın vurgulu dikey degrade
            top_color = (15, 23, 42)      # Deep Slate
            bottom_color = (2, 6, 23)     # Midnight Black
            accent_glow = (251, 191, 36)  # Altın sarısı
        elif any(k in proj for k in ["aviation", "flight", "disaster"]):
            top_color = (30, 41, 59)
            bottom_color = (15, 23, 42)
            accent_glow = (56, 189, 248)  # Buz mavisi
        else:
            top_color = (17, 24, 39)
            bottom_color = (3, 7, 18)
            accent_glow = (147, 51, 234)

        # Dikey Degrade Çizimi
        for y in range(height):
            ratio = y / float(height)
            r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
            g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
            b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Hafif radyal parıltı (Sahneye göre hafif değişken odak)
        glow_center_y = int(height * (0.35 + (scene_idx % 3) * 0.15))
        glow_radius = int(width * 0.45)

        glow_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_overlay)
        glow_draw.ellipse(
            [
                (width // 2) - glow_radius,
                glow_center_y - glow_radius,
                (width // 2) + glow_radius,
                glow_center_y + glow_radius
            ],
            fill=(accent_glow[0], accent_glow[1], accent_glow[2], 18)
        )
        img = Image.alpha_composite(img.convert("RGBA"), glow_overlay).convert("RGB")
        img.save(out_p, "JPEG", quality=95)

        logger.warning(
            f"🛡️ [PipelineIntegration] Güvenli deterministik fallback görseli üretildi: {out_p.name} "
            f"({width}x{height}, Tema: {project_type})"
        )
        return out_p

    # ─────────────────────────────────────────────────────────────
    # 2. RETRY DÖNGÜSÜ İLE GÜVENLİ VARLIK SEÇİMİ (8-10 ADAY)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def fetch_and_validate_scene_asset(
        cls,
        candidate_generator_fn: Callable[[int], Optional[Union[str, Path]]],
        scene_idx: int,
        scene_prompt: str,
        project_type: str = "basketball_analysis",
        target_entity: Optional[str] = None,
        max_attempts: int = 10,
        work_dir: Optional[Union[str, Path]] = None,
        is_vertical: bool = True,
        blacklist_labels: Optional[List[str]] = None,
        dynamic_negatives: Optional[List[str]] = None
    ) -> Tuple[Path, ValidationResult]:
        """
        Bir sahne için en az max_attempts (8-10) aday görsel çekip doğrular.
        - İlk geçerli aday onaylanır ve used_assets kümesine kaydedilir.
        - Reddedilen adayın dosyası temizlenir.
        - Havuz tükenirse kesinlikle başa sarılmaz; deterministik degrade fallback devreye girer.
        """
        last_result: Optional[ValidationResult] = None

        # Eğer dinamik negatifler verilmemişse QueryBuilder ile sahne prompt'undan üret
        if not dynamic_negatives and query_builder is not None:
            cq = query_builder.build_context_locked_queries(scene_prompt, fallback_entity=target_entity or "NBA Player")
            dynamic_negatives = cq.dynamic_negatives

        for attempt in range(1, max_attempts + 1):
            logger.info(f"[QualityGate - Retry] Sahne {scene_idx} - Aday #{attempt}/{max_attempts} isteniyor...")
            candidate_path = candidate_generator_fn(attempt)
            if not candidate_path:
                logger.warning(f"[QualityGate - Retry] Aday #{attempt} arama motoru tarafından temin edilemedi.")
                continue

            c_p = Path(candidate_path)
            if not c_p.exists():
                continue

            # Kalite Kapısından Geçir (No-Loop + Metadata + SigLIP/CLIP)
            result = asset_validator.validate_candidate(
                image_path=c_p,
                scene_prompt=scene_prompt,
                project_type=project_type,
                target_entity=target_entity,
                is_vertical=is_vertical,
                blacklist_labels=blacklist_labels,
                dynamic_negatives=dynamic_negatives
            )
            last_result = result

            if result.is_valid:
                logger.info(f"🎯 [QualityGate] Sahne {scene_idx} adayı #{attempt} ONAYLANDI: {c_p.name} (Skor: {result.score:.2f})")
                # No-Loop kaydına ekle
                asset_validator.register_used_asset(c_p)
                return c_p, result
            else:
                logger.warning(
                    f"🚫 [QualityGate] Sahne {scene_idx} adayı #{attempt} REDDEDİLDİ ({result.reason}): {c_p.name}"
                )
                try:
                    if c_p.exists():
                        c_p.unlink()
                except Exception as e_del:
                    logger.debug(f"Reddedilen dosya silme uyarısı: {e_del}")

        # Tüm adaylar reddedildi! ASLA LOOP YAPILMAZ -> Güvenli Fallback atanır
        logger.error(
            f"❌ [QualityGate] Sahne {scene_idx} için tüm adaylar ({max_attempts} deneme) kalite kapısına takıldı! "
            f"Başa sarılmıyor (No-Loop), deterministik estetik degrade atanıyor."
        )
        target_dir = Path(work_dir) if work_dir else Path("/tmp")
        fallback_path = target_dir / f"scene_{scene_idx:02d}_safe_fallback.jpg"
        cls.generate_safe_fallback_background(fallback_path, project_type=project_type, scene_idx=scene_idx)
        asset_validator.register_used_asset(fallback_path)

        fallback_result = ValidationResult(
            is_valid=True,
            status="ACCEPTED",
            score=0.80,
            tier_failed=None,
            reason="Deterministik güvenli fallback görseli devreye alındı (No-Loop kuralı).",
            metadata={"is_fallback": True, "attempts_tried": max_attempts}
        )
        return fallback_path, fallback_result

    # ─────────────────────────────────────────────────────────────
    # 3. ZAMAN ÇİZELGESİ VE SÜRE KİLİDİ ENTEGRASYONU (+0.60s)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def apply_timeline_locks(
        cls,
        audio_path: Union[str, Path],
        tail_padding_sec: float = 0.60
    ) -> Dict[str, Any]:
        """
        Dış ses dosyasının süresini okuyup +0.60s tampon ile kesin video kompozisyon süresini kilitler.
        """
        return timeline_guard.calculate_locked_timeline_duration(audio_path, tail_padding_sec=tail_padding_sec)


# Singleton nesne
pipeline_integration = PipelineIntegration()
