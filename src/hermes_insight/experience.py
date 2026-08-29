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
from hermes_insight.features import extract_features
from hermes_insight.match import build_idf, expand_query_features, match_patterns
from hermes_insight.models import (
    Domain,
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
    {
        "title": "mesh ghost peer after reboot",
        "body": (
            "After a host reboot, mesh/VPN peers can look alive in the ledger while "
            "the control plane lost the node — or ESTAB sockets remain to stale IPs. "
            "Reconcile: peer online flag, last handshake age, route table, and real "
            "ping/SSH before treating the ghost as a live hop."
        ),
        "kind": "rule",
        "domain": "system",
        "tags": ["mesh", "network", "peer", "reboot", "vpn", "stale"],
        "features": ["mesh", "peer", "reboot", "handshake", "stale", "route", "ghost"],
    },
    {
        "title": "split DNS vs mesh path",
        "body": (
            "Name resolves on one plane (public DNS) while traffic expects another "
            "(mesh/private). Symptom: works on laptop, fails on server, or intermittent "
            "timeouts. Fix the resolution plane first, then the route."
        ),
        "kind": "rule",
        "domain": "system",
        "tags": ["dns", "mesh", "network", "split-horizon"],
        "features": ["dns", "resolve", "mesh", "route", "timeout", "split"],
    },
    {
        "title": "single writer for shared state",
        "body": (
            "SQLite DBs, lock files, and long-poll credentials need one writer/consumer. "
            "Two agents on one DB path or one bot token thrash each other. Compartment "
            "paths and exclusive locks before scaling seats."
        ),
        "kind": "rule",
        "domain": "multi_agent",
        "tags": ["lock", "sqlite", "credential", "compartment"],
        "features": ["lock", "writer", "sqlite", "credential", "compartment", "exclusive"],
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
    import time as _time

    have_titles = {p.title for p in existing_starters}
    # Any kind — starters include prototypes (e.g. delivery gap)
    for p in lat.store.list_patterns(limit=200):
        if "starter" in (p.tags or []) or "bootstrap" in (p.tags or []):
            have_titles.add(p.title)
        if p.title in {r["title"] for r in AGENT_STARTER_PATTERNS}:
            have_titles.add(p.title)
    missing = [row for row in AGENT_STARTER_PATTERNS if row["title"] not in have_titles]

    if not force and not missing and len(existing_starters) >= 6:
        last = float(lat.store.get_meta("last_densify_at", "0") or 0)
        now = _time.time()
        rules = lat.store.list_patterns(kind="rule", limit=20)
        orphan_rules = sum(1 for r in rules if not lat.store.links_for(r.id, limit=1))
        dens: Dict[str, Any] = {}
        if (orphan_rules >= 3 or last <= 0) and (now - last > 21600):
            dens = densify_structural_links(lat, min_score=0.12, limit_per=6)
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
    rows = AGENT_STARTER_PATTERNS if force else missing
    if force:
        rows = AGENT_STARTER_PATTERNS
    for row in rows:
        pat = lat.ingest(
            row["title"],
            row["body"],
            kind=row.get("kind", "rule"),
            domain=row.get("domain", "agent"),
            tags=list(row.get("tags") or []) + ["starter", "bootstrap"],
            features=row.get("features"),
            confidence=0.75,
            source="bootstrap",
            link=False,
        )
        ids.append(pat.id)
    dens = densify_structural_links(lat, min_score=0.10, limit_per=12)
    lat.store.set_meta("bootstrap_version", "0.9.0")
    lat.store.set_meta("last_densify_at", str(_time.time()))
    return {
        "seeded": len(ids),
        "pattern_ids": ids,
        "skipped": False,
        "missing_filled": len(missing) if not force else len(AGENT_STARTER_PATTERNS),
        **dens,
    }


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
    meta_key = f"task_chain_last:{tag.removeprefix('task:')}"
    previous_id = store.get_meta(meta_key, "")
    prev = store.get_pattern(previous_id) if previous_id else None
    if not prev or prev.id == pat.id or tag not in (prev.tags or []):
        # Backward-compatible recovery for tasks created before the chain cursor existed.
        recent = [
            p
            for p in store.list_patterns(domain=Domain.EXPERIENCE.value, limit=80)
            if tag in (p.tags or []) and p.id != pat.id and p.kind in {
                PatternKind.EVENT, PatternKind.EPISODE, PatternKind.TASK, PatternKind.SEQUENCE
            }
        ]
        prev = (
            max(recent, key=lambda p: (p.created_at, p.updated_at, p.id))
            if recent
            else None
        )
    if not prev:
        store.set_meta(meta_key, pat.id)
        return
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
    store.set_meta(meta_key, pat.id)


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
    used_pattern_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Close a task and attribute outcomes to patterns explicitly applied."""
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
    applied: List[str] = []
    close_row = res.get("experience") or {}
    close_id = str(close_row.get("id") or "")
    if used_pattern_ids is not None and close_id:
        close_pattern = lat.store.get_pattern(close_id)
        for pattern_id in dict.fromkeys(str(x) for x in used_pattern_ids if str(x).strip()):
            pattern = lat.store.get_pattern(pattern_id)
            if not pattern or pattern.kind in {
                PatternKind.EVENT,
                PatternKind.EPISODE,
                PatternKind.TASK,
            }:
                continue
            lat.store.upsert_link(
                Link.create(
                    close_id,
                    pattern.id,
                    LinkKind.APPLIED,
                    weight=0.9,
                    note=f"explicitly applied in task {task_id}",
                    metadata={"task_id": task_id, "outcome": outcome},
                )
            )
            applied.append(pattern.id)
        if close_pattern:
            close_pattern.metadata["used_pattern_ids"] = applied
            lat.store.upsert_pattern(close_pattern)

    reinforced: List[str] = []
    # Similarity links are evidence of resemblance, not proof that a pattern was
    # applied. Outcome credit is therefore explicit-only.
    credited_ids = applied
    if reinforce_connected and outcome.lower() in {"done", "success", "fixed", "shipped", "resolved"}:
        if credited_ids:
            from hermes_insight.evolve import reinforce

            updated = reinforce(lat.store, credited_ids, helpful=True)
            reinforced = [p.id for p in updated]
    elif reinforce_connected and outcome.lower() in {"failed", "blocked", "wrong"}:
        if credited_ids:
            from hermes_insight.evolve import reinforce

            reinforce(lat.store, credited_ids[:3], helpful=False)

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
        "applied_patterns": applied,
        "credit_mode": "explicit" if used_pattern_ids is not None else "none",
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
    observations: Optional[Sequence[str]] = None,
    environment_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Associative pre-action recall — delegates to the recall engine."""
    from hermes_insight.recall import recall as _recall

    return _recall(
        lat,
        query,
        limit=limit,
        include_experiences=include_experiences,
        write_meta=write_meta,
        domain=domain,
        observations=observations,
        environment_id=environment_id,
        task_id=task_id,
    )


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
