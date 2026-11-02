#!/bin/bash
set -e
JOB_FILE="$1"
if [ -z "$JOB_FILE" ]; then
    echo "Usage: run_job.sh <job_file.json>"
    exit 1
fi

DIR="/home/ubuntu/yt-remote-worker"
cd "$DIR"

LOG_FILE="$DIR/logs/$(basename "$JOB_FILE" .json).log"
mkdir -p "$DIR/logs" "$DIR/jobs"

# Akilli Hibrit Yonlendirici (Smart Hybrid Dispatcher)
# Eger is emri basketbol veya spor ise ultra-hizli Rust motoru (yt-worker) calisir
IS_SPORTS=$(grep -E '"(thebasketballshows|basketball_analysis|sports)"' "$JOB_FILE" || true)

if [ -n "$IS_SPORTS" ] && [ -x "$DIR/yt-worker" ]; then
    echo "[SmartRouter] 🦀 Rust yt-worker motoru secildi: $JOB_FILE" >> "$LOG_FILE"
    nice -n 19 ionice -c 3 "$DIR/yt-worker" --job "$JOB_FILE" >> "$LOG_FILE" 2>&1 &
    ROUTER_NAME="Rust"
else
    echo "[SmartRouter] 🐍 Python server_worker motoru secildi: $JOB_FILE" >> "$LOG_FILE"
    export OMP_NUM_THREADS=2
    nice -n 19 ionice -c 3 /home/ubuntu/defense_news_shorts/.venv/bin/python3 -u "$DIR/server_worker.py" --job "$JOB_FILE" >> "$LOG_FILE" 2>&1 &
    ROUTER_NAME="Python"
fi

PID=$!
echo "$PID" > "$DIR/jobs/$(basename "$JOB_FILE" .json).pid"
echo "Job started with PID $PID (Engine: $ROUTER_NAME)"
