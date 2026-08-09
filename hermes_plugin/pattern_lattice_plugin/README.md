# Pattern Lattice — optional Hermes plugin skeleton

This directory is a **thin adapter** target for Hermes Agent plugin discovery.
The cognitive engine lives in the `pattern-lattice` Python package, not here.

## Install (when you wire it)

```bash
pip install pattern-lattice   # or editable path
cp -R hermes_plugin/pattern_lattice_plugin "$HERMES_HOME/plugins/pattern_lattice"
```

Then follow current Hermes docs for plugin enablement (`hermes plugins`, config
keys, restart/reload). Plugin surfaces change across Hermes versions — keep this
adapter thin and call `pattern_lattice.PatternLattice` only.

## Intended tools

| Tool | Maps to |
|------|---------|
| `pattern_cycle` | `PatternLattice.cycle` |
| `pattern_ingest` | `PatternLattice.ingest` |
| `pattern_match` | `PatternLattice.match` |
| `pattern_feedback` | `PatternLattice.feedback` |

## Config (suggested)

```yaml
# under $HERMES_HOME/config.yaml — illustrative only
plugins:
  pattern_lattice:
    db_path: ${HERMES_HOME}/memories/pattern-lattice.db
```

## Status

v0.1 ships the **library + skill**. This folder documents the plugin shape so
Hermes users can complete wiring against their installed Hermes API without a
core fork.
