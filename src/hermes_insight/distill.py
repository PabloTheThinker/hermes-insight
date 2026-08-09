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

# Ultra-common tokens that rarely are THE lever — keep agent/model terms OUT of noise
_NOISE_HINTS = {
    "maybe", "somehow", "just", "really", "very", "thing", "stuff", "issue",
    "problem", "situation", "basically", "actually", "user", "system",
    "code", "file", "data", "value", "type", "name", "text", "info", "item",
    "object", "class", "function", "method", "module", "import", "return",
    "true", "false", "none", "self", "this", "that", "with", "from", "into",
    "need", "required", "using", "used", "use", "make", "get", "set", "add",
    "long", "lived", "process", "between", "identity", "home", "directory",
    "enabl", "enable", "enabled", "service", "unit", "level",
    "something", "anything", "everything", "nothing", "someth", "anyth",
    "wrong", "broken", "error", "bug", "fail", "failed", "weird", "strange",
    "happen", "going", "work", "works", "working",
}

# Incomplete / mangled stems that must never be the lever
_BAD_LEVERS = {
    "someth", "anyth", "everyth", "noth", "unknow", "variabl", "structur",
    "gener", "system", "thing", "stuff", "issue", "problem", "wrong", "broken",
}

# Prefer these if present — high-leverage ops/structure vocabulary
_LEVER_PRIORS = {
    "credential", "token", "isolation", "linger", "longpoll", "consumer",
    "conflict", "profile", "retry", "timeout", "circuit", "cache", "stampede",
    "backoff", "jitter", "webhook", "tenant", "compartment", "auth", "secret",
    "singleflight", "race", "deadlock", "throttle", "quota", "session",
    # AI agent / model field
    "agent", "model", "tool", "skill", "plugin", "context", "memory",
    "delegation", "inference", "embedding", "harness", "prompt", "toolset",
    "multi_agent", "eval", "subagent", "persona", "routing",
}


def distill(
    text: str,
    *,
    matches: Sequence[MatchResult] | None = None,
    known: Sequence[Pattern] | None = None,
    max_supporting: int = 6,
    domain_hint: str | None = None,
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
    ranked = [f for _, f in scored if f not in _BAD_LEVERS and len(f) >= 3]
    # Prefer lever priors when top candidates are weak scenic noise
    prior_hits = [f for f in ranked if f in _LEVER_PRIORS]
    if prior_hits and (not ranked or ranked[0] not in _LEVER_PRIORS):
        # promote first prior if scenic top is weak
        if not ranked or ranked[0] in _NOISE_HINTS or ranked[0] in _BAD_LEVERS:
            ranked = prior_hits + [f for f in ranked if f not in prior_hits]


    # Domain-conditioned lever priors
    _DOMAIN_PRIORS = {
        "multi_agent": ["compartment", "isolation", "profile", "agent", "delegation", "credential"],
        "agent": ["credential", "token", "profile", "cache", "tool", "skill", "session"],
        "skill": ["skill", "routing", "tool", "model", "procedure"],
        "model": ["model", "routing", "inference", "eval", "skill"],
        "system": ["retry", "timeout", "circuit", "cache", "credential", "consumer"],
        "code": ["retry", "cache", "timeout", "circuit", "auth", "token"],
        "experience": ["recurring", "catalogue", "recall", "failure"],
    }
    dpriors = _DOMAIN_PRIORS.get((domain_hint or "").lower(), [])
    for dp in reversed(dpriors):
        if dp in ranked:
            ranked = [dp] + [x for x in ranked if x != dp]
            break
        # soft promote if present in text/features
        if dp in feats or dp in blob:
            ranked = [dp] + [x for x in ranked if x != dp]
            break

    actual = ranked[0] if ranked else "insufficient_signal"
    if actual in _BAD_LEVERS or actual in _NOISE_HINTS:
        actual = prior_hits[0] if prior_hits else "insufficient_signal"

    # When a strong structural match exists, anchor the lever to that rule —
    # not a nearby scenic token (timeout vs retry, agent vs isolation, etc.).
    actual = refine_lever_from_matches(
        actual,
        matches=matches,
        domain_hint=domain_hint,
        query_features=set(feats) | set(tokens),
    )

    supporting = [f for f in ranked[1 : max_supporting + 1] if f != actual]

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


_GENERIC_LEVERS = {
    "agent",
    "model",
    "tool",
    "system",
    "procedure",
    "process",
    "service",
    "work",
    "load",
}


# Title → preferred lever when score is strong
_TITLE_LEVER_RULES: List[tuple[str, str]] = [
    ("retry storm", "retry"),
    ("retry", "retry"),
    ("skill routing", "skill"),
    ("skill dump", "skill"),
    ("skill from hard", "skill"),
    ("profile isolation", "isolation"),
    ("isolation wall", "isolation"),
    ("credential", "token"),
    ("single-consumer", "token"),
    ("single consumer", "token"),
    ("prompt cache", "cache"),
    ("token waist", "token"),
    ("tool schema", "token"),
    ("session interrupt", "session"),
    ("circuit", "circuit"),
    ("backoff", "backoff"),
    ("jitter", "jitter"),
]


def refine_lever_from_matches(
    distilled: str,
    *,
    matches: Sequence[MatchResult] | None,
    domain_hint: str | None = None,
    query_features: Optional[set] = None,
) -> str:
    """Prefer the controlling feature of a strong top match over a weak distill."""
    if not matches:
        return distilled or "insufficient_signal"
    top = matches[0]
    score = float(top.score or 0.0)
    if score < 0.45:
        # weak match — keep distilled unless it's garbage
        if distilled and distilled not in _BAD_LEVERS and distilled not in _NOISE_HINTS:
            return distilled
        return distilled or "insufficient_signal"

    title = (top.pattern.title or "").lower()
    shared = [stem_token(s) for s in (top.shared_features or []) if s]
    pat_feats = [stem_token(f) for f in (top.pattern.features or [])[:16] if f]
    qf = {stem_token(x) for x in (query_features or set()) if x}

    # 1) Title rules win when clear
    for needle, lever in _TITLE_LEVER_RULES:
        if needle in title:
            return lever

    # 2) Domain-specific preferred tokens present on the match
    domain_prefs = {
        "multi_agent": ["isolation", "compartment", "profile", "credential", "token"],
        "skill": ["skill", "routing", "procedure", "model"],
        "system": ["retry", "jitter", "backoff", "circuit", "timeout", "cache"],
        "agent": ["token", "credential", "cache", "session", "skill", "profile"],
        "code": ["retry", "cache", "timeout", "auth", "token"],
    }
    prefs = domain_prefs.get((domain_hint or top.pattern.domain.value or "").lower(), [])
    pool = shared + pat_feats
    for pref in prefs:
        if pref in pool or pref in qf:
            return pref

    # 3) Best non-generic shared feature that appears in the query
    for f in shared:
        if f in qf and f not in _GENERIC_LEVERS and f not in _BAD_LEVERS and len(f) >= 3:
            return f

    # 4) Pattern's own features (non-generic)
    for f in pat_feats:
        if f not in _GENERIC_LEVERS and f not in _BAD_LEVERS and len(f) >= 3:
            return f

    # 5) Keep distilled if it's specific; else first shared
    if distilled and distilled not in _GENERIC_LEVERS and distilled not in _BAD_LEVERS:
        return distilled
    for f in shared:
        if f not in _BAD_LEVERS and len(f) >= 3:
            return f
    return distilled or "insufficient_signal"


def _principle(actual: str, supporting: Sequence[str], text: str) -> str:
    sup = ", ".join(supporting[:4]) if supporting else "context factors"
    lower = text.lower()
    if actual in {"credential", "token", "secret", "auth"}:
        return (
            f"Agent identity/access is gated by `{actual}`; enforce single-consumer and "
            f"compartment isolation before tuning peripherals ({sup})."
        )
    if actual in {"agent", "profile", "compartment", "multi_agent"}:
        return (
            f"Fleet structure turns on `{actual}`; fix identity boundaries and delegation "
            f"paths before feature work ({sup})."
        )
    if actual in {"model", "inference", "routing", "embedding"}:
        return (
            f"Model route / inference is gated by `{actual}`; stabilize provider·model·eval "
            f"before prompt thrash ({sup})."
        )
    if actual in {"tool", "toolset", "skill", "plugin"}:
        return (
            f"Capability surface is controlled by `{actual}`; own the tool/skill graph "
            f"before adding more agents ({sup})."
        )
    if actual in {"context", "memory", "prompt", "session"}:
        return (
            f"State/context health hinges on `{actual}`; compress, compartment, or rewrite "
            f"policy before scaling turns ({sup})."
        )
    if actual in {"isolation", "tenant"}:
        return (
            f"Boundary failure centers on `{actual}`; separate homes/credentials/scopes "
            f"before feature work ({sup})."
        )
    if actual in {"linger", "session", "logout"}:
        return (
            f"Process lifetime depends on `{actual}`; detach agent runtimes from interactive shells "
            f"({sup})."
        )
    if actual in {"consumer", "longpoll", "conflict", "race", "delegation"}:
        return (
            f"Contention clusters on `{actual}`; ensure exactly-one active consumer or clear "
            f"delegation ownership ({sup})."
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
    if actual in {"unknown", "insufficient_signal", ""}:
        return 0.12
    c = 0.30
    if actual and actual not in _NOISE_HINTS and actual not in _BAD_LEVERS:
        c += 0.12
    if actual in _LEVER_PRIORS:
        c += 0.18
    if supporting:
        c += min(0.12, 0.03 * len(supporting))
    if matches:
        top = float(matches[0].score)
        c += 0.35 * top
        # penalize overconfidence when top match is weak
        if top < 0.2:
            c *= 0.75
    return float(max(0.05, min(0.95, c)))
