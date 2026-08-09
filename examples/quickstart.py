#!/usr/bin/env python3
"""Minimal example: build a tiny lattice and run a cycle."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hermes_insight import HermesInsight


def main() -> None:
    db = Path(tempfile.mkdtemp()) / "ex.db"
    lat = HermesInsight(db_path=db)

    lat.ingest(
        "singleflight",
        "Coalesce concurrent recomputes for the same key into one in-flight call.",
        domain="code",
        kind="rule",
        tags=["cache", "singleflight", "coalesce"],
    )
    lat.ingest(
        "thundering herd",
        "Many clients stampede a backend when a shared resource becomes available.",
        domain="system",
        kind="prototype",
        tags=["stampede", "herd", "load"],
    )

    report = lat.cycle(
        "hot key expired and every pod refetched origin at once",
        observations=["latency cliff", "origin CPU pegged"],
        domain="code",
    )
    print(report.brief)
    print("db:", db)


if __name__ == "__main__":
    main()
