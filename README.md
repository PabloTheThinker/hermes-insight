# Hermes Insight

**Pattern recognition ability for AI agents** — a local structural lattice that matches, links, distills, and learns from experience.

Standalone Python library + CLI. **No cloud dependency.** Optional [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill + native plugin.

> **Not an official Nous Research product.** Independent companion for the Hermes community.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Why

Agents are strong at next-token reasoning and weak at **durable structural memory**:

- same failure rediscovered every session  
- no “what is the actual variable?”  
- no lived time binding events → rules  

Hermes Insight is that missing layer: **encode → match → link → distill → perceive → reinforce**.

---

## 30-second ability

```bash
pip install -e ".[dev]"   # or: pip install hermes-insight
export HERMES_INSIGHT_DB=./my-insight.db

hermes-insight bootstrap
hermes-insight perceive "two workers share one bot token; long-poll conflicts" \
  -o "409 from getUpdates" --log
```

```python
from hermes_insight import HermesInsight

lat = HermesInsight(db_path="./my-insight.db")
lat.bootstrap()
print(lat.perceive(
    "two workers share one bot token; long-poll conflicts",
    observations=["409 from getUpdates"],
    log_experience=True,
)["card"])
```

Returns: **lever**, **top structures**, **lived echoes**, **action hint**, **`usable`** flag.

---

## Install on any Hermes agent

```bash
./scripts/install_for_hermes.sh
# named agent / profile:
HERMES_HOME=~/.hermes/profiles/myagent ./scripts/install_for_hermes.sh --agent myagent --tier worker
```

| Tool | Role |
|------|------|
| **`insight_perceive`** | Primary ability — lever + matches + hint |
| `insight_task` | Open/close multi-step episodes |
| `insight_experience` | Log events; auto-link to patterns |
| `insight_recall` | Fast-only recall |
| `insight_cycle` | Deep multi-lens cycle |
| `insight_forge` | Maps / playbooks / invention seeds |
| `insight_hygiene` | Decay fabric noise + densify links |

Doctrine: [docs/ABILITY.md](docs/ABILITY.md) · [docs/EXPERIENCE.md](docs/EXPERIENCE.md)

**Loop:** `perceive` → act on hint → `experience` / task close → next recall is smarter.

---

## Production check

```bash
pip install -e ".[dev]"
pytest -q
bash scripts/check_isolation.sh
python3 scripts/production_e2e.py
```

---

## Privacy

- Local SQLite only; separate DB per agent compartment  
- Scrubber redacts secret-shaped strings and skips `.env`  
- Public tree must pass `scripts/check_isolation.sh`  
- Session auto-log only records **failed/interrupted** turns (not every chat)  
- See [SECURITY.md](SECURITY.md)

---

## Status

**0.7.4** — perceive ability, experience layer, structural priors, mesh/network starters, session-noise hygiene, any-agent install, public isolation gate.

## License

MIT © Pablo Navarro
