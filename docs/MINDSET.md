# Cognitive plates — swappable mindsets

Hermes Insight can retrieve with a **Cognitive Plate**: a named, inspectable
configuration of recall / perceive / plan knobs. The plate is a **trait
overlay**, not a diagnosis and not an identity.

The metaphor comes from [Sonny Jane Wise’s Neurodiversity Smorgasbord
(2024)](https://www.livedexperienceeducator.com/blog/theneurodiversitysmorgasbord):
you pick items from platters; **the plate can change**. That is the right
shape for an agent seat. Credit: Wise.

This is **not** “make the agent autistic / ADHD.” It is not a DSM label.
Skipped platters that would simulate distress or pathology: eating, sleep,
motor, stimming-as-tic, voice-hearing, mania / psychosis / hallucination.

> Recall doctrine: [RECALL.md](RECALL.md). Research map: [RESEARCH.md](RESEARCH.md).

## Axes (first slice)

Only platters that already map onto the lattice:

| Axis | Settings | Engine effect |
|------|----------|----------------|
| **Attention** | monotropic / balanced / polytropic | Spread hops, lateral inhibition, working-set size |
| **Memory** | semantic / balanced / episodic / procedural | Lane weights on rules, facts, echoes, sequences |
| **Time** | linear / balanced / cyclical | Recency half-life vs repeating `sequence` boost |
| **Sensory** | filter / balanced / sensitive | Thin-query bar and usable activation |
| **Processing** | gist / balanced / distill | Distill aggressiveness and brief density |

`load=monotropic` on the Hermespace `perceive_card` still means **protect /
skip**. That word on a plate means **attention style**, not load shedding.

## Named plates

| Name | Intent |
|------|--------|
| `balanced` | 0.9 recall/perceive/plan constants (default) |
| `monotropic` | Deep one thread: fewer hops, stronger inhibition, smaller set, semantic + linear |
| `polytropic` | Scan many rhymes: more hops, weaker inhibition, wider set, episodic + cyclical |
| `catalogue` | Novelty-sensitive distill: monotropic attention + sensitive input + cyclical time |
| `custom` | Any axis mix via `attune(..., attention=..., memory=...)` |

Persist the last plate in store meta (`active_mindset`). A per-call
`mindset=` override does not write the store. The plate can change any time.

```python
lat.attune("monotropic")                 # persist for this seat
pack = lat.recall("retry storm under load")
assert pack["mindset"]["name"] == "monotropic"

# one-shot override
wide = lat.recall("retry storm under load", mindset="polytropic")
```

```bash
hermes-insight attune monotropic
hermes-insight recall "retry storm load" --mindset catalogue
```

Plugin: `insight_attune` plus optional `mindset` on `insight_recall` /
`insight_perceive` / `insight_plan`. `insight_stats` reports the active plate.

## Ethics

- Credit Wise. Do not diagnose people or agents.
- Do not claim lived neurodivergent identity for a process.
- A plate is inspectable (`pack["mindset"]`, `stats()["mindset"]`) and temporary.
- Strength of a pattern is not truth. Hops are associative, not causal.
- Recall never writes `applied` credit. Attune never writes `applied` credit.
- Forbidden in briefs and plate notes: autism, ADHD, disorder, diagnosis, DSM,
  psychosis, mania.

## Anti-patterns

| Don’t | Do instead |
|-------|------------|
| “This agent is autistic/ADHD” | Name the plate and its axes |
| Leave a plate on forever | Change it when the seat changes |
| Treat a wide polytropic set as proof | Verify; hops are still associative |
| Conflate card `load=monotropic` with the plate | Card load = protect/skip |
| Implement skipped platters | Stay on cognition-relevant axes |
