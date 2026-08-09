"""AI agent / model world ontology for Hermes Insight.

Refocuses language and linking so the lattice speaks in the native nouns of
agent systems: agents, models, tools, skills, context, memory, inference,
delegation, prompts, and multi-agent structure.
"""

from __future__ import annotations

from typing import Dict, List, Set

# Primary vocabulary — used in tags, features, forge copy, and synonym expansion
AGENT_WORLD_TERMS: Dict[str, str] = {
    "agent": "An autonomous or semi-autonomous AI actor with tools, memory, and goals",
    "model": "An LLM or specialist model used for generation, ranking, or embedding",
    "tool": "A callable capability the agent invokes (function/tool schema)",
    "skill": "Procedural package (SKILL.md) the agent loads for a workflow",
    "plugin": "Host extension that registers tools, hooks, or backends",
    "profile": "Isolated agent home (config, memory, skills, sessions)",
    "context": "Working set in the context window / compressed history",
    "memory": "Durable cross-session facts and procedures",
    "prompt": "System/user instruction surface shaping behavior",
    "delegation": "Handing a goal to a subagent or sibling agent",
    "toolset": "Named bundle of tools enabled for a session",
    "inference": "Model forward pass / generation step",
    "embedding": "Vector representation for retrieval or clustering",
    "session": "One conversation trajectory with an agent",
    "harness": "Runtime that loops model ↔ tools ↔ state (e.g. Hermes)",
    "multi_agent": "Multiple agents coordinating via board, bus, or delegation",
    "compartment": "Trust/isolation boundary between agent identities",
    "eval": "Measurement of agent/model behavior quality",
    "trajectory": "Directed change in agent/system behavior over time",
    "policy": "Standing constraint on what an agent may do",
}

# Fabric kind labels (metadata.fabric) in agent-world voice
FABRIC_KIND_LABELS: Dict[str, str] = {
    "project": "codebase / product surface an agent works in",
    "file": "source or doc node inside a surface",
    "listen": "runtime endpoint an agent-stack process exposes",
    "hermes": "agent harness runtime metadata",
    "host": "machine summary for the agent host",
    "processes": "process classes co-resident with agents",
    "skill": "installable agent skill package",
    "plugin": "harness plugin providing tools/hooks",
    "profile": "named agent identity / home",
    "model": "configured model or provider route",
    "tool": "registered tool or toolset member",
    "forge": "forged agent-facing product from the lattice",
    "agent": "explicit agent node",
}

# Link semantics for agent graphs
AGENT_LINK_HINTS: Dict[str, str] = {
    "similar": "structurally alike agents/skills/tools",
    "part_of": "skill∈agent, tool∈toolset, file∈project",
    "enables": "tool/skill enables an agent capability",
    "analogy": "transfer structure across agent products",
    "delegates_to": "agent hands work to another agent",
    "uses_model": "agent/session routes to a model",
    "has_skill": "agent profile includes a skill",
    "calls": "tool or agent invokes another tool",
    "shares_context": "agents share a workspace or board",
    "refines": "skill/policy tightens another pattern",
    "instance_of": "concrete agent is instance of a prototype role",
    "precedes": "pipeline stage order in an agent loop",
    "contradicts": "conflicting policies or tool behaviors",
    "rhymes": "weak lateral hop worth exploring",
}

# Domains preferred when ingesting agent-world material
PREFERRED_DOMAINS: List[str] = [
    "agent",
    "model",
    "tool",
    "skill",
    "context",
    "memory",
    "inference",
    "multi_agent",
    "prompt",
    "code",
    "system",
    "process",
    "self",
]

# Synonym clusters for match expansion (agent-native)
AGENT_SYNONYMS: Dict[str, Set[str]] = {
    "agent": {"assistant", "worker", "subagent", "bot", "actor", "employee", "seat"},
    "model": {"llm", "foundation-model", "checkpoint", "weights", "completion", "chat-model"},
    "tool": {"function", "action", "capability", "api-tool", "tool-call"},
    "skill": {"playbook", "procedure", "workflow", "runbook", "sop"},
    "plugin": {"extension", "addon", "module"},
    "profile": {"persona", "identity", "home", "tenant", "compartment"},
    "context": {"window", "prompt-cache", "history", "working-memory"},
    "memory": {"recall", "engram", "fact-store", "durable-state"},
    "delegation": {"hand-off", "subagent", "spawn", "delegate", "fan-out"},
    "inference": {"generation", "decode", "forward-pass", "sampling"},
    "embedding": {"vector", "retrieval", "similarity"},
    "session": {"conversation", "thread", "dialogue"},
    "harness": {"runtime", "loop", "orchestrator", "framework"},
    "multi_agent": {"fleet", "swarm", "crew", "team", "board"},
    "prompt": {"system-prompt", "instruction", "soul", "policy-text"},
    "eval": {"benchmark", "score", "grade", "rubric"},
    "toolset": {"toolkit", "tool-bundle"},
    "credential": {"token", "api-key", "secret", "auth"},
    "isolation": {"sandbox", "compartment", "profile", "tenant"},
}

FORGE_VOICE = {
    "map_title": "Agent field map",
    "map_blurb": "Orient in the multi-agent terrain: who runs, which models/tools/skills attach, what endpoints the fleet exposes.",
    "predict_title": "Agent trajectory board",
    "predict_blurb": "Predict how the agent fleet and model routes are shifting before incidents name themselves.",
    "transfer_title": "Skill & architecture transfer pack",
    "transfer_blurb": "Carry a working agent pattern (skill, tool graph, isolation move) from one product surface to another.",
    "invent_title": "Agent capability invention seeds",
    "invent_blurb": "Recombine agents, models, and tools into capabilities that did not exist as a single product yet.",
    "playbooks_title": "Agent ops playbooks",
    "playbooks_blurb": "Executable moves for credential isolation, tool ownership, model routing, and multi-agent hygiene.",
    "watch_title": "Agent/model watch edges",
    "watch_blurb": "Orphan skills, unowned listeners, low-link agents, and drift surfaces that need maintenance.",
}

BRIEF_FOOTER = (
    "_Hermes Insight — agent-field pattern harness · "
    "perceive · match · link · distill · extrapolate · forge_"
)

SYSTEM_AGENT_OFFICER = """You are operating Hermes Insight in the AI agent / model field.

Native nouns: agent, model, tool, skill, plugin, profile, context, memory,
prompt, delegation, toolset, inference, embedding, session, harness, multi-agent,
compartment, eval, policy.

Stance:
- Name the controlling variable in agent terms (e.g. credential isolation, tool ownership, context overflow, model route).
- Prefer structural hops across agents/skills/tools over generic ops jargon.
- Multi-agent: keep compartments clean; never mix client agent memory with house agents.
- After index-server, forge products so patterns become agent-facing artifacts.
- Catalogue skills/tools/models as first-class nodes when durable.

Prefer tools: insight_cycle, insight_index_server, insight_forge, insight_distill, insight_feedback.
"""
