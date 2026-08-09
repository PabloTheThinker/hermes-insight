"""Improved hybrid matching with IDF, path boosts, and ops synonym expansion."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from hermes_insight.features import jaccard, normalize_text, overlap_list, stem_token, tokenize
from hermes_insight.models import MatchResult, Pattern, PatternKind

# Domain synonym expansion — structural rhymes agents should catch
_SYNONYMS: Dict[str, Set[str]] = {
    "credential": {"token", "secret", "key", "auth", "password", "bot"},
    "token": {"credential", "secret", "bot", "auth"},
    "isolation": {"separate", "compartment", "sandbox", "profile", "tenant"},
    "profile": {"tenant", "home", "isolation", "identity", "agent"},
    "linger": {"systemd", "lingering", "session", "logout", "ssh"},
    "longpoll": {"polling", "getupdates", "webhook", "consumer"},
    "consumer": {"worker", "listener", "subscriber", "poll"},
    "conflict": {"collision", "duplicate", "race", "contention"},
    "retry": {"backoff", "jitter", "transient", "timeout"},
    "timeout": {"deadline", "latency", "slow", "hang"},
    "circuit": {"breaker", "bulkhead", "failfast"},
    "cache": {"ttl", "stampede", "singleflight", "memo"},
}


def expand_query_features(features: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for f in features:
        fl = stem_token(f)
        if fl not in seen:
            seen.add(fl)
            out.append(fl)
        for syn in _SYNONYMS.get(fl, ()):
            s = stem_token(syn)
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


def build_idf(patterns: Sequence[Pattern]) -> Dict[str, float]:
    """Inverse document frequency over pattern feature universes."""
    df: Counter[str] = Counter()
    n = max(len(patterns), 1)
    for p in patterns:
        uni = set(_universe(p))
        for t in uni:
            df[t] += 1
    idf: Dict[str, float] = {}
    for t, c in df.items():
        idf[t] = math.log(1.0 + n / (1.0 + c)) + 0.5
    return idf


def _universe(pattern: Pattern) -> List[str]:
    uni: List[str] = list(pattern.features)
    uni.extend(pattern.tags)
    uni.extend(tokenize(pattern.title))
    uni.extend(tokenize(pattern.body)[:32])
    # metadata symbols if present
    meta = pattern.metadata or {}
    for s in meta.get("symbols") or []:
        uni.append(stem_token(str(s)))
        uni.extend(tokenize(str(s).replace("_", " ")))
    for im in meta.get("imports") or []:
        uni.append(stem_token(str(im)))
    for pp in meta.get("path_parts") or []:
        uni.append(stem_token(str(pp)))
    seen: Set[str] = set()
    out: List[str] = []
    for f in uni:
        fl = str(f).lower()
        if fl in seen or len(fl) < 2:
            continue
        seen.add(fl)
        out.append(fl)
    return out


def weighted_overlap(
    query_features: Sequence[str],
    pattern: Pattern,
    idf: Optional[Dict[str, float]] = None,
) -> Tuple[float, List[str]]:
    q = [stem_token(x) for x in query_features]
    qset = set(q)
    uni = _universe(pattern)
    uset = set(uni)
    shared = [t for t in q if t in uset]
    if not shared and not qset:
        return 0.0, []
    idf = idf or {}
    num = sum(idf.get(t, 1.0) for t in shared)
    den = sum(idf.get(t, 1.0) for t in qset) or 1.0
    # also reward rare features present in pattern even if query used synonym form
    return min(1.0, num / den), shared


def template_score(query: str, pattern: Pattern) -> float:
    q = normalize_text(query)
    if not q:
        return 0.0
    title = normalize_text(pattern.title)
    body = normalize_text(pattern.body)
    if q == title or q == body:
        return 1.0
    if title and (title in q or q in title):
        return 0.85
    # phrase hits on path-like titles
    qt, pt = set(tokenize(query)), set(tokenize(pattern.title + " " + pattern.body[:400]))
    if not qt or not pt:
        return 0.0
    return len(qt & pt) / max(len(qt), 1) * 0.75


def prototype_score(
    query_features: Sequence[str],
    pattern: Pattern,
    idf: Optional[Dict[str, float]] = None,
) -> float:
    w, _ = weighted_overlap(query_features, pattern, idf)
    prior = 0.08 * pattern.strength
    kind_boost = 0.04 if pattern.kind in (PatternKind.PROTOTYPE, PatternKind.RULE, PatternKind.SYNTHESIS) else 0.0
    return min(1.0, w + prior + kind_boost)


def feature_score(
    query_features: Sequence[str],
    pattern: Pattern,
    idf: Optional[Dict[str, float]] = None,
) -> Tuple[float, List[str]]:
    w, shared = weighted_overlap(query_features, pattern, idf)
    if not shared:
        return jaccard(query_features, _universe(pattern)) * 0.45, []
    qset = set(stem_token(x) for x in query_features)
    precision = len(set(shared)) / max(len(qset), 1)
    recall = len(set(shared)) / max(len(set(_universe(pattern))), 1)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    # blend IDF-weighted overlap with f1
    score = 0.55 * w + 0.45 * f1
    tag_hit = bool(set(stem_token(t) for t in pattern.tags) & qset)
    if tag_hit:
        score = min(1.0, score + 0.12)
    return min(1.0, score), shared


def hybrid_score(
    query: str,
    query_features: Sequence[str],
    pattern: Pattern,
    *,
    idf: Optional[Dict[str, float]] = None,
    w_template: float = 0.20,
    w_prototype: float = 0.35,
    w_feature: float = 0.45,
    domain_hint: Optional[str] = None,
) -> MatchResult:
    qf = expand_query_features(query_features)
    t = template_score(query, pattern)
    p = prototype_score(qf, pattern, idf)
    f, shared = feature_score(qf, pattern, idf)
    score = (w_template * t) + (w_prototype * p) + (w_feature * f)
    score *= 0.72 + 0.28 * pattern.confidence
    # domain agreement boost
    if domain_hint and pattern.domain.value == domain_hint:
        score = min(1.0, score * 1.08)
    # path/module keywords in query
    if any(x in query.lower() for x in ("plugin", "tool", "cron", "profile", "skill")):
        title_l = pattern.title.lower()
        if any(k in title_l for k in ("plugin", "tool", "cron", "profile", "skill", "gateway", "registry")):
            score = min(1.0, score + 0.05)

    method = "hybrid"
    dominant = max(("template", t), ("prototype", p), ("feature", f), key=lambda x: x[1])
    if dominant[1] >= 0.7 and dominant[1] >= score - 0.08:
        method = dominant[0]
    rationale = (
        f"{method}: t={t:.2f} p={p:.2f} f={f:.2f} shared={len(shared)} "
        f"str={pattern.strength:.2f}"
    )
    return MatchResult(
        pattern=pattern,
        score=float(min(1.0, score)),
        method=method,
        shared_features=shared[:24],
        rationale=rationale,
    )


def match_patterns(
    query: str,
    query_features: Sequence[str],
    candidates: Iterable[Pattern],
    *,
    limit: int = 10,
    min_score: float = 0.04,
    domain_hint: Optional[str] = None,
    idf: Optional[Dict[str, float]] = None,
) -> List[MatchResult]:
    cand_list = list(candidates)
    if idf is None and cand_list:
        idf = build_idf(cand_list)
    results: List[MatchResult] = []
    for pat in cand_list:
        mr = hybrid_score(query, query_features, pat, idf=idf, domain_hint=domain_hint)
        if mr.score >= min_score:
            results.append(mr)
    results.sort(key=lambda m: (m.score, m.pattern.strength, m.pattern.confidence), reverse=True)
    return results[:limit]


def best_match(
    query: str,
    query_features: Sequence[str],
    candidates: Sequence[Pattern],
) -> Optional[MatchResult]:
    hits = match_patterns(query, query_features, candidates, limit=1)
    return hits[0] if hits else None
