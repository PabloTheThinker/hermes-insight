"""Science-grounded recall layer — complementary systems, spread, FOK, engrams."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight import HermesInsight
from hermes_insight.models import Link, LinkKind, PatternKind


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "recall.db")


def test_complementary_systems_split_rules_and_echoes(lat: HermesInsight):
    lat.bootstrap()
    opened = lat.open_task("retry incident", goal="retry amplification without jitter")
    lat.experience(
        "retries without jitter",
        "Client retry loop without jitter caused dependency stampede and alert fatigue",
        task_id=opened["task_id"],
        outcome="observed",
    )
    lat.close_task(opened["task_id"], outcome="done", summary="added jitter")

    pack = lat.recall("deploy caused retry storm and noisy pages")
    assert pack["success"] is True
    assert pack["usable"] is True
    assert pack["process"] in {"familiarity", "recollection", "both"}
    rule_titles = " ".join(m["title"] for m in pack["matches"]).lower()
    echo_titles = " ".join(e["title"] for e in pack["experiences"]).lower()
    assert pack["rules"] == pack["matches"]
    assert pack["echoes"] == pack["experiences"]
    assert "retry" in rule_titles or "storm" in rule_titles
    assert "retry" in echo_titles or "jitter" in echo_titles or "stampede" in echo_titles
    assert any(m.get("kind") == "rule" for m in pack["matches"])
    assert any(e.get("kind") in {"event", "episode", "task"} for e in pack["experiences"])


def test_spreading_activation_recovers_lexically_distant_cause(lat: HermesInsight):
    lat.bootstrap()
    cause = lat.experience(
        "calendar double-booked Tuesday",
        "Standup and vendor call overlap with no slack buffer on the calendar.",
        kind="event",
        tags=["calendar", "schedule"],
    )
    effect = lat.experience(
        "operator skipped lunch after alerts",
        "Cortisol spike and skipped lunch after a morning of paging.",
        kind="event",
        tags=["stress", "paging"],
    )
    lat.store.upsert_link(
        Link.create(
            cause["experience"]["id"],
            effect["experience"]["id"],
            LinkKind.CAUSES,
            weight=0.9,
            note="schedule pressure produced the stress episode",
        )
    )

    pack = lat.recall("calendar double-booked Tuesday standup and vendor call")
    hop_titles = " ".join(h["title"] for h in pack.get("hops") or []).lower()
    echo_titles = " ".join(e["title"] for e in pack.get("experiences") or []).lower()
    blob = hop_titles + " " + echo_titles
    assert "skipped lunch" in blob or "cortisol" in blob or "operator skipped" in blob
    assert pack["usable"] is True


def test_encoding_specificity_boosts_matching_environment(lat: HermesInsight):
    lat.bootstrap()
    env_here = lat.ingest(
        "environment:here:aaa11111",
        "workspace fingerprint here-branch",
        kind="prototype",
        domain="system",
        tags=["environment", "snapshot"],
        features=["environment", "snapshot", "here"],
        link=False,
    )
    env_other = lat.ingest(
        "environment:other:bbb22222",
        "workspace fingerprint other-branch",
        kind="prototype",
        domain="system",
        tags=["environment", "snapshot"],
        features=["environment", "snapshot", "other"],
        link=False,
    )
    here_echo = lat.experience(
        "cache stampede on here",
        "TTL expiry caused a cache stampede against origin after deploy.",
        kind="event",
    )
    other_echo = lat.experience(
        "cache stampede on other",
        "TTL expiry caused a cache stampede against origin after deploy.",
        kind="event",
    )
    lat.store.upsert_link(
        Link.create(here_echo["experience"]["id"], env_here.id, LinkKind.OBSERVED_IN, weight=0.85)
    )
    lat.store.upsert_link(
        Link.create(other_echo["experience"]["id"], env_other.id, LinkKind.OBSERVED_IN, weight=0.85)
    )

    with_ctx = lat.recall(
        "cache stampede after TTL expiry",
        environment_id=env_here.id,
    )
    without_ctx = lat.recall("cache stampede after TTL expiry")

    def _echo_score(pack: dict, title_part: str) -> float:
        for row in pack.get("experiences") or []:
            if title_part in str(row.get("title") or ""):
                return float(row.get("score") or 0)
        return 0.0

    assert _echo_score(with_ctx, "here") > _echo_score(with_ctx, "other")
    assert _echo_score(with_ctx, "here") >= _echo_score(without_ctx, "here")


def test_feeling_of_knowing_refuses_thin_query(lat: HermesInsight):
    lat.bootstrap()
    pack = lat.recall("stuff is broken")
    assert pack["success"] is True
    assert pack["usable"] is False
    assert pack["thin_query"] is True
    assert pack["process"] == "none"
    assert pack["lever"] == "insufficient_signal"
    assert pack["matches"] == []
    assert pack["experiences"] == []
    assert "Insight recall" in pack["brief"]


def test_remember_then_recall_hits_fact_lane(lat: HermesInsight):
    lat.bootstrap()
    stored = lat.remember(
        "prefer jitter on retries",
        source="operator",
        salience=0.8,
        pointer="user.md#retry-pref",
    )
    assert stored["success"] is True
    assert stored["fact"]["kind"] == "fact"
    assert stored["fact"]["domain"] == "memory"
    assert "engram" in stored["fact"]["tags"]
    assert stored["fact"]["metadata"]["pointer"] == "user.md#retry-pref"

    pack = lat.recall("deploy caused retry storm and noisy pages")
    fact_titles = " ".join(f["title"] for f in pack.get("facts") or []).lower()
    assert "jitter" in fact_titles or "retries" in fact_titles
    assert any(f.get("kind") == "fact" for f in pack.get("facts") or [])
    assert pack["usable"] is True


def test_working_set_respects_lane_budget(lat: HermesInsight):
    lat.bootstrap()
    for i in range(6):
        lat.experience(
            f"retry echo {i}",
            f"retry storm instance {i} without jitter under load",
            kind="event",
        )
    pack = lat.recall("retry storm without jitter under load", limit=3)
    assert len(pack["matches"]) <= 3
    assert len(pack["rules"]) <= 3
    assert len(pack["experiences"]) <= 3
    assert len(pack["echoes"]) <= 3
    assert len(pack["facts"]) <= 3
    assert len(pack["hops"]) <= 3
    working = pack["working_set"]
    assert len(working["rules"]) <= 3
    assert len(working["echoes"]) <= 3
    assert len(working["facts"]) <= 3
    assert len(working["hops"]) <= 3


def test_recall_does_not_create_applied_credit(lat: HermesInsight):
    lat.bootstrap()
    before = [
        link
        for pattern in lat.store.list_patterns(kind="rule", limit=40)
        for link in lat.store.links_for(pattern.id, limit=40)
        if link.kind == LinkKind.APPLIED
    ]
    pack = lat.recall("two gateway workers share one bot token and long-poll conflicts")
    assert pack["success"] is True
    after = [
        link
        for pattern in lat.store.list_patterns(kind="rule", limit=40)
        for link in lat.store.links_for(pattern.id, limit=40)
        if link.kind == LinkKind.APPLIED
    ]
    assert after == before


def test_recall_harvests_linked_event_as_dot(lat: HermesInsight):
    lat.bootstrap()
    rules = [
        p
        for p in lat.store.list_patterns(kind="rule", limit=40)
        if "retry" in p.title.lower()
    ]
    assert rules
    event = lat.experience(
        "calendar double-booked Tuesday",
        "Standup and vendor call overlap with no slack buffer.",
        kind="event",
        auto_connect=False,
    )
    lat.store.upsert_link(
        Link.create(
            event["experience"]["id"],
            rules[0].id,
            LinkKind.INSTANCE_OF,
            weight=0.85,
        )
    )
    pack = lat.recall(
        "retries without jitter stampede origin after deploy",
        write_meta=False,
    )
    assert pack["success"] is True
    titles = " ".join(
        [e.get("title") or "" for e in pack.get("experiences") or []]
        + [d.get("echo_title") or "" for d in pack.get("dots") or []]
    ).lower()
    assert "calendar" in titles
    assert any(d.get("pattern_id") == rules[0].id for d in pack.get("dots") or [])


def test_remember_rejects_empty_claim(lat: HermesInsight):
    assert lat.remember("   ")["success"] is False


def test_fact_kind_is_first_class():
    assert PatternKind.FACT.value == "fact"
