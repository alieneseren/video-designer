"""
core/asset_fetcher.py
=====================
Çoklu Sorgu Genişletmesi & Minimum İndirme Kotası Motoru.
(Multi-Query Expansion & Minimum Asset Quota Engine)

Amaç:
- Aday Havuzu Kıtlığı (Fetch Starvation) ve 3 Görselli Sonsuz Döngü hatasını
  ortadan kaldırmak için arama motorunu çoklu-sorgu ile zenginleştirir.
- Her video için tek bir sorguyla yetinmeyip en az 5-10 farklı aksiyon varyasyonu üretir.
- MediaWiki API'sine uygun unquoted ve aşamalı anahtar kelime gevşetmesi (term relaxation)
  ile yüksek aday getirisi sağlar.
- İndirilen her adayı SigLIP / CLIP vizyon motoruyla denetler (Quality Gate).
- Minimum havuz kotası (min_unique_assets = 15) dolana kadar arama ve doğrulamaya devam eder.
- Tekrarları (MD5 hash + URL tracking) engeller.
"""

from __future__ import annotations

import re
import os
import time
import shutil
import logging
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Union
from PIL import Image, ImageEnhance, ImageFilter

import requests

try:
    from core.query_builder import query_builder, QueryBuilder
except ImportError:
    try:
        from src.core.query_builder import query_builder, QueryBuilder
    except ImportError:
        query_builder = None
        QueryBuilder = None

try:
    from core.asset_validator import asset_validator, AssetValidator
except ImportError:
    try:
        from src.core.asset_validator import asset_validator, AssetValidator
    except ImportError:
        asset_validator = None
        AssetValidator = None

logger = logging.getLogger("AssetFetcher")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

WIKIMEDIA_USER_AGENT = "YouTubeAutomatedSportsVideoEngine/2.2 (contact: admin@basketballshows.internal)"
COMMERCIAL_STOCK_DOMAINS = [
    "gettyimages", "istockphoto", "shutterstock", "alamy",
    "dreamstime", "depositphotos", "stock.adobe", "123rf",
    "vectorstock", "bigstockphoto", "canstockphoto", "imagebank",
    "watermark", "stockphoto", "gty.im", "gty", "wireimage"
]

BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "57648418-49ecb0060f2db281a386d04cf")

# Spor dışı, kara liste veya alakasız etiketler (Bilet, Salon, Bar ve Yanlış Oyuncu Korumalı)
BLACK_LISTED_TERMS = [
    "offensive lineman", "lineman", "football", "nfl", "soccer", "baseball",
    "hockey", "rugby", "helmet", "tennis", "golf", "bengals", "panthers",
    "logo", "signature", "sig.", "icon", "symbol", "diagram", "robinho",
    "brazil", "world cup", "fifa", "military", "atsugi", "signing",
    "celtics", "boston", "mchale", "parish", "larry bird", "larry_bird",
    "rural", "backyard", "driveway", "cargo", "pink_house", "house", "playground",
    "drawing", "clipart", "illustration", "cartoon", "vector",
    # Bilet, Jumbotron, Tribün ve Boş Salon / Bar Sızıntıları
    "ticket", "stub", "ticket stub", "ticket_stub", "jumbotron", "scoreboard",
    "concession", "bar", "arena bar", "arena seats", "empty arena", "crowd in stands",
    "admission", "admission ticket", "receipt", "document",
    # Yanlış Dönem Oyuncuları (2000'ler Rockets sızıntısı)
    "scola", "luis scola", "luther head", "luther_head", "bonzi wells", "bonzi_wells",
    "yao ming", "yao_ming", "harden", "james harden"
]


def format_sports_image(src_path: Union[str, Path], dst_path: Union[str, Path], target_w: int = 1080, target_h: int = 1920) -> bool:
    """Görseli 9:16 dikey oranına akıllı crop edip sinematik kontrast/keskinlik ekler."""
    try:
        src_p = Path(src_path)
        dst_p = Path(dst_path)
        dst_p.parent.mkdir(parents=True, exist_ok=True)

        im = Image.open(src_p).convert("RGB")
        src_w, src_h = im.size
        src_ratio = src_w / src_h
        tgt_ratio = target_w / target_h

        if src_ratio > tgt_ratio:
            new_h = target_h
            new_w = int(new_h * src_ratio)
        else:
            new_w = target_w
            new_h = int(new_w / src_ratio)

        im = im.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        im = im.crop((left, top, left + target_w, top + target_h))

        # Kontrast ve doygunluk
        enh = ImageEnhance.Contrast(im)
        im = enh.enhance(1.08)
        col = ImageEnhance.Color(im)
        im = col.enhance(1.05)

        im.save(dst_p, "JPEG", quality=95)
        return True
    except Exception as e:
        logger.warning(f"format_sports_image hatası ({src_path}): {e}")
        return False


class AssetFetcher:
    """
    Çoklu-sorgu genişletmesi ve deterministik kalite kapısı ile
    minimum 15-20 zengin NBA maç görseli toplayan otonom varlık motoru.
    """

    def __init__(self, validator: Optional[AssetValidator] = None, q_builder: Optional[QueryBuilder] = None):
        self.validator = validator or asset_validator or AssetValidator()
        self.q_builder = q_builder or query_builder or QueryBuilder()

    @staticmethod
    def clean_query_for_wikimedia(raw_query: str) -> List[str]:
        """
        MediaWiki API'sinin 0 sonuç dönmesini engelleyen temiz arama varyantları türetir.
        Karakter adını KESİNLİKLE korur; asla salt takım veya genel salon sorgusu üretmez.
        """
        # Tırnaklı ana karakter(ler)i tespit et (örn: '"Hakeem Olajuwon"')
        quoted_entities = re.findall(r'"([^"]+)"', raw_query)
        unquoted_rest = re.sub(r'"[^"]+"', '', raw_query).strip()
        rest_words = [w for w in unquoted_rest.split() if w.strip()]

        variants: List[str] = [raw_query]

        if quoted_entities:
            main_ent = quoted_entities[0]
            # 1. Tırnaklı tam eşleşme varyantları
            if rest_words:
                variants.append(f'"{main_ent}" {" ".join(rest_words[:3])}')
                variants.append(f'"{main_ent}" {" ".join(rest_words[:2])}')
            variants.append(f'"{main_ent}" basketball')
            variants.append(f'"{main_ent}" NBA')

            # 2. MediaWiki esnek tam isim varyantları (Karakter adı daima korunur)
            if rest_words:
                variants.append(f"{main_ent} {' '.join(rest_words[:2])}")
            variants.append(f"{main_ent} basketball")
            variants.append(f"{main_ent} NBA")
        else:
            # Tırnak yoksa kelimelerden türet ama en az ilk 2 kelimeyi (oyuncu adı) zorunlu tut
            clean = re.sub(r'["\']', '', raw_query).strip()
            words = clean.split()
            variants.append(clean)
            if len(words) >= 2:
                player_base = f"{words[0]} {words[1]}"
                if len(words) > 3:
                    variants.append(f"{player_base} {' '.join(words[2:4])}")
                variants.append(f"{player_base} basketball")
                variants.append(f"{player_base} NBA")

        seen = set()
        out = []
        for v in variants:
            v_s = v.strip()
            if v_s and v_s.lower() not in seen:
                seen.add(v_s.lower())
                out.append(v_s)
        return out

    @classmethod
    def search_wikimedia_commons(cls, query: str, limit: int = 15, bad_keywords: Optional[List[str]] = None) -> List[str]:
        """Wikimedia Commons API üzerinden gerçek NBA fotoğraflarını arar (Negatif hariç tutma ve bilet/salon korumalı)."""
        bad_words = set((bad_keywords or []) + BLACK_LISTED_TERMS)
        query_variants = cls.clean_query_for_wikimedia(query)
        urls: List[str] = []
        seen_urls: Set[str] = set()

        # Negatif arama hariç tutmaları (MediaWiki gsrsearch için)
        neg_suffix = " -ticket -stub -jumbotron -scoreboard -concession -bar -arena -Scola -Head -Harden"

        for q_try in query_variants:
            if len(urls) >= limit:
                break
            try:
                api_url = "https://commons.wikimedia.org/w/api.php"
                # MediaWiki API'sine negatif filtreleri zincirle
                search_query = f"{q_try}{neg_suffix}" if "-" not in q_try else q_try
                params = {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": search_query,
                    "gsrnamespace": 6,  # 6 = File namespace
                    "gsrlimit": limit * 2,
                    "prop": "imageinfo",
                    "iiprop": "url|size|mime",
                    "format": "json"
                }
                headers = {"User-Agent": WIKIMEDIA_USER_AGENT}
                resp = requests.get(api_url, params=params, headers=headers, timeout=8)
                if resp.status_code != 200:
                    continue

                try:
                    data = resp.json()
                except Exception:
                    continue

                pages = data.get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    title = str(pdata.get("title", "")).lower()
                    # Katı negatif kelime denetimi (Bilet, salon, bar, Scola, Yao Ming, Harden vb.)
                    if any(bad in title for bad in bad_words):
                        continue

                    infos = pdata.get("imageinfo", [])
                    if not infos:
                        continue
                    u = infos[0].get("url")
                    if not u or u in seen_urls:
                        continue

                    u_lower = u.lower()
                    if any(bad in u_lower for bad in bad_words):
                        continue

                    clean_u = u_lower.split("?")[0]
                    if clean_u.endswith((".jpg", ".jpeg", ".png", ".webp")):
                        seen_urls.add(u)
                        urls.append(u)
                        if len(urls) >= limit:
                            break
            except Exception as e:
                logger.debug(f"Wikimedia sorgu uyarısı ('{q_try}'): {e}")

        return urls

    @classmethod
    def search_pixabay_photos(cls, query: str, limit: int = 5) -> List[str]:
        """Pixabay API üzerinden gerçek basketbol maç fotoğrafları arar."""
        if not PIXABAY_API_KEY:
            return []
        try:
            clean_q = re.sub(r'["\']', '', query).strip()
            api_url = (
                f"https://pixabay.com/api/?key={PIXABAY_API_KEY}"
                f"&q={urllib.parse.quote(clean_q)}"
                f"&image_type=photo&per_page=15&safesearch=true"
            )
            resp = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                urls = []
                for h in hits:
                    u = h.get("largeImageURL") or h.get("webformatURL")
                    tags = str(h.get("tags", "")).lower()
                    if any(b in tags for b in ["cartoon", "drawing", "illustration", "child", "yard", "kid"]):
                        continue
                    if u:
                        urls.append(u)
                        if len(urls) >= limit:
                            break
                return urls
        except Exception as e:
            logger.debug(f"Pixabay fotoğraf arama hatası: {e}")
        return []

    def search_duckduckgo_images(self, query: str, limit: int = 20) -> List[str]:
        """
        DuckDuckGo / DDGS API üzerinden doğrudan web editoryal maç fotoğraflarını çeker (API keysiz, 0 ms headless).
        Getty Images, Alamy, Shutterstock gibi filigranlı ticari ajans alan adlarını doğrudan dışlar.
        """
        urls: List[str] = []
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            clean_q = query.strip()
            # Negatif filtre eklerini ve ticari filigran bloklarını DuckDuckGo arama sorgusuna ekle
            search_str = f"{clean_q} -ticket -stub -scoreboard -concession -getty -alamy -shutterstock -stock -gty"
            with DDGS() as ddgs:
                results = list(ddgs.images(search_str, max_results=max(limit * 2, 35)))
                for r in results:
                    img_url = r.get("image")
                    if not img_url:
                        continue
                    title = (r.get("title") or "").lower()
                    u_low = img_url.lower()

                    # 1. Filigranlı ticari stok siteleri ve ajans CDN filtreleri (Kesin dışlama)
                    if any(sd in u_low for sd in COMMERCIAL_STOCK_DOMAINS):
                        continue

                    # 2. Bilet, salon ve yanlış dönem oyuncusu filtreleri
                    if any(bad in title or bad in u_low for bad in [
                        "ticket", "stub", "scoreboard", "jumbotron", "concession",
                        "scola", "bonzi wells", "luther head", "robert parish", "mchale", "watermark", "gty.im", "gty"
                    ]):
                        continue

                    # 3. Desteklenen temiz görsel uzantıları
                    if any(ext in u_low for ext in [".jpg", ".jpeg", ".png", ".webp"]) or ("format=" in u_low and "jpg" in u_low):
                        urls.append(img_url)
                        if len(urls) >= limit:
                            break
        except Exception as e:
            logger.debug(f"DuckDuckGo görsel arama hatası ('{query}'): {e}")
        return urls

    def fetch_diverse_nba_assets(
        self,
        script_data: Dict[str, Any],
        scratch_dir: Union[str, Path],
        min_unique_assets: int = 25,
        target_entity: Optional[str] = None,
        opponent_entity: Optional[str] = None,
        era_year: Optional[int] = None,
        width: int = 1080,
        height: int = 1920,
        downloads_dir: Optional[Union[str, Path]] = None,
        photo_pool_dir: Optional[Union[str, Path]] = None
    ) -> List[Path]:
        """
        Zengin, çoklu-sorgu destekli ve SigLIP onaylı NBA maç görseli havuzu inşa eder.
        Havuzda en az `min_unique_assets` (varsayılan 25) onaylı görsel olana kadar
        farklı sorgu varyasyonlarını işletir.
        İndirilen ham medyalar `downloads_dir` içine, onaylanmış temiz görseller
        `photo_pool_dir` içine kaydedilerek tam proje izolasyonu sağlanır.
        """
        s_dir = Path(scratch_dir)
        s_dir.mkdir(parents=True, exist_ok=True)
        d_dir = Path(downloads_dir) if downloads_dir else (s_dir / "downloads")
        p_dir = Path(photo_pool_dir) if photo_pool_dir else (s_dir / "photo_pool")
        d_dir.mkdir(parents=True, exist_ok=True)
        p_dir.mkdir(parents=True, exist_ok=True)

        # 1. Bağlam kilitli sorgu ve dinamik negatifleri al
        cq = self.q_builder.build_context_locked_queries(script_data)
        entity = target_entity or cq.entity
        team = cq.team_name or ""
        year = era_year or cq.target_year
        dyn_negatives = cq.dynamic_negatives

        # 2. Çoklu-sorgu varyasyonlarını üret
        multi_queries = self.q_builder.build_multi_queries(
            entity=entity,
            opponent=opponent_entity,
            year=year,
            script_or_context=script_data
        )

        # Sahne bazlı sorguları da ekle
        scene_queries = []
        scenes = script_data.get("scenes") or script_data.get("script_data", {}).get("scenes") or []
        for sc in scenes:
            if isinstance(sc, dict):
                sc_txt = sc.get("narration") or sc.get("text") or ""
                if sc_txt:
                    sc_cq = self.q_builder.build_context_locked_queries(script_data, scene_narration=sc_txt)
                    scene_queries.append(sc_cq.primary_query)

        # Genişletilmiş tüm arama sorguları
        all_candidate_queries: List[str] = []
        seen_q = set()
        for q in multi_queries + scene_queries + [cq.primary_query] + cq.fallback_queries:
            if q and q.lower() not in seen_q:
                seen_q.add(q.lower())
                all_candidate_queries.append(q)

        # Ekstra garantili yüksek getirili yedek sorgular (Tam dinamik, asla hardcoded oyuncu/yıl içermez)
        extra_fallbacks = [
            f"{entity} {team}".strip(),
            f"{entity} NBA",
            f"{entity} basketball",
            f"{entity} dunk",
            f"{entity} action shot",
            "NBA basketball court game action",
            "NBA basketball arena action shot"
        ]
        if year:
            extra_fallbacks.append(f"{entity} {year}")
            if team:
                extra_fallbacks.append(f"{team} {year}")
        if opponent_entity:
            extra_fallbacks.extend([
                f"{opponent_entity} NBA",
                f"{opponent_entity} basketball",
                f"{entity} vs {opponent_entity}"
            ])
        for ef in extra_fallbacks:
            if ef.lower() not in seen_q:
                seen_q.add(ef.lower())
                all_candidate_queries.append(ef)

        logger.info(f"🔎 [AssetFetcher] {len(all_candidate_queries)} adet çoklu-sorgu varyasyonu hazırlandı. Hedef Havuz: en az {min_unique_assets} görsel.")

        photo_pool: List[Path] = []
        used_urls: Set[str] = set()

        # 3. Sırayla tüm varyasyonları tara ve Quality Gate ile filtrele
        for q_idx, query in enumerate(all_candidate_queries):
            if len(photo_pool) >= min_unique_assets:
                break

            logger.info(f"🏀 [AssetFetcher] Sorgu çalıştırılıyor ({q_idx+1}/{len(all_candidate_queries)}): '{query}' (Mevcut Havuz: {len(photo_pool)}/{min_unique_assets})")
            # 1. DuckDuckGo Web/Editoryal maç fotoğraflarını çek
            ddg_urls = self.search_duckduckgo_images(query, limit=10)
            # 2. Wikimedia Commons açık arşiv fotoğraflarını ekle
            wiki_urls = self.search_wikimedia_commons(query, limit=6)
            urls = ddg_urls + [wu for wu in wiki_urls if wu not in ddg_urls]

            for u in urls:
                if len(photo_pool) >= min_unique_assets:
                    break
                if u in used_urls:
                    continue
                used_urls.add(u)

                try:
                    headers = {"User-Agent": BROWSER_USER_AGENT, "Referer": "https://duckduckgo.com/"}
                    r = requests.get(u, headers=headers, timeout=10)
                    if r.status_code != 200 or len(r.content) < 15000:
                        continue

                    # İndir ve formatla (Downloads dizinine ham, Photo Pool'a optimize)
                    cand_idx = len(photo_pool)
                    raw_path = d_dir / f"raw_download_{cand_idx:03d}_{int(time.time()*1000)%10000}.jpg"
                    target_path = p_dir / f"photo_{cand_idx:03d}.jpg"
                    raw_path.write_bytes(r.content)

                    ok = format_sports_image(raw_path, target_path, target_w=width, target_h=height)
                    try:
                        raw_path.unlink()
                    except Exception:
                        pass

                    if not ok or not target_path.exists():
                        continue

                    # Pre-Render Quality Gate Denetimi
                    val = self.validator.validate_candidate(
                        image_path=target_path,
                        scene_prompt=query,
                        project_type="basketball_analysis",
                        target_entity=entity,
                        is_vertical=True,
                        dynamic_negatives=dyn_negatives
                    )

                    if not val.is_valid:
                        logger.info(f"⚠️ [AssetFetcher] Kalite kapısı eledi ({val.reason}): {target_path.name}")
                        try:
                            target_path.unlink()
                        except Exception:
                            pass
                        continue

                    # MD5 ve No-Loop kaydı
                    self.validator.register_used_asset(target_path)
                    photo_pool.append(target_path)
                    logger.info(f"✅ [AssetFetcher] Onaylı NBA görseli havuza eklendi: {target_path.name} (Havuz: {len(photo_pool)}/{min_unique_assets})")

                except Exception as e_dl:
                    logger.debug(f"Görsel indirme hatası ({u}): {e_dl}")

        # 4. Eğer havuz dolmadıysa DuckDuckGo odaklı editoryal maç aramaları ile tamamla
        if len(photo_pool) < min_unique_assets:
            logger.info(f"🏀 [AssetFetcher] Hedef havuz dolmadı ({len(photo_pool)}/{min_unique_assets}), odaklı DuckDuckGo editoryal sorguları çalıştırılıyor...")
            yr_part = f"{year} " if year else ""
            tm_part = f"{team} " if team else ""
            ddg_target_queries = [
                f'"{entity}" {yr_part}NBA game action photo'.strip(),
                f'"{entity}" championship trophy celebration'.strip(),
                f'"{entity}" clutch game winner playoff celebration'.strip(),
                f'"{entity}" fastbreak slam dunk transition'.strip(),
                f'"{entity}" chase down block defense'.strip(),
                f'"{entity}" pull up jumper mid-range'.strip(),
                f'"{entity}" {tm_part}high resolution action wallpaper'.strip(),
                f'"{entity}" {tm_part}slam dunk championship photo'.strip(),
                f'"{entity}" {yr_part}playoffs clutch action court'.strip(),
                f'"{entity}" basketball court authentic photo',
                f'"{entity}" {tm_part}game highlights photo'.strip(),
                f'"{entity}" NBA finals defense shot',
                f'"{entity}" authentic game jersey action photo'
            ]
            if opponent_entity:
                ddg_target_queries.insert(1, f'"{entity}" vs "{opponent_entity}" {yr_part}NBA game action'.strip())

            if "wilt" in entity.lower() or "chamberlain" in entity.lower():
                wilt_priority = [
                    f'"{entity}" dunk Philadelphia Warriors 1962',
                    f'"{entity}" vs Bill Russell Celtics game action',
                    f'"{entity}" rebound finger roll baseline move',
                    f'"{entity}" Los Angeles Lakers 1972 finals',
                    f'"{entity}" scoring Hershey Pennsylvania game action',
                    f'"{entity}" Philadelphia Warriors 1962 game action',
                    f'"{entity}" hook shot rebound rim defense'
                ]
                ddg_target_queries = wilt_priority + ddg_target_queries
            for tq in ddg_target_queries:
                if len(photo_pool) >= min_unique_assets:
                    break
                t_urls = self.search_duckduckgo_images(tq, limit=15)
                for tu in t_urls:
                    if len(photo_pool) >= min_unique_assets:
                        break
                    if tu in used_urls:
                        continue
                    used_urls.add(tu)
                    try:
                        headers = {"User-Agent": BROWSER_USER_AGENT, "Referer": "https://duckduckgo.com/"}
                        r = requests.get(tu, headers=headers, timeout=10)
                        if r.status_code != 200 or len(r.content) < 15000:
                            continue
                        cand_idx = len(photo_pool)
                        raw_path = d_dir / f"raw_ddg_{cand_idx:03d}_{int(time.time()*1000)%10000}.jpg"
                        target_path = p_dir / f"photo_{cand_idx:03d}.jpg"
                        raw_path.write_bytes(r.content)
                        ok = format_sports_image(raw_path, target_path, target_w=width, target_h=height)
                        try:
                            raw_path.unlink()
                        except Exception:
                            pass
                        if not ok or not target_path.exists():
                            continue

                        val = self.validator.validate_candidate(
                            image_path=target_path,
                            scene_prompt=tq,
                            project_type="basketball_analysis",
                            target_entity=entity,
                            is_vertical=True,
                            dynamic_negatives=dyn_negatives
                        )
                        if not val.is_valid:
                            logger.info(f"⚠️ [AssetFetcher] Kalite kapısı eledi ({val.reason}): {target_path.name}")
                            try:
                                target_path.unlink()
                            except Exception:
                                pass
                            continue

                        self.validator.register_used_asset(target_path)
                        photo_pool.append(target_path)
                        logger.info(f"✅ [AssetFetcher] Onaylı DuckDuckGo maç karesi havuza eklendi: {target_path.name} (Havuz: {len(photo_pool)}/{min_unique_assets})")
                    except Exception as e_ddg_dl:
                        logger.debug(f"DuckDuckGo görsel indirme hatası: {e_ddg_dl}")

        # 5. Son çare Pixabay genel spor fotoğrafları ile tamamla
        if len(photo_pool) < min_unique_assets:
            logger.info(f"⚠️ [AssetFetcher] Wikimedia havuzu {len(photo_pool)} adette kaldı. Pixabay NBA aksiyon fotoğrafları taranıyor...")
            pix_queries = [
                "basketball action slam dunk",
                "professional basketball game court",
                "basketball player defense shot",
                "basketball arena championship",
                "basketball court action player"
            ]
            for pq in pix_queries:
                if len(photo_pool) >= min_unique_assets:
                    break
                p_urls = self.search_pixabay_photos(pq, limit=8)
                for pu in p_urls:
                    if len(photo_pool) >= min_unique_assets:
                        break
                    if pu in used_urls:
                        continue
                    used_urls.add(pu)
                    try:
                        r = requests.get(pu, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                        if r.status_code != 200 or len(r.content) < 25000:
                            continue
                        cand_idx = len(photo_pool)
                        raw_path = d_dir / f"raw_pix_{cand_idx:03d}.jpg"
                        target_path = p_dir / f"photo_{cand_idx:03d}.jpg"
                        raw_path.write_bytes(r.content)
                        ok = format_sports_image(raw_path, target_path, target_w=width, target_h=height)
                        try:
                            raw_path.unlink()
                        except Exception:
                            pass
                        if not ok or not target_path.exists():
                            continue

                        val = self.validator.validate_candidate(
                            image_path=target_path,
                            scene_prompt=pq,
                            project_type="basketball_analysis",
                            target_entity="basketball",
                            is_vertical=True,
                            dynamic_negatives=dyn_negatives
                        )
                        if not val.is_valid:
                            try:
                                target_path.unlink()
                            except Exception:
                                pass
                            continue

                        self.validator.register_used_asset(target_path)
                        photo_pool.append(target_path)
                        logger.info(f"✅ [AssetFetcher - Pixabay] Onaylı maç görseli eklendi: {target_path.name} (Havuz: {len(photo_pool)}/{min_unique_assets})")
                    except Exception:
                        pass

        logger.info(f"🎉 [AssetFetcher] Aday havuzu derlendi: Toplam {len(photo_pool)} adet onaylı benzersiz NBA aksiyon fotoğrafı hazır!")
        return photo_pool


# Singleton Nesne
asset_fetcher = AssetFetcher()
