# Hermes Insight — Deep guide for Hermes agents

**Who this is for:** any Hermes agent (or human operator teaching an agent) that has just gained the Hermes Insight skill/plugin and needs to understand *what this is*, *how the machine works*, and *how to use it every day*.

**Package:** `hermes-insight` · **Primary tool:** `insight_perceive` · **Not** an official Nous product — community companion for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Read this once after install. After that, the loop at the top of §5 is enough for daily work.

---

## 1. What this is (one breath)

Hermes Insight is a **local pattern-recognition lattice**.

It is not chat memory. It is not a vector DB cosplay. It is not “search the repo.”

It stores **structures** (rules, skills, events, tasks, tools, agents…) as nodes, **links** them, **matches** new situations against them, **distills** the controlling variable (the *lever*), and **reinforces** what actually helped.

If language models are good at next-token reasoning, Insight is the missing layer for:

| Gap without Insight | With Insight |
|---------------------|--------------|
| Same failure every session | Lived events link to the rule that fixed it |
| Scenic root-cause stories | Named **lever** + structural prior |
| Skills dumped wholesale | Starters + match prefer *rules* and *routing* |
| Multi-agent bleed | Separate DBs + isolation priors |
| “I think I saw this” | Scores, hops, and `usable` flag |

**Mental model:** a growing graph of *what shapes recur* in agent work — ops, multi-agent, skills, systems — that you **query before inventing** and **write after learning**.

---

## 2. What you gain when the skill is installed

### 2.1 Native plugin tools (`insight_*`)

After `./scripts/install_for_hermes.sh` (and a Hermes reload), you typically get tools including:

| Tool | Role | Use when |
|------|------|----------|
| **`insight_perceive`** | **Primary ability** | Almost always — situation → lever + matches + hint |
| **`insight_plan`** | **Decision route** | Consequential/multi-step work → ranked patterns, skills, tools |
| **`insight_observe`** | **Grounding** | Typed event or workspace snapshot/delta |
| **`insight_learn`** | **Induction** | Recurring ordered workflows across distinct tasks |
| **`insight_recall`** | Associative retrieve | Need to remember what the lattice already knows |
| `insight_attune` | Cognitive plate | Swap recall/perceive/plan mindset for this seat |
| `insight_remember` | Compact engram | Durable fact / preference pointer |
| `insight_task` | Open/close episodes | Multi-step jobs; keep `task_id` |
| `insight_experience` | Log event/episode | After fix, failure, decision |
| `insight_connect` | Explicit link | “Same shape as X” |
| `insight_cycle` | Full cognitive cycle | Novel/deep architecture |
| `insight_distill` | Lever only | Short lever extract |
| `insight_match` | Raw match list | Debugging recognition |
| `insight_bootstrap` | Seed starters | Empty or thin lattice |
| `insight_hygiene` | Decay + densify | After bulk index / weekly |
| `insight_feedback` | Reinforce/weaken | After real-world outcome |
| `insight_forge` | Products from lattice | Maps, playbooks, invention seeds |
| `insight_ingest` / `ingest_tree` / `index_*` | Grow fabric | Code/skills/server fabric (scrubbed) |
| `insight_stats` | Counts + path | Health check |

### 2.2 Skill file

`skills/hermes-insight/SKILL.md` (or your Hermes skills path) is the **short doctrine**.  
**This file** (`docs/AGENT-GUIDE.md`) is the **deep manual**. Load the skill on hard work; read this guide when teaching a new agent or redesigning loops.

### 2.3 Python + CLI (same brain)

```bash
hermes-insight bootstrap
hermes-insight perceive "…" -o "fact" --log
hermes-insight hygiene
```

```python
from hermes_insight import HermesInsight
lat = HermesInsight(db_path="…", agent_id="myagent", agent_tier="worker")
lat.bootstrap()
print(lat.perceive("…", log_experience=True)["card"])
```

Plugin tools and Python/CLI share the same SQLite lattice (path from config / `HERMES_INSIGHT_DB`).

---

## 3. Core concepts (ontology)

### 3.1 Pattern

A **pattern** is a node:

- `title`, `body`
- `kind` — what sort of thing it is  
- `domain` — field of work  
- `features` — tokenized structural tags used for match  
- `tags` — free labels (`starter`, `fabric`, `experience`, …)  
- `strength` / `confidence` / `use_count` — evolve with use  

### 3.2 Kinds (high level)

| Kind | Meaning |
|------|---------|
| `rule` | Structural law — highest value for recognition |
| `prototype` | Exemplar / template shape (or bulk-indexed file) |
| `skill` | Agent skill inventory row |
| `tool` / `agent` / `model` | Field inventory |
| `event` | One lived observation |
| `episode` | Multi-step arc or material session failure |
| `task` | Open/closed work unit |
| `synthesis` | Forged / evolved higher-order node |
| `relation` | Explicit relational structure |

**Prefer acting on `rule` matches.** Fabric `prototype` files are context, not gospel.

### 3.3 Domains

Examples: `agent`, `multi_agent`, `skill`, `system`, `code`, `experience`, `process`, `general`.

Pass `domain=` on perceive when you know the field — lever priors improve.

### 3.4 Links

Edges between patterns, e.g.:

- `instance_of` — this event is an instance of that rule  
- `experienced_as` — lived rhyme  
- `next` — temporal chain inside a task  
- `similar` / other structural relations  

**Hops** = neighbors of top matches — “what else is connected?”

### 3.5 Lever

The **actual variable** that moves the outcome (not scenic noise).

Examples: `token`, `retry`, `isolation`, `cache`, `mesh`, `skill`.

When top structure score is strong, the lever is **anchored to that rule** (title/features), not a random nearby word.

### 3.6 `usable`

Boolean on `perceive` results:

- `true` — enough structure to act (matches + score + real lever)  
- `false` — thin/vague query; gather observations and try again  

**Do not invent root cause when `usable` is false.**

---

## 4. How the machine works (pipeline)

### 4.1 Perceive (default ability)

```text
situation (+ observations)
        │
        ▼
  scrub secrets-shaped text
        │
        ▼
  bootstrap starters if missing titles
        │
        ▼
  extract features + synonym expand
        │
        ▼
  candidate_pool (FTS + structural shortlist — not full table scan)
        │
        ▼
  hybrid match (template · prototype · feature · IDF)
        + structural kind priors (rules up, bare files down)
        + dedupe / diversity
        │
        ▼
  distill lever → refine from top match when strong
        │
        ▼
  lived experiences + graph hops
        │
        ▼
  action_hint + card + usable
        │
        ▼
  optional log_experience (auto-link)
```

**Deep mode** (`deep=true` or auto when weak but substantive): runs a full **cycle** (match, distill, anomalies, brief) and merges results.

### 4.2 Experience / task arc

```text
plan?  →  open_task  →  experience*  →  close_task(used_pattern_ids)
 │           │              │                    │
ranked     priors        auto-link        explicit outcome credit
```

- **open** — creates task node, returns prior matches, `task_id`  
- **experience** — files event/episode; links to structural matches; chains `next`  
- **close** — outcome episode; `used_pattern_ids` attributes success/failure only to
  patterns or skills actually applied

This is how the lattice **learns in lived time**, not only from bulk code index.

### 4.3 Native observation

`insight_observe(mode=environment)` captures scrubbed Git/manifests/runtime/tool metadata
and links each changed snapshot with `precedes`. `mode=event` records a typed event with
task/trace identity, tool or skill, outcome, provenance, trust, and sensitivity. Events
link to the current snapshot through `observed_in`, so plans know which digital
environment produced an outcome. This is native Insight storage—no AgentDrive dependency.

### 4.4 Workflow induction

`insight_learn` mines contiguous typed-event sequences and counts support by distinct
`task_id`, not event frequency. Every result retains success, failure, neutral outcomes,
environment count, and counterexamples. Three tasks can create a `candidate`;
`verified_local` requires at least five independently labeled tasks and a conservative
Wilson success lower bound. `materialize=true` writes a reviewable `sequence` node only.
It never writes or executes a Hermes skill.

### 4.5 Cycle

Longer multi-lens pass for architecture / novel scenes. Use when perceive is weak or the problem is strategic. Produces a structured brief.

### 4.6 Forge

Turns the lattice into **human/agent products**: orientation maps, playbooks, prediction boards, etc. under a run directory. Use after the lattice has substance.

### 4.7 Hygiene

- **Decay** weakens unused fabric/code dumps so they stop drowning rules  
- **Densify** links structural nodes so hops work  
- **Prune session-auto** weakens old noisy “session turn completed” episodes  

Run periodically or after bulk `index_*`.

### 4.8 Starters (bootstrap)

Empty or incomplete lattices get **starter rules** — agent-field priors such as:

- credential single-consumer  
- tool schema token waist  
- prompt cache sacred  
- profile isolation wall  
- retry storm amplifies load  
- skill routing not skill dump  
- mesh ghost peer / split DNS / single writer  
- …  

Bootstrap **fills missing titles** without blindly duplicating everything.

### 4.9 Privacy / compartments

- Scrubber redacts secret-shaped strings  
- **One DB per trust boundary** (house ≠ client)  
- Plugin session hook logs **failed/interrupted** turns only — not every completed chat  
- Material learning still comes from **you**: `log=true`, `insight_experience`, task close  

Never paste raw credentials into titles/bodies.

---

## 5. How you should work (agent doctrine)

### 5.1 Default loop (memorize this)

```text
1. insight_observe(mode=environment) when state materially changed
2. insight_perceive(situation, observations?)
3. For consequential/multi-step work: insight_plan(situation, observations?)
4. If usable: open task → typed events/work → close with used_pattern_ids
5. After ≥3 comparable tasks: insight_learn(materialize=false), inspect counterexamples
6. If novel/weak: deep=true or insight_cycle
7. Promote only verified-local procedure through reviewed skill_manage
```

### 5.2 When to call perceive

**Do call:**

- Before hard debugging  
- Before architecture / multi-agent layout choices  
- On recurring failures  
- When something “feels like last time”  
- Before blaming the wrong layer (network vs credential vs cache)  

**Skip or keep light:**

- Pure trivia / one-shot arithmetic  
- Already-known single-line shell facts  
- When you already hold a fresh perceive card for this exact scene  

### 5.3 How to write a good situation

Bad:

> something is wrong  

Good:

> two gateway workers share one bot token; long-poll returns 409  
> observations: duplicate getUpdates; messages dropped  

**Concrete nouns + symptoms + what changed** beat vibes.

### 5.4 How to read the card

1. **`usable`** — if false, gather facts; don’t cosplay certainty  
2. **`lever`** — name you will measure/intervene on  
3. **Top structure** — especially `kind=rule` — apply that first  
4. **`action_hint`** — operational sentence  
5. **Lived echoes** — prior events/tasks; read them before reinventing  
6. **Hops** — related nodes (other rules, agents, past tasks)  

Trust strong scores (≥ ~0.35–0.5 with a clear rule). Verify weak ones.

### 5.5 Logging (how the agent *learns*)

| Action | Effect |
|--------|--------|
| `insight_perceive(..., log=true)` | Files event + auto-links |
| `insight_plan` | Ranks routes; does not execute or claim they were used |
| `insight_observe` | Records environment identity or a typed task/tool/skill event |
| `insight_experience` | Explicit event/episode |
| `insight_task` close + `used_pattern_ids` | Records applied-edge evidence and reinforces/weakens |
| `insight_learn` | Mines distinct-task recurrence; never auto-writes a skill |
| `insight_feedback` | Manual strengthen/weaken |
| Plugin session end | Only failures/interrupts auto-file |

**Preferences → memory. Procedures → skills. Structures + lived rhymes → Insight.**

### 5.6 Multi-agent / client rules

- Separate `db_path` + `agent_id` per client or trust tier  
- Never point a client lattice at house conductor secrets  
- Isolation wall is a first-class starter — use domain `multi_agent`  

### 5.7 Stance (non-negotiable)

1. Recall before rediscovery (`insight_recall`; refuse when `usable` is false)  
2. Name the actual variable  
3. Prefer structural rules over scenic detail  
4. Observation ≠ inference — label confidence  
5. Compartment DBs  
6. No raw secrets in the lattice  

---

## 6. Install & wiring (for operators and agents)

### 6.1 One-shot install

```bash
# from hermes-insight repo
./scripts/install_for_hermes.sh

# profile / named agent
HERMES_HOME=~/.hermes/profiles/myagent \
  ./scripts/install_for_hermes.sh --agent myagent --tier worker
```

What it does:

- Installs Python package into the Hermes environment  
- Copies native plugin under `$HERMES_HOME/plugins/hermes-insight/`  
- Merges plugin enablement into config (**merge** `plugins.enabled` — never replace the whole list)  
- Installs skill file into skills path  
- Points DB at a compartment path under memories  

Reload Hermes so plugin tools appear.

### 6.2 Config sketch

```yaml
plugins:
  enabled:
    - hermes-insight   # among existing entries
  entries:
    hermes-insight:
      agent_id: myagent
      agent_tier: worker   # or conductor, client, …
      db_path: /path/to/myagent.insight.db
```

Env overrides: `HERMES_INSIGHT_DB`, `HERMES_INSIGHT_AGENT_ID`, `HERMES_INSIGHT_AGENT_TIER`.

### 6.3 SOUL / system prompt fragment (optional paste)

```markdown
## Pattern recognition (Hermes Insight)
You have `insight_*` tools. Default ability: **insight_perceive**.
Before hard debugging or architecture choices, perceive the situation.
If usable, act on the lever + top rule + action_hint.
Log meaningful scenes (log=true) and use insight_task for multi-step work.
Do not invent root cause when usable is false — gather observations.
Separate Insight DBs per trust boundary. Never store raw credentials.
```

### 6.4 Verify

```text
insight_stats          → version, pattern/link counts, db path
insight_bootstrap      → starters present
insight_perceive "two workers share one bot token; long-poll 409"
                       → usable true, lever token-ish, rule credential…
```

---

## 7. Worked examples

### 7.1 Credential / dual consumer

**Input:** two workers, one bot token, 409 on long-poll  

**Expect:** lever ≈ `token` · rule **credential single-consumer** · hint about single consumer  

**Then:** fix process topology; `log=true`; next time lived echo appears.

### 7.2 Retry storm

**Input:** after deploy, origin melts; no jitter  

**Expect:** lever ≈ `retry` · rule **retry storm amplifies load**  

### 7.3 Profile isolation

**Input:** client agent sees conductor skills/memory  

**Expect:** lever ≈ `isolation` · rule **profile isolation wall**  

### 7.4 Skill sprawl

**Input:** hundreds of skills; wrong procedure  

**Expect:** lever ≈ `skill` / routing · rule **skill routing not skill dump**  

### 7.5 Mesh ghost peer

**Input:** mesh ledger peer after reboot; stale handshake  

**Expect:** rule **mesh ghost peer after reboot** (or DNS split if resolution-shaped)  

### 7.6 Vague query

**Input:** “stuff is broken”  

**Expect:** `usable=false`, lever `insufficient_signal`, ask for concrete observations  

---

## 8. Anti-patterns

| Don’t | Do instead |
|-------|------------|
| Call cycle on every trivial turn | perceive first |
| Dump entire chat into experience | Short structural body + outcome |
| Share one DB across clients | Compartment paths |
| Trust top `route.ts` file over a rule | Prefer `kind=rule` |
| Ignore `usable=false` | Gather observations |
| Log every session complete | Use task/experience on real work |
| Grow core tools to “remember” | Insight + skills |
| Bare `hermes update` myths | Insight is independent of harness update |

---

## 9. Performance & scale (what to expect)

- **Perceive** on large lattices targets ~100–200ms class via candidate shortlist (not full scans)  
- Bulk fabric (many source files) is normal; **hygiene** keeps rules on top  
- Forge/cycle are heavier — use deliberately  
- Strength/use_count move with feedback and successful task close  

---

## 10. How Insight relates to other memory

| Store | Holds | Insight relation |
|-------|-------|------------------|
| Hot MEMORY / USER | Compact durable prefs | Preferences, not procedures |
| Skills | How to do work | Write skills after hard fixes; Insight stores *that the shape recurs* |
| Session DB | Chat history | Insight is structural, not transcript search |
| Fabric index | Code/skills/tools inventory | Fuel for match; rules still win |
| Insight lattice | Structures + lived links + compact facts | This document; [RECALL.md](RECALL.md) |

**Rule of three:** preference → memory · procedure → skill · recurring structure/event/fact → Insight.
Recall of any of them goes through `insight_recall`, not a file dump.

---

## 11. Failure modes & recovery

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No `insight_*` tools | Plugin not enabled / no reload | Install script + reload Hermes |
| Empty matches | No bootstrap / empty DB | `insight_bootstrap` |
| Always fabric files on top | No hygiene / no starters | bootstrap + hygiene |
| Session spam in echoes | Old auto episodes | hygiene prune; new builds don’t file completed spam |
| Client sees house patterns | Shared DB path | Split `db_path` / agent_id |
| Weak novel domain | No starters yet | log experiences; add rules; forge later |
| Secrets in body | Unscrubbed paste | scrubber helps — still don’t paste secrets |

---

## 12. Teaching a new agent (checklist)

1. Install package + plugin + skill (`install_for_hermes.sh`)  
2. Reload Hermes; confirm `insight_stats`  
3. `insight_bootstrap`  
4. Paste SOUL fragment (§6.3)  
5. Run three perceives: credential, isolation, vague (must refuse)  
6. Open a task, log one experience, close with outcome  
7. Point agent at **this guide** + short `SKILL.md`  
8. Separate DB if the agent is client-facing  

---

## 13. API quick reference

### recall / remember

```text
recall(query, observations?=, environment_id?=, task_id?=, limit=8, mindset?=)
  → {
      usable, thin_query, process, lever, confidence,
      matches[] / rules[], facts[], experiences[] / echoes[],
      hops[], contradictions[], dots[], pathways[], pathway_growth,
      working_set, brief, mindset
    }

attune(name|plate, attention?=, memory?=, time?=, sensory?=, processing?=)
  → { mindset, knobs, summary, note }

remember(claim, source?=, salience?=, pointer?=, task_id?=)
  → { fact, connected, pointer }
```

See [RECALL.md](RECALL.md). Trait plates: [MINDSET.md](MINDSET.md) — not a diagnosis.

### perceive (conceptual)

```text
perceive(situation, observations?=, domain?=, log?=false, deep?=false)
  → {
      usable, lever, confidence, top_score,
      action_hint, card,
      matches[], experiences[], hops[], dots[], pathways[],
      brief, deep_used, thin_query,
      logged_experience?, pattern_ids[]
    }
```

### task

```text
open  name, goal?  → task_id, priors, echoes, dots, pathways, brief
close task_id?, outcome?, summary?, used_pattern_ids?  → applied_patterns[], reinforced?
```

### plan

```text
plan(situation, observations?=, domain?=, limit=5)
  → {
      usable, lever, confidence, card,
      recommendations[{score, relevance, reliability, outcome_evidence, action}],
      environment_affordances[], lived_echoes[], workflow[]
    }
```

### learn

```text
learn(min_support=3, min_steps=2, max_steps=4, materialize=false)
  → {
      candidates[{
        steps[], support, lifecycle, score,
        evidence{distinct_tasks, distinct_environments, successes, failures,
                 counterexample_task_ids, success_lower_bound}
      }],
      materialized[],
      safety{automatic_skill_write=false, automatic_execution=false}
    }
```

### experience

```text
experience(title, body, kind=event|episode, task_id?, outcome?, tags?)
  → auto-linked pattern connections
```

---

## 14. Related docs

| Doc | Depth |
|-----|--------|
| [ABILITY.md](ABILITY.md) | Short ability card |
| [RECALL.md](RECALL.md) | Associative retrieve + remember |
| [MINDSET.md](MINDSET.md) | Cognitive plates (Wise 2024) |
| [EXPERIENCE.md](EXPERIENCE.md) | Experience layer summary |
| [SECURITY.md](../SECURITY.md) | Privacy / isolation |
| [COMMUNITY.md](COMMUNITY.md) | Positioning for humans |
| Skill `hermes-insight` | Hot path for agents |
| Repo README | Install + status |

---

## 15. Version note

This guide targets the **0.9.x** line (associative recall + remember, cognitive plates,
perceive + plan, native observation, explicit applied-pattern outcomes, evidence-gated
workflow induction, structural priors, and session-noise hygiene). APIs evolve; trust
`insight_stats.version` on the live lattice.

---

## 16. Closing doctrine (print this)

> You are not required to remember every incident.  
> You are required to **recognize shape**, **name the lever**, **act on the best rule**, and **leave a trail** so the next turn — or the next agent — is faster.  
> That trail is Hermes Insight.

*When in doubt: `insight_perceive`.*
