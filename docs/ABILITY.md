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
        ├─ recognition-cued recall of events/tasks bound to those patterns
        ├─ connect dots (experienced_as / instance_of, never applied credit)
        ├─ grow Hebbian pathways (potentiate binds, sibling echoes, local sequences)
        ├─ action hint (mentions a lived echo or grown pathway when one exists)
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
| Recognition-cued recall | recognized rules harvest bound events/tasks (`dots`) |
| Pathway growth | repeated dots potentiate binds and grow local `sequence` candidates |
| Lever focus | distill actual variable with prior vocabulary |
| Transfer | analogy / hops via graph neighbors |
| Reinforcement | task close + feedback strengthens useful nodes |
| Environment grounding | typed snapshots and `observed_in` event links |
| Recurrence | ordered workflows supported by distinct tasks and counterexamples |

## Agent doctrine (paste into SOUL or skill)

```markdown
## Pattern recognition
Before hard debugging or architecture choices, call `insight_perceive`.
Trust the lever + top structural match when score ≥ 0.35; verify when weaker.
Use `insight_observe` for material environment/tool/skill transitions.
Use insight_task open/close around multi-step work and credit only applied patterns.
After at least three comparable tasks, inspect `insight_learn` without auto-promoting.
```

## Related tools

| Tool | When |
|------|------|
| **insight_perceive** | Default ability |
| insight_plan | Outcome-aware route grounded in the current environment |
| insight_observe | Typed event or environment snapshot |
| insight_learn | Evidence-gated recurring workflow induction |
| **insight_recall** | Associative retrieve — working set + `usable` |
| insight_attune | Set the active cognitive plate (trait mindset, not a diagnosis) |
| insight_remember | Compact durable fact / engram |
| insight_cycle | Explicit deep analysis |
| insight_experience / task | Bind time |
| insight_forge | Turn lattice into products |
