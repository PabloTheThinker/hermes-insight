"""Tests for pattern-recognition ability + structural match priors."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight import HermesInsight, __version__


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "pr.db")


def test_version():
    assert __version__ == "0.7.0"


def test_perceive_prefers_structural_rule(lat: HermesInsight):
    lat.bootstrap()
    # dump a noisy code-like node that shares some tokens
    lat.ingest(
        "token_utils.py",
        "def get_token():\n    return os.environ['TOKEN']\n",
        domain="code",
        kind="prototype",
        tags=["fabric", "file", "token"],
        confidence=0.5,
    )
    out = lat.perceive(
        "two gateway workers share one bot credential and long-poll conflicts fire",
        observations=["409 conflict", "duplicate getUpdates consumers"],
        domain="agent",
    )
    assert out["success"]
    assert out["lever"]
    assert out["action_hint"]
    assert out["card"]
    titles = [m["title"] for m in out["matches"][:3]]
    # structural starter should beat bare source filename
    assert any("credential" in t.lower() or "consumer" in t.lower() for t in titles)
    assert titles[0] != "token_utils.py" or out["matches"][0]["score"] < 0.5


def test_perceive_log_experience(lat: HermesInsight):
    lat.bootstrap()
    out = lat.perceive(
        "retries without jitter caused a stampede after deploy",
        log_experience=True,
        experience_title="retry storm after deploy",
    )
    assert out["success"]
    assert out.get("logged_experience")
    # second perceive should be able to see lived echo path via lattice growth
    st = lat.stats()
    assert st["patterns"] >= 11


def test_structural_rule_outranks_filename(lat: HermesInsight):
    lat.ingest(
        "retry with jitter",
        "Clients should retry transient failures with exponential backoff and jitter.",
        domain="code",
        kind="rule",
        tags=["retry", "backoff", "jitter"],
        confidence=0.9,
    )
    lat.ingest(
        "client.py",
        "retry timeout backoff client network",
        domain="code",
        kind="prototype",
        tags=["fabric", "file"],
        confidence=0.55,
    )
    hits = lat.match("timeouts and retries hammering the dependency", limit=5)
    assert hits
    top = hits[0]
    title = (top.get("pattern") or {}).get("title") or top.get("title") or ""
    score = float(top.get("score") or 0)
    assert "retry" in title.lower() or score > 0.1
