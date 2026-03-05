#!/usr/bin/env bash
# Inspect which shared libraries (.so) are bundled inside a PyInstaller onefile executable.
# Works on either the built executable (e.g. dist/aish) or the produced .deb.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  packaging/inspect_pyinstaller_bundle.sh <path-to-aish-or-deb> [--all]

Examples:
  packaging/inspect_pyinstaller_bundle.sh dist/aish
  packaging/inspect_pyinstaller_bundle.sh ./aish_0.1.0-1+20260129_amd64.deb

Output:
  - Prints all bundled .so entries (sorted)
  - Prints whether libstdc++.so.6 / libgcc_s.so.1 are bundled

Options:
  --all   Print full archive listing (not just .so)
EOF
}

if [[ ${1:-} == "" || ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

INPUT="$1"
shift || true
PRINT_ALL=0
if [[ ${1:-} == "--all" ]]; then
  PRINT_ALL=1
fi

if [[ ! -e "$INPUT" ]]; then
  echo "Error: input not found: $INPUT" >&2
  exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv not found. Run inside this repo or install uv." >&2
  exit 2
fi

ARCHIVE_VIEWER=(uv run python -m PyInstaller.utils.cliutils.archive_viewer)

EXE_PATH="$INPUT"
TMPDIR=""
cleanup() {
  if [[ -n "$TMPDIR" && -d "$TMPDIR" ]]; then
    rm -rf "$TMPDIR"
  fi
}
trap cleanup EXIT

if [[ "$INPUT" == *.deb ]]; then
  if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Error: dpkg-deb not found. Install dpkg first." >&2
    exit 2
  fi
  TMPDIR="$(mktemp -d)"
  dpkg-deb -x "$INPUT" "$TMPDIR"

  if [[ -x "$TMPDIR/usr/bin/aish" ]]; then
    EXE_PATH="$TMPDIR/usr/bin/aish"
  else
    echo "Error: cannot find executable at $TMPDIR/usr/bin/aish" >&2
    exit 2
  fi
fi

if [[ ! -x "$EXE_PATH" ]]; then
  echo "Error: not executable: $EXE_PATH" >&2
  exit 2
fi

echo "==> Inspecting PyInstaller archive in: $EXE_PATH" >&2

if [[ $PRINT_ALL -eq 1 ]]; then
  "${ARCHIVE_VIEWER[@]}" -l "$EXE_PATH" | cat
  exit 0
fi

# List only bundled shared libs.
SO_LIST=$(
  # Use --brief output so we get plain file names (stable across PyInstaller versions).
  "${ARCHIVE_VIEWER[@]}" -l -b "$EXE_PATH" \
    | grep -E '\.so(\.|$)' \
    | sort -u
)

if [[ -z "$SO_LIST" ]]; then
  echo "(no .so entries found in archive output)" >&2
else
  echo "$SO_LIST"
fi

echo "" >&2
echo "==> Check toolchain libs:" >&2
if echo "$SO_LIST" | grep -qE 'libstdc\+\+\.so\.6(\.|$)'; then
  echo "FOUND: libstdc++.so.6 is bundled" >&2
else
  echo "OK: libstdc++.so.6 is NOT bundled" >&2
fi

if echo "$SO_LIST" | grep -qE 'libgcc_s\.so\.1(\.|$)'; then
  echo "FOUND: libgcc_s.so.1 is bundled" >&2
else
  echo "OK: libgcc_s.so.1 is NOT bundled" >&2
fi
