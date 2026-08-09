# Hermes Insight — optional Hermes plugin skeleton

This directory is a **thin adapter** target for Hermes Agent plugin discovery.
The cognitive engine lives in the `hermes-insight` Python package, not here.

## Install (when you wire it)

```bash
pip install hermes-insight   # or editable path
cp -R hermes_plugin/hermes_insight_plugin "$HERMES_HOME/plugins/hermes_insight"
```

Then follow current Hermes docs for plugin enablement (`hermes plugins`, config
keys, restart/reload). Plugin surfaces change across Hermes versions — keep this
adapter thin and call `hermes_insight.HermesInsight` only.

## Intended tools

| Tool | Maps to |
|------|---------|
| `pattern_cycle` | `HermesInsight.cycle` |
| `pattern_ingest` | `HermesInsight.ingest` |
| `pattern_match` | `HermesInsight.match` |
| `pattern_feedback` | `HermesInsight.feedback` |

## Config (suggested)

```yaml
# under $HERMES_HOME/config.yaml — illustrative only
plugins:
  hermes_insight:
    db_path: ${HERMES_HOME}/memories/hermes-insight.db
```

## Status

v0.1 ships the **library + skill**. This folder documents the plugin shape so
Hermes users can complete wiring against their installed Hermes API without a
core fork.
