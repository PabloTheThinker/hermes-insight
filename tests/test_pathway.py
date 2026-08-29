"""Hebbian pathway growth from recognition-cued insights."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight.harness import HermesInsight
from hermes_insight.models import Link, LinkKind, PatternKind
from hermes_insight.pathway import grow_pathways


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "path.db")


def _retry_rule(lat: HermesInsight):
    rules = [
        p
        for p in lat.store.list_patterns(kind="rule", limit=40)
        if "retry" in p.title.lower()
    ]
    assert rules
    return rules[0]


def _bind_echoes(lat: HermesInsight, rule_id: str, count: int = 3) -> list[str]:
    echo_ids: list[str] = []
    for i in range(count):
        logged = lat.experience(
            f"retry timeout {i}",
            "Timeout then retry without jitter after deploy.",
            kind="event",
            auto_connect=False,
            task_id=f"t-path-{i}",
        )
        echo_id = str(logged["experience"]["id"])
        lat.store.upsert_link(
            Link.create(echo_id, rule_id, LinkKind.EXPERIENCED_AS, weight=0.55)
        )
        echo_ids.append(echo_id)
    return echo_ids


def _dots(rule, echo_ids: list[str]) -> list[dict]:
    return [
        {
            "pattern_id": rule.id,
            "pattern_title": rule.title,
            "pattern_kind": "rule",
            "echo_id": echo_id,
            "echo_title": f"retry timeout {i}",
            "echo_kind": "event",
            "link_kind": "experienced_as",
            "score": 0.5,
            "task_id": f"t-path-{i}",
        }
        for i, echo_id in enumerate(echo_ids)
    ]


def test_repeated_recognition_grows_a_pathway_not_a_skill(lat: HermesInsight):
    lat.bootstrap()
    rule = _retry_rule(lat)
    echo_ids = _bind_echoes(lat, rule.id, 3)
    matches = [{"id": rule.id, "title": rule.title, "kind": "rule", "score": 0.6}]
    growth = grow_pathways(lat, _dots(rule, echo_ids), matches)

    assert growth["strengthened"] == 3
    assert growth["sibling_links"] >= 1
    assert growth["pathways"]
    row = growth["pathways"][0]
    pathway = lat.store.get_pattern(row["id"])
    assert pathway is not None
    assert pathway.kind == PatternKind.SEQUENCE
    assert "pathway" in (pathway.tags or [])
    assert pathway.metadata.get("automatic_skill_write") is False
    assert pathway.metadata.get("pathway") is True
    assert pathway.metadata.get("lifecycle") == "candidate"
    assert int(pathway.metadata.get("support") or 0) >= 3

    skills = lat.store.list_patterns(kind="skill", limit=50)
    assert all(not (p.metadata or {}).get("pathway") for p in skills)
    assert all("pathway" not in (p.tags or []) for p in skills)

    applied = [
        link
        for pattern in lat.store.list_patterns(kind="rule", limit=40)
        for link in lat.store.links_for(pattern.id, limit=40)
        if link.kind == LinkKind.APPLIED
    ]
    assert applied == []


def test_second_growth_potentiates_bind_weight(lat: HermesInsight):
    lat.bootstrap()
    rule = _retry_rule(lat)
    echo_ids = _bind_echoes(lat, rule.id, 1)
    matches = [{"id": rule.id, "title": rule.title, "kind": "rule", "score": 0.6}]
    dots = _dots(rule, echo_ids)
    grow_pathways(lat, dots, matches)
    first = [
        link.weight
        for link in lat.store.links_for(echo_ids[0], limit=40)
        if link.target_id == rule.id and link.kind == LinkKind.EXPERIENCED_AS
    ][0]
    grow_pathways(lat, dots, matches)
    second = [
        link.weight
        for link in lat.store.links_for(echo_ids[0], limit=40)
        if link.target_id == rule.id and link.kind == LinkKind.EXPERIENCED_AS
    ][0]
    assert second > first


def test_sibling_echoes_share_context(lat: HermesInsight):
    lat.bootstrap()
    rule = _retry_rule(lat)
    echo_ids = _bind_echoes(lat, rule.id, 2)
    matches = [{"id": rule.id, "title": rule.title, "kind": "rule", "score": 0.6}]
    grow_pathways(lat, _dots(rule, echo_ids), matches)
    pair = set(echo_ids)
    laterals = [
        link
        for link in lat.store.links_for(echo_ids[0], limit=40)
        if link.kind in {LinkKind.SHARES_CONTEXT, LinkKind.SIMILAR}
        and {link.source_id, link.target_id} == pair
    ]
    assert laterals
    assert laterals[0].kind == LinkKind.SHARES_CONTEXT


def test_recall_surfaces_grown_pathway(lat: HermesInsight):
    lat.bootstrap()
    rule = _retry_rule(lat)
    _bind_echoes(lat, rule.id, 3)
    pack = lat.recall(
        "retries without jitter stampede origin after deploy",
        write_meta=True,
    )
    assert pack["success"] is True
    assert isinstance(pack.get("pathways"), list)
    titles = " ".join(p.get("title") or "" for p in pack.get("pathways") or []).lower()
    stored = [
        p
        for p in lat.store.list_patterns(kind="sequence", limit=200)
        if (p.metadata or {}).get("pathway")
    ]
    assert stored
    assert "pathway" in titles or stored[0].title.startswith("pathway:")
    assert all(p.metadata.get("automatic_skill_write") is False for p in stored)


def test_perceive_card_can_mention_pathways(lat: HermesInsight):
    lat.bootstrap()
    rule = _retry_rule(lat)
    _bind_echoes(lat, rule.id, 3)
    out = lat.perceive(
        "retries without jitter stampede origin after deploy",
        observations=["alert fatigue", "no backoff"],
        domain="system",
    )
    assert out["success"] is True
    assert isinstance(out.get("pathways"), list)
    stored = [
        p
        for p in lat.store.list_patterns(kind="sequence", limit=200)
        if (p.metadata or {}).get("pathway")
    ]
    assert stored
    if out.get("pathways"):
        assert "Grown pathways" in (out.get("card") or "")
