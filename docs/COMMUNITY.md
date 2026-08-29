# Hermes Community fit — what X/builders need vs Hermes Insight

*Research snapshot 2026-08-09 from public X discussion on Hermes Agent / AI agent frameworks + our production E2E.*

This is an **independent companion** for [Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research). Not an official Nous product.

## What people on X keep asking for

### 1. Shared multi-agent memory / one brain
Plugins like Icarus market “one brain,” entity wikis, cross-agent recall. Builders want **shared structure** without leaking compartments.  
**Insight fit:** multi-agent DBs + `agent_id` compartments; fabric links `HAS_SKILL` / `USES_MODEL` / `SHARES_CONTEXT`; forge maps the fleet.

### 2. Memory graphs, not only MEMORY.md
Vector dumps and flat notes lose relationships. Demand is for **walkable graphs** (entities, edges, provenance).  
**Insight fit:** SQLite pattern graph + links (part_of, enables, analogy, delegates_to, uses_model…). Index skills/tools/models/profiles as first-class nodes.

### 3. Skills discovery / routing / less sprawl
Huge skill hubs → selection bottleneck; people want routing, cleanup, and “what skill for this model.”  
**Insight fit:** `skill:*` nodes + forge **skill↔model routing** seed; distill lever often lands on `skill` when profiles share routes; feedback reinforces skills that paid rent.

### 4. Multi-agent orchestration clarity
Profiles, subagents, MOA, Kanban — users want **visible fleet structure** and ownership of endpoints.  
**Insight fit:** `agent:*` profiles, listen endpoints, plugin/tool graph, orientation map + prediction board for trajectory of the fleet.

### 5. Self-improving loop that compounds
Skills from experience + dreaming/pruning.  
**Insight fit:** forge products (map/predict/transfer/invent/playbooks/watch) + synthesis nodes written back; evolve/decay; production ritual `index → forge → feedback`.

### 6. Plugin sprawl / “one layer”
Desire for fewer moving parts that still deepen intelligence.  
**Insight fit:** single plugin `hermes-insight` with `insight_*` tools covering index, cycle, forge — structural layer beside memory providers.

### 7. Production reliability / scrubbing / isolation
Absolute paths, poisoned memory, client leak risk.  
**Insight fit:** secret/IP/home scrubbing; client vs conductor DBs; E2E production script gates isolation + scrub.

### 8. Portable agent patterns across harnesses
Skills/memory that aren’t locked to one CLI.  
**Insight fit:** standalone Python package + skill pack + optional Hermes plugin; agent-field ontology portable to other harnesses.

## Production E2E (what “ready” means here)

```bash
pip install -e ".[dev]"
python3 scripts/production_e2e.py
```

Last full run (see `docs/E2E-PRODUCTION-LAST.json`): production gates on latest tag — boot, seed, multi-agent isolation, fabric index, perceive/experience, agent-field cycles, forge artifacts, feedback, scrub, plugin handlers, export.

## 60-second community install

```bash
pip install hermes-insight   # or: pip install -e .
export HERMES_INSIGHT_DB="$HERMES_HOME/memories/hermes-insight/insight.db"

# optional native plugin
cp -R hermes_plugin/hermes_insight_plugin "$HERMES_HOME/plugins/hermes-insight"
# enable hermes-insight under plugins.enabled + restart Hermes

hermes-insight bootstrap
hermes-insight perceive "how should profiles share a model without leaking client skills?"
hermes-insight forge
```

## Positioning one-liner (for X / Discord)

> **Hermes Insight** — pattern recognition ability for agents: perceive situations, distill the controlling variable, connect experience, forge maps. Companion plugin for Hermes Agent.

## Honest non-goals

- Not a full conversational memory provider (use Honcho/Mem0/etc. beside it).
  Insight **recalls** a working set; it does not replace MEMORY.md or ingest chat.  
- Not a replacement for Hermes skills hub discovery UI.  
- Not automatic fine-tuning — it *structures* what you’d train or route on.

## Contribute upstream-friendly

- Keep this repo free of operator paths/secrets (`scripts/check_isolation.sh`).  
- Prefer widening Hermes plugin surface over core PRs.  
- Issues/PRs: agent-field ontology, forge products, fabric extractors.
