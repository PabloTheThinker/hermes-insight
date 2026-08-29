<p align="center">
  <img src="https://img.shields.io/badge/Hermes-Insight-0A0A0A?style=for-the-badge&labelColor=111111" alt="Hermes Insight">
</p>

# Hermes Insight

<p align="center">
  <a href="https://github.com/PabloTheThinker/hermes-insight/blob/main/docs/AGENT-GUIDE.md"><img src="https://img.shields.io/badge/Docs-Agent%20Guide-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://github.com/PabloTheThinker/hermes-insight/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Companion%20for-Hermes%20Agent-blueviolet?style=for-the-badge" alt="Hermes Agent"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/PabloTheThinker/hermes-insight/releases"><img src="https://img.shields.io/github/v/release/PabloTheThinker/hermes-insight?style=for-the-badge&label=Release" alt="Release"></a>
</p>

<p align="center">
  <b>Pattern recognition ability for AI agents</b> — a local structural lattice that matches, links, distills, and learns from experience.
</p>

**Hermes Insight** is the missing cognition layer for tool-using agents: durable **structure**, not just chat history. Agents encode situations as patterns, match them multi-lens, name the controlling **lever**, bind **lived events** to rules, and reinforce what actually worked — so the next session does not rediscover the same failure.

Standalone Python library + CLI. **Zero cloud dependency.** Optional native plugin and skill for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

> **Not an official [Nous Research](https://nousresearch.com) product.** Independent open-source companion for the Hermes community. Hermes® / Hermes Agent are trademarks of their respective owners.

<table>
<tr><td><b>One-call ability</b></td><td><code>insight_perceive</code> — lever, top structures, lived echoes, action hint, <code>usable</code> flag.</td></tr>
<tr><td><b>Experience-grounded plan</b></td><td><code>insight_plan</code> — rank rules, skills, and local affordances using explicit success/failure evidence.</td></tr>
<tr><td><b>Lived time</b></td><td>Events, episodes, and tasks auto-link to structural rules so experience compounds across sessions.</td></tr>
<tr><td><b>Structural priors</b></td><td>Rules and starters outrank random source-file noise; thin queries refuse instead of hallucinating.</td></tr>
<tr><td><b>Any Hermes seat</b></td><td>Install script for default home or any profile — separate SQLite DB per trust boundary.</td></tr>
<tr><td><b>Local-only</b></td><td>No network in the core path. Scrubber redacts secret-shaped strings. Isolation gate for public trees.</td></tr>
<tr><td><b>Agent-native docs</b></td><td>Deep <a href="docs/AGENT-GUIDE.md">Agent Guide</a> so a new Hermes agent can learn what this is and how to work.</td></tr>
</table>

---

## Quick Install

### Library + CLI

```bash
git clone https://github.com/PabloTheThinker/hermes-insight.git
cd hermes-insight
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optional environment:

```bash
export HERMES_INSIGHT_DB=./my-insight.db
export HERMES_INSIGHT_AGENT_ID=default
```

### Hermes Agent plugin (any seat)

```bash
./scripts/install_for_hermes.sh

# Named agent / profile:
HERMES_HOME=~/.hermes/profiles/myagent \
  ./scripts/install_for_hermes.sh --agent myagent --tier worker
```

Then reload Hermes so `insight_*` tools appear. The installer **merges** `hermes-insight` into `plugins.enabled` — it does not wipe your existing plugin list.

---

## Getting Started

### 30-second ability

```bash
hermes-insight bootstrap
hermes-insight perceive "two workers share one bot token; long-poll conflicts" \
  -o "409 from getUpdates" --log
hermes-insight observe environment --root .
hermes-insight plan "stabilize the duplicate-consumer failure" \
  -o "409 from getUpdates"
hermes-insight learn --min-support 3       # inspect recurring typed workflows
```

```python
from hermes_insight import HermesInsight

lat = HermesInsight(db_path="./my-insight.db")
lat.bootstrap()
card = lat.perceive(
    "two workers share one bot token; long-poll conflicts",
    observations=["409 from getUpdates"],
    log_experience=True,
)
print(card["card"])
print(card["action_hint"], "usable=", card["usable"])
```

### CLI cheatsheet

```bash
hermes-insight bootstrap              # seed agent-field starter rules
hermes-insight perceive "situation" -o "fact" --log
hermes-insight recall "query"
hermes-insight attune monotropic     # trait plate; not a diagnosis
hermes-insight remember "durable fact" --pointer "user.md#heading"
hermes-insight hygiene                # decay fabric noise + densify links
hermes-insight stats
hermes-insight forge                  # maps / playbooks from the lattice
hinsight perceive "…"                 # short alias
```

### Default agent loop

```text
observe env → recall → perceive → plan? → task open → typed events → task close → learn
    │            │         │         │         │             │              │         │
 current      memory    lever/rule  route   boundary      evidence       credit   recurrence
```

| Tool | Role |
|------|------|
| **`insight_perceive`** | Primary ability — lever, structures, hint, `usable` |
| **`insight_plan`** | Ranked rules/skills/affordances + auditable outcome evidence |
| **`insight_observe`** | Typed agent/tool events or scrubbed environment snapshots + deltas |
| **`insight_learn`** | Recurring workflow induction across distinct tasks, with counterexamples |
| `insight_task` | Open/close multi-step episodes (`task_id`) |
| `insight_experience` | Log events; auto-link to patterns |
| **`insight_recall`** | Associative retrieve — working set + `usable` |
| `insight_attune` | Cognitive plate — swappable recall/perceive/plan mindset |
| `insight_remember` | Compact durable fact / engram |
| `insight_cycle` | Deep multi-lens cycle |
| `insight_forge` | Lattice → maps / playbooks / invention seeds |
| `insight_hygiene` | Decay unused fabric; densify structural links |
| `insight_bootstrap` | Seed missing starter rules |
| `insight_feedback` | Reinforce or weaken patterns after real outcomes |

**New agents:** read the **[Agent Guide](docs/AGENT-GUIDE.md)** once — ontology, pipeline, doctrine, install, examples, anti-patterns.

---

## Why this exists

Language models are strong at next-token reasoning and weak at **durable structural memory**:

| Without Insight | With Insight |
|-----------------|--------------|
| Same failure every session | Lived events link to the rule that fixed it |
| Scenic root-cause stories | Named **lever** + scored structural prior |
| Skill dump / wrong procedure | Routing priors and rule-first match |
| Multi-agent bleed | Separate DBs + isolation starters |
| “I think I’ve seen this” | Scores, hops, and an honest `usable` flag |

Foundation pipeline:

```text
encode → match → link → distill → perceive → reinforce
```

---

## How it works

### Foundations

1. **Pattern lattice** — SQLite + FTS5 graph of rules, skills, events, tasks, tools, agents, synthesis nodes  
2. **Hybrid match** — template · prototype · feature · IDF, with structural kind priors (rules up, bare filenames down)  
3. **Candidate pool** — FTS + structural shortlist so large fabric dumps stay fast  
4. **Distill** — controlling variable (*lever*), refined from strong top matches  
5. **Experience layer** — events / episodes / tasks with `instance_of`, `experienced_as`, `next` links
5b. **Recall layer** — spreading activation + dual-process working set + compact `fact` engrams  
6. **Starters** — bootstrap agent-field priors (credentials, cache, isolation, retry storms, skill routing, mesh/DNS, …)  
7. **Hygiene** — decay unused fabric; densify links; weaken session-auto noise  
8. **Experience-grounded planning** — rank workflows from relevance + explicitly attributed task outcomes
9. **Native observation layer** — provenance-rich events and metadata-only workspace snapshots, with no AgentDrive dependency
10. **Evidence-gated induction** — repeated ordered workflows become reviewable sequence candidates only after independent task support

### Perceive card (what you act on)

1. `usable` — if false, gather concrete observations; do not invent root cause  
2. `lever` — variable to measure and intervene on  
3. Top **rule** + `action_hint` — operational next step  
4. Lived echoes + hops — prior events and related nodes  

### Privacy model

- Local SQLite only; **one DB per trust boundary** (house ≠ client)  
- Scrubber redacts secret-shaped strings; skips `.env`-class paths on ingest  
- Session hooks log **failed/interrupted** turns only — not every completed chat  
- Public trees must pass `scripts/check_isolation.sh`  
- Full policy: [SECURITY.md](SECURITY.md)

---

## Hermes Agent integration

| Piece | Path / role |
|-------|-------------|
| Native plugin | `hermes_plugin/hermes_insight_plugin/` → `$HERMES_HOME/plugins/hermes-insight/` |
| Skill | `skills/hermes-insight/` (`SKILL.md`, `HOW-IT-WORKS.md`, `AGENT-GUIDE.md`) |
| Installer | `scripts/install_for_hermes.sh` |
| Primary tool | `insight_perceive` |
| Hermespace organ | `HermesInsight.perceive_card(goal, load="mid")` — soft-import, not a MemoryProvider |

Optional SOUL / system fragment:

```markdown
## Pattern recognition (Hermes Insight)
Default tool: insight_perceive. Before hard debugging or architecture, perceive.
If usable, act on lever + top rule + action_hint. Log meaningful scenes (log=true).
Use insight_task for multi-step work. If usable is false, gather observations first.
Separate Insight DBs per trust boundary. Never store raw credentials.
```

Config sketch:

```yaml
plugins:
  enabled:
    - hermes-insight          # among your existing entries
  entries:
    hermes-insight:
      agent_id: myagent
      agent_tier: worker      # worker | conductor | client | …
      db_path: /path/to/myagent.insight.db
```

Env overrides: `HERMES_INSIGHT_DB`, `HERMES_INSIGHT_AGENT_ID`, `HERMES_INSIGHT_AGENT_TIER`.

---

## Documentation

| Document | What’s covered |
|----------|----------------|
| **[Agent Guide](docs/AGENT-GUIDE.md)** | Deep manual for Hermes agents — ontology, pipeline, doctrine, install, examples |
| **[Experience-grounded intuition](docs/INTUITION.md)** | Research, AgentDrive comparison, planner design, and roadmap |
| [Ability](docs/ABILITY.md) | Short ability card |
| [Experience](docs/EXPERIENCE.md) | Tasks, events, recall loop |
| [Recall](docs/RECALL.md) | Science-grounded retrieve organ + remember |
| [Mindset](docs/MINDSET.md) | Cognitive plates (swappable trait mindsets) |
| [Security](SECURITY.md) | Privacy, compartments, isolation |
| [Contributing](CONTRIBUTING.md) | Dev setup and PR hygiene |
| [Changelog](CHANGELOG.md) | Version history |
| [Community](docs/COMMUNITY.md) | Positioning for humans |

---

## Development

```bash
pip install -e ".[dev]"
pytest -q
bash scripts/check_isolation.sh
python3 -m compileall -q src hermes_plugin
# optional local-only (indexes ~/.hermes — not in CI):
python3 scripts/production_e2e.py
```

| Layout | Purpose |
|--------|---------|
| `src/hermes_insight/` | Core library (store, match, distill, experience, ability, forge, CLI) |
| `hermes_plugin/` | Native Hermes plugin |
| `skills/hermes-insight/` | Agent skill + how-it-works + Agent Guide |
| `scripts/` | Install, E2E, isolation gate |
| `tests/` | Unit tests |
| `docs/` | Human + agent documentation |
| `examples/` | Minimal quickstart |

Requires **Python 3.10+**. Core runtime dependencies: none beyond the standard library (+ pytest for dev).

---

## Status

**0.9.x** — production-shaped alpha for companion use:

- `perceive` ability and experience layer  
- **associative `recall`** — dual-process working set, spreading activation, `usable`
- `remember` compact engrams (not a MemoryProvider)
- `plan` ability with explicit applied-pattern outcome attribution
- typed events and environment snapshots that ground plans in current workspace state
- recurring workflow induction with distinct-task support, Wilson confidence, retained failures, and no automatic skill writes
- Structural match priors and candidate-pool performance  
- Mesh/network starters and session-noise hygiene  
- Any-agent install path and public isolation gate  

See [CHANGELOG.md](CHANGELOG.md) and [Releases](https://github.com/PabloTheThinker/hermes-insight/releases).

---

## Contributing

Issues and PRs welcome. Please:

1. Keep the public tree free of operator/host fingerprints (`bash scripts/check_isolation.sh`)  
2. Add or update tests for behavioral changes  
3. Prefer skills and docs over one-off prose  

Details: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT](LICENSE) © Pablo Navarro

---

## Related

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — the agent runtime this companion targets  
- [Hermes Agent docs](https://hermes-agent.nousresearch.com/docs/) — official documentation  
- [agentskills.io](https://agentskills.io) — open skill standard (skill packaging compatible in spirit)

<p align="center">
  <sub>When in doubt: <code>insight_perceive</code>.</sub>
</p>
