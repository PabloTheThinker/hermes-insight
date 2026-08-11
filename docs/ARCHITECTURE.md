# Architecture

## Goals

1. Give agents a **durable structural memory** beyond chat logs  
2. Multi-lens recognition (not single cosine silo)  
3. Lateral **cross-domain** linking as a first-class operation  
4. ND-inspired operators: distill, extrapolate, catalogue novelty  
5. Self-evolution: reinforce, decay, synthesize higher-order nodes  
6. Zero required cloud; zero coupling to any single agent host  
7. Hermes-friendly packaging (skill now, plugin later)
8. Native typed events + environment state without another agent-memory runtime

## Non-goals (v0.1)

- Replacing the LLM reasoner  
- Training neural nets  
- Multimodal embeddings (can be added later as feature providers)  
- Multi-tenant SaaS  

## Component diagram

```text
                 ┌──────────────────┐
                 │  CLI / Skill /   │
                 │  host agent      │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │ HermesInsight   │  harness.py
                 │ plan/cycle/ingest │
                 └────────┬─────────┘
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
   features/match   distill/planner     induction/evolve
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                   PatternStore
                   SQLite + FTS5
```

## Data model

- **Pattern** — node (kind, domain, features, strength, confidence, evidence)  
- **Link** — directed edge (similar, analogy, part_of, contradicts, …)  
- **Trajectory** — ephemeral or storable direction object from a cycle  
- **Distillation** — actual variable + principle + action  
- **CycleReport** — finished product for the agent  
- **Plan** — ranked applicable patterns + environment affordances + outcome evidence
- **Environment snapshot** — scrubbed Git/manifests/runtime/tool state + structural delta
- **Typed event** — trace/task/tool/skill/outcome/provenance record linked to its snapshot
- **Induced workflow** — ordered event subsequence supported by distinct task traces,
  labeled outcomes, environment count, and retained counterexamples

Kinds: template, prototype, feature, sequence, relation, rule, trajectory, anomaly, synthesis.

## Scoring

Hybrid score:

```text
score = 0.25*template + 0.35*prototype + 0.40*feature
score *= 0.7 + 0.3*confidence
```

Cross-domain links boost **analogy** when feature overlap exists across different domains.

Planner reliability is deliberately separate from similarity. Only an explicit
`task close(..., used_pattern_ids=[...])` creates an `applied` edge used as success/failure
evidence. See [INTUITION.md](INTUITION.md) for the calibrated score and roadmap.

Workflow induction is also separate from lexical recognition. `insight_learn` mines
contiguous typed-event sequences, counts each `task_id` once, and materializes only
reviewable `sequence` nodes. `verified_local` requires at least five distinct tasks,
five labeled outcomes, no more than one failure, and a 95% Wilson success lower bound of
at least 0.55. It never writes or executes Hermes skills.

## Evolution

1. Feedback ±strength/confidence  
2. Soft decay on unused nodes  
3. Cluster synthesis when a strong node has ≥2 structural neighbors → `synthesis` pattern  

## Storage layout

Default: `~/.hermes-insight/insight.db`  
Override: `HERMES_INSIGHT_DB` or `HermesInsight(db_path=...)`  

Hermes profiles should pass an explicit path under the profile home, e.g.
`$HERMES_HOME/memories/hermes-insight.db` (documented in HERMES.md — never hardcode operator machines).

## Extension points

| Extension | How |
|-----------|-----|
| Better features | pass `features=` into `ingest` or swap `extract_features` |
| Embeddings | pre-filter candidates before hybrid match |
| LLM rewrite | use `prompts.py` templates; write back via `ingest` |
| Hermes tools | `hermes_plugin/` registers tool schemas calling the harness |
| Multi-agent share | export/import JSON; do not share DBs with secrets |

## Quality bar (craft)

- Map before cut — public harness stable, internals free to move  
- Prove with pytest  
- JSON boundaries  
- Isolation check before public push  
