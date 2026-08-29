"""Improved hybrid matching with IDF, path boosts, and ops synonym expansion."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from hermes_insight.features import jaccard, normalize_text, overlap_list, stem_token, tokenize
from hermes_insight.models import MatchResult, Pattern, PatternKind

# Domain synonym expansion — structural rhymes agents should catch
# (includes classic ops + AI agent/model field)
_SYNONYMS: Dict[str, Set[str]] = {
    "credential": {"token", "secret", "key", "auth", "password", "bot", "api-key"},
    "token": {"credential", "secret", "bot", "auth", "api-key"},
    "isolation": {"separate", "compartment", "sandbox", "profile", "tenant"},
    "profile": {"tenant", "home", "isolation", "identity", "agent", "persona"},
    "linger": {"systemd", "lingering", "session", "logout", "ssh"},
    "longpoll": {"polling", "getupdates", "webhook", "consumer"},
    "consumer": {"worker", "listener", "subscriber", "poll"},
    "conflict": {"collision", "duplicate", "race", "contention"},
    "retry": {"backoff", "jitter", "transient", "timeout"},
    "timeout": {"deadline", "latency", "slow", "hang"},
    "circuit": {"breaker", "bulkhead", "failfast"},
    "cache": {"ttl", "stampede", "singleflight", "memo", "prompt-cache"},
    # AI agent / model field
    "agent": {"assistant", "worker", "subagent", "bot", "actor", "employee", "seat"},
    "model": {"llm", "foundation-model", "checkpoint", "completion", "chat-model", "weights"},
    "tool": {"function", "action", "capability", "api-tool", "tool-call"},
    "skill": {"playbook", "procedure", "workflow", "runbook", "sop"},
    "plugin": {"extension", "addon", "module"},
    "context": {"window", "history", "working-memory", "prompt-cache"},
    "memory": {"recall", "engram", "fact-store", "durable-state"},
    "delegation": {"hand-off", "spawn", "delegate", "fan-out", "subagent"},
    "inference": {"generation", "decode", "sampling", "forward-pass"},
    "embedding": {"vector", "retrieval", "similarity"},
    "session": {"conversation", "thread", "dialogue"},
    "harness": {"runtime", "loop", "orchestrator", "framework"},
    "multi_agent": {"fleet", "swarm", "crew", "team", "board", "kanban"},
    "prompt": {"system-prompt", "instruction", "soul", "policy-text"},
    "eval": {"benchmark", "score", "grade", "rubric"},
    "toolset": {"toolkit", "tool-bundle"},
    "compartment": {"isolation", "profile", "tenant", "sandbox"},
}

# Merge ontology synonyms if available
try:
    from hermes_insight.ontology import AGENT_SYNONYMS

    for _k, _vs in AGENT_SYNONYMS.items():
        _SYNONYMS.setdefault(_k, set()).update(_vs)
except Exception:  # pragma: no cover
    pass


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

    # --- structural pattern recognition priors ---
    # Prefer rules/prototypes/skills over raw source-file dumps for agent/ops queries.
    kind = pattern.kind
    if kind == PatternKind.RULE:
        score = min(1.0, score + 0.14)
    elif kind == PatternKind.PROTOTYPE:
        score = min(1.0, score + 0.10)
    elif kind == PatternKind.SYNTHESIS:
        score = min(1.0, score + 0.08)
    elif kind == PatternKind.SEQUENCE:
        score = min(1.0, score + 0.08)
    elif kind == PatternKind.SKILL:
        score = min(1.0, score + 0.07)
    elif kind == PatternKind.FACT:
        score = min(1.0, score + 0.09)
    elif kind in (PatternKind.EVENT, PatternKind.EPISODE, PatternKind.TASK):
        # lived experience — recency-weighted
        import time as _time

        age_h = max(0.0, (_time.time() - float(pattern.updated_at or pattern.created_at or 0)) / 3600.0)
        recency = 0.12 * math.exp(-age_h / 72.0)  # half-life ~ days
        score = min(1.0, score + 0.05 + recency)
    elif kind in (PatternKind.FEATURE,):
        score = min(1.0, score + 0.02)

    tags = set(stem_token(x) for x in (pattern.tags or []))
    if "starter" in tags or "bootstrap" in tags:
        score = min(1.0, score + 0.06)
    if "experience" in tags:
        score = min(1.0, score + 0.04)
    if "fabric" in tags and kind not in (PatternKind.RULE, PatternKind.PROTOTYPE, PatternKind.SKILL):
        # fabric file nodes are structural inventory, not usually the lever
        score *= 0.92

    title_l = pattern.title.lower()
    # demote bare source filenames unless query is clearly about that file
    if re.search(r"\.(py|ts|tsx|js|go|rs|md)$", title_l) or title_l.startswith("skill:"):
        q_l = query.lower()
        base = title_l.split("/")[-1]
        if base not in q_l and title_l not in q_l:
            if kind not in (PatternKind.SKILL, PatternKind.RULE, PatternKind.PROTOTYPE):
                score *= 0.82

    # path/module keywords in query
    if any(x in query.lower() for x in ("plugin", "tool", "cron", "profile", "skill", "gateway", "credential", "agent")):
        if any(k in title_l for k in ("plugin", "tool", "cron", "profile", "skill", "gateway", "registry", "credential", "agent", "consumer")):
            score = min(1.0, score + 0.06)

    # use_count soft prior — patterns that paid rent before
    if pattern.use_count:
        score = min(1.0, score + min(0.06, 0.01 * math.log1p(pattern.use_count)))

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

    # Dedupe near-identical nodes (many route.ts / same title fabric dumps)
    deduped: List[MatchResult] = []
    seen_hash: Set[str] = set()
    seen_title: Set[str] = set()
    kind_counts: Dict[str, int] = {}
    for mr in results:
        h = mr.pattern.content_hash or ""
        title_key = re.sub(r"\s+", " ", mr.pattern.title.lower().strip())
        # collapse skill:foo duplicates and bare filenames
        base_title = title_key.split("/")[-1]
        if h and h in seen_hash:
            continue
        if base_title in seen_title and mr.pattern.kind not in {
            PatternKind.RULE,
            PatternKind.EVENT,
            PatternKind.EPISODE,
            PatternKind.TASK,
            PatternKind.FACT,
        }:
            # allow second rule-like; skip extra file dumps with same name
            if kind_counts.get(base_title, 0) >= 1:
                continue
        k = mr.pattern.kind.value
        # diversity: cap pure prototypes after we already have strong rules
        if k == "prototype" and kind_counts.get("rule", 0) >= 2 and kind_counts.get("prototype", 0) >= 2:
            if mr.score < 0.45:
                continue
        if h:
            seen_hash.add(h)
        seen_title.add(base_title)
        kind_counts[base_title] = kind_counts.get(base_title, 0) + 1
        kind_counts[k] = kind_counts.get(k, 0) + 1
        deduped.append(mr)
        if len(deduped) >= limit:
            break
    return deduped


def best_match(
    query: str,
    query_features: Sequence[str],
    candidates: Sequence[Pattern],
) -> Optional[MatchResult]:
    hits = match_patterns(query, query_features, candidates, limit=1)
    return hits[0] if hits else None
