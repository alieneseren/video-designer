#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=== 1. Eski Sınırlı Önbellek ve İndirilenler Temizleniyor ==="
pkill -9 -f "server_worker" 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf temp/* cache/* assets/downloads/* 2>/dev/null || true

PYTHON_BIN="python3"
if [ -f "/home/ubuntu/defense_news_shorts/.venv/bin/python3" ]; then
    PYTHON_BIN="/home/ubuntu/defense_news_shorts/.venv/bin/python3"
elif [ -f "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
fi

export PYTHONPATH="$DIR/src:$DIR:$PYTHONPATH"

echo "=== 2. Çoklu Sorgu ve Zengin Aday İndirme Testi ==="
$PYTHON_BIN -c "
from core.query_builder import QueryBuilder
queries = QueryBuilder().build_multi_queries('Hakeem Olajuwon', 'David Robinson', 1995)
print('Oluşturulan Sorgular:', queries)
assert len(queries) >= 4, 'En az 4 arama varyasyonu üretilmeli!'
"

echo "=== 3. Hakeem Olajuwon Videosu Zengin Görsel Havuzuyla Yeniden Derleniyor ==="
$PYTHON_BIN -m core.pipeline_orchestrator \
    --project "hakeem_dream_shake" \
    --topic "Hakeem Olajuwon Dream Shake 1995 Western Conference Finals David Robinson" \
    --min-assets 14 \
    --force-rebuild \
    --output "output/final_hakeem_action.mp4"

echo "=== Render Tamamlandı! Video output/final_hakeem_action.mp4 konumunda hazır. ==="
