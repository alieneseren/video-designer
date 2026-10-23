"""
voice_clone_manager.py
======================
Yerel Gerçekçi Ses Klonlama Stüdyosu Yönetim Motoru.
Apple Silicon (MPS) hızlandırması ile kullanıcıdan alınan ses örneğini analiz eder,
tını ve speaker embedding'lerini çıkarır, .pt ses profili üretir ve
saniyeler içinde kullanıma hazır hale getirir.
"""

import os
import sys
import time
import json
import shutil
import logging
import threading
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import torch
import soundfile as sf

logger = logging.getLogger("VoiceCloneManager")

BASE_DIR = Path(__file__).resolve().parent.parent
CLONES_DIR = BASE_DIR / "data" / "voice_clones"
TEMP_DIR = CLONES_DIR / "temp"
REGISTRY_FILE = CLONES_DIR / "registry.json"

# Chatterbox ve src modül yollarını garanti et
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

CHATTERBOX_ROOT = BASE_DIR / "chatterbox" / "src"
if str(CHATTERBOX_ROOT) not in sys.path:
    sys.path.insert(0, str(CHATTERBOX_ROOT))


class VoiceCloneManager:
    _instance = None
    _lock = threading.Lock()
    _jobs: Dict[str, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VoiceCloneManager, cls).__new__(cls)
                    cls._instance._init_storage()
        return cls._instance

    def _init_storage(self):
        CLONES_DIR.mkdir(parents=True, exist_ok=True)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        if not REGISTRY_FILE.exists():
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump({"active_id": "", "clones": []}, f, indent=2, ensure_ascii=False)

    def _read_registry(self) -> Dict[str, Any]:
        data = {"active_id": "", "clones": []}
        try:
            if REGISTRY_FILE.exists():
                with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception as e:
            logger.warning(f"Registry okunamadı: {e}")

        # Otomatik tarama: Klasörlerde meta.json varsa ve listede yoksa ekle
        known_ids = {c.get("id") for c in data.get("clones", []) if isinstance(c, dict)}
        found_any_new = False
        if CLONES_DIR.exists():
            for folder in CLONES_DIR.iterdir():
                if folder.is_dir() and folder.name != "temp":
                    meta_p = folder / "meta.json"
                    if meta_p.exists() and folder.name not in known_ids:
                        try:
                            with open(meta_p, "r", encoding="utf-8") as mf:
                                meta = json.load(mf)
                                data.setdefault("clones", []).append(meta)
                                known_ids.add(folder.name)
                                found_any_new = True
                        except Exception as me:
                            logger.warning(f"Meta okunamadı: {meta_p} -> {me}")

        if found_any_new:
            self._write_registry(data)

        return data

    def _write_registry(self, data: Dict[str, Any]):
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_device(self) -> str:
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def list_clones(self) -> List[Dict[str, Any]]:
        reg = self._read_registry()
        active_id = reg.get("active_id", "")
        clones = reg.get("clones", [])
        for c in clones:
            c["is_active"] = (c.get("id") == active_id)
        # En yeni en başta
        return sorted(clones, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_active_clone(self) -> Optional[Dict[str, Any]]:
        reg = self._read_registry()
        active_id = reg.get("active_id", "")
        if not active_id:
            return None
        for c in reg.get("clones", []):
            if c.get("id") == active_id:
                c["is_active"] = True
                return c
        return None

    def get_clone(self, clone_id: str) -> Optional[Dict[str, Any]]:
        reg = self._read_registry()
        for c in reg.get("clones", []):
            if c.get("id") == clone_id:
                c["is_active"] = (c.get("id") == reg.get("active_id", ""))
                return c
        return None

    def activate_clone(self, clone_id: str) -> bool:
        reg = self._read_registry()
        found = None
        for c in reg.get("clones", []):
            if c.get("id") == clone_id:
                found = c
                break
        if not found:
            return False

        reg["active_id"] = clone_id
        self._write_registry(reg)

        # settings_manager'a kaydet
        voice_path = found.get("voice_pt_path") or found.get("voice_wav_path")
        update_dict = {
            "tts_engine": "chatterbox",
            "chatterbox_voice": str(voice_path),
            "active_voice_clone_id": clone_id,
            "rvc_pth_path": str(found.get("rvc_pth_path") or ""),
            "rvc_index_path": str(found.get("rvc_index_path") or "")
        }
        try:
            import server
            server.settings_mgr.update(update_dict)
        except Exception:
            try:
                from settings_manager import SettingsManager
            except ImportError:
                from src.settings_manager import SettingsManager
            mgr = SettingsManager()
            mgr.update(update_dict)

        logger.info(f"Ses profili aktif edildi: {found.get('name')} ({voice_path})")
        return True

    def delete_clone(self, clone_id: str) -> bool:
        reg = self._read_registry()
        reg["clones"] = [c for c in reg.get("clones", []) if c.get("id") != clone_id]
        if reg.get("active_id") == clone_id:
            reg["active_id"] = ""
            try:
                from settings_manager import SettingsManager
            except ImportError:
                from src.settings_manager import SettingsManager
            mgr = SettingsManager()
            mgr.update({"chatterbox_voice": "", "active_voice_clone_id": "", "rvc_pth_path": "", "rvc_index_path": ""})

        self._write_registry(reg)

        clone_folder = CLONES_DIR / clone_id
        if clone_folder.exists():
            shutil.rmtree(clone_folder, ignore_errors=True)
        return True

    def start_cloning_job(self, name: str, temp_audio_path: str, description: str = "") -> str:
        job_id = f"vc_job_{int(time.time() * 1000)}"
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "name": name.strip() or "Özel Ses Profili",
                "description": description.strip(),
                "temp_audio_path": temp_audio_path,
                "status": "queued",
                "progress": 5,
                "current_stage": "İşlem sıraya alındı...",
                "start_time": time.perf_counter(),
                "elapsed_seconds": 0.0,
                "total_duration": None,
                "error": None,
                "result": None
            }

        worker_thread = threading.Thread(
            target=self._run_cloning_worker,
            args=(job_id,),
            daemon=True
        )
        worker_thread.start()
        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"status": "not_found", "error": "İş bulunamadı"}

            res = dict(job)
            if res["status"] in ("queued", "processing"):
                res["elapsed_seconds"] = round(time.perf_counter() - res["start_time"], 2)
            return res

    def _update_job(self, job_id: str, **kwargs):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)
                if self._jobs[job_id]["status"] in ("queued", "processing"):
                    self._jobs[job_id]["elapsed_seconds"] = round(
                        time.perf_counter() - self._jobs[job_id]["start_time"], 2
                    )

    def _run_cloning_worker(self, job_id: str):
        job = self.get_job_status(job_id)
        name = job["name"]
        desc = job.get("description", "")
        src_path = Path(job["temp_audio_path"])
        clone_id = f"vc_{int(time.time())}"
        out_dir = CLONES_DIR / clone_id
        out_dir.mkdir(parents=True, exist_ok=True)

        t_start = time.perf_counter()

        try:
            # ── 1. Doğrulama ──
            self._update_job(job_id, status="processing", progress=15, current_stage="Ses dosyası doğrulanıyor...")
            if not src_path.exists():
                raise FileNotFoundError(f"Yüklenen ses dosyası bulunamadı: {src_path}")

            # ── 2. FFmpeg Temizleme & Mastering ──
            self._update_job(job_id, progress=35, current_stage="FFmpeg ile 24kHz mastering, gürültü temizleme ve normalizasyon...")
            clean_wav = out_dir / "voice.wav"
            cmd = [
                "ffmpeg", "-y", "-i", str(src_path),
                "-vn", "-ac", "1", "-ar", "24000",
                "-filter:a", "loudnorm=I=-16:TP=-1.5:LRA=11,silenceremove=start_periods=1:start_threshold=-50dB:start_duration=0.2",
                str(clean_wav)
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            # Ses süresini oku
            try:
                audio_info = sf.info(str(clean_wav))
                sample_duration = round(audio_info.duration, 2)
            except Exception:
                sample_duration = 0.0

            # ── 3. Sinir Ağı ile Conditionals Çıkarma ──
            device = self.get_device()
            self._update_job(job_id, progress=60, current_stage=f"Apple Silicon ({device.upper()}) ile tını ve speaker embedding'ler çıkarılıyor...")
            
            from chatterbox.tts import ChatterboxTTS, Conditionals
            from chatterbox_voice import ChatterboxVoiceEngine
            
            engine = ChatterboxVoiceEngine()
            model = engine.get_model()
            
            # Sesi hazırla
            model.prepare_conditionals(str(clean_wav), exaggeration=0.5)

            # ── 4. Ses Profilini (.pt) Kaydet ──
            self._update_job(job_id, progress=80, current_stage="Ses profili (.pt) sinir ağı parametrelerine kaydediliyor...")
            clone_pt_path = out_dir / "voice.pt"
            model.conds.save(clone_pt_path)

            # ── 5. Test Önizleme Sentezi ──
            self._update_job(job_id, progress=92, current_stage="Örnek ses önizlemesi sentezleniyor...")
            preview_wav = out_dir / "preview.wav"
            test_phrase = "Merhaba! Yerel ses klonlama işlemi başarıyla tamamlandı. Artık tüm YouTube ve video projelerinizde benim sesimi kullanabilirsiniz."
            
            try:
                from chatterbox_generator import ChatterboxAudioGenerator
                gen = ChatterboxAudioGenerator()
                gen.generate(
                    text=test_phrase,
                    lang="tr",
                    output_path=str(preview_wav),
                    audio_prompt_path=str(clone_pt_path)
                )
            except Exception as synth_err:
                logger.warning(f"Önizleme sentezi uyarısı: {synth_err}")
                # Hata olsa bile ham wav'dan basit bir kopya veya sessizlik oluştur
                if not preview_wav.exists() and clean_wav.exists():
                    shutil.copyfile(clean_wav, preview_wav)

            total_elapsed = round(time.perf_counter() - t_start, 2)

            meta = {
                "id": clone_id,
                "name": name,
                "description": desc,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "audio_duration_sec": sample_duration,
                "processing_time_sec": total_elapsed,
                "voice_pt_path": str(clone_pt_path.resolve()),
                "voice_wav_path": str(clean_wav.resolve()),
                "preview_audio_path": str(preview_wav.resolve()),
                "device": device
            }

            meta_file = out_dir / "meta.json"
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            reg = self._read_registry()
            reg["clones"].append(meta)
            # Eğer kayıtlı aktif ses yoksa doğrudan aktif et
            if not reg.get("active_id"):
                reg["active_id"] = clone_id
                self.activate_clone(clone_id)
            else:
                self._write_registry(reg)

            self._update_job(
                job_id,
                status="completed",
                progress=100,
                current_stage=f"Tebrikler! Klonlama {total_elapsed} saniyede tamamlandı.",
                total_duration=total_elapsed,
                result=meta
            )
            logger.info(f"✅ Klonlama tamamlandı: {name} ({total_elapsed} sn)")

        except Exception as e:
            total_elapsed = round(time.perf_counter() - t_start, 2)
            logger.error(f"Klonlama hatası: {e}", exc_info=True)
            self._update_job(
                job_id,
                status="failed",
                progress=100,
                current_stage=f"Klonlama başarısız oldu: {str(e)}",
                total_duration=total_elapsed,
                error=str(e)
            )

    @staticmethod
    def run_rvc_inference(
        input_wav: str,
        output_wav: str,
        pth_path: str,
        index_path: str,
        pitch: int = 0,
        formant: float = 1.0
    ) -> bool:
        """Applio CLI üzerinden RVC ses dönüşümü (Voice Conversion) koşturur.
        pitch: Perde kaydırma (-24..24)
        formant: Ses yolu uzunluğu (1.0 = normal, 1.25 = çocuk, 0.92 = yaşlı)
        """
        applio_python = Path("/Users/alienes/Applio/env/bin/python")
        applio_core = Path("/Users/alienes/Applio/core.py")
        if not (applio_python.exists() and applio_core.exists()):
            logger.warning(f"Applio ortamı bulunamadı: {applio_python}")
            return False

        pth_abs = Path(pth_path).resolve()
        idx_abs = Path(index_path).resolve()
        in_abs = Path(input_wav).resolve()
        out_abs = Path(output_wav).resolve()

        if not (pth_abs.exists() and idx_abs.exists()):
            logger.warning(f"RVC model veya index dosyası eksik: {pth_abs}, {idx_abs}")
            return False

        out_abs.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(applio_python), str(applio_core), "infer",
            "--input-path", str(in_abs),
            "--output-path", str(out_abs),
            "--pth-path", str(pth_abs),
            "--index-path", str(idx_abs),
            "--pitch", str(pitch),
            "--f0-method", "rmvpe"
        ]
        if formant and abs(float(formant) - 1.0) > 0.01:
            f_val = str(round(float(formant), 2))
            cmd.extend([
                "--formant-shifting",
                "--formant-qfrency", f_val,
                "--formant-timbre", f_val
            ])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(applio_core.parent))
            if res.returncode == 0 and out_abs.exists():
                return True
            logger.error(f"RVC infer çıkış kodu: {res.returncode}, stderr: {res.stderr}")
            return False
        except Exception as e:
            logger.error(f"RVC inference hatası: {e}")
            return False

    def synthesize_speech(
        self,
        text: str,
        output_path: str,
        lang: str = "auto",
        pitch: int = 0,
        formant: float = 1.0,
        clone_id: Optional[str] = None
    ) -> bool:
        """Belirtilen metni aktif veya seçili klon ses ile (Chatterbox + Applio RVC + Watermark) sentezler.
        Çıktıyı doğrudan output_path dosyasına kaydeder.
        """
        reg = self._read_registry()
        target_id = clone_id or reg.get("active_id")
        clone = next((c for c in reg.get("clones", []) if c.get("id") == target_id), None)
        if not clone and reg.get("clones"):
            clone = reg["clones"][0]
        if not clone:
            logger.error("[VoiceCloneManager] Hiç kayıtlı klon ses bulunamadı.")
            return False

        # 23 Dilde Akıllı Dil Algılama
        SUPPORTED_CHATTERBOX_LANGS = {
            "tr", "en", "de", "fr", "es", "it", "ru", "ar", "ja", "ko",
            "zh", "pt", "nl", "pl", "sv", "da", "no", "fi", "el", "he", "hi"
        }

        if not lang or lang == "auto":
            try:
                from langdetect import detect
                detected_lang = detect(text[:600])
                if detected_lang in SUPPORTED_CHATTERBOX_LANGS:
                    lang = detected_lang
                    logger.info(f"[SYNTH] 🌐 Dil otomatik algılandı: {lang}")
                else:
                    lang = "tr"
            except Exception as det_err:
                logger.warning(f"Dil algılama uyarısı: {det_err}, varsayılan 'tr' kullanılıyor.")
                lang = "tr"

        if lang.lower().strip() == "tr":
            try:
                from text_normalizer import normalize_turkish_tts_text
                text = normalize_turkish_tts_text(text)
            except Exception:
                pass

        prompt_path = clone.get("voice_pt_path") or clone.get("voice_wav_path")
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        base_out = out_p.parent / f"base_{out_p.stem}_{int(time.time()*1000)%100000}.wav"

        from chatterbox_generator import ChatterboxAudioGenerator
        gen = ChatterboxAudioGenerator()
        ok, _ = gen.generate(
            text=text,
            lang=lang,
            output_path=str(base_out),
            audio_prompt_path=str(prompt_path) if prompt_path and os.path.exists(str(prompt_path)) else None
        )
        if not ok or not base_out.exists():
            logger.error("[VoiceCloneManager] Taban Chatterbox sesi üretilemedi.")
            return False

        # Eğer RVC modeli varsa, sesi Applio RVC modeli ile giydir
        pth = clone.get("rvc_pth_path")
        idx = clone.get("rvc_index_path")
        if pth and idx and os.path.exists(pth) and os.path.exists(idx):
            rvc_ok = self.run_rvc_inference(str(base_out), str(out_p), pth, idx, pitch=pitch, formant=formant)
            try:
                if base_out.exists():
                    os.remove(base_out)
            except Exception:
                pass
            if not rvc_ok or not out_p.exists():
                logger.warning("[VoiceCloneManager] RVC dönüşümü başarısız, taban ses taşınıyor.")
                shutil.move(str(base_out), str(out_p))
        else:
            if pitch and int(pitch) != 0:
                p_val = int(pitch)
                scale = 2.0 ** (p_val / 12.0)
                cmd_p = [
                    "ffmpeg", "-y", "-i", str(base_out),
                    "-af", f"asetrate=24000*{scale:.4f},atempo={1.0/scale:.4f},aresample=24000",
                    str(out_p)
                ]
                res_p = subprocess.run(cmd_p, capture_output=True)
                if not out_p.exists() or out_p.stat().st_size < 1000:
                    shutil.move(str(base_out), str(out_p))
                else:
                    try:
                        os.remove(base_out)
                    except Exception:
                        pass
            else:
                shutil.move(str(base_out), str(out_p))

        # Adli Ultrasonik Filigran Mühürleme
        if out_p.exists():
            try:
                from audio_watermark import AudioWatermarker
                AudioWatermarker.embed(str(out_p), signature="ALIENES!")
            except Exception as wm_err:
                logger.warning(f"Filigran ekleme uyarısı: {wm_err}")

        return out_p.exists() and out_p.stat().st_size > 500

    def synthesize_custom_test(
        self,
        clone_id: str,
        text: str,
        lang: str = "tr",
        pitch: int = 0,
        formant: float = 1.0
    ) -> Optional[str]:
        """Klonlanan sesle özel bir test cümlesi sentezleyip dosya yolunu döner.
        Çocuk, genç, yaşlı ve kadın tonları için pitch ve formant parametrelerini destekler.
        """
        out_dir = CLONES_DIR / clone_id
        timestamp = int(time.time())
        test_out = out_dir / f"test_{timestamp}.wav"
        ok = self.synthesize_speech(
            text=text,
            output_path=str(test_out),
            lang=lang,
            pitch=pitch,
            formant=formant,
            clone_id=clone_id
        )
        return str(test_out) if ok else None

    def apply_voice_clone_to_video(
        self,
        video_path: Union[str, Path],
        clone_id: Optional[str] = None,
        pitch: Optional[int] = None,
        formant: Optional[float] = None,
        output_path: Optional[Union[str, Path]] = None,
        embed_watermark: bool = True,
        bgm_path: Optional[Union[str, Path]] = None,
        bgm_volume: float = 0.18
    ) -> Dict[str, Any]:
        """
        Yerel Apple Silicon (MPS/CPU) hızlandırmasıyla videonun sesini çıkarır,
        aktif RVC ses klon modelini (Applio) giydirir, adli ultrasonik filigranı
        ekler ve videoyu YENİDEN KODLAMADAN (-c:v copy) saniyeler içinde birleştirir.
        """
        v_path = Path(video_path).resolve()
        if not v_path.exists() or v_path.stat().st_size < 10000:
            logger.error(f"[VoiceCloneManager] Geçersiz video dosyası: {v_path}")
            return {"success": False, "reason": "invalid_video_file", "video_path": str(v_path)}

        reg = self._read_registry()
        target_id = clone_id or reg.get("active_id")
        clone = next((c for c in reg.get("clones", []) if c.get("id") == target_id), None)
        if not clone and reg.get("clones"):
            clone = reg["clones"][0]

        if not clone:
            logger.warning("[VoiceCloneManager] Kayıtlı klon ses profili bulunamadı.")
            return {"success": False, "reason": "no_clone_found", "video_path": str(v_path)}

        pth = clone.get("rvc_pth_path")
        idx = clone.get("rvc_index_path")
        if not (pth and idx and os.path.exists(pth) and os.path.exists(idx)):
            logger.info(f"[VoiceCloneManager] Seçili ses profilinde RVC modeli tanımlı değil ({clone.get('name')}). Orijinal ses korunuyor.")
            return {"success": False, "reason": "no_rvc_model", "video_path": str(v_path), "clone_name": clone.get("name")}

        ts = int(time.time() * 1000) % 1000000
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        raw_audio = TEMP_DIR / f"extract_{ts}.wav"
        cloned_audio = TEMP_DIR / f"cloned_{ts}.wav"
        temp_video_out = TEMP_DIR / f"remux_{ts}.mp4"
        dest_video = Path(output_path).resolve() if output_path else v_path

        t_start = time.perf_counter()
        try:
            # 1. Videodan saf 44.1kHz mono sesi ayıkla
            logger.info(f"[VoiceCloneManager] 🎬 Videodan ses çıkarılıyor: {v_path.name}")
            cmd_extract = [
                "ffmpeg", "-y", "-i", str(v_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
                str(raw_audio)
            ]
            subprocess.run(cmd_extract, capture_output=True, check=True, timeout=120)

            if not raw_audio.exists() or raw_audio.stat().st_size < 1000:
                logger.error("[VoiceCloneManager] Videodan ses çıkarılamadı.")
                return {"success": False, "reason": "audio_extraction_failed", "video_path": str(v_path)}

            # 2. Applio RVC modeli ile ses tonunu dönüştür
            p_val = pitch if pitch is not None else 0
            f_val = formant if formant is not None else 1.0
            logger.info(f"[VoiceCloneManager] 🎙️ RVC ses dönüşümü başlatılıyor ({clone.get('name')}, pitch={p_val}, formant={f_val})...")

            rvc_ok = self.run_rvc_inference(
                input_wav=str(raw_audio),
                output_wav=str(cloned_audio),
                pth_path=str(pth),
                index_path=str(idx),
                pitch=p_val,
                formant=f_val
            )

            if not rvc_ok or not cloned_audio.exists() or cloned_audio.stat().st_size < 1000:
                logger.warning("[VoiceCloneManager] RVC dönüşümü başarısız oldu, orijinal ses korunuyor.")
                return {"success": False, "reason": "rvc_inference_failed", "video_path": str(v_path)}

            # 3. Adli Ultrasonik Filigran Mühürleme
            if embed_watermark:
                try:
                    from audio_watermark import AudioWatermarker
                    AudioWatermarker.embed(str(cloned_audio), signature="ALIENES!")
                    logger.info("[VoiceCloneManager] 🛡️ Ultrasonik telif filigranı (ALIENES!) mühürlendi.")
                except Exception as wm_err:
                    logger.warning(f"[VoiceCloneManager] Filigran uyarısı: {wm_err}")

            # 4. Hızlı Remux (Video Akışını Yeniden Kodlamadan: -c:v copy)
            logger.info("[VoiceCloneManager] ⚡ Hızlı remux yapılıyor (-c:v copy)...")
            resolved_bgm = None
            if bgm_path:
                bp = Path(bgm_path).resolve()
                if bp.exists():
                    resolved_bgm = bp

            # Sesi YouTube/Shorts standartlarına (EBU R128: -14 LUFS, True Peak -1.5dB) normalize et
            # Fon müziğini vokal frekanslarını baskılamayacak seviyeye (0.05 - 0.06 / -25dB) çek
            effective_bgm_vol = min(float(bgm_volume), 0.06) if float(bgm_volume) > 0.06 else float(bgm_volume)

            if resolved_bgm:
                logger.info(f"[VoiceCloneManager] 🎵 Fon müziği temiz ve dengeli miksleniyor ({resolved_bgm.name}, vol={effective_bgm_vol})...")
                cmd_remux = [
                    "ffmpeg", "-y",
                    "-i", str(v_path),
                    "-i", str(cloned_audio),
                    "-stream_loop", "-1", "-i", str(resolved_bgm),
                    "-filter_complex", (
                        f"[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[vocal_norm];"
                        f"[2:a]volume={effective_bgm_vol}[bgm];"
                        f"[vocal_norm][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
                    ),
                    "-c:v", "copy",
                    "-map", "0:v:0",
                    "-map", "[aout]",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    str(temp_video_out)
                ]
            else:
                cmd_remux = [
                    "ffmpeg", "-y",
                    "-i", str(v_path),
                    "-i", str(cloned_audio),
                    "-filter_complex", "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[aout]",
                    "-c:v", "copy",
                    "-map", "0:v:0",
                    "-map", "[aout]",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    str(temp_video_out)
                ]
            subprocess.run(cmd_remux, capture_output=True, check=True, timeout=120)

            if not temp_video_out.exists() or temp_video_out.stat().st_size < 10000:
                logger.error("[VoiceCloneManager] Remux işlemi başarısız veya boş dosya üretti.")
                return {"success": False, "reason": "remux_failed", "video_path": str(v_path)}

            # 5. Orijinal dosyanın yerine taşı (Atomik)
            shutil.move(str(temp_video_out), str(dest_video))
            elapsed = round(time.perf_counter() - t_start, 2)
            logger.info(f"✅ [VoiceCloneManager] Klon ses ve filigran {elapsed} sn içinde başarıyla giydirildi: {dest_video.name}")

            return {
                "success": True,
                "video_path": str(dest_video),
                "clone_id": target_id,
                "clone_name": clone.get("name", ""),
                "processing_time_sec": elapsed,
                "watermarked": embed_watermark
            }

        except Exception as e:
            logger.error(f"[VoiceCloneManager] apply_voice_clone_to_video hatası: {e}", exc_info=True)
            return {"success": False, "reason": str(e), "video_path": str(v_path)}
        finally:
            # Geçici dosyaları temizle
            for tmp_f in [raw_audio, cloned_audio, temp_video_out]:
                if tmp_f and tmp_f.exists():
                    try:
                        tmp_f.unlink(missing_ok=True)
                    except Exception:
                        pass



