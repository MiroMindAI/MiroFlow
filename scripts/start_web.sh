#!/bin/bash
# MiroFlow Web App Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MiroFlow Web App${NC}"
echo -e "${BLUE}========================================${NC}"

# Sync dependencies with uv
echo -e "${GREEN}Syncing dependencies with uv...${NC}"
uv sync

# Check if frontend needs to be built
STATIC_DIR="$PROJECT_ROOT/web_app/static"
FRONTEND_DIR="$PROJECT_ROOT/web_app/frontend"

if [ ! -d "$STATIC_DIR" ] || [ -z "$(ls -A $STATIC_DIR 2>/dev/null)" ]; then
    echo -e "${GREEN}Building frontend...${NC}"
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi

    npm run build
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}Frontend built successfully!${NC}"
fi

# Start the server
echo -e "${GREEN}Starting server on http://0.0.0.0:8000${NC}"
echo -e "${GREEN}API docs available at http://0.0.0.0:8000/docs${NC}"
echo ""

uv run python -m web_app.main
