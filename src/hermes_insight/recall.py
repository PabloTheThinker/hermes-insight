"""Science-grounded recall layer for Hermes Insight.

Retrieve is associative, not nearest-neighbor dump:

* complementary episodic / semantic lanes
* encoding-specificity cues (query + observations + environment + task)
* bounded spreading activation with fan effect and lateral inhibition
* feeling-of-knowing refusal on thin queries
* compact remember/engram writes (hippocampal index, not transcript store)

Not a MemoryProvider. Recall never creates ``applied`` credit.
"""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, TYPE_CHECKING

from hermes_insight.distill import distill
from hermes_insight.features import extract_features
from hermes_insight.match import build_idf, expand_query_features, match_patterns
from hermes_insight.mindset import (
    CognitivePlate,
    MindsetArg,
    RecallKnobs,
    apply_to_recall,
    is_thin_query,
    resolve_plate,
)
from hermes_insight.models import Domain, Link, LinkKind, MatchResult, Pattern, PatternKind
from hermes_insight.scrub import scrub_text

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight


_SPREAD_STEPS = 3
_SPREAD_FACTOR = 0.80
_INHIBIT_TOP_M = 7
_INHIBIT_BETA = 0.12
_USABLE_ACTIVATION = 0.12
_ENV_BOOST = 1.35
_RECENCY_HALF_LIFE_DAYS = 30.0
_PRACTICE_DELTA = 0.01

_LINK_WEIGHTS: Dict[LinkKind, float] = {
    LinkKind.CAUSES: 0.95,
    LinkKind.APPLIED: 0.90,
    LinkKind.INSTANCE_OF: 0.85,
    LinkKind.OBSERVED_IN: 0.80,
    LinkKind.RESOLVED_BY: 0.78,
    LinkKind.TRIGGERED_BY: 0.75,
    LinkKind.NEXT: 0.75,
    LinkKind.EXPERIENCED_AS: 0.70,
    LinkKind.PRECEDES: 0.65,
    LinkKind.ENABLES: 0.60,
    LinkKind.REFINES: 0.55,
    LinkKind.PART_OF: 0.50,
    LinkKind.CONTRADICTS: 0.40,
    LinkKind.SIMILAR: 0.35,
    LinkKind.ANALOGY: 0.30,
    LinkKind.SHARES_CONTEXT: 0.30,
    LinkKind.RHYMES: 0.20,
    LinkKind.DELEGATES_TO: 0.35,
    LinkKind.USES_MODEL: 0.30,
    LinkKind.HAS_SKILL: 0.30,
    LinkKind.CALLS: 0.30,
}

_FAMILIAR_KINDS = {
    PatternKind.RULE,
    PatternKind.SKILL,
    PatternKind.SEQUENCE,
    PatternKind.SYNTHESIS,
    PatternKind.PROTOTYPE,
    PatternKind.TEMPLATE,
}
_RECOLLECT_KINDS = {PatternKind.EVENT, PatternKind.EPISODE, PatternKind.TASK}


def _is_thin(query: str, features: Sequence[str], knobs: Optional[RecallKnobs] = None) -> bool:
    return is_thin_query(query, knobs or RecallKnobs(), features)


def _is_experience(pattern: Pattern) -> bool:
    tags = set(pattern.tags or [])
    return pattern.kind in _RECOLLECT_KINDS or "experience" in tags


def _is_fact(pattern: Pattern) -> bool:
    tags = set(pattern.tags or [])
    return pattern.kind == PatternKind.FACT or (
        pattern.domain == Domain.MEMORY and ("engram" in tags or "fact" in tags)
    )


def _session_noise(pattern: Pattern, *, want_session: bool) -> bool:
    tags = set(pattern.tags or [])
    if want_session or "material" in tags:
        return False
    return (
        _is_experience(pattern)
        and "session" in tags
        and "auto" in tags
        and str(pattern.title).startswith("session turn")
    )


def _recency_factor(pattern: Pattern, *, now: float, knobs: Optional[RecallKnobs] = None) -> float:
    half = (knobs.recency_half_life_days if knobs else _RECENCY_HALF_LIFE_DAYS)
    ref = float(pattern.last_used_at or pattern.updated_at or pattern.created_at or now)
    age_days = max(0.0, (now - ref) / 86400.0)
    if pattern.kind in _FAMILIAR_KINDS and "starter" in set(pattern.tags or []):
        return 0.85 + 0.15 * math.exp(-age_days / (half * 2))
    return 0.55 + 0.45 * math.exp(-age_days / half)


def _observed_in(lat: "HermesInsight", pattern_id: str, environment_id: str) -> bool:
    if not environment_id:
        return False
    for link in lat.store.links_for(pattern_id, limit=40):
        if link.kind != LinkKind.OBSERVED_IN:
            continue
        if environment_id in {link.source_id, link.target_id}:
            return True
    return False


def _compose_cue(
    lat: "HermesInsight",
    query: str,
    *,
    observations: Optional[Sequence[str]] = None,
    environment_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> str:
    parts = [query]
    for item in observations or []:
        cleaned = scrub_text(str(item)).strip()
        if cleaned:
            parts.append(cleaned)
    env_id = (environment_id or "").strip()
    if env_id:
        env = lat.store.get_pattern(env_id)
        if env:
            parts.append(env.title)
            parts.append(env.body[:400])
    if task_id:
        parts.append(f"task:{task_id}")
    return "\n".join(p for p in parts if p)


def _row(pattern: Pattern, score: float, method: str, shared: Sequence[str]) -> Dict[str, Any]:
    return {
        "id": pattern.id,
        "title": pattern.title,
        "score": round(float(score), 4),
        "method": method,
        "kind": pattern.kind.value,
        "domain": pattern.domain.value,
        "shared": list(shared)[:10],
        "body_preview": pattern.body[:220],
    }


def _spread_activation(
    lat: "HermesInsight",
    seeds: Dict[str, float],
    *,
    environment_id: str = "",
    now: float,
    knobs: Optional[RecallKnobs] = None,
) -> Dict[str, float]:
    knobs = knobs or RecallKnobs()
    activation = {pid: float(score) for pid, score in seeds.items() if score > 0}
    for _ in range(knobs.spread_steps):
        incoming: Dict[str, float] = defaultdict(float)
        for pid, act in list(activation.items()):
            if act < 0.01:
                continue
            links = lat.store.links_for(pid, limit=40)
            fan = max(1, len(links))
            for link in links:
                other = link.target_id if link.source_id == pid else link.source_id
                kind_w = _LINK_WEIGHTS.get(link.kind, 0.25)
                if link.kind in {LinkKind.ANALOGY, LinkKind.RHYMES}:
                    kind_w *= knobs.analogy_boost
                incoming[other] += knobs.spread_factor * kind_w * float(link.weight) * act / fan
        for oid, add in incoming.items():
            activation[oid] = activation.get(oid, 0.0) + add

    boosted: Dict[str, float] = {}
    for pid, act in activation.items():
        pattern = lat.store.get_pattern(pid)
        if not pattern:
            continue
        value = act * _recency_factor(pattern, now=now, knobs=knobs)
        if _observed_in(lat, pid, environment_id):
            value *= knobs.env_boost
        boosted[pid] = value
    return boosted


def _lateral_inhibition(
    lat: "HermesInsight",
    activation: Dict[str, float],
    knobs: Optional[RecallKnobs] = None,
) -> Dict[str, float]:
    k = knobs or RecallKnobs()
    by_kind: Dict[str, List[tuple[str, float]]] = defaultdict(list)
    for pid, act in activation.items():
        pattern = lat.store.get_pattern(pid)
        if not pattern:
            continue
        by_kind[pattern.kind.value].append((pid, act))

    inhibited = dict(activation)
    for rows in by_kind.values():
        rows.sort(key=lambda item: item[1], reverse=True)
        leaders = rows[: k.inhibit_top_m]
        if not leaders:
            continue
        for pid, act in rows[k.inhibit_top_m :]:
            penalty = k.inhibit_beta * sum(max(0.0, lead - act) for _, lead in leaders)
            inhibited[pid] = max(0.0, act - penalty)
    return inhibited


def _lane_weight(pattern: Pattern, knobs: RecallKnobs) -> float:
    if _is_fact(pattern):
        return knobs.fact_weight
    if pattern.kind == PatternKind.SEQUENCE:
        return knobs.sequence_weight
    if _is_experience(pattern):
        return knobs.echo_weight
    if pattern.kind == PatternKind.RULE:
        return knobs.rule_weight
    return 1.0


def _mindset_block(plate: CognitivePlate) -> Dict[str, Any]:
    return plate.to_dict()


def _contradictions(
    lat: "HermesInsight",
    activated_ids: Iterable[str],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for pid in activated_ids:
        pattern = lat.store.get_pattern(pid)
        if not pattern:
            continue
        for link in lat.store.links_for(pid, limit=20):
            if link.kind != LinkKind.CONTRADICTS:
                continue
            other_id = link.target_id if link.source_id == pid else link.source_id
            if other_id in seen:
                continue
            other = lat.store.get_pattern(other_id)
            if not other:
                continue
            seen.add(other_id)
            out.append(
                {
                    "id": other.id,
                    "title": other.title,
                    "kind": other.kind.value,
                    "domain": other.domain.value,
                    "via": pattern.title,
                    "score": round(float(link.weight), 4),
                }
            )
            if len(out) >= limit:
                return out
    return out


_ECHO_LINK_KINDS = {
    LinkKind.EXPERIENCED_AS,
    LinkKind.INSTANCE_OF,
    LinkKind.TRIGGERED_BY,
    LinkKind.RESOLVED_BY,
    LinkKind.APPLIED,
    LinkKind.OBSERVED_IN,
    LinkKind.PART_OF,
}


def _dot(
    pattern: Pattern,
    echo: Pattern,
    *,
    link_kind: str,
    score: float,
) -> Dict[str, Any]:
    task_id = str((echo.metadata or {}).get("task_id") or "")
    return {
        "pattern_id": pattern.id,
        "pattern_title": pattern.title,
        "pattern_kind": pattern.kind.value,
        "echo_id": echo.id,
        "echo_title": echo.title,
        "echo_kind": echo.kind.value,
        "link_kind": link_kind,
        "score": round(float(score), 4),
        "task_id": task_id,
    }


def harvest_linked_echoes(
    lat: "HermesInsight",
    matches: Sequence[Dict[str, Any]],
    *,
    limit: int,
    knobs: Optional[RecallKnobs] = None,
    exclude_ids: Optional[Set[str]] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Recall events/tasks already bound to recognized structural patterns."""
    k = knobs or RecallKnobs()
    skip = set(exclude_ids or ())
    echoes: List[Dict[str, Any]] = []
    dots: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for row in matches[:8]:
        pid = str(row.get("id") or "")
        pattern = lat.store.get_pattern(pid) if pid else None
        if not pattern:
            continue
        seed = float(row.get("score") or 0.0)
        for link in lat.store.links_for(pid, limit=40):
            if link.kind not in _ECHO_LINK_KINDS:
                continue
            other_id = link.target_id if link.source_id == pid else link.source_id
            if other_id in skip or other_id in seen or other_id == pid:
                continue
            other = lat.store.get_pattern(other_id)
            if not other or not _is_experience(other):
                continue
            if _session_noise(other, want_session=False):
                continue
            seen.add(other_id)
            score = max(0.04, seed * float(link.weight) * k.echo_weight)
            echo = _row(other, score, "linked", [])
            echo["via"] = pattern.title
            echo["link_kind"] = link.kind.value
            echoes.append(echo)
            dots.append(_dot(pattern, other, link_kind=link.kind.value, score=score))
            if len(echoes) >= limit:
                echoes.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
                dots.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
                return echoes[:limit], dots[:limit]
    echoes.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    dots.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    return echoes[:limit], dots[:limit]


def connect_recognition_dots(
    lat: "HermesInsight",
    matches: Sequence[Dict[str, Any]],
    experiences: Sequence[Dict[str, Any]],
    *,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Bind recalled events/tasks to recognized structure. Never writes applied credit."""
    dots: List[Dict[str, Any]] = []
    written = 0
    for echo_row in experiences[:6]:
        echo = lat.store.get_pattern(str(echo_row.get("id") or ""))
        if not echo or not _is_experience(echo):
            continue
        echo_score = float(echo_row.get("score") or 0.0)
        if echo_score < 0.06:
            continue
        for match_row in matches[:4]:
            pattern = lat.store.get_pattern(str(match_row.get("id") or ""))
            if not pattern or _is_experience(pattern) or _is_fact(pattern):
                continue
            match_score = float(match_row.get("score") or 0.0)
            if match_score < 0.10:
                continue
            if _already_bound(lat, echo.id, pattern.id):
                continue
            kind = (
                LinkKind.INSTANCE_OF
                if pattern.kind in {PatternKind.RULE, PatternKind.PROTOTYPE, PatternKind.TEMPLATE}
                else LinkKind.EXPERIENCED_AS
            )
            weight = min(1.0, max(0.2, 0.45 * match_score + 0.35 * echo_score))
            lat.store.upsert_link(
                Link.create(
                    echo.id,
                    pattern.id,
                    kind,
                    weight=weight,
                    note="recognition-cued recall bind",
                )
            )
            dots.append(_dot(pattern, echo, link_kind=kind.value, score=weight))
            written += 1
            if written >= limit:
                return dots
    return dots


def _already_bound(lat: "HermesInsight", left_id: str, right_id: str) -> bool:
    pair = {left_id, right_id}
    for link in lat.store.links_for(left_id, limit=40):
        if link.kind not in {LinkKind.EXPERIENCED_AS, LinkKind.INSTANCE_OF}:
            continue
        if {link.source_id, link.target_id} == pair:
            return True
    return False


def _empty_failure(error: str, plate: Optional[CognitivePlate] = None) -> Dict[str, Any]:
    pack: Dict[str, Any] = {
        "success": False,
        "error": error,
        "usable": False,
        "thin_query": False,
        "matches": [],
        "rules": [],
        "experiences": [],
        "echoes": [],
        "facts": [],
        "hops": [],
        "contradictions": [],
        "dots": [],
        "pathways": [],
        "pathway_growth": {"strengthened": 0, "sibling_links": 0},
        "working_set": {
            "rules": [],
            "facts": [],
            "echoes": [],
            "contradictions": [],
            "hops": [],
        },
        "process": "none",
        "brief": "",
        "lever": "",
        "confidence": 0.0,
    }
    if plate is not None:
        pack["mindset"] = _mindset_block(plate)
    return pack


def _thin_pack(
    query: str,
    write_meta: bool,
    lat: "HermesInsight",
    plate: CognitivePlate,
) -> Dict[str, Any]:
    brief = "\n".join(
        [
            "## Insight recall",
            "**Lever:** insufficient_signal",
            "**Confidence:** 0.12",
            "_Query was thin — gather concrete observations before treating this as memory._",
        ]
    )
    if write_meta:
        lat.store.set_meta("last_recall_line", "insufficient_signal: none")
        lat.store.set_meta("last_brief_line", "lever=`insufficient_signal` · match=`none`")
    return {
        "success": True,
        "usable": False,
        "thin_query": True,
        "lever": "insufficient_signal",
        "confidence": 0.12,
        "matches": [],
        "rules": [],
        "experiences": [],
        "echoes": [],
        "facts": [],
        "hops": [],
        "contradictions": [],
        "dots": [],
        "pathways": [],
        "pathway_growth": {"strengthened": 0, "sibling_links": 0},
        "working_set": {
            "rules": [],
            "facts": [],
            "echoes": [],
            "contradictions": [],
            "hops": [],
        },
        "process": "none",
        "brief": brief,
        "active_task_id": lat.store.get_meta("active_task_id", ""),
        "query": query,
        "mindset": _mindset_block(plate),
    }


def recall(
    lat: "HermesInsight",
    query: str,
    *,
    limit: int = 8,
    include_experiences: bool = True,
    write_meta: bool = True,
    domain: Optional[str] = None,
    observations: Optional[Sequence[str]] = None,
    environment_id: Optional[str] = None,
    task_id: Optional[str] = None,
    mindset: MindsetArg = None,
    connect_dots: bool = False,
) -> Dict[str, Any]:
    """Associative pre-action recall: dual-process working set + usable flag.

    ``mindset`` is a named plate, a custom axis dict, or omitted (the
    persisted ``active_mindset`` / balanced default).

    When ``connect_dots`` or ``write_meta`` is true, recognized structures
    bind to recalled events/tasks via ``experienced_as`` / ``instance_of``
    (never ``applied`` credit) and those binds grow Hebbian pathways.
    """
    from hermes_insight.experience import seed_agent_starters

    plate = resolve_plate(lat, mindset)
    knobs = apply_to_recall(plate)

    query = scrub_text(query or "").strip()
    if not query:
        return _empty_failure("query required", plate)

    seed_agent_starters(lat)
    env_id = scrub_text(environment_id or "").strip() or lat.store.get_meta(
        "last_environment_snapshot_id", ""
    )
    cue = _compose_cue(
        lat,
        query,
        observations=observations,
        environment_id=env_id or None,
        task_id=task_id,
    )
    feats = expand_query_features(extract_features(cue))
    if _is_thin(query, extract_features(query), knobs):
        return _thin_pack(query, write_meta, lat, plate)

    lane_limit = max(1, int(limit * knobs.lane_limit_scale))
    pool = lat.store.candidate_pool(
        cue,
        domain=domain,
        fts_limit=48,
        structural_limit=140,
        fill_limit=50,
    )
    idf = build_idf(pool)
    hits = match_patterns(
        cue,
        feats,
        pool,
        limit=max(16, lane_limit * 3),
        min_score=0.04,
        domain_hint=domain,
        idf=idf,
    )
    hit_by_id = {h.pattern.id: h for h in hits}
    seeds = {h.pattern.id: float(h.score) for h in hits}
    now = time.time()
    activation = _lateral_inhibition(
        lat,
        _spread_activation(lat, seeds, environment_id=env_id, now=now, knobs=knobs),
        knobs,
    )

    want_session = any(w in query.lower() for w in ("session", "turn completed", "telegram session"))
    matches: List[Dict[str, Any]] = []
    experiences: List[Dict[str, Any]] = []
    facts: List[Dict[str, Any]] = []
    hops: List[Dict[str, Any]] = []
    seeded_ids = set(seeds)

    ranked_ids = sorted(activation, key=lambda pid: activation[pid], reverse=True)
    for pid in ranked_ids:
        pattern = lat.store.get_pattern(pid)
        if not pattern or _session_noise(pattern, want_session=want_session):
            continue
        hit = hit_by_id.get(pid)
        act = activation[pid]
        match_score = float(hit.score) if hit else 0.0
        score = (0.65 * match_score + 0.35 * act) if hit else act
        if env_id and _observed_in(lat, pid, env_id):
            score *= 1.18
        score *= _lane_weight(pattern, knobs)
        method = hit.method if hit else "spread"
        shared = hit.shared_features[:10] if hit else []
        row = _row(pattern, score, method, shared)
        if _is_fact(pattern):
            facts.append(row)
        elif _is_experience(pattern):
            if include_experiences:
                experiences.append(row)
                if pid not in seeded_ids:
                    hops.append(
                        {
                            "id": pattern.id,
                            "title": pattern.title,
                            "kind": pattern.kind.value,
                            "domain": pattern.domain.value,
                            "via": "spread",
                            "score": round(float(score), 4),
                        }
                    )
        elif pid in seeded_ids and pattern.kind in _FAMILIAR_KINDS:
            matches.append(row)
        elif pid not in seeded_ids:
            hops.append(
                {
                    "id": pattern.id,
                    "title": pattern.title,
                    "kind": pattern.kind.value,
                    "domain": pattern.domain.value,
                    "via": "spread",
                    "score": round(float(score), 4),
                }
            )
        else:
            matches.append(row)

    matches.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    experiences.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    facts.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    hops.sort(key=lambda r: float(r.get("score") or 0), reverse=True)

    matches = matches[:lane_limit]
    experiences = experiences[:lane_limit]
    facts = facts[:lane_limit]
    hop_cap = max(1, int(round(lane_limit * knobs.hop_weight)))
    hops = hops[:hop_cap]
    contradictions = _contradictions(lat, ranked_ids[:24], limit=lane_limit)

    existing_echo_ids = {str(r.get("id") or "") for r in experiences}
    linked_echoes, dots = harvest_linked_echoes(
        lat,
        matches,
        limit=lane_limit,
        knobs=knobs,
        exclude_ids=None,
    )
    if include_experiences:
        for echo in linked_echoes:
            if echo["id"] not in existing_echo_ids:
                experiences.append(echo)
                existing_echo_ids.add(echo["id"])
        experiences.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
        experiences = experiences[:lane_limit]
    pathways: List[Dict[str, Any]] = []
    pathway_growth = {"strengthened": 0, "sibling_links": 0}
    if connect_dots or write_meta:
        for extra in connect_recognition_dots(lat, matches, experiences):
            if extra["echo_id"] not in {d.get("echo_id") for d in dots}:
                dots.append(extra)
        dots.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
        dots = dots[:lane_limit]
        from hermes_insight.pathway import grow_pathways

        growth = grow_pathways(lat, dots, matches)
        pathways = list(growth.get("pathways") or [])
        pathway_growth = {
            "strengthened": int(growth.get("strengthened") or 0),
            "sibling_links": int(growth.get("sibling_links") or 0),
        }

    working_ids = [r["id"] for r in matches + experiences + facts]
    if write_meta:
        for pid in working_ids[: max(3, min(6, lane_limit))]:
            pattern = lat.store.get_pattern(pid)
            if not pattern:
                continue
            pattern.touch(_PRACTICE_DELTA)
            lat.store.upsert_pattern(pattern)

    distill_hits: List[MatchResult] = []
    for row in matches[:5]:
        hit = hit_by_id.get(str(row["id"]))
        if hit:
            distill_hits.append(hit)
    if not distill_hits:
        distill_hits = hits[:5]
    distillation = distill(cue, matches=distill_hits, domain_hint=domain)
    lever = distillation.actual_variable
    confidence = float(distillation.confidence)

    peak = 0.0
    if activation:
        peak = max(activation.values())
    top_score = float(matches[0]["score"]) if matches else peak
    usable = (
        bool(matches or experiences or facts)
        and peak >= knobs.usable_activation
        and lever not in {"insufficient_signal", "unknown", ""}
        and top_score >= 0.08
    )
    if not usable and not (matches or experiences or facts):
        lever = "insufficient_signal"
        confidence = min(confidence, 0.20)

    has_fam = bool(matches)
    has_rec = bool(experiences or facts)
    if has_fam and has_rec:
        process = "both"
    elif has_fam:
        process = "familiarity"
    elif has_rec:
        process = "recollection"
    else:
        process = "none"

    traj_bits = []
    if matches:
        traj_bits.append(f"strongest prior: **{matches[0]['title']}** ({matches[0]['score']:.2f})")
    if experiences:
        traj_bits.append(f"lived echo: **{experiences[0]['title']}**")
    if facts:
        traj_bits.append(f"fact: **{facts[0]['title']}**")
    if hops:
        traj_bits.append("hop: " + ", ".join(h["title"] for h in hops[:3]))
    if dots:
        traj_bits.append(
            "dot: "
            + ", ".join(f"{d['echo_title']}←{d['pattern_title']}" for d in dots[:3])
        )
    if pathways:
        traj_bits.append(
            "pathway: "
            + ", ".join(f"{p['title']} ({p['support']})" for p in pathways[:2])
        )

    brief_lines = [
        "## Insight recall",
        f"**Lever:** {lever}",
        f"**Confidence:** {confidence:.2f}",
        f"**Usable:** {str(usable).lower()} · **process:** {process}",
    ]
    if traj_bits:
        brief_lines.append("- " + " · ".join(traj_bits))
    if matches:
        brief_lines.append("### Structural priors")
        for item in matches[: knobs.brief_match_n]:
            brief_lines.append(f"- `{item['score']:.2f}` **{item['title']}** — {item['body_preview'][:120]}")
    if facts:
        brief_lines.append("### Facts")
        for item in facts[: knobs.brief_fact_n]:
            brief_lines.append(f"- `{item['score']:.2f}` **{item['title']}**")
    if experiences:
        brief_lines.append("### Lived experiences")
        for item in experiences[: knobs.brief_echo_n]:
            brief_lines.append(f"- `{item['score']:.2f}` **{item['title']}**")
    if hops:
        brief_lines.append("### Connected hops")
        for item in hops[: knobs.brief_hop_n]:
            brief_lines.append(f"- {item['title']} ({item['kind']}/{item['domain']})")
    if contradictions:
        brief_lines.append("### Contradictions")
        for item in contradictions[: max(2, knobs.brief_fact_n)]:
            brief_lines.append(f"- {item['title']} ← {item.get('via', '')}")
    if dots:
        brief_lines.append("### Connected dots")
        for item in dots[: knobs.brief_echo_n]:
            brief_lines.append(
                f"- **{item['echo_title']}** ({item['echo_kind']}) ← "
                f"**{item['pattern_title']}** ({item['link_kind']})"
            )
    if pathways:
        brief_lines.append("### Grown pathways")
        for item in pathways[: knobs.brief_echo_n]:
            brief_lines.append(
                f"- **{item['title']}** (support {item['support']}, {item['lifecycle']})"
            )
    brief = "\n".join(brief_lines)

    if write_meta:
        top_t = matches[0]["title"] if matches else "none"
        lat.store.set_meta("last_recall_line", f"{lever}: {top_t}")
        lat.store.set_meta(
            "last_brief_line",
            f"lever=`{lever}` · match=`{top_t}`"
            + (f"@{matches[0]['score']:.2f}" if matches else ""),
        )

    working_set = {
        "rules": matches,
        "facts": facts,
        "echoes": experiences,
        "contradictions": contradictions,
        "hops": hops,
    }
    return {
        "success": True,
        "usable": usable,
        "thin_query": False,
        "lever": lever,
        "confidence": confidence,
        "matches": matches,
        "rules": matches,
        "experiences": experiences,
        "echoes": experiences,
        "facts": facts,
        "hops": hops,
        "contradictions": contradictions,
        "dots": dots,
        "pathways": pathways,
        "pathway_growth": pathway_growth,
        "working_set": working_set,
        "process": process,
        "brief": brief,
        "active_task_id": lat.store.get_meta("active_task_id", ""),
        "mindset": _mindset_block(plate),
    }


def remember(
    lat: "HermesInsight",
    claim: str,
    *,
    source: str = "",
    salience: float = 0.6,
    pointer: str = "",
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Store one compact durable fact. Pointers are refs, never file contents."""
    from hermes_insight.experience import seed_agent_starters

    claim = scrub_text(claim or "").strip()
    if not claim:
        return {"success": False, "error": "claim required"}

    seed_agent_starters(lat)
    source = scrub_text(source or "").strip()[:120]
    pointer = scrub_text(pointer or "").splitlines()[0].strip()[:200]
    try:
        sal = float(salience)
    except (TypeError, ValueError):
        sal = 0.6
    sal = min(0.95, max(0.15, sal))

    tags = ["engram", "memory", "fact"]
    if task_id:
        tid = "".join(ch for ch in str(task_id) if ch.isalnum() or ch in {"_", "-"})[:48]
        if tid:
            tags.append(f"task:{tid}")
    metadata: Dict[str, Any] = {"engram": True, "salience": sal}
    if pointer:
        metadata["pointer"] = pointer
    if source:
        metadata["source"] = source
    if lat.agent_id:
        metadata.setdefault("agent_id", lat.agent_id)

    pattern = lat.ingest(
        claim[:100],
        claim[:1200],
        kind=PatternKind.FACT,
        domain=Domain.MEMORY,
        tags=tags,
        confidence=sal,
        source=source or "remember",
        link=False,
        metadata=metadata,
    )

    connected: List[Dict[str, Any]] = []
    feats = expand_query_features(extract_features(claim))
    pool = [
        item
        for item in lat.store.candidate_pool(claim, fts_limit=32, structural_limit=80, fill_limit=30)
        if item.id != pattern.id and item.kind in {PatternKind.RULE, PatternKind.PROTOTYPE, PatternKind.SKILL}
    ]
    if pool:
        hits = match_patterns(claim, feats, pool, limit=5, min_score=0.08, idf=build_idf(pool))
        for hit in hits:
            link = Link(
                id=f"l_{uuid.uuid4().hex[:12]}",
                source_id=pattern.id,
                target_id=hit.pattern.id,
                kind=LinkKind.INSTANCE_OF,
                weight=min(1.0, max(0.2, hit.score)),
                note=f"remember instance_of score={hit.score:.3f}",
            )
            lat.store.upsert_link(link)
            connected.append(
                {
                    "pattern_id": hit.pattern.id,
                    "title": hit.pattern.title,
                    "score": round(hit.score, 4),
                    "link_kind": LinkKind.INSTANCE_OF.value,
                }
            )

    env_id = lat.store.get_meta("last_environment_snapshot_id", "")
    if env_id and lat.store.get_pattern(env_id):
        lat.store.upsert_link(
            Link.create(
                pattern.id,
                env_id,
                LinkKind.OBSERVED_IN,
                weight=0.7,
                note="remember bound to current environment snapshot",
            )
        )

    lat.store.set_meta("last_remember_id", pattern.id)
    lat.store.set_meta("last_remember_line", claim[:120])
    return {
        "success": True,
        "fact": pattern.to_dict(),
        "connected": connected,
        "pointer": pointer,
    }
