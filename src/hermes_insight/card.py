"""Bounded perceive-card organ for optional hosts (Hermespace).

Space feature-detects ``perceive_card`` the way it feature-detects Cube.
Not a MemoryProvider. Does not dump the lattice. Does not call plan().
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Union

CARD_API_VERSION = "1.0"

# Character budgets (Cube-aligned load names: low / mid / high / protect).
_HINT_CHARS = {
    "low": 280,
    "mid": 200,
    "high": 120,
    "protect": 80,
}
_TEXT_CHARS = {
    "low": 420,
    "mid": 320,
    "high": 220,
    "protect": 160,
}
_RULE_CHARS = 80


def _normalize_load(load: Union[str, float, None]) -> str:
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
    if level in _HINT_CHARS:
        return level
    if level in {"protected", "mono", "monotropic"}:
        return "protect"
    return "mid"


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


def _empty(*, error: str = "", load_level: str = "mid") -> Dict[str, Any]:
    card: Dict[str, Any] = {
        "ok": False,
        "usable": False,
        "lever": "",
        "top_rule": "",
        "action_hint": "",
        "text": "",
        "load": load_level,
        "api_version": CARD_API_VERSION,
    }
    if error:
        card["error"] = error
    return card


def _top_rule(matches: Any) -> str:
    if not isinstance(matches, list):
        return ""
    fallback = ""
    for match in matches:
        if not isinstance(match, dict):
            continue
        title = str(match.get("title") or "").strip()
        if not title:
            continue
        kind = str(match.get("kind") or "")
        if not fallback:
            fallback = title
        if kind == "rule" or not title.startswith("skill:"):
            return title
    return fallback


def perceive_card(
    query: str,
    *,
    load: Union[str, float, None] = None,
    observations: Optional[Sequence[str]] = None,
    lattice: Any = None,
    db_path: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Bounded pattern-recognition card for optional hosts.

    Feature-detect::

        try:
            from hermes_insight import perceive_card
        except ImportError:
            perceive_card = None

    Returns a tiny dict (never the lattice): ``lever``, ``top_rule``,
    ``usable``, ``action_hint``, plus a short ``text`` line for inject.
    Fail-soft: never raises. Does not call ``insight_plan`` / ``plan()``.
    """
    level = _normalize_load(load)
    situation = (query or "").strip()
    if not situation:
        return _empty(error="empty_query", load_level=level)

    try:
        lat = lattice
        if lat is None:
            from hermes_insight.harness import HermesInsight

            lat = HermesInsight(db_path=db_path, agent_id=agent_id)
        pack = lat.perceive(
            situation,
            observations=list(observations or []),
            deep=False,
            log_experience=False,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft organ surface
        return _empty(error=str(exc)[:200], load_level=level)

    if not isinstance(pack, dict):
        return _empty(error="invalid_perceive", load_level=level)

    lever = str(pack.get("lever") or "")
    usable = bool(pack.get("usable"))
    hint = _clip(str(pack.get("action_hint") or ""), _HINT_CHARS[level])
    top_rule = _clip(_top_rule(pack.get("matches")), _RULE_CHARS)

    if usable and lever:
        text = f"lever=`{lever}`"
        if top_rule:
            text += f" · rule={top_rule}"
        if hint:
            text += f" — {hint}"
    elif lever == "insufficient_signal":
        text = "Insight: needs more signal"
    else:
        text = f"Insight: lever=`{lever or 'unknown'}` (not usable)"

    return {
        "ok": True,
        "usable": usable,
        "lever": lever,
        "top_rule": top_rule,
        "action_hint": hint,
        "text": _clip(text, _TEXT_CHARS[level]),
        "load": level,
        "api_version": CARD_API_VERSION,
    }
