# Changelog

## Unreleased

## 0.9.0 — 2026-08-26

- **Associative recall layer** — `insight_recall` returns a budgeted working set
  with dual-process lanes (rules / facts / echoes / contradictions), spreading
  activation, encoding-specificity cues, and a feeling-of-knowing `usable` flag
- **Compact engrams** — `insight_remember` stores one scrubbed `kind=fact` claim
  with an optional artifact pointer; never file contents or chat dumps
- Retrieval practice touches recalled nodes; recall still never creates `applied`
  outcome credit
- Docs: [RECALL.md](docs/RECALL.md) maps human and neural-network memory research
  onto the lattice

## 0.8.x — unreleased follow-ups

- Drop invalid Hermes hook `session_end`; keep `on_session_end` only
- `plugin.yaml` declares `provides_hooks`, advisory `python_dependencies`, and
  `config_schema` for `agent_id` / `db_path` / `agent_tier`
- Locked Space cable: `HermesInsight.perceive_card(goal, load="mid")` returns only
  `ok, usable, lever, rule, action_hint, card, skipped, reason` (high/protect skips)
- CI: `pytest -q`, isolation gate, `compileall` (not `production_e2e.py`)
- Package docstring: optional organ, not “skill/plugin later”

## 0.8.0 — 2026-08-10

- **Experience-grounded planner** — `insight_plan` ranks rules, skills, workflows, and
  local environment affordances with transparent score components
- **Explicit outcome attribution** — task close accepts `used_pattern_ids` and records
  `applied` edges, separating actual use from similarity
- **Calibrated reliability** — successful and failed applications update a conservative,
  sample-size-shrunk reliability score
- **Native observation layer** — typed agent/tool/skill events plus scrubbed environment
  snapshots and structural deltas, stored in the existing Insight lattice
- **Environment-grounded plans** — plans identify the workspace snapshot that produced
  their evidence, with no AgentDrive runtime or storage integration
- **Evidence-gated workflow induction** — `insight_learn` mines ordered typed-event
  sequences across distinct tasks, retains counterexamples, and assigns candidate or
  verified-local lifecycle using conservative outcome bounds
- **Hermes-native skill rewrite** — progressive-disclosure frontmatter, acquisition
  procedure, pitfalls, verification, and reviewed pattern-to-skill promotion guidance
- **SQLite production hardening** — bounded lock wait, WAL, and normal synchronous mode
- **Explicit-only outcome credit** — retrieval and similarity links never receive task
  success/failure reinforcement unless listed in `used_pattern_ids`
- **Deterministic task chains** — per-task last-event cursors preserve sequential `next`
  links without ranking events by mutable strength timestamps
- **Reliable Hermes skill routing** — skill visibility now requires the plugin's
  `hermes_insight` toolset and includes the canonical slash-command acquisition path
- **Safe plugin setup** — config merge parses actual `plugins.enabled`, preserves unrelated
  configuration, sanitizes agent ids, and creates a minimal config for fresh profiles
- **Supported teaching surface** — removed obsolete plugin prompt-injection hooks; the
  progressively disclosed filesystem skill is authoritative
- **Research deep dive** — pattern recognition, agent memory/skill research, AgentDrive
  comparison, integration boundary, and prioritized community roadmap
- CLI, Python, Hermes plugin, skill, tests, and docs updated for the planning loop

## 0.7.4 — 2026-08-09

- **Session auto-log dampened** — only failed/interrupted turns file episodes; completed turns bump a counter only
- **Mesh/network starters** — ghost peer after reboot, split DNS vs mesh path, single-writer shared state
- **Bootstrap fills missing starter titles** without full force re-seed
- **Recall** hides bulk session-turn noise unless the query is about sessions
- **Hygiene** can weaken old session-auto episodes (`prune_session_auto`)
- Lever title rules for mesh/dns/lock; public docs/README refresh

## 0.7.3 — 2026-08-09

- Lever refinement from strong top match; prefer rules over skill inventory
- Hop `via` labels; fresher last_brief; agent_tier from config

## 0.7.2 — 2026-08-09

- candidate_pool speed (~110ms); fabric decay; domain lever priors; gated densify

## 0.7.1 — 2026-08-09

- Quality pass: garbage levers, dedupe, densify, thin-query honesty

## 0.7.0 — 2026-08-09

- `perceive` ability + experience layer + public isolation

## 0.6.0 and earlier

- Experience APIs, forge, fabric index, multi-agent, core cycle
