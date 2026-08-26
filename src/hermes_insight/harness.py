"""HermesInsight harness — the public agent API.

Cycle (aligned to superior pattern processing + ND connecting-the-dots):

1. Perception   — feature decompose observations
2. Recognition  — template / prototype / feature match (IDF hybrid)
3. Seeking      — FTS + lateral candidate hunt
4. Maintenance  — upsert catalogue, anomaly file
5. Processing   — distill actual variable (deep focus)
6. Generation   — trajectory + synthesis + optional new nodes
7. Transfer     — brief for the agent/human

Multi-agent: pass agent_id for compartmentalized lattices.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from hermes_insight.anomaly import detect_anomalies, file_anomaly
from hermes_insight.brief import compact_one_liner, format_brief
from hermes_insight.code_extract import file_to_pattern_fields
from hermes_insight.cross_domain import analogy_map, auto_link
from hermes_insight.distill import distill
from hermes_insight.evolve import evolve_once, reinforce
from hermes_insight.extrapolate import extrapolate
from hermes_insight.features import extract_features
from hermes_insight.match import build_idf, expand_query_features, match_patterns
from hermes_insight.models import (
    CycleReport,
    Domain,
    Evidence,
    Pattern,
    PatternKind,
    ProcessDim,
)
from hermes_insight.multi_agent import (
    AgentScope,
    MultiAgentRegistry,
    resolve_agent_db,
    sanitize_agent_id,
)
from hermes_insight.store import PatternStore

PathLike = Union[str, Path]


def default_db_path(*, agent_id: Optional[str] = None) -> Path:
    return resolve_agent_db(agent_id=agent_id)


class HermesInsight:
    """High-level harness. Construct once per agent profile/workspace."""

    def __init__(
        self,
        db_path: Optional[PathLike] = None,
        *,
        agent_id: Optional[str] = None,
        agent_tier: str = "worker",
    ) -> None:
        self.agent_id = sanitize_agent_id(agent_id) if agent_id else None
        self.db_path = (
            Path(db_path).expanduser().resolve()
            if db_path
            else resolve_agent_db(agent_id=self.agent_id)
        )
        self.store = PatternStore(self.db_path)
        self.agent_tier = agent_tier
        # registry lives next to multi-agent root when using agent_id
        home = Path(os.environ.get("HERMES_INSIGHT_HOME", "~/.hermes-insight")).expanduser()
        if os.environ.get("HERMES_HOME") and not os.environ.get("HERMES_INSIGHT_HOME"):
            home = Path(os.environ["HERMES_HOME"]) / "memories" / "hermes-insight"
        self._registry = MultiAgentRegistry(home / "agents.json")
        if self.agent_id and not self._registry.get(self.agent_id):
            self._registry.register(
                AgentScope(agent_id=self.agent_id, tier=agent_tier)
            )

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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Pattern:
        feats = list(features) if features else extract_features(f"{title}\n{body}")
        meta = dict(metadata or {})
        if self.agent_id:
            meta.setdefault("agent_id", self.agent_id)
            tags = list(tags or [])
            if self.agent_id not in tags:
                tags = [self.agent_id, *tags]
        pat = Pattern.create(
            title=title,
            body=body,
            kind=kind,
            domain=domain,
            features=feats,
            tags=tags,
            confidence=confidence,
            evidence=[Evidence(source=source, kind="observation", confidence=confidence)],
            metadata=meta,
        )
        # Lived events are occurrences, not reusable catalogue entries. Two tasks may
        # produce identical text and still need distinct timestamps, task links, and
        # outcome evidence. Structural nodes retain content deduplication.
        if pat.kind not in {PatternKind.EVENT, PatternKind.EPISODE, PatternKind.TASK}:
            for existing in self.store.list_patterns(limit=800):
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

    def ingest_file(
        self,
        path: PathLike,
        *,
        domain: Domain | str = Domain.CODE,
        link: bool = True,
        confidence: float = 0.55,
    ) -> Optional[Pattern]:
        from hermes_insight.scrub import scrub_metadata, scrub_text, should_skip_path

        p = Path(path).expanduser()
        if should_skip_path(str(p)):
            return None
        fields = file_to_pattern_fields(p)
        if not fields:
            return None
        title, body, features, tags, meta = fields
        body = scrub_text(body)
        meta = scrub_metadata(meta)
        if self.agent_id:
            tags = [self.agent_id, *tags]
            meta["agent_id"] = self.agent_id
        return self.ingest(
            title=title,
            body=body,
            domain=domain,
            features=features,
            tags=tags,
            confidence=confidence,
            source=p.name,
            link=link,
            metadata=meta,
        )

    def ingest_tree(
        self,
        root: PathLike,
        *,
        glob: str = "**/*.py",
        limit: int = 80,
        domain: Domain | str = Domain.CODE,
        link: bool = True,
        min_bytes: int = 80,
        max_bytes: int = 120_000,
    ) -> Dict[str, Any]:
        root_p = Path(root).expanduser().resolve()
        paths = [
            p
            for p in sorted(root_p.glob(glob))
            if p.is_file()
            and "__pycache__" not in p.parts
            and not p.name.startswith("test_")
            and min_bytes <= p.stat().st_size <= max_bytes
        ][:limit]
        ingested = 0
        skipped = 0
        ids: List[str] = []
        for p in paths:
            pat = self.ingest_file(p, domain=domain, link=link)
            if pat:
                ingested += 1
                ids.append(pat.id)
            else:
                skipped += 1
        return {
            "root": str(root_p),
            "candidates": len(paths),
            "ingested": ingested,
            "skipped": skipped,
            "pattern_ids": ids[:50],
            "stats": self.stats(),
        }

    def get(self, pattern_id: str) -> Optional[Pattern]:
        return self.store.get_pattern(pattern_id)

    def search(self, query: str, *, limit: int = 15) -> List[Pattern]:
        fts = self.store.fts_search(query, limit=limit)
        if len(fts) >= limit:
            return fts
        feats = expand_query_features(extract_features(query))
        pool = self.store.candidate_pool(query, fts_limit=40, structural_limit=80, fill_limit=60)
        idf = build_idf(pool)
        ranked = match_patterns(query, feats, pool, limit=limit, idf=idf)
        seen = {p.id for p in fts}
        out = list(fts)
        for m in ranked:
            if m.pattern.id not in seen:
                out.append(m.pattern)
                seen.add(m.pattern.id)
            if len(out) >= limit:
                break
        return out

    def match(
        self,
        query: str,
        *,
        limit: int = 10,
        min_score: float = 0.04,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        feats = expand_query_features(extract_features(query))
        pool = self.store.candidate_pool(
            query,
            domain=domain,
            fts_limit=48,
            structural_limit=140,
            fill_limit=60,
        )
        idf = build_idf(pool)
        hits = match_patterns(
            query,
            feats,
            pool,
            limit=limit,
            min_score=min_score,
            domain_hint=domain,
            idf=idf,
        )
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
        feats = expand_query_features(extract_features(blob))
        domain_s = domain.value if isinstance(domain, Domain) else str(domain)
        dims = [
            ProcessDim.PERCEPTION.value,
            ProcessDim.SEEKING.value,
            ProcessDim.RECOGNITION.value,
        ]

        pool = self.store.candidate_pool(
            blob,
            domain=None if domain_s == "general" else domain_s,
            fts_limit=56,
            structural_limit=160,
            fill_limit=80,
        )
        if not pool:
            pool = self.store.all_patterns(limit=500)
        idf = build_idf(pool)
        matches = match_patterns(
            blob,
            feats,
            pool,
            limit=12,
            min_score=0.04,
            domain_hint=domain_s if domain_s != "general" else None,
            idf=idf,
        )
        for m in matches:
            m.pattern.touch(0.02)
            self.store.upsert_pattern(m.pattern)

        dims.append(ProcessDim.PROCESSING.value)
        distillation = distill(blob, matches=matches, domain_hint=domain_s)

        dims.append(ProcessDim.PERCEPTION.value)
        anomalies = detect_anomalies(blob, pool, novelty_threshold=0.14)

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
            ap = file_anomaly(
                blob,
                matches=matches,
                domain=domain_s,
            )
            if self.agent_id:
                ap.metadata["agent_id"] = self.agent_id
                ap.tags = list(dict.fromkeys([self.agent_id, *ap.tags]))
            self.store.upsert_pattern(ap)
            auto_link(self.store, ap, min_score=0.12, limit=6)
            generated.append(ap)
            dims.append(ProcessDim.MAINTENANCE.value)

        links_out: List[Dict[str, Any]] = []
        if matches:
            top = matches[0].pattern
            for lk in self.store.links_for(top.id, limit=12):
                links_out.append(lk.to_dict())
            new_links = auto_link(self.store, top, min_score=0.18, limit=6)
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
        if self.agent_id:
            report.brief = f"_agent: `{self.agent_id}` ({self.agent_tier})_\n\n" + report.brief
        self.store.set_meta(
            "last_brief_line",
            compact_one_liner(distillation, matches, traj),
        )
        return report

    # ------------------------------------------------------------------
    # Specialized ops
    # ------------------------------------------------------------------

    def distill(self, text: str, *, domain: Optional[str] = None) -> Dict[str, Any]:
        pool = self.store.candidate_pool(text, domain=domain, fts_limit=40, structural_limit=120, fill_limit=60)
        matches = match_patterns(
            text,
            expand_query_features(extract_features(text)),
            pool,
            limit=10,
            domain_hint=domain,
            idf=build_idf(pool),
        )
        return distill(text, matches=matches, domain_hint=domain).to_dict()

    def extrapolate(self, observations: Sequence[str]) -> Dict[str, Any]:
        blob = "\n".join(observations)
        pool = self.store.candidate_pool(blob, fts_limit=40, structural_limit=100, fill_limit=50)
        matches = match_patterns(
            blob,
            expand_query_features(extract_features(blob)),
            pool,
            limit=10,
            idf=build_idf(pool),
        )
        return extrapolate(observations, matches=matches).to_dict()

    def analogy(self, pattern_id: str, target_domain: str, *, limit: int = 5) -> List[Dict[str, Any]]:
        src = self.store.get_pattern(pattern_id)
        if not src:
            return []
        return analogy_map(src, target_domain, self.store.all_patterns(limit=2500), limit=limit)

    def feedback(self, pattern_ids: Sequence[str], *, helpful: bool = True) -> List[Dict[str, Any]]:
        updated = reinforce(self.store, pattern_ids, helpful=helpful)
        return [p.to_dict() for p in updated]

    def evolve(self, *, decay: bool = True) -> Dict[str, Any]:
        return evolve_once(self.store, decay=decay)

    def register_agent(
        self,
        agent_id: str,
        *,
        tier: str = "worker",
        display_name: str = "",
        parent_id: Optional[str] = None,
        share_tags: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        scope = AgentScope(
            agent_id=agent_id,
            display_name=display_name or agent_id,
            tier=tier,
            parent_id=parent_id,
            share_tags=list(share_tags or []),
        )
        return self._registry.register(scope).to_dict()

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._registry.list()]

    def stats(self) -> Dict[str, Any]:
        c = self.store.count()
        from hermes_insight import __version__
        from hermes_insight.mindset import resolve_plate

        return {
            "db_path": str(self.db_path),
            "agent_id": self.agent_id,
            "agent_tier": self.agent_tier,
            "patterns": c["patterns"],
            "links": c["links"],
            "last_brief_line": self.store.get_meta("last_brief_line", ""),
            "last_experience_line": self.store.get_meta("last_experience_line", ""),
            "last_recall_line": self.store.get_meta("last_recall_line", ""),
            "active_task_id": self.store.get_meta("active_task_id", ""),
            "mindset": resolve_plate(self).to_dict(),
            "version": __version__,
        }

    def attune(self, mindset: Any = "balanced", **axes: Any) -> Dict[str, Any]:
        """Set the active cognitive plate. The plate can change at any time."""
        from hermes_insight.mindset import attune as _attune

        return _attune(self, mindset, **axes)

    # ------------------------------------------------------------------
    # Experience — tasks, events, fast recall (any Hermes agent path)
    # ------------------------------------------------------------------

    def plan(
        self,
        situation: str,
        *,
        observations: Optional[Sequence[str]] = None,
        domain: Optional[str] = None,
        limit: int = 5,
        mindset: Any = None,
    ) -> Dict[str, Any]:
        """Rank applicable patterns and affordances using explicit task outcomes."""
        from hermes_insight.planner import plan_task

        return plan_task(
            self,
            situation,
            observations=observations,
            domain=domain,
            limit=limit,
            mindset=mindset,
        )

    def learn(
        self,
        *,
        min_support: int = 3,
        min_steps: int = 2,
        max_steps: int = 4,
        limit: int = 12,
        materialize: bool = False,
    ) -> Dict[str, Any]:
        """Induce recurring workflows from independent typed task traces."""
        from hermes_insight.induction import induce_workflows

        return induce_workflows(
            self,
            min_support=min_support,
            min_steps=min_steps,
            max_steps=max_steps,
            limit=limit,
            materialize=materialize,
        )

    def snapshot_environment(
        self,
        root: PathLike = ".",
        *,
        include_tools: bool = True,
    ) -> Dict[str, Any]:
        """Capture scrubbed workspace state and a delta from its prior snapshot."""
        from hermes_insight.observation import snapshot_environment

        return snapshot_environment(self, root, include_tools=include_tools)

    def record_event(
        self,
        event_type: str,
        summary: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Record a typed, provenance-rich event in the existing Insight lattice."""
        from hermes_insight.observation import record_event

        return record_event(self, event_type, summary, **kwargs)

    def perceive(
        self,
        situation: str,
        *,
        observations: Optional[Sequence[str]] = None,
        domain: Optional[str] = None,
        limit: int = 8,
        log_experience: bool = False,
        experience_title: Optional[str] = None,
        task_id: Optional[str] = None,
        deep: bool = False,
        mindset: Any = None,
    ) -> Dict[str, Any]:
        """Pattern recognition ability — one call for lever + priors + action hint."""
        from hermes_insight.ability import perceive as _perceive

        return _perceive(
            self,
            situation,
            observations=observations,
            domain=domain,
            limit=limit,
            log_experience=log_experience,
            experience_title=experience_title,
            task_id=task_id,
            deep=deep,
            mindset=mindset,
        )

    def perceive_card(
        self,
        goal: str,
        *,
        load: str = "mid",
        observations: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Bounded Space-cable card — lever + rule + usable + action_hint only.

        Feature-detect::

            from hermes_insight import HermesInsight
            if hasattr(HermesInsight, "perceive_card"):
                card = HermesInsight(...).perceive_card(goal, load="mid")

        High/protect load returns an empty card immediately. Never dumps the
        lattice, never injects ``perceive()["card"]``, never calls ``plan()``.
        """
        from hermes_insight.card import build_perceive_card

        return build_perceive_card(self, goal, load=load, observations=observations)

    def hygiene(self, *, decay: bool = True, densify: bool = True, prune_session_auto: bool = True) -> Dict[str, Any]:
        """Decay fabric noise + densify structural links (periodic maintenance)."""
        out: Dict[str, Any] = {}
        if densify:
            from hermes_insight.experience import densify_structural_links

            out["densify"] = densify_structural_links(self)
        if decay:
            out["decay"] = self.store.decay_fabric_noise()
        if prune_session_auto:
            weakened = 0
            for p in self.store.list_patterns(kind="episode", limit=500):
                tags = set(p.tags or [])
                if "session" in tags and "auto" in tags and "material" not in tags:
                    if p.title.startswith("session turn") or p.title.startswith("session completed"):
                        old = p.strength
                        p.strength = max(0.08, p.strength * 0.5)
                        if p.strength < old:
                            self.store.upsert_pattern(p)
                            weakened += 1
            out["session_auto_weakened"] = weakened
        return out

    def bootstrap(self, *, force: bool = False) -> Dict[str, Any]:
        """Seed starter agent-field patterns so a fresh lattice can match."""
        from hermes_insight.experience import seed_agent_starters

        return seed_agent_starters(self, force=force)

    def experience(
        self,
        title: str,
        body: str,
        *,
        kind: str = "event",
        task_id: Optional[str] = None,
        outcome: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        confidence: float = 0.65,
        auto_connect: bool = True,
    ) -> Dict[str, Any]:
        """Log a lived event/episode and auto-link to structural patterns."""
        from hermes_insight.experience import log_experience

        return log_experience(
            self,
            title,
            body,
            kind=kind,
            task_id=task_id or self.store.get_meta("active_task_id") or None,
            outcome=outcome,
            tags=tags,
            confidence=confidence,
            auto_connect=auto_connect,
        )

    def recall(
        self,
        query: str,
        *,
        limit: int = 8,
        include_experiences: bool = True,
        domain: Optional[str] = None,
        write_meta: bool = True,
        observations: Optional[Sequence[str]] = None,
        environment_id: Optional[str] = None,
        task_id: Optional[str] = None,
        mindset: Any = None,
    ) -> Dict[str, Any]:
        """Associative pre-action recall: dual-process working set + usable flag."""
        from hermes_insight.recall import recall as _recall

        return _recall(
            self,
            query,
            limit=limit,
            include_experiences=include_experiences,
            domain=domain,
            write_meta=write_meta,
            observations=observations,
            environment_id=environment_id,
            task_id=task_id,
            mindset=mindset,
        )

    def remember(
        self,
        claim: str,
        *,
        source: str = "",
        salience: float = 0.6,
        pointer: str = "",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store one compact durable fact/engram. Pointers are refs, not contents."""
        from hermes_insight.recall import remember as _remember

        return _remember(
            self,
            claim,
            source=source,
            salience=salience,
            pointer=pointer,
            task_id=task_id,
        )

    def open_task(
        self,
        name: str,
        *,
        goal: str = "",
        tags: Optional[Sequence[str]] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Open a task episode; returns task_id and prior pattern matches."""
        from hermes_insight.experience import open_task as _open

        return _open(self, name, goal=goal, tags=tags, task_id=task_id)

    def close_task(
        self,
        task_id: Optional[str] = None,
        *,
        outcome: str = "done",
        summary: str = "",
        reinforce_connected: bool = True,
        used_pattern_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Close a task and optionally credit patterns that were actually applied."""
        from hermes_insight.experience import close_task as _close

        tid = task_id or self.store.get_meta("active_task_id", "")
        if not tid:
            return {"success": False, "error": "no task_id (pass one or open_task first)"}
        return _close(
            self,
            tid,
            outcome=outcome,
            summary=summary,
            reinforce_connected=reinforce_connected,
            used_pattern_ids=used_pattern_ids,
        )

    def connect(
        self,
        left: str,
        right: Optional[str] = None,
        *,
        kind: str = "similar",
        note: str = "",
        weight: float = 0.6,
    ) -> Dict[str, Any]:
        """Explicit link two patterns, or auto-connect free text into the lattice."""
        from hermes_insight.experience import connect as _connect

        return _connect(self, left, right, kind=kind, note=note, weight=weight)

    def ingest_messages(
        self,
        messages: Sequence[Dict[str, Any]],
        *,
        task_id: Optional[str] = None,
        title: str = "session slice",
    ) -> Dict[str, Any]:
        """Ingest a scrubbed chat transcript slice as a connected episode."""
        from hermes_insight.experience import ingest_messages as _ing

        return _ing(
            self,
            messages,
            task_id=task_id or self.store.get_meta("active_task_id") or None,
            title=title,
        )

    def export_patterns(self, *, limit: int = 1000) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.store.list_patterns(limit=limit)]

    # ------------------------------------------------------------------
    # Server fabric — see projects, files, metadata, connections
    # ------------------------------------------------------------------

    def index_server(
        self,
        *,
        roots: Optional[Sequence[str | Path]] = None,
        include_projects: bool = True,
        include_files: bool = True,
        include_connections: bool = True,
        include_processes: bool = True,
        include_hermes: bool = True,
        max_files_per_project: int = 40,
        max_projects: int = 80,
        link: bool = True,
    ) -> Dict[str, Any]:
        """Index the machine fabric into this lattice (secrets scrubbed)."""
        from hermes_insight.fabric import FabricIndexer

        report = FabricIndexer(self).index_server(
            roots=roots,
            include_projects=include_projects,
            include_files=include_files,
            include_connections=include_connections,
            include_processes=include_processes,
            include_hermes=include_hermes,
            max_files_per_project=max_files_per_project,
            max_projects=max_projects,
            link=link,
        )
        self.store.set_meta("last_fabric_index", str(report.to_dict()))
        out = report.to_dict()
        out["stats"] = self.stats()
        return out

    def index_path(
        self,
        path: PathLike,
        *,
        as_project: bool = True,
        max_files: int = 60,
        link: bool = True,
    ) -> Dict[str, Any]:
        """Index one project or directory tree into the lattice."""
        from hermes_insight.fabric import FabricIndexer, project_summary
        from hermes_insight.features import extract_features
        from hermes_insight.scrub import scrub_text

        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"success": False, "error": f"path not found: {p}"}
        idx = FabricIndexer(self)
        report_files = 0
        project_id = None
        if as_project or p.is_dir():
            summary = project_summary(p if p.is_dir() else p.parent)
            body = (
                f"Path index `{summary.get('name')}`\n"
                f"manifests: {summary.get('manifests')}\n"
                f"languages: {summary.get('languages')}\n"
                f"{summary.get('readme_head') or ''}"
            )
            pat = self.ingest(
                title=f"project:{summary.get('name')}",
                body=scrub_text(body)[:3500],
                domain=Domain.CODE,
                kind=PatternKind.PROTOTYPE,
                tags=["fabric", "project", str(summary.get("name"))[:32]],
                features=extract_features(body),
                confidence=0.65,
                source="index-path",
                metadata={"fabric": "project", **summary},
                link=link,
            )
            project_id = pat.id
            if p.is_dir():
                from hermes_insight.fabric import FabricReport

                rep = FabricReport()
                report_files = idx._ingest_project_files(
                    p,
                    project_id=pat.id,
                    max_files=max_files,
                    globs=("**/*.py", "**/*.ts", "**/*.tsx", "**/*.md", "**/*.yaml", "**/*.yml", "**/*.toml"),
                    link=link,
                    report=rep,
                )
                return {
                    "success": True,
                    "project_id": project_id,
                    "files_ingested": rep.files_ingested,
                    "skipped": rep.skipped,
                    "stats": self.stats(),
                }
            else:
                fp = self.ingest_file(p, link=link)
                return {
                    "success": True,
                    "project_id": project_id,
                    "file_id": fp.id if fp else None,
                    "stats": self.stats(),
                }
        fp = self.ingest_file(p, link=link)
        return {"success": bool(fp), "file_id": fp.id if fp else None, "stats": self.stats()}

    def index_connections(self, *, link: bool = True) -> Dict[str, Any]:
        """Index listening ports / process connections only."""
        return self.index_server(
            roots=[],
            include_projects=False,
            include_files=False,
            include_connections=True,
            include_processes=True,
            include_hermes=False,
            link=link,
        )

    def fabric_stats(self) -> Dict[str, Any]:
        """Counts of fabric-tagged patterns currently in the lattice."""
        patterns = self.store.all_patterns(limit=10000)
        fabric = [p for p in patterns if "fabric" in (p.tags or []) or (p.metadata or {}).get("fabric")]
        by = {}
        for p in fabric:
            kind = (p.metadata or {}).get("fabric") or "tagged"
            by[kind] = by.get(kind, 0) + 1
        return {
            "fabric_patterns": len(fabric),
            "by_kind": by,
            "last_index": self.store.get_meta("last_fabric_index", "")[:500],
            "stats": self.stats(),
        }

    def forge(
        self,
        *,
        out_dir: Optional[PathLike] = None,
        write_synthesis: bool = True,
        products: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Turn lattice connections into human-usable products (map/predict/transfer/invent/act/watch)."""
        from hermes_insight.forge import forge as _forge

        bundle = _forge(
            self,
            out_dir=out_dir,
            write_synthesis=write_synthesis,
            products=products,
        )
        self.store.set_meta("last_forge_dir", bundle.stats.get("run_dir", ""))
        return {
            "success": True,
            "run_dir": bundle.stats.get("run_dir"),
            "products": list(bundle.products.keys()),
            "synthesis_ids": bundle.synthesis_ids,
            "stats": bundle.stats,
            "created_at": bundle.created_at,
        }
