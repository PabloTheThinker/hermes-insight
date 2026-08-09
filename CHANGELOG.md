# Changelog

## 0.7.2 — 2026-08-09

- **Speed:** `candidate_pool` (FTS + structural shortlist) — perceive ~2s → ~110ms on 600-node lattices
- **Fabric hygiene:** `decay_fabric_noise` + `insight_hygiene` / CLI `hygiene`
- **Auto experience:** plugin `on_session_end` logs completed/failed turns into the lattice
- **Bootstrap:** seed when starters missing (not merely when DB non-empty); densify rate-limited
- **Levers:** domain-conditioned priors in distill
- Less disk thrash (touch top-3 only); deep cycle only when truly weak

## 0.7.1 — 2026-08-09

- Quality pass: fix garbage levers, dedupe file dumps, densify links, thin-query honesty, skill-routing starter
- `usable` flag on perceive

## 0.7.0 — 2026-08-09

- `perceive` ability + `insight_perceive` primary tool
- Structural match priors; public SECURITY/CONTRIBUTING; isolation gate

## 0.6.0 — 2026-08-09

- Experience layer (recall/task/experience/connect) + install_for_hermes.sh

## 0.5.x — 2026-08-09

- Agent-field ontology, fabric index, forge, production E2E

## 0.1.0–0.4.0 — 2026-08-09

- Core cycle, multi-agent, plugin, forge products
