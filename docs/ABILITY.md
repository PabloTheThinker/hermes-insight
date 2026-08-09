# Pattern recognition ability

How Hermes Insight becomes a **real ability** for any Hermes agent — not a pile of optional tools.

> **Deep manual for agents:** [AGENT-GUIDE.md](AGENT-GUIDE.md) — full ontology, pipeline, doctrine, install, examples.

## One call

```text
insight_perceive(situation, observations?, log?, deep?)
        │
        ├─ bootstrap starters if empty
        ├─ feature extract + synonym expand
        ├─ hybrid match (template · prototype · feature · IDF)
        ├─ structural priors (rules > random source files)
        ├─ distill controlling lever
        ├─ lived experience echoes + graph hops
        ├─ action hint
        └─ optional: log experience for next time
```

Python:

```python
from hermes_insight import HermesInsight

lat = HermesInsight()  # uses HERMES_INSIGHT_DB or ~/.hermes-insight
card = lat.perceive(
    "two workers share one bot token; long-poll conflicts",
    observations=["409 from getUpdates"],
    log_experience=True,
)
print(card["card"])
print(card["action_hint"])
```

CLI:

```bash
hermes-insight bootstrap
hermes-insight perceive "retries stampede origin after cache expiry" --log
```

## What “good recognition” means here

| Property | Implementation |
|----------|----------------|
| Multi-lens match | template + prototype + feature + hybrid |
| Structural preference | rules/prototypes boosted; bare filenames demoted |
| Lived time | experience events auto-link; recency boost |
| Lever focus | distill actual variable with prior vocabulary |
| Transfer | analogy / hops via graph neighbors |
| Reinforcement | task close + feedback strengthens useful nodes |

## Agent doctrine (paste into SOUL or skill)

```markdown
## Pattern recognition
Before hard debugging or architecture choices, call `insight_perceive`.
Trust the lever + top structural match when score ≥ 0.35; verify when weaker.
Log meaningful scenes (log=true or insight_experience) so next session is faster.
Use insight_task open/close around multi-step work.
```

## Related tools

| Tool | When |
|------|------|
| **insight_perceive** | Default ability |
| insight_recall | Fast-only (no deep, no log) |
| insight_cycle | Explicit deep analysis |
| insight_experience / task | Bind time |
| insight_forge | Turn lattice into products |
