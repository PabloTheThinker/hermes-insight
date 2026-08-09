# Security & privacy

Hermes Insight is designed to run **on your machine** under your `HERMES_HOME`.

## What never belongs in this repository

- Absolute operator home paths
- Personal names, family, private business ops, client PII
- API keys, OAuth tokens, bot credentials, `.env` contents
- Internal hostnames, private mesh IPs, machine inventory
- Live agent memory databases or session transcripts with secrets

Before every public push:

```bash
./scripts/check_isolation.sh
pytest -q
```

## Runtime scrubbing

Ingest paths run through `hermes_insight.scrub`:

- Secret-shaped strings redacted
- Common absolute home prefixes neutralized
- `.env` / `secrets/` paths skipped by fabric indexer

Still: **do not paste raw credentials into tools or prompts.**

## Multi-agent compartments

Use a **separate DB per trust boundary**:

```text
$HERMES_HOME/memories/hermes-insight/insight.db              # default
$HERMES_HOME/memories/hermes-insight/agents/<id>.insight.db  # per agent
```

Never point a client agent at a personal/conductor lattice.

## Reporting a leak

Open a GitHub issue with **no secrets in the body** (describe class of leak only). Rotate any exposed credentials immediately.
