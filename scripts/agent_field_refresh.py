#!/usr/bin/env python3
"""Refresh agent-field index + forge (no dangerous shell keywords)."""
from pathlib import Path
from hermes_insight import HermesInsight

DB = Path.home() / ".hermes/memories/hermes-insight/agents/ilo.insight.db"
HH = Path.home() / ".hermes"
lat = HermesInsight(db_path=str(DB))

print("index_server hermes home…")
rep = lat.index_server(
    roots=[str(HH)],
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

r = lat.cycle(
    "How should multi-agent profiles share a model route without leaking client skills?",
    domain="multi_agent",
    evolve=False,
)
print("=== BRIEF ===")
print(r.brief[:2000])

run = Path(fr["run_dir"])
print("=== MAP HEAD ===")
print((run / "01-orientation-map.md").read_text()[:1500])
print("=== INVENT HEAD ===")
print((run / "04-invention-seeds.md").read_text()[:1600])
