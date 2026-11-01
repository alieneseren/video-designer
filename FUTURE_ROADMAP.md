# Gelecek Özellikler Yol Haritası (Future Feature Roadmap)

Bu dosya, ilerleyen aşamalarda `yt-oto-video` otonom video üretim sistemine kazandırılması planlanan Ar-Ge fikirlerini ve mimari planları içerir.

---

## 📌 1. YouTube Viral Tersine Mühendislik Motoru (Viral Hook Reverse-Engineering)
* **İlham Kaynağı:** Orkun Işıtmak - Banana Studio (`orkunisitmak/banana-studio`) YouTube konsept ve transkript analiz yeteneği.
* **Amaç:** Manuel konu ve araştırma yerine, doğrudan YouTube üzerinde viral olmuş başarılı Shorts/videoların dinamiğini çözüp özgün senaryo üretmek.
* **Nasıl Çalışacak?**
  1. Kullanıcı veya otonom sistem başarılı bir rakip YouTube Shorts / Video URL'si verir.
  2. Sistem videonun altyazısını/transkriptini (`yt-dlp` / whisper) ve başlık/açıklama metinlerini çeker.
  3. LLM (Claude / GPT-4o / Gemini) videonun kanca (hook) yapısını, izleyici tutma taktiğini ve ana bilgi noktalarını deşifre eder.
  4. Bizim `real_media_fetcher.py` + `visual_content_guard.py` motorumuzla telifsiz gerçek görsel/stok eşleştirmesi yapılarak kanalın formatına uygun, sıfırdan 10 sahneli özgün bir Shorts kurgusu oluşturulur.

---

## 📌 2. Yüksek CTR'lı Otomatik Kapak (Clickbait Thumbnail) Motoru
* **İlham Kaynağı:** Banana Studio Thumbnail Layering & Visual Contrast System.
* **Amaç:** YouTube algoritmasında tıklama oranını (CTR) maksimize eden dikkat çekici kapaklar üretmek.
* **Nasıl Çalışacak?**
  1. Videonun en dramatik anındaki yüksek çözünürlüklü kare seçilir (örn. 48% eğimli kırmızı vagonun uçuruma tırmandığı an).
  2. Nesne ayrıştırma (rembg / contour cutout) ile ana odak öne çıkarılır.
  3. Üzerine büyük, sarı/kırmızı yüksek kontrastlı, siyah dış konturlu merak uyandırıcı 2-3 kelimelik başlık yazılır (örn: *"DON'T LOOK DOWN!"*).
  4. Video YouTube API ile yüklenirken bu kapak otomatik olarak atanır.

---

## 📌 3. Telifsiz YouTube B-Roll Kesici (Creative Commons Sub-clip Scraper)
* **Amaç:** Pixabay veya Wikimedia'da video bulunamayan çok nadir konularda (örn. 1889'dan kalma antik tren mekanizmaları) Creative Commons lisanslı YouTube içeriklerinden 3-4 saniyelik B-roll kesitler alıp dikey 9:16 formata kırparak kurguya dahil etmek.
