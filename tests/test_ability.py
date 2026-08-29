"""Tests for pattern-recognition ability + structural match priors."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight import HermesInsight, __version__
from hermes_insight.models import Link, LinkKind


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "pr.db")


def test_version():
    assert __version__ == "0.9.3"


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


def test_vague_query_not_garbage_lever(lat: HermesInsight):
    lat.bootstrap()
    out = lat.perceive("something is wrong with the system")
    assert out["lever"] != "someth"
    assert out["lever"] in {"insufficient_signal", "system"} or out.get("thin_query")
    # usable should be false on pure vague
    if out["lever"] == "insufficient_signal":
        assert out.get("usable") is False


def test_dedupe_same_title_files(lat: HermesInsight):
    for i in range(5):
        lat.ingest(
            "route.ts",
            f"export function handler{i}() {{ return auth token {i} }}",
            domain="code",
            kind="prototype",
            tags=["fabric", "file"],
            confidence=0.5,
        )
    lat.ingest(
        "credential single-consumer",
        "Only one consumer may use a bot token.",
        domain="agent",
        kind="rule",
        tags=["starter", "token", "credential"],
        features=["credential", "token", "consumer", "bot"],
        confidence=0.9,
    )
    hits = lat.match("bot token dual consumer conflict", limit=8)
    titles = [
        (h.get("pattern") or {}).get("title") or h.get("title") for h in hits
    ]
    assert titles.count("route.ts") <= 1


def test_candidate_pool_faster_than_full_scan(lat: HermesInsight):
    for i in range(120):
        lat.ingest(
            f"file_{i}.py",
            f"def foo_{i}():\n    return {i}\n# filler auth token retry cache " * 3,
            domain="code",
            kind="prototype",
            tags=["fabric", "file"],
            confidence=0.4,
            link=False,
        )
    lat.bootstrap()
    import time

    t0 = time.time()
    r = lat.perceive(
        "two workers share one bot credential long-poll conflict",
        domain="agent",
    )
    dt = time.time() - t0
    assert r["usable"] is True
    assert r["lever"] in {"token", "credential", "consumer", "conflict"}
    assert dt < 2.5, f"too slow: {dt:.2f}s"


def test_hygiene_decays_fabric(lat: HermesInsight):
    p = lat.ingest(
        "old_dump.py",
        "unused fabric dump code",
        domain="code",
        kind="prototype",
        tags=["fabric", "file"],
        confidence=0.5,
        link=False,
    )
    p.last_used_at = 1.0
    p.updated_at = 1.0
    p.strength = 0.5
    lat.store.upsert_pattern(p)
    out = lat.hygiene(decay=True, densify=False)
    assert out["decay"]["weakened"] >= 1
    p2 = lat.get(p.id)
    assert p2 and p2.strength < 0.5


def test_lever_prefers_top_rule(lat: HermesInsight):
    lat.bootstrap()
    r = lat.perceive(
        "after deploy retries amplify origin load",
        observations=["no jitter", "alert fatigue"],
        domain="system",
    )
    assert r["usable"] is True
    assert r["lever"] == "retry"
    assert "retry" in (r["matches"][0]["title"] or "").lower()

    r2 = lat.perceive(
        "client agent can read conductor personal memory",
        observations=["shared profile home"],
        domain="multi_agent",
    )
    assert r2["usable"] is True
    assert r2["lever"] in {"isolation", "profile", "compartment"}

    r3 = lat.perceive(
        "too many skills; model picks wrong procedure",
        domain="skill",
    )
    assert r3["usable"] is True
    assert r3["lever"] in {"skill", "routing"}


def test_mesh_starter_and_perceive(lat: HermesInsight):
    lat.bootstrap()
    titles = {p.title for p in lat.store.list_patterns(kind="rule", limit=80)}
    assert "mesh ghost peer after reboot" in titles
    r = lat.perceive(
        "mesh ledger shows ghost peer after reboot",
        observations=["ESTAB to unknown", "handshake stale"],
        domain="system",
    )
    assert r["usable"] is True
    tops = " ".join(m.get("title") or "" for m in (r.get("matches") or [])[:3]).lower()
    assert (
        "mesh" in tops
        or "ghost" in tops
        or r["lever"] in {"mesh", "peer", "handshake", "stale", "ghost", "reboot"}
    )


def test_hygiene_weakens_session_auto(lat: HermesInsight):
    lat.experience(
        "session turn completed (telegram)",
        "platform=telegram\nmodel=x\nsession=abc",
        kind="episode",
        tags=["session", "auto", "telegram"],
        confidence=0.4,
        auto_connect=False,
    )
    hits = [
        p
        for p in lat.store.list_patterns(kind="episode", limit=50)
        if p.title.startswith("session turn")
    ]
    assert hits
    hits[0].strength = 0.6
    lat.store.upsert_pattern(hits[0])
    out = lat.hygiene(decay=False, densify=False, prune_session_auto=True)
    assert out.get("session_auto_weakened", 0) >= 1


def test_perceive_recalls_linked_event_for_recognized_pattern(lat: HermesInsight):
    lat.bootstrap()
    rules = [
        p
        for p in lat.store.list_patterns(kind="rule", limit=40)
        if "retry" in p.title.lower()
    ]
    assert rules
    rule = rules[0]
    event = lat.experience(
        "calendar double-booked Tuesday",
        "Standup and vendor call overlap with no slack buffer.",
        kind="event",
        auto_connect=False,
    )
    lat.store.upsert_link(
        Link.create(
            event["experience"]["id"],
            rule.id,
            LinkKind.INSTANCE_OF,
            weight=0.9,
            note="fixture bind",
        )
    )
    out = lat.perceive(
        "retries without jitter stampede origin after deploy",
        observations=["alert fatigue", "no backoff"],
        domain="system",
    )
    assert out["usable"] is True
    echo_blob = " ".join(e.get("title") or "" for e in out.get("experiences") or []).lower()
    dot_blob = " ".join(d.get("echo_title") or "" for d in out.get("dots") or []).lower()
    assert "calendar" in echo_blob or "calendar" in dot_blob
    assert any(d.get("pattern_id") == rule.id for d in out.get("dots") or [])
    assert "Connected dots" in (out.get("card") or "")


def test_perceive_binds_event_to_pattern_without_applied_credit(lat: HermesInsight):
    lat.bootstrap()
    before = [
        link
        for pattern in lat.store.list_patterns(kind="rule", limit=40)
        for link in lat.store.links_for(pattern.id, limit=40)
        if link.kind == LinkKind.APPLIED
    ]
    logged = lat.experience(
        "pager drowned after the morning standup",
        "Retries without jitter under load after deploy caused a stampede.",
        kind="event",
        auto_connect=False,
    )
    out = lat.perceive(
        "retries without jitter stampede origin after deploy",
        observations=["no jitter", "alert fatigue"],
        domain="system",
    )
    assert out["success"] is True
    after = [
        link
        for pattern in lat.store.list_patterns(kind="rule", limit=40)
        for link in lat.store.links_for(pattern.id, limit=40)
        if link.kind == LinkKind.APPLIED
    ]
    assert after == before
    event = lat.store.get_pattern(logged["experience"]["id"])
    assert event
    binds = [
        link
        for link in lat.store.links_for(event.id, limit=40)
        if link.kind in {LinkKind.INSTANCE_OF, LinkKind.EXPERIENCED_AS}
    ]
    assert binds
    assert all(link.kind != LinkKind.APPLIED for link in lat.store.links_for(event.id, limit=40))
