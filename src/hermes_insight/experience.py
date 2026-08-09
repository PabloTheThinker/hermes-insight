"""Experience layer — connect tasks & events to structural patterns fast.

Any Hermes agent should be able to:

1. **recall** before acting (what have we seen like this?)
2. **experience** / note events mid-task (catalogue lived structure)
3. **open/close tasks** so multi-step work becomes an episode with links
4. **connect** two things explicitly (or auto-link a blob to the lattice)
5. **bootstrap** starter agent-field patterns so a fresh DB is not empty

Design: experiences are first-class Pattern nodes (kind=event|episode|task)
with tags ``experience``, optional ``task:<id>``, and auto-links into the
existing lattice. No separate storage silo — FTS + match still work.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

from hermes_insight.cross_domain import auto_link
from hermes_insight.distill import distill
from hermes_insight.features import extract_features
from hermes_insight.match import build_idf, expand_query_features, match_patterns
from hermes_insight.models import (
    Domain,
    Evidence,
    Link,
    LinkKind,
    Pattern,
    PatternKind,
)
from hermes_insight.scrub import scrub_text

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight
    from hermes_insight.store import PatternStore


def _new_task_id() -> str:
    return f"t_{uuid.uuid4().hex[:10]}"


def _task_tag(task_id: str) -> str:
    tid = re.sub(r"[^a-zA-Z0-9_\-]", "", task_id)[:48]
    return f"task:{tid}"


# ---------------------------------------------------------------------------
# Starter patterns — so any fresh agent has something to match against
# ---------------------------------------------------------------------------

AGENT_STARTER_PATTERNS: List[Dict[str, Any]] = [
    {
        "title": "credential single-consumer",
        "body": (
            "Bot tokens, OAuth long-poll, and exclusive locks break when two "
            "workers share one credential. Symptom: conflict / 409 / silent hang."
        ),
        "kind": "rule",
        "domain": "agent",
        "tags": ["credential", "token", "gateway", "conflict", "longpoll"],
        "features": ["credential", "consumer", "token", "conflict", "exclusive"],
    },
    {
        "title": "tool schema token waist",
        "body": (
            "Every core tool schema is paid on every model call. Prefer skills, "
            "CLI+skill, deferred tools, or plugins over growing the core toolset."
        ),
        "kind": "rule",
        "domain": "agent",
        "tags": ["tools", "tokens", "schema", "footprint", "cache"],
        "features": ["tool", "schema", "token", "cache", "footprint"],
    },
    {
        "title": "prompt cache sacred",
        "body": (
            "Do not mutate past context, toolsets, or system prompt mid-conversation. "
            "Breaks prompt caching and multiplies cost. Compress is the exception."
        ),
        "kind": "rule",
        "domain": "agent",
        "tags": ["cache", "prompt", "context", "cost"],
        "features": ["cache", "prompt", "context", "compression"],
    },
    {
        "title": "skill from hard fix",
        "body": (
            "After a multi-step fix or user correction, write or patch a skill. "
            "Preferences go to memory; procedures go to skills; chat history is not enough."
        ),
        "kind": "rule",
        "domain": "skill",
        "tags": ["skill", "learn", "memory", "procedure"],
        "features": ["skill", "patch", "learn", "procedure", "memory"],
    },
    {
        "title": "delegate vs durable work",
        "body": (
            "delegate_task dies with the parent process. Use cron or "
            "terminal(background, notify_on_complete) for work that must outlive the session."
        ),
        "kind": "rule",
        "domain": "multi_agent",
        "tags": ["delegate", "cron", "durable", "background"],
        "features": ["delegate", "cron", "background", "durable", "session"],
    },
    {
        "title": "profile isolation wall",
        "body": (
            "Hermes profiles are islands. Client secrets, SOUL, and skills must not "
            "bleed across profiles. Separate Insight DBs per trust boundary."
        ),
        "kind": "rule",
        "domain": "multi_agent",
        "tags": ["profile", "isolation", "client", "compartment"],
        "features": ["profile", "isolation", "compartment", "client", "secret"],
    },
    {
        "title": "retry storm amplifies load",
        "body": (
            "Blind retries without jitter/backoff turn a dependency blip into a self-DDoS. "
            "Couple retries with circuit breakers and alert dedupe."
        ),
        "kind": "rule",
        "domain": "system",
        "tags": ["retry", "backoff", "circuit", "alert"],
        "features": ["retry", "backoff", "jitter", "circuit", "storm"],
    },
    {
        "title": "observation vs inference",
        "body": (
            "Separate what was seen from what was concluded. Pattern briefs must "
            "label confidence and not invent file contents or API results."
        ),
        "kind": "rule",
        "domain": "agent",
        "tags": ["evidence", "hygiene", "hallucination", "brief"],
        "features": ["observation", "inference", "evidence", "confidence"],
    },
    {
        "title": "session interrupt delivery gap",
        "body": (
            "When a stream is interrupted, final delivery can be dropped leaving a "
            "partial cursor. Always verify the user got the last complete answer."
        ),
        "kind": "prototype",
        "domain": "agent",
        "tags": ["gateway", "interrupt", "delivery", "stream"],
        "features": ["interrupt", "stream", "delivery", "gateway", "partial"],
    },
    {
        "title": "skill routing not skill dump",
        "body": (
            "When skill count is high, route by task class and model cost — do not load "
            "every skill. Distill the job, pick one skill, patch it when wrong."
        ),
        "kind": "rule",
        "domain": "skill",
        "tags": ["skill", "routing", "sprawl", "model", "selection"],
        "features": ["skill", "routing", "sprawl", "selection", "model"],
    },
    {
        "title": "recurring failure is a pattern",
        "body": (
            "The second time the same class of failure appears, catalogue it and "
            "link to the fix. Third time should hit recall, not rediscovery."
        ),
        "kind": "rule",
        "domain": "experience",
        "tags": ["recurring", "catalogue", "recall", "learn"],
        "features": ["recurring", "failure", "catalogue", "recall", "link"],
    },
]


def densify_structural_links(lat: "HermesInsight", *, min_score: float = 0.12, limit_per: int = 10) -> Dict[str, Any]:
    """Ensure rules/starters/skills are linked into the graph (fixes empty hops)."""
    from hermes_insight.cross_domain import auto_link

    structural = []
    seen = set()
    for p in lat.store.list_patterns(kind="rule", limit=40):
        if p.id not in seen:
            seen.add(p.id); structural.append(p)
    for p in lat.store.list_patterns(kind="synthesis", limit=20):
        if p.id not in seen:
            seen.add(p.id); structural.append(p)
    for p in lat.store.structural_patterns(limit=40):
        if "starter" in (p.tags or []) or p.kind.value in {"event", "episode", "task"}:
            if p.id not in seen:
                seen.add(p.id); structural.append(p)
    structural = structural[:60]
    linked = 0
    for p in structural:
        before = len(lat.store.links_for(p.id, limit=50))
        auto_link(lat.store, p, candidates=structural, min_score=min_score, limit=limit_per)
        after = len(lat.store.links_for(p.id, limit=50))
        if after > before:
            linked += 1
    return {"structural_nodes": len(structural), "nodes_gained_links": linked}


def seed_agent_starters(lat: "HermesInsight", *, force: bool = False) -> Dict[str, Any]:
    """Install starter patterns if structural starters missing (or force)."""
    st = lat.stats()
    existing_starters = [
        p
        for p in lat.store.list_patterns(kind="rule", limit=50)
        if "starter" in (p.tags or []) or "bootstrap" in (p.tags or [])
    ]
    if len(existing_starters) >= 6 and not force:
        # Cheap orphan check — full densify only when structural graph is sparse
        import time as _time

        last = float(lat.store.get_meta("last_densify_at", "0") or 0)
        now = _time.time()
        rules = lat.store.list_patterns(kind="rule", limit=20)
        orphan_rules = sum(1 for r in rules if not lat.store.links_for(r.id, limit=1))
        dens: Dict[str, Any] = {}
        # densify at most every 6h; prefer starters-only for speed
        if (orphan_rules >= 3 or last <= 0) and (now - last > 21600):
            dens = densify_structural_links(lat, min_score=0.12, limit_per=6)
            # only densify starter/rule subset already limited inside function
            lat.store.set_meta("last_densify_at", str(now))
        dens.update(
            {
                "seeded": 0,
                "skipped": True,
                "reason": "starters present",
                "patterns": st["patterns"],
                "starters": len(existing_starters),
            }
        )
        return dens
    ids: List[str] = []
    for row in AGENT_STARTER_PATTERNS:
        pat = lat.ingest(
            row["title"],
            row["body"],
            kind=row.get("kind", "rule"),
            domain=row.get("domain", "agent"),
            tags=list(row.get("tags") or []) + ["starter", "bootstrap"],
            features=row.get("features"),
            confidence=0.75,
            source="bootstrap",
            link=False,  # densify as a batch after all seeds land
        )
        ids.append(pat.id)
    dens = densify_structural_links(lat, min_score=0.10, limit_per=12)
    lat.store.set_meta("bootstrap_version", "0.7.2")
    import time as _time

    lat.store.set_meta("last_densify_at", str(_time.time()))
    return {"seeded": len(ids), "pattern_ids": ids, "skipped": False, **dens}


# ---------------------------------------------------------------------------
# Core experience ops
# ---------------------------------------------------------------------------

def log_experience(
    lat: "HermesInsight",
    title: str,
    body: str,
    *,
    kind: str = "event",
    task_id: Optional[str] = None,
    outcome: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
    confidence: float = 0.65,
    auto_connect: bool = True,
    connect_limit: int = 8,
) -> Dict[str, Any]:
    """Catalogue a lived event/episode and auto-link to similar patterns."""
    title = scrub_text(title or "").strip()[:120]
    body = scrub_text(body or "").strip()
    if not title or not body:
        return {"success": False, "error": "title and body required"}

    kind_map = {
        "event": PatternKind.EVENT,
        "episode": PatternKind.EPISODE,
        "task": PatternKind.TASK,
        "sequence": PatternKind.SEQUENCE,
    }
    pk = kind_map.get(str(kind).lower(), PatternKind.EVENT)
    tag_list = ["experience", str(kind).lower()]
    if task_id:
        tag_list.append(_task_tag(task_id))
    for t in tags or []:
        if t and str(t).lower() not in tag_list:
            tag_list.append(str(t).lower())
    if outcome:
        tag_list.append(f"outcome:{str(outcome).lower()[:32]}")

    meta: Dict[str, Any] = {
        "experience": True,
        "outcome": outcome,
        "task_id": task_id,
        "logged_at": time.time(),
    }
    if lat.agent_id:
        meta["agent_id"] = lat.agent_id

    pat = lat.ingest(
        title,
        body,
        kind=pk,
        domain=Domain.EXPERIENCE,
        tags=tag_list,
        confidence=confidence,
        source="experience",
        link=False,  # we link more carefully below
        metadata=meta,
    )

    connected: List[Dict[str, Any]] = []
    if auto_connect:
        blob = f"{title}\n{body}"
        feats = expand_query_features(extract_features(blob))
        pool = lat.store.candidate_pool(
            blob, fts_limit=40, structural_limit=120, fill_limit=40
        )
        pool = [p for p in pool if p.id != pat.id]
        if len(pool) < 20:
            pool = [p for p in lat.store.structural_patterns(limit=100) if p.id != pat.id]
        idf = build_idf(pool)
        hits = match_patterns(blob, feats, pool, limit=connect_limit, min_score=0.06, idf=idf)
        for h in hits:
            # experience instance-of / experienced_as structural pattern
            lk_kind = LinkKind.EXPERIENCED_AS
            if h.pattern.kind in {PatternKind.RULE, PatternKind.PROTOTYPE, PatternKind.TEMPLATE}:
                lk_kind = LinkKind.INSTANCE_OF
            link = Link(
                id=f"l_{uuid.uuid4().hex[:12]}",
                source_id=pat.id,
                target_id=h.pattern.id,
                kind=lk_kind,
                weight=min(1.0, max(0.15, h.score)),
                note=f"auto experience link score={h.score:.3f}",
            )
            lat.store.upsert_link(link)
            h.pattern.touch(0.025)
            lat.store.upsert_pattern(h.pattern)
            connected.append(
                {
                    "pattern_id": h.pattern.id,
                    "title": h.pattern.title,
                    "score": round(h.score, 4),
                    "method": h.method,
                    "link_kind": lk_kind.value,
                }
            )
        # also generic auto_link for analogy hops
        auto_link(lat.store, pat, min_score=0.16, limit=6)

    # temporal chain within task
    if task_id:
        _chain_task_event(lat.store, pat, task_id)

    one_liner = ""
    if connected:
        one_liner = f"linked→ {connected[0]['title']} ({connected[0]['score']:.2f})"
    else:
        one_liner = "novel experience (no strong prior match)"

    lat.store.set_meta("last_experience_id", pat.id)
    lat.store.set_meta("last_experience_line", f"{title}: {one_liner}")

    return {
        "success": True,
        "experience": pat.to_dict(),
        "connected": connected,
        "one_liner": one_liner,
        "task_id": task_id,
    }


def _chain_task_event(store: "PatternStore", pat: Pattern, task_id: str) -> None:
    """Link this event as NEXT after the previous event in the same task."""
    tag = _task_tag(task_id)
    # find recent experiences with same task tag
    recent = [
        p
        for p in store.list_patterns(domain=Domain.EXPERIENCE.value, limit=40)
        if tag in (p.tags or []) and p.id != pat.id
    ]
    if not recent:
        # also scan general list
        recent = [
            p
            for p in store.list_patterns(limit=80)
            if tag in (p.tags or []) and p.id != pat.id and p.kind in {
                PatternKind.EVENT, PatternKind.EPISODE, PatternKind.TASK, PatternKind.SEQUENCE
            }
        ]
    if not recent:
        return
    prev = max(recent, key=lambda p: p.updated_at or p.created_at)
    link = Link(
        id=f"l_{uuid.uuid4().hex[:12]}",
        source_id=prev.id,
        target_id=pat.id,
        kind=LinkKind.NEXT,
        weight=0.7,
        note=f"task chain {task_id}",
        metadata={"task_id": task_id},
    )
    store.upsert_link(link)


def open_task(
    lat: "HermesInsight",
    name: str,
    *,
    goal: str = "",
    tags: Optional[Sequence[str]] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Open a task episode. Returns task_id for subsequent experience logs."""
    tid = task_id or _new_task_id()
    body = scrub_text((goal or "").strip() or f"Task opened: {name}")
    seed_agent_starters(lat)
    return _open_task_impl(lat, name, goal=body, tags=tags, task_id=tid)


def _open_task_impl(
    lat: "HermesInsight",
    name: str,
    *,
    goal: str = "",
    tags: Optional[Sequence[str]] = None,
    task_id: str,
) -> Dict[str, Any]:
    body = goal or f"Task opened: {name}"
    recall_pack = recall(lat, f"{name}\n{body}", limit=6, write_meta=False)
    res = log_experience(
        lat,
        title=f"task open: {name}"[:100],
        body=body,
        kind="task",
        task_id=task_id,
        tags=list(tags or []) + ["task_open", "open"],
        confidence=0.7,
        auto_connect=True,
    )
    lat.store.set_meta("active_task_id", task_id)
    lat.store.set_meta("active_task_name", name)
    return {
        "success": True,
        "task_id": task_id,
        "name": name,
        "status": "open",
        "experience": res.get("experience"),
        "priors": recall_pack.get("matches", [])[:6],
        "brief": recall_pack.get("brief", ""),
        "connected": res.get("connected", []),
    }


def close_task(
    lat: "HermesInsight",
    task_id: str,
    *,
    outcome: str = "done",
    summary: str = "",
    reinforce_connected: bool = True,
) -> Dict[str, Any]:
    """Close a task: log outcome episode, reinforce helpful patterns."""
    summary = scrub_text(summary or f"Task {task_id} closed with outcome={outcome}")
    res = log_experience(
        lat,
        title=f"task close: {outcome}"[:100],
        body=summary,
        kind="episode",
        task_id=task_id,
        outcome=outcome,
        tags=["task_close", str(outcome).lower()],
        confidence=0.75,
        auto_connect=True,
    )
    reinforced: List[str] = []
    if reinforce_connected and outcome.lower() in {"done", "success", "fixed", "shipped", "resolved"}:
        ids = [c["pattern_id"] for c in res.get("connected") or []]
        if ids:
            from hermes_insight.evolve import reinforce

            updated = reinforce(lat.store, ids, helpful=True)
            reinforced = [p.id for p in updated]
    elif reinforce_connected and outcome.lower() in {"failed", "blocked", "wrong"}:
        ids = [c["pattern_id"] for c in res.get("connected") or []]
        if ids:
            from hermes_insight.evolve import reinforce

            reinforce(lat.store, ids[:3], helpful=False)

    active = lat.store.get_meta("active_task_id", "")
    if active == task_id:
        lat.store.set_meta("active_task_id", "")
        lat.store.set_meta("active_task_name", "")

    return {
        "success": True,
        "task_id": task_id,
        "status": "closed",
        "outcome": outcome,
        "experience": res.get("experience"),
        "connected": res.get("connected", []),
        "reinforced": reinforced,
        "one_liner": res.get("one_liner"),
    }


def recall(
    lat: "HermesInsight",
    query: str,
    *,
    limit: int = 8,
    include_experiences: bool = True,
    write_meta: bool = True,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """Fast pre-action recall: matches + related experiences + one brief."""
    query = scrub_text(query or "").strip()
    if not query:
        return {"success": False, "error": "query required", "matches": [], "experiences": [], "brief": ""}

    seed_agent_starters(lat)

    feats = expand_query_features(extract_features(query))
    pool = lat.store.candidate_pool(
        query,
        domain=domain,
        fts_limit=48,
        structural_limit=140,
        fill_limit=50,
    )
    idf = build_idf(pool)
    hits = match_patterns(
        query,
        feats,
        pool,
        limit=limit,
        min_score=0.04,
        domain_hint=domain,
        idf=idf,
    )
    matches: List[Dict[str, Any]] = []
    experiences: List[Dict[str, Any]] = []
    for i, h in enumerate(hits):
        if i < 3:
            h.pattern.touch(0.01)
            lat.store.upsert_pattern(h.pattern)
        row = {
            "id": h.pattern.id,
            "title": h.pattern.title,
            "score": round(h.score, 4),
            "method": h.method,
            "kind": h.pattern.kind.value,
            "domain": h.pattern.domain.value,
            "shared": h.shared_features[:10],
            "body_preview": h.pattern.body[:220],
        }
        if h.pattern.kind in {PatternKind.EVENT, PatternKind.EPISODE, PatternKind.TASK} or "experience" in (
            h.pattern.tags or []
        ):
            if include_experiences:
                experiences.append(row)
        else:
            matches.append(row)

    # pull neighbors of top match for faster connect-the-dots
    hops: List[Dict[str, Any]] = []
    if hits:
        via_title = hits[0].pattern.title
        for nb in lat.store.neighbors(hits[0].pattern.id, limit=6):
            hops.append(
                {
                    "id": nb.id,
                    "title": nb.title,
                    "kind": nb.kind.value,
                    "domain": nb.domain.value,
                    "via": via_title,
                }
            )

    distillation = distill(query, matches=hits, domain_hint=domain)
    traj_bits = []
    if hits:
        traj_bits.append(f"strongest prior: **{hits[0].pattern.title}** ({hits[0].score:.2f})")
    if experiences:
        traj_bits.append(f"lived echo: **{experiences[0]['title']}**")
    if hops:
        traj_bits.append("hop: " + ", ".join(h["title"] for h in hops[:3]))

    brief_lines = [
        "## Insight recall",
        f"**Lever:** {distillation.actual_variable}",
        f"**Confidence:** {distillation.confidence:.2f}",
    ]
    if traj_bits:
        brief_lines.append("- " + " · ".join(traj_bits))
    if matches:
        brief_lines.append("### Structural priors")
        for m in matches[:5]:
            brief_lines.append(f"- `{m['score']:.2f}` **{m['title']}** — {m['body_preview'][:120]}")
    if experiences:
        brief_lines.append("### Lived experiences")
        for e in experiences[:4]:
            brief_lines.append(f"- `{e['score']:.2f}` **{e['title']}**")
    if hops:
        brief_lines.append("### Connected hops")
        for h in hops[:5]:
            brief_lines.append(f"- {h['title']} ({h['kind']}/{h['domain']})")
    brief = "\n".join(brief_lines)

    if write_meta:
        top_t = matches[0]["title"] if matches else "none"
        lat.store.set_meta(
            "last_recall_line",
            f"{distillation.actual_variable}: {top_t}",
        )
        lat.store.set_meta(
            "last_brief_line",
            f"lever=`{distillation.actual_variable}` · match=`{top_t}`"
            + (f"@{matches[0]['score']:.2f}" if matches else ""),
        )

    return {
        "success": True,
        "lever": distillation.actual_variable,
        "confidence": distillation.confidence,
        "matches": matches,
        "experiences": experiences,
        "hops": hops,
        "brief": brief,
        "active_task_id": lat.store.get_meta("active_task_id", ""),
    }


def connect(
    lat: "HermesInsight",
    left: str,
    right: Optional[str] = None,
    *,
    kind: str = "similar",
    note: str = "",
    weight: float = 0.6,
) -> Dict[str, Any]:
    """Connect two pattern ids, or auto-connect free text ``left`` into the lattice."""
    left = (left or "").strip()
    right = (right or "").strip() if right else ""

    # If right missing: treat left as blob to auto-link via experience
    if not right:
        return log_experience(
            lat,
            title=left[:80] or "connect",
            body=left,
            kind="event",
            tags=["connect_auto"],
            auto_connect=True,
        )

    # resolve ids or titles
    src = lat.store.get_pattern(left)
    dst = lat.store.get_pattern(right)
    if not src:
        # try search
        found = lat.search(left, limit=1)
        src = found[0] if found else None
    if not dst:
        found = lat.search(right, limit=1)
        dst = found[0] if found else None
    if not src or not dst:
        return {
            "success": False,
            "error": "could not resolve both sides to patterns",
            "left": left,
            "right": right,
        }

    try:
        lk = LinkKind(kind)
    except ValueError:
        lk = LinkKind.SIMILAR

    link = Link(
        id=f"l_{uuid.uuid4().hex[:12]}",
        source_id=src.id,
        target_id=dst.id,
        kind=lk,
        weight=float(weight),
        note=scrub_text(note or "explicit connect"),
    )
    saved = lat.store.upsert_link(link)
    return {
        "success": True,
        "link": saved.to_dict(),
        "source": {"id": src.id, "title": src.title},
        "target": {"id": dst.id, "title": dst.title},
    }


def ingest_messages(
    lat: "HermesInsight",
    messages: Sequence[Dict[str, Any]],
    *,
    task_id: Optional[str] = None,
    title: str = "session slice",
    max_chars: int = 6000,
) -> Dict[str, Any]:
    """Ingest a scrubbed session transcript slice as one episode + connect."""
    parts: List[str] = []
    for m in messages:
        role = str(m.get("role") or m.get("type") or "msg")
        content = m.get("content") or m.get("text") or ""
        if isinstance(content, list):
            # multimodal-ish
            content = " ".join(
                str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content
            )
        content = scrub_text(str(content)).strip()
        if not content:
            continue
        # skip huge tool dumps
        if len(content) > 2000:
            content = content[:2000] + "…"
        parts.append(f"{role}: {content}")
    blob = "\n".join(parts)
    if len(blob) > max_chars:
        blob = blob[: max_chars // 2] + "\n…\n" + blob[-max_chars // 2 :]
    if not blob.strip():
        return {"success": False, "error": "no message content"}
    return log_experience(
        lat,
        title=title[:100],
        body=blob,
        kind="episode",
        task_id=task_id,
        tags=["session", "transcript"],
        confidence=0.55,
        auto_connect=True,
    )
