# Hermes Insight plugin

Native Hermes Agent plugin for **pattern recognition**.

## Install

```bash
pip install hermes-insight   # or: pip install -e /path/to/hermes-insight

# recommended one-shot
./scripts/install_for_hermes.sh

# manual
mkdir -p "$HERMES_HOME/plugins"
cp -R hermes_plugin/hermes_insight_plugin "$HERMES_HOME/plugins/hermes-insight"
```

```yaml
# $HERMES_HOME/config.yaml
plugins:
  enabled:
    - hermes-insight   # merge into existing list
  entries:
    hermes-insight:
      agent_id: default
      # db_path: ${HERMES_HOME}/memories/hermes-insight/insight.db
```

Restart Hermes / gateway after enabling.

## Primary tool

| Tool | Purpose |
|------|---------|
| **`insight_perceive`** | Pattern recognition ability — lever + matches + action hint |
| **`insight_plan`** | Ranked patterns, skills, and local affordances with outcome evidence |
| **`insight_observe`** | Typed events or scrubbed workspace snapshots and deltas |
| `insight_task` | Open/close task episodes |
| `insight_experience` | Log event; auto-connect |
| `insight_recall` | Fast recall only |
| `insight_cycle` | Deep multi-lens cycle |
| `insight_forge` | Maps / playbooks / seeds |
| `insight_bootstrap` | Seed starter patterns |

Slash (when supported): `/insight stats` · `/insight perceive <q>` ·
`/insight plan <q>` · `/insight recall <q>` · `/insight cycle <q>`

## Notes

- Independent companion — **not** an official Nous product  
- Separate DB per agent compartment  
- See `docs/ABILITY.md` and `SECURITY.md`
