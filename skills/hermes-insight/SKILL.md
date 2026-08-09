---
name: hermes-insight
description: "Use when an agent needs pattern recognition — perceive situations, distill levers, connect experience, match structures."
version: "0.7.4"
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

## When to load

- Before hard debugging / architecture / recurring failures  
- Multi-step tasks that should leave structural memory  
- “Same shape as X” / cross-domain rhyme  
- After failures and fixes  

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
```

Restart Hermes after enabling.

## Default ability

**Call `insight_perceive` first** with the situation (+ optional observations).

```text
insight_perceive → (optional) insight_task open → insight_experience* → insight_task close
```

| Tool | When |
|------|------|
| **insight_perceive** | Default — lever + structures + action hint |
| insight_task | Multi-step work (`open` / `close`) |
| insight_experience | After events/fixes |
| insight_cycle | Explicit deep analysis |
| insight_forge | Lattice → maps/playbooks |

Set `log=true` on perceive (or use experience) so the **next** session is faster.

## Stance

1. Recall before rediscovery  
2. Name the **actual variable**  
3. Prefer structural rules over scenic detail  
4. Observation ≠ inference  
5. Separate DBs per trust boundary  
6. Never paste raw credentials  

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

https://github.com/PabloTheThinker/hermes-insight  
`docs/ABILITY.md` · `docs/EXPERIENCE.md` · `SECURITY.md`
