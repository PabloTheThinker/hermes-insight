---
name: hermes-insight
description: "Use when an agent needs superior pattern recognition — recall priors, log experience, connect events to structure, distill levers, multi-agent lattices."
version: "0.6.0"
author: Pablo Navarro
license: MIT
metadata:
  hermes:
    tags: [cognition, pattern-recognition, memory, harness, spp, multi-agent, experience]
    requires_binaries: []
---

# Hermes Insight (Hermes skill)

**Field:** AI agents and models.  
Native nouns: agent, model, tool, skill, plugin, profile, context, memory, multi-agent, inference, **experience**, **task**, **event**.

Superior pattern-processing harness. Neurodivergent-inspired connecting-the-dots:
**recall → act → experience → connect → distill → reinforce**.

Standalone package + native Hermes plugin (`insight_*` tools).

## When to load

- Before hard debugging / architecture / recurring ops (**recall first**)
- Multi-step tasks that should leave structural memory
- Cross-domain “same shape as X”
- After failures and fixes (so the next session is faster)
- Multi-agent compartmentalized lattices
- Bulk code/tree catalogue + forge products

## Install (any Hermes agent)

```bash
# from the hermes-insight repo
./scripts/install_for_hermes.sh
# or a profile / client agent:
HERMES_HOME=~/.hermes/profiles/myagent ./scripts/install_for_hermes.sh --agent myagent --tier worker

# manual
pip install hermes-insight   # or: pip install -e /path/to/hermes-insight
mkdir -p "$HERMES_HOME/skills/cognition/hermes-insight"
cp skills/hermes-insight/SKILL.md "$HERMES_HOME/skills/cognition/hermes-insight/"
cp -R hermes_plugin/hermes_insight_plugin "$HERMES_HOME/plugins/hermes-insight"
```

```yaml
plugins:
  enabled: […existing…, hermes-insight]   # merge — never replace the whole list
  entries:
    hermes-insight:
      agent_id: default          # optional compartment
      # db_path: ${HERMES_HOME}/memories/hermes-insight/insight.db
```

Restart Hermes after enabling. Fresh DBs auto-seed starter agent-field patterns on first `insight_recall` / `bootstrap`.

## Default loop (do this — it is the product)

| Step | Tool | When |
|------|------|------|
| 1 | **`insight_recall`** | BEFORE hard work — priors + lived echoes + hops |
| 2 | **`insight_task` open** | Starting multi-step work — keep `task_id` |
| 3 | **`insight_experience`** | After events, failures, fixes, decisions |
| 4 | **`insight_connect`** | When you see “same shape as X” |
| 5 | **`insight_task` close** | Done — outcome + summary reinforces patterns |
| 6 | **`insight_cycle`** | Deep novel root-cause when recall is thin |
| 7 | **`insight_feedback`** | Manual reinforce/weaken if needed |

Also: `insight_bootstrap`, `insight_ingest_messages`, fabric index + `insight_forge`.

## Cognitive stance

1. **Recall before rediscovery** — second failure should hit the lattice  
2. Structure over gist — name the **actual variable**  
3. Multi-lens match — template · prototype · features · IDF hybrid  
4. Lateral hops — cross-domain analogy  
5. Catalogue novelty — do not force-fit  
6. Observation ≠ inference  
7. Finished briefs  
8. Feedback loops — reinforce what paid rent  
9. Multi-agent — separate DBs per trust boundary  

## CLI

```bash
hermes-insight bootstrap
hermes-insight recall "two workers share one bot token"
hermes-insight task open --name fix-gateway --goal "conflict on getUpdates"
hermes-insight experience "saw 409" "second consumer still polling" --task-id t_xxx
hermes-insight task close --task-id t_xxx --outcome fixed --summary "one consumer rule"
hermes-insight cycle "…" -o "obs"
hermes-insight forge
hermes-insight index-server
```

## Python

```python
from hermes_insight import HermesInsight

lat = HermesInsight(agent_id="conductor", agent_tier="conductor")
lat.bootstrap()
print(lat.recall("gateway credential conflict")["brief"])
t = lat.open_task("fix conflict", goal="dual long-poll")
lat.experience("conflict", "409 from getUpdates", task_id=t["task_id"])
lat.close_task(t["task_id"], outcome="fixed", summary="single consumer")
```

## Privacy

Separate DB per trust boundary (personal vs client). Never catalogue secrets into shared lattices.

## Docs

https://github.com/PabloTheThinker/hermes-insight  
`docs/RESEARCH.md` · `docs/ARCHITECTURE.md` · `docs/HERMES.md` · `docs/EXPERIENCE.md`
