# 🚀 YouTube Otomatik İçerik Sistemi — Kurulum Rehberi

## Sistem Özeti

```
LM Studio (Gemma 4 / Local AI) → Senaryo
        ↓
Edge TTS → Seslendirme (27+ dil)
        ↓
NASA API → Ücretsiz uzay görselleri
        ↓
MoviePy → Video montaj (1920×1080, H.264)
        ↓
FastAPI + React Dashboard → Yönetim paneli
```

---

## 1. Hızlı Başlat

```bash
# 1) LM Studio'yu aç, bir model yükle (ör: google/gemma-4-12b-qat)
# 2) LM Studio → Local Server → Start Server (port 1234)
# 3) Proje klasörüne git:
cd yt-oto-video/files

# 4) Tek tuşla başlat:
./start.sh
# → Tarayıcıda aç: http://localhost:8000
```

---

## 2. Ön Koşullar

- **Python 3.11+**
- **Node.js 18+** (dashboard build için)
- **FFmpeg** (`brew install ffmpeg`)
- **LM Studio** (https://lmstudio.ai) — ücretsiz, yerel AI
  - veya Anthropic API (Claude) / Google API (Gemini) desteği de mevcut

---

## 3. Proje Kurulumu

```bash
# Repoyu klonla
cd yt-oto-video/files

# Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dashboard build
cd dashboard
npm install
npm run build
cd ..

# Çalıştır
./start.sh
```

---

## 4. AI Provider Ayarları

### A) LM Studio (Önerilen — Ücretsiz, Yerel)

1. LM Studio'yu indir: https://lmstudio.ai
2. Model yükle (önerilen: `google/gemma-4-12b-qat`)
3. **Local Server → Start Server** (port 1234 varsayılan)
4. Dashboard'da **Ayarlar** → Provider: **LM Studio**
5. LM Studio URL: `http://localhost:1234/v1`

### B) Anthropic Claude (Bulut)

1. https://console.anthropic.com → API Key oluştur
2. Dashboard Ayarlar → Provider: Claude → API Key gir

### C) Google Gemini (Bulut)

1. https://aistudio.google.com → API Key oluştur
2. Dashboard Ayarlar → Provider: Gemini → API Key gir

### D) Instagram Reels zamanlama (Chrome eklentisi)

Bu akış Meta Graph API kullanmaz. Planlanan saatte videoyu Chrome eklentisi, Instagram web sitesinde oturum açılmış kullanıcı arayüzüne yükler.

1. Chrome'da `chrome://extensions` sayfasını açıp Geliştirici Modu'nu etkinleştirin ve projedeki `extension/` klasörünü paketlenmemiş eklenti olarak yükleyin. Eklenti zaten kuruluysa klasörü yeniden yükleyin/yenileyin.
2. Kanalı düzenleyin, Instagram paylaşımını etkinleştirin ve Instagram kullanıcı adını girin.
3. Chrome'da bu hesapla Instagram'a giriş yapın. Zamanlama anında Chrome, eklenti ve proje sunucusu çalışır durumda kalmalı; bilgisayar uykuya geçmemelidir. Eklenti gerekirse Instagram sekmesini açıp öne getirir.
4. Dashboard **Instagram Planla** sayfasından veya Chrome eklentisinden video, tarih ve saat seçerek plan oluşturun. Plan oluşturmak anında yükleme veya paylaşım yapmaz.
5. Zaman geldiğinde eklenti yerel sunucudan videoyu alır, Instagram web yükleme penceresine ekler, açıklamayı yazar ve **Paylaş** adımını tamamlar. Instagram arayüzü güncellenirse otomasyon başarısız olabilir; hata plan listesinde görünür. Paylaşım isteği gönderildikten sonra sonuç belirsizse yinelenen gönderi riskini önlemek için tekrar otomatik denenmez ve plan **Kontrol gerekli** durumuna alınır.

Tarayıcı/eklentinin kapalı veya Instagram oturumunun süresi dolmuş olması zamanında paylaşımı engeller. Başarısız, henüz gönderim yapılmamış işlemler en fazla üç kez denenir. Web arayüzü otomasyonu Instagram'ın arayüz değişikliklerine bağlıdır; ilk kullanımdan önce düşük riskli bir hesapta test edin.

---

### E) Uzak sunucu Kokoro-TTS (daha doğal anlatıcı)

Kokoro, uzak üretim kuyruğundaki havacılık ve genel anlatıcı sesleri için isteğe bağlıdır; mevcut Chatterbox ortamından ayrı bir sanal ortamda kurulur. Kurulum yaklaşık 355 MB model dosyasını indirir ve Chatterbox/PyTorch bağımlılıklarını değiştirmez.

Uzak sunucuya proje dosyalarını aktardıktan sonra sunucuda çalıştırın:

```bash
bash /home/ubuntu/yt-remote-worker/scripts/remote_server/install_kokoro.sh
```

Dashboard **Ayarlar → Uzak Sunucu Seslendirmesi** bölümünden Kokoro-TTS'yi seçin. Seçim, daha sonra uzak kuyruğa gönderilen işlere eklenir; önceden kuyruğa alınmış işler ayarları değiştirilmedikçe mevcut motorlarını kullanır. İngilizce, İspanyolca, Fransızca, Hintçe, İtalyanca, Japonca, Brezilya Portekizcesi ve Mandarin desteklenir. Desteklenmeyen diller havacılık işlerinde Chatterbox'a, diğer video işlerinde Edge TTS'e yönlendirilir. İngilizce için anlatıcı sesi ve 0.8×–1.2× hız ayarlanabilir.

Havacılık anlatımında Chatterbox'ın aşırı vurgulu sentez parametresi de daha doğal varsayılan değerlere çekilmiştir. Sunucu kuyruğunu devam ettirmeden önce kısa bir örnek videoyu dinleyip ses ve hızı Ayarlar'dan doğrulayın.

---

## 5. NASA API (Görseller)

1. https://api.nasa.gov → "Generate API Key" → e-posta gir
2. Anında gelir, ücretsiz
3. Dashboard Ayarlar → NASA API Key gir

---

## 6. Kullanım

### Dashboard (Tarayıcı)
- `http://localhost:8000` adresini aç
- **+ Yeni Kanal** → Dil, konu kategorisi, özel konular gir
- **▶ Video Üret** butonu ile tek tıkla video oluştur
- Ayarlar sayfasından AI modeli ve API anahtarlarını yönet
- **AI Sohbet → Üretim Asistanı** bölümünde LM Studio'ya doğal dille komut ver (ör. “Reddit hikâyeleri için Gemini API ile 3 video üret”). LM Studio'nun Local Server'ı açık olmalı; seçilen Gemini/Claude sağlayıcısının API anahtarı Ayarlar'da kayıtlı olmalı.
- Asistan, aktif kanal/kategoriye ait mevcut üretilebilir plan satırlarını kullanır; plan sayısı yetersizse seçilen sağlayıcıyla eksik konuları ekler ve videoları sırayla üretir. Üretim durumu aynı ekranda izlenebilir.

### CLI (Komut Satırı)
```bash
source .venv/bin/activate

# Tüm kanalları çalıştır
python src/main.py

# Belirli kanal
python src/main.py --channel ch_uzay_tr

# Kanal listele
python src/main.py --list

# Yeni kanal ekle (sihirbaz)
python src/main.py --setup
```

---

## 7. Proje Dosya Yapısı

```
files/
├── start.sh                 ← Tek tuşla başlatma betiği
├── src/
│   ├── server.py            ← FastAPI backend + dashboard hosting
│   ├── main.py              ← CLI orkestratör
│   ├── script_writer.py     ← AI senaryo üretimi (LM Studio/Gemini/Claude)
│   ├── video_generator.py   ← TTS + NASA görsel + MoviePy montaj
│   ├── channel_manager.py   ← Kanal CRUD yönetimi
│   ├── settings_manager.py  ← API anahtarı ve ayar yönetimi
│   └── youtube_uploader.py  ← YouTube yükleme (opsiyonel)
├── dashboard/
│   ├── src/App.jsx          ← React dashboard UI
│   └── dist/                ← Build çıktısı (start.sh ile otomatik)
├── config/
│   ├── settings.json        ← API anahtarları (şifreli)
│   └── channels.json        ← Kanal yapılandırmaları
├── credentials/             ← OAuth dosyaları (opsiyonel, git'e ekleme!)
└── output/                  ← Üretilen videolar
```

---

## 8. Desteklenen Diller

| Kod | Dil | Ses Motoru |
|---|---|---|
| tr | Türkçe | tr-TR-AhmetNeural |
| en | İngilizce | en-US-JennyNeural |
| de | Almanca | de-DE-KatjaNeural |
| fr | Fransızca | fr-FR-DeniseNeural |
| es | İspanyolca | es-ES-ElviraNeural |
| ja | Japonca | ja-JP-NanamiNeural |
| ko | Korece | ko-KR-SunHiNeural |
| zh | Çince | zh-CN-XiaoxiaoNeural |
| ar | Arapça | ar-SA-ZariyahNeural |
| + 18 dil daha | | |

---

## 9. API Endpoints

| Method | URL | Açıklama |
|---|---|---|
| GET | `/api/settings` | Ayarları getir (maskelenmiş) |
| PUT | `/api/settings` | Ayarları güncelle |
| GET | `/api/channels` | Kanalları listele |
| POST | `/api/channels` | Kanal ekle |
| PUT | `/api/channels/{id}` | Kanal güncelle |
| DELETE | `/api/channels/{id}` | Kanal sil |
| PUT | `/api/channels/{id}/toggle` | Aktif/Pasif |
| POST | `/api/run/{id}` | Video üretim başlat |
| GET | `/api/run/status/{exec_id}` | Üretim durumu |
| GET | `/api/channels/{id}/instagram-schedule-info` | Kanal Instagram planlama bilgileri |
| GET/POST | `/api/instagram/schedules` | Instagram planlarını listele veya yeni plan oluştur |
| POST | `/api/instagram/schedules/claim` | Chrome eklentisi için zamanı gelmiş sıradaki planı al |
| GET | `/api/instagram/schedules/{schedule_id}/video` | Yükleme için planlanmış yerel videoyu eklentiye sun |
| POST | `/api/instagram/schedules/{schedule_id}/result` | Eklentinin yayın sonucunu kaydet |
| DELETE | `/api/instagram/schedules/{schedule_id}` | Henüz başlamamış Instagram planını iptal et |
| POST | `/api/assistant/produce` | LM Studio doğal dil komutuyla seri video üretimi başlat |
| GET | `/api/logs` | Üretim logları |
| GET | `/docs` | Swagger API dokümantasyonu |
