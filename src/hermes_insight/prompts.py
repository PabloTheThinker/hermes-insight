"""Optional prompt scaffolds when an LLM co-pilots the lattice."""

from __future__ import annotations

try:
    from hermes_insight.ontology import SYSTEM_AGENT_OFFICER as SYSTEM_PATTERN_OFFICER
except Exception:  # pragma: no cover
    SYSTEM_PATTERN_OFFICER = """You operate Hermes Insight in the AI agent / model field.
Prefer agent nouns: agent, model, tool, skill, context, memory, multi-agent.
"""

CYCLE_USER_TEMPLATE = """Run an agent-field pattern cycle.

Situation:
{situation}

Prior observations (optional):
{observations}

Produce in agent/model language:
1) Controlling variable (distillation) — e.g. credential, model route, tool ownership, context
2) Best matching agents/skills/tools/models already catalogued
3) Transfers worth making across agent products
4) Trajectory of the fleet + next expected + risks
5) What to catalogue (skill, tool, model route, policy)
"""

FEATURE_ENRICH_TEMPLATE = """Extract agent-field structural features from this text.
Prefer tokens like agent, model, tool, skill, plugin, profile, context, memory,
delegation, inference, embedding, session, harness, prompt, eval, toolset.
Return a JSON list of 8-24 short feature tokens (snake_case where multiword).
No prose.

Text:
{text}
"""

SYNTHESIS_TEMPLATE = """These agent-field pattern nodes appear related. Propose ONE higher-order synthesis:
- title (agent/model capability language)
- principle (one paragraph)
- shared features
- domains spanned (agent|model|tool|skill|multi_agent|…)
- what would falsify this synthesis
- first build for an AI agent product

Nodes:
{nodes}
"""
