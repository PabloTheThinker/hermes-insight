# Hermes Insight

**Superior pattern-processing harness for AI agents.**

Neurodivergent-inspired *connecting-the-dots* cognition as software: encode structures, match them with multiple lenses, hop laterally across domains, distill the actual variable, extrapolate trajectories, and evolve a living catalogue.

Standalone Python library + CLI. **No cloud dependency. No host coupling.** Optional [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill pack included for install-as-skill workflows.

> **Name note:** *Hermes Insight* is an independent companion harness for agents (including Hermes Agent). It is **not** an official Nous Research product.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Why this exists

Pattern recognition is not “one embedding distance.”

Human (and especially many neurodivergent) cognition often:

1. **Decomposes** input into features  
2. **Matches** via templates, prototypes, *and* feature sets  
3. **Catalogues** the world so novelty is noticeable  
4. **Distills** a messy scene to the *actual variable*  
5. **Extrapolates** where a sequence is heading  
6. **Links across domains** when structure rhymes (analogy)  
7. **Generates** higher-order syntheses from clusters  
8. **Reinforces** what worked  

AI agents are usually strong at local next-token reasoning and weak at *durable structural memory with lateral hops*. Hermes Insight is a harness for that missing layer.

Research foundations (see [`docs/RESEARCH.md`](docs/RESEARCH.md)):

- Superior pattern processing (SPP) as a core of human cognitive advantage  
- Classic cognitive models: template / prototype / feature analysis  
- Operational six-dimension pattern cognition (perception → generation continuum)  
- Lived ND descriptions: distillation, trajectory, sensory cataloguing, explicit social pattern analysis  

This project is **inspired by** those ideas. It is **not** a diagnostic tool and not a claim about any individual.

---

## Pattern Forge

Patterns earn rent when they become products:

```bash
hermes-insight forge
# → orientation map, prediction board, transfer pack, invention seeds, playbooks, watch edges
```

## Server fabric

Index host structure (scrubbed) so Insight sees projects, software trees, metadata, and connections:

```bash
hermes-insight index-server
hermes-insight fabric-stats
hermes-insight cycle "how do plugins relate to listening services?"
```

## Quick start

```bash
# clone
git clone https://github.com/PabloTheThinker/hermes-insight.git
cd hermes-insight

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# isolated demo (temp DB)
hermes-insight demo

# your own lattice
export HERMES_INSIGHT_DB=./my-insight.db
hermes-insight ingest "retry with jitter" \
  "Retry transient failures with exponential backoff and jitter." \
  --domain code --tag retry --tag backoff

hermes-insight cycle "timeouts spike and on-call is drowning in pages" \
  -o "retries amplified downstream load" \
  -o "duplicate alerts every few minutes"
```

Python API:

```python
from hermes_insight import HermesInsight

lat = HermesInsight(db_path="./my-insight.db")
lat.ingest(
    "circuit breaker",
    "Open the circuit when error rate spikes to protect callers.",
    domain="code",
    kind="rule",
    tags=["circuit", "breaker"],
)
report = lat.cycle(
    "dependency errors cascading into our API",
    observations=["p99 climbing", "retries storm"],
)
print(report.brief)
print(report.distillation.actual_variable)
```

---

## Cognitive cycle

```text
observations
    │
    ▼
┌────────────┐
│ Perception │  feature decompose
└─────┬──────┘
      ▼
┌────────────┐
│  Seeking   │  FTS + candidate hunt
└─────┬──────┘
      ▼
┌────────────┐
│Recognition │  template · prototype · feature · hybrid
└─────┬──────┘
      ▼
┌────────────┐
│ Processing │  distill actual variable
└─────┬──────┘
      ▼
┌────────────┐
│Maintenance │  catalogue · anomaly file · links
└─────┬──────┘
      ▼
┌────────────┐
│ Generation │  trajectory · synthesis · bigger ideas
└─────┬──────┘
      ▼
   brief  →  agent acts  →  feedback/reinforce
```

---

## CLI

Also: `ingest-tree`, `--agent`, `register-agent`, native Hermes plugin tools `insight_*`.


| Command | Purpose |
|--------|---------|
| `stats` | counts + db path |
| `ingest` | add pattern |
| `match` / `search` | recognition |
| `cycle` | full brief |
| `distill` | actual variable |
| `extrapolate` | trajectory |
| `analogy` | cross-domain map |
| `feedback` | reinforce / weaken |
| `evolve` | decay + cluster synthesis |
| `export` | JSON dump |
| `demo` | seed + sample cycle |

Global flags: `--db PATH`, `--json`, `--version`.

Env:

- `HERMES_INSIGHT_DB` — sqlite file  
- `HERMES_INSIGHT_HOME` — directory defaulting to `~/.hermes-insight`

---

## Hermes Agent

**Phase 1 (now):** standalone package anyone can use.

**Skill pack:** copy or install [`skills/hermes-insight/SKILL.md`](skills/hermes-insight/SKILL.md) into a Hermes skills directory:

```bash
# from a Hermes host
mkdir -p "$HERMES_HOME/skills/cognition/hermes-insight"
cp skills/hermes-insight/SKILL.md "$HERMES_HOME/skills/cognition/hermes-insight/"
# optional: pip install this repo into the Hermes venv
pip install -e /path/to/hermes-insight
```

**Phase 2 (later):** optional plugin under `hermes_plugin/` registering tools — designed to follow Hermes plugin discovery (`~/.hermes/plugins/`) without forking Hermes core. See [`docs/HERMES.md`](docs/HERMES.md).

---

## Design principles (Hermes-grade craft)

- One clear public harness (`HermesInsight`), thin CLI over it  
- SQLite + FTS5 durable state (local, profile-safe paths)  
- Deterministic core — LLM optional via `prompts.py` scaffolds  
- JSON-serializable everything at the boundary  
- Tests for cycle, match, distill, anomaly, CLI demo  
- Isolation script: `scripts/check_isolation.sh`  

---

## Project layout

```text
src/hermes_insight/     # library
tests/                   # pytest
docs/                    # research + architecture + hermes
skills/hermes-insight/  # Hermes SKILL.md
hermes_plugin/           # optional future plugin skeleton
examples/                # scripts
```

---

## Status

`0.1.0` alpha — core cycle works offline; API may evolve before `0.2`.

---

## License

MIT © Pablo Navarro

## Author

Published by **Pablo Navarro**. Built for agents that need to *see structure*, not only complete text.
