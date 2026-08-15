"""Locked HermesInsight.perceive_card Space-cable contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_insight import HermesInsight
from hermes_insight.card import CARD_KEYS


@pytest.fixture()
def lat(tmp_path: Path) -> HermesInsight:
    return HermesInsight(db_path=tmp_path / "card.db")


def test_feature_detect_is_method_on_harness():
    assert hasattr(HermesInsight, "perceive_card")
    assert callable(getattr(HermesInsight, "perceive_card"))


@pytest.mark.parametrize("load", ["high", "protect"])
def test_high_protect_returns_empty_card(lat: HermesInsight, load: str):
    def boom(*args, **kwargs):
        raise AssertionError("perceive must not run under high/protect load")

    lat.perceive = boom  # type: ignore[method-assign]
    out = lat.perceive_card("two workers share one bot credential", load=load)
    assert set(out) == set(CARD_KEYS)
    assert out["skipped"] is True
    assert out["reason"] == "high_load"
    assert out["card"] == ""
    assert out["usable"] is False
    assert out["lever"] == ""
    assert out["rule"] == ""
    assert out["action_hint"] == ""
    assert "matches" not in out
    assert "hops" not in out
    assert "brief" not in out


def test_mid_card_is_bounded_and_has_no_lattice_dump(lat: HermesInsight):
    lat.bootstrap()
    out = lat.perceive_card(
        "two workers share one bot credential and long-poll conflicts fire",
        load="mid",
        observations=["409 conflict", "duplicate getUpdates consumers"],
    )
    assert set(out) == set(CARD_KEYS)
    assert out["skipped"] is False
    assert out["ok"] is True
    assert len(out["card"]) <= 400
    assert "matches" not in out
    assert "hops" not in out
    assert "brief" not in out
    assert "experiences" not in out


def test_card_formats_fields_not_unbounded_perceive_card(lat: HermesInsight):
    def fake_perceive(goal, **kwargs):
        assert kwargs.get("deep") is False
        assert kwargs.get("log_experience") is False
        assert kwargs.get("limit") == 1
        return {
            "usable": True,
            "lever": "retry",
            "action_hint": "add jitter",
            "matches": [
                {"title": "skill: inventory", "kind": "skill"},
                {"title": "retry with jitter", "kind": "rule"},
            ],
            "card": "UNBOUNDED " * 80,
            "brief": "do not leak",
            "hops": [{"title": "nope"}],
            "experiences": [{"title": "nope"}],
        }

    lat.perceive = fake_perceive  # type: ignore[method-assign]
    out = lat.perceive_card("retries stampede origin", load="mid")
    assert set(out) == set(CARD_KEYS)
    assert out["rule"] == "retry with jitter"
    assert out["lever"] == "retry"
    assert out["usable"] is True
    assert out["action_hint"] == "add jitter"
    assert "UNBOUNDED" not in out["card"]
    assert "do not leak" not in out["card"]
    assert "lever=retry" in out["card"]
    assert "rule=retry with jitter" in out["card"]
    assert len(out["card"]) <= 400


def test_rule_falls_back_to_top_title(lat: HermesInsight):
    def fake_perceive(goal, **kwargs):
        return {
            "usable": True,
            "lever": "token",
            "action_hint": "one consumer",
            "matches": [{"title": "credential single-consumer", "kind": "prototype"}],
        }

    lat.perceive = fake_perceive  # type: ignore[method-assign]
    out = lat.perceive_card("shared bot token", load="mid")
    assert out["rule"] == "credential single-consumer"


def test_mid_does_not_call_plan(lat: HermesInsight):
    lat.bootstrap()

    def boom(*args, **kwargs):
        raise AssertionError("plan must not be called")

    lat.plan = boom  # type: ignore[method-assign]
    out = lat.perceive_card(
        "two workers share one bot credential and long-poll conflicts fire",
        load="mid",
    )
    assert "matches" not in out
    assert "hops" not in out
    assert "brief" not in out
