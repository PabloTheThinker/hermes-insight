#!/usr/bin/env python3
"""Dogfood Hermes Insight v0.2 against local Hermes Agent source."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hermes_insight import HermesInsight


def main() -> int:
    db = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/hinsight-e2e.db")
    if db.exists():
        db.unlink()

    # multi-agent: conductor compartment
    lat = HermesInsight(db_path=str(db), agent_id="conductor", agent_tier="conductor")

    agent_root = Path.home() / "hermes-agent"
    if not agent_root.exists():
        agent_root = Path("/home/ilo/hermes-agent")

    print("=== ingest_tree ===")
    for sub in ("agent", "tools", "cron", "hermes_cli"):
        root = agent_root / sub
        if root.is_dir():
            r = lat.ingest_tree(root, limit=25, link=True)
            print(sub, r["ingested"], "of", r["candidates"])

    # curated ops patterns (domain knowledge)
    seeds = [
        (
            "single long-poll consumer per bot credential",
            "Chat long-poll APIs allow only one active consumer per bot credential; "
            "two workers sharing a token cause conflict errors and dropped updates.",
            "system",
            "rule",
            ["credential", "token", "consumer", "longpoll", "conflict"],
        ),
        (
            "linger user services past shell logout",
            "User-level services need lingering enabled so long-lived processes "
            "survive interactive shell logout and SSH disconnect.",
            "system",
            "rule",
            ["linger", "systemd", "session", "logout", "ssh"],
        ),
        (
            "profile home isolation",
            "Each agent identity must use a separate profile home directory so "
            "skills, sessions, and credentials never collide.",
            "system",
            "rule",
            ["profile", "isolation", "home", "tenant", "credential"],
        ),
        (
            "credential isolation between agents",
            "Never reuse OAuth tokens, bot credentials, or API keys across agent "
            "identities or client compartments.",
            "system",
            "rule",
            ["credential", "isolation", "token", "secret", "agent"],
        ),
    ]
    for title, body, domain, kind, tags in seeds:
        lat.ingest(title, body, domain=domain, kind=kind, tags=tags, confidence=0.85)

    print("=== cycle ===")
    report = lat.cycle(
        "Long-lived messaging process dies when remote shell closes; "
        "chat long-poll conflicts if two workers share one bot credential; "
        "need lingering user services and a single consumer per credential; "
        "profile home isolation between agents is required",
        observations=[
            "user-level service unit with linger enabled",
            "only one long-poll consumer per bot credential",
            "separate profile home directory per agent identity",
            "credential isolation between agent identities",
        ],
        domain="system",
        evolve=True,
    )
    out = Path("/tmp/hinsight-e2e-brief.md")
    out.write_text(report.brief, encoding="utf-8")
    print(report.brief[:2800])
    print("STATS", json.dumps(lat.stats(), indent=2))
    print("TOP")
    for m in report.matches[:8]:
        print(f"  {m.score:.3f} {m.method:10} {m.pattern.title[:90]}")
    print("lever", report.distillation.actual_variable if report.distillation else None)
    print("traj", report.trajectory.direction if report.trajectory else None)

    # second agent compartment should not see conductor DB content
    other_db = db.parent / "worker-e2e.db"
    if other_db.exists():
        other_db.unlink()
    w = HermesInsight(db_path=str(other_db), agent_id="worker-a", agent_tier="worker")
    w.ingest("unrelated", "widget factory throughput", domain="process")
    print("MULTI", "conductor_patterns", lat.stats()["patterns"], "worker_patterns", w.stats()["patterns"])

    # success criteria
    lever = (report.distillation.actual_variable or "").lower()
    top = report.matches[0].score if report.matches else 0
    ok_lever = lever in {
        "credential", "token", "isolation", "linger", "consumer", "longpoll",
        "conflict", "profile",
    }
    ok_score = top >= 0.15
    print("PASS_LEVER", ok_lever, lever)
    print("PASS_SCORE", ok_score, round(top, 3))
    print("brief_path", out)
    return 0 if ok_lever and ok_score else 2


if __name__ == "__main__":
    raise SystemExit(main())
