#!/usr/bin/env python3
"""Minimal example: perceive a situation with the pattern-recognition ability."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hermes_insight import HermesInsight


def main() -> None:
    db = Path(tempfile.mkdtemp()) / "ex.db"
    lat = HermesInsight(db_path=db)
    lat.bootstrap()

    card = lat.perceive(
        "hot cache key expired and every pod refetched origin at once",
        observations=["latency cliff", "origin CPU pegged"],
        log_experience=True,
    )
    print(card["card"])
    print("---")
    print("hint:", card["action_hint"])
    print("db:", db)


if __name__ == "__main__":
    main()
