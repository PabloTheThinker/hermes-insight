"""Distillation — find the actual variable.

Neurodivergent-style strength: strip a situation to the structural lever
that actually moves the outcome, discard scenic noise.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Optional, Sequence

from pattern_lattice.features import extract_features, tokenize
from pattern_lattice.models import Distillation, MatchResult, Pattern


_NOISE_HINTS = {
    "maybe",
    "somehow",
    "just",
    "really",
    "very",
    "thing",
    "stuff",
    "issue",
    "problem",
    "situation",
    "basically",
    "actually",  # ironic but often filler
}


def distill(
    text: str,
    *,
    matches: Sequence[MatchResult] | None = None,
    known: Sequence[Pattern] | None = None,
    max_supporting: int = 6,
) -> Distillation:
    """Extract a core variable + principle from free text and optional matches."""
    feats = extract_features(text, max_features=40)
    tokens = tokenize(text)

    # Boost features that appear in strong matches
    boost: Counter[str] = Counter()
    for m in matches or []:
        for f in m.shared_features:
            boost[f.lower()] += 1.0 + m.score
        for f in m.pattern.features[:12]:
            boost[f.lower()] += 0.4 * m.score
        boost.update(t for t in tokenize(m.pattern.title)[:8])

    for p in known or []:
        for f in p.features[:8]:
            boost[f.lower()] += 0.2 * p.strength

    scored: List[tuple[float, str]] = []
    for f in feats:
        fl = f.lower()
        if fl in _NOISE_HINTS:
            continue
        score = 1.0 + boost.get(fl, 0.0)
        # prefer multi-token structural cues and mid-length identifiers
        if "_" in fl:
            score += 0.5
        if any(ch.isdigit() for ch in fl):
            score += 0.15
        if 4 <= len(fl) <= 24:
            score += 0.2
        scored.append((score, fl))

    scored.sort(reverse=True)
    ranked = [f for _, f in scored]
    actual = ranked[0] if ranked else (tokens[0] if tokens else "unknown")
    supporting = ranked[1 : max_supporting + 1]

    discarded: List[str] = []
    for t in tokens:
        if t not in ranked[: max_supporting + 1] and t in _NOISE_HINTS:
            discarded.append(t)
    # also mark low-score features as discarded noise candidates
    for _, f in scored[max_supporting + 3 : max_supporting + 10]:
        if f not in discarded:
            discarded.append(f)

    principle = _principle(actual, supporting, text)
    actionable = _actionable(actual, principle)
    confidence = _confidence(actual, supporting, matches)

    return Distillation(
        actual_variable=actual,
        supporting=supporting,
        discarded=discarded[:12],
        confidence=confidence,
        principle=principle,
        actionable=actionable,
    )


def _principle(actual: str, supporting: Sequence[str], text: str) -> str:
    sup = ", ".join(supporting[:4]) if supporting else "context factors"
    # Heuristic principle templates — agents can rewrite with an LLM later
    lower = text.lower()
    if any(k in lower for k in ("fail", "error", "bug", "break", "outage")):
        return (
            f"Failures cluster around `{actual}`; treat it as the controlling variable "
            f"before tuning peripheral factors ({sup})."
        )
    if any(k in lower for k in ("slow", "latency", "delay", "wait", "perf")):
        return (
            f"Performance is gated by `{actual}`; optimize or isolate that lever "
            f"rather than spreading effort across ({sup})."
        )
    if any(k in lower for k in ("people", "team", "user", "customer", "social")):
        return (
            f"Human/system dynamics turn on `{actual}`; other signals ({sup}) are secondary."
        )
    return (
        f"The structural lever is `{actual}`. Secondary structure: {sup}. "
        f"Solve for that variable to keep the rest of the system coherent."
    )


def _actionable(actual: str, principle: str) -> str:
    return f"Name, measure, and intervene on `{actual}` first. {principle}"


def _confidence(
    actual: str,
    supporting: Sequence[str],
    matches: Optional[Sequence[MatchResult]],
) -> float:
    c = 0.35
    if actual and actual != "unknown":
        c += 0.2
    if supporting:
        c += min(0.2, 0.04 * len(supporting))
    if matches:
        top = matches[0].score if matches else 0.0
        c += 0.25 * top
    return float(max(0.05, min(0.95, c)))
