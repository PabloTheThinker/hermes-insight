---
name: hermes-insight
description: "Use when an agent needs superior pattern recognition — distill levers, match structures, cross-domain analogy, trajectories, catalogue novelty, multi-agent lattices, code ingest. CLI + native insight_* tools."
version: "0.4.0"
author: Pablo Navarro
license: MIT
metadata:
  hermes:
    tags: [cognition, pattern-recognition, memory, harness, spp, multi-agent]
    requires_binaries: []
---

# Hermes Insight (Hermes skill)

Superior pattern-processing harness for agents. Neurodivergent-inspired connecting-the-dots: **encode → match → link → distill → extrapolate → evolve**.

Standalone package + optional **native Hermes plugin** (`insight_*` tools).

## When to load

- Root-cause / “what’s actually going on” analysis  
- Repeated incidents, architectures, ops, market shapes  
- Cross-domain analogy (“same shape as X”)  
- Durable structural memory beyond chat logs  
- Multi-agent compartmentalized lattices  
- Bulk code/tree pattern catalogue  

## Setup

```bash
pip install hermes-insight   # or editable path

mkdir -p "$HERMES_HOME/memories/hermes-insight"
export HERMES_INSIGHT_DB="${HERMES_INSIGHT_DB:-$HERMES_HOME/memories/hermes-insight/insight.db}"
```

### Native plugin (recommended on Hermes)

```bash
cp -R hermes_plugin/hermes_insight_plugin "$HERMES_HOME/plugins/hermes-insight"
```

```yaml
plugins:
  enabled: [hermes-insight]   # merge with your existing list
  entries:
    hermes-insight:
      agent_id: default
      # db_path: ${HERMES_HOME}/memories/hermes-insight/insight.db
```

Restart Hermes after enabling. Tools: `insight_cycle`, `insight_ingest`, `insight_ingest_tree`, `insight_match`, `insight_distill`, `insight_feedback`, `insight_stats`, `insight_evolve`.

## Cognitive stance

1. Structure over gist — name the **actual variable**  
2. Multi-lens match — template · prototype · features · IDF hybrid  
3. Lateral hops — cross-domain analogy  
4. Trajectories early — direction + risks + confidence  
5. Catalogue novelty — do not force-fit  
6. Observation ≠ inference  
7. Finished briefs  
8. Feedback loops — reinforce what paid rent  
9. Multi-agent — separate DBs/compartments per trust boundary  

## Forge (make something new)

```bash
hermes-insight forge
```

Human uses of patterns → map · predict · transfer · invent · playbooks · watch.
Plugin: `insight_forge`.

## Server fabric (see everything)

```bash
hermes-insight index-server
hermes-insight index-path ~/projects/foo
hermes-insight index-connections
hermes-insight fabric-stats
```

Plugin: insight_index_server, insight_index_path, insight_index_connections, insight_fabric_stats.
Secrets and host fingerprints are scrubbed before catalogue.

## CLI

```bash
hermes-insight demo
hermes-insight --agent conductor cycle "situation" -o "obs1" -o "obs2"
hermes-insight ingest-tree /path/to/repo --limit 60
hermes-insight ingest "title" "body" --domain code --tag x
hermes-insight match "query" --domain system
hermes-insight distill "messy text"
hermes-insight feedback p_xxx
hermes-insight register-agent worker-a --tier worker --parent conductor
```

## Python

```python
from hermes_insight import HermesInsight

lat = HermesInsight(agent_id="conductor", agent_tier="conductor")
lat.ingest_tree("~/hermes-agent/agent", limit=40)
report = lat.cycle("...", observations=["..."], domain="system")
print(report.brief)
```

## Prefer tools when plugin is live

| Need | Tool |
|------|------|
| Full analysis | `insight_cycle` |
| Catalogue file/tree | `insight_ingest` / `insight_ingest_tree` |
| Lever only | `insight_distill` |
| After success/fail | `insight_feedback` |

## Privacy

Separate DB per trust boundary (personal vs client). Never catalogue secrets into shared lattices.

## Docs

Repo: https://github.com/PabloTheThinker/hermes-insight  
`docs/RESEARCH.md` · `docs/ARCHITECTURE.md` · `docs/HERMES.md`
