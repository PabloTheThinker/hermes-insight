"""HermesInsight harness — the public agent API.

Cycle (aligned to superior pattern processing + ND connecting-the-dots):

1. Perception   — feature decompose observations
2. Recognition  — template / prototype / feature match
3. Seeking      — FTS + lateral candidate hunt
4. Maintenance  — upsert catalogue, anomaly file
5. Processing   — distill actual variable (deep focus)
6. Generation   — trajectory + synthesis + optional new nodes
7. Transfer     — brief for the agent/human
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from hermes_insight.anomaly import detect_anomalies, file_anomaly
from hermes_insight.brief import compact_one_liner, format_brief
from hermes_insight.cross_domain import analogy_map, auto_link
from hermes_insight.distill import distill
from hermes_insight.evolve import evolve_once, reinforce
from hermes_insight.extrapolate import extrapolate
from hermes_insight.features import extract_features
from hermes_insight.match import match_patterns
from hermes_insight.models import (
    CycleReport,
    Domain,
    Evidence,
    LinkKind,
    Pattern,
    PatternKind,
    ProcessDim,
)
from hermes_insight.store import PatternStore


PathLike = Union[str, Path]


def default_db_path() -> Path:
    env = os.environ.get("HERMES_INSIGHT_DB")
    if env:
        return Path(env).expanduser()
    home = Path(os.environ.get("HERMES_INSIGHT_HOME", "~/.hermes-insight")).expanduser()
    home.mkdir(parents=True, exist_ok=True)
    return home / "insight.db"


class HermesInsight:
    """High-level harness. Construct once per agent profile/workspace."""

    def __init__(self, db_path: Optional[PathLike] = None) -> None:
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.store = PatternStore(self.db_path)

    # ------------------------------------------------------------------
    # Ingest / catalogue
    # ------------------------------------------------------------------

    def ingest(
        self,
        title: str,
        body: str,
        *,
        kind: PatternKind | str = PatternKind.PROTOTYPE,
        domain: Domain | str = Domain.GENERAL,
        features: Optional[Sequence[str]] = None,
        tags: Optional[Sequence[str]] = None,
        confidence: float = 0.6,
        source: str = "agent",
        auto_link_min: float = 0.18,
        link: bool = True,
    ) -> Pattern:
        feats = list(features) if features else extract_features(f"{title}\n{body}")
        pat = Pattern.create(
            title=title,
            body=body,
            kind=kind,
            domain=domain,
            features=feats,
            tags=tags,
            confidence=confidence,
            evidence=[Evidence(source=source, kind="observation", confidence=confidence)],
        )
        # de-dupe by content hash among recent
        for existing in self.store.list_patterns(limit=500):
            if existing.content_hash == pat.content_hash:
                existing.touch(0.01)
                self.store.upsert_pattern(existing)
                if link:
                    auto_link(self.store, existing, min_score=auto_link_min, limit=8)
                return existing
        self.store.upsert_pattern(pat)
        if link:
            auto_link(self.store, pat, min_score=auto_link_min, limit=8)
        return pat

    def get(self, pattern_id: str) -> Optional[Pattern]:
        return self.store.get_pattern(pattern_id)

    def search(self, query: str, *, limit: int = 15) -> List[Pattern]:
        fts = self.store.fts_search(query, limit=limit)
        if len(fts) >= limit:
            return fts
        feats = extract_features(query)
        pool = self.store.all_patterns(limit=2000)
        ranked = match_patterns(query, feats, pool, limit=limit)
        seen = {p.id for p in fts}
        out = list(fts)
        for m in ranked:
            if m.pattern.id not in seen:
                out.append(m.pattern)
                seen.add(m.pattern.id)
            if len(out) >= limit:
                break
        return out

    def match(self, query: str, *, limit: int = 10, min_score: float = 0.08) -> List[Dict[str, Any]]:
        feats = extract_features(query)
        # Prefer FTS shortlist then full hybrid on union
        shortlist = self.store.fts_search(query, limit=40)
        pool_ids = {p.id for p in shortlist}
        pool = list(shortlist)
        if len(pool) < 25:
            for p in self.store.all_patterns(limit=1500):
                if p.id not in pool_ids:
                    pool.append(p)
        hits = match_patterns(query, feats, pool, limit=limit, min_score=min_score)
        for h in hits:
            h.pattern.touch(0.015)
            self.store.upsert_pattern(h.pattern)
        return [h.to_dict() for h in hits]

    # ------------------------------------------------------------------
    # Full cognitive cycle
    # ------------------------------------------------------------------

    def cycle(
        self,
        query: str,
        *,
        observations: Optional[Sequence[str]] = None,
        ingest_query: bool = False,
        domain: Domain | str = Domain.GENERAL,
        evolve: bool = True,
        file_novel: bool = True,
        brief_style: str = "agent",
    ) -> CycleReport:
        obs = [query.strip()] if query.strip() else []
        if observations:
            obs.extend(o.strip() for o in observations if o and str(o).strip())
        blob = "\n".join(obs)
        feats = extract_features(blob)
        dims = [
            ProcessDim.PERCEPTION.value,
            ProcessDim.SEEKING.value,
            ProcessDim.RECOGNITION.value,
        ]

        shortlist = self.store.fts_search(blob, limit=40)
        pool = shortlist or self.store.all_patterns(limit=2000)
        if shortlist and len(shortlist) < 30:
            extra = self.store.all_patterns(limit=1000)
            seen = {p.id for p in pool}
            for p in extra:
                if p.id not in seen:
                    pool.append(p)

        matches = match_patterns(blob, feats, pool, limit=10, min_score=0.06)
        for m in matches:
            m.pattern.touch(0.02)
            self.store.upsert_pattern(m.pattern)

        dims.append(ProcessDim.PROCESSING.value)
        distillation = distill(blob, matches=matches)

        dims.append(ProcessDim.PERCEPTION.value)  # novelty check
        anomalies = detect_anomalies(blob, pool, novelty_threshold=0.16)

        generated: List[Pattern] = []
        if ingest_query and query.strip():
            generated.append(
                self.ingest(
                    title=query.strip()[:80],
                    body=blob,
                    domain=domain,
                    confidence=0.55,
                    source="cycle",
                )
            )

        if file_novel and anomalies and anomalies[0].get("status") in {"novel", "uncatalogued"}:
            ap = file_anomaly(blob, matches=matches, domain=str(domain.value if isinstance(domain, Domain) else domain))
            self.store.upsert_pattern(ap)
            auto_link(self.store, ap, min_score=0.12, limit=6)
            generated.append(ap)
            dims.append(ProcessDim.MAINTENANCE.value)

        # Links from top match
        links_out: List[Dict[str, Any]] = []
        if matches:
            top = matches[0].pattern
            for lk in self.store.links_for(top.id, limit=12):
                links_out.append(lk.to_dict())
            # ensure fresh lateral proposals
            new_links = auto_link(self.store, top, min_score=0.2, limit=5)
            for lk in new_links:
                d = lk.to_dict()
                if d not in links_out:
                    links_out.append(d)

        dims.append(ProcessDim.GENERATION.value)
        traj = extrapolate(obs, matches=matches, title=f"traj:{distillation.actual_variable}")

        if evolve and matches:
            rep = evolve_once(self.store, focus=matches[0].pattern, decay=False)
            for sid in rep.get("syntheses") or []:
                sp = self.store.get_pattern(str(sid))
                if sp:
                    generated.append(sp)

        report = CycleReport(
            query=query,
            observations=obs,
            matches=matches,
            links=links_out,
            distillation=distillation,
            trajectory=traj,
            generated=generated,
            anomalies=anomalies,
            brief="",
            dims_used=list(dict.fromkeys(dims)),
        )
        report.brief = format_brief(report, style=brief_style)
        # store last one-liner in meta for CLI status
        self.store.set_meta("last_brief_line", compact_one_liner(distillation, matches, traj))
        return report

    # ------------------------------------------------------------------
    # Specialized ops
    # ------------------------------------------------------------------

    def distill(self, text: str) -> Dict[str, Any]:
        matches = match_patterns(text, extract_features(text), self.store.all_patterns(limit=1000), limit=8)
        return distill(text, matches=matches).to_dict()

    def extrapolate(self, observations: Sequence[str]) -> Dict[str, Any]:
        blob = "\n".join(observations)
        matches = match_patterns(blob, extract_features(blob), self.store.all_patterns(limit=1000), limit=8)
        return extrapolate(observations, matches=matches).to_dict()

    def analogy(self, pattern_id: str, target_domain: str, *, limit: int = 5) -> List[Dict[str, Any]]:
        src = self.store.get_pattern(pattern_id)
        if not src:
            return []
        return analogy_map(src, target_domain, self.store.all_patterns(limit=2000), limit=limit)

    def feedback(self, pattern_ids: Sequence[str], *, helpful: bool = True) -> List[Dict[str, Any]]:
        updated = reinforce(self.store, pattern_ids, helpful=helpful)
        return [p.to_dict() for p in updated]

    def evolve(self, *, decay: bool = True) -> Dict[str, Any]:
        return evolve_once(self.store, decay=decay)

    def stats(self) -> Dict[str, Any]:
        c = self.store.count()
        return {
            "db_path": str(self.db_path),
            "patterns": c["patterns"],
            "links": c["links"],
            "last_brief_line": self.store.get_meta("last_brief_line", ""),
        }

    def export_patterns(self, *, limit: int = 1000) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.store.list_patterns(limit=limit)]
