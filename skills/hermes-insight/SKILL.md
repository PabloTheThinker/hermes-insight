---
name: hermes-insight
description: "Use when an agent needs superior pattern recognition — distill levers, match structures, cross-domain analogy, trajectories, catalogue novelty, evolve a pattern graph. Offline harness + CLI."
version: "0.1.0"
author: Pablo Navarro
license: MIT
metadata:
  hermes:
    tags: [cognition, pattern-recognition, memory, harness, spp]
    requires_binaries: []
---

# Hermes Insight (Hermes skill)

Superior pattern-processing harness for agents. Neurodivergent-inspired connecting-the-dots: **encode → match → link → distill → extrapolate → evolve**.

This skill teaches you to *use* the standalone `hermes-insight` package. It does not embed operator-specific data.

## When to load

- Root-cause / “what’s actually going on” analysis  
- Repeated incidents, social dynamics, code architectures, market shapes  
- Need cross-domain analogy (“this is the same shape as X”)  
- Building durable structural memory beyond chat logs  
- Novelty detection against a known catalogue  

## Setup (once per environment)

```bash
pip install hermes-insight
# or editable: pip install -e /path/to/hermes-insight

# profile-scoped DB (Hermes)
mkdir -p "$HERMES_HOME/memories"
export HERMES_INSIGHT_DB="${HERMES_INSIGHT_DB:-$HERMES_HOME/memories/hermes-insight.db}"
```

Verify:

```bash
hermes-insight --version
hermes-insight demo
```

## Standing cognitive stance

1. Structure over gist — name the **actual variable**  
2. Three match lenses — template, prototype, features  
3. Lateral hops — analogy across domains when structure rhymes  
4. Trajectories early — direction + risks + confidence  
5. Catalogue novelty — do not force-fit  
6. Observation ≠ inference  
7. Finished briefs — not warehouses  
8. Feedback loops — reinforce patterns that proved useful  

## Core commands

```bash
# Full cycle → markdown brief
hermes-insight cycle "situation text" \
  -o "observation 1" \
  -o "observation 2"

# JSON for tool parsing
hermes-insight --json cycle "situation" -o "obs"

# Catalogue a learned structure
hermes-insight ingest "short title" "full body..." \
  --domain code --kind rule --tag retry --confidence 0.75

# Match only
hermes-insight match "query text" -n 8

# Distill lever
hermes-insight distill "messy paragraph..."

# Trajectory
hermes-insight extrapolate "step1" "step2" "step3"

# After a pattern helped in the real world
hermes-insight feedback p_xxxxxxxxxxxx

# If it misled
hermes-insight feedback p_xxxxxxxxxxxx --unhelpful

# Evolution tick (synthesis + optional decay)
hermes-insight evolve
```

Domains: `general|code|system|social|process|sensory|language|market|science|self`  
Kinds: `template|prototype|feature|sequence|relation|rule|trajectory|anomaly|synthesis`

## Python (execute_code / tools)

```python
from hermes_insight import HermesInsight
import os

db = os.environ.get("HERMES_INSIGHT_DB")  # prefer explicit
lat = HermesInsight(db_path=db) if db else HermesInsight()

lat.ingest("title", "body", domain="code", kind="rule", tags=["x"])
report = lat.cycle("query", observations=["a", "b"])
print(report.brief)
print(report.distillation.actual_variable)
```

## Workflow recipe

1. **Collect** observations (raw, dated if possible)  
2. **`cycle`** — read distillation + matches + trajectory + anomalies  
3. **Act** on the lever (smallest intervention)  
4. **`ingest`** new confirmed structures  
5. **`feedback`** on patterns that paid rent  
6. Periodic **`evolve`** on long-running agents  

## Anti-patterns

- Treating analogy as proof  
- Cataloguing secrets or personal data into shared lattices  
- Skipping feedback (graph never learns)  
- One giant undifferentiated domain for everything  
- Replacing investigation with pattern cosplay  

## Related docs (in the package repo)

- `docs/RESEARCH.md` — cognitive foundations  
- `docs/ARCHITECTURE.md` — software map  
- `docs/HERMES.md` — install + plugin phase  

## Privacy

Use a **separate DB per trust boundary** (personal vs client vs public experiments).
