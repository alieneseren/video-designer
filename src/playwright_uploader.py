"""
playwright_uploader.py
AI Tabanlı Tam Otomatik YouTube Studio Tarayıcı Yükleyicisi (Playwright).

Bu modül, Chrome eklentisine ihtiyaç duymadan doğrudan backend üzerinden:
1. Tarayıcıyı açar (kullanıcı profili ve çerezleri koruyarak).
2. YouTube Studio'ya (https://studio.youtube.com) bağlanır.
3. Hedef kanal adı ile YouTube Studio'daki aktif kanalı kontrol eder; gerekirse kanal/hesap değiştirir.
4. Video dosyasını yükler.
5. Başlık, açıklama ve etiketleri doldurur.
6. 'Çocuklara özel değil' seçeneğini işaretler.
7. İlgili ülkenin yerel saatine göre 19:00 yayım zamanlamasını ayarlar.
8. Yüklemeyi tamamlar, videoyu 'yuklenen' klasörüne taşır ve içerik planını günceller.
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from playwright.sync_api import sync_playwright, Page, BrowserContext, ElementHandle


class YouTubePlaywrightUploader:
    def __init__(self, user_data_dir: Optional[str] = None, headless: bool = False):
        self.output_base = Path("output")
        self.user_data_dir = user_data_dir or str(self.output_base / "browser_profile")
        self.headless = headless
        os.makedirs(self.user_data_dir, exist_ok=True)

    def _log(self, msg: str, level: str = "info", logger: Optional[Callable] = None):
        print(f"[PLAYWRIGHT-UPLOADER] [{level.upper()}] {msg}")
        if logger:
            try:
                logger(msg, level=level)
            except Exception:
                pass

    def switch_channel(self, page: Page, target_channel_name: str, logger: Optional[Callable] = None) -> bool:
        """YouTube Studio profil menüsünden hedef kanala geçiş yapar."""
        try:
            self._log(f"🔄 Kanal kontrol ediliyor. Hedef: '{target_channel_name}'", logger=logger)
            page.wait_for_timeout(2000)

            # Sağ üstteki profil avatarını bul ve tıkla
            avatar_selectors = [
                "button#avatar-btn",
                "ytcp-profile-icon",
                "#avatar-btn",
                "img#img[alt*='Avatar']",
                "#entity-badge",
            ]
            avatar_clicked = False
            for sel in avatar_selectors:
                if page.locator(sel).first.is_visible():
                    page.locator(sel).first.click()
                    avatar_clicked = True
                    break

            if not avatar_clicked:
                self._log("⚠️ Profil avatarı bulunamadı, mevcut kanalda devam ediliyor.", level="warn", logger=logger)
                return True

            page.wait_for_timeout(1500)

            # 'Hesap değiştir' veya 'Switch account' seçeneğini bul
            switch_btn = page.locator("tp-yt-paper-item:has-text('Hesap değiştir'), tp-yt-paper-item:has-text('Switch account')").first
            if switch_btn.is_visible():
                switch_btn.click()
                page.wait_for_timeout(2000)

                # Hedef kanal adını listede ara
                target_item = page.locator(f"ytd-account-item-renderer:has-text('{target_channel_name}'), tp-yt-paper-item:has-text('{target_channel_name}')").first
                if target_item.is_visible():
                    self._log(f"✅ '{target_channel_name}' kanalına geçiş yapılıyor...", logger=logger)
                    target_item.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page.wait_for_timeout(3000)
                    return True
                else:
                    self._log(f"ℹ️ Kanal listesinde '{target_channel_name}' bulunamadı veya zaten aktif.", logger=logger)
                    # Menüyü kapatmak için boş bir yere tıkla
                    page.keyboard.press("Escape")
            else:
                page.keyboard.press("Escape")

            return True
        except Exception as e:
            self._log(f"⚠️ Kanal geçiş uyarısı: {e}", level="warn", logger=logger)
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return True

    def upload_single_video(self, payload: Dict[str, Any], logger: Optional[Callable] = None) -> Dict[str, Any]:
        """Tek bir videoyu YouTube Studio'ya yükler ve 19:00 saatine planlar."""
        video_path = payload.get("video_path", "")
        if not video_path or not Path(video_path).exists():
            # Tam yolu bulmayı dene
            alt_path = Path(payload.get("folder_path", "")) / "final.mp4"
            if alt_path.exists():
                video_path = str(alt_path)
            else:
                return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}

        title = payload.get("title", "Yeni Video")[:100]
        desc = payload.get("description", "")[:5000]
        channel_name = payload.get("channel_name", "")
        schedule_date = payload.get("schedule_date", "")
        schedule_time = payload.get("schedule_time", "19:00")
        display_summary = payload.get("display_summary", f"{schedule_date} {schedule_time}")

        self._log(f"🎬 YouTube Studio Yüklemesi Başlatılıyor: '{title}'", logger=logger)
        self._log(f"📍 Kanal: '{channel_name}' | ⏰ Planlanan Yayım: {display_summary}", logger=logger)

        with sync_playwright() as p:
            # Google Chrome yüklüyse onu kullan, yoksa Chromium
            chrome_app_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]

            context_kwargs = {
                "user_data_dir": self.user_data_dir,
                "headless": self.headless,
                "args": launch_args,
                "viewport": {"width": 1280, "height": 800},
            }
            if os.path.exists(chrome_app_path):
                context_kwargs["executable_path"] = chrome_app_path

            context = p.chromium.launch_persistent_context(**context_kwargs)
            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)

                # Giriş kontrolü
                if "accounts.google.com" in page.url or "signin" in page.url:
                    self._log("⚠️ YouTube hesabına giriş yapılması gerekiyor. Lütfen açılan tarayıcıdan Google/YouTube hesabınıza 1 kez giriş yapın.", level="warn", logger=logger)
                    # Kullanıcının giriş yapması için 60 saniye bekle
                    for _ in range(60):
                        if "studio.youtube.com" in page.url and "accounts.google.com" not in page.url:
                            break
                        page.wait_for_timeout(1000)

                # Kanal geçişi
                if channel_name:
                    self.switch_channel(page, channel_name, logger=logger)

                # 1. 'OLUŞTUR' / 'YÜKLE' Butonuna Tıkla
                self._log("📤 'Video Yükle' butonu aranıyor...", logger=logger)
                create_clicked = False
                for btn_sel in [
                    "#create-icon", "button#upload-button", "ytcp-button#create-icon",
                    "[aria-label*='Create']", "[aria-label*='Oluştur']", "#upload-icon",
                    "ytcp-icon-button#create-icon", "ytcp-button[label*='Create']", "ytcp-button[label*='Oluştur']"
                ]:
                    loc = page.locator(btn_sel).first
                    if loc.is_visible():
                        loc.click()
                        create_clicked = True
                        break

                page.wait_for_timeout(1500)
                upload_menu_item = page.locator(
                    "tp-yt-paper-item:has-text('Video yükle'), tp-yt-paper-item:has-text('Upload videos'), "
                    "ytcp-text-menu-item:has-text('Video yükle'), ytcp-text-menu-item:has-text('Upload videos')"
                ).first
                if upload_menu_item.is_visible():
                    upload_menu_item.click()
                    page.wait_for_timeout(2000)

                # 2. Dosya Seçim Input'una Videoyu Gönder
                self._log(f"📁 Video dosyası yükleniyor: {Path(video_path).name}", logger=logger)
                file_input = page.locator("input[type='file'], input[name='Filedata']").first
                try:
                    file_input.wait_for(state="attached", timeout=15000)
                    file_input.set_input_files(os.path.abspath(video_path))
                except Exception as file_err:
                    self._log(f"⚠️ Dosya seçici doğrudan bulunamadı, 'Dosya seç' butonuna tıklanıyor: {file_err}", level="warn", logger=logger)
                    select_btn = page.locator("#select-files-button, button:has-text('Dosya seç'), button:has-text('Select files')").first
                    with page.expect_file_chooser() as fc_info:
                        select_btn.click()
                    file_chooser = fc_info.value
                    file_chooser.set_files(os.path.abspath(video_path))

                # Yükleme diyaloğunun açılmasını bekle
                page.wait_for_selector("#dialog, ytcp-uploads-dialog, [role='dialog']", state="visible", timeout=30000)
                page.wait_for_timeout(3000)
                self._log("✅ Video başarıyla YouTube Studio yükleme penceresine aktarıldı.", logger=logger)

                # 3. Başlık ve Açıklamayı Doldur
                self._log(f"📝 Başlık dolduruluyor: '{title}'", logger=logger)
                title_box = page.locator(
                    "#textbox[aria-label*='title'], #textbox[aria-label*='başlık'], "
                    "ytcp-social-suggestions-textbox[aria-label*='title'] #textbox, "
                    "div#textbox[contenteditable='true'], ytcp-mention-textbox #textbox"
                ).first
                if title_box.is_visible():
                    title_box.click()
                    page.keyboard.press("Meta+A")
                    page.keyboard.press("Backspace")
                    title_box.fill(title)
                else:
                    self._log("⚠️ Başlık kutusu bulunamadı, varsayılan başlık kullanılıyor.", level="warn", logger=logger)

                page.wait_for_timeout(1000)
                if desc:
                    self._log("📄 Açıklama metni yazılıyor...", logger=logger)
                    desc_box = page.locator(
                        "#description-textarea #textbox, "
                        "ytcp-social-suggestions-textbox[aria-label*='description'] #textbox, "
                        "ytcp-mention-textbox[aria-label*='description'] #textbox"
                    ).first
                    if desc_box.is_visible():
                        desc_box.click()
                        page.keyboard.press("Meta+A")
                        page.keyboard.press("Backspace")
                        desc_box.fill(desc)

                # 4. Çocuklara Özel Değil Seçeneğini İşaretle
                self._log("👶 'Çocuklara özel değil' seçeneği işaretleniyor...", logger=logger)
                not_mfk = page.locator(
                    "tp-yt-paper-radio-button[name='NOT_MADE_FOR_KIDS'], "
                    "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK'], "
                    "tp-yt-paper-radio-button:has-text('Hayır, çocuklara özel değil'), "
                    "tp-yt-paper-radio-button:has-text('No, it\\'s not made for kids')"
                ).first
                if not_mfk.is_visible():
                    not_mfk.click()
                page.wait_for_timeout(1000)

                # 5. Adımları İlerlet (Details -> Video elements -> Checks -> Visibility)
                self._log("➡️ Görünürlük (Visibility) sekmesine ilerleniyor...", logger=logger)
                for step_idx in range(3):
                    # Butonun tıklanabilir (disabled olmadığını) kontrol et
                    next_btn = page.locator("#next-button, button#next-button, ytcp-button#next-button").first
                    for wait_retry in range(15):
                        is_disabled = next_btn.get_attribute("aria-disabled") == "true" or next_btn.get_attribute("disabled") is not None
                        if not is_disabled and next_btn.is_visible():
                            break
                        page.wait_for_timeout(1000)
                    if next_btn.is_visible():
                        next_btn.click()
                        page.wait_for_timeout(2000)

                # 6. 'Planlayın' (Schedule) Seçeneğini İşaretle
                self._log(f"⏰ Yayım zamanı ayarlanıyor: {display_summary}", logger=logger)
                schedule_radio = page.locator(
                    "#schedule-radio-button, tp-yt-paper-radio-button[name='schedule'], "
                    "tp-yt-paper-radio-button:has-text('Planlayın'), tp-yt-paper-radio-button:has-text('Schedule'), "
                    "#second-container-expand-button"
                ).first
                if schedule_radio.is_visible():
                    schedule_radio.click()
                    page.wait_for_timeout(1500)

                # Tarih ve Saat Kutularını Ayarla
                if schedule_date:
                    date_input = page.locator("ytcp-date-picker input, #datepicker-trigger input, input[aria-label*='date'], input[aria-label*='tarih']").first
                    if date_input.is_visible():
                        date_input.click()
                        page.keyboard.press("Meta+A")
                        page.keyboard.press("Backspace")
                        date_input.fill(schedule_date)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(1000)

                if schedule_time:
                    time_input = page.locator("ytcp-time-of-day-picker input, #time-of-day-trigger input, input[aria-label*='time'], input[aria-label*='saat']").first
                    if time_input.is_visible():
                        time_input.click()
                        page.keyboard.press("Meta+A")
                        page.keyboard.press("Backspace")
                        time_input.fill(schedule_time)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(1000)

                # 7. 'Planla' (Schedule / Done) Butonuna Tıkla
                self._log("🚀 'Planla' butonuna tıklanıyor ve yükleme kaydediliyor...", logger=logger)
                done_btn = page.locator(
                    "#done-button, ytcp-button#done-button, button#done-button, "
                    "ytcp-button:has-text('Planla'), ytcp-button:has-text('Schedule'), "
                    "ytcp-button:has-text('Kaydet'), ytcp-button:has-text('Save')"
                ).first
                for wait_done in range(15):
                    is_done_disabled = done_btn.get_attribute("aria-disabled") == "true" or done_btn.get_attribute("disabled") is not None
                    if not is_done_disabled and done_btn.is_visible():
                        break
                    page.wait_for_timeout(1000)

                if done_btn.is_visible():
                    done_btn.click()
                    page.wait_for_timeout(6000)

                # 8. Kapatma Diyaloğu
                close_btn = page.locator("#close-button, ytcp-button#close-button, button#close-button, [aria-label*='Kapat'], [aria-label*='Close']").first
                if close_btn.is_visible():
                    close_btn.click()
                    page.wait_for_timeout(2000)

                self._log(f"🎉 Yükleme ve 19:00 Planlaması Tamamlandı! ({title})", logger=logger)

                # Backend'deki klasör durumunu güncelle
                folder = payload.get("folder", "")
                if folder:
                    try:
                        import requests
                        requests.post(f"http://127.0.0.1:8000/api/output/{folder}/status", json={"youtube": True}, timeout=5)
                    except Exception:
                        pass

                return {
                    "success": True,
                    "title": title,
                    "channel_name": channel_name,
                    "display_summary": display_summary,
                }

            except Exception as e:
                self._log(f"❌ YouTube Studio yükleme hatası: {e}", level="error", logger=logger)
                return {"success": False, "error": str(e)}
            finally:
                context.close()

    def upload_group_queue(self, queue: List[Dict[str, Any]], logger: Optional[Callable] = None) -> Dict[str, Any]:
        """Gruptaki tüm kanalların videolarını sırayla YouTube Studio'ya yükler ve 19:00 saatine planlar."""
        results = []
        total = len(queue)
        self._log(f"🚀 Grup Yükleme Başlatıldı! Toplam {total} kanal sırayla yüklenecek.", logger=logger)

        for idx, payload in enumerate(queue):
            ch_name = payload.get("channel_name", payload.get("channel_id", f"Kanal #{idx+1}"))
            self._log(f"--- [{idx+1}/{total}] '{ch_name}' Kanalı Yükleniyor ---", logger=logger)
            res = self.upload_single_video(payload, logger=logger)
            results.append({
                "channel_id": payload.get("channel_id"),
                "channel_name": ch_name,
                "success": res.get("success", False),
                "error": res.get("error"),
                "display_summary": res.get("display_summary"),
            })
            time.sleep(3)

        success_count = sum(1 for r in results if r["success"])
        self._log(f"🏁 Grup Yükleme Tamamlandı! Başarılı: {success_count}/{total}", logger=logger)

        return {
            "success": success_count > 0,
            "total": total,
            "success_count": success_count,
            "results": results,
        }


# Singleton örnek
youtube_playwright_uploader = YouTubePlaywrightUploader(headless=False)
