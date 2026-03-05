#!/usr/bin/env bash
# Build a standalone deb package from the PyInstaller binary (dist/aish).
# This does NOT change the existing build.sh workflow.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage: packaging/make_deb_from_pyinstaller.sh [--no-build] [--out-dir DIR] [--no-date] [--release]

Options:
  --no-build       Do not run ./build.sh; assume dist/aish already exists.
  --out-dir DIR    Output directory for .deb (default: ./dist-deb)
  --no-date        Do not append build date suffix to the deb Version.
  --release        Release build: disable date suffix and default revision to "1".

Environment overrides:
  AISH_DEB_PACKAGE_NAME  Debian package name (default: "aish")
  AISH_DEB_REVISION      Debian revision suffix appended to Version (default: "1")
  AISH_DEB_RELEASE       Release build mode: 1/0 (default: "0")
  AISH_DEB_APPEND_DATE   Append build date to Version: 1/0 (default: "1")
  AISH_DEB_BUILD_DATE    Date string appended when enabled (default: "$(date +%Y%m%d)")
  AISH_DEB_MAINTAINER    Maintainer field (default: "ai-shell <noreply@example.com>")
  AISH_DEB_SECTION       Debian section (default: "utils")
  AISH_DEB_PRIORITY      Debian priority (default: "optional")
EOF
}

NO_BUILD=0
OUT_DIR="$ROOT/dist-deb"
RELEASE_MODE="${AISH_DEB_RELEASE:-0}"
APPEND_DATE="${AISH_DEB_APPEND_DATE:-1}"
BUILD_DATE="${AISH_DEB_BUILD_DATE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      NO_BUILD=1
      shift
      ;;
    --no-date)
      APPEND_DATE=0
      shift
      ;;
    --release)
      RELEASE_MODE=1
      APPEND_DATE=0
      shift
      ;;
    --out-dir)
      OUT_DIR="${2:-}"
      if [[ -z "$OUT_DIR" ]]; then
        echo "--out-dir requires a value" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "Error: dpkg-deb not found. Install dpkg (Debian/Ubuntu) first." >&2
  exit 1
fi

if [[ $NO_BUILD -eq 0 ]]; then
  ./build.sh
fi

BIN="$ROOT/dist/aish"
if [[ ! -f "$BIN" ]]; then
  echo "Error: $BIN not found. Run ./build.sh first (or omit --no-build)." >&2
  exit 1
fi

SANDBOX_BIN="$ROOT/dist/aish-sandbox"
if [[ ! -f "$SANDBOX_BIN" ]]; then
  echo "Error: $SANDBOX_BIN not found." >&2
  echo "Hint: rebuild with ./build.sh to generate dist/aish-sandbox." >&2
  exit 1
fi

# Read version from pyproject.toml
# - Python 3.11+: tomllib
# - Python 3.10:  fall back to tomli if present; otherwise regex
if command -v uv >/dev/null 2>&1; then
  VERSION="$(uv run python - <<'PY'
import pathlib
import re

text = pathlib.Path('pyproject.toml').read_text(encoding='utf-8')

data = None
try:
    import tomllib  # py>=3.11
    data = tomllib.loads(text)
except ModuleNotFoundError:
    try:
        import tomli  # optional
        data = tomli.loads(text)
    except ModuleNotFoundError:
        data = None

if isinstance(data, dict):
    print(data.get('project', {}).get('version', '0.0.0'))
else:
    m = re.search(r"^version\s*=\s*\"([^\"]+)\"\s*$", text, flags=re.MULTILINE)
    print(m.group(1) if m else '0.0.0')
PY
  )"
else
  VERSION="$(sed -nE 's/^version[[:space:]]*=[[:space:]]*"([^"]+)"[[:space:]]*$/\1/p' pyproject.toml | head -n1)"
  VERSION="${VERSION:-0.0.0}"
fi

PKGNAME="${AISH_DEB_PACKAGE_NAME:-aish}"
ARCH="$(dpkg --print-architecture)"

MAINTAINER="${AISH_DEB_MAINTAINER:-ai-shell <noreply@example.com>}"
SECTION="${AISH_DEB_SECTION:-utils}"
PRIORITY="${AISH_DEB_PRIORITY:-optional}"

# Default Debian revision to 1 for both daily builds and release builds.
DEB_REVISION="${AISH_DEB_REVISION:-1}"
if [[ -n "$DEB_REVISION" ]]; then
  DEB_VERSION="${VERSION}-${DEB_REVISION}"
else
  DEB_VERSION="${VERSION}"
fi

# Append build date suffix for easier daily-build differentiation.
# Use "+YYYYMMDD" so it remains a valid Debian version and does not
# conflict with the Debian revision separator '-'.
if [[ "$APPEND_DATE" != "0" ]]; then
  if [[ -z "$BUILD_DATE" ]]; then
    BUILD_DATE="$(date +%Y%m%d)"
  fi
  DEB_VERSION="${DEB_VERSION}+${BUILD_DATE}"
fi

PKGROOT="$(mktemp -d)"
trap 'rm -rf "$PKGROOT"' EXIT

mkdir -p "$PKGROOT/DEBIAN" \
  "$PKGROOT/usr/bin" \
  "$PKGROOT/etc/aish" \
  "$PKGROOT/usr/share/doc/$PKGNAME" \
  "$PKGROOT/lib/systemd/system"

install -m 0755 "$BIN" "$PKGROOT/usr/bin/aish"

# Install sandbox daemon binary and systemd units (merged into the main package).
install -m 0755 "$SANDBOX_BIN" "$PKGROOT/usr/bin/aish-sandbox"
install -m 0644 "$ROOT/debian/aish-sandbox.service" "$PKGROOT/lib/systemd/system/aish-sandbox.service"
install -m 0644 "$ROOT/debian/aish-sandbox.socket" "$PKGROOT/lib/systemd/system/aish-sandbox.socket"

# Ship a system-wide default security policy as a conffile.
if [[ -f "$ROOT/config/security_policy.yaml" ]]; then
  install -m 0644 "$ROOT/config/security_policy.yaml" "$PKGROOT/etc/aish/security_policy.yaml"
fi

cat > "$PKGROOT/DEBIAN/control" <<EOF
Package: $PKGNAME
Version: $DEB_VERSION
Section: $SECTION
Priority: $PRIORITY
Architecture: $ARCH
Maintainer: $MAINTAINER
Depends: bubblewrap, util-linux
Description: AI Shell (standalone PyInstaller binary)
EOF

cat > "$PKGROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e

case "$1" in
  configure|abort-upgrade|abort-deconfigure|abort-remove)
    if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
      systemctl daemon-reload >/dev/null 2>&1 || true
      systemctl enable aish-sandbox.socket >/dev/null 2>&1 || true
      if systemctl is-active --quiet aish-sandbox.socket || systemctl is-active --quiet aish-sandbox.service; then
        systemctl restart aish-sandbox.socket >/dev/null 2>&1 || true
      else
        systemctl start aish-sandbox.socket >/dev/null 2>&1 || true
      fi
    fi
  ;;
esac

exit 0
EOF
chmod 0755 "$PKGROOT/DEBIAN/postinst"

cat > "$PKGROOT/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e

case "$1" in
  remove|deconfigure)
    if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
      systemctl stop --no-block aish-sandbox.service >/dev/null 2>&1 || true
      systemctl disable --now aish-sandbox.socket >/dev/null 2>&1 || true
      systemctl reset-failed aish-sandbox.service >/dev/null 2>&1 || true
    fi
  ;;
esac

exit 0
EOF
chmod 0755 "$PKGROOT/DEBIAN/prerm"

cat > "$PKGROOT/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e

case "$1" in
  remove|purge)
    if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
      systemctl disable --now aish-sandbox.socket >/dev/null 2>&1 || true
      systemctl stop --no-block aish-sandbox.service >/dev/null 2>&1 || true
      systemctl reset-failed aish-sandbox.service >/dev/null 2>&1 || true
      systemctl daemon-reload >/dev/null 2>&1 || true
    fi
  ;;
esac

exit 0
EOF
chmod 0755 "$PKGROOT/DEBIAN/postrm"

# Mark config file as conffile so dpkg keeps local changes on upgrade.
if [[ -f "$PKGROOT/etc/aish/security_policy.yaml" ]]; then
  cat > "$PKGROOT/DEBIAN/conffiles" <<'EOF'
/etc/aish/security_policy.yaml
EOF
fi

mkdir -p "$OUT_DIR"
OUT_DEB="$OUT_DIR/${PKGNAME}_${DEB_VERSION}_${ARCH}.deb"
dpkg-deb --build "$PKGROOT" "$OUT_DEB" >/dev/null

echo "Built deb: $OUT_DEB"