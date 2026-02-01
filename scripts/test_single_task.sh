#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# Test a single task with the Kimi k2.5 model
# Usage:
#   ./scripts/test_single_task.sh <task_index>           # Test task by index (0-based)
#   ./scripts/test_single_task.sh --task-id <id>         # Test task by ID
#   ./scripts/test_single_task.sh --question "What is 2+2?" --answer "4"  # Test custom question

set -e

# Default configuration
CONFIG_PATH="config/standard_gaia-validation-text-103_kimi_k25.yaml"
OUTPUT_DIR="logs/single_task_tests"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "Single Task Test Runner"
echo "=================================================="

# Parse arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No arguments provided${NC}"
    echo ""
    echo "Usage:"
    echo "  $0 <task_index>                    # Test task by index (0-based)"
    echo "  $0 --task-id <id>                  # Test task by ID"
    echo "  $0 --task-question \"Q?\" [--ground-truth \"A\"]  # Test custom question"
    echo ""
    echo "Options:"
    echo "  --config <path>       Configuration file path (default: $CONFIG_PATH)"
    echo "  --output-dir <path>   Output directory (default: $OUTPUT_DIR)"
    echo ""
    echo "Examples:"
    echo "  $0 0                                          # Test first task"
    echo "  $0 --task-id abc123                           # Test specific task"
    echo "  $0 --task-question \"What is 2+2?\" --ground-truth \"4\""
    exit 1
fi

# Build command arguments
CMD_ARGS=()

# Check if first argument is a number (task index)
if [[ "$1" =~ ^[0-9]+$ ]]; then
    CMD_ARGS+=(--task-index "$1")
    shift
fi

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --config-path)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --task-id)
            CMD_ARGS+=(--task-id "$2")
            shift 2
            ;;
        --task-question)
            CMD_ARGS+=(--task-question "$2")
            shift 2
            ;;
        --ground-truth)
            CMD_ARGS+=(--ground-truth "$2")
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Display configuration
echo -e "${YELLOW}Configuration:${NC}"
echo "  Config file: $CONFIG_PATH"
echo "  Output dir:  $OUTPUT_DIR"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo -e "${RED}Error: Configuration file not found: $CONFIG_PATH${NC}"
    exit 1
fi

# Run the test
echo -e "${GREEN}Running test...${NC}"
echo ""

uv run python test_single_task.py \
    --config-path "$CONFIG_PATH" \
    --output-dir "$OUTPUT_DIR" \
    "${CMD_ARGS[@]}"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Test completed successfully!${NC}"
else
    echo -e "${RED}✗ Test failed with exit code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
