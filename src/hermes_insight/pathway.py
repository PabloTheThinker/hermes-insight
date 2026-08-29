"""Hebbian pathway growth from recognition-cued insights.

Repeated perceive/recall bindings potentiate existing links (fire together,
wire together), grow lateral sibling pathways between lived episodes, and
consolidate a local SEQUENCE when support is high enough.

Never writes Hermes skills (``PatternKind.SKILL``) or ``applied`` credit.
Pathways stay local ``sequence`` candidates with ``automatic_skill_write=false``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, TYPE_CHECKING

from hermes_insight.features import extract_features
from hermes_insight.models import Domain, Link, LinkKind, Pattern, PatternKind

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight


MIN_SUPPORT = 3
POTENTIATE_DELTA = 0.08
TOUCH_ECHO = 0.03
TOUCH_STRUCT = 0.015
TOUCH_PATHWAY = 0.04
SIBLING_WEIGHT = 0.45
SIBLING_CAP = 4
PATHWAY_ENABLES_WEIGHT = 0.70
PATHWAY_PART_OF_WEIGHT = 0.50

_GROWABLE_KINDS = {
    PatternKind.RULE,
    PatternKind.PROTOTYPE,
    PatternKind.TEMPLATE,
    PatternKind.SEQUENCE,
}

_BIND_KINDS = {
    LinkKind.EXPERIENCED_AS,
    LinkKind.INSTANCE_OF,
    LinkKind.TRIGGERED_BY,
    LinkKind.RESOLVED_BY,
    LinkKind.OBSERVED_IN,
    LinkKind.PART_OF,
}

_LATERAL_KINDS = {LinkKind.SHARES_CONTEXT, LinkKind.SIMILAR}

_EXPERIENCE_KINDS = {PatternKind.EVENT, PatternKind.EPISODE, PatternKind.TASK}


def _empty_growth() -> Dict[str, Any]:
    return {"strengthened": 0, "sibling_links": 0, "pathways": []}


def _is_pathway(pattern: Optional[Pattern]) -> bool:
    if pattern is None:
        return False
    tags = set(pattern.tags or [])
    return bool((pattern.metadata or {}).get("pathway")) or "pathway" in tags


def _parse_kind(raw: str) -> LinkKind:
    try:
        return LinkKind(raw)
    except ValueError:
        return LinkKind.EXPERIENCED_AS


def _find_bind(
    lat: "HermesInsight",
    echo_id: str,
    pattern_id: str,
    kind: LinkKind,
) -> Optional[Link]:
    pair = {echo_id, pattern_id}
    for link in lat.store.links_for(echo_id, limit=60):
        if link.kind != kind:
            continue
        if {link.source_id, link.target_id} == pair:
            return link
    return None


def _potentiate_bind(
    lat: "HermesInsight",
    echo_id: str,
    pattern_id: str,
    kind_raw: str,
) -> float:
    kind = _parse_kind(kind_raw)
    existing = _find_bind(lat, echo_id, pattern_id, kind)
    if existing:
        weight = min(1.0, float(existing.weight) + POTENTIATE_DELTA)
        lat.store.upsert_link(
            Link.create(
                existing.source_id,
                existing.target_id,
                existing.kind,
                weight=weight,
                note="hebbian potentiation",
                metadata=dict(existing.metadata or {}),
            )
        )
        return weight
    weight = 0.55
    lat.store.upsert_link(
        Link.create(
            echo_id,
            pattern_id,
            kind,
            weight=weight,
            note="hebbian potentiation",
        )
    )
    return weight


def _already_lateral(lat: "HermesInsight", left_id: str, right_id: str) -> bool:
    pair = {left_id, right_id}
    for link in lat.store.links_for(left_id, limit=40):
        if link.kind not in _LATERAL_KINDS:
            continue
        if {link.source_id, link.target_id} == pair:
            return True
    return False


def _link_siblings(lat: "HermesInsight", echo_ids: Sequence[str]) -> int:
    unique: List[str] = []
    for eid in echo_ids:
        if eid and eid not in unique:
            unique.append(eid)
    written = 0
    for i, left in enumerate(unique[:6]):
        for right in unique[i + 1 :]:
            if written >= SIBLING_CAP:
                return written
            if _already_lateral(lat, left, right):
                continue
            lat.store.upsert_link(
                Link.create(
                    left,
                    right,
                    LinkKind.SHARES_CONTEXT,
                    weight=SIBLING_WEIGHT,
                    note="pathway sibling",
                )
            )
            written += 1
    return written


def _bound_echoes(lat: "HermesInsight", pattern_id: str) -> List[Pattern]:
    echoes: List[Pattern] = []
    seen: Set[str] = set()
    for link in lat.store.links_for(pattern_id, limit=80):
        if link.kind not in _BIND_KINDS:
            continue
        other_id = link.target_id if link.source_id == pattern_id else link.source_id
        if other_id == pattern_id or other_id in seen:
            continue
        node = lat.store.get_pattern(other_id)
        if node is None or node.kind not in _EXPERIENCE_KINDS:
            continue
        if _is_pathway(node):
            continue
        seen.add(other_id)
        echoes.append(node)
    return echoes


def _support(echoes: Sequence[Pattern]) -> tuple[int, List[str], List[str]]:
    echo_ids: List[str] = []
    task_ids: List[str] = []
    for echo in echoes:
        if echo.id not in echo_ids:
            echo_ids.append(echo.id)
        task_id = str((echo.metadata or {}).get("task_id") or "")
        if task_id and task_id not in task_ids:
            task_ids.append(task_id)
    support = len(task_ids) if task_ids else len(echo_ids)
    return support, echo_ids, task_ids


def _existing_pathway(lat: "HermesInsight", source_id: str) -> Optional[Pattern]:
    source = lat.store.get_pattern(source_id)
    if source is not None:
        stored = str((source.metadata or {}).get("grown_pathway_id") or "")
        if stored:
            found = lat.store.get_pattern(stored)
            if found is not None:
                return found
    signature = f"pathway:{source_id}"
    for pattern in lat.store.list_patterns(kind=PatternKind.SEQUENCE.value, limit=1000):
        if str((pattern.metadata or {}).get("pathway_signature") or "") == signature:
            return pattern
    return None


def _pathway_row(pathway: Pattern, *, support: int, grown: bool) -> Dict[str, Any]:
    return {
        "id": pathway.id,
        "title": pathway.title,
        "support": support,
        "lifecycle": str((pathway.metadata or {}).get("lifecycle") or "candidate"),
        "grown": grown,
    }


def _upsert_pathway(
    lat: "HermesInsight",
    source: Pattern,
    echo_ids: Sequence[str],
    task_ids: Sequence[str],
    support: int,
) -> Dict[str, Any]:
    existing = _existing_pathway(lat, source.id)
    if existing is not None:
        existing.touch(TOUCH_PATHWAY)
        meta = dict(existing.metadata or {})
        meta["support"] = max(int(meta.get("support") or 0), support)
        prior_tasks = [str(x) for x in (meta.get("task_ids") or []) if str(x)]
        prior_echoes = [str(x) for x in (meta.get("echo_ids") or []) if str(x)]
        meta["task_ids"] = list(dict.fromkeys([*prior_tasks, *task_ids]))[:12]
        meta["echo_ids"] = list(dict.fromkeys([*prior_echoes, *echo_ids]))[:16]
        if str(meta.get("lifecycle") or "") == "observed" and support >= MIN_SUPPORT:
            meta["lifecycle"] = "candidate"
        meta["automatic_skill_write"] = False
        meta["pathway"] = True
        existing.metadata = meta
        if "pathway" not in (existing.tags or []):
            existing.tags = list(dict.fromkeys([*(existing.tags or []), "pathway", "grown"]))
        lat.store.upsert_pattern(existing)
        pathway = existing
        grown = False
    else:
        features = extract_features(
            f"{source.title} pathway {source.body}",
            max_features=24,
        )
        pathway = Pattern.create(
            title=f"pathway: {source.title}"[:120],
            body=(
                f"Grown local pathway from repeated {source.kind.value} recognition. "
                "Not a published skill. Review before operational use."
            ),
            kind=PatternKind.SEQUENCE,
            domain=Domain.PROCESS,
            features=features,
            tags=["pathway", "grown", "candidate"],
            confidence=min(0.72, 0.40 + 0.06 * support),
            metadata={
                "pathway": True,
                "pathway_signature": f"pathway:{source.id}",
                "source_pattern_id": source.id,
                "support": support,
                "task_ids": list(task_ids)[:12],
                "echo_ids": list(echo_ids)[:16],
                "lifecycle": "candidate",
                "automatic_skill_write": False,
            },
        )
        pathway.strength = 0.55
        lat.store.upsert_pattern(pathway)
        grown = True
        src_meta = dict(source.metadata or {})
        src_meta["grown_pathway_id"] = pathway.id
        source.metadata = src_meta
        lat.store.upsert_pattern(source)

    lat.store.upsert_link(
        Link.create(
            pathway.id,
            source.id,
            LinkKind.ENABLES,
            weight=PATHWAY_ENABLES_WEIGHT,
            note="grown pathway enables recognized structure",
        )
    )
    for echo_id in list(echo_ids)[:8]:
        if not lat.store.get_pattern(echo_id):
            continue
        lat.store.upsert_link(
            Link.create(
                echo_id,
                pathway.id,
                LinkKind.PART_OF,
                weight=PATHWAY_PART_OF_WEIGHT,
                note="echo participates in grown pathway",
            )
        )
    return _pathway_row(pathway, support=support, grown=grown)


def grow_pathways(
    lat: "HermesInsight",
    dots: Sequence[Dict[str, Any]],
    matches: Sequence[Dict[str, Any]],
    *,
    min_support: int = MIN_SUPPORT,
) -> Dict[str, Any]:
    """Potentiate binds, link sibling echoes, and consolidate local pathways."""
    if not dots and not matches:
        return _empty_growth()

    strengthened = 0
    sibling_links = 0
    seen_binds: Set[tuple[str, str, str]] = set()
    by_pattern: Dict[str, List[str]] = {}

    for dot in dots:
        echo_id = str(dot.get("echo_id") or "")
        pattern_id = str(dot.get("pattern_id") or "")
        kind_raw = str(dot.get("link_kind") or LinkKind.EXPERIENCED_AS.value)
        if not echo_id or not pattern_id:
            continue
        key = (echo_id, pattern_id, kind_raw)
        if key in seen_binds:
            continue
        seen_binds.add(key)
        _potentiate_bind(lat, echo_id, pattern_id, kind_raw)
        strengthened += 1
        echo = lat.store.get_pattern(echo_id)
        if echo is not None:
            echo.touch(TOUCH_ECHO)
            lat.store.upsert_pattern(echo)
        source = lat.store.get_pattern(pattern_id)
        if source is not None and not _is_pathway(source):
            source.touch(TOUCH_STRUCT)
            lat.store.upsert_pattern(source)
        by_pattern.setdefault(pattern_id, []).append(echo_id)

    for echo_ids in by_pattern.values():
        sibling_links += _link_siblings(lat, echo_ids)

    grown: List[Dict[str, Any]] = []
    seen_sources: Set[str] = set()
    source_ids = [str(row.get("id") or "") for row in matches[:8] if row.get("id")]
    for pattern_id in list(by_pattern.keys()) + source_ids:
        if not pattern_id or pattern_id in seen_sources:
            continue
        seen_sources.add(pattern_id)
        source = lat.store.get_pattern(pattern_id)
        if source is None or source.kind not in _GROWABLE_KINDS:
            continue
        if _is_pathway(source):
            continue
        echoes = _bound_echoes(lat, pattern_id)
        support, echo_ids, task_ids = _support(echoes)
        if support < min_support:
            continue
        grown.append(_upsert_pathway(lat, source, echo_ids, task_ids, support))

    return {
        "strengthened": strengthened,
        "sibling_links": sibling_links,
        "pathways": grown,
    }
