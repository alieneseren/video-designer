# 🔒 LOCK: BASKETBALL ENGINE 2.0 (SPORTS SCIENCE KATEGORİSİ)
Tarih: 2026-11-15
Durum: KİLİTLİ (DOKUNULMAZ / REGRESYON KORUMALI)

---

## 📁 Kilitli Dosyalar ve SHA256 Snapshot

- `src/modules/basketball/contracts.py` — SHA256: `52318568049b40a3e59e800d5208adae1e04d3687322f625a1e2cb607abadd29`
- `src/modules/basketball/validator.py` — SHA256: `e50513cf1c97d7a67997e89a36ad061486b8813fae5dd589c33a56bd66517ea9`
- `src/modules/basketball/asset_validator.py` — SHA256: `19d89d0634d824f239584758f323425914157ce0a307470df4c9f5507c12c9f9`
- `src/modules/basketball/vision_verifier.py` — SHA256: `3e646f11234465b06bd603e3578e19a108b2c6fa4e205448fc67bacdbd18620a`
- `src/modules/basketball/video_harvester.py` — SHA256: `556d4a37a60290b3316c9130b5d02bc6f844b303e4a698f2afc7679705553725`
- `src/modules/basketball/orchestrator.py` — SHA256: `ac097dc6752f6fd9f5295ff37d9717d79279beb81639311ab3411f4336db6b26`
- `run_basketball_v2.py` — SHA256: `1eee3e8eb97cd581c218456f50fd73dabb7506cc77a0d6e7c2af66dd4aaf50b6`
- `remotion/src/compositions/BasketballShorts.tsx` — SHA256: `847ff81b4672b0b01cf3a332f7dc5a63e8a720dde45013b3b49ad22f3705b705`
- `tests/test_deterministic_gates.py` — SHA256: `9bdded4f29cc5b90395840901a7ec8dec9825f27f94c4aa7305d77ff756d64ae`

---

## 📐 Kritik Fonksiyon ve Sınıf İmzaları

### 1. `contracts.py`
- `class MediaType(str, Enum)`: `VIDEO_CLIP`, `KEN_BURNS_PHOTO`
- `class BasketballCut`:
  - `cut_index: int`, `start_time: float`, `end_time: float`, `duration: float`, `media_path: str`, `media_type: MediaType`, `target_subject: str`, `action_notes: str = ""`
  - `validate(self) -> None`
- `class BasketballRenderSpec`:
  - `job_id: str`, `channel_id: str`, `topic: str`, `athlete_name: str`, `audio_path: str`, `sentence_boundaries: List[Dict[str, Any]]`, `cuts: List[BasketballCut]`, `category_badge_text: str = "🏀 SPORTS SCIENCE"`, `category_badge_duration: float = 4.0`, `cta_display_duration: float = 2.0`
  - `validate_strict_zero_loop(self) -> None`

### 2. `vision_verifier.py`
- `class BasketballVisionVerifier`:
  - `extract_middle_frame_image(media_path: Path, timestamp: float = 1.0) -> Optional[Image.Image]`
  - `check_motion_and_freeze(video_path: Path, min_motion_diff: float = 1.5) -> Tuple[bool, float]`
  - `check_entity_presence(pil_img: Image.Image, target_subject: Optional[str], query: str) -> Tuple[bool, str, float, float]`
  - `verify_slice(media_path: Path, concrete_visual_query: str, target_subject: Optional[str] = None, min_cosine_similarity: float = 0.26, min_motion_diff: float = 1.5, min_width: int = 720, min_laplacian_variance: float = 75.0) -> Dict[str, Any]`

### 3. `asset_validator.py`
- `measure_laplacian_sharpness(file_path: Path) -> Tuple[int, int, float]`
- `extract_3point_frames(video_path: Path, temp_dir: Path) -> List[Path]`
- `get_3point_fingerprints(file_path: Path, temp_dir: Path) -> List[imagehash.ImageHash]`
- `compute_file_md5(file_path: Path) -> str`
- `get_video_duration(video_path: Path) -> float`
- `class BasketballAssetValidator`:
  - `validate_timeline(cuts: List[Dict[str, Any]], work_dir: Path) -> Tuple[bool, List[str]]`
  - `extract_source_id(media_path: Path, cut: Dict[str, Any]) -> str`

### 4. `video_harvester.py`
- `is_source_banned_for_project(source_id_or_path: str, athlete_key: str) -> bool`
- `class VideoHarvester`:
  - `__init__(work_dir: Path, bypass_cache: bool = False, project_id: str = "")`
  - `download_recipe_videos(athlete_key: str) -> Dict[str, Path]`
  - `slice_recipe_clips(athlete_key: str, downloaded_videos: Dict[str, Path]) -> List[Dict[str, Any]]`
  - `fetch_authentic_photos(athlete_key: str) -> Dict[str, Path]`
  - `build_unique_asset_pool(athlete_key: str, bypass_cache: bool = False, project_id: str = "") -> List[Dict[str, Any]]`
  - `get_backup_pool(athlete_key: str, used_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]`

### 5. `orchestrator.py`
- `class BasketballOrchestrator`:
  - `__init__(channel_id: str = "thebasketballshows")`
  - `select_replacement_asset(...) -> Optional[Dict[str, Any]]`
  - `enforce_hard_pacing_limits(...) -> List[Dict[str, Any]]`
  - `produce_video(job_id: str, athlete_key: str, topic: str, voice_clone_id: str = "vc_1792868444", force_rebuild: bool = False, bypass_cache: bool = False, unlock_indices: Optional[List[int]] = None, patch_segments: Optional[Dict[int, Dict[str, Any]]] = None, custom_queries: Optional[Dict[int, str]] = None) -> Path`
  - `patch_video(job_id: str, athlete_key: str, unlock_indices: List[int], custom_queries: Optional[Dict[int, str]] = None, bypass_cache: bool = False) -> Path`

---

## 🎯 Çıktı ve Kalite Kontratı

1. **Video Formatı:** 1080x1920 dikey (9:16), 30 fps, H.264/AAC MP4.
2. **Tempo & Pacing:** Her kesme (cut) kesinlikle `<= 2.40s` (72 kare). Sert bölücü (Hard Splitter) ile otomatik bölünür.
3. **Tekillik & Hijyen (Zero-Loop Kontratı):**
   - Sıfır modülo (%) veya başa sarma döngüsü.
   - Zaman çizelgesindeki her sahnenin dosya yolu (`media_path`) ve MD5 hash'i kesinlikle tekildir.
   - Ardışık sahne tekrarı (A-A) fiziksel olarak engellenmiştir.
4. **Görsel Kalite Eşikleri:**
   - cv2.Laplacian keskinlik varyansı: `>= 75.0` (Whip-pan, düşük çözünürlük veya hareket bulanıklığı reddedilir).
   - Minimum çözünürlük: `>= 720p` (hem en hem boy için).
   - Minimum hareket farkı (`min_motion_diff`): `>= 1.5` (donmuş/statik video engeli).
   - Semantik CLIP / SigLIP cosine similarity: `>= 0.26`.
   - Negatif domain katı tavanı: `max_neg_sim < 0.245` ve `max_neg_sim <= pos_anchor_threshold - 0.02`.
   - Çoklu kare denetimi: Videolar için `0.2s`, `1.0s`, `1.8s` noktalarından 3 örnek kare denetlenir.
5. **Ses & Filigran:**
   - M4 RVC ses giydirme (`voice_clone_id="vc_1792868444"`).
   - Ultrasonik telif filigranı (`ALIENES!`).

---

## 🚫 Negatif Kurallar (Yasaklar)

1. **Amatör ve Uygunsuz Mekanlar:**
   - Amatör tuğla duvarlı salonlar (`#67`, `MVP 75`, `defense_14.mp4`), açık hava asfalt sokak sahaları, futbol stadyumları ve atletizm koşu pistleri YASAKTIR.
2. **Ölü Top ve Rol Oyuncusu:**
   - Dead-ball serbest atış dizilişleri, benchte oturan/bekleyen oyuncular ve hedef sporcunun olmadığı geniş açı rol oyuncusu kesitleri YASAKTIR.
3. **Çapraz Proje Sızıntısı:**
   - James Harden projesinde San Antonio Spurs, Derek Fisher, 2004 Lakers veya SBC Center varlıkları YASAKTIR.
   - Derek Fisher projesinde Houston Rockets veya James Harden varlıkları YASAKTIR.
4. **Kör Yedek Atama:**
   - Backup pool'dan rastgele görsel/video seçilemez; her yedek aday `verify_slice()` ve `measure_laplacian_sharpness()` testlerinden geçmek zorundadır.
5. **Sahte URL / Source ID Çoğaltması:**
   - Aynı YouTube kaynak URL'sinden birden fazla sahte ID ile kesit alıp tekillik kotasını baypas etmek YASAKTIR (Canonical YouTube ID deduplication zorunludur).

---

## 🧪 Doğrulama ve Test Kalkanı

- Test komutu: `PYTHONPATH=src:. .venv/bin/python -m unittest tests/test_deterministic_gates.py`
- Test sayısı: **25/25 deterministik gate testi eksiksiz geçmek zorundadır**.
