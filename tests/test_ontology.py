"""Agent-field ontology smoke tests."""

from hermes_insight.models import Domain, LinkKind, PatternKind
from hermes_insight.ontology import AGENT_WORLD_TERMS, FORGE_VOICE
from hermes_insight.match import expand_query_features


def test_agent_domains_exist():
    for d in ("agent", "model", "tool", "skill", "context", "memory", "multi_agent", "prompt"):
        assert Domain(d).value == d


def test_agent_link_kinds():
    for k in ("delegates_to", "uses_model", "has_skill", "calls", "shares_context"):
        assert LinkKind(k).value == k


def test_agent_pattern_kinds():
    for k in ("agent", "model", "tool", "skill", "prompt"):
        assert PatternKind(k).value == k


def test_synonyms_expand_agent_terms():
    exp = expand_query_features(["agent", "model", "skill"])
    assert "subagent" in exp or "worker" in exp
    assert "llm" in exp or "completion" in exp
    assert "playbook" in exp or "workflow" in exp


def test_ontology_voice():
    assert "agent" in FORGE_VOICE["map_title"].lower() or "field" in FORGE_VOICE["map_title"].lower()
    assert "agent" in AGENT_WORLD_TERMS
    assert "model" in AGENT_WORLD_TERMS
