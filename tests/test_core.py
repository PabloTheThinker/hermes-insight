"""tests for pattern-lattice core."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pattern_lattice.features import extract_features, jaccard
from pattern_lattice.harness import PatternLattice
from pattern_lattice.models import Domain, PatternKind


@pytest.fixture()
def lat(tmp_path: Path) -> PatternLattice:
    return PatternLattice(db_path=tmp_path / "t.db")


def test_extract_features_basic():
    feats = extract_features("Retry with exponential backoff and jitter on network timeouts")
    assert "retry" in feats or "backoff" in feats
    assert jaccard(["a", "b"], ["b", "c"]) == pytest.approx(1 / 3)


def test_ingest_match_cycle(lat: PatternLattice):
    lat.ingest(
        "retry with jitter",
        "Clients should retry transient failures with exponential backoff and jitter.",
        domain="code",
        kind="rule",
        tags=["retry", "backoff"],
        confidence=0.8,
    )
    lat.ingest(
        "alert fatigue",
        "Duplicate low-signal pages train operators to ignore alerts.",
        domain="system",
        tags=["alert", "fatigue"],
    )
    hits = lat.match("timeouts and retries hammering the dependency", limit=5)
    assert hits
    assert hits[0]["score"] > 0

    report = lat.cycle(
        "timeouts and noisy pages after deploy",
        observations=["retries amplified traffic", "duplicate alerts"],
        evolve=True,
    )
    assert report.distillation is not None
    assert report.distillation.actual_variable
    assert report.brief
    assert "Pattern Lattice brief" in report.brief
    st = lat.stats()
    assert st["patterns"] >= 2


def test_distill_and_feedback(lat: PatternLattice):
    p = lat.ingest(
        "root cause is connection pool exhaustion",
        "Latency spikes when the pool is exhausted; adding CPU does not help.",
        domain="system",
        features=["pool", "exhaustion", "latency", "connection"],
    )
    d = lat.distill("Everything is slow and the connection pool is exhausted under load")
    assert d["actual_variable"]
    updated = lat.feedback([p.id], helpful=True)
    assert updated[0]["strength"] >= p.strength


def test_extrapolate(lat: PatternLattice):
    t = lat.extrapolate(
        [
            "error rate up 2%",
            "error rate up 8%",
            "pages firing continuously",
        ]
    )
    assert t["direction"]
    assert t["next_expected"]


def test_demo_cli(tmp_path: Path):
    from pattern_lattice.cli import main

    db = tmp_path / "demo.db"
    rc = main(["--db", str(db), "demo"])
    assert rc == 0
    lat = PatternLattice(db_path=db)
    assert lat.stats()["patterns"] >= 5


def test_export_json_roundtrip(lat: PatternLattice):
    lat.ingest("alpha", "body alpha about cache stampede and ttl", domain="code")
    data = lat.export_patterns()
    assert isinstance(data, list)
    json.dumps(data)  # serializable


def test_anomaly_on_empty(lat: PatternLattice):
    r = lat.cycle("completely novel quantum flute protocol", evolve=False)
    assert r.anomalies
    assert r.generated  # filed anomaly
