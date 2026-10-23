#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# YouTube Otomasyon — Tek Tuşla Başlatıcı (macOS)
# ─────────────────────────────────────────────────────────

# Terminal penceresinin başlığını ayarla
echo -ne "\033]0;YouTube Otomasyon Başlatıcı\007"

# Çalışma dizinini bu betiğin olduğu klasör yap
cd "$(dirname "$0")"

echo "🚀 YouTube Otomasyon Sistemi Başlatılıyor..."
echo ""

# 1. Sanal ortamı kontrol et
if [ ! -d ".venv" ]; then
    echo "❌ Hata: .venv bulunamadı. Lütfen önce kurulumu tamamlayın."
    read -p "Çıkmak için Enter'a basın..."
    exit 1
fi

# 2. Node.js ve bağımlılık kontrolü
if ! command -v npm &>/dev/null; then
    echo "❌ Hata: npm (Node.js) bulunamadı."
    read -p "Çıkmak için Enter'a basın..."
    exit 1
fi

# 3. Portları temizleme (varsa eski çalışanları temizle)
echo "🧹 Eski servisler kontrol ediliyor..."
pkill -9 -f "src.server:app" || true
pkill -9 -f "vite" || true
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true

# 4. Backend Başlat (Arka planda)
echo "🐍 Backend başlatılıyor (Port: 8000)..."
.venv/bin/uvicorn src.server:app --host 127.0.0.1 --port 8000 --reload --reload-dir src > backend.log 2>&1 &
BACKEND_PID=$!

# 5. Frontend Başlat (Arka planda)
echo "⚛️  Vite Frontend başlatılıyor (Port: 5173)..."
cd dashboard
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Temiz çıkış handler'ı (Ctrl+C yapıldığında veya terminal kapatıldığında)
cleanup() {
    echo ""
    echo "🛑 Sistem durduruluyor..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✅ Tüm servisler kapatıldı."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 6. Servislerin ayağa kalkmasını bekle
echo "⏳ Servisler başlatılıyor, lütfen bekleyin..."
sleep 3

# Tarayıcıyı otomatik aç
if command -v open &>/dev/null; then
    echo "🌐 Tarayıcı açılıyor: http://localhost:5173"
    open "http://localhost:5173"
else
    echo "🌐 Lütfen tarayıcınızdan şu adrese gidin: http://localhost:5173"
fi

echo ""
echo "🔥 Sistem başarıyla çalıştırıldı!"
echo "👉 Backend Logları:  tail -f backend.log"
echo "👉 Frontend Logları: tail -f frontend.log"
echo "🛑 Durdurmak için bu Terminal penceresinde Ctrl+C tuşlarına basın."
echo ""

# Betiğin açık kalması ve arka plan loglarını veya bekleme durumunu sürdürmesi için:
while kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; do
    sleep 1
done

echo "⚠️  Bir servis durdu, sistem kapatılıyor."
cleanup
