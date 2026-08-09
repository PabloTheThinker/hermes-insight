# Hermes Agent integration

Hermes Insight is **standalone first**. Hermes integration is layered so any
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
mkdir -p "$HERMES_HOME/skills/cognition/hermes-insight"
cp skills/hermes-insight/SKILL.md \
  "$HERMES_HOME/skills/cognition/hermes-insight/SKILL.md"
```

Install the Python package into the same environment Hermes uses:

```bash
pip install -e /path/to/hermes-insight
# or: pip install hermes-insight  # once published to PyPI
```

Point the lattice at profile-scoped storage:

```bash
export HERMES_INSIGHT_DB="$HERMES_HOME/memories/hermes-insight.db"
```

In-session, Hermes can load the skill (`/skill hermes-insight` or auto-discovery)
and shell out to:

```bash
hermes-insight cycle "..." -o "observation one" -o "observation two"
hermes-insight ingest "title" "body" --domain code --tag x
hermes-insight feedback p_xxx
```

Or use the Python API inside `execute_code` if preferred.

## Phase 2 — Optional plugin skeleton

Directory: `hermes_plugin/hermes_insight_plugin/`

Intended install:

```bash
cp -R hermes_plugin/hermes_insight_plugin \
  "$HERMES_HOME/plugins/hermes_insight"
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
| default | `$HERMES_HOME/memories/hermes-insight.db` |
| named | `~/.hermes/profiles/<name>/memories/hermes-insight.db` |

Do not share lattices across clients or trust boundaries.

## What not to do

- Do not vendor operator machine paths into this repo  
- Do not open a Hermes core PR just to add this capability  
- Do not put secrets or personal data into example DBs committed to git  

## Verification checklist

- [ ] `hermes-insight demo` works in a clean venv  
- [ ] `pytest` green  
- [ ] `scripts/check_isolation.sh` green  
- [ ] Skill visible to Hermes after copy + reload  
- [ ] DB path under `$HERMES_HOME` for real use  
