"""Native typed events and environment snapshots."""

from __future__ import annotations

from pathlib import Path

from hermes_insight import HermesInsight
from hermes_insight.models import LinkKind


def test_environment_snapshot_tracks_structural_delta(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    lat = HermesInsight(db_path=tmp_path / "observe.db")

    first = lat.snapshot_environment(project, include_tools=False)
    assert first["success"] is True
    assert first["state"]["manifests"] == ["pyproject.toml"]
    assert first["delta"]["changed_fields"] == ["initial"]

    (project / "package.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    second = lat.snapshot_environment(project, include_tools=False)
    assert second["success"] is True
    assert second["snapshot_id"] != first["snapshot_id"]
    assert second["previous_snapshot_id"] == first["snapshot_id"]
    assert "manifests" in second["delta"]["changed_fields"]

    links = lat.store.links_for(first["snapshot_id"], limit=10)
    assert any(
        link.kind == LinkKind.PRECEDES and link.target_id == second["snapshot_id"]
        for link in links
    )


def test_typed_event_preserves_provenance_and_scrubs_nested_data(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    lat = HermesInsight(db_path=tmp_path / "events.db", agent_id="worker")
    snapshot = lat.snapshot_environment(project, include_tools=False)

    first = lat.record_event(
        "tool.started",
        "run focused test",
        trace_id="trace-1",
        tool="pytest",
        details={"command": "pytest tests/test_one.py"},
        provenance={"source": "tool-hook"},
        trust_class="workspace",
    )
    assert first["success"] is True

    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    second = lat.record_event(
        "tool.completed",
        f"test completed with token={secret}",
        parent_event_id=first["event_id"],
        trace_id="trace-1",
        tool="pytest",
        status="success",
        outcome="passed",
        duration_ms=12.5,
        details={
            "nested": [{"path": "/home/someone/private", "credential": secret}],
            "failures": 0,
        },
    )
    assert second["success"] is True
    body = second["event"]["body"]
    assert secret not in body
    assert "/home/someone" not in body
    assert second["envelope"]["environment_snapshot_id"] == snapshot["snapshot_id"]
    assert second["envelope"]["schema"] == "hermes-insight.event.v1"
    assert second["envelope"]["agent_id"] == "worker"

    links = lat.store.links_for(second["event_id"], limit=10)
    assert any(link.kind == LinkKind.PRECEDES for link in links)
    assert any(link.kind == LinkKind.OBSERVED_IN for link in links)


def test_plan_includes_latest_environment_state(tmp_path: Path):
    project = tmp_path / "workspace"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    lat = HermesInsight(db_path=tmp_path / "plan-env.db")
    snapshot = lat.snapshot_environment(project, include_tools=False)

    plan = lat.plan(
        "timeouts amplify retry load after deployment",
        observations=["clients have no jitter"],
        domain="system",
    )
    assert plan["environment_state"]["snapshot_id"] == snapshot["snapshot_id"]
    assert plan["environment_state"]["root_name"] == "workspace"
    assert "Environment:" in plan["card"]
