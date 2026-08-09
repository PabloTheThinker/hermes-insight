"""tests for hermes-insight core + multi-agent + code ingest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_insight.features import extract_features, jaccard
from hermes_insight.harness import HermesInsight
from hermes_insight.match import expand_query_features


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "t.db")


def test_extract_features_basic():
    feats = extract_features("Retry with exponential backoff and jitter on network timeouts")
    assert "retry" in feats or "backoff" in feats
    assert jaccard(["a", "b"], ["b", "c"]) == pytest.approx(1 / 3)


def test_synonym_expansion():
    exp = expand_query_features(["credential", "timeout"])
    assert "token" in exp or "secret" in exp
    assert "deadline" in exp or "latency" in exp or "timeout" in exp


def test_ingest_match_cycle(lat: HermesInsight):
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
    assert hits[0]["score"] > 0.05

    report = lat.cycle(
        "timeouts and noisy pages after deploy",
        observations=["retries amplified traffic", "duplicate alerts"],
        evolve=True,
    )
    assert report.distillation is not None
    assert report.distillation.actual_variable
    assert report.brief
    assert "Hermes Insight" in report.brief
    assert "agent-field" in report.brief or "brief" in report.brief
    st = lat.stats()
    assert st["patterns"] >= 2
    assert st["version"] == "0.6.0"


def test_distill_prefers_structural_lever(lat: HermesInsight):
    lat.ingest(
        "single consumer per credential",
        "Only one long-poll consumer may use a bot credential at a time.",
        domain="system",
        kind="rule",
        tags=["credential", "consumer", "longpoll"],
        confidence=0.9,
    )
    d = lat.distill(
        "two workers share one bot credential and long-poll conflicts fire constantly"
    )
    assert d["actual_variable"] in {
        "credential",
        "consumer",
        "token",
        "conflict",
        "longpoll",
    }


def test_feedback(lat: HermesInsight):
    p = lat.ingest(
        "root cause is connection pool exhaustion",
        "Latency spikes when the pool is exhausted; adding CPU does not help.",
        domain="system",
        features=["pool", "exhaustion", "latency", "connection"],
    )
    updated = lat.feedback([p.id], helpful=True)
    assert updated[0]["strength"] >= p.strength


def test_extrapolate(lat: HermesInsight):
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
    from hermes_insight.cli import main

    db = tmp_path / "demo.db"
    rc = main(["--db", str(db), "demo"])
    assert rc == 0
    lat = HermesInsight(db_path=db)
    assert lat.stats()["patterns"] >= 5


def test_export_json_roundtrip(lat: HermesInsight):
    lat.ingest("alpha", "body alpha about cache stampede and ttl", domain="code")
    data = lat.export_patterns()
    assert isinstance(data, list)
    json.dumps(data)


def test_anomaly_on_empty(lat: HermesInsight):
    r = lat.cycle("completely novel quantum flute protocol", evolve=False)
    assert r.anomalies
    assert r.generated


def test_multi_agent_isolation(tmp_path: Path):
    a = HermesInsight(db_path=tmp_path / "a.db", agent_id="alpha", agent_tier="conductor")
    b = HermesInsight(db_path=tmp_path / "b.db", agent_id="beta", agent_tier="worker")
    a.ingest("secret-a", "alpha only pattern about credential isolation", domain="system")
    b.ingest("secret-b", "beta only pattern about widget throughput", domain="process")
    assert a.stats()["patterns"] >= 1
    assert b.stats()["patterns"] >= 1
    assert a.db_path != b.db_path
    titles_a = {p["title"] for p in a.export_patterns()}
    assert "secret-b" not in titles_a


def test_ingest_file_python(tmp_path: Path, lat: HermesInsight):
    src = tmp_path / "sample_mod.py"
    src.write_text(
        '"""Sample module for credential token handling."""\n\n'
        "def validate_token(token: str) -> bool:\n"
        "    return bool(token)\n\n"
        "class CredentialStore:\n"
        "    def get(self, name: str) -> str:\n"
        "        return name\n",
        encoding="utf-8",
    )
    pat = lat.ingest_file(src)
    assert pat is not None
    blob = " ".join(pat.features)
    assert "validate" in blob or "credential" in blob or "token" in blob
    assert pat.metadata.get("symbols")


def test_plugin_handlers_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import importlib.util
    import sys

    plugin_dir = (
        Path(__file__).resolve().parents[1] / "hermes_plugin" / "hermes_insight_plugin"
    )
    monkeypatch.setenv("HERMES_INSIGHT_DB", str(tmp_path / "plug.db"))
    spec = importlib.util.spec_from_file_location("hip_plugin", plugin_dir / "__init__.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hip_plugin"] = mod
    spec.loader.exec_module(mod)

    out = json.loads(mod.handle_insight_stats({}))
    assert out["success"] is True
    out2 = json.loads(
        mod.handle_insight_ingest(
            {
                "title": "t1",
                "body": "retry backoff jitter rule",
                "domain": "code",
                "tags": ["retry"],
            }
        )
    )
    assert out2["success"] is True
    out3 = json.loads(
        mod.handle_insight_cycle(
            {"query": "retries failing with timeouts", "domain": "code"}
        )
    )
    assert out3["success"] is True
    assert "brief" in out3["data"]
