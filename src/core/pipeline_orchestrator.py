"""
core/pipeline_orchestrator.py
=============================
Fail-Safe Video Production Pipeline Orchestrator
(Sıfır Siyah Ekran, Sıfır Konu Sapması, Sıfır Döngü Garantili Orkestratör)

Akış:
1. Segment Analizi & Çapalanmış Arama:
   - QueryBuilder ile soyut ifadeler zorunlu karakter/takım/yıl çapasıyla kilitlenir.
   - Dinamik negatifler (çapraz spor: soccer, fifa, nfl, askeri, amatör, rakip yıldızlar) enjekte edilir.
2. Aday İndirme & Yerel AI Doğrulama:
   - Sahne başına en az 8-10 aday taranır (Candidate Pool Expansion).
   - SigLIP / OpenCLIP CPU ile taranır, negatif skoru yüksek adaylar anında elenir.
   - No-Loop takibi ile daha önce kullanılan görseller tekilleştirilir (Deduplication).
3. 3-Kademeli Güvenli Fallback (Zero Black Screen Guarantee):
   - Aday havuzu tükenirse ASLA None dönmez, ASLA siyah ekran bırakmaz.
   - Kademe 1: Karakter Arşiv Karesi (Önceden onaylanmış fotoğraf + alternatif Ken Burns).
   - Kademe 2: Dinamik İstatistik / İnfografik Kartı (Pillow ile takım renklerinde glassmorphic kart).
   - Kademe 3: Soyut Hareketli Doku (Koyu degrade + grid + parçacık dokusu).
   - Katı Güvence: assert clip.exists() and clip.stat().st_size > 1000
4. Timeline Guard & Süre Kilidi:
   - Dış ses süresi mutagen ile okunur, final_duration = audio_duration + 0.60s tampon ile kilitlenir.
   - Altyazılar ekran genişliğinin %80'ine göre 2 satıra kırılır (Auto-Wrap Bounding Box).
"""

from __future__ import annotations

import os
import sys
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Callable, Tuple

# PYTHONPATH Koruması
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from core.query_builder import query_builder, ContextLockedQuery
except ImportError:
    from src.core.query_builder import query_builder, ContextLockedQuery

try:
    from core.asset_validator import asset_validator, ValidationResult
except ImportError:
    from src.core.asset_validator import asset_validator, ValidationResult

try:
    from core.fallback_engine import fallback_engine, FallbackEngine
except ImportError:
    from src.core.fallback_engine import fallback_engine, FallbackEngine

try:
    from core.timeline_guard import timeline_guard, TimelineDurationLock
except ImportError:
    from src.core.timeline_guard import timeline_guard, TimelineDurationLock

logger = logging.getLogger("PipelineOrchestrator")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


class PipelineOrchestrator:
    """
    Sıfır siyah ekran ve sıfır konu sapması garantili otonom video üretim boru hattı orkestratörü.
    """

    def __init__(
        self,
        query_engine=query_builder,
        validator=asset_validator,
        fallback=fallback_engine,
        timeline=timeline_guard
    ):
        self.query_builder = query_engine
        self.asset_validator = validator
        self.fallback_engine = fallback
        self.timeline_guard = timeline

    # ─────────────────────────────────────────────────────────────
    # 1. SAHNE BAZLI VARLIK VE KALİTE KAPISI ORKESTRASYONU
    # ─────────────────────────────────────────────────────────────

    def orchestrate_scene_asset(
        self,
        scene_idx: int,
        scene_text: str,
        primary_entity: str,
        team_name: Optional[str] = None,
        era_year: Optional[int] = None,
        project_type: str = "basketball_analysis",
        candidate_generator_fn: Optional[Callable[[int, str], Optional[Union[str, Path]]]] = None,
        character_archive_image: Optional[Union[str, Path]] = None,
        duration: float = 3.0,
        work_dir: Optional[Union[str, Path]] = None,
        candidate_limit: int = 8,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30
    ) -> Tuple[Path, Dict[str, Any]]:
        """
        Bir sahne için karaktere kilitli arama yapar, adayları kalite kapısından geçirir,
        aday bulunamazsa 3 kademeli deterministik fallback motoru ile siyah ekranı önler.
        
        Döner: (clip_or_image_path, metadata)
        Katı Değişmez: Asla None dönmez, dönen dosya her zaman >1KB ve mevcuttur!
        """
        assert duration > 0, f"Geçersiz süre: {duration} <= 0"
        assert primary_entity and primary_entity.strip(), "Primary entity zorunludur!"

        target_dir = Path(work_dir) if work_dir else Path("/tmp")
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Adım: Zorunlu Çapalı Arama Terimleri ve Dinamik Negatiflerin Üretilmesi
        context_query: ContextLockedQuery = self.query_builder.build_context_locked_queries(
            scene_text=scene_text,
            fallback_entity=primary_entity,
            target_team=team_name,
            era_year=era_year
        )
        
        # Güvenlik Kontrolü: Çapa Değişmezi (Invariant Check)
        for q in context_query.anchored_queries:
            assert primary_entity.lower() in q.lower(), (
                f"KRİTİK GÜVENLİK İHLALİ: Sorguda karakter çapası eksik! Sorgu: '{q}', Karakter: '{primary_entity}'"
            )

        logger.info(
            f"🔍 [Orchestrator] Sahne {scene_idx} için çapalanmış sorgu: '{context_query.primary_query}' "
            f"(Negatif havuzu: {len(context_query.dynamic_negatives)} etiket)"
        )

        chosen_candidate_path: Optional[Path] = None
        validation_info: Optional[ValidationResult] = None

        # 2. Adım: Genişletilmiş Aday Havuzunu Çek ve Doğrula (En az candidate_limit aday)
        if candidate_generator_fn:
            for attempt in range(1, candidate_limit + 1):
                query_idx = (attempt - 1) % len(context_query.anchored_queries)
                active_query = context_query.anchored_queries[query_idx]

                candidate_raw = candidate_generator_fn(attempt, active_query)
                if not candidate_raw:
                    continue

                c_path = Path(candidate_raw)
                if not c_path.exists() or c_path.stat().st_size < 1000:
                    continue

                # Yerel AI Kapısından Geçir (SigLIP / OpenCLIP + No-Loop)
                val_result: ValidationResult = self.asset_validator.validate_candidate(
                    image_path=c_path,
                    scene_prompt=f"{primary_entity} {scene_text}",
                    project_type=project_type,
                    target_entity=primary_entity,
                    is_vertical=True,
                    dynamic_negatives=context_query.dynamic_negatives
                )

                if val_result.is_valid:
                    self.asset_validator.register_used_asset(c_path)
                    chosen_candidate_path = c_path
                    validation_info = val_result
                    logger.info(
                        f"🎯 [Orchestrator] Sahne {scene_idx} adayı #{attempt} ONAYLANDI: "
                        f"{c_path.name} (Skor: {val_result.score:.2f})"
                    )
                    break
                else:
                    logger.warning(
                        f"🚫 [Orchestrator] Sahne {scene_idx} adayı #{attempt} REDDEDİLDİ "
                        f"({val_result.reason}): {c_path.name}"
                    )
                    try:
                        if c_path.exists():
                            c_path.unlink()
                    except Exception:
                        pass

        # 3. Adım: Aday Bulunduysa Video Klibe Dönüştür
        if chosen_candidate_path and chosen_candidate_path.exists():
            # Eğer zaten MP4 ise doğrudan kullan
            if chosen_candidate_path.suffix.lower() == ".mp4":
                return chosen_candidate_path, {
                    "source": "candidate_video",
                    "validation": validation_info.to_dict() if validation_info else {},
                    "is_fallback": False
                }
            
            # Fotoğraf ise Ken Burns klibine dönüştür
            out_clip = target_dir / f"scene_{scene_idx:03d}_kenburns.mp4"
            clip_res = self.fallback_engine.convert_image_to_clip(
                image_path=chosen_candidate_path,
                output_clip_path=out_clip,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                subtle_zoom=True
            )
            assert clip_res.exists() and clip_res.stat().st_size > 1000, "Ken Burns klip üretilemedi!"
            return clip_res, {
                "source": "candidate_image",
                "validation": validation_info.to_dict() if validation_info else {},
                "is_fallback": False
            }

        # 4. Adım: Aday Havuzu Tükendi! -> 3-Kademeli Güvenli Fallback Motoru Devrede
        logger.warning(
            f"🛡️ [Orchestrator] Sahne {scene_idx} aday havuzu tükendi. "
            f"Sıfır Siyah Ekran Garantisi (FallbackEngine) devreye alınıyor..."
        )
        fallback_clip_path = target_dir / f"scene_{scene_idx:03d}_fail_safe.mp4"
        
        safe_clip = self.fallback_engine.resolve_fail_safe_clip(
            output_clip_path=fallback_clip_path,
            duration=duration,
            primary_entity=primary_entity,
            team_name=team_name,
            scene_text=scene_text,
            character_archive_image=character_archive_image,
            scratch_dir=target_dir,
            width=width,
            height=height,
            fps=fps
        )

        # KATI DOĞRULAMA (INVARIANT ASSERTION)
        assert safe_clip is not None, "KRİTİK HATA: FallbackEngine None döndü!"
        assert safe_clip.exists(), f"KRİTİK HATA: FallbackEngine klip dosyası mevcut değil: {safe_clip}"
        assert safe_clip.stat().st_size > 1000, f"KRİTİK HATA: FallbackEngine klip dosyası 0-byte: {safe_clip}"

        return safe_clip, {
            "source": "fallback_engine",
            "is_fallback": True,
            "tier_used": "fail_safe_hierarchy"
        }

    # ─────────────────────────────────────────────────────────────
    # 2. ZAMAN ÇİZELGESİ VE SÜRE KİLİDİ ORKESTRASYONU (+0.60s)
    # ─────────────────────────────────────────────────────────────

    def orchestrate_timeline_locks(
        self,
        audio_path: Union[str, Path],
        tail_padding_sec: float = 0.60
    ) -> TimelineDurationLock:
        """
        Dış ses süresini okur ve +0.60s tampon ile kesin video kompozisyon süresini kilitler.
        """
        return self.timeline_guard.calculate_locked_timeline_duration(
            audio_path=audio_path,
            tail_padding_sec=tail_padding_sec
        )

    # ─────────────────────────────────────────────────────────────
    # 3. ALTYAZI SINIRLAMA VE SARMA ORKESTRASYONU (%80 KUTU)
    # ─────────────────────────────────────────────────────────────

    def orchestrate_subtitles(
        self,
        raw_subtitles: List[Dict[str, Any]],
        screen_width: int = 1080,
        max_width_ratio: float = 0.80,
        font_size: int = 56
    ) -> List[Dict[str, Any]]:
        """
        Tüm altyazı segmentlerini ekranın %80 genişlik sınırına göre
        kelime sınırlarından 2 satıra sarar. Taşmayı önler.
        """
        return self.timeline_guard.format_and_wrap_subtitles(
            subtitles=raw_subtitles,
            screen_width=screen_width,
            max_width_ratio=max_width_ratio,
            font_size=font_size
        )

    # ─────────────────────────────────────────────────────────────
    # 4. KESİN VE HATASIZ COMPOSITING VE FINAL RENDER KONTROLÜ
    # ─────────────────────────────────────────────────────────────

    def render_final_composition(
        self,
        video_cuts: List[Union[str, Path]],
        audio_path: Union[str, Path],
        output_video_path: Union[str, Path],
        bgm_path: Optional[Union[str, Path]] = None,
        subtitles_overlay_video: Optional[Union[str, Path]] = None,
        scratch_dir: Optional[Union[str, Path]] = None,
        tail_padding_sec: float = 0.60,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30
    ) -> Path:
        """
        Tüm klipleri, kilitli süredeki dış sesi ve altyazıyı birleştirir.
        Dış sesin son kelimesinin kesilmesini önlemek için apad + fadeout filtresini uygular.
        """
        out_p = Path(output_video_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        s_dir = Path(scratch_dir) if scratch_dir else out_p.parent / "orchestrator_scratch"
        s_dir.mkdir(parents=True, exist_ok=True)

        # 1. Kilitli Süreyi Al
        lock_info = self.orchestrate_timeline_locks(audio_path, tail_padding_sec=tail_padding_sec)
        final_dur = lock_info.final_video_duration

        # 2. Kliplerin Concat Dosyasını Yaz
        concat_txt = s_dir / "cuts_orchestrated.txt"
        with open(concat_txt, "w") as f:
            for c in video_cuts:
                c_p = Path(c).resolve()
                assert c_p.exists() and c_p.stat().st_size > 1000, f"Geçersiz veya 0-byte klip: {c_p}"
                f.write(f"file '{c_p}'\n")

        master_visuals = s_dir / "master_visuals_concat.mp4"
        subprocess.run([
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-c", "copy", str(master_visuals)
        ], capture_output=True, check=True)

        fadeout_start = max(0.0, final_dur - 0.40)

        # 3. Audio Tampon & Fadeout Filtresi
        # apad ile audio süresini final_dur'a tamamla ve fadeout uygula
        audio_p = Path(audio_path).resolve()
        
        if bgm_path and Path(bgm_path).exists():
            bgm_p = Path(bgm_path).resolve()
            if subtitles_overlay_video and Path(subtitles_overlay_video).exists():
                cmd = [
                    FFMPEG, "-y",
                    "-i", str(master_visuals),
                    "-i", str(subtitles_overlay_video),
                    "-i", str(audio_p),
                    "-stream_loop", "-1", "-i", str(bgm_p),
                    "-filter_complex",
                    f"[0:v][1:v]overlay=0:0:eof_action=pass[vcomp];"
                    f"[vcomp]trim=0:{final_dur:.3f},setpts=PTS-STARTPTS[vout];"
                    f"[2:a]apad=pad_dur={tail_padding_sec:.3f},afade=t=out:st={fadeout_start:.2f}:d=0.40[a_voice];"
                    f"[3:a]volume=0.14,afade=t=out:st={fadeout_start:.2f}:d=0.40[a_bgm];"
                    f"[a_voice][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                    "-map", "[vout]", "-map", "[aout]",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                    "-t", f"{final_dur:.3f}",
                    str(out_p)
                ]
            else:
                cmd = [
                    FFMPEG, "-y",
                    "-i", str(master_visuals),
                    "-i", str(audio_p),
                    "-stream_loop", "-1", "-i", str(bgm_p),
                    "-filter_complex",
                    f"[0:v]trim=0:{final_dur:.3f},setpts=PTS-STARTPTS[vout];"
                    f"[1:a]apad=pad_dur={tail_padding_sec:.3f},afade=t=out:st={fadeout_start:.2f}:d=0.40[a_voice];"
                    f"[2:a]volume=0.14,afade=t=out:st={fadeout_start:.2f}:d=0.40[a_bgm];"
                    f"[a_voice][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                    "-map", "[vout]", "-map", "[aout]",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                    "-t", f"{final_dur:.3f}",
                    str(out_p)
                ]
        else:
            cmd = [
                FFMPEG, "-y",
                "-i", str(master_visuals),
                "-i", str(audio_p),
                "-filter_complex",
                f"[0:v]trim=0:{final_dur:.3f},setpts=PTS-STARTPTS[vout];"
                f"[1:a]apad=pad_dur={tail_padding_sec:.3f},afade=t=out:st={fadeout_start:.2f}:d=0.40[aout]",
                "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                "-t", f"{final_dur:.3f}",
                str(out_p)
            ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not out_p.exists() or out_p.stat().st_size < 5000:
            raise RuntimeError(f"FFmpeg compositing başarısız oldu: {res.stderr}")

        logger.info(f"🏆 [Orchestrator] Üretim tamamlandı: {out_p.name} ({out_p.stat().st_size / 1024 / 1024:.2f} MB, {final_dur:.2f}s)")
        return out_p


# Singleton Nesne
pipeline_orchestrator = PipelineOrchestrator()


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Fail-Safe Video Production Pipeline Orchestrator CLI")
    parser.add_argument("--project", default="hakeem_dream_shake", help="Proje adı / kimliği")
    parser.add_argument("--topic", default="Hakeem Olajuwon Dream Shake 1995 Western Conference Finals David Robinson", help="Konu / Başlık")
    parser.add_argument("--force-rebuild", action="store_true", help="Önbellek ve scratch dizinini sıfırdan oluştur")
    parser.add_argument("--min-assets", type=int, default=14, help="Minimum benzersiz varlık sayısı")
    parser.add_argument("--output", default="output/final_hakeem_fixed.mp4", help="Çıktı video dosyası yolu")
    args = parser.parse_args()

    print(f"🚀 [PipelineOrchestrator CLI] Başlatılıyor: Project={args.project}, Topic='{args.topic}', MinAssets={args.min_assets}")
    out_file = Path(args.output).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    work_dir = out_file.parent / f"work_{args.project}"
    if args.force_rebuild and work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Sunucuda veya yerelde hazır Hakeem işi varsa onu kaynak olarak al
    base_dir = Path(__file__).resolve().parent.parent
    candidate_job_files = (
        list(base_dir.glob("jobs/*Hakeem*.json")) +
        list(Path("/home/ubuntu/yt-remote-worker/jobs").glob("*Hakeem*.json"))
    )
    job_payload = None
    for jf in candidate_job_files:
        if jf.is_file() and not jf.name.endswith("_status.json"):
            try:
                job_payload = json.loads(jf.read_text(encoding="utf-8"))
                print(f"📄 [PipelineOrchestrator CLI] Kaynak iş yüklendi: {jf.name}")
                break
            except Exception:
                pass

    if not job_payload:
        job_payload = {
            "channel_id": "thebasketballshows",
            "title": args.topic,
            "script_data": {
                "title": args.topic,
                "scenes": [
                    {"narration": "In the nineteen-nineties golden era of dominant centers, Hakeem Olajuwon did not overpower defenders-he completely dissolved their balance."},
                    {"narration": "The secret weapon was not his speed, but his soccer-honed center of gravity. Olajuwon planted his pivot foot with zero knee deceleration, giving defenders false kinetic cues that he was committed to a baseline hook."},
                    {"narration": "The moment the defender committed his weight forward, Olajuwon executed a reverse half-spin while maintaining an identical shoulder angle, forcing the human brain visual cortex into a fatal processing delay."},
                    {"narration": "By the time David Robinson realized the fake, Hakeem was already rising for an uncontested reverse layup. It was not just basketball; it was optical illusion elevated to high art."}
                ]
            }
        }

    try:
        from sports_shorts_engine import render_sports_shorts_job
    except ImportError:
        from src.sports_shorts_engine import render_sports_shorts_job

    print(f"🎬 [PipelineOrchestrator CLI] Spor shorts motoru ile render başlıyor...")
    res_video = render_sports_shorts_job(job_payload, work_dir)
    if res_video and res_video.exists():
        shutil.copy2(str(res_video), str(out_file))
        print(f"=== Üretim Tamamlandı! Yeni video {out_file} konumunda hazır. ===")
    else:
        sys.exit(1)
