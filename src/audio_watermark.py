"""
Ultrasonic Inaudible Audio Watermark & Forensic Copyright Protection Module.
Developed for Ali Enes Automated Video Production Pipeline.

Features:
- Ultrasonic Frequency Shift Keying (FSK) in the 18.2 kHz - 18.6 kHz band.
- Standardized at 44.1 kHz sampling rate for 100% stability across Applio RVC, Edge-TTS, and Remotion.
- Inaudible to adult humans (>18 kHz, -50 dBFS).
- Highly resilient to MP3 (192-320 kbps) and AAC (YouTube standard).
- Frame-synchronized preamble correlation (locks in even if audio was trimmed or sliced).
- Verifier accepts WAV, MP3, AAC, M4A, and MP4/MKV video files directly.
"""

import os
import sys
import argparse
import subprocess
import tempfile
import numpy as np
import scipy.io.wavfile as wavfile
from pathlib import Path
from typing import Optional, Dict, Any


class AudioWatermarker:
    TARGET_SR = 44100
    
    # 16-bit sync preamble (Barker-like sequence for high auto-correlation peak)
    PREAMBLE = [1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0]
    DEFAULT_SIGNATURE = "ALIENES!"
    
    # Ultrasonic carrier frequencies (inaudible to adult humans, safe below 22.05 kHz Nyquist)
    F0 = 18200      # Bit 0 frequency (Hz)
    F1 = 18600      # Bit 1 frequency (Hz)
    PILOT_F = 18400 # Continuous pilot lock tone (Hz)
    
    BIT_DURATION = 0.045  # 45 ms per bit
    AMPLITUDE = 0.0035    # ~ -49.5 dBFS (inaudible, imperceptible energy)

    @classmethod
    def _text_to_bits(cls, text: str) -> list[int]:
        bits = []
        for char in text.encode("utf-8"):
            for b in f"{char:08b}":
                bits.append(int(b))
        return bits

    @classmethod
    def _bits_to_text(cls, bits: list[int]) -> str:
        chars = []
        for i in range(0, len(bits) - 7, 8):
            byte_bits = bits[i:i+8]
            val = int("".join(str(b) for b in byte_bits), 2)
            if 32 <= val <= 126:
                chars.append(chr(val))
            else:
                chars.append("?")
        return "".join(chars)

    @classmethod
    def embed(
        cls,
        input_file: str,
        output_file: Optional[str] = None,
        signature: Optional[str] = None,
        gain: Optional[float] = None
    ) -> bool:
        """
        Embeds an inaudible ultrasonic watermark into audio_file (WAV, MP3, etc.).
        Standardizes to 44.1 kHz. Overwrites input_file safely if output_file is None.
        """
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"[WATERMARK] Hata: Dosya bulunamadı -> {input_file}")
            return False

        sig = (signature or cls.DEFAULT_SIGNATURE)[:12]
        amp = gain if gain is not None else cls.AMPLITUDE
        target_out = Path(output_file) if output_file else input_path
        target_ext = target_out.suffix.lower() if target_out.suffix else ".wav"

        # Temporary files for conversion
        fd1, raw_wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd1)
        raw_wav = Path(raw_wav_path)

        try:
            # Step 1: Normalize input to 44.1 kHz WAV using ffmpeg
            cmd = ["ffmpeg", "-y", "-i", str(input_path), "-ar", str(cls.TARGET_SR), "-ac", "1", str(raw_wav)]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            sr, audio_data = wavfile.read(str(raw_wav))
            if audio_data.dtype == np.int16:
                samples = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                samples = audio_data.astype(np.float32) / 2147483648.0
            else:
                samples = audio_data.astype(np.float32)

            total_samples = len(samples)
            if total_samples < sr:
                print(f"[WATERMARK] Uyarı: Ses dosyası çok kısa ({total_samples/sr:.2f}s).")

            # Step 2: Build FSK bitstream
            sig_bits = cls._text_to_bits(sig)
            packet = cls.PREAMBLE + sig_bits
            samples_per_bit = int(sr * cls.BIT_DURATION)

            full_bits = []
            while len(full_bits) * samples_per_bit < total_samples:
                full_bits.extend(packet)
            full_bits = full_bits[: max(1, total_samples // samples_per_bit)]

            # Generate FSK watermark
            watermark = np.zeros(total_samples, dtype=np.float32)
            phase = 0.0
            for i, bit in enumerate(full_bits):
                start = i * samples_per_bit
                end = min(start + samples_per_bit, total_samples)
                dur = end - start
                if dur <= 0: break
                f = cls.F1 if bit == 1 else cls.F0
                t = np.arange(dur) / sr
                watermark[start:end] = amp * np.sin(2 * np.pi * f * t + phase)
                phase = (phase + 2 * np.pi * f * (dur / sr)) % (2 * np.pi)

            # Add subtle pilot lock carrier at 18.4 kHz (-55 dBFS)
            t_full = np.arange(total_samples) / sr
            watermark += (amp * 0.4) * np.sin(2 * np.pi * cls.PILOT_F * t_full)

            # Mix & Clip
            watermarked = np.clip(samples + watermark, -1.0, 1.0)
            out_int16 = (watermarked * 32767.0).astype(np.int16)

            # Step 3: Write out
            fd2, tmp_target_path = tempfile.mkstemp(suffix=target_ext)
            os.close(fd2)
            tmp_target = Path(tmp_target_path)

            if target_ext == ".wav":
                wavfile.write(str(tmp_target), sr, out_int16)
            else:
                # Intermediary wav to compressed format with metadata
                int_w = tmp_target_path + ".int.wav"
                wavfile.write(int_w, sr, out_int16)
                meta_args = [
                    "-metadata", "artist=Ali Enes",
                    "-metadata", "copyright=© Ali Enes - All Rights Reserved",
                    "-metadata", f"comment=Forensic Voice Signature: {sig}"
                ]
                cmd = ["ffmpeg", "-y", "-i", int_w] + meta_args + ["-b:a", "256k", str(tmp_target)]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                try: os.unlink(int_w)
                except Exception: pass

            target_out.parent.mkdir(parents=True, exist_ok=True)
            if tmp_target.exists():
                tmp_target.replace(target_out)

            print(f"[WATERMARK] 🛡️ Ultrasonik telif filigranı gömüldü: '{sig}' -> {target_out.name}")
            return True

        except Exception as e:
            print(f"[WATERMARK] Mühürleme hatası: {e}")
            return False
        finally:
            if raw_wav.exists():
                try: raw_wav.unlink()
                except Exception: pass

    @classmethod
    def verify(
        cls,
        media_file: str,
        expected_signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inspects an audio or video file (WAV, MP3, AAC, MP4, MKV) and verifies
        whether Ali Enes's inaudible ultrasonic watermark is present.
        """
        media_path = Path(media_file)
        if not media_path.exists():
            return {"verified": False, "error": f"Dosya bulunamadı: {media_file}"}

        sr = cls.TARGET_SR
        cmd = [
            "ffmpeg", "-y", "-i", str(media_path),
            "-vn", "-ar", str(sr), "-ac", "1",
            "-f", "s16le", "pipe:1"
        ]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
            raw_bytes = proc.stdout
            if not raw_bytes:
                return {"verified": False, "error": "Ses verisi okunamadı."}
            samples_int = np.frombuffer(raw_bytes, dtype=np.int16)
            audio = samples_int.astype(np.float32) / 32768.0
        except Exception as proc_err:
            return {"verified": False, "error": f"FFmpeg çıkarma hatası: {proc_err}"}

        duration = len(audio) / sr
        if duration < 0.5:
            return {"verified": False, "error": "Ses süresi çok kısa (< 0.5 saniye)."}

        expected_sig = (expected_signature or cls.DEFAULT_SIGNATURE).strip()
        samples_per_bit = int(sr * cls.BIT_DURATION)
        step = max(samples_per_bit // 4, 1)

        t_step = np.arange(samples_per_bit) / sr
        sin0, cos0 = np.sin(2 * np.pi * cls.F0 * t_step), np.cos(2 * np.pi * cls.F0 * t_step)
        sin1, cos1 = np.sin(2 * np.pi * cls.F1 * t_step), np.cos(2 * np.pi * cls.F1 * t_step)

        num_steps = (len(audio) - samples_per_bit) // step
        if num_steps <= 0:
            return {"verified": False, "error": "Yetersiz örnek sayısı."}

        metric = []
        for s in range(num_steps):
            idx = s * step
            chunk = audio[idx : idx + samples_per_bit]
            e0 = (np.sum(chunk * sin0)**2 + np.sum(chunk * cos0)**2)
            e1 = (np.sum(chunk * sin1)**2 + np.sum(chunk * cos1)**2)
            metric.append(e1 - e0)
        metric = np.array(metric)

        preamble_pattern = []
        for p in cls.PREAMBLE:
            preamble_pattern.extend([1.0 if p == 1 else -1.0] * 4)

        corr = np.correlate(metric, preamble_pattern, mode="valid")
        if len(corr) == 0:
            return {"verified": False, "error": "Korelasyon hesaplanamadı."}

        sig_bits = cls._text_to_bits(expected_sig)
        total_packet_bits = len(cls.PREAMBLE) + len(sig_bits)
        total_packet_samples = total_packet_bits * samples_per_bit

        # Find local peaks within valid bounds
        valid_steps = [s for s in range(len(corr)) if (s * step + total_packet_samples) <= len(audio)]
        threshold = max(50.0, np.std(metric) * len(cls.PREAMBLE) * 0.15)
        
        peaks = []
        for s in valid_steps:
            left_ok = (s == 0) or (corr[s] >= corr[s-1])
            right_ok = (s == len(corr) - 1) or (corr[s] >= corr[s+1])
            if left_ok and right_ok and corr[s] > threshold:
                peaks.append((s, float(corr[s])))

        peaks.sort(key=lambda x: x[1], reverse=True)

        matched_results = []
        for peak_step, peak_val in peaks[:12]:
            start_sample = peak_step * step
            decoded_bits = []
            for b in range(total_packet_bits):
                b_idx = start_sample + b * samples_per_bit
                chunk = audio[b_idx : b_idx + samples_per_bit]
                e0 = (np.sum(chunk * sin0)**2 + np.sum(chunk * cos0)**2)
                e1 = (np.sum(chunk * sin1)**2 + np.sum(chunk * cos1)**2)
                decoded_bits.append(1 if e1 > e0 else 0)

            dec_preamble = decoded_bits[:len(cls.PREAMBLE)]
            preamble_score = sum(1 for a, b in zip(dec_preamble, cls.PREAMBLE) if a == b)

            if preamble_score >= 12: # At least 75% preamble match
                payload = decoded_bits[len(cls.PREAMBLE) : total_packet_bits]
                dec_str = cls._bits_to_text(payload)
                char_score = sum(1 for a, b in zip(dec_str, expected_sig) if a == b)
                matched_results.append({
                    "step": peak_step,
                    "preamble_score": preamble_score,
                    "payload_text": dec_str,
                    "char_score": char_score,
                    "peak_val": peak_val
                })

        # Carrier detection check (at pilot frequency 18.4 kHz)
        fft_chunk = audio[: min(len(audio), sr * 5)]
        fft_vals = np.abs(np.fft.rfft(fft_chunk))
        freqs = np.fft.rfftfreq(len(fft_chunk), 1 / sr)
        carrier_idx = np.argmin(np.abs(freqs - cls.PILOT_F))
        local_floor = np.median(fft_vals[max(0, carrier_idx - 100) : carrier_idx + 100]) + 1e-6
        carrier_ratio = float(fft_vals[carrier_idx] / local_floor)
        carrier_detected = carrier_ratio > 1.8

        if matched_results:
            matched_results.sort(key=lambda x: (x["char_score"], x["preamble_score"], x["peak_val"]), reverse=True)
            best = matched_results[0]
            best_match = best["payload_text"]
            confidence = (best["char_score"] / max(len(expected_sig), 1)) * 100.0
            is_valid = confidence >= 62.5 # e.g. 5 out of 8 characters
        else:
            best_match = ""
            confidence = 0.0
            is_valid = False

        return {
            "verified": is_valid,
            "signature": best_match,
            "expected_signature": expected_sig,
            "confidence_percent": round(confidence, 1),
            "carrier_detected": carrier_detected,
            "carrier_snr_ratio": round(carrier_ratio, 2),
            "verified_packets": len(matched_results),
            "duration_seconds": round(duration, 2),
            "file": str(media_path.name)
        }


def main():
    parser = argparse.ArgumentParser(description="Ali Enes Ultrasonic Audio Watermark Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Embed command
    embed_p = subparsers.add_parser("embed", help="Embed watermark into audio/video file")
    embed_p.add_argument("file", help="Path to input audio/video file")
    embed_p.add_argument("--output", "-o", default=None, help="Output path (default: overwrite in-place)")
    embed_p.add_argument("--signature", "-s", default="ALIENES!", help="Signature text (default: ALIENES!)")

    # Verify command
    verify_p = subparsers.add_parser("verify", help="Verify watermark in audio/video file")
    verify_p.add_argument("file", help="Path to audio/video file to inspect")
    verify_p.add_argument("--signature", "-s", default="ALIENES!", help="Expected signature text")

    args = parser.parse_args()

    if args.command == "embed":
        ok = AudioWatermarker.embed(args.file, output_file=args.output, signature=args.signature)
        sys.exit(0 if ok else 1)
    elif args.command == "verify":
        res = AudioWatermarker.verify(args.file, expected_signature=args.signature)
        print("=" * 60)
        print("🔍 ADLİ SES FİLİGRANI DENETİM RAPORU (FORENSIC WATERMARK REPORT)")
        print("=" * 60)
        print(f"📁 Dosya: {res.get('file')}")
        print(f"⏱️ Süre: {res.get('duration_seconds')} saniye")
        print(f"📡 18.4 kHz Ultrasonik Taşıyıcı: {'VAR (KİLİTLENDİ)' if res.get('carrier_detected') else 'YOK'} (SNR: {res.get('carrier_snr_ratio')}x)")
        print(f"🔑 Çözümlenen İmza: '{res.get('signature')}'")
        print(f"📦 Doğrulanan Paket Sayısı: {res.get('verified_packets')}")
        print(f"🎯 Güven Skoru: %{res.get('confidence_percent')}")
        print(f"📊 Durum: {'✅ RESMİ SAHİPLİK DOĞRULANDI (ALİ ENES)' if res.get('verified') else '❌ FİLİGRAN BULUNAMADI VEYA GEÇERSİZ'}")
        print("=" * 60)
        sys.exit(0 if res.get("verified") else 1)


if __name__ == "__main__":
    main()
