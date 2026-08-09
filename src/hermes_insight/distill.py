"""Distillation — find the actual variable.

Neurodivergent-style strength: strip a situation to the structural lever
that actually moves the outcome, discard scenic noise.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence

from hermes_insight.features import extract_features, stem_token, tokenize
from hermes_insight.match import expand_query_features
from hermes_insight.models import Distillation, MatchResult, Pattern

# Ultra-common tokens that rarely are THE lever in multi-module corpora
_NOISE_HINTS = {
    "maybe", "somehow", "just", "really", "very", "thing", "stuff", "issue",
    "problem", "situation", "basically", "actually", "agent", "user", "system",
    "code", "file", "data", "value", "type", "name", "text", "info", "item",
    "object", "class", "function", "method", "module", "import", "return",
    "true", "false", "none", "self", "this", "that", "with", "from", "into",
    "need", "required", "using", "used", "use", "make", "get", "set", "add",
    "long", "lived", "process", "between", "identity", "home", "directory",
    "enabl", "enable", "enabled", "service", "unit", "level",
}

# Prefer these if present — high-leverage ops/structure vocabulary
_LEVER_PRIORS = {
    "credential", "token", "isolation", "linger", "longpoll", "consumer",
    "conflict", "profile", "retry", "timeout", "circuit", "cache", "stampede",
    "backoff", "jitter", "webhook", "tenant", "compartment", "auth", "secret",
    "singleflight", "race", "deadlock", "throttle", "quota", "session",
}


def distill(
    text: str,
    *,
    matches: Sequence[MatchResult] | None = None,
    known: Sequence[Pattern] | None = None,
    max_supporting: int = 6,
) -> Distillation:
    """Extract a core variable + principle from free text and optional matches."""
    feats = expand_query_features(extract_features(text, max_features=48))
    tokens = tokenize(text)

    boost: Dict[str, float] = {}
    def _badd(k: str, v: float) -> None:
        boost[k] = boost.get(k, 0.0) + v

    for m in matches or []:
        w = 1.0 + max(m.score, 0.0) * 2.0
        for f in m.shared_features:
            _badd(stem_token(f), w)
        for f in m.pattern.features[:16]:
            _badd(stem_token(f), 0.35 * m.score)
        for t in m.pattern.tags[:8]:
            _badd(stem_token(t), 0.5 * m.score)
        for t in tokenize(m.pattern.title)[:10]:
            _badd(t, 0.25 * m.score)

    for p in known or []:
        for f in p.features[:8]:
            _badd(stem_token(f), 0.15 * p.strength)

    # corpus rarity proxy: features that appear in fewer match titles score higher
    title_df: Counter[str] = Counter()
    for m in matches or []:
        for t in set(tokenize(m.pattern.title + " " + " ".join(m.pattern.features[:20]))):
            title_df[t] += 1
    n_docs = max(len(matches or []), 1)

    scored: List[tuple[float, str]] = []
    for f in feats:
        fl = stem_token(f)
        if fl in _NOISE_HINTS or len(fl) < 3:
            continue
        score = 1.0 + boost.get(fl, 0.0)
        if fl in _LEVER_PRIORS:
            score += 2.2
        # rarity among matched docs
        df = title_df.get(fl, 0)
        if df:
            score += 1.2 * (1.0 - (df / n_docs))
        else:
            score += 0.4  # present in query but not ubiquitous in matches
        if "_" in fl:
            score += 0.4
        if 4 <= len(fl) <= 22:
            score += 0.25
        # multi-word structural bigrams from extract_features
        if fl.count("_") == 1:
            score += 0.15
        scored.append((score, fl))

    # also consider pure lever priors found in text even if feature extract missed
    blob = " ".join(tokens)
    for prior in _LEVER_PRIORS:
        if prior in blob or prior in feats:
            if not any(s == prior for _, s in scored):
                scored.append((2.5 + boost.get(prior, 0.0), prior))

    scored.sort(reverse=True)
    ranked = [f for _, f in scored]
    actual = ranked[0] if ranked else (tokens[0] if tokens else "unknown")
    supporting = ranked[1 : max_supporting + 1]

    discarded: List[str] = []
    for t in tokens:
        if t in _NOISE_HINTS and t not in ranked[: max_supporting + 1]:
            discarded.append(t)
    for _, f in scored[max_supporting + 3 : max_supporting + 12]:
        if f not in discarded:
            discarded.append(f)

    principle = _principle(actual, supporting, text)
    actionable = f"Name, measure, and intervene on `{actual}` first. {principle}"
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
    lower = text.lower()
    if actual in {"credential", "token", "secret", "auth"}:
        return (
            f"Access identity is gated by `{actual}`; enforce single-consumer and isolation "
            f"before tuning peripherals ({sup})."
        )
    if actual in {"isolation", "profile", "tenant", "compartment"}:
        return (
            f"Boundary failure centers on `{actual}`; separate homes/credentials/scopes "
            f"before feature work ({sup})."
        )
    if actual in {"linger", "session", "logout"}:
        return (
            f"Process lifetime depends on `{actual}`; detach services from interactive shells "
            f"({sup})."
        )
    if actual in {"consumer", "longpoll", "conflict", "race"}:
        return (
            f"Contention clusters on `{actual}`; ensure exactly-one active consumer "
            f"and eliminate duplicate pollers ({sup})."
        )
    if any(k in lower for k in ("fail", "error", "bug", "break", "outage", "conflict")):
        return (
            f"Failures cluster around `{actual}`; treat it as the controlling variable "
            f"before tuning peripheral factors ({sup})."
        )
    if any(k in lower for k in ("slow", "latency", "delay", "timeout", "perf")):
        return (
            f"Performance is gated by `{actual}`; optimize or isolate that lever "
            f"rather than spreading effort across ({sup})."
        )
    return (
        f"The structural lever is `{actual}`. Secondary structure: {sup}. "
        f"Solve for that variable to keep the rest of the system coherent."
    )


def _confidence(
    actual: str,
    supporting: Sequence[str],
    matches: Optional[Sequence[MatchResult]],
) -> float:
    c = 0.35
    if actual and actual != "unknown":
        c += 0.15
    if actual in _LEVER_PRIORS:
        c += 0.15
    if supporting:
        c += min(0.15, 0.03 * len(supporting))
    if matches:
        c += 0.25 * matches[0].score
    return float(max(0.05, min(0.95, c)))
