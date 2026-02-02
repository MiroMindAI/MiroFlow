#!/bin/bash

LOG_DIR="/mnt/agent-framework/bin_wang/miroflow-private-2026/logs/gaia-validation-165/standard_gaia-validation-165_mirothinker_20260203_0113"

while true; do
    clear
    echo "=== Progress Check $(date '+%Y-%m-%d %H:%M:%S') ==="
    uv run python utils/check_progress_gaia-validation-text-103.py "$LOG_DIR"
    sleep 60
done
