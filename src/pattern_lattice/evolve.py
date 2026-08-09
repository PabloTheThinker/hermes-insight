"""Self-evolution loop — reinforce, generate, prune.

Agents get smarter when patterns that work get stronger, weak noise
decays, and synthesis nodes are created from dense clusters.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence

from pattern_lattice.cross_domain import auto_link
from pattern_lattice.features import extract_features
from pattern_lattice.models import Domain, Pattern, PatternKind
from pattern_lattice.store import PatternStore


def reinforce(
    store: PatternStore,
    pattern_ids: Sequence[str],
    *,
    amount: float = 0.05,
    helpful: bool = True,
) -> List[Pattern]:
    updated: List[Pattern] = []
    delta = amount if helpful else -abs(amount)
    for pid in pattern_ids:
        p = store.get_pattern(pid)
        if not p:
            continue
        p.touch(delta_strength=delta)
        if not helpful:
            p.confidence = max(0.05, p.confidence - abs(amount) * 0.5)
        else:
            p.confidence = min(0.99, p.confidence + abs(amount) * 0.25)
        store.upsert_pattern(p)
        updated.append(p)
    return updated


def decay_unused(
    store: PatternStore,
    *,
    half_life_days: float = 30.0,
    now: Optional[float] = None,
    floor: float = 0.05,
) -> int:
    """Apply soft strength decay to patterns not recently used."""
    import time

    now = now if now is not None else time.time()
    seconds = half_life_days * 86400.0
    changed = 0
    for p in store.all_patterns(limit=10000):
        ref = p.last_used_at or p.updated_at or p.created_at
        age = max(0.0, now - ref)
        if age < seconds * 0.25:
            continue
        # exponential-ish soft decay
        factor = 0.5 ** (age / seconds)
        new_strength = max(floor, p.strength * (0.85 + 0.15 * factor))
        if abs(new_strength - p.strength) >= 0.01:
            p.strength = new_strength
            store.upsert_pattern(p)
            changed += 1
    return changed


def synthesize_from_cluster(
    store: PatternStore,
    seed: Pattern,
    neighbors: Sequence[Pattern],
    *,
    min_neighbors: int = 2,
) -> Optional[Pattern]:
    """Generate a synthesis pattern from a dense neighborhood — bigger idea formation."""
    if len(neighbors) < min_neighbors:
        return None

    feat_counts: Counter[str] = Counter()
    for p in [seed, *neighbors]:
        feat_counts.update(f.lower() for f in p.features)
        feat_counts.update(tokenize_title(p.title))

    common = [f for f, c in feat_counts.most_common(24) if c >= 2]
    if len(common) < 3:
        return None

    titles = [seed.title] + [n.title for n in neighbors[:5]]
    body = (
        "Synthesis generated from cluster:\n"
        + "\n".join(f"- {t}" for t in titles)
        + "\n\nShared structure: "
        + ", ".join(common[:16])
        + "\n\nHypothesis: these instances are facets of one higher-order pattern."
    )
    domain = seed.domain
    # if neighbors span domains, mark general + analogy-rich
    domains = {seed.domain.value, *(n.domain.value for n in neighbors)}
    if len(domains) > 2:
        domain = Domain.GENERAL

    synth = Pattern.create(
        title=f"synthesis: {common[0]} / {common[1]}",
        body=body,
        kind=PatternKind.SYNTHESIS,
        domain=domain,
        features=common,
        tags=["synthesis", "generated", *common[:4]],
        confidence=min(0.8, 0.35 + 0.08 * len(neighbors)),
        metadata={
            "seed_id": seed.id,
            "member_ids": [seed.id, *[n.id for n in neighbors]],
            "cluster_size": len(neighbors) + 1,
        },
    )
    # avoid exact duplicate bodies
    for existing in store.list_patterns(kind=PatternKind.SYNTHESIS.value, limit=200):
        if existing.content_hash == synth.content_hash:
            return existing
        if jacc(existing.features, synth.features) >= 0.85:
            return existing

    store.upsert_pattern(synth)
    auto_link(store, synth, candidates=[seed, *neighbors], min_score=0.12, limit=12)
    return synth


def evolve_once(
    store: PatternStore,
    *,
    focus: Optional[Pattern] = None,
    decay: bool = True,
) -> Dict[str, object]:
    """One evolution tick: optional decay + cluster synthesis around strong nodes."""
    report: Dict[str, object] = {"decayed": 0, "syntheses": []}
    if decay:
        report["decayed"] = decay_unused(store)

    roots: List[Pattern]
    if focus:
        roots = [focus]
    else:
        roots = store.list_patterns(limit=15)

    synths: List[str] = []
    for root in roots:
        if root.strength < 0.35 and root.kind != PatternKind.SYNTHESIS:
            continue
        neigh = store.neighbors(root.id, limit=10)
        # also pull feature-similar even without links
        if len(neigh) < 2:
            pool = store.all_patterns(limit=500)
            from pattern_lattice.match import match_patterns

            hits = match_patterns(
                root.title + " " + root.body,
                root.features,
                [p for p in pool if p.id != root.id],
                limit=6,
                min_score=0.15,
            )
            neigh = [h.pattern for h in hits]
        s = synthesize_from_cluster(store, root, neigh)
        if s:
            synths.append(s.id)
    report["syntheses"] = synths
    report["counts"] = store.count()
    return report


def tokenize_title(title: str) -> List[str]:
    return extract_features(title, max_features=8)


def jacc(a: Sequence[str], b: Sequence[str]) -> float:
    from pattern_lattice.features import jaccard

    return jaccard(a, b)
