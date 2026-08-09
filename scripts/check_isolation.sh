#!/usr/bin/env bash
# Fail if operator/host fingerprints leak into the public tree.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PATTERNS=(
  '/home/ilo'
  '/home/pablo'
  'parallax'
  'vektra'
  'PabloTheThinker@proton'
  'thethinker.pablo'
  'HERMES_HOME=/home'
  'tailscale'
  '100\.'
  'lotus'
  'ilo@'
  'mocha'
  'fudoshin'
  'client.*secret'
  'OPENAI_API_KEY'
  'XAI_API_KEY'
)

FAIL=0
while IFS= read -r -d '' f; do
  # skip binary-ish and this script's own pattern list noise handled below
  case "$f" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.pdf|*.woff*|*.sqlite*|*.db) continue ;;
    scripts/check_isolation.sh) continue ;;
  esac
  for p in "${PATTERNS[@]}"; do
    if grep -nIiE "$p" "$f" >/dev/null 2>&1; then
      echo "LEAK in $f matching /$p/"
      grep -nIiE "$p" "$f" | head -5 || true
      FAIL=1
    fi
  done
done < <(find . -type f \
  ! -path './.git/*' \
  ! -path './.venv/*' \
  ! -path './venv/*' \
  ! -path './dist/*' \
  ! -path './build/*' \
  ! -path './.pytest_cache/*' \
  ! -path '*/__pycache__/*' \
  ! -path './*.egg-info/*' \
  -print0)

if [[ "$FAIL" -ne 0 ]]; then
  echo "Isolation check FAILED"
  exit 1
fi
echo "Isolation check OK"
