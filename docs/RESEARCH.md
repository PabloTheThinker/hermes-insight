# Research brief — Pattern recognition → Hermes Insight

This document synthesizes the research behind Hermes Insight. It is an engineering
operationalization, not a medical or diagnostic claim.

## 1. What pattern recognition is

In cognitive science and everyday cognition, **pattern recognition** is the process of
identifying structure in input by relating current information to stored knowledge —
noticing similarities, differences, regularities, and trajectories — then using that
structure to categorize, predict, decide, or learn.

It is fundamental to perception, language, expertise, and decision-making. In machine
learning, “pattern recognition” often means supervised classification; here we mean the
**broader cognitive function**: encode, compare, integrate, and generate structure.

## 2. What it does (functional breakdown)

| Function | Role |
|----------|------|
| Encode | Turn sensory/linguistic input into internal structural representations |
| Match | Compare input to templates, prototypes, or feature sets |
| Separate / complete | Distinguish similar patterns; fill partial cues (memory systems) |
| Integrate | Bind features and episodes into maps and narratives |
| Predict | Expect what comes next from regularities |
| Transfer | Communicate or reuse structure (language, teaching, analogy) |
| Generate | Fabricate new patterns (imagination, invention, hypothesis) |

Mattson (2014) frames **superior pattern processing (SPP)** as central to uniquely
elaborated human capacities: language, invention, imagination/mental time travel, and
even forms of magical thinking when SPP runs without adequate reality checks. SPP is
defined around electrochemical network encoding, integration, and transfer of perceived
*or mentally fabricated* patterns.

## 3. Purpose (why brains — and agents — need it)

1. **Compression** — the world is too high-dimensional; patterns are usable codes  
2. **Prediction** — adaptive behavior requires anticipating regularities  
3. **Generalization** — act in novel situations via structural similarity  
4. **Communication** — shared patterns enable language and culture  
5. **Invention** — recombine patterns into tools, protocols, art, science  

For AI agents specifically: tools and raw context windows do not automatically yield a
*living structural memory* that hops domains and names levers. That is the gap this
harness targets.

## 4. Classic cognitive models (still useful)

Four textbook families (not mutually exclusive in real brains):

1. **Template matching** — compare input to stored exemplars (brittle but fast when exact)  
2. **Prototype matching** — compare to an averaged/ideal category center  
3. **Feature analysis** — detect parts (Pandemonium-style “daemons”) then combine  
4. **Recognition-by-components** — parse objects into structural primitives (geons, etc.)  

Hermes Insight implements (1)–(3) explicitly as score channels and blends them into a
**hybrid** recognizer. Agents (or optional LLMs) can enrich features toward (4).

## 5. Neurodivergent-associated pattern cognition (operational, not clinical)

Many autistic and ADHD adults describe pattern cognition that is:

- **Detail-to-structure** rather than gist-first  
- **Monotropic** — deep processing inside a focus yields denser regularities  
- **Cross-domain** — structural rhymes jump silos (“this outage is the same shape as alert fatigue”)  
- **Distilling** — find the *actual variable* underneath scenic noise  
- **Trajectory-sensitive** — see sequences with direction early  
- **Catalogue-based** — novelty pops because the known set is explicit  
- **Explicit** in social reading — analytical pattern match vs purely implicit “vibe”  

A 2021 theoretical line treats **pattern** dimensions (perception, recognition,
maintenance, generation, seeking, processing) as a unifying lens for diverse autistic
traits. Empirical support is stronger for enhanced perceptual/visual pattern tasks than
for every everyday claim; lived experience still supplies high-value *engineering
metaphors* for agent design.

**Critical cautions encoded in the software:**

- Pattern seeking without source hygiene → conspiracy-shaped overfitting  
- Trajectory confidence must be labeled; early-right can be socially costly  
- Novelty alerts should resolve by *identification/filing*, not chronic alarm  
- Strength of a pattern ≠ moral or factual truth  

## 6. Mapping research → software

| Research idea | Module |
|---------------|--------|
| Feature analysis | `features.py` |
| Template / prototype / hybrid match | `match.py` |
| Durable catalogue + search | `store.py` (SQLite+FTS5) |
| Distill actual variable | `distill.py` |
| Trajectory / mental time-forward | `extrapolate.py` |
| Cross-domain analogy | `cross_domain.py` |
| Novelty catalogue | `anomaly.py` |
| Generation + reinforcement | `evolve.py` |
| Full SPP-like loop | `harness.py` `cycle()` |
| Transfer to agent/human | `brief.py` |
| Optional LLM copilot scaffolds | `prompts.py` |
| Associative recall / feeling of knowing | `recall.py` |
| Compact engrams (hippocampal index) | `recall.remember` / `PatternKind.FACT` |
| Trait plates (swappable mindsets) | `mindset.py` — Wise 2024 smorgasbord, not DSM |

## 7. Selected references (starting points)

- Mattson, M. P. (2014). *Superior pattern processing is the essence of the evolved human brain.* Frontiers in Neuroscience. PMC4141622  
- Classic PR theories overview — template, prototype, feature analysis (cognitive psychology texts; e.g. libretexts cognitive chapters)  
- Lived-experience synthesis on autistic pattern recognition — e.g. weirdlysuccessful.org “pattern recognition in autism” (2026)  
- Crespi, B. (2021). *Pattern Unifies Autism* (theoretical framework; treat as hypothesis-generating)  
- General definitions: pattern recognition as matching stimulus information to memory (cognitive neuroscience primers)
- Park et al. (2023). *Generative Agents* — observation, retrieval, reflection, and planning: https://arxiv.org/abs/2304.03442
- Packer et al. (2023). *MemGPT* — tiered context and external memory: https://arxiv.org/abs/2310.08560
- Axelsen et al. (2026). *MemSkill* — learnable memory-skill selection and evolution: https://arxiv.org/abs/2602.02474
- *Agentic Episodic Control* (ACL Findings 2026) — selective decision-critical recall: https://aclanthology.org/2026.findings-acl.654/
- O’Reilly & Norman (2002). *Hippocampal and neocortical contributions to memory* — complementary learning systems: https://ccnlab.org/papers/OReillyNorman02.pdf
- Tulving & Thomson (1973). Encoding specificity.
- Collins & Loftus (1975); Anderson (1983). Spreading activation / ACT-R.
- Ramsauer et al. (2020). *Hopfield Networks is All You Need* — modern Hopfield = attention: https://arxiv.org/abs/2008.02217
- Jiang et al. (2026). *SYNAPSE* — spreading activation for agent memory: https://aclanthology.org/2026.findings-acl.1108.pdf
- Wise, S. J. (2024). *The Neurodiversity Smorgasbord* — trait plate, not a label: https://www.livedexperienceeducator.com/blog/theneurodiversitysmorgasbord

The engineering deep dive, AgentDrive comparison, scoring design, and prioritized build
roadmap are in **[INTUITION.md](INTUITION.md)**. The recall-layer mapping is in
**[RECALL.md](RECALL.md)**. Swappable cognitive plates (credit: Sonny Jane Wise,
Neurodiversity Smorgasbord, 2024) are in **[MINDSET.md](MINDSET.md)**.

## 8. Ethics

- Do not use this project to “diagnose” people.  
- Do not treat analogy hops as proof.  
- Prefer observation/inference separation in evidence fields.  
- Keep personal and sensitive data out of shared lattices.
