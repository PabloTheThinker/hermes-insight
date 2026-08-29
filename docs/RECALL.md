# Recall layer — how Insight remembers

Hermes Insight is a **retrieve organ**, not a chat archive. This document maps
human and neural-network memory research onto the lattice, then tells an agent
how to use it.

> Deep daily manual: [AGENT-GUIDE.md](AGENT-GUIDE.md). Planner/induction: [INTUITION.md](INTUITION.md).

**Not a Hermes `MemoryProvider`.** Insight does not dump MEMORY.md, session
transcripts, or the lattice into context. It returns a **budgeted working set**.

## Science → operators

| Mechanism | Research | Insight operator |
|-----------|----------|------------------|
| Complementary learning systems | Hippocampus: fast, pattern-separated episodes. Neocortex: slow overlapping structure (McClelland; O’Reilly & Norman 2002) | Rules/skills vs events/facts; `insight_learn` consolidates |
| Hippocampal index | Hippocampus stores **pointers** to cortical features, not the whole episode | `insight_remember` writes a compact engram + optional artifact pointer |
| Encoding specificity | Recall succeeds when the cue overlaps encoding context (Tulving & Thomson 1973) | Cue = query + observations + environment snapshot + task |
| Pattern completion | Partial cue reconstructs a bound pattern (Hopfield; Ramsauer et al. 2020 = attention) | Working set, not a neighbor list |
| Spreading activation | Retrieval is energy propagation (Collins & Loftus; Anderson ACT-R; SYNAPSE 2026) | 2–3 hop spread with fan effect and lateral inhibition |
| Dual process | Familiarity (“know”) vs recollection (“remember”) (Yonelinas; Tulving) | Lanes: `rules` / `facts` / `echoes` / `contradictions` |
| Selective episodic control | Indiscriminate recall is a retrieval dilemma (AEC, ACL 2026) | `usable` + thin-query refusal |
| Testing effect + decay | Retrieval strengthens a trace; unused traces fade | Light `touch` on the working set; hygiene still decays; **no `applied` credit** |
| Feeling of knowing | Humans can reject “I don’t have this” | `usable=false` — do not invent a memory |

Hard boundaries: stdlib only, no embeddings, no transcript dumps, one DB per
trust boundary, similarity is not causal credit.

## Pipeline

```text
cue (query + optional environment / task / observations)
  → scrub + thin-query gate
  → hybrid match seeds
  → spreading activation over existing links
  → dual-process split + contradictions
  → budgeted working set + usable + brief
```

`insight_perceive` answers “what shape is this?”.
`insight_recall` answers “what do we already know that matters here?”.

Optional `mindset=` (or a persisted plate from `insight_attune`) changes
spread, inhibition, lane weights, and the thin-query bar. Defaults reproduce
these 0.9 constants. See [MINDSET.md](MINDSET.md).

## How to call

```python
pack = lat.recall(
    "deploy caused retry storm and noisy pages",
    observations=["no jitter on clients"],
    environment_id=snapshot_id,   # optional encoding-specificity cue
    limit=5,
)
if not pack["usable"]:
    # gather facts; do not treat this as memory
    ...
```

```bash
hermes-insight recall "two workers share one bot token" -o "409 from getUpdates"
hermes-insight remember "prefer jitter on retries" --pointer "user.md#retry-pref"
```

### Read the pack

1. **`usable`** — if false, gather observations. Feeling of knowing said no.
2. **`process`** — `familiarity` (rules), `recollection` (facts/echoes), `both`, or `none`.
3. **`rules` / `matches`** — structural priors.
4. **`facts`** — compact engrams from `insight_remember`.
5. **`echoes` / `experiences`** — lived events/tasks.
6. **`hops`** — nodes activated by spread that the query did not match (the
   SYNAPSE “bridge”: lexically distant but causally linked).
7. **`contradictions`** — `contradicts` neighbors of activated nodes.
8. **`working_set`** — the same lanes, already budgeted by `limit`.
9. **`mindset`** — name + axes of the plate that produced this set.
10. **`dots`** — explicit bindings from a recognized rule/skill to a lived
    event or task (`experienced_as` / `instance_of`). Recognition cues recall.

Backward-compatible keys (`matches`, `experiences`, `hops`, `brief`, `lever`)
remain so `insight_plan` and older tests keep working.

## Remember (encode side)

```text
insight_remember(claim, source?, salience?, pointer?, task_id?)
```

Writes one scrubbed `kind=fact` node (`domain=memory`, tags include `engram`).
Optional `pointer` is an artifact ref (`user.md#deploy-pref`), **never file
contents**. The fact auto-links `instance_of` matching rules and `observed_in`
the current environment snapshot when one exists.

This is the hippocampal-index idea: store the binding, not the episode dump.

## Doctrine

- Recall before rediscovery.
- Remember one claim at a time. Chat logs are not engrams.
- Preferences may still live in MEMORY.md; **recalling** them goes through Insight.
- Procedures still become skills. Structures and facts stay in the lattice.
- Closing a task with `used_pattern_ids` is the only way to give outcome credit.
  Recall is retrieval practice, not success.

## Anti-patterns

| Don’t | Do instead |
|-------|------------|
| Dump MEMORY.md / the lattice | `insight_recall` for a working set |
| Treat a high hop as proof | Verify; hops are associative, not causal |
| Ignore `usable=false` | Gather two or three observations |
| Log every chat turn as a fact | `remember` one durable claim |
| Credit a pattern because it was recalled | Only `used_pattern_ids` on task close |

## Related

- [RESEARCH.md](RESEARCH.md) — cognitive and agent-memory sources
- [MINDSET.md](MINDSET.md) — cognitive plates (Wise 2024)
- [INTUITION.md](INTUITION.md) — planner, observation, induction
- [EXPERIENCE.md](EXPERIENCE.md) — task/event write path
- [ABILITY.md](ABILITY.md) — perceive card
