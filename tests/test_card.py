"""Bounded perceive-card organ — Space feature-detect surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight import HermesInsight, perceive_card
from hermes_insight.card import CARD_API_VERSION, perceive_card as card_fn


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "card.db")


def test_feature_detect_public_export():
    assert callable(perceive_card)
    assert perceive_card is card_fn
    assert CARD_API_VERSION == "1.0"


def test_empty_query_fail_soft(lat: HermesInsight):
    out = perceive_card("", lattice=lat)
    assert out["ok"] is False
    assert out["usable"] is False
    assert out["lever"] == ""
    assert out["top_rule"] == ""
    assert out["action_hint"] == ""
    assert out["error"] == "empty_query"


def test_broken_lattice_fail_soft():
    class Broken:
        def perceive(self, *args, **kwargs):
            raise RuntimeError("db locked")

    out = perceive_card("retries stampede origin", lattice=Broken())
    assert out["ok"] is False
    assert out["usable"] is False
    assert "db locked" in out.get("error", "")


def test_perceive_card_does_not_call_plan(lat: HermesInsight):
    lat.bootstrap()

    def boom(*args, **kwargs):
        raise AssertionError("plan must not be called")

    lat.plan = boom  # type: ignore[method-assign]
    out = perceive_card(
        "two workers share one bot credential and long-poll conflicts fire",
        observations=["409 conflict"],
        lattice=lat,
    )
    assert out["ok"] is True
    assert set(out) >= {"lever", "top_rule", "usable", "action_hint", "text"}
    assert "matches" not in out
    assert "card" not in out
    assert "hops" not in out
    assert "brief" not in out


def test_usable_card_is_bounded(lat: HermesInsight):
    lat.bootstrap()
    out = perceive_card(
        "two workers share one bot credential and long-poll conflicts fire",
        observations=["409 conflict", "duplicate getUpdates consumers"],
        lattice=lat,
        load="protect",
    )
    assert out["ok"] is True
    assert out["usable"] is True
    assert out["lever"]
    assert out["top_rule"]
    assert out["action_hint"]
    assert out["load"] == "protect"
    assert len(out["action_hint"]) <= 80
    assert len(out["text"]) <= 160
    assert len(out["top_rule"]) <= 80


def test_thin_query_not_usable(lat: HermesInsight):
    lat.bootstrap()
    out = perceive_card("something is wrong", lattice=lat)
    assert out["ok"] is True
    assert out["usable"] is False
    assert out["lever"] in {"insufficient_signal", "system"}


def test_db_path_constructs_lattice(tmp_path: Path):
    db = tmp_path / "via-path.db"
    out = perceive_card("x", db_path=str(db))
    assert out["ok"] is True
    assert "usable" in out
    assert db.exists()
