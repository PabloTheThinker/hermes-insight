# Hermes Agent integration

Hermes Insight ships a native plugin plus a progressively disclosed Hermes skill. The
plugin owns precise execution and local SQLite state; the skill teaches the agent when
and how to use that capability.

## Install

```bash
./scripts/install_for_hermes.sh

# Named profile / trust compartment:
HERMES_HOME=~/.hermes/profiles/myagent \
  ./scripts/install_for_hermes.sh --agent myagent --tier worker
```

The installer:

1. installs the Python package into the selected Hermes environment;
2. copies the complete skill bundle (`SKILL.md` plus `references/`);
3. copies and enables the `hermes-insight` plugin without replacing other plugins;
4. creates a profile-scoped database and bootstraps starter patterns.

Restart Hermes after installation. Skill discovery is session-cached, so start a new
session (or explicitly invalidate the cache) before checking `/hermes-insight`.

## Hermes skill acquisition

Hermes sees the frontmatter name and short description in its session skill index. It
offers the skill only when the plugin's `hermes_insight` toolset is present, then loads
the full procedure with:

```text
skill_view(name="hermes-insight")
```

The deep reference remains unloaded until needed:

```text
skill_view(name="hermes-insight", file_path="references/AGENT-GUIDE.md")
```

The skill follows current Hermes Agent conventions: concise routing description,
cross-platform declaration, `When to Use`, prerequisites, procedure, pitfalls, and
verification. It teaches:

```text
observe → perceive → plan → task/events → attributed outcome → learn
```

## Profile isolation

| Profile | Default database |
|---|---|
| default | `$HERMES_HOME/memories/hermes-insight/insight.db` |
| named | `$HERMES_HOME/memories/hermes-insight/agents/<agent>.insight.db` |

Never share a writable lattice across clients or trust boundaries. Imported/community
content is not equivalent to local evidence.

## Production checks

```bash
python3 -m pytest -q
bash scripts/check_isolation.sh
python3 -m compileall -q src hermes_plugin
```

Then verify in a fresh Hermes session:

1. `insight_stats` reports the intended profile and database.
2. `insight_observe(mode="environment", root="<workspace>")` returns a snapshot.
3. A concrete `insight_perceive` is usable and a vague one abstains.
4. A task can record typed events and close with honest `used_pattern_ids`.
5. Repeated traces across distinct tasks appear in `insight_learn`; repeated events in one
   task do not fake support.

## Hermespace organ

Hermespace may soft-import Insight the way it soft-imports Cube. Feature-detect
the bounded helper — do not vendor this repo, and do not treat Insight as a
`MemoryProvider`:

```python
from hermes_insight import HermesInsight

if hasattr(HermesInsight, "perceive_card"):
    card = HermesInsight(db_path=db).perceive_card(goal, load="mid")
    # keys: ok, usable, lever, rule, action_hint, card, skipped, reason
```

High/protect load returns an empty card (`skipped=True`, `reason=high_load`).
The cable never dumps the lattice, never injects `perceive()["card"]`, and never
calls `insight_plan`.

## Boundaries

- No AgentDrive package, runtime, database, code import, or protocol dependency.
- No automatic Hermes skill writing, installation, execution, or publication.
- No raw credentials or unrestricted transcript ingestion.
- No cross-profile evidence sharing without a future explicit policy surface.
- Not a Hermes `MemoryProvider`. Hermespace must soft-import, not vendor.
