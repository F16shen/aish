.PHONY: help install dev test lint format build build-binary build-v20-binary build-ubuntu-binary clean install-binary deploy

# Default target
help:
	@echo "🚀  AI Shell - Make Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install        Install dependencies"
	@echo "  make dev            Install dev dependencies"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linting"
	@echo "  make format         Format code"
	@echo ""
	@echo "Building:"
	@echo "  make build          Build Python wheel"
	@echo "  make build-binary   Build standalone binary"
	@echo "  make build-v20-binary   Build V20-style .deb from standalone binary"
	@echo "  make build-ubuntu-binary Build Ubuntu-style .deb from standalone binary"
	@echo "  make clean          Clean build artifacts"
	@echo ""
	@echo "Deployment:"
	@echo "  make install-binary Install binary to /usr/local/bin"
	@echo "  make deploy         Deploy to remote server (set SERVER env)"

install:
	@echo "📦 Installing dependencies..."
	uv sync

dev:
	@echo "📦 Installing dev dependencies..."
	uv sync --all-extras

test:
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v

lint:
	@echo "🔍 Running linting..."
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	@echo "🎨 Formatting code..."
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

build:
	@echo "📦 Building Python wheel..."
	uv build

build-binary:
	@echo "🔨 Building standalone binary..."
	./build.sh

# 目前版本使用v20编译通用软件包，暂时不区分系统版本
build-v20-binary:
	@echo "📦 Building .deb from standalone binary..."
	AISH_DEB_REVISION= ./packaging/make_deb_from_pyinstaller.sh --out-dir ./dist-deb-v20

build-ubuntu-binary:
	@echo "📦 Building Ubuntu .deb from standalone binary..."
	AISH_DEB_REVISION=ubuntu ./packaging/make_deb_from_pyinstaller.sh --out-dir ./dist-deb-ubuntu

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ *.spec.backup __pycache__/ .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.egg-info" -exec rm -rf {} +

install-binary: build-binary
	@echo "📥 Installing binary to /usr/local/bin..."
	sudo cp dist/aish /usr/local/bin/
	sudo chmod +x /usr/local/bin/aish
	@echo "✅ Binary installed! Try: aish --help"

deploy:
	@if [ -z "$(SERVER)" ]; then \
		echo "❌ SERVER environment variable not set"; \
		echo "Usage: make deploy SERVER=user@hostname"; \
		exit 1; \
	fi
	@echo "🚀 Deploying to $(SERVER)..."
	scp dist/aish $(SERVER):/tmp/
	ssh $(SERVER) "sudo mv /tmp/aish /usr/local/bin/ && sudo chmod +x /usr/local/bin/aish"
	@echo "✅ Deployed! Try: ssh $(SERVER) 'aish --help'" 