#!/bin/bash
set -e
JOB_FILE="$1"
if [ -z "$JOB_FILE" ]; then
    echo "Usage: run_job.sh <job_file.json>"
    exit 1
fi

DIR="/home/ubuntu/yt-remote-worker"
cd "$DIR"

export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export VECLIB_MAXIMUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export TOKENIZERS_PARALLELISM=false

LOG_FILE="$DIR/logs/$(basename "$JOB_FILE" .json).log"

nice -n 19 ionice -c 3 /home/ubuntu/defense_news_shorts/.venv/bin/python3 "$DIR/server_worker.py" --job "$JOB_FILE" > "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$DIR/jobs/$(basename "$JOB_FILE" .json).pid"
echo "Job started with PID $PID"
