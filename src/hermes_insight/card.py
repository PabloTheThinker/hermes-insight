"""Bounded perceive-card cable for Hermespace.

Space feature-detects ``HermesInsight.perceive_card`` via ``hasattr``.
Not a MemoryProvider. Does not dump the lattice. Does not call plan().
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Union

CARD_KEYS = (
    "ok",
    "usable",
    "lever",
    "rule",
    "action_hint",
    "card",
    "skipped",
    "reason",
)
_CARD_LIMIT = 400


def normalize_load(load: Union[str, float, None] = "mid") -> str:
    if load is None:
        return "mid"
    if isinstance(load, (int, float)):
        value = float(load)
        if value >= 0.85:
            return "protect"
        if value >= 0.65:
            return "high"
        if value >= 0.35:
            return "mid"
        return "low"
    level = str(load).strip().lower()
    if level in {"protected", "mono", "monotropic"}:
        return "protect"
    if level in {"low", "mid", "high", "protect"}:
        return level
    return "mid"


def _payload(
    *,
    ok: bool,
    usable: bool = False,
    lever: str = "",
    rule: str = "",
    action_hint: str = "",
    card: str = "",
    skipped: bool = False,
    reason: str = "",
) -> Dict[str, Any]:
    return {
        "ok": ok,
        "usable": usable,
        "lever": lever,
        "rule": rule,
        "action_hint": action_hint,
        "card": card,
        "skipped": skipped,
        "reason": reason,
    }


def _rule_title(matches: Any) -> str:
    if not isinstance(matches, list):
        return ""
    fallback = ""
    for match in matches:
        if not isinstance(match, dict):
            continue
        title = str(match.get("title") or "").strip()
        if not title:
            continue
        if not fallback:
            fallback = title
        if str(match.get("kind") or "") == "rule":
            return title
    return fallback


def _format_card(lever: str, rule: str, usable: bool, action_hint: str) -> str:
    text = (
        f"lever={lever}"
        f" · rule={rule}"
        f" · usable={str(usable).lower()}"
        f" — {action_hint}"
    ).strip()
    return text[:_CARD_LIMIT]


def build_perceive_card(
    lat: Any,
    goal: str,
    *,
    load: Union[str, float, None] = "mid",
    observations: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Return the locked Space-cable dict. Never raises."""
    if normalize_load(load) in {"high", "protect"}:
        return _payload(ok=True, skipped=True, reason="high_load")

    try:
        pack = lat.perceive(
            goal,
            observations=observations,
            deep=False,
            log_experience=False,
            limit=1,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft organ surface
        return _payload(ok=False, skipped=True, reason=str(exc)[:200])

    if not isinstance(pack, dict):
        return _payload(ok=False, skipped=True, reason="invalid_perceive")

    lever = str(pack.get("lever") or "")
    usable = bool(pack.get("usable"))
    action_hint = str(pack.get("action_hint") or "")
    rule = _rule_title(pack.get("matches"))
    return _payload(
        ok=True,
        usable=usable,
        lever=lever,
        rule=rule,
        action_hint=action_hint,
        card=_format_card(lever, rule, usable, action_hint),
        skipped=False,
        reason="",
    )
