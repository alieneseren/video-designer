"""
Global Asset Registry & Whitelist Memory
Manages cross-video used asset tracking, pool de-duplication, and smart shuffling
to prevent loop crashes and ensure 100% visual variety across YouTube Shorts.
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional

logger = logging.getLogger("GlobalAssetRegistry")


class GlobalAssetRegistry:
    def __init__(self, memory_file: Optional[Path] = None):
        if memory_file is None:
            base = Path(__file__).resolve().parent.parent.parent / "assets" / "curated_sports"
            if not base.exists():
                base = Path("/home/ubuntu/yt-remote-worker/assets/curated_sports")
            memory_file = base / "global_used_assets.json"
        self.memory_file = memory_file
        self.data: Dict[str, Dict[str, List[str]]] = self._load()

    def _load(self) -> Dict[str, Dict[str, List[str]]]:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load global memory: {e}")
        return {}

    def _save(self):
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save global memory: {e}")

    def get_used_assets(self, channel: str, athlete_key: str) -> List[str]:
        return self.data.get(channel, {}).get(athlete_key, [])

    def register_job_assets(self, channel: str, athlete_key: str, used_filenames: List[str]):
        """Yeni üretilen videoda kullanılan varlıkları küresel hafızaya kaydeder."""
        if channel not in self.data:
            self.data[channel] = {}
        if athlete_key not in self.data[channel]:
            self.data[channel][athlete_key] = []

        current = self.data[channel][athlete_key]
        for fn in used_filenames:
            if fn not in current:
                current.append(fn)

        # En fazla son 60 kullanılan varlığı tut (FIFO rotasyonu)
        if len(current) > 60:
            self.data[channel][athlete_key] = current[-60:]

        self._save()
        logger.info(f"Registered {len(used_filenames)} assets for {channel}/{athlete_key} in global memory.")

    def select_unique_photos(
        self,
        candidate_photos: List[Path],
        needed_count: int,
        channel: str,
        athlete_key: str,
        seed: str
    ) -> List[Path]:
        """
        Pozitif beyaz listeden önceki videolarda kullanılmamış,
        tamamen benzersiz ve karıştırılmış fotoğraf seçkisi döner.
        """
        used_history = set(self.get_used_assets(channel, athlete_key))
        
        # 1. Aşama: Son videolarda hiç kullanılmamış taze fotoğraflar
        fresh_photos = [p for p in candidate_photos if p.name not in used_history]
        
        # Eğer taze fotoğraflar yeterliyse doğrudan kullan
        if len(fresh_photos) >= needed_count:
            selected_pool = list(fresh_photos)
        else:
            # Havuz yetersizse, en eski kullanılanları devreye al (havuzu sıfırlama rotasyonu)
            logger.warning(
                f"Taze varlık sayısı ({len(fresh_photos)}) gereken kesme sayısından ({needed_count}) az. "
                f"Tüm onaylı havuz ({len(candidate_photos)}) akıllı rotasyona alınıyor."
            )
            # Hafızadaki en son kullanılanları sona at, en eskileri başa al
            used_ordered = self.get_used_assets(channel, athlete_key)
            used_weight = {fn: idx for idx, fn in enumerate(used_ordered)}
            
            # Az kullanılan veya hiç kullanılmayanlara öncelik veren sıralama
            sorted_candidates = sorted(candidate_photos, key=lambda p: used_weight.get(p.name, -1))
            selected_pool = sorted_candidates

        # 2. Aşama: Deterministik ama rastgele akıllı karıştırma (Seed-based shuffle)
        # Her video ID için farklı bir montaj kompozisyonu üretir, alfabetik sırayı bozar
        rng = random.Random(seed)
        rng.shuffle(selected_pool)

        # 3. Aşama: Tekillik güvencesi - asla aynı görsel listede iki kez yer alamaz
        unique_result: List[Path] = []
        seen_names: Set[str] = set()
        for p in selected_pool:
            if p.name not in seen_names:
                unique_result.append(p)
                seen_names.add(p.name)
            if len(unique_result) == needed_count:
                break

        return unique_result


global_asset_registry = GlobalAssetRegistry()
