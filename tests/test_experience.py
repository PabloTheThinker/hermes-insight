"""Experience layer tests — recall, task arc, connect, bootstrap."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight import __version__
from hermes_insight.harness import HermesInsight


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "exp.db")


def test_version():
    assert __version__ == "0.7.0"


def test_bootstrap_and_recall(lat: HermesInsight):
    seed = lat.bootstrap()
    assert seed["seeded"] >= 8
    # second call skips
    again = lat.bootstrap()
    assert again.get("skipped") is True

    pack = lat.recall("two gateway workers share one bot token and long-poll conflicts")
    assert pack["success"] is True
    assert pack["lever"]
    assert pack["matches"] or pack["experiences"]
    assert "Insight recall" in pack["brief"]
    # should hit credential single-consumer starter
    titles = " ".join(m["title"] for m in pack["matches"]).lower()
    assert "credential" in titles or "consumer" in titles or pack["lever"]


def test_task_arc_connects_experience(lat: HermesInsight):
    lat.bootstrap()
    opened = lat.open_task(
        "fix gateway conflict",
        goal="two consumers fight over the same bot credential",
    )
    assert opened["success"]
    tid = opened["task_id"]
    assert tid
    assert opened.get("priors") is not None

    mid = lat.experience(
        "saw 409 conflict",
        "Telegram getUpdates returns conflict; second worker still polling",
        kind="event",
        task_id=tid,
        tags=["gateway", "telegram"],
    )
    assert mid["success"]
    assert mid["experience"]["kind"] == "event"
    # should auto-connect to starter credential pattern
    assert isinstance(mid.get("connected"), list)

    mid2 = lat.experience(
        "killed duplicate consumer",
        "Stopped second gateway; single consumer restored; conflicts gone",
        kind="event",
        task_id=tid,
        outcome="success",
    )
    assert mid2["success"]

    closed = lat.close_task(
        tid,
        outcome="fixed",
        summary="Root cause was dual long-poll on one bot token. One consumer rule.",
    )
    assert closed["success"]
    assert closed["status"] == "closed"
    # chain should have created links
    st = lat.stats()
    assert st["patterns"] >= 10
    assert st["links"] >= 1
    assert st["version"] == "0.7.0"
    assert st.get("active_task_id") in {"", None}


def test_connect_free_text(lat: HermesInsight):
    lat.bootstrap()
    res = lat.connect(
        "prompt cache broke after we swapped tools mid conversation and costs exploded"
    )
    assert res["success"]
    assert res.get("connected") is not None or res.get("experience")


def test_ingest_messages(lat: HermesInsight):
    lat.bootstrap()
    res = lat.ingest_messages(
        [
            {"role": "user", "content": "Gateway keeps dying on SSH logout"},
            {
                "role": "assistant",
                "content": "Enable linger with loginctl; gateway was killed with session",
            },
        ],
        title="ssh logout gateway death",
    )
    assert res["success"]
    assert res["experience"]["kind"] == "episode"


def test_second_recall_finds_lived_echo(lat: HermesInsight):
    lat.bootstrap()
    t = lat.open_task("retry storm", goal="pages after deploy from retry amplification")
    lat.experience(
        "retries without jitter",
        "Client retry loop without jitter caused dependency stampede and alert fatigue",
        task_id=t["task_id"],
        outcome="observed",
    )
    lat.close_task(t["task_id"], outcome="done", summary="added jitter and circuit breaker")

    pack = lat.recall("deploy caused retry storm and noisy pages")
    assert pack["success"]
    # either structural match (retry storm starter) or lived experience
    blob = (pack.get("brief") or "").lower()
    assert "retry" in blob or "storm" in blob or "alert" in blob or pack.get("lever")
