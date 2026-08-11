"""Experience-grounded planning and explicit outcome attribution tests."""

from __future__ import annotations

from pathlib import Path

from hermes_insight import HermesInsight
from hermes_insight.models import LinkKind


def test_plan_ranks_explicit_success_over_failure(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "planner.db")
    good = lat.ingest(
        "skill:retry-with-jitter",
        "Inspect retry ownership, add bounded exponential backoff with jitter, then load test.",
        kind="skill",
        domain="skill",
        features=["retry", "backoff", "jitter", "timeout", "load"],
        tags=["skill", "retry"],
        metadata={"skill_name": "retry-with-jitter", "fabric": "skill"},
        confidence=0.8,
        link=False,
    )
    bad = lat.ingest(
        "skill:retry-immediately",
        "Retry every timeout immediately without a bound.",
        kind="skill",
        domain="skill",
        features=["retry", "backoff", "jitter", "timeout", "load"],
        tags=["skill", "retry"],
        metadata={"skill_name": "retry-immediately", "fabric": "skill"},
        confidence=0.8,
        link=False,
    )

    for index in range(3):
        opened = lat.open_task(f"good retry run {index}", goal="stabilize timeout retries")
        lat.close_task(
            opened["task_id"],
            outcome="success",
            summary="bounded jitter stopped retry amplification",
            used_pattern_ids=[good.id],
        )
        opened = lat.open_task(f"bad retry run {index}", goal="stabilize timeout retries")
        lat.close_task(
            opened["task_id"],
            outcome="failed",
            summary="immediate retries amplified load",
            used_pattern_ids=[bad.id],
        )

    plan = lat.plan(
        "timeouts trigger retry amplification under load",
        observations=["clients need bounded backoff and jitter"],
        domain="skill",
        limit=10,
    )
    assert plan["success"] is True
    assert plan["usable"] is True
    rows = {row["pattern_id"]: row for row in plan["recommendations"]}
    assert rows[good.id]["outcome_evidence"]["successes"] == 3
    assert rows[good.id]["outcome_evidence"]["failures"] == 0
    assert rows[bad.id]["outcome_evidence"]["failures"] == 3
    assert rows[good.id]["reliability"] > rows[bad.id]["reliability"]
    assert rows[good.id]["score"] > rows[bad.id]["score"]
    assert good.id in plan["card"]

    applied = [
        link
        for link in lat.store.links_for(good.id, limit=20)
        if link.kind == LinkKind.APPLIED
    ]
    assert len(applied) == 3


def test_plan_exposes_local_affordances_without_execution(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "affordance.db")
    lat.ingest(
        "rule:inspect-tests-before-patch",
        "Inspect the failing test and its owning module before changing implementation.",
        kind="rule",
        domain="code",
        features=["test", "failure", "inspect", "patch", "code"],
        confidence=0.85,
        link=False,
    )
    tool = lat.ingest(
        "tool:test_runner",
        "Local test runner for focused regression checks.",
        kind="tool",
        domain="tool",
        features=["test", "runner", "regression", "failure"],
        metadata={"fabric": "tool", "tool_name": "test_runner"},
        link=False,
    )

    plan = lat.plan(
        "fix a regression in code after a focused test failure",
        observations=["need to inspect the owning module and rerun tests"],
        domain="code",
    )
    assert plan["success"] is True
    assert plan["recommendations"]
    affordances = {row["id"]: row for row in plan["environment_affordances"]}
    assert tool.id in affordances
    assert "Use tool" in affordances[tool.id]["invoke_hint"]
    assert plan["ability"] == "experience_grounded_planning"


def test_plan_refuses_thin_situation(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "thin.db")
    plan = lat.plan("broken")
    assert plan["success"] is True
    assert plan["usable"] is False
    assert plan["lever"] == "insufficient_signal"
