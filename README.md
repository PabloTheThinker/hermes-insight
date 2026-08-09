# Hermes Insight

**Pattern harness for the AI agent / model field** — agents, models, tools, skills, multi-agent compartments, fabric index, Pattern Forge, and an **experience layer** so any Hermes agent can connect tasks & events to structure faster.

Standalone Python library + CLI. **No cloud dependency.** Optional [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill + native plugin.

> **Name note:** *Hermes Insight* is an independent companion for the Hermes community. It is **not** an official Nous Research product.

Built for what Hermes/agent builders keep asking for: **walkable structure**, **multi-agent compartments**, **skill/model routing signal**, **fleet maps**, a **forge loop**, and **lived experience → pattern links** so agents stop rediscovering the same failure every session. See [docs/COMMUNITY.md](docs/COMMUNITY.md) · [docs/EXPERIENCE.md](docs/EXPERIENCE.md).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Production check

```bash
pip install -e ".[dev]"
python3 scripts/production_e2e.py
```

## Install on any Hermes agent (one command)

```bash
./scripts/install_for_hermes.sh
# profile / client compartment:
HERMES_HOME=~/.hermes/profiles/myagent ./scripts/install_for_hermes.sh --agent myagent
```

Installs package + skill + plugin, merges config safely, bootstraps starter patterns.

### Agent loop (the product)

```text
insight_recall  →  insight_task open  →  insight_experience*  →  insight_task close
                         └──────── insight_cycle (if novel) ────────┘
```

| Tool | Job |
|------|-----|
| `insight_recall` | Fast priors + lived echoes + hops **before** acting |
| `insight_task` | Open/close task episodes (`task_id` chains events) |
| `insight_experience` | Log event/episode; **auto-connect** to matching patterns |
| `insight_connect` | Explicit “same shape as X” or free-text auto-link |
| `insight_cycle` | Deep multi-lens cycle when the scene is novel |
| `insight_forge` | Turn lattice into maps / playbooks / invention seeds |

---

## Why this exists

Pattern recognition is not “one embedding distance.” Agents need durable structural memory with lateral hops **and** lived time. Hermes Insight is that harness (SPP-inspired — see [`docs/RESEARCH.md`](docs/RESEARCH.md)). Not a diagnostic tool.

---

## Quick start

```bash
git clone https://github.com/PabloTheThinker/hermes-insight.git
cd hermes-insight
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

hermes-insight demo
export HERMES_INSIGHT_DB=./my-insight.db
hermes-insight bootstrap
hermes-insight recall "two gateway workers share one bot token"
hermes-insight task open --name fix-conflict --goal "getUpdates 409"
# … work …
hermes-insight experience "saw conflict" "second consumer still polling" --task-id TID
hermes-insight task close --task-id TID --outcome fixed --summary "single consumer rule"
```

```python
from hermes_insight import HermesInsight

lat = HermesInsight(db_path="./my-insight.db")
lat.bootstrap()
print(lat.recall("dependency errors cascading after deploy")["brief"])
t = lat.open_task("stop retry storm", goal="pages after deploy")
lat.experience("retries without jitter", "amplified load", task_id=t["task_id"])
lat.close_task(t["task_id"], outcome="fixed", summary="jitter + circuit breaker")
```

---

## Pattern Forge + server fabric

```bash
hermes-insight index-server
hermes-insight forge
```

---

## Status

`0.6.0` — experience layer (recall/task/experience/connect), any-agent install script, starter bootstrap, expanded plugin tools.

## License

MIT © Pablo Navarro
