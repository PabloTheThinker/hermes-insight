#!/usr/bin/env python3
"""Refresh agent-field index + forge for the current HERMES_HOME (generic)."""
from __future__ import annotations

import os
from pathlib import Path

from hermes_insight import HermesInsight

home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
agent = (os.environ.get("HERMES_INSIGHT_AGENT_ID") or "").strip()
mem = home / "memories" / "hermes-insight"
if agent:
    db = mem / "agents" / f"{agent}.insight.db"
else:
    db = mem / "insight.db"
db.parent.mkdir(parents=True, exist_ok=True)

lat = HermesInsight(db_path=str(db), agent_id=agent or None)

print("index_server hermes home…", home)
rep = lat.index_server(
    roots=[str(home)],
    include_files=False,
    include_connections=True,
    include_processes=False,
    include_hermes=True,
    max_projects=8,
    max_files_per_project=5,
)
print({k: rep.get(k) for k in ("patterns_created", "projects_found", "connections_found", "errors")})
print("fabric", lat.fabric_stats().get("by_kind"))

print("forge…")
fr = lat.forge(products=["map", "predict", "invent", "playbooks"])
print("run", fr.get("run_dir"))
print("synth", fr.get("synthesis_ids"))

r = lat.perceive(
    "How should multi-agent profiles share a model route without leaking client skills?",
    domain="multi_agent",
    deep=True,
)
print("=== PERCEIVE CARD ===")
print(r.get("card", "")[:2000])
