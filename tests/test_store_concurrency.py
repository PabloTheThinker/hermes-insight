"""SQLite production settings tolerate bounded concurrent agent writes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hermes_insight import HermesInsight


def test_concurrent_distinct_event_writes(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "concurrent.db")

    def write(index: int) -> str:
        result = lat.record_event(
            "worker.observation",
            f"worker {index} completed a bounded observation",
            trace_id=f"trace-{index}",
            status="success",
            details={"worker": index},
        )
        assert result["success"] is True
        return result["event_id"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(write, range(24)))

    assert len(set(ids)) == 24
    events = lat.store.list_patterns(kind="event", limit=100)
    assert len(events) == 24
