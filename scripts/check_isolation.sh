#!/usr/bin/env bash
# Fail if operator/host fingerprints leak into the public tree.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Patterns that must never appear in published sources (except this script).
# Keep intentional scrub *fixtures* under tests/ out of scope for path-based IPs.
PATTERNS=(
  '/home/ilo'
  '/home/pablo'
  'parallax'
  'vektra'
  'PabloTheThinker@proton'
  'thethinker\.pablo'
  'HERMES_HOME=/home'
  'tailscale'
  'tail[0-9a-f]+\.ts\.net'
  '\bilo@'
  '\bmocha\b'
  'fudoshin'
  'OPENAI_API_KEY[[:space:]]*='
  'XAI_API_KEY[[:space:]]*='
)

# Stricter patterns — apply only outside tests/ (tests may include scrub fixtures)
STRICT_NON_TEST=(
  '100\.[0-9]+\.[0-9]+\.[0-9]+'
  'client.*secret'
  '/home/[a-z]'
)

FAIL=0
scan_file() {
  local f="$1"
  shift
  local patterns=("$@")
  local p
  for p in "${patterns[@]}"; do
    if grep -nIiE "$p" "$f" >/dev/null 2>&1; then
      echo "LEAK in $f matching /$p/"
      grep -nIiE "$p" "$f" | head -5 || true
      FAIL=1
    fi
  done
}

while IFS= read -r -d '' f; do
  case "$f" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.pdf|*.woff*|*.sqlite*|*.db) continue ;;
    ./scripts/check_isolation.sh) continue ;;
    ./.git/*|./.venv/*|./venv/*|./dist/*|./build/*|./.pytest_cache/*|./*/.e2e-last/*) continue ;;
  esac
  scan_file "$f" "${PATTERNS[@]}"
  case "$f" in
    ./tests/*) ;;
    *) scan_file "$f" "${STRICT_NON_TEST[@]}" ;;
  esac
done < <(find . -type f \
  ! -path './.git/*' \
  ! -path './.venv/*' \
  ! -path './venv/*' \
  ! -path './dist/*' \
  ! -path './build/*' \
  ! -path './.pytest_cache/*' \
  ! -path './.e2e-last/*' \
  ! -path '*/__pycache__/*' \
  ! -path './*.egg-info/*' \
  -print0)

if [[ "$FAIL" -ne 0 ]]; then
  echo "Isolation check FAILED"
  exit 1
fi
echo "Isolation check OK"
