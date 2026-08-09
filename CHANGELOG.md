# Changelog

## 0.2.0 — 2026-08-09

- **Match quality:** IDF-weighted hybrid scores, synonym expansion, richer feature universe (tags/symbols/path)
- **Distill:** lever priors + noise suppression (stops generic `agent`/`user` traps)
- **Code-aware ingest:** `ingest_file` / `ingest_tree` with AST symbol extraction
- **Multi-agent compartments:** `agent_id` / tiers, separate DBs, registry
- **Native Hermes plugin:** tools `insight_*`, `plugin.yaml`, slash `/insight`
- CLI: `--agent`, `ingest-tree`, `register-agent`, `agents`
- Dogfood script against real Hermes Agent source trees
- Production E2E success gates on lever + match score

## 0.1.0 — 2026-08-09

- Initial public release as **Hermes Insight**
- Core cycle, SQLite+FTS5, skill pack, demo
