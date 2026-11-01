import os
import sys
import torch
import torchaudio as ta

# Ensure chatterbox is on the path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "chatterbox", "src"))

try:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
except ImportError:
    # Fallback to local import if needed
    try:
        from chatterbox.src.chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except ImportError:
        ChatterboxMultilingualTTS = None


class ChatterboxAudioGenerator:
    """Resemble AI Chatterbox Multilingual TTS modelini kullanarak yerel ses sentezler."""
    
    _model = None
    
    @classmethod
    def get_model(cls):
        if cls._model is None:
            if ChatterboxMultilingualTTS is None:
                raise ImportError("Chatterbox kütüphanesi yüklenemedi. Lütfen 'chatterbox' bağımlılıklarını kontrol edin.")
            
            # Cihaz tespiti (macOS MPS, CUDA GPU, veya CPU)
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
                
            print(f"[CHATTERBOX] Model yükleniyor (Cihaz: {device})...")
            
            # Mac MPS için torch.load yaması
            if device == "mps":
                map_location = torch.device(device)
                torch_load_original = torch.load
                def patched_torch_load(*args, **kwargs):
                    if 'map_location' not in kwargs:
                        kwargs['map_location'] = map_location
                    return torch_load_original(*args, **kwargs)
                torch.load = patched_torch_load

            cls._model = ChatterboxMultilingualTTS.from_pretrained(device=device)
            print("[CHATTERBOX] Model başarıyla yüklendi.")
            
        return cls._model

    def generate(
        self,
        text: str,
        lang: str,
        output_path: str,
        audio_prompt_path: str = None,
        exaggeration: float = 0.5,
        scenes: list = None,
        character_name: str = None,
        require_audio_prompt: bool = False,
    ) -> tuple[bool, list[dict]]:
        """
        Yerel Chatterbox modelini kullanarak ses üretir ve kaydeder.
        Sahneler veya cümleler halinde parçalara bölerek sentezler ve sessizlik ekleyerek birleştirir.
        """
        try:
            model = self.get_model()
            
            # Dil eşlemesi: Sadece küçük harfli ISO2 kodları
            lang_id = lang.lower().strip()
            # Eğer dil desteklenmiyorsa varsayılan 'en'
            from chatterbox.mtl_tts import SUPPORTED_LANGUAGES
            if lang_id not in SUPPORTED_LANGUAGES:
                print(f"[CHATTERBOX] Uyarı: '{lang_id}' dili desteklenmiyor. Varsayılan 'en' kullanılacak.")
                lang_id = "en"

            # Casper AI: Karakter RAG ile TTS Ses ve Ton Eşleme
            if character_name:
                try:
                    from character_rag import CharacterRAGManager
                    c_voice = CharacterRAGManager.get_voice_for_character(character_name)
                    if c_voice.get("voice_id") and os.path.exists(str(c_voice["voice_id"])):
                        audio_prompt_path = str(c_voice["voice_id"])
                    p_set = c_voice.get("pitch_settings") or {}
                    if isinstance(p_set, dict) and p_set.get("exaggeration"):
                        exaggeration = float(p_set["exaggeration"])
                    print(f"[CHATTERBOX] 🎙️ Karakter RAG ses profili devrede: '{character_name}' (Ses: {c_voice.get('voice_id')})")
                except Exception as rag_err:
                    print(f"[CHATTERBOX] RAG ses eşleme uyarısı: {rag_err}")

            # Varsayılan Türkçe ses için projenin özgün hibrit referans sesi
            if not audio_prompt_path and lang_id == "tr":
                for c in [
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "voice_clones", "vc_ttsmaker_enes_hybrid", "voice.wav")),
                    "/home/ubuntu/yt-render-server/assets/whatsapp/assets/voice_samples/hybrid_male.wav",
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "assets", "whatsapp", "assets", "voice_samples", "hybrid_male.wav")),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "whatsapp", "assets", "voice_samples", "hybrid_male.wav")),
                    "config/assets/whatsapp/assets/voice_samples/hybrid_male.wav"
                ]:
                    if os.path.exists(c):
                        audio_prompt_path = c
                        break
                
            import numpy as np
            import re
            
            # Duygu durumunu tahmin eden kelime analizi fonksiyonu
            # Casper AI: Mikro-Duygu ve Prosodi Analizi (Kahkaha, Fısıltı, Nefes)
            def analyze_emotion(seg_txt: str) -> str:
                t_low = seg_txt.lower()
                # Kahkaha / Neşe
                laugh = ["haha", "ahah", "hehe", "hihi", "kıkır", "sjsj", "lol", "lmao", "😂", "🤣"]
                # İç çekme / Nefes / Ünlem
                sigh = ["uff", "pff", "oof", "aman", "of", "ah", "eyvah", "vah", "yuh", "çüş", "yeter"]
                # Fısıltı / Gizemli
                whisper = ["şşş", "fısır", "sessizce", "gizlice", "psst", "çaktırma"]
                # Heyecan / Coşku
                excited = ["heyecan", "inanılmaz", "mükemmel", "harika", "süper", "şok", "büyük", "patlama", "hızlı",
                           "incredible", "amazing", "exciting", "shocking", "explosion", "awesome", "unbelievable", "huge", "furious"]
                # Dram / Gizem / Gerilim
                dramatic = ["gizem", "karanlık", "tehlike", "korku", "ölüm", "sır", "dehşet", "derin", "tuzak",
                            "mystery", "dark", "danger", "fear", "death", "secret", "horror", "deep", "hidden", "dramatic"]
                # Hüzün / Melankoli
                sad = ["üzgün", "yalnız", "kayıp", "sessiz", "son", "hoşçakal", "ağla", "hüzün",
                       "sad", "lonely", "lost", "silent", "final", "goodbye", "cry", "grief", "melancholy"]
                # Mutluluk / Pozitiflik
                happy = ["mutlu", "gül", "neşeli", "keyif", "sevinç", "başarı", "zafer",
                         "happy", "smile", "joy", "success", "victory", "celebrate", "glad"]
                
                for kw in laugh:
                    if kw in t_low: return "laugh"
                for kw in sigh:
                    if kw in t_low: return "sigh"
                for kw in whisper:
                    if kw in t_low: return "whisper"
                for kw in excited:
                    if kw in t_low: return "excited"
                for kw in dramatic:
                    if kw in t_low: return "dramatic"
                for kw in sad:
                    if kw in t_low: return "sad"
                for kw in happy:
                    if kw in t_low: return "happy"
                return "neutral"

            # Duygu durumuna göre ultra-stabil sentez parametreleri
            # Sıcaklık ve exaggeration difüzyon modellerinde kekelemeye yol açmamalıdır.
            def get_emotion_params(emo: str) -> tuple[float, float, float, float]:
                e = emo.lower().strip()
                # Döndürülen: (exaggeration, temperature, cfg_weight, repetition_penalty)
                if e == "laugh":
                    return 0.42, 0.49, 0.74, 1.34  # Coşkulu kahkaha tonlaması
                elif e == "sigh":
                    return 0.32, 0.38, 0.70, 1.30  # Nefesli iç çekme tonlaması
                elif e == "whisper":
                    return 0.22, 0.30, 0.84, 1.38  # Yumuşak fısıltı ve yüksek berraklık
                elif e == "excited":
                    return 0.38, 0.48, 0.72, 1.35
                elif e in ("dramatic", "mysterious", "shocked"):
                    return 0.35, 0.45, 0.70, 1.35
                elif e == "sad":
                    return 0.32, 0.42, 0.68, 1.30
                elif e == "happy":
                    return 0.36, 0.46, 0.72, 1.32
                # neutral / varsayılan
                return 0.34, 0.44, 0.70, 1.30

            def clean_tts_text(raw: str) -> str:
                if not raw:
                    return ""
                # Emojileri ve garip unicode işaretlerini temizle
                cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', raw)
                # Reddit etiketlerini Türkçeleştir / sadeleştir
                cleaned = re.sub(r'\br/[A-Za-z0-9_]+\b', 'Reddit', cleaned)
                cleaned = re.sub(r'\bu/[A-Za-z0-9_]+\b', 'kullanıcı', cleaned)
                cleaned = re.sub(r'\bAITAH?\b', 'ben mi hatalıyım', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\bTIFU\b', 'büyük bir hata yaptım', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\bOP\b', 'yazar', cleaned)
                cleaned = re.sub(r'\bTL;?DR\b', 'özetle', cleaned, flags=re.IGNORECASE)
                # Türkçe metin normalizasyonu (sayılar: 2026 -> iki bin yirmi altı, saatler, kısaltmalar)
                if lang_id == "tr":
                    try:
                        from text_normalizer import normalize_turkish_tts_text
                    except ImportError:
                        from src.text_normalizer import normalize_turkish_tts_text
                    cleaned = normalize_turkish_tts_text(cleaned)
                # Üç nokta ve benzerlerini tek noktaya indir (kekelemeyi engeller)
                cleaned = re.sub(r'\.{2,}', '.', cleaned)
                cleaned = re.sub(r'\?{2,}', '?', cleaned)
                cleaned = re.sub(r'\!{2,}', '!', cleaned)
                cleaned = re.sub(r'\?\!|\!\?', '?', cleaned)
                # Markdown, tırnak, parantez ve çizgi karakterlerini temizle
                cleaned = re.sub(r'[\*#_~`"“”‘’«»\'\[\]\(\)\{\}\<\>\\]', '', cleaned)
                # Kelime arasındaki kısa çizgileri boşluğa çevir (Örn: forty-eight -> forty eight, triple-doubles -> triple doubles)
                cleaned = re.sub(r'(\b\w+)\s*[-]\s*(\w+\b)', r'\1 \2', cleaned)
                # Cümleler arası uzun tire veya em-dash'leri virgüle çevir
                cleaned = re.sub(r'\s*[\—–]\s*', ', ', cleaned)
                cleaned = re.sub(r'\s+[-]\s+', ', ', cleaned)
                # Fazla boşlukları düzelt
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                return cleaned

            def split_into_tts_chunks(raw_text: str, max_words: int = 16) -> list[str]:
                text_clean = clean_tts_text(raw_text)
                if not text_clean:
                    return []
                
                # 1. Cümle bitişlerinden böl (. ! ?)
                raw_sents = re.split(r'(?<=[.!?])\s+', text_clean)
                chunks = []
                
                for sent in raw_sents:
                    sent = sent.strip()
                    if not sent:
                        continue
                    words = sent.split()
                    if len(words) <= max_words:
                        chunks.append(sent)
                        continue
                    
                    # Cümle uzun (> max_words), yan cümle / virgül / bağlaçlardan böl
                    sub_clauses = re.split(r'(?<=[,;:])\s+', sent)
                    curr_chunk = []
                    curr_wc = 0
                    
                    for sc in sub_clauses:
                        sc = sc.strip()
                        if not sc:
                            continue
                        sc_words = sc.split()
                        if curr_wc + len(sc_words) <= max_words:
                            curr_chunk.append(sc)
                            curr_wc += len(sc_words)
                        else:
                            if curr_chunk:
                                chunks.append(" ".join(curr_chunk))
                                curr_chunk = []
                                curr_wc = 0
                            
                            # Eğer tek bir yan cümle bile max_words'ten büyükse bağlaçlardan böl
                            if len(sc_words) > max_words:
                                conj_pattern = r'\b(and|but|that|which|because|while|although|to|ve|ama|fakat|çünkü|ancak|oysa|halbuki|lakin|ki)\b'
                                parts = re.split(conj_pattern, sc, flags=re.IGNORECASE)
                                sub_buf = []
                                sub_wc = 0
                                for p in parts:
                                    p = p.strip()
                                    if not p:
                                        continue
                                    p_words = p.split()
                                    if sub_wc + len(p_words) <= max_words:
                                        sub_buf.append(p)
                                        sub_wc += len(p_words)
                                    else:
                                        if sub_buf:
                                            chunks.append(" ".join(sub_buf))
                                            sub_buf = []
                                            sub_wc = 0
                                        if len(p_words) > max_words:
                                            for k in range(0, len(p_words), max_words):
                                                chunk_slice = " ".join(p_words[k:k+max_words])
                                                if chunk_slice:
                                                    chunks.append(chunk_slice)
                                        else:
                                            sub_buf.append(p)
                                            sub_wc = len(p_words)
                                if sub_buf:
                                    chunks.append(" ".join(sub_buf))
                            else:
                                curr_chunk.append(sc)
                                curr_wc = len(sc_words)
                                
                    if curr_chunk:
                        chunks.append(" ".join(curr_chunk))
                        
                return [c.strip() for c in chunks if c.strip()]

            segments = []
            if scenes:
                for s_idx, s in enumerate(scenes):
                    narr_text = s.get("narration", "")
                    chunks = split_into_tts_chunks(narr_text, max_words=13)
                    emo = s.get("emotion", "").strip()
                    for c in chunks:
                        segments.append({
                            "text": c,
                            "emotion": emo,
                            "scene_idx": s_idx
                        })
            
            if not segments:
                chunks = split_into_tts_chunks(text.strip(), max_words=13)
                for c in chunks:
                    segments.append({
                        "text": c,
                        "emotion": "",
                        "scene_idx": 0
                    })
                
            if not segments:
                segments = [{
                    "text": clean_tts_text(text),
                    "emotion": "",
                    "scene_idx": 0
                }]
                
            print(f"[CHATTERBOX] Ses segmentler halinde üretiliyor. Toplam segment sayısı: {len(segments)}")
            
            boundaries = []
            scene_wavs = []
            current_offset = 0.0
            
            for idx, seg in enumerate(segments):
                seg_text = seg["text"]
                emotion_tag = seg.get("emotion", "")
                scene_idx = seg.get("scene_idx", 0)
                
                # Eğer duygu belirtilmemişse metinden otomatik analiz et
                if not emotion_tag:
                    emotion_tag = analyze_emotion(seg_text)
                    
                exg, tmp, cfg, rep_pen = get_emotion_params(emotion_tag)
                
                print(f"[CHATTERBOX] Segment {idx+1}/{len(segments)} (Sahne {scene_idx}) sentezleniyor: '{seg_text[:35]}...' | Duygu: {emotion_tag} (Exg: {exg}, Tmp: {tmp}, CFG: {cfg}, RepPen: {rep_pen})")
                
                try:
                    wav = model.generate(
                        text=seg_text,
                        language_id=lang_id,
                        audio_prompt_path=audio_prompt_path if audio_prompt_path and os.path.exists(audio_prompt_path) else None,
                        exaggeration=exg,
                        temperature=tmp,
                        cfg_weight=cfg,
                        repetition_penalty=rep_pen
                    )
                    wav_np = wav.squeeze(0).cpu().numpy()
                except Exception as gen_err:
                    if require_audio_prompt and audio_prompt_path:
                        raise RuntimeError("Seçilen klon ses sentez sırasında uygulanamadı.") from gen_err
                    print(f"[CHATTERBOX] Segment üretim hatası: {gen_err}, güvenli fallback deneniyor...")
                    wav = model.generate(
                        text=seg_text,
                        language_id=lang_id,
                        audio_prompt_path=None,
                        exaggeration=0.30,
                        temperature=0.35,
                        cfg_weight=0.80,
                        repetition_penalty=1.40
                    )
                    wav_np = wav.squeeze(0).cpu().numpy()
                
                # Baş ve sondaki aşırı boşlukları kırp
                abs_wav = np.abs(wav_np)
                thresh = 0.005
                above_thresh = np.where(abs_wav > thresh)[0]
                if len(above_thresh) > 0:
                    start_idx = max(0, above_thresh[0] - int(model.sr * 0.02))
                    end_idx = min(len(wav_np), above_thresh[-1] + int(model.sr * 0.03))
                    wav_np = wav_np[start_idx:end_idx]
                
                dur = len(wav_np) / model.sr
                seg_words_count = max(len(seg_text.split()), 1)
                word_rate = dur / seg_words_count
                
                # ANOMALİ / SAÇMALAMA KONTROLÜ:
                # Normal konuşma 0.25 - 0.55 sn/kelimedir. Eğer >1.05 sn/kelime ise model takılmış/saçmalamıştır.
                if (word_rate > 1.05 and dur > 2.8) or dur < 0.15:
                    print(f"[CHATTERBOX] Uyarı: Segmentte kekeleme/anomali tespit edildi ({dur:.2f}s, {seg_words_count} kelime, {word_rate:.2f}s/kelime). Ultra-güvenli modda düzeltiliyor...")
                    try:
                        wav_retry = model.generate(
                            text=seg_text,
                            language_id=lang_id,
                            audio_prompt_path=audio_prompt_path if audio_prompt_path and os.path.exists(audio_prompt_path) else None,
                            exaggeration=0.28,
                            temperature=0.32,
                            cfg_weight=0.82,
                            repetition_penalty=1.45
                        )
                        wav_np_retry = wav_retry.squeeze(0).cpu().numpy()
                        abs_w = np.abs(wav_np_retry)
                        ab = np.where(abs_w > 0.005)[0]
                        if len(ab) > 0:
                            s_i = max(0, ab[0] - int(model.sr * 0.02))
                            e_i = min(len(wav_np_retry), ab[-1] + int(model.sr * 0.03))
                            wav_np_retry = wav_np_retry[s_i:e_i]
                        dur_retry = len(wav_np_retry) / model.sr
                        if (dur_retry / seg_words_count) < word_rate:
                            wav_np = wav_np_retry
                            dur = dur_retry
                            print(f"[CHATTERBOX] Düzeltme başarılı: Yeni süre {dur:.2f}s")
                    except Exception as ret_err:
                        print(f"[CHATTERBOX] Düzeltme yeniden deneme hatası: {ret_err}")

                # Casper AI: Mikro-Duygu ve Noktalamaya Göre Inter-Speech Pause Ölçeklendirme
                is_last_in_total = (idx == len(segments) - 1)
                is_last_in_scene = is_last_in_total or (idx < len(segments) - 1 and segments[idx + 1].get("scene_idx") != scene_idx)
                base_pause = 0.40 if is_last_in_total else (0.12 if is_last_in_scene else 0.06)

                seg_raw = seg_text.strip()
                if is_last_in_total:
                    pause_duration = 0.40
                elif emotion_tag == "sigh" or any(w in seg_raw.lower() for w in ["uff", "aman", "of", "oof", "pff"]):
                    pause_duration = max(base_pause, 0.22)  # Nefes / iç çekme boşluğu
                elif emotion_tag == "laugh" or any(w in seg_raw.lower() for w in ["haha", "hehe", "sjsj", "lol"]):
                    pause_duration = max(base_pause, 0.18)  # Kahkaha sonrası duraksama
                elif seg_raw.endswith("?") or seg_raw.endswith("?!"):
                    pause_duration = max(base_pause, 0.18)  # Soru ve merak duraklaması
                elif seg_raw.endswith("!"):
                    pause_duration = max(base_pause, 0.16)  # Ünlem vurgusu
                elif seg_raw.endswith("..."):
                    pause_duration = max(base_pause, 0.25)  # Dramatik duraksama
                elif seg_raw.endswith(",") or seg_raw.endswith(";"):
                    pause_duration = max(base_pause, 0.10)  # Yan cümle nefes payı
                else:
                    pause_duration = base_pause
                
                # Her segmentin süresi duraklamayı da içermelidir; böylece video ve altyazı süresi
                # ses dosyası uzunluğuyla tamı tamına eşleşir ve son cümle asla kesilmez!
                boundaries.append({
                    "text": seg_text,
                    "offset": current_offset,
                    "duration": dur + pause_duration,
                    "scene_idx": scene_idx,
                    "pause_duration": pause_duration
                })
                scene_wavs.append(wav_np)
                current_offset += dur + pause_duration
                
            if not scene_wavs:
                print("[CHATTERBOX] Hata: Sentezlenecek segment bulunamadı.")
                return False, []
                
            combined_wavs = []
            for i, wav_np in enumerate(scene_wavs):
                combined_wavs.append(wav_np)
                pause_s = boundaries[i].get("pause_duration", 0.06)
                silence_samples = int(model.sr * pause_s)
                silence = np.zeros(silence_samples, dtype=np.float32)
                combined_wavs.append(silence)
                    
            final_wav = np.concatenate(combined_wavs)
            
            if output_path.endswith(".mp3"):
                output_path = output_path.replace(".mp3", ".wav")
                
            import soundfile as sf
            sf.write(output_path, final_wav, model.sr)
            print(f"[CHATTERBOX] Ses dosyası kaydedildi → {output_path} | Toplam Süre: {len(final_wav)/model.sr:.2f}s | Segment Sayısı: {len(segments)}")
            return True, boundaries
            
        except Exception as e:
            print(f"[CHATTERBOX] Hata: {e}")
            import traceback
            traceback.print_exc()
            if require_audio_prompt and audio_prompt_path:
                raise RuntimeError("Seçilen klon sesle sentez başarısız oldu.") from e
            return False, []
