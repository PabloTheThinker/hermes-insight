#!/usr/bin/env bash
# Install Hermes Insight for ANY Hermes Agent profile/home.
# Usage:
#   ./scripts/install_for_hermes.sh
#   HERMES_HOME=~/.hermes/profiles/client ./scripts/install_for_hermes.sh
#   ./scripts/install_for_hermes.sh --agent worker1 --tier worker
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
AGENT_ID=""
AGENT_TIER="worker"
FORCE_SEED=0
SKIP_PLUGIN=0
SKIP_SKILL=0
PYTHON_BIN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT_ID="$2"; shift 2 ;;
    --tier) AGENT_TIER="$2"; shift 2 ;;
    --hermes-home) HERMES_HOME="$2"; shift 2 ;;
    --force-seed) FORCE_SEED=1; shift ;;
    --skip-plugin) SKIP_PLUGIN=1; shift ;;
    --skip-skill) SKIP_SKILL=1; shift ;;
    --python) PYTHON_BIN="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$HERMES_HOME"
HERMES_HOME="$(cd "$HERMES_HOME" && pwd)"

echo "== Hermes Insight install =="
echo "  repo:        $ROOT"
echo "  HERMES_HOME: $HERMES_HOME"
echo "  agent_id:    ${AGENT_ID:-default}"
echo "  tier:        $AGENT_TIER"

if [[ -n "$PYTHON_BIN" ]]; then
  PY="$PYTHON_BIN"
elif [[ -x "$HERMES_HOME/venv/bin/python" ]]; then
  PY="$HERMES_HOME/venv/bin/python"
elif [[ -x "${HOME}/hermes-agent/venv/bin/python" ]]; then
  PY="${HOME}/hermes-agent/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "No python3 found" >&2
  exit 1
fi
echo "  python:      $PY"

echo "-- pip install hermes-insight (editable)"
"$PY" -m pip install -e "$ROOT" -q

if [[ "$SKIP_SKILL" -eq 0 ]]; then
  SKILL_DST="$HERMES_HOME/skills/cognition/hermes-insight"
  mkdir -p "$SKILL_DST"
  cp -f "$ROOT/skills/hermes-insight/SKILL.md" "$SKILL_DST/SKILL.md"
  echo "-- skill → $SKILL_DST/SKILL.md"
fi

if [[ "$SKIP_PLUGIN" -eq 0 ]]; then
  PLUG_DST="$HERMES_HOME/plugins/hermes-insight"
  mkdir -p "$HERMES_HOME/plugins"
  rm -rf "$PLUG_DST"
  cp -a "$ROOT/hermes_plugin/hermes_insight_plugin" "$PLUG_DST"
  echo "-- plugin → $PLUG_DST"
  "$PY" "$ROOT/scripts/_merge_plugin_config.py" "$HERMES_HOME" "$AGENT_ID"
fi

MEM="$HERMES_HOME/memories/hermes-insight"
mkdir -p "$MEM/agents"
if [[ -n "$AGENT_ID" ]]; then
  DB="$MEM/agents/${AGENT_ID}.insight.db"
else
  DB="$MEM/insight.db"
fi
export HERMES_HOME
export HERMES_INSIGHT_DB="$DB"

echo "-- bootstrap lattice → $DB"
"$PY" - <<PY
from hermes_insight import HermesInsight
lat = HermesInsight(
    db_path=r"""$DB""",
    agent_id=(r"""$AGENT_ID""" or None),
    agent_tier=r"""$AGENT_TIER""",
)
print("bootstrap:", lat.bootstrap(force=bool($FORCE_SEED)))
print("stats:", lat.stats())
r = lat.recall("two workers share one bot credential long-poll conflict")
print("recall_lever:", r.get("lever"))
print("recall_top:", [m.get("title") for m in (r.get("matches") or [])[:3]])
PY

cat <<EOF

== Done ==
Any Hermes agent workflow:
  1. insight_recall   — before hard work
  2. insight_task open — multi-step jobs
  3. insight_experience — after events/fixes
  4. insight_task close — reinforce patterns
  5. insight_cycle — deep novel root-cause

CLI:
  hermes-insight --db "$DB" recall "gateway credential conflict"
  hermes-insight --db "$DB" task open --name demo --goal "test"

Restart Hermes/gateway so plugin tools load.
EOF
