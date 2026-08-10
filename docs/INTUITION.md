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

Hermes Insight should not duplicate AgentDrive wholesale. AgentDrive is a Python 3.11+
platform with MCP, web, orchestration, cryptography, and other runtime dependencies;
Insight is intentionally a Python 3.10+, standard-library cognition component and native
Hermes plugin. The useful boundary is:

| Hermes Insight owns | AgentDrive can own |
|---|---|
| Situation encoding and structural match | Broad cross-harness memory substrate |
| Local digital-environment graph | Learned/fused skill lifecycle |
| Lever extraction and compact plan | Genome/DNA promotion and governance |
| Explicit applied-pattern outcomes | MCP-wide execution and orchestration |
| Hermes-native tool surface | Multi-client framework surfaces |

As of this research pass, AgentDrive declares MIT in its README and `pyproject.toml`, but
its repository root does not contain a standalone license text. This implementation uses
the architectural ideas above and contains independently written code; it does not copy
AgentDrive source. A future direct code import should first confirm a complete license
artifact at the exact revision being used.

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
evidence and is weakened. Omitting `used_pattern_ids` preserves legacy reinforcement but
does not create planner reliability evidence.

## What to build next

### 1. Event adapter contract

Add a normalized observation envelope for filesystem changes, service state, test runs,
tool calls, calendars, queues, and messages:

```json
{
  "source": "test_runner",
  "event_type": "command.completed",
  "subject": "tests/test_retry.py",
  "before": {"failures": 3},
  "after": {"failures": 0},
  "at": "ISO-8601",
  "privacy": "workspace",
  "provenance": {"tool_call_id": "..."}
}
```

Adapters must be opt-in, read-scoped, scrubbed, and compartment-aware. Insight should
store structural deltas, not unrestricted raw telemetry.

### 2. Workflow mining

Mine repeated `next` chains only after enough comparable tasks exist:

- canonicalize event verbs and resource types;
- discover frequent subsequences;
- preserve failure branches and rollback steps;
- propose a `sequence` pattern with support count and applicability boundary;
- require review before exporting it as a Hermes skill.

Do not let an LLM turn one anecdote into a universal playbook.

### 3. Skill execution ledger

Map Hermes skill invocation hooks to task ids and pattern ids automatically. Track
matched, loaded, executed, succeeded, failed, and user-corrected as distinct events.
Selection is not execution, and execution is not success.

### 4. Environment state and change detection

Extend the fabric index from snapshots to deltas:

- project/branch/test state;
- process and endpoint ownership;
- available tools and skill versions;
- permission and trust-boundary constraints;
- stale nodes when a capability disappears.

Plans should state which affordances were observed recently and which are merely catalogued.

### 5. Counterfactual and verification layer

For consequential changes, return:

- primary pattern and best alternative;
- evidence that would distinguish them;
- expected observable result;
- rollback/stop condition;
- contradictions and known failure contexts.

This is how fast pattern recognition remains calibrated rather than becoming confident
overfitting.

### 6. AgentDrive bridge

Prefer an explicit interchange boundary over shared databases:

- export Insight pattern, applied-edge, and plan records as versioned JSON;
- map AgentDrive learned/fused skills into read-only Insight `skill` nodes;
- return Insight outcome evidence to AgentDrive as provenance-bearing observations;
- optionally expose the bridge through MCP after the JSON contract stabilizes.

Both systems should preserve source ids, scopes, timestamps, and trust boundaries.

### 7. Evaluation

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
- an AgentDrive interchange mapper;
- a contradiction or stale-affordance detector.

Every contribution should answer: what evidence created this pattern, where does it apply,
what outcome would weaken it, and what data boundary contains it?
