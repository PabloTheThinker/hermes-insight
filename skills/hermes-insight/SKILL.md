---
name: hermes-insight
description: Recognize recurring structures and learn from outcomes.
version: 0.9.1
author: Pablo Navarro (PabloTheThinker), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cognition, pattern-recognition, experience, planning, learning, memory]
    category: cognition
    related_skills: []
    requires_toolsets: [hermes_insight]
---

# Hermes Insight Skill

Hermes Insight gives an agent durable structural recognition across sessions. It matches
current situations to rules and lived outcomes, recalls a budgeted working set, names
the controlling lever, grounds plans in the current digital environment, and learns
recurring workflows. It does not replace reasoning, prove causality from similarity,
dump MEMORY.md, or import AgentDrive.

## When to Use

- Before difficult debugging, architecture, operations, or tool-routing decisions.
- When a failure, correction, or workflow appears to repeat.
- When a multi-step task should teach future Hermes sessions.
- When the workspace, available tools, or service state materially changed.
- When at least three independent task traces may contain a reusable workflow.

Don't use for trivia, one-step deterministic actions, bulk chat logging, or as evidence
that a weak analogy is true.

## Prerequisites

- The `hermes-insight` plugin is enabled for the active Hermes profile.
- `insight_stats` returns the intended agent id, database path, and version.
- Each client or trust boundary uses a separate Insight database.
- No credential value, private key, or unrestricted transcript is supplied to Insight.

If the tools are missing, tell the user the plugin must be installed and Hermes restarted.
Load `references/AGENT-GUIDE.md` for platform-specific installation instructions. Do not
invent tool results or silently fall back to a different memory store.

## How to Run

Invoke `/hermes-insight <situation>` to load this doctrine explicitly. Once loaded, call
`insight_perceive` with the concrete situation and observations. Use `insight_plan` before
consequential multi-step work, and keep all subsequent events under one `task_id`.

## How It Works

```text
observe → recall → perceive → plan → task/events → attributed outcome → learn
  state    memory    shape     route     evidence          credit        recurrence
```

The lattice contains typed patterns and links in local SQLite:

- rules, skills, tools, agents, events, tasks, environments, facts, and induced sequences;
- `instance_of`, `next`, `applied`, `observed_in`, and other explicit relations;
- hybrid template/prototype/feature matching with structural priors;
- conservative reliability from patterns explicitly applied to completed tasks;
- recurring workflow induction across distinct task ids, including failures.

Similarity proposes a candidate. Explicit task outcomes and repeated independent traces
determine whether that candidate earns trust.

For ontology, scoring, privacy, and advanced examples, load
`skill_view(name="hermes-insight", file_path="references/AGENT-GUIDE.md")`.

## Quick Reference

| Tool | Use |
|---|---|
| `insight_perceive` | Situation → lever, matching structures, echoes, `usable` |
| `insight_recall` | Working set: rules, facts, echoes, hops, `usable` |
| `insight_attune` | Set the cognitive plate (trait mindset, not a diagnosis) |
| `insight_remember` | One compact durable fact / engram |
| `insight_plan` | Ranked route with reliability and environment state |
| `insight_observe` | Typed event or scrubbed workspace snapshot/delta |
| `insight_task` | Open/close a task and attribute its outcome |
| `insight_experience` | Record a meaningful event or episode |
| `insight_learn` | Mine repeated workflows across distinct tasks |
| `insight_feedback` | Explicitly strengthen or weaken known patterns |
| `insight_hygiene` | Decay noise and repair structural links |
| `insight_cycle` | Deeper recognition for novel, substantive situations |

## Procedure

1. **Ground the environment when it matters.** Call
   `insight_observe(mode="environment", root="<workspace>")` after changing repository,
   branch, dependency state, or available tools. Continue when the returned snapshot and
   delta describe the intended workspace.
2. **Recall, then perceive.** Call `insight_recall` when you need prior facts, echoes,
   or rules. Optional `insight_attune` sets a trait plate for this seat (see
   `docs/MINDSET.md`); a per-call `mindset=` overrides it. If `usable=false`, gather
   observations. Then call `insight_perceive` with
   component names, symptoms, exact errors, observations, and an optional domain.
   Continue only after checking `usable`, `lever`, top score, and the top rule.
   Use `insight_remember` for one durable claim — never chat logs.
3. **Refuse weak structure.** If `usable=false`, gather two or three new observations and
   perceive again. Do not turn a weak match into a root-cause claim.
4. **Plan consequential work.** Call `insight_plan` and inspect the primary route,
   alternatives, explicit success/failure counts, environment fingerprint, verification
   step, and rollback condition. Continue when the route fits current permissions and
   state.
5. **Open a task.** Call `insight_task(action="open", name=..., goal=...)` and retain its
   `task_id`. The task boundary is the unit of independent workflow evidence.
6. **Leave typed evidence.** For important tool or skill transitions, call
   `insight_observe(mode="event", event_type=..., task_id=..., tool=... or skill_id=...,
   status=..., outcome=..., provenance=...)`. Use `insight_experience` for a concise
   human-readable decision, failure, correction, or discovery.
7. **Execute and verify.** Follow the chosen route, measure the expected result, and stop
   or roll back when its stated condition is met. Completion requires observable evidence,
   not the absence of an exception.
8. **Close with honest credit.** Call `insight_task(action="close", task_id=...,
   outcome=..., summary=..., used_pattern_ids=[...])`. Include only patterns or skills
   actually applied. A recommendation that was merely viewed receives no credit.
9. **Induce recurrence after enough tasks.** Call `insight_learn(materialize=false)` after
   at least three comparable typed tasks. Inspect distinct-task support, labeled outcomes,
   counterexamples, environment count, Wilson lower bound, and lifecycle.
10. **Materialize cautiously.** Use `insight_learn(materialize=true)` only when the
    candidate is understandable and its counterexamples are retained. This writes a local
    `sequence` pattern for review; it never writes or executes a Hermes skill.

## From a Verified Pattern to a Hermes Skill

Promote procedure only when `insight_learn` reports `verified_local` and the evidence
matches the intended environment:

1. Define applicability and excluded conditions.
2. Include required tools, ordered steps, verification, rollback, and known failures.
3. Cite aggregate support and counterexamples without copying private task bodies.
4. Ask for user review before calling `skill_manage(action="create", ...)` or patching an
   existing skill. Respect the Hermes skill write-approval gate.
5. Start a new Hermes session before expecting discovery; the skill index is session-cached.

Never auto-publish or auto-install a learned procedure. Private evidence remains in its
profile compartment.

## Pitfalls

- **Similarity is not causality.** A high match score still requires observation.
- **Selection is not application.** Do not place untried ids in `used_pattern_ids`.
- **One task is not recurrence.** Repeated events inside one task count once.
- **Success-only memory overfits.** Retain failed tasks and counterexamples.
- **Materialized is not verified.** `candidate` sequences remain review-only.
- **Environment drift invalidates precedent.** Capture a new snapshot after material change.
- **Shared databases cross trust boundaries.** Use one database per profile/client.
- **Raw telemetry becomes a liability.** Store concise structure and artifact references.
- **Completed-session spam hides signal.** Record meaningful transitions, not every turn.

## Verification

- `insight_stats` reports the expected profile and a writable local database.
- A concrete `insight_perceive` or `insight_recall` returns a meaningful lever; a
  vague query returns `usable=false`.
- `insight_remember` stores one compact fact; `insight_recall` can retrieve it.
- `insight_plan` displays the current environment snapshot and separates relevance from
  reliability.
- Closing a task with actual `used_pattern_ids` changes explicit outcome evidence.
- Three identical traces inside one task produce no recurring-workflow candidate.
- Three or more distinct tasks can produce a `candidate`; only the documented evidence
  gate can produce `verified_local`.
- `insight_learn` always reports `automatic_skill_write=false` and
  `automatic_execution=false`.
