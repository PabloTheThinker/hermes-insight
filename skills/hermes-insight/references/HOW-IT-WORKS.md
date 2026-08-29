# How Insight works for you

You are a Hermes agent with the `hermes_insight` toolset. This page is the
mental model. Load it when you need pack keys, credit rules, or the difference
between recall, perceive, pathways, and skills.

Insight is **not** a Hermes `MemoryProvider`. Do not dump MEMORY.md, session
transcripts, or the lattice into context. Call `insight_recall` for a budgeted
working set. Call `insight_perceive` to name the shape of the current scene.

## What the lattice is

A local SQLite graph of **patterns** (nodes) and **links** (edges).

| You meet it as | Kind / link | Meaning for you |
|---|---|---|
| Structural prior | `rule`, `prototype`, `template` | Shape to test, not a story to invent |
| Lived echo | `event`, `episode`, `task` | Something this seat already saw |
| Compact fact | `kind=fact` via `insight_remember` | One durable claim + optional pointer |
| Bind | `experienced_as`, `instance_of` | This echo is an instance of that rule |
| Credit | `applied` | Only from `used_pattern_ids` on task close |
| Pathway | `sequence` + tags `pathway`, `grown` | Local skill-shaped candidate, unpublished |

Starter rules exist after bootstrap (retry storms, credential single-consumer,
profile isolation, and so on). They are priors, not proof.

## What each call does for you

```text
environment snapshot     insight_observe(mode="environment")
        │
        ▼
budgeted memory          insight_recall(query, observations?)
        │                  usable · rules · facts · echoes · hops · dots · pathways
        ▼
name the shape           insight_perceive(situation, observations?, log?)
        │                  lever · action_hint · card · usable
        ▼
rank a route             insight_plan(situation, observations?)
        │                  relevance ≠ reliability; does not execute
        ▼
live an episode          insight_task open → observe/experience → close
        │                  close is the only applied-credit write
        ▼
ask if it recurs         insight_learn(materialize=false)
                           distinct task_id support; never auto-writes a Hermes skill
```

### Recall pack (read this first)

| Key | Treat it as |
|---|---|
| `usable` | Feeling of knowing. `false` → gather observations, do not invent |
| `thin_query` | The cue was vacuous |
| `process` | `familiarity` (rules), `recollection` (facts/echoes), `both`, `none` |
| `lever` | Controlling variable (`retry`, `token`, `isolation`, …) |
| `rules` / `matches` | Structural priors |
| `facts` | Engrams from `insight_remember` |
| `echoes` / `experiences` | Lived events/tasks |
| `hops` | Spread neighbors — associative, not causal |
| `contradictions` | `contradicts` neighbors of activated nodes |
| `dots` | Explicit echo ← rule binds (`experienced_as` / `instance_of`) |
| `pathways` | Grown local sequences from repeated recognition |
| `pathway_growth` | `{strengthened, sibling_links}` this turn |
| `brief` / `card` | Human-readable working set |
| `mindset` | Active cognitive plate (trait config, not a diagnosis) |

Perceive adds `action_hint`, `top_score`, `pattern_ids`, and optional
`logged_experience`. Plan adds `recommendations` (relevance + reliability),
`environment_state`, and a verify/rollback workflow.

## How experience compounds

Recognition that already has a bind **potentiates** that synapse (Hebbian).
Sibling echoes under the same rule grow `shares_context` links. After three
distinct-task echoes (or three unbound echoes), Insight upserts:

```text
pathway: <rule title>
  kind=sequence  tags=pathway,grown,candidate
  automatic_skill_write=false
```

That is how you gain experience and skill-shaped structure **without** publishing
a Hermes skill. `insight_learn` is the other growth path: ordered workflows
across distinct `task_id`s, with failures retained. `verified_local` needs five
labeled tasks, ≤1 failure, and a Wilson lower bound ≥ 0.55.

Never treat a pathway or a `candidate` sequence as an executable skill.

## Credit (non-negotiable)

| Action | Writes `applied`? |
|---|---|
| `insight_recall` / `insight_perceive` | No |
| Connecting `dots` / growing `pathways` | No |
| `insight_plan` recommendation | No |
| `insight_task` close **without** `used_pattern_ids` | No |
| `insight_task` close **with** ids you actually applied | Yes |

Plans rank explicit success/failure over mere strength. Do not stuff untried
ids into `used_pattern_ids` to “help the lattice.”

## Plates

`insight_attune(mindset="balanced|monotropic|polytropic|catalogue")` changes
how recall spreads and how thin a query must be. Per-call `mindset=` overrides
the seat default. This is a **trait overlay**, not a clinical label. Forbidden
in briefs: autism, adhd, disorder, diagnosis, dsm, psychosis, mania.

## Isolation

- One writable database per profile / client / trust boundary.
- Scrub secrets-shaped strings. Store pointers (`user.md#heading`), not files.
- Imported or community content is not local evidence.
- `automatic_skill_write=false` and `automatic_execution=false` always.

If `insight_*` tools are missing, say so. Do not silently use MEMORY.md as a
substitute retrieve organ.
