# Contributing

Thanks for helping Hermes Insight stay a clean companion for the Hermes Agent community.

## Basics

1. Fork + branch from `main`
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install -e ".[dev]"`
4. `pytest -q`
5. `./scripts/check_isolation.sh`
6. Open a PR with a short “why” and test proof

## Design bar

- **Narrow public API** — prefer extending `HermesInsight.perceive` / experience over new core tools
- **Deterministic core** — no required cloud calls
- **Scrub by default** — never land host fingerprints
- **Tests for match/distill/perceive** when changing recognition behavior
- **Plugin stays thin** — handlers call the library; logic lives in `src/hermes_insight/`

## Not in scope for core PRs

- Vendor SaaS lock-ins
- Operator-specific house paths or business SKUs
- Forking Hermes Agent core (ship as plugin/skill)

## License

MIT. By contributing you agree your changes are MIT-licensed.
