"""Evidence-gated recurring workflow induction."""

from __future__ import annotations

from pathlib import Path

from hermes_insight import HermesInsight


def _record_pytest_task(
    lat: HermesInsight,
    task_id: str,
    *,
    outcome: str,
) -> None:
    lat.open_task(
        f"focused regression {task_id}",
        goal="run the focused pytest check and inspect its result",
        task_id=task_id,
    )
    first = lat.record_event(
        "tool.started",
        "focused regression started",
        task_id=task_id,
        trace_id=f"trace-{task_id}",
        tool="pytest",
        status="running",
    )
    lat.record_event(
        "tool.completed",
        "focused regression completed",
        task_id=task_id,
        trace_id=f"trace-{task_id}",
        parent_event_id=first["event_id"],
        tool="pytest",
        status="success" if outcome == "success" else "failed",
        outcome="passed" if outcome == "success" else "failed",
    )
    lat.close_task(
        task_id,
        outcome=outcome,
        summary=f"focused regression task ended: {outcome}",
    )


def test_induction_requires_distinct_tasks_and_reaches_verified_gate(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "induction.db")
    for index in range(5):
        _record_pytest_task(lat, f"task-{index}", outcome="success")

    learned = lat.learn(min_support=3, min_steps=2, max_steps=2)
    assert learned["success"] is True
    assert learned["task_traces"] == 5
    target = next(
        row
        for row in learned["candidates"]
        if row["steps"]
        == ["tool:pytest:tool.started", "tool:pytest:tool.completed"]
    )
    assert target["support"] == 5
    assert target["lifecycle"] == "verified_local"
    assert target["evidence"]["successes"] == 5
    assert target["evidence"]["success_lower_bound"] >= 0.55
    assert learned["safety"]["automatic_skill_write"] is False


def test_materialization_is_idempotent_and_keeps_counterexamples(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "materialize.db")
    for index, outcome in enumerate(("success", "success", "failed")):
        _record_pytest_task(lat, f"task-{index}", outcome=outcome)

    first = lat.learn(
        min_support=3,
        min_steps=2,
        max_steps=2,
        materialize=True,
    )
    target = next(
        row
        for row in first["candidates"]
        if row["steps"]
        == ["tool:pytest:tool.started", "tool:pytest:tool.completed"]
    )
    assert target["lifecycle"] == "candidate"
    assert target["evidence"]["failures"] == 1
    assert target["evidence"]["counterexample_task_ids"] == ["task-2"]
    materialized = next(
        row for row in first["materialized"] if row["signature"] == target["signature"]
    )
    pattern = lat.get(materialized["pattern_id"])
    assert pattern is not None
    assert pattern.kind.value == "sequence"
    assert pattern.metadata["lifecycle"] == "candidate"
    assert "Counterexamples retained" in pattern.body

    second = lat.learn(
        min_support=3,
        min_steps=2,
        max_steps=2,
        materialize=True,
    )
    again = next(
        row
        for row in second["materialized"]
        if row["signature"] == target["signature"]
    )
    assert again["pattern_id"] == materialized["pattern_id"]

    plan = lat.plan(
        "run the focused pytest regression workflow",
        observations=["need tool started and completed evidence"],
        domain="process",
        limit=12,
    )
    rows = {row["pattern_id"]: row for row in plan["recommendations"]}
    ids = set(rows)
    assert pattern.id in ids
    assert rows[pattern.id]["actionable"] is False
    assert "Review-only" in rows[pattern.id]["action"]


def test_repeated_events_in_one_task_do_not_fake_support(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "support.db")
    lat.open_task("one task", task_id="single")
    for index in range(4):
        lat.record_event(
            "tool.started",
            f"run {index} started",
            task_id="single",
            tool="pytest",
        )
        lat.record_event(
            "tool.completed",
            f"run {index} completed",
            task_id="single",
            tool="pytest",
        )
    lat.close_task("single", outcome="success", summary="one task with repeated runs")
    learned = lat.learn(min_support=2, min_steps=2, max_steps=2)
    assert learned["task_traces"] == 1
    assert learned["candidates"] == []
