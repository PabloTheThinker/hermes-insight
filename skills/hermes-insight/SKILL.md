---
name: hermes-insight
description: "Use when an agent needs pattern recognition — perceive situations, distill levers, connect experience, match structures."
version: "0.8.0"
author: Pablo Navarro
license: MIT
metadata:
  hermes:
    tags: [cognition, pattern-recognition, memory, harness, spp, multi-agent, experience]
    requires_binaries: []
---

# Hermes Insight (Hermes skill)

**Pattern recognition ability** for agents: encode → match → link → distill → perceive → reinforce.

Standalone package + native plugin (`insight_*`).

## Deep manual (read when new to Insight)

**[references/AGENT-GUIDE.md](references/AGENT-GUIDE.md)** — full ontology, pipeline, doctrine, install, examples, anti-patterns.

Also in repo: `docs/AGENT-GUIDE.md` ·  
https://github.com/PabloTheThinker/hermes-insight/blob/main/docs/AGENT-GUIDE.md

Load that document (skill_view file_path `references/AGENT-GUIDE.md`, or open the file) the first time you gain this skill. Daily work only needs the loop below.

## When to load

- Before hard debugging / architecture / recurring failures  
- Multi-step tasks that should leave structural memory  
- “Same shape as X” / cross-domain rhyme  
- After failures and fixes  
- Teaching a new agent what Insight is  

## Install (any Hermes agent)

```bash
./scripts/install_for_hermes.sh
# or profile:
HERMES_HOME=~/.hermes/profiles/myagent ./scripts/install_for_hermes.sh --agent myagent
```

```yaml
plugins:
  enabled: […existing…, hermes-insight]   # merge — never replace the list
  entries:
    hermes-insight:
      agent_id: default
      agent_tier: worker
```

Reload Hermes after enabling so `insight_*` tools appear.

## Default ability

**Call `insight_perceive` first** with the situation (+ optional observations).

```text
insight_perceive → insight_plan? → insight_task open → insight_experience* → insight_task close
```

| Tool | When |
|------|------|
| **insight_perceive** | Default — lever + structures + action hint + `usable` |
| **insight_plan** | Consequential work — ranked patterns/skills/tools + outcome evidence |
| insight_task | Multi-step work (`open` / `close`) |
| insight_experience | After events/fixes |
| insight_cycle | Explicit deep analysis |
| insight_forge | Lattice → maps/playbooks |
| insight_hygiene | Decay fabric noise; densify links |

Set `log=true` on perceive (or use experience) so the **next** session is faster.
When closing a planned task, pass only the `used_pattern_ids` actually applied so future
plans learn from real success/failure rather than similarity.

### How to read a perceive card

1. `usable` — if false, gather concrete observations; do not invent root cause  
2. `lever` — variable to measure/intervene on  
3. Top **rule** match + `action_hint` — act here first  
4. Lived echoes + hops — prior events/tasks  

## Stance

1. Recall before rediscovery  
2. Name the **actual variable**  
3. Prefer structural rules over scenic detail  
4. Observation ≠ inference  
5. Separate DBs per trust boundary  
6. Never paste raw credentials  

## SOUL fragment (optional)

```markdown
## Pattern recognition (Hermes Insight)
Default tool: insight_perceive. Before hard debugging or architecture, perceive.
If usable, act on lever + top rule + action_hint. Log meaningful scenes (log=true).
Use insight_task for multi-step work. If usable is false, gather observations first.
```

## CLI / Python

```bash
hermes-insight bootstrap
hermes-insight perceive "situation" -o "fact" --log
```

```python
from hermes_insight import HermesInsight
lat = HermesInsight()
print(lat.perceive("…", log_experience=True)["card"])
```

## Docs

| Doc | Use |
|-----|-----|
| **[references/AGENT-GUIDE.md](references/AGENT-GUIDE.md)** | Deep agent manual |
| [docs/ABILITY.md](../../docs/ABILITY.md) | Short ability card |
| [docs/EXPERIENCE.md](../../docs/EXPERIENCE.md) | Experience layer |
| [SECURITY.md](../../SECURITY.md) | Privacy |

https://github.com/PabloTheThinker/hermes-insight
