"""Cross-domain linking — lateral connecting-the-dots.

The distinctive ND move: map structure from domain A onto domain B
(analogy), not just nearest-neighbor within one silo.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from pattern_lattice.features import jaccard, overlap_list
from pattern_lattice.models import Domain, Link, LinkKind, Pattern
from pattern_lattice.store import PatternStore


def propose_links(
    pattern: Pattern,
    candidates: Sequence[Pattern],
    *,
    min_score: float = 0.12,
    limit: int = 12,
) -> List[Tuple[Link, float, str]]:
    """Return (link, score, rationale) proposals without writing."""
    out: List[Tuple[Link, float, str]] = []
    for other in candidates:
        if other.id == pattern.id:
            continue
        score, kind, rationale = _relation(pattern, other)
        if score < min_score:
            continue
        link = Link.create(
            pattern.id,
            other.id,
            kind,
            weight=score,
            note=rationale,
        )
        out.append((link, score, rationale))
    out.sort(key=lambda x: x[1], reverse=True)
    return out[:limit]


def auto_link(
    store: PatternStore,
    pattern: Pattern,
    *,
    candidates: Optional[Sequence[Pattern]] = None,
    min_score: float = 0.18,
    limit: int = 8,
    write: bool = True,
) -> List[Link]:
    pool = list(candidates) if candidates is not None else store.all_patterns(limit=2000)
    proposals = propose_links(pattern, pool, min_score=min_score, limit=limit)
    links: List[Link] = []
    for link, _, _ in proposals:
        if write:
            link = store.upsert_link(link)
        links.append(link)
    return links


def _relation(a: Pattern, b: Pattern) -> Tuple[float, LinkKind, str]:
    feat_j = jaccard(a.features, b.features)
    shared = overlap_list(a.features, b.features)
    tag_j = jaccard(a.tags, b.tags)
    same_domain = a.domain == b.domain
    cross = a.domain != b.domain and a.domain != Domain.GENERAL and b.domain != Domain.GENERAL

    # Default similarity
    score = 0.55 * feat_j + 0.25 * tag_j
    kind = LinkKind.SIMILAR
    rationale = f"feature_j={feat_j:.2f} shared={len(shared)}"

    # Part-of: one feature set nearly subset
    sa, sb = set(x.lower() for x in a.features), set(x.lower() for x in b.features)
    if sa and sb:
        if sa < sb and len(sa) >= 2:
            score = max(score, 0.5 + 0.4 * (len(sa) / max(len(sb), 1)))
            kind = LinkKind.PART_OF
            rationale = f"{a.id} features ⊆ {b.id}"
        elif sb < sa and len(sb) >= 2:
            score = max(score, 0.5 + 0.4 * (len(sb) / max(len(sa), 1)))
            kind = LinkKind.PART_OF
            rationale = f"{b.id} features ⊆ {a.id}"

    # Instance / prototype
    if a.kind.value == "prototype" and feat_j >= 0.25 and same_domain:
        score = max(score, feat_j + 0.1)
        kind = LinkKind.INSTANCE_OF
        rationale = "candidate instance of prototype"

    # Contradiction cues in titles/bodies
    contradict_pairs = (
        ("always", "never"),
        ("increase", "decrease"),
        ("enable", "disable"),
        ("allow", "deny"),
        ("success", "failure"),
    )
    blob_a = (a.title + " " + a.body).lower()
    blob_b = (b.title + " " + b.body).lower()
    for x, y in contradict_pairs:
        if (x in blob_a and y in blob_b) or (y in blob_a and x in blob_b):
            score = max(score, 0.45 + 0.2 * feat_j)
            kind = LinkKind.CONTRADICTS
            rationale = f"opposing cues {x}/{y}"
            break

    # Cross-domain analogy: shared structure, different domain — the ND hop
    if cross and feat_j >= 0.15:
        score = max(score, 0.35 + 0.5 * feat_j)
        kind = LinkKind.ANALOGY
        rationale = (
            f"cross-domain analogy {a.domain.value}↔{b.domain.value} "
            f"shared={shared[:6]}"
        )

    # Weak lateral rhyme
    if 0.08 <= feat_j < 0.15 and not same_domain:
        score = max(score, feat_j + 0.05)
        kind = LinkKind.RHYMES
        rationale = "weak lateral association"

    # Sequence / precedes if both sequence-like and overlapping
    if a.kind.value == "sequence" and b.kind.value == "sequence" and feat_j >= 0.2:
        kind = LinkKind.PRECEDES
        score = max(score, feat_j + 0.1)
        rationale = "related sequences"

    return float(min(1.0, score)), kind, rationale


def analogy_map(
    source: Pattern,
    target_domain: Domain | str,
    pool: Sequence[Pattern],
    *,
    limit: int = 5,
) -> List[Dict]:
    """Find structures in target_domain that rhyme with source."""
    td = target_domain.value if isinstance(target_domain, Domain) else str(target_domain)
    hits = []
    for other in pool:
        if other.id == source.id:
            continue
        if other.domain.value != td and td != Domain.GENERAL.value:
            continue
        score, kind, rationale = _relation(source, other)
        if kind in (LinkKind.ANALOGY, LinkKind.SIMILAR, LinkKind.RHYMES) and score >= 0.12:
            hits.append(
                {
                    "source_id": source.id,
                    "target_id": other.id,
                    "target_title": other.title,
                    "score": score,
                    "kind": kind.value,
                    "rationale": rationale,
                    "shared_features": overlap_list(source.features, other.features)[:12],
                }
            )
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]
