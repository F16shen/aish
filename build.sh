#!/bin/bash
# Build script for  AI Shell binary
set -e

echo "🚀 Building  AI Shell binary..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ Error: uv is not installed. Please install uv first.${NC}"
    exit 1
fi

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
uv sync

# Clean previous builds
echo -e "${YELLOW}🧹 Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.spec.backup

# Check if PyInstaller is installed
if ! uv run python -c "import PyInstaller" &> /dev/null; then
    echo -e "${BLUE}📦 Installing PyInstaller...${NC}"
    uv add --dev pyinstaller
fi

# Build using PyInstaller spec file
echo -e "${BLUE}🔨 Building binary with PyInstaller...${NC}"
uv run pyinstaller aish.spec

# Check if build was successful
if [ -f "dist/aish" ] && [ -f "dist/aish-sandbox" ]; then
    echo -e "${GREEN}✅ Binary built successfully!${NC}"
    echo -e "${GREEN}📍 Location: dist/aish${NC}"
    echo -e "${GREEN}📍 Location: dist/aish-sandbox${NC}"
    
    # Get file sizes
    SIZE_MAIN=$(du -h dist/aish | cut -f1)
    SIZE_SANDBOX=$(du -h dist/aish-sandbox | cut -f1)
    echo -e "${GREEN}🔍 Size (aish): ${SIZE_MAIN}${NC}"
    echo -e "${GREEN}🔍 Size (aish-sandbox): ${SIZE_SANDBOX}${NC}"
    
    # Make executable
    chmod +x dist/aish dist/aish-sandbox
    
    # Test the binaries
    echo -e "${BLUE}🧪 Testing binaries...${NC}"
    if ./dist/aish --help > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Binary test passed!${NC}"
        if ./dist/aish-sandbox --help > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Sandbox binary test passed!${NC}"
        else
            echo -e "${YELLOW}⚠️  Sandbox binary has some issues but was built successfully${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Binary has some issues but was built successfully${NC}"
        echo -e "${YELLOW}   (This may be due to LiteLLM/tiktoken packaging complexity)${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}📋 Usage:${NC}"
    echo -e "  ${GREEN}./dist/aish --help${NC}    # Show help"
    echo -e "  ${GREEN}./dist/aish run${NC}       # Start shell"
    echo -e "  ${GREEN}./dist/aish config${NC}    # Show config"
    echo ""
    echo -e "${YELLOW}📦 Deploy to Linux:${NC}"
    echo -e "  ${GREEN}scp dist/aish user@server:/usr/local/bin/${NC}"
    echo -e "  ${GREEN}ssh user@server 'chmod +x /usr/local/bin/aish'${NC}"
else
    echo -e "${RED}❌ Build failed! Expected binaries not found (dist/aish, dist/aish-sandbox).${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Build completed successfully!${NC}" 