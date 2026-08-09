# Hermes Agent integration

Pattern Lattice is **standalone first**. Hermes integration is layered so any
agent host can use the library; Hermes gets a skill pack and an optional plugin.

## Principles (aligned with Hermes contribution norms)

- Prefer **skills** over core tools when instructions + CLI suffice  
- Ship host integrations as **standalone plugins**, not Hermes core PRs  
- Use `$HERMES_HOME` / profile paths — never hardcode machine homes  
- JSON tool boundaries; durable state under the active profile  

## Phase 1 — Skill (available now)

Install the skill markdown into the active Hermes skills tree:

```bash
# HERMES_HOME is your profile root (default ~/.hermes)
mkdir -p "$HERMES_HOME/skills/cognition/pattern-lattice"
cp skills/pattern-lattice/SKILL.md \
  "$HERMES_HOME/skills/cognition/pattern-lattice/SKILL.md"
```

Install the Python package into the same environment Hermes uses:

```bash
pip install -e /path/to/pattern-lattice
# or: pip install pattern-lattice  # once published to PyPI
```

Point the lattice at profile-scoped storage:

```bash
export PATTERN_LATTICE_DB="$HERMES_HOME/memories/pattern-lattice.db"
```

In-session, Hermes can load the skill (`/skill pattern-lattice` or auto-discovery)
and shell out to:

```bash
pattern-lattice cycle "..." -o "observation one" -o "observation two"
pattern-lattice ingest "title" "body" --domain code --tag x
pattern-lattice feedback p_xxx
```

Or use the Python API inside `execute_code` if preferred.

## Phase 2 — Optional plugin skeleton

Directory: `hermes_plugin/pattern_lattice_plugin/`

Intended install:

```bash
cp -R hermes_plugin/pattern_lattice_plugin \
  "$HERMES_HOME/plugins/pattern_lattice"
# restart Hermes / reload plugins per current Hermes docs
```

The skeleton documents hooks for:

- `register_tool` — `pattern_cycle`, `pattern_ingest`, `pattern_feedback`  
- optional `system_prompt_block` — short stance from `prompts.SYSTEM_PATTERN_OFFICER`  

Implement against the live Hermes plugin API on your installed version
(`hermes version` → docs → “Build a Hermes Plugin”). APIs move; keep the
**library** stable and the plugin thin.

## Profile isolation

| Profile | DB path example |
|---------|-----------------|
| default | `$HERMES_HOME/memories/pattern-lattice.db` |
| named | `~/.hermes/profiles/<name>/memories/pattern-lattice.db` |

Do not share lattices across clients or trust boundaries.

## What not to do

- Do not vendor operator machine paths into this repo  
- Do not open a Hermes core PR just to add this capability  
- Do not put secrets or personal data into example DBs committed to git  

## Verification checklist

- [ ] `pattern-lattice demo` works in a clean venv  
- [ ] `pytest` green  
- [ ] `scripts/check_isolation.sh` green  
- [ ] Skill visible to Hermes after copy + reload  
- [ ] DB path under `$HERMES_HOME` for real use  
