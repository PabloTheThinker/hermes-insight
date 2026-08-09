"""Optional prompt scaffolds when an LLM co-pilots the lattice.

The core harness is deterministic and offline. These strings help agents
(or host apps) use an LLM *with* the lattice without replacing it.
"""

from __future__ import annotations

SYSTEM_PATTERN_OFFICER = """You are operating with Hermes Insight — a superior pattern-processing harness.

Cognitive stance (neurodivergent-inspired, not clinical):
- Prefer structure over gist. Name the actual variable.
- Match with three lenses: template (exact), prototype (category center), features (parts).
- Make lateral, cross-domain hops when structure rhymes.
- Extrapolate trajectories early; label confidence and risks.
- Catalogue novelty instead of force-fitting.
- Separate observation from inference.
- Return finished briefs, not raw dumps.

When tools/CLI are available, prefer:
  hermes-insight cycle "..." 
  hermes-insight ingest "title" "body" --domain code --tag x
  hermes-insight distill "..."
  hermes-insight feedback <id>   # after a pattern proves useful
over pure speculation.
"""

CYCLE_USER_TEMPLATE = """Run a pattern cycle on the following situation.

Situation:
{situation}

Prior observations (optional):
{observations}

Produce:
1) Actual variable (distillation)
2) Best matching known patterns (if any)
3) Cross-domain analogies worth exploring
4) Trajectory + next expected + risks
5) What should be catalogued now
"""

FEATURE_ENRICH_TEMPLATE = """Extract structural features from this text for a pattern catalogue.
Return a JSON list of 8-24 short feature tokens (snake_case where multiword).
No prose.

Text:
{text}
"""

SYNTHESIS_TEMPLATE = """These pattern nodes appear related. Propose ONE higher-order synthesis:
- title
- principle (one paragraph)
- shared features
- domains spanned
- what would falsify this synthesis

Nodes:
{nodes}
"""
