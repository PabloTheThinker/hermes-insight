# Changelog

## 0.8.0 — 2026-08-10

- **Experience-grounded planner** — `insight_plan` ranks rules, skills, workflows, and
  local environment affordances with transparent score components
- **Explicit outcome attribution** — task close accepts `used_pattern_ids` and records
  `applied` edges, separating actual use from similarity
- **Calibrated reliability** — successful and failed applications update a conservative,
  sample-size-shrunk reliability score
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
