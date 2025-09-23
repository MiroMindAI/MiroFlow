#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

RESULTS_DIR=${RESULTS_DIR:-"logs/xbench-ds/$(date +"%Y%m%d_%H%M")"}
echo "Results will be saved in: $RESULTS_DIR"

export CHINESE_CONTEXT="true"

uv run main.py common-benchmark \
  --config_file_name=agent_quickstart_1 \
  benchmark=xbench-ds \
  output_dir=$RESULTS_DIR