"""
remote_runner.py
Oracle Cloud (132.226.187.103) Uzak Üretim Köprüsü.
Lokal yt-oto-video backend'inden sunucuya senaryoları ve görevleri iletir,
üretim sürecini düşük öncelikle (nice 19) koşturur ve durumu izler.
"""

from __future__ import annotations
import os
import re
import json
import time
import shutil
import tempfile
import subprocess
import shlex
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

SSH_HOST = "132.226.187.103"
SSH_USER = "ubuntu"
SSH_KEY_PATH = "/Users/alienes/new_affilate/ssh-key-2026-09-02 (1).key"
REMOTE_BASE_DIR = "/home/ubuntu/yt-remote-worker"


class RemoteRunner:
    def __init__(
        self,
        host: str = SSH_HOST,
        user: str = SSH_USER,
        key_path: str = SSH_KEY_PATH,
        remote_dir: str = REMOTE_BASE_DIR
    ):
        self.host = host
        self.user = user
        self.key_path = str(Path(key_path).expanduser().resolve())
        self.remote_dir = remote_dir

    def _run_ssh_cmd(self, cmd_str: str, timeout: int = 25) -> tuple[int, str, str]:
        """SSH üzerinden uzakta tekil komut çalıştırır."""
        ssh_cmd = [
            "ssh",
            "-i", self.key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            f"{self.user}@{self.host}",
            cmd_str
        ]
        try:
            proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "SSH komutu zaman aşımına uğradı."
        except Exception as e:
            return 1, "", str(e)

    def is_reachable(self) -> bool:
        """Sunucu erişilebilirliğini test eder."""
        try:
            rc, out, _ = self._run_ssh_cmd("echo PING_OK", timeout=5)
            return rc == 0 and "PING_OK" in out
        except Exception:
            return False

    def sync_credentials(self, local_credentials_dir: Optional[str] = None) -> bool:
        """Lokal OAuth credentials dosyalarını sunucuya senkronize eder."""
        cred_dir = Path(local_credentials_dir) if local_credentials_dir else Path(__file__).resolve().parent.parent / "credentials"
        if not cred_dir.exists():
            return False

        files = list(cred_dir.glob("*.json"))
        if not files:
            return False

        scp_cmd = [
            "scp",
            "-i", self.key_path,
            "-o", "StrictHostKeyChecking=no",
            *[str(f) for f in files],
            f"{self.user}@{self.host}:{self.remote_dir}/credentials/"
        ]
        try:
            proc = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
            return proc.returncode == 0
        except Exception as e:
            print(f"[RemoteRunner] Credentials sync hatası: {e}")
            return False

    def dispatch_job(
        self,
        job_id: str,
        channel_id: str,
        channel_config: dict,
        row_id: str,
        script_data: dict,
        custom_images: Optional[dict] = None,
        custom_audios: Optional[dict] = None,
        youtube_upload: bool = False
    ) -> Dict[str, Any]:
        """
        Sunucuda otonom video üretim görevini başlatır.
        """
        # 1. Sesler sağlanmamışsa ve indirmede klonlama kapalıysa yerel M4 üzerinde sentezle
        embedded_audios = custom_audios or {}
        if not embedded_audios:
            try:
                from settings_manager import SettingsManager
                auto_clone_on_dl = SettingsManager().get("auto_apply_voice_clone_on_download", False)
            except Exception:
                auto_clone_on_dl = False

            try:
                from voice_clone_manager import VoiceCloneManager
                has_clone = bool(VoiceCloneManager().get_active_clone())
            except Exception:
                has_clone = False

            if has_clone and not auto_clone_on_dl:
                fake_item = {
                    "material_id": job_id,
                    "channel_id": channel_id,
                    "row_id": row_id,
                    "script": script_data,
                    "folder_path": ""
                }
                try:
                    self._synthesize_item_audios_locally(fake_item, script_data, channel_config, embedded_audios, Path(tempfile.gettempdir()))
                except Exception as e_s:
                    print(f"[RemoteRunner] dispatch_job ses sentezleme uyarısı: {e_s}")

        # 1.8. Avatar görselini göm (eğer tanımlıysa ve custom_images'da yoksa)
        all_images = dict(custom_images or {})
        av_path_cfg = channel_config.get("reddit_avatar_path")
        if not av_path_cfg and "reddit" in channel_id.lower():
            try:
                from channel_manager import ChannelManager
                ch_m = ChannelManager()
                grp_info = ch_m.get_channel_group(channel_id)
                if grp_info and grp_info.get("reddit_avatar_path"):
                    av_path_cfg = grp_info.get("reddit_avatar_path")
            except Exception:
                pass

        if "avatar" not in all_images and av_path_cfg:
            av_p = Path(av_path_cfg)
            if not av_p.is_absolute():
                av_p = Path(__file__).resolve().parent.parent / av_p
            if av_p.exists():
                try:
                    with open(av_p, "rb") as f_img:
                        b64 = base64.b64encode(f_img.read()).decode("utf-8")
                        mime = "image/png" if av_p.suffix.lower() == ".png" else "image/jpeg"
                        all_images["avatar"] = f"data:{mime};base64,{b64}"
                except Exception as e_av:
                    print(f"[RemoteRunner] Reddit avatar okuma uyarısı: {e_av}")

        # 2. Job payload hazırla
        payload = {
            "job_id": job_id,
            "channel_id": channel_id,
            "channel_config": channel_config,
            "row_id": str(row_id),
            "script_data": script_data,
            "custom_images": all_images,
            "custom_audios": embedded_audios,
            "youtube_upload": youtube_upload,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        payload.update(self._remote_tts_options())

        # 2. Geçici yerel dosyaya yaz ve SCP ile sunucuya aktar
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
            json.dump(payload, tmp, ensure_ascii=False, indent=2)

        remote_job_file = f"{self.remote_dir}/jobs/{job_id}.json"
        scp_cmd = [
            "scp",
            "-i", self.key_path,
            "-o", "StrictHostKeyChecking=no",
            tmp_path,
            f"{self.user}@{self.host}:{remote_job_file}"
        ]

        try:
            subprocess.run(scp_cmd, capture_output=True, text=True, check=True, timeout=120)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        # 3. Sunucuda run_job.sh başlat (arka planda, düşük öncelikle)
        start_cmd = f"bash {self.remote_dir}/run_job.sh {remote_job_file}"
        rc, stdout, stderr = self._run_ssh_cmd(start_cmd, timeout=10)

        if rc != 0:
            raise RuntimeError(f"Sunucuda iş başlatılamadı: {stderr or stdout}")

        return {
            "success": True,
            "job_id": job_id,
            "channel_id": channel_id,
            "remote_job_file": remote_job_file,
            "status": "dispatched",
            "message": "Görev Oracle Cloud sunucusuna aktarıldı ve düşük öncelikle başlatıldı."
        }

    @staticmethod
    def _remote_tts_options() -> dict:
        try:
            from settings_manager import SettingsManager
        except ImportError:
            from src.settings_manager import SettingsManager

        settings = SettingsManager()
        try:
            speed = float(settings.get("kokoro_speed", "0.94"))
        except (TypeError, ValueError) as exc:
            raise ValueError("kokoro_speed sayısal bir değer olmalıdır.") from exc
        if not 0.8 <= speed <= 1.2:
            raise ValueError("kokoro_speed 0.8 ile 1.2 arasında olmalıdır.")

        engine = settings.get("remote_tts_engine", "chatterbox")
        if engine not in {"chatterbox", "kokoro"}:
            raise ValueError(f"Desteklenmeyen uzak TTS motoru: {engine}")
        return {
            "tts_engine": engine,
            "kokoro_voice": settings.get("kokoro_voice", "am_michael"),
            "kokoro_speed": speed,
        }

    def _synthesize_item_audios_locally(
        self,
        item: dict,
        script_data: dict,
        ch_config: dict,
        embedded_audios: dict,
        mat_folder: Path
    ):
        """
        Oracle Cloud sunucusuna göndermeden önce Apple Silicon M4 donanımıyla
        Ali Enes'in RVC klon sesini kullanarak tüm sahneleri/diyalogları ultra hızlı sentezler,
        adli filigranı basar ve custom_audios sözlüğüne base64 olarak ekler.
        """
        import base64
        import tempfile
        try:
            from voice_clone_manager import VoiceCloneManager
            vc_mgr = VoiceCloneManager()
            active_clone = vc_mgr.get_active_clone()
            if not active_clone:
                return
        except Exception as e_vc:
            print(f"[RemoteRunner] Ses klonlama motoru yüklenemedi: {e_vc}")
            return

        lang = (ch_config.get("language") or "auto").lower().strip()
        mat_dir = mat_folder if (mat_folder and mat_folder.exists()) else Path(tempfile.gettempdir())

        # Kanalın seçtiği özel ses klonunu çözümle (yoksa aktif global klon)
        channel_clone_id = (
            ch_config.get("voice_clone_id")
            or ch_config.get("edit_options", {}).get("voice_clone_id")
            or (active_clone.get("id") if active_clone else None)
        )

        # 1. WhatsApp Diyalog Mesajları
        messages = script_data.get("messages") or script_data.get("dialogue") or []
        if messages and isinstance(messages, list):
            print(f"[RemoteRunner] 🎙️ WhatsApp için {len(messages)} mesaj melez ses profilleri ve yaş/persona modülasyonuyla sentezleniyor (Kanal Klonu: {channel_clone_id})...")
            female_clone_id = "vc_ttsmaker_female_hybrid"
            male_clone_id = channel_clone_id or active_clone.get("id") or "vc_ttsmaker_enes_hybrid"

            for m_idx, msg in enumerate(messages):
                txt = str(msg.get("text") or msg.get("content") or msg.get("message") or "").strip()
                if not txt:
                    continue
                sender = str(msg.get("sender") or msg.get("from") or "me").lower()
                sender_name = str(msg.get("sender_name") or msg.get("name") or "").lower()
                full_ident = f"{sender} {sender_name}".lower()

                # Karakter / Rol / Cinsiyet ve Yaş persona tespiti
                is_me = ("me" in sender or "user" in sender or "ben" in sender or "sen" in sender_name or "you" in sender_name)

                female_keywords = [
                    "mom", "mother", "anne", "kadin", "kadın", "girl", "sister", "karım", "wifey",
                    "lady", "mrs", "abla", "kız", "kiz", "kizim", "kızım", "nine", "nene", "teyze",
                    "kaynana", "yenge", "büyükanne", "halacım", "hala", "sevgilim", "aşkım", "bayan"
                ]
                is_female = any(w in full_ident for w in female_keywords)

                elderly_keywords = [
                    "grandpa", "dede", "amca", "boss", "patron", "usta", "farooq", "landlord", "pops",
                    "nine", "nene", "teyze", "kaynana", "ihtiyar", "babaanne", "anneanne", "hacı", "haci", "valide"
                ]
                is_elderly = any(w in full_ident for w in elderly_keywords)

                child_keywords = [
                    "child", "kid", "cocuk", "çocuk", "oglum", "oğlum", "kizim", "kızım", "boy", "girl",
                    "ufaklık", "velet", "bebek", "küçük"
                ]
                is_child = any(w in full_ident for w in child_keywords)

                if is_female:
                    target_clone = female_clone_id
                    if is_child:
                        pitch, formant = 4, 1.08    # Canlı küçük kız çocuğu
                    elif is_elderly:
                        pitch, formant = -3, 0.94   # Tonton nine / olgun teyze
                    else:
                        pitch, formant = 0, 1.00    # Doğal yetişkin kadın sesi
                else:
                    target_clone = male_clone_id
                    if is_child:
                        pitch, formant = 5, 1.12    # Afacan erkek çocuk tonu
                    elif is_elderly:
                        pitch, formant = -3, 0.92   # Tok / otoriter dede, amca, patron
                    else:
                        pitch, formant = 0, 1.00    # Doğal genç / yetişkin erkek sesi

                out_wav = mat_dir / f"msg_{m_idx}.wav"
                ok = vc_mgr.synthesize_speech(
                    text=txt,
                    output_path=str(out_wav),
                    lang=lang,
                    pitch=pitch,
                    formant=formant,
                    clone_id=target_clone
                )
                if ok and out_wav.exists() and out_wav.stat().st_size > 500:
                    b64 = base64.b64encode(out_wav.read_bytes()).decode("utf-8")
                    embedded_audios[str(m_idx)] = f"data:audio/wav;base64,{b64}"
                    embedded_audios[f"msg_{m_idx}"] = f"data:audio/wav;base64,{b64}"
            return

        # 2. Havacılık, Reddit ve Sahne Odaklı Kanallar
        scenes = script_data.get("scenes") or []
        if scenes and isinstance(scenes, list):
            print(f"[RemoteRunner] 🎙️ {len(scenes)} sahne melez ses profilleri ile yerel M4'te sentezleniyor...")
            for s_idx, sc in enumerate(scenes):
                txt = str(sc.get("narration") or sc.get("text") or "").strip()
                if not txt:
                    continue
                speaker = str(sc.get("speaker") or sc.get("character") or sc.get("role") or "").lower()
                is_sc_female = (sc.get("gender") == "female") or any(w in speaker for w in ["kadin", "kadın", "anne", "kız", "girl", "woman", "wife", "abla", "nine"])
                target_cid = "vc_ttsmaker_female_hybrid" if is_sc_female else (channel_clone_id or active_clone.get("id") or "vc_ttsmaker_enes_hybrid")

                out_wav = mat_dir / f"scene_{s_idx}_audio.wav"
                ok = vc_mgr.synthesize_speech(
                    text=txt,
                    output_path=str(out_wav),
                    lang=lang,
                    pitch=0,
                    formant=1.0,
                    clone_id=target_cid
                )
                if ok and out_wav.exists() and out_wav.stat().st_size > 500:
                    b64 = base64.b64encode(out_wav.read_bytes()).decode("utf-8")
                    embedded_audios[str(s_idx)] = f"data:audio/wav;base64,{b64}"
                    embedded_audios[f"scene_{s_idx}"] = f"data:audio/wav;base64,{b64}"
            return

        # 3. Genel / Tek Parça Seslendirme (General & Belgesel)
        full_text = script_data.get("narration") or script_data.get("story") or script_data.get("body") or script_data.get("title") or ""
        if isinstance(full_text, list):
            full_text = " ".join(full_text)
        if full_text.strip():
            print(f"[RemoteRunner] 🎙️ Genel anlatım kanal ses klonu ({channel_clone_id}) ile yerel M4'te sentezleniyor...")
            out_wav = mat_dir / "voiceover.wav"
            ok = vc_mgr.synthesize_speech(
                text=full_text.strip(),
                output_path=str(out_wav),
                lang=lang,
                pitch=0,
                formant=1.0,
                clone_id=channel_clone_id
            )
            if ok and out_wav.exists() and out_wav.stat().st_size > 500:
                b64 = base64.b64encode(out_wav.read_bytes()).decode("utf-8")
                embedded_audios["0"] = f"data:audio/wav;base64,{b64}"
                embedded_audios["voiceover"] = f"data:audio/wav;base64,{b64}"

    def dispatch_batch_to_cloud_queue(
        self,
        items: list[dict],
        output_base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Kullanıcının seçtiği materyalleri (senaryolar, gömülü görseller, kanal konfigürasyonu)
        Oracle Cloud sıralı üretim kuyruğuna (/home/ubuntu/yt-remote-worker/queue/) aktarır.
        
        Tüm dosyaların sunucuya aktarıldığından emin olmak için:
        1. Her bir materyali self-contained JSON olarak paketler (görseller base64 data-uri yapılır).
        2. Geçici klasördeki tüm .json dosyalarını SCP ile sunucuya gönderir.
        3. SSH ile sunucudaki queue/ klasöründe bu dosyaların varlığını ve boyutlarını doğrular.
        4. start_queue.sh betiğini tetikleyerek bağımsız çalışan queue_runner.py'yi garanti altına alır.
        5. Yerel makinenin (Mac) güvenle kapatılabileceğini bildiren onay mesajı döner.
        """
        import base64
        from datetime import datetime
        try:
            from channel_manager import ChannelManager
            ch_mgr = ChannelManager()
            all_channels = {c["channel_id"]: c for c in ch_mgr.all_channels()}
        except Exception:
            all_channels = {}

        if not items:
            return {"success": False, "message": "Kuyruğa gönderilecek materyal seçilmedi."}

        # 1. Geçici staging klasörü oluştur
        temp_dir = Path(tempfile.mkdtemp(prefix="cloud_queue_batch_"))
        queued_jobs = []
        uploaded_filenames = []

        try:
            for idx, item in enumerate(items):
                mat_id = item.get("material_id") or item.get("id") or f"mat_{int(time.time())}_{idx}"
                ch_id = item.get("channel_id") or "general"
                row_id = str(item.get("row_id") or "")
                title = item.get("title") or f"Video #{row_id}"
                script_data = item.get("script") or {}
                raw_images = item.get("images") or {}

                # Kanal ayarlarını al
                ch_config = all_channels.get(ch_id, {})
                if not ch_config:
                    ch_config = {"channel_id": ch_id, "name": ch_id, "topic_category": item.get("channel_category") or "general"}

                # Görselleri göm (eğer yerel dosya ise base64'e çevir)
                embedded_images = {}
                if isinstance(raw_images, dict):
                    for k, val in raw_images.items():
                        if not val:
                            continue
                        val_str = str(val).strip()
                        if os.path.isfile(val_str):
                            try:
                                with open(val_str, "rb") as f_img:
                                    b64 = base64.b64encode(f_img.read()).decode("utf-8")
                                    mime = "image/png" if val_str.lower().endswith(".png") else "image/jpeg"
                                    embedded_images[str(k)] = f"data:{mime};base64,{b64}"
                            except Exception as e:
                                print(f"[RemoteRunner] Görsel okuma uyarısı ({val_str}): {e}")
                                embedded_images[str(k)] = val_str
                        else:
                            embedded_images[str(k)] = val_str

                # Eğer grup ise her üye kanal için ayrı bulut kuyruk işi oluştur
                if ch_id.startswith("group:"):
                    clean_gid = ch_id.replace("group:", "")
                    grp = ch_mgr.get_group(clean_gid)
                    member_cids = grp.get("channel_ids", []) if grp else []

                    # Çok dilli senaryo çözümlemesi
                    multi_scripts = {}
                    if isinstance(script_data, dict):
                        has_lang_keys = any(k in script_data for k in ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"])
                        if has_lang_keys:
                            multi_scripts = script_data
                        elif "scripts" in script_data and isinstance(script_data["scripts"], dict):
                            multi_scripts = script_data["scripts"]

                    try:
                        from localization_helper import ensure_localized_script
                    except ImportError:
                        from src.localization_helper import ensure_localized_script

                    for sub_idx, cid in enumerate(member_cids):
                        sub_cfg = all_channels.get(cid, {})
                        if not sub_cfg:
                            continue
                        sub_lang = (sub_cfg.get("language") or "tr").lower().strip()
                        base_sc = multi_scripts.get(sub_lang) or multi_scripts.get("tr") or script_data
                        sub_script = ensure_localized_script(base_sc, sub_lang)
                        sub_disp_title = sub_script.get("title") or title
                        sub_title = f"[{grp.get('name')}] {sub_cfg.get('name')} - {sub_disp_title}"
                        sub_job_id = f"exec_mat_{clean_gid}_{cid}_{row_id}_{int(time.time())}_{sub_idx}"
                        job_filepath = temp_dir / f"{sub_job_id}.json"

                        # Avatar görselini göm
                        sub_images = dict(embedded_images)
                        if "avatar" not in sub_images:
                            av_path_cfg = sub_cfg.get("reddit_avatar_path") or (grp.get("reddit_avatar_path") if grp else None)
                            if av_path_cfg:
                                av_p = Path(av_path_cfg)
                                if not av_p.is_absolute():
                                    av_p = Path(__file__).resolve().parent.parent / av_p
                                if av_p.exists():
                                    try:
                                        with open(av_p, "rb") as f_img:
                                            b64 = base64.b64encode(f_img.read()).decode("utf-8")
                                            mime = "image/png" if av_p.suffix.lower() == ".png" else "image/jpeg"
                                            sub_images["avatar"] = f"data:{mime};base64,{b64}"
                                    except Exception as e_av:
                                        print(f"[RemoteRunner] Group member avatar okuma uyarısı: {e_av}")

                        sub_payload = {
                            "job_id": sub_job_id,
                            "channel_id": cid,
                            "channel_config": sub_cfg,
                            "row_id": str(row_id),
                            "title": sub_title,
                            "script_data": sub_script,
                            "custom_images": sub_images,
                            "custom_audios": {},
                            "youtube_upload": bool(item.get("youtube_upload", False)),
                            "created_at": datetime.now().isoformat()
                        }
                        sub_payload.update(self._remote_tts_options())
                        job_filepath.write_text(json.dumps(sub_payload, ensure_ascii=False, indent=2), encoding="utf-8")

                        uploaded_filenames.append(f"{sub_job_id}.json")
                        queued_jobs.append({
                            "job_id": sub_job_id,
                            "channel_id": cid,
                            "material_id": mat_id,
                            "row_id": row_id,
                            "title": sub_title,
                            "channel_name": sub_cfg.get("name")
                        })
                    continue

                # Sesleri göm (Eğer Chatterbox veya önceden üretilmiş ses varsa base64 yap)
                embedded_audios = {}
                is_crayon_job = (
                    (ch_config.get("topic_category") or "").lower() == "crayon_combat"
                    or any(name in ch_id.lower() for name in ("tacticallcrayon", "tacticalcrayon"))
                )
                mat_folder = Path(item.get("folder_path") or "")
                if mat_folder.exists() and not is_crayon_job:
                    for f_aud in sorted(mat_folder.glob("scene_*_audio.*")):
                        m_idx = re.search(r"scene_(\d+)_audio", f_aud.name)
                        if m_idx:
                            idx_str = m_idx.group(1)
                            try:
                                with open(f_aud, "rb") as fa:
                                    b64_a = base64.b64encode(fa.read()).decode("utf-8")
                                    mime_a = "audio/wav" if f_aud.suffix.lower() == ".wav" else "audio/mpeg"
                                    embedded_audios[idx_str] = f"data:{mime_a};base64,{b64_a}"
                            except Exception as e_a:
                                print(f"[RemoteRunner] Ses okuma uyarısı ({f_aud}): {e_a}")
                    for f_aud in sorted(mat_folder.glob("msg_*.*")):
                        m_idx = re.search(r"msg_(\d+)", f_aud.name)
                        if m_idx:
                            idx_str = m_idx.group(1)
                            try:
                                with open(f_aud, "rb") as fa:
                                    b64_a = base64.b64encode(fa.read()).decode("utf-8")
                                    mime_a = "audio/wav" if f_aud.suffix.lower() == ".wav" else "audio/mpeg"
                                    embedded_audios[idx_str] = f"data:{mime_a};base64,{b64_a}"
                            except Exception as e_a:
                                print(f"[RemoteRunner] WhatsApp ses okuma uyarısı ({f_aud}): {e_a}")
                    voiceover_f = mat_folder / "voiceover.wav"
                    if not voiceover_f.exists():
                        voiceover_f = mat_folder / "voiceover.mp3"
                    if voiceover_f.exists() and "0" not in embedded_audios:
                        try:
                            with open(voiceover_f, "rb") as fa:
                                b64_a = base64.b64encode(fa.read()).decode("utf-8")
                                mime_a = "audio/wav" if voiceover_f.suffix.lower() == ".wav" else "audio/mpeg"
                                embedded_audios["0"] = f"data:{mime_a};base64,{b64_a}"
                                embedded_audios["voiceover"] = f"data:{mime_a};base64,{b64_a}"
                        except Exception as e_a:
                            print(f"[RemoteRunner] Voiceover okuma uyarısı ({voiceover_f}): {e_a}")

                # Eğer diskte ses yoksa ve aktif klon ses profili tanımlıysa VE indirmede klonlama kapalıysa yerel Apple Silicon M4 gücüyle önceden sentezle
                if not embedded_audios and not is_crayon_job:
                    try:
                        from settings_manager import SettingsManager
                        auto_clone_on_dl = SettingsManager().get("auto_apply_voice_clone_on_download", False)
                    except Exception:
                        auto_clone_on_dl = False

                    try:
                        from voice_clone_manager import VoiceCloneManager
                        has_clone = bool(VoiceCloneManager().get_active_clone())
                    except Exception:
                        has_clone = False

                    if has_clone and not auto_clone_on_dl:
                        try:
                            self._synthesize_item_audios_locally(item, script_data, ch_config, embedded_audios, mat_folder)
                        except Exception as e_s:
                            print(f"[RemoteRunner] Kuyruk için yerel ses sentezleme uyarısı: {e_s}")

                job_id = f"exec_{mat_id}"
                job_filename = f"{job_id}.json"
                job_filepath = temp_dir / job_filename

                # Avatar görselini göm (tekil kanal için)
                if "avatar" not in embedded_images:
                    av_path_cfg = ch_config.get("reddit_avatar_path")
                    if not av_path_cfg and "reddit" in ch_id.lower():
                        try:
                            grp_info = ch_mgr.get_channel_group(ch_id)
                            if grp_info and grp_info.get("reddit_avatar_path"):
                                av_path_cfg = grp_info.get("reddit_avatar_path")
                        except Exception:
                            pass
                    if av_path_cfg:
                        av_p = Path(av_path_cfg)
                        if not av_p.is_absolute():
                            av_p = Path(__file__).resolve().parent.parent / av_p
                        if av_p.exists():
                            try:
                                with open(av_p, "rb") as f_img:
                                    b64 = base64.b64encode(f_img.read()).decode("utf-8")
                                    mime = "image/png" if av_p.suffix.lower() == ".png" else "image/jpeg"
                                    embedded_images["avatar"] = f"data:{mime};base64,{b64}"
                            except Exception as e_av:
                                print(f"[RemoteRunner] Single channel avatar okuma uyarısı: {e_av}")

                payload = {
                    "job_id": job_id,
                    "channel_id": ch_id,
                    "channel_config": ch_config,
                    "row_id": row_id,
                    "title": title,
                    "script_data": script_data,
                    "custom_images": embedded_images,
                    "custom_audios": embedded_audios,
                    "youtube_upload": bool(item.get("youtube_upload", False)),
                    "created_at": datetime.now().isoformat()
                }
                payload.update(self._remote_tts_options())

                job_filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                queued_jobs.append({
                    "job_id": job_id,
                    "channel_id": ch_id,
                    "material_id": mat_id,
                    "row_id": row_id,
                    "title": title,
                    "file_name": job_filename
                })
                uploaded_filenames.append(job_filename)

            # Stage outside the queue; only complete, valid JSON jobs are atomically published.
            remote_queue_dir = f"{self.remote_dir}/queue"
            remote_stage_dir = f"{remote_queue_dir}/.incoming/{uuid.uuid4().hex}"
            remote_stage_quoted = shlex.quote(remote_stage_dir)
            stage_rc, _, stage_err = self._run_ssh_cmd(
                f"mkdir -p -- {remote_stage_quoted}",
                timeout=15,
            )
            if stage_rc != 0:
                raise RuntimeError(f"Sunucuda geçici kuyruk dizini oluşturulamadı: {stage_err.strip()}")

            expected_sizes = {
                filename: (temp_dir / filename).stat().st_size
                for filename in uploaded_filenames
            }
            total_bytes = sum(expected_sizes.values())
            transfer_timeout = max(120, min(1800, 120 + (total_bytes // (1024 * 1024)) * 15))
            try:
                scp_cmd = [
                    "scp",
                    "-i", self.key_path,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    "-o", "ServerAliveInterval=15",
                    "-o", "ServerAliveCountMax=3",
                    *[str(temp_dir / f) for f in uploaded_filenames],
                    f"{self.user}@{self.host}:{remote_stage_dir}/"
                ]
                try:
                    proc = subprocess.run(
                        scp_cmd,
                        capture_output=True,
                        text=True,
                        timeout=transfer_timeout,
                    )
                except subprocess.TimeoutExpired as e:
                    raise RuntimeError(
                        f"Dosyaların sunucuya aktarımı {transfer_timeout} saniyede tamamlanmadı "
                        f"(toplam {total_bytes / (1024 * 1024):.1f} MB)."
                    ) from e
                if proc.returncode != 0:
                    raise RuntimeError(f"Dosyalar sunucuya SCP ile aktarılamadı: {proc.stderr.strip()}")

                verify_script = f"""
import json, os
from pathlib import Path
stage_dir = Path({remote_stage_dir!r})
queue_dir = Path({remote_queue_dir!r})
expected = {json.dumps(expected_sizes)}
for filename, expected_size in expected.items():
    source = stage_dir / filename
    if not source.is_file() or source.stat().st_size != expected_size or source.stat().st_size <= 100:
        raise RuntimeError(f"Dosya boyutu doğrulanamadı: {{filename}}")
    with source.open("r", encoding="utf-8") as job_file:
        json.load(job_file)
for filename in expected:
    os.replace(stage_dir / filename, queue_dir / filename)
print(json.dumps({{"verified": list(expected)}}))
"""
                rc_ver, ver_out, ver_err = self._run_ssh_cmd(
                    f"python3 -c {shlex.quote(verify_script)}",
                    timeout=30,
                )
                if rc_ver != 0 or not ver_out.strip():
                    raise RuntimeError(f"Sunucuya aktarılan iş dosyaları doğrulanamadı: {ver_err.strip()}")
                try:
                    ver_data = json.loads(ver_out.strip())
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Sunucudan geçersiz doğrulama yanıtı alındı: {ver_out.strip()}") from exc
                verified_count = len(ver_data.get("verified", []))
                if verified_count != len(uploaded_filenames):
                    raise RuntimeError(
                        f"Bazı dosyalar sunucuda doğrulanamadı: {verified_count}/{len(uploaded_filenames)}"
                    )
            finally:
                self._run_ssh_cmd(
                    f"rm -rf -- {remote_stage_quoted}",
                    timeout=15,
                )

            # 4. Sunucudaki start_queue.sh betiğini çalıştır (arka plan kuyruk sürecini başlat/tetikle)
            start_rc, start_out, _ = self._run_ssh_cmd(f"bash {self.remote_dir}/start_queue.sh", timeout=15)
            print(f"[RemoteRunner] start_queue.sh çıktısı (RC {start_rc}): {start_out.strip()}")

            return {
                "success": True,
                "verified": True,
                "total_queued": len(queued_jobs),
                "verified_count": verified_count,
                "jobs": queued_jobs,
                "safe_to_shutdown": True,
                "feedback_message": (
                    f"Tüm materyaller ({verified_count} adet video planı) Oracle Cloud sunucusuna "
                    "eksiksiz aktarıldı ve doğrulandı! Yerel bilgisayarınızı (Mac) güvenle kapatabilir "
                    "veya uyku moduna alabilirsiniz. Sunucu arka planda sırayla (FIFO) üretime devam edecek."
                )
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Sunucudaki görevin anlık durumunu döndürür."""
        try:
            status_file = f"{self.remote_dir}/jobs/{job_id}_status.json"
            cmd = f"cat {status_file} 2>/dev/null || echo ''"
            rc, stdout, _ = self._run_ssh_cmd(cmd, timeout=20)

            if rc == 0 and stdout.strip():
                try:
                    return json.loads(stdout.strip())
                except Exception:
                    pass

            # Durum dosyası henüz oluşmadıysa veya geçici gecikme varsa log dosyasının son satırlarını kontrol et
            log_file = f"{self.remote_dir}/logs/{job_id}.log"
            rc_log, log_out, _ = self._run_ssh_cmd(f"tail -n 5 {log_file} 2>/dev/null || echo ''", timeout=15)
            
            return {
                "job_id": job_id,
                "status": "rendering",
                "progress": 30,
                "message": "Sunucuda render devam ediyor...",
                "recent_log": log_out.strip() if rc_log == 0 else ""
            }
        except Exception:
            return {
                "job_id": job_id,
                "status": "rendering",
                "progress": 30,
                "message": "Sunucuda render devam ediyor (durum sorgulanıyor)..."
            }

    def download_final_video(self, job_id: str, channel_id: str, local_dest_path: str) -> bool:
        """Sunucuda üretilen nihai MP4 videosunu (final_video.mp4 veya final.mp4) yerel bilgisayara çeker."""
        dest_p = Path(local_dest_path).resolve()
        dest_p.parent.mkdir(parents=True, exist_ok=True)

        # Nihai dosyanın varlığını doğrula (ASLA ara sahne klibi scene_*.mp4 indirme!)
        find_cmd = (
            f"for f in {self.remote_dir}/output/{channel_id}/{job_id}/final_video.mp4 "
            f"{self.remote_dir}/output/{channel_id}/{job_id}/final.mp4; do "
            f"if [ -f \"$f\" ] && [ $(stat -c%s \"$f\" 2>/dev/null || stat -f%z \"$f\" 2>/dev/null || echo 0) -gt 100000 ]; then "
            f"echo \"$f\"; break; fi; done"
        )
        rc, out, _ = self._run_ssh_cmd(find_cmd, timeout=10)
        remote_video = out.strip()
        if not remote_video:
            print(f"[RemoteRunner] ⚠️ Nihai video henüz hazır değil ({channel_id}/{job_id}). Render tamamlanması bekleniyor...")
            return False

        # 1. Öncelik: rsync ile hızlı, sıkıştırılmış ve kesilirse devam edebilen (resume) indirme
        rsync_cmd = [
            "rsync",
            "-avz",
            "--partial",
            "--inplace",
            "-e", f"ssh -i '{self.key_path}' -o StrictHostKeyChecking=no",
            f"{self.user}@{self.host}:{remote_video}",
            str(dest_p)
        ]
        try:
            proc_r = subprocess.run(rsync_cmd, capture_output=True, text=True, timeout=1800)
            if proc_r.returncode == 0 and dest_p.exists() and dest_p.stat().st_size > 100000:
                return True
        except Exception as e_r:
            print(f"[RemoteRunner] rsync denemesi uyarısı: {e_r}. scp fallback deneniyor...")

        # 2. Öncelik: Standart scp fallback (30 dakika zaman aşımı)
        scp_cmd = [
            "scp",
            "-i", self.key_path,
            "-o", "StrictHostKeyChecking=no",
            f"{self.user}@{self.host}:{remote_video}",
            str(dest_p)
        ]
        try:
            proc = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=1800)
            return proc.returncode == 0 and dest_p.exists() and dest_p.stat().st_size > 100000
        except Exception as e:
            print(f"[RemoteRunner] SCP indirme hatası: {e}")
            return False

    def list_server_videos(self, channel_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """Sunucuda üretilmiş ve indirilmeyi bekleyen videoları listeler (Sadece tamamlanmış nihai videolar)."""
        py_cmd = f"""python3 -c "
import os, json, glob
res = []
base = '{self.remote_dir}'
status_path = os.path.join(base, 'queue_status.json')
current_active_job = ''
if os.path.exists(status_path):
    try:
        q_stat = json.loads(open(status_path, 'r', encoding='utf-8').read())
        current_active_job = q_stat.get('current_job', '')
    except Exception:
        pass

pattern = '{self.remote_dir}/output/{channel_id or '*'}'
# SADECE nihai videoları ara; her iş klasöründen yalnızca tek ve en güncel olanı al (final_video.mp4 öncelikli)
seen_jobs = set()
for jd in glob.glob(pattern + '/*'):
    if not os.path.isdir(jd):
        continue
    parts = jd.split('/')
    if len(parts) < 3:
        continue
    ch = parts[-2]
    jid = parts[-1]
    if (ch, jid) in seen_jobs or jid == current_active_job:
        continue

    p = None
    for cand in ['final_video.mp4', 'final.mp4']:
        cp = os.path.join(jd, cand)
        if os.path.isfile(cp):
            p = cp
            break
    if not p:
        continue

    try:
        size_mb = round(os.path.getsize(p) / (1024*1024), 2)
        if size_mb < 0.1:
            continue
    except Exception:
        continue

    seen_jobs.add((ch, jid))
    meta_path = os.path.join(jd, 'metadata.json')
    video_info_path = os.path.join(jd, 'video_info.json')
    meta = {{}}
    if os.path.exists(meta_path):
        try:
            meta = json.loads(open(meta_path, 'r', encoding='utf-8').read())
        except Exception:
            pass
    elif os.path.exists(video_info_path):
        try:
            meta = json.loads(open(video_info_path, 'r', encoding='utf-8').read())
        except Exception:
            pass
    source_job_path = os.path.join(base, 'jobs', jid + '.json')
    res.append({{
        'channel_id': ch,
        'job_id': jid,
        'file_path': p,
        'file_name': os.path.basename(p),
        'size_mb': size_mb,
        'can_regenerate': os.path.isfile(source_job_path),
        'title': meta.get('title') or f'{{ch}} - {{jid}}',
        'created_at': meta.get('created_at'),
        'duration': meta.get('duration', 45),
        'row_id': str(meta.get('row_id') or meta.get('plan_id') or '')
    }})
print(json.dumps(res))
" """
        rc, stdout, _ = self._run_ssh_cmd(py_cmd, timeout=12)
        if rc == 0 and stdout.strip():
            try:
                return json.loads(stdout.strip())
            except Exception:
                pass

        # Fallback: ls -l (Sadece final_video.mp4)
        path_filter = f"{self.remote_dir}/output/{channel_id}/*/final_video.mp4" if channel_id else f"{self.remote_dir}/output/*/*/final_video.mp4"
        cmd = f"ls -l {path_filter} 2>/dev/null || true"
        rc, stdout, _ = self._run_ssh_cmd(cmd, timeout=10)

        results = []
        if not stdout.strip():
            return results

        lines = stdout.strip().split("\n")
        for line in lines:
            parts = line.split()
            if len(parts) >= 9:
                file_path = parts[-1]
                size_bytes = int(parts[4]) if parts[4].isdigit() else 0
                p_parts = file_path.split("/")
                if len(p_parts) >= 4:
                    ch = p_parts[-3]
                    jid = p_parts[-2]
                    results.append({
                        "channel_id": ch,
                        "job_id": jid,
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "size_mb": round(size_bytes / (1024 * 1024), 2),
                        "can_regenerate": False,
                        "title": f"{ch} - {jid}",
                        "duration": 45
                    })
        return results

    def regenerate_server_video(self, channel_id: str, job_id: str) -> Dict[str, Any]:
        """Requeue one completed server video from its retained original job payload."""
        for value, label in ((channel_id, "Kanal"), (job_id, "İş")):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", value or ""):
                raise ValueError(f"{label} kimliği geçersiz.")

        script = """
import json, os, re, secrets, sys, time
from pathlib import Path

base = Path(sys.argv[1])
channel_id, source_job_id = sys.argv[2:4]
def fail(message, code=2):
    print(json.dumps({"success": False, "message": message}, ensure_ascii=False))
    raise SystemExit(code)

video_dir = base / "output" / channel_id / source_job_id
video_paths = [video_dir / "final_video.mp4", video_dir / "final.mp4"]
if not any(path.is_file() and path.stat().st_size > 100_000 for path in video_paths):
    fail("Sunucuda yeniden üretilebilecek hazır video bulunamadı.")

source_payload_path = base / "jobs" / f"{source_job_id}.json"
if not source_payload_path.is_file():
    fail("Bu videonun üretim materyali sunucuda bulunamadı; yeniden üretim yapılamıyor.")
try:
    payload = json.loads(source_payload_path.read_text(encoding="utf-8"))
except Exception as error:
    fail(f"Kaynak üretim materyali okunamadı: {error}")
if payload.get("channel_id") != channel_id or payload.get("job_id") != source_job_id:
    fail("Kaynak üretim materyali seçilen video ile eşleşmiyor.")

queue_dir = base / "queue"
queue_dir.mkdir(parents=True, exist_ok=True)
refresh_prefix = f"{source_job_id}_refresh_"
for queued_path in queue_dir.glob("*.json"):
    try:
        queued_payload = json.loads(queued_path.read_text(encoding="utf-8"))
    except Exception:
        continue
    if queued_payload.get("job_id", "").startswith(refresh_prefix):
        fail("Bu video için yeniden üretim zaten kuyrukta.")
jobs_dir = base / "jobs"
for status_path in jobs_dir.glob(f"{source_job_id}_refresh_*_status.json"):
    try:
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        continue
    if status_data.get("status") in {"queued", "running", "rendering", "uploading"}:
        fail("Bu video şu anda yeniden üretiliyor.")
timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
new_job_id = f"{source_job_id}_refresh_{timestamp}_{secrets.token_hex(3)}"
payload["job_id"] = new_job_id
payload["regenerated_from_job_id"] = source_job_id
payload["youtube_upload"] = False
payload["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
staged_path = queue_dir / f".{new_job_id}.tmp"
queue_path = queue_dir / f"{new_job_id}.json"
try:
    with staged_path.open("x", encoding="utf-8") as job_file:
        json.dump(payload, job_file, ensure_ascii=False, indent=2)
    os.replace(staged_path, queue_path)
except Exception as error:
    staged_path.unlink(missing_ok=True)
    fail(f"Yeniden üretim kuyruğu hazırlanamadı: {error}")
print(json.dumps({
    "success": True,
    "job_id": new_job_id,
    "channel_id": channel_id,
    "source_job_id": source_job_id
}, ensure_ascii=False))
"""
        command = (
            f"python3 -c {shlex.quote(script)} "
            f"{shlex.quote(self.remote_dir)} {shlex.quote(channel_id)} {shlex.quote(job_id)}"
        )
        rc, stdout, stderr = self._run_ssh_cmd(command, timeout=30)
        try:
            result = json.loads(stdout.strip()) if stdout.strip() else {}
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Sunucudan geçersiz yeniden üretim yanıtı alındı: {stdout.strip()}") from error
        if rc != 0 or not result.get("success"):
            message = result.get("message") or stderr.strip() or "Yeniden üretim kuyruğa eklenemedi."
            raise RuntimeError(message)

        start_rc, start_out, start_err = self._run_ssh_cmd(
            f"bash {shlex.quote(self.remote_dir + '/start_queue.sh')}",
            timeout=15,
        )
        if start_rc != 0:
            raise RuntimeError(
                "Video yeniden üretim kuyruğuna eklendi ancak sunucu kuyruğu başlatılamadı: "
                f"{start_err.strip() or start_out.strip()}"
            )
        result["message"] = "Video güncel üretim koduyla yeniden üretilmek üzere kuyruğa eklendi."
        return result

    def get_queue_status(self) -> Dict[str, Any]:
        """Sunucu sıralı görev kuyruğu durumunu (kalan iş, aktif çalışan, vb.) sorgular."""
        py_cmd = f"""python3 -c "
import os, json, glob
base = '{self.remote_dir}'
status_path = os.path.join(base, 'queue_status.json')
q_files = glob.glob(os.path.join(base, 'queue', '*.json'))
j_files = glob.glob(os.path.join(base, 'jobs', '*.json'))
info = {{}}
if os.path.exists(status_path):
    try:
        info = json.loads(open(status_path, 'r', encoding='utf-8').read())
    except Exception:
        pass
info['queue_count'] = len(q_files)
info['jobs_count'] = len(j_files)
info['queue_files'] = [os.path.basename(f) for f in sorted(q_files)]
print(json.dumps(info))
" """
        rc, stdout, _ = self._run_ssh_cmd(py_cmd, timeout=10)
        if rc == 0 and stdout.strip():
            try:
                res = json.loads(stdout.strip())
                # Runner sürecinin PID kontrolü (bracket trick ile grep'in kendi sürecini eşleştirmesini önle)
                rc_p, p_out, _ = self._run_ssh_cmd("ps -eo pid,args | grep '[q]ueue_runner.py' || true", timeout=5)
                has_proc = bool(rc_p == 0 and p_out.strip())
                # Eğer süreç çalışmıyorsa veya kuyruk boşsa ve aktif iş yoksa is_running False olmalıdır
                if not has_proc or (res.get("queue_count", 0) == 0 and not res.get("current_job")):
                    res["is_running"] = False
                else:
                    res["is_running"] = True
                return res
            except Exception:
                pass
        return {"queue_count": 0, "jobs_count": 0, "is_running": False}

    def delete_remote_job(self, job_id: str, channel_id: Optional[str] = None) -> bool:
        """Sunucudaki işi, çıktılarını, kuyruk ve durum dosyalarını tamamen temizler."""
        ch_filter = channel_id if channel_id and channel_id != "default" else "*"
        del_cmd = f"""python3 -c "
import os, glob, shutil
base = '{self.remote_dir}'
# 1. Output klasörünü sil
for d in glob.glob(os.path.join(base, 'output', '{ch_filter}', '{job_id}*')):
    shutil.rmtree(d, ignore_errors=True)
# 2. Jobs ve Queue dosyalarını sil
for f in glob.glob(os.path.join(base, 'jobs', '{job_id}*')):
    try: os.remove(f)
    except Exception: pass
for f in glob.glob(os.path.join(base, 'queue', '{job_id}*')):
    try: os.remove(f)
    except Exception: pass
for f in glob.glob(os.path.join(base, 'logs', '{job_id}*')):
    try: os.remove(f)
    except Exception: pass
print('DELETED')
" """
        rc, out, _ = self._run_ssh_cmd(del_cmd, timeout=15)
        return rc == 0

    def is_job_downloaded_locally(self, channel_id: str, job_id: str, local_base_dir: Optional[str] = None) -> bool:
        """Belirtilen job_id'ye ait geçerli bir videonun yerel diskte (kontrol, yuklenecek, yuklenen) zaten var olup olmadığını denetler."""
        if not channel_id or not job_id:
            return False
        base = Path(local_base_dir) if local_base_dir else Path(__file__).resolve().parent.parent / "output"
        ch_base = base / channel_id
        if not ch_base.exists():
            return False
        for sub in ["kontrol", "yuklenecek", "yuklenen", ""]:
            s_dir = ch_base / sub if sub else ch_base
            if not s_dir.exists() or not s_dir.is_dir():
                continue
            for item in s_dir.iterdir():
                if item.is_dir() and job_id in item.name:
                    v1 = item / "final.mp4"
                    v2 = item / "video.mp4"
                    if (v1.exists() and v1.stat().st_size > 500000) or (v2.exists() and v2.stat().st_size > 500000):
                        return True
        return False

    def download_and_cleanup_job(
        self,
        channel_id: str,
        job_id: str,
        local_base_dir: Optional[str] = None,
        delete_remote: bool = False,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Sunucudan videoyu ve metadatasını indirip 'output/<channel_id>/yuklenecek/' veya 'kontrol/' klasörüne kaydeder,
        ardından sunucudaki dosyaları temizler.
        """
        # 0. Ön Denetim: Video yerelde zaten mevcut mu? (Mükerrer indirmeyi önle, force=True ise yeniden indir)
        if not force and self.is_job_downloaded_locally(channel_id, job_id, local_base_dir):
            print(f"[RemoteRunner] ℹ️ İş '{job_id}' ({channel_id}) yerelde zaten mevcut. Mükerrer indirme engellendi.")
            if delete_remote:
                self.delete_remote_job(job_id, channel_id)
            return {
                "success": True,
                "job_id": job_id,
                "channel_id": channel_id,
                "already_existed": True,
                "message": "Video yerelde zaten mevcut olduğundan mükerrer indirme atlandı."
            }

        # 0.1. Kanal Kalite Kontrol (AI QA) Ayarını Kontrol Et
        is_auto_qa = False
        try:
            from src.channel_manager import ChannelManager
            cm = ChannelManager()
            ch_cfg = cm.get_channel(channel_id)
            if ch_cfg:
                is_auto_qa = bool(
                    ch_cfg.get("auto_ai_qa_enabled") or
                    ch_cfg.get("auto_ai_qa", {}).get("enabled") or
                    ch_cfg.get("edit_options", {}).get("auto_ai_qa_enabled")
                )
        except Exception:
            pass

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base = Path(local_base_dir) if local_base_dir else Path(__file__).resolve().parent.parent / "output"
        # Tüm sunucudan indirilen videolar öncelikle kalite kontrol için 'kontrol' klasörüne kaydedilir.
        # Kullanıcı arayüzden 'Kontrolden Geçti' butonuna basınca 'yuklenecek' klasörüne aktarılır.
        sub_folder = "kontrol"
        target_dir = base / channel_id / sub_folder / f"{timestamp}_{job_id}"
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            remote_job_dir = f"{self.remote_dir}/output/{channel_id}/{job_id}"
            dest_video = target_dir / "final.mp4"

            # 1. Video dosyasını indir
            ok = self.download_final_video(job_id, channel_id, str(dest_video))
            if not ok or not dest_video.exists() or dest_video.stat().st_size < 100000:
                raise RuntimeError(f"Video sunucudan indirilemedi veya geçersiz boyutta ({channel_id}/{job_id}).")

            # 2. Metadata, altyazı ve video_info dosyalarını indir (BGM ve kanal bilgilerini içerir)
            meta_data = {}
            for meta_name in ["metadata.json", "video_info.json", "subtitles.srt", "youtube_chapters.txt"]:
                remote_meta = f"{remote_job_dir}/{meta_name}"
                dest_meta = target_dir / meta_name
                scp_meta = [
                    "scp",
                    "-i", self.key_path,
                    "-o", "StrictHostKeyChecking=no",
                    f"{self.user}@{self.host}:{remote_meta}",
                    str(dest_meta)
                ]
                try:
                    subprocess.run(scp_meta, capture_output=True, timeout=15)
                    if meta_name == "metadata.json" and dest_meta.exists():
                        meta_data = json.loads(dest_meta.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # 2.5. Fon Müziğini (BGM) Çözümle
            bgm_track_name = meta_data.get("bgm_track")
            if not bgm_track_name:
                if "reddit" in channel_id.lower() or "reddit" in str(meta_data.get("topic_category", "")).lower():
                    bgm_track_name = "reddit_official_bgm.mp3"
                elif "wa" in channel_id.lower() or "chat" in channel_id.lower():
                    bgm_track_name = "monkeys_spinning.mp3"

            bgm_volume = float(meta_data.get("bgm_volume", 0.18))
            local_bgm_path = None
            if bgm_track_name:
                proj_root = Path(__file__).resolve().parent.parent
                candidates_bgm = [
                    proj_root / "config" / "bgm" / bgm_track_name,
                    proj_root / "remotion" / "public" / "media" / bgm_track_name,
                ]
                for cb in candidates_bgm:
                    if cb.exists():
                        local_bgm_path = cb
                        break

            # 3. Yerel RVC Ses Klonu & Filigran Giydirme (Apple Silicon M4)
            clone_applied = False
            clone_info = {}
            try:
                from settings_manager import SettingsManager
                settings = SettingsManager().get_all()
                auto_clone = settings.get("auto_apply_voice_clone_on_download", True)
            except Exception:
                auto_clone = True

            if auto_clone:
                try:
                    from voice_clone_manager import VoiceCloneManager
                    channel_voice_clone = (
                        ch_cfg.get("voice_clone_id")
                        or ch_cfg.get("edit_options", {}).get("voice_clone_id")
                    ) if ch_cfg else None
                    print(f"[RemoteRunner] 🎙️ Yerel RVC ses modeli ({channel_voice_clone or 'aktif/varsayılan'}) ve temiz fon müziği giydiriliyor: {dest_video.name}...")
                    clone_res = VoiceCloneManager().apply_voice_clone_to_video(
                        dest_video,
                        clone_id=channel_voice_clone,
                        bgm_path=local_bgm_path,
                        bgm_volume=bgm_volume
                    )
                    if clone_res.get("success"):
                        clone_applied = True
                        clone_info = clone_res
                        print(f"[RemoteRunner] ✅ RVC ses ve fon müziği giydirme tamamlandı: {clone_res.get('clone_name')} ({clone_res.get('processing_time_sec')} sn)")
                    else:
                        print(f"[RemoteRunner] ℹ️ RVC giydirme atlandı/başarısız ({clone_res.get('reason')}). Orijinal ses korunuyor.")
                        if local_bgm_path:
                            self._mix_bgm_into_video(dest_video, local_bgm_path, bgm_volume)
                except Exception as vc_err:
                    print(f"[RemoteRunner] ⚠️ RVC ses giydirme hatası (orijinal ses korunuyor): {vc_err}")
                    if local_bgm_path:
                        self._mix_bgm_into_video(dest_video, local_bgm_path, bgm_volume)
            else:
                if local_bgm_path:
                    self._mix_bgm_into_video(dest_video, local_bgm_path, bgm_volume)

            # video.mp4 kopyası oluştur (YouTube Studio uploader uyumluluğu)
            shutil.copy2(str(dest_video), str(target_dir / "video.mp4"))

            # Eğer klon ses giydirildiyse metadata'yı güncelle
            if clone_applied:
                meta_path = target_dir / "metadata.json"
                try:
                    meta_data = {}
                    if meta_path.exists():
                        meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
                    meta_data["voice_clone_applied"] = True
                    meta_data["voice_clone_id"] = clone_info.get("clone_id")
                    meta_data["voice_clone_name"] = clone_info.get("clone_name")
                    meta_data["watermarked"] = clone_info.get("watermarked", True)
                    meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as meta_e:
                    print(f"[RemoteRunner] Metadata klon ses güncelleme uyarısı: {meta_e}")

            # 2.8. Otonom Yerel AI ile Viral Başlık, Açıklama ve Etiket Üretimi (Ayar/Aktifleştirme gerektirmez)
            try:
                from ai_metadata_generator import auto_generate_and_apply_metadata
                print(f"[RemoteRunner] 🤖 Yerel AI ile video SEO, başlık, açıklama ve etiketleri optimize ediliyor: {dest_video.name}...")
                auto_generate_and_apply_metadata(target_dir, channel_id=channel_id)
            except Exception as meta_ai_err:
                print(f"[RemoteRunner] ⚠️ Otomatik AI metadata üretimi uyarısı: {meta_ai_err}")

            # 3. Sunucudan videoyu kaldır & materyalleri 24 saat sakla (1 Gün Kuralı)
            remote_cleaned = False
            if delete_remote:
                cleanup_cmd = f"""python3 -c "
    import os, time, glob, shutil
    job_dir = '{remote_job_dir}'
    now = time.time()
    if os.path.exists(job_dir):
        # Ağır bitmiş video dosyalarını temizle (sunucu video listesinden anında düşsün)
        for f in ['final_video.mp4', 'final.mp4', 'visual_track.mp4']:
            fp = os.path.join(job_dir, f)
            if os.path.exists(fp):
                try: os.remove(fp)
                except Exception: pass
        # 24 saat saklama başlangıç zaman damgası bırak
        ts_file = os.path.join(job_dir, 'downloaded_at.timestamp')
        with open(ts_file, 'w') as f:
            f.write(str(now))

    # 24 saati (86400 saniye) geçmiş olan materyal klasörlerini tamamen süpür
    base_out = '{self.remote_dir}/output'
    for ts_path in glob.glob(os.path.join(base_out, '*', '*', 'downloaded_at.timestamp')):
        try:
            with open(ts_path) as tf:
                dl_time = float(tf.read().strip())
            if now - dl_time > 86400:
                d_to_remove = os.path.dirname(ts_path)
                shutil.rmtree(d_to_remove, ignore_errors=True)
                j_name = os.path.basename(d_to_remove)
                for jf in glob.glob(f'{self.remote_dir}/jobs/{{j_name}}*'):
                    try: os.remove(jf)
                    except Exception: pass
                for lf in glob.glob(f'{self.remote_dir}/logs/{{j_name}}*'):
                    try: os.remove(lf)
                    except Exception: pass
        except Exception:
            pass
    " """
                rc, _, _ = self._run_ssh_cmd(cleanup_cmd, timeout=15)
                remote_cleaned = (rc == 0)
                print(f"[RemoteRunner] 🧹 Video sunucu listesinden düşürüldü, materyaller 24 saat saklanacak: {channel_id}/{job_id}")

            return {
                "success": True,
                "channel_id": channel_id,
                "job_id": job_id,
                "local_dir": str(target_dir),
                "video_path": str(dest_video),
                "size_mb": round(dest_video.stat().st_size / (1024 * 1024), 2),
                "remote_cleaned": remote_cleaned,
                "voice_clone_applied": clone_applied,
                "voice_clone_info": clone_info
            }
        except Exception as e:
            # HATA DURUMUNDA: Asla diskte boş veya bozuk klasör bırakma!
            if target_dir.exists():
                try:
                    shutil.rmtree(str(target_dir), ignore_errors=True)
                    print(f"[RemoteRunner] 🧹 Başarısız indirme sonrası boş klasör silindi: {target_dir.name}")
                except Exception:
                    pass
            raise e

    def download_all_pending_for_channel(self, channel_id: str) -> list[Dict[str, Any]]:
        """Kanal için sunucudaki tüm hazır videoları indirir ve sunucudan siler."""
        videos = self.list_server_videos(channel_id)
        downloaded = []
        for v in videos:
            jid = v.get("job_id")
            if not jid:
                continue
            if self.is_job_downloaded_locally(channel_id, jid):
                print(f"[RemoteRunner] ℹ️ '{jid}' ({channel_id}) yerelde zaten mevcut, mükerrer indirme atlandı.")
                self.delete_remote_job(jid, channel_id)
                continue
            try:
                res = self.download_and_cleanup_job(channel_id, jid, delete_remote=True)
                downloaded.append(res)
            except Exception as e:
                print(f"[RemoteRunner] İndirme hatası ({jid}): {e}")
        return downloaded

    def download_all_pending(self, channel_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """Sunucudaki hazır videoları indirir ve sunucudan siler."""
        videos = self.list_server_videos(channel_id)
        downloaded = []
        for v in videos:
            ch = v.get("channel_id")
            jid = v.get("job_id")
            if not ch or not jid:
                continue
            if self.is_job_downloaded_locally(ch, jid):
                print(f"[RemoteRunner] ℹ️ '{jid}' ({ch}) yerelde zaten mevcut, mükerrer indirme atlandı.")
                self.delete_remote_job(jid, ch)
                continue
            try:
                res = self.download_and_cleanup_job(ch, jid, delete_remote=True)
                downloaded.append(res)
            except Exception as e:
                print(f"[RemoteRunner] İndirme hatası ({ch}/{jid}): {e}")
        return downloaded

    def _mix_bgm_into_video(self, video_path: Path, bgm_path: Path, bgm_volume: float = 0.06) -> bool:
        """Kuru sesli videoya belirtilen fon müziğini -c:v copy ile dengeli miksler."""
        try:
            effective_bgm_vol = min(float(bgm_volume), 0.06) if float(bgm_volume) > 0.06 else float(bgm_volume)
            temp_out = video_path.parent / f"bgm_{video_path.name}"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-stream_loop", "-1", "-i", str(bgm_path),
                "-filter_complex", (
                    f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[vocal_norm];"
                    f"[1:a]volume={effective_bgm_vol}[bgm];"
                    f"[vocal_norm][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
                ),
                "-c:v", "copy",
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(temp_out)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            if temp_out.exists() and temp_out.stat().st_size > 1000:
                shutil.move(str(temp_out), str(video_path))
                print(f"[RemoteRunner] 🎵 Fon müziği başarıyla mikslendi: {bgm_path.name}")
                return True
        except Exception as e_mix:
            print(f"[RemoteRunner] ⚠️ Fon müziği miksleme uyarısı: {e_mix}")
        return False
