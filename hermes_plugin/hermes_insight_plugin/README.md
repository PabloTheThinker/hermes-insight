# Hermes Insight plugin

Native Hermes Agent plugin for the **Hermes Insight** pattern-processing harness.

## Install

```bash
pip install hermes-insight   # or: pip install -e /path/to/hermes-insight

mkdir -p "$HERMES_HOME/plugins"
cp -R hermes_plugin/hermes_insight_plugin "$HERMES_HOME/plugins/hermes-insight"
```

Enable (opt-in list):

```yaml
# $HERMES_HOME/config.yaml
plugins:
  enabled:
    - hermes-insight
  entries:
    hermes-insight:
      # optional multi-agent compartment
      agent_id: default
      # optional override
      # db_path: ${HERMES_HOME}/memories/hermes-insight/insight.db
```

Restart the Hermes process / gateway after enabling.

## Tools

| Tool | Purpose |
|------|---------|
| `insight_cycle` | Full brief (match · distill · trajectory · novelty) |
| `insight_ingest` | Catalogue title/body or one file |
| `insight_ingest_tree` | Bulk code-aware tree ingest |
| `insight_match` | Recognition only |
| `insight_distill` | Actual variable |
| `insight_feedback` | Reinforce / weaken |
| `insight_stats` | Counts + path |
| `insight_evolve` | Evolution tick |

Slash: `/insight stats` · `/insight cycle <query>` (when command registration is supported).

## Notes

- Independent companion project — **not** an official Nous Research product.
- Per-profile DB defaults to `$HERMES_HOME/memories/hermes-insight/insight.db`.
- Multi-agent: set `agent_id` or `--agent` / `HERMES_INSIGHT_AGENT_ID`.
