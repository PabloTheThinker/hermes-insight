# Experience-grounded intuition for Hermes agents

Hermes Insight uses **intuition** in an engineering sense: fast policy selection from
compressed experience. It does not claim consciousness, instinct, or certainty. A useful
agent intuition must remain inspectable:

```text
current situation
  → structural relevance
  → applicable local capabilities
  → explicit prior outcomes
  → ranked plan + uncertainty
  → execution
  → attributed outcome
  ↺
```

The critical distinction is between a pattern that merely resembles a task and a pattern
that was **actually applied** and then succeeded or failed. Similarity is a candidate
generator. Outcome evidence is what lets a candidate become a learned workflow.

## Research synthesis

Pattern recognition is more than classification. For an agent it spans four interacting
memory functions:

1. **Perceptual encoding** — reduce files, processes, tools, messages, and events into
   stable features and relations.
2. **Episodic recall** — retrieve prior situations at decision-critical moments.
3. **Semantic consolidation** — turn repeated episodes into rules and environment models.
4. **Procedural selection** — choose a skill or workflow, execute it, and update its value
   from the result.

Several research lines support this architecture:

- [Generative Agents](https://arxiv.org/abs/2304.03442) combined observation, retrieval,
  reflection, and planning. Its useful lesson is a loop, not a transcript dump.
- [MemGPT](https://arxiv.org/abs/2310.08560) treated context as a tiered resource. This
  supports keeping only a small working set active while durable structures remain local.
- [Lost in the Middle](https://arxiv.org/abs/2307.03172) showed that long context does not
  guarantee effective use. Retrieval and ordering remain control problems.
- [Agentic Episodic Control](https://aclanthology.org/2026.findings-acl.654/) reports that
  selective, decision-critical episodic retrieval outperforms indiscriminate recall in its
  tested environments.
- [MemSkill](https://arxiv.org/abs/2602.02474) treats memory operations as selectable,
  evolvable skills instead of fixed extraction rules.
- [Memento-Skills](https://arxiv.org/abs/2603.18743) frames skill memory as policy
  improvement: route a skill, record outcomes, attribute failure, then gate revisions.
- [Memory–Skill Co-Evolution](https://arxiv.org/abs/2607.16621) argues for evidence-linked
  procedural policies with applicability boundaries, verification rules, and reliability.

These are research systems and preprints, not proof that any one architecture generalizes
to every agent task. Hermes Insight therefore uses conservative, deterministic scoring
and exposes the score components.

## What AgentDrive contributes

[AgentDrive](https://github.com/PabloTheThinker/AgentDrive) is a broader local-first agent
platform by the same maintainer. Its useful infrastructure ideas are:

- an Experience Graph for typed, provenance-bearing structural memory;
- a usage ledger that separates skill matches, runs, successes, and failures;
- task-time skill routing instead of loading every skill;
- a capability funnel from experience → memory → skill → governed package;
- local compartments and context packs rather than one global prompt dump.

Hermes Insight should not duplicate or integrate AgentDrive wholesale. AgentDrive is a
Python 3.11+ platform with MCP, web, orchestration, cryptography, and other runtime
dependencies; Insight is intentionally a Python 3.10+, standard-library cognition
component and native Hermes plugin. AgentDrive is research input only:

| Recreate natively in Hermes Insight | Deliberately leave outside Insight |
|---|---|
| Typed events and provenance in Insight's SQLite graph | AgentDrive runtime/package dependency |
| Local digital-environment snapshots and deltas | Shared AgentDrive databases or services |
| Lever extraction and outcome-aware planning | AgentDrive Genome/DNA formats |
| Conservative pattern/skill evidence lifecycle | AgentDrive MCP execution/orchestration |
| Hermes-native tools, skills, and compartments | Automatic source-code or skill importing |

As of this research pass, AgentDrive declares MIT in its README and `pyproject.toml`, but
its repository root does not contain a standalone license text. This implementation uses
the architectural ideas above and contains independently written code; it does not copy
AgentDrive source. Hermes Insight will reimplement selected concepts against its own data
model and tests; it will not import AgentDrive code even if licensing is later clarified.

## Implemented slice: `insight_plan`

`insight_plan` turns the existing lattice into a pre-action plan:

```python
plan = insight.plan(
    "timeouts trigger retry amplification under load",
    observations=["clients have no jitter"],
    domain="system",
)
```

It returns:

- `lever` and `usable`, preserving the existing thin-query refusal;
- ranked `recommendations` from rules, skills, sequences, syntheses, and prototypes;
- `environment_affordances` for matching local skills, tools, models, and agents;
- a five-part workflow: orient → route → execute → verify → learn;
- explicit score components and outcome samples;
- a compact card for an agent to act on.

The ranking is intentionally simple:

```text
0.68 × current relevance
+ 0.17 × outcome reliability
+ 0.10 × reinforced strength
+ 0.05 × source confidence
+ bounded structural-kind bonus
```

Reliability uses a Beta(1,1) posterior shrunk toward neutral when evidence is sparse. A
single success cannot make a weakly related pattern dominate. Only explicit application
credit counts:

```python
insight.close_task(
    task_id,
    outcome="success",
    summary="bounded jitter stopped the amplification",
    used_pattern_ids=[recommended_pattern_id],
)
```

This creates an `applied` edge from the outcome episode to the pattern. Auto-linked
similarity does **not** receive causal credit. On failure, the same pattern gains negative
evidence and is weakened. Omitting `used_pattern_ids` records the outcome episode but
credits no pattern; retrieval and auto-link activity do not count as successful use.

## Implemented slice: native observation

`insight_observe` recreates the useful typed-history concept directly in Insight:

- `mode=event` records trace/task/step identity, tool or skill, status, outcome, duration,
  artifact references, provenance, trust class, sensitivity, and redaction version;
- `mode=environment` captures metadata-only workspace state: Git revision/branch/dirty
  paths, manifests, runtime, and available tools;
- successive workspace states are joined by `precedes` and expose structural deltas;
- events link to the exact environment through `observed_in`;
- plans include the latest environment fingerprint and change state.

All records use the existing SQLite pattern graph. Inputs are scrubbed recursively, remain
inside the agent compartment, and require no AgentDrive package, service, or data format.

## Implemented slice: recurring workflow induction

`insight_learn` recognizes ordered recurrence rather than text resemblance:

- canonical tool/skill/event steps form contiguous subsequences;
- support is counted by distinct `task_id`, never event count;
- successes, failures, neutral outcomes, environment count, and counterexample task ids
  remain attached;
- a Beta posterior and 95% Wilson lower bound prevent small perfect samples from looking
  certain;
- `candidate` begins at three tasks;
- `verified_local` requires at least five distinct tasks, five labeled outcomes, at most
  one failure, and Wilson lower bound ≥ 0.55;
- optional materialization writes only a local `sequence` node.

It never writes, installs, publishes, or executes a Hermes skill. Promotion remains a
reviewed Hermes `skill_manage` operation with applicability, verification, rollback, and
counterexamples.

## Implemented slice: associative recall

`insight_recall` is the retrieve organ. It is no longer “perceive, but faster.”

- dual-process lanes: rules (familiarity), facts/echoes (recollection), contradictions
- encoding-specificity cues: observations, environment snapshot, task id
- bounded spreading activation with fan effect and lateral inhibition
- feeling-of-knowing: thin queries return `usable=false`
- `insight_remember` writes compact `fact` engrams with optional artifact pointers
- retrieval practice touches the working set; it never creates `applied` credit

See [RECALL.md](RECALL.md) for the science → operator map.

## What to build next

### 1. Skill execution hooks

Map Hermes skill invocation hooks to task ids and pattern ids automatically. Track
matched, loaded, executed, succeeded, failed, and user-corrected as distinct events.
Selection is not execution, and execution is not success.

### 2. Richer environment adapters

Extend native snapshots with opt-in adapters for:

- test and CI state;
- process and endpoint ownership;
- skill versions and invocation hooks;
- permission and trust-boundary constraints;
- stale nodes when a capability disappears.

Plans should state which affordances were observed recently and which are merely catalogued.

### 3. Counterfactual and verification layer

For consequential changes, return:

- primary pattern and best alternative;
- evidence that would distinguish them;
- expected observable result;
- rollback/stop condition;
- contradictions and known failure contexts.

This is how fast pattern recognition remains calibrated rather than becoming confident
overfitting.

### 4. Native reimplementation boundary

Use AgentDrive as a comparison case, then implement the useful behavior directly:

- define a Hermes Insight event envelope with provenance, scope, and redaction metadata;
- capture local environment snapshots and structural deltas in the existing lattice;
- route Insight-native skills and patterns using explicitly attributed outcomes;
- promote patterns only through Insight-owned evidence and review gates.

There is no runtime dependency, shared storage, automatic import, or required protocol
connection between the projects.

### 5. Evaluation

Create a public Hermes community benchmark containing recurring debugging, routing,
multi-agent isolation, and environment-change tasks. Measure:

- top-k pattern/skill selection;
- abstention quality on thin or novel tasks;
- success lift over ungrounded planning;
- calibration error versus observed outcomes;
- negative transfer across projects;
- privacy/isolation violations;
- plan latency and context size.

The purpose is not to maximize recall. It is to improve the next decision while knowing
when the lattice does not yet know enough.

## Community contribution seams

The most useful community additions are narrow and testable:

- an event adapter with a privacy fixture;
- a starter rule with a counterexample;
- a workflow-mining fixture from synthetic task chains;
- a skill route benchmark with success and failure outcomes;
- a native event/environment adapter;
- a contradiction or stale-affordance detector.

Every contribution should answer: what evidence created this pattern, where does it apply,
what outcome would weaken it, and what data boundary contains it?
