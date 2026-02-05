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

needs_rebuild=false

# Check if static dir is missing or empty
if [ ! -d "$STATIC_DIR" ] || [ -z "$(ls -A $STATIC_DIR 2>/dev/null)" ]; then
    needs_rebuild=true
    echo -e "${GREEN}Static directory missing or empty, will build frontend...${NC}"
else
    # Check if any frontend source file is newer than the built index.html
    BUILT_FILE="$STATIC_DIR/index.html"
    if [ -f "$BUILT_FILE" ]; then
        # Find any .ts, .tsx, .css file newer than the built file
        NEWER_FILES=$(find "$FRONTEND_DIR/src" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.css" \) -newer "$BUILT_FILE" 2>/dev/null | head -5)
        if [ -n "$NEWER_FILES" ]; then
            needs_rebuild=true
            echo -e "${GREEN}Frontend source files changed, will rebuild...${NC}"
            echo "Changed files:"
            echo "$NEWER_FILES" | while read f; do echo "  - $(basename $f)"; done
        fi
    else
        needs_rebuild=true
    fi
fi

if [ "$needs_rebuild" = true ]; then
    echo -e "${GREEN}Building frontend...${NC}"
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi

    npm run build
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}Frontend built successfully!${NC}"
else
    echo -e "${GREEN}Frontend is up to date${NC}"
fi

# Start the server
echo -e "${GREEN}Starting server on http://0.0.0.0:8000${NC}"
echo -e "${GREEN}API docs available at http://0.0.0.0:8000/docs${NC}"
echo ""

uv run python -m web_app.main
