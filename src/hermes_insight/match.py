"""Multi-method pattern matching: template, prototype, feature, hybrid.

Mirrors classic cognitive theories of pattern recognition and blends them
the way real brains do — not a single distance metric.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from hermes_insight.features import jaccard, normalize_text, overlap_list, tokenize
from hermes_insight.models import MatchResult, Pattern, PatternKind


def template_score(query: str, pattern: Pattern) -> float:
    """Near-exact structural match on normalized title/body."""
    q = normalize_text(query)
    if not q:
        return 0.0
    title = normalize_text(pattern.title)
    body = normalize_text(pattern.body)
    if q == title or q == body:
        return 1.0
    if title and (title in q or q in title):
        return 0.85
    # token equality ratio
    qt, pt = set(tokenize(query)), set(tokenize(pattern.title + " " + pattern.body))
    if not qt or not pt:
        return 0.0
    return len(qt & pt) / max(len(qt), 1) * 0.7


def _pattern_feature_universe(pattern: Pattern) -> List[str]:
    """Features + tags + title tokens — tags are deliberate human signal."""
    uni: List[str] = list(pattern.features)
    uni.extend(pattern.tags)
    uni.extend(tokenize(pattern.title))
    # light body tokens for recall without drowning in prose
    uni.extend(tokenize(pattern.body)[:24])
    # unique preserve order
    seen = set()
    out: List[str] = []
    for f in uni:
        fl = f.lower()
        if fl in seen:
            continue
        seen.add(fl)
        out.append(fl)
    return out


def prototype_score(query_features: Sequence[str], pattern: Pattern) -> float:
    """Distance to category center via feature overlap + strength prior."""
    universe = _pattern_feature_universe(pattern)
    base = jaccard(query_features, universe)
    # prototypes with higher strength are slightly preferred (well-formed centers)
    prior = 0.1 * pattern.strength
    kind_boost = 0.05 if pattern.kind in (PatternKind.PROTOTYPE, PatternKind.RULE) else 0.0
    return min(1.0, base + prior + kind_boost)


def feature_score(query_features: Sequence[str], pattern: Pattern) -> float:
    """Pandemonium-style: how many critical features fire."""
    if not query_features:
        return 0.0
    universe = _pattern_feature_universe(pattern)
    shared = overlap_list(list(query_features), universe)
    if not shared:
        return jaccard(query_features, universe) * 0.5
    # precision-oriented: shared / query features
    qset = set(x.lower() for x in query_features)
    precision = len(shared) / max(len(qset), 1)
    recall = len(shared) / max(len(set(universe)) or 1, 1)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    # bonus for any tag hit
    tag_hit = bool(set(pattern.tags) & qset)
    if tag_hit:
        f1 = min(1.0, f1 + 0.15)
    return min(1.0, f1)


def hybrid_score(
    query: str,
    query_features: Sequence[str],
    pattern: Pattern,
    *,
    w_template: float = 0.25,
    w_prototype: float = 0.35,
    w_feature: float = 0.40,
) -> MatchResult:
    t = template_score(query, pattern)
    p = prototype_score(query_features, pattern)
    f = feature_score(query_features, pattern)
    score = (w_template * t) + (w_prototype * p) + (w_feature * f)
    # confidence of the stored pattern modulates final score lightly
    score *= 0.7 + 0.3 * pattern.confidence
    shared = overlap_list(list(query_features), _pattern_feature_universe(pattern))
    method = "hybrid"
    dominant = max(("template", t), ("prototype", p), ("feature", f), key=lambda x: x[1])
    if dominant[1] >= 0.75 and dominant[1] >= score - 0.05:
        method = dominant[0]
    rationale = (
        f"{method}: template={t:.2f} prototype={p:.2f} feature={f:.2f} "
        f"shared={len(shared)} strength={pattern.strength:.2f}"
    )
    return MatchResult(
        pattern=pattern,
        score=float(score),
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
    min_score: float = 0.05,
) -> List[MatchResult]:
    results: List[MatchResult] = []
    for pat in candidates:
        mr = hybrid_score(query, query_features, pat)
        if mr.score >= min_score:
            results.append(mr)
    results.sort(key=lambda m: (m.score, m.pattern.strength), reverse=True)
    return results[:limit]


def best_match(
    query: str,
    query_features: Sequence[str],
    candidates: Sequence[Pattern],
) -> Optional[MatchResult]:
    hits = match_patterns(query, query_features, candidates, limit=1)
    return hits[0] if hits else None
