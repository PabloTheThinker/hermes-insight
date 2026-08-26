"""Cognitive plates — trait mindsets, not diagnostic labels."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight import HermesInsight
from hermes_insight.mindset import (
    RecallKnobs,
    apply_to_recall,
    contains_forbidden_language,
    plate_from_name,
    resolve_plate,
)
from hermes_insight.models import LinkKind, PatternKind


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "mindset.db")


def test_balanced_matches_v09_recall_defaults():
    knobs = apply_to_recall(plate_from_name("balanced"))
    golden = RecallKnobs()
    assert knobs.spread_steps == golden.spread_steps == 3
    assert knobs.inhibit_top_m == golden.inhibit_top_m == 7
    assert knobs.inhibit_beta == golden.inhibit_beta == 0.12
    assert knobs.usable_activation == golden.usable_activation == 0.12
    assert knobs.recency_half_life_days == golden.recency_half_life_days == 30.0
    assert knobs.lane_limit_scale == 1.0
    assert knobs.thin_min_features == 3
    assert knobs.thin_min_words == 8
    assert knobs.thin_require_both is True


def test_monotropic_working_set_narrower_and_more_rule_heavy(lat: HermesInsight):
    lat.bootstrap()
    for i in range(6):
        lat.experience(
            f"retry echo {i}",
            f"retry storm instance {i} without jitter under load after deploy",
            kind="event",
        )
    query = "retry storm without jitter under load after deploy"
    mono = lat.recall(query, limit=8, mindset="monotropic", write_meta=False)
    poly = lat.recall(query, limit=8, mindset="polytropic", write_meta=False)
    mono_n = sum(len(mono["working_set"][k]) for k in ("rules", "facts", "echoes", "hops"))
    poly_n = sum(len(poly["working_set"][k]) for k in ("rules", "facts", "echoes", "hops"))
    assert mono_n < poly_n
    assert len(mono["matches"]) <= len(poly["matches"])
    assert mono["mindset"]["name"] == "monotropic"
    assert poly["mindset"]["name"] == "polytropic"
    assert any(m.get("kind") == "rule" for m in mono["matches"])


def test_cyclical_time_ranks_sequence_above_one_off_event(lat: HermesInsight):
    lat.bootstrap()
    seq = lat.ingest(
        "retry jitter circuit sequence",
        "Ordered workflow: detect retry amplification, add jitter, close the circuit.",
        kind=PatternKind.SEQUENCE,
        domain="system",
        features=["retry", "jitter", "circuit", "workflow", "sequence"],
        tags=["recurring", "workflow"],
        confidence=0.7,
        link=False,
    )
    event = lat.experience(
        "one-off retry this morning",
        "A single retry burst this morning after a deploy.",
        kind="event",
    )
    pack = lat.recall(
        "retry jitter circuit workflow",
        mindset={"name": "custom", "time": "cyclical", "memory": "procedural"},
        write_meta=False,
    )
    titles = [row["title"] for row in pack["matches"] + pack["experiences"]]
    assert seq.title in titles
    seq_score = next(
        float(row["score"])
        for row in pack["matches"] + pack["experiences"]
        if row["title"] == seq.title
    )
    event_score = next(
        (float(row["score"]) for row in pack["experiences"] if row["title"] == event["experience"]["title"]),
        0.0,
    )
    assert seq_score > event_score


def test_sensitive_accepts_borderline_query_filter_refuses(lat: HermesInsight):
    lat.bootstrap()
    query = "retry storm load"
    sensitive = lat.recall(query, mindset="catalogue", write_meta=False)
    filtered = lat.recall(query, mindset="monotropic", write_meta=False)
    assert sensitive["thin_query"] is False
    assert sensitive["usable"] is True
    assert filtered["thin_query"] is True
    assert filtered["usable"] is False


def test_attune_persists_and_per_call_override(lat: HermesInsight):
    lat.bootstrap()
    tuned = lat.attune("monotropic")
    assert tuned["success"] is True
    assert tuned["mindset"]["name"] == "monotropic"
    assert "diagnosis" not in tuned["note"].lower()
    stored = resolve_plate(lat)
    assert stored.name == "monotropic"
    assert lat.stats()["mindset"]["name"] == "monotropic"

    query = "two gateway workers share one bot token and long-poll conflicts"
    implicit = lat.recall(query, write_meta=False)
    override = lat.recall(query, mindset="polytropic", write_meta=False)
    assert implicit["mindset"]["name"] == "monotropic"
    assert override["mindset"]["name"] == "polytropic"


def test_attune_does_not_create_applied_credit(lat: HermesInsight):
    lat.bootstrap()
    before = [
        link
        for pattern in lat.store.list_patterns(kind="rule", limit=40)
        for link in lat.store.links_for(pattern.id, limit=40)
        if link.kind == LinkKind.APPLIED
    ]
    lat.attune("catalogue")
    lat.recall("two workers share one bot token", write_meta=True)
    after = [
        link
        for pattern in lat.store.list_patterns(kind="rule", limit=40)
        for link in lat.store.links_for(pattern.id, limit=40)
        if link.kind == LinkKind.APPLIED
    ]
    assert after == before


def test_no_diagnostic_language_in_plate_or_brief(lat: HermesInsight):
    lat.bootstrap()
    for name in ("balanced", "monotropic", "polytropic", "catalogue"):
        plate = plate_from_name(name)
        assert not contains_forbidden_language(plate.summary())
        assert not contains_forbidden_language(json_blob(plate.to_dict()))
    pack = lat.recall("retry storm without jitter", mindset="catalogue", write_meta=False)
    assert not contains_forbidden_language(pack.get("brief") or "")
    note = lat.attune("polytropic")["note"]
    assert not contains_forbidden_language(note)


def json_blob(data: dict) -> str:
    return " ".join(str(v) for v in data.values())
