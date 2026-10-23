#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# YouTube Otomasyon — Tek tuşla başlatma betiği
# ─────────────────────────────────────────────────────────
set -e

cd "$(dirname "$0")"
echo "🎬 YouTube Otomasyon Sistemi Başlatılıyor..."
echo ""

# ── 1. Virtual Environment ──────────────────────────────
if [ ! -d ".venv" ]; then
    echo "❌ .venv bulunamadı. Kurulum için:"
    echo "   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source .venv/bin/activate
echo "✅ Python virtual env aktif ($(python --version | cut -d' ' -f2))"

# ── 2. FFmpeg kontrol ──────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
    echo "❌ ffmpeg bulunamadı. Kurulum: brew install ffmpeg"
    exit 1
fi
echo "✅ ffmpeg mevcut ($(ffmpeg -version 2>&1 | head -1 | grep -oP '\d+\.\d+\.\d+' | head -1))"

# ── 3. Klasörler ────────────────────────────────────────
mkdir -p output config credentials
echo "✅ Klasörler hazır"

# ── 4. Dashboard build ─────────────────────────────────
if [ -f "dashboard/package.json" ] && [ ! -d "dashboard/dist" ]; then
    echo "📦 Dashboard build ediliyor..."
    cd dashboard
    npm install --silent 2>/dev/null
    npm run build --silent
    cd ..
    echo "✅ Dashboard build tamamlandı"
elif [ -d "dashboard/dist" ]; then
    echo "✅ Dashboard build mevcut (tekrar build için: cd dashboard && npm run build)"
fi

# ── 5. LM Studio kontrol ───────────────────────────────
if curl -s -m 3 http://localhost:1234/v1/models >/dev/null 2>&1; then
    MODEL_COUNT=$(curl -s http://localhost:1234/v1/models 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null || echo "0")
    echo "✅ LM Studio çalışıyor ($MODEL_COUNT model yüklü)"
else
    echo "⚠️  LM Studio çalışmıyor (http://localhost:1234). LM Studio'yu başlatın!"
fi

# ── 6. Backend başlat ──────────────────────────────────
echo ""
echo "🚀 Backend başlatılıyor: http://localhost:8000"
echo "   Dashboard:  http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
echo "   Durdurmak için: Ctrl+C"
echo ""

uvicorn src.server:app \
    --host 127.0.0.1 \
    --port 8000 \
    --app-dir . \
    --reload \
    --reload-dir src \
    --log-level info
