"""Pattern recognition as a first-class agent ability.

``perceive`` is the one-call API Hermes agents should use mid-task.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

from hermes_insight.features import extract_features
from hermes_insight.scrub import scrub_text

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight


def _action_hint(lever: str, matches: Sequence[Dict[str, Any]], conf: float) -> str:
    if lever in {"insufficient_signal", "unknown", ""}:
        return (
            "Not enough structure yet — add 2–3 concrete observations "
            "(error text, component names, what changed) and perceive again."
        )
    if not matches:
        return (
            f"Lever looks like `{lever}` but the lattice is thin — "
            "catalogue this scene with log=true, then re-perceive."
        )
    top = matches[0]
    title = top.get("title") or "prior"
    preview = (top.get("body_preview") or "").strip().split("\n")[0][:160]
    score = float(top.get("score") or 0)
    if score >= 0.35 and conf >= 0.45:
        return (
            f"Treat as instance of **{title}** (score {score:.2f}). "
            f"Apply that rule first: {preview}"
        )
    if score >= 0.18:
        return (
            f"Possible rhyme with **{title}** ({score:.2f}). "
            f"Verify the lever `{lever}` against: {preview}"
        )
    return (
        f"Weak prior **{title}** ({score:.2f}). "
        f"Hold lever `{lever}` lightly; gather one more observation before committing."
    )


def _collect_hops(lat: "HermesInsight", matches: Sequence[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    hops: List[Dict[str, Any]] = []
    seen = set()
    for m in matches[:4]:
        pid = m.get("id")
        if not pid:
            continue
        for nb in lat.store.neighbors(str(pid), limit=6):
            if nb.id in seen:
                continue
            seen.add(nb.id)
            hops.append(
                {
                    "id": nb.id,
                    "title": nb.title,
                    "kind": nb.kind.value,
                    "domain": nb.domain.value,
                    "via": m.get("title"),
                }
            )
            if len(hops) >= limit:
                return hops
    return hops


def perceive(
    lat: "HermesInsight",
    situation: str,
    *,
    observations: Optional[Sequence[str]] = None,
    domain: Optional[str] = None,
    limit: int = 8,
    log_experience: bool = False,
    experience_title: Optional[str] = None,
    task_id: Optional[str] = None,
    deep: bool = False,
) -> Dict[str, Any]:
    """Run pattern recognition on a live situation."""
    situation = scrub_text(situation or "").strip()
    obs = [scrub_text(o).strip() for o in (observations or []) if o and str(o).strip()]
    blob = situation if not obs else situation + "\n" + "\n".join(obs)

    from hermes_insight.experience import densify_structural_links, seed_agent_starters

    seed_agent_starters(lat)

    feats = extract_features(blob)
    thin_query = len(feats) < 3 and len(blob.split()) < 8

    pack = lat.recall(blob, limit=limit, domain=domain)
    matches: List[Dict[str, Any]] = list(pack.get("matches") or [])
    experiences: List[Dict[str, Any]] = list(pack.get("experiences") or [])
    hops: List[Dict[str, Any]] = list(pack.get("hops") or [])
    lever = str(pack.get("lever") or "")
    conf = float(pack.get("confidence") or 0.0)
    brief = str(pack.get("brief") or "")

    top_score = float(matches[0].get("score") or 0) if matches else 0.0
    deep_used = False

    # Auto-deep when we have substance but weak match
    need_deep = bool(deep) or (
        (not thin_query)
        and top_score < 0.18
        and len(blob) >= 48
    )
    if need_deep:
        report = lat.cycle(
            situation,
            observations=obs,
            domain=domain or "general",
            evolve=False,
            file_novel=True,
            ingest_query=False,
        )
        deep_used = True
        cycle_brief = report.brief or ""
        if report.matches:
            for m in report.matches[:limit]:
                row = {
                    "id": m.pattern.id,
                    "title": m.pattern.title,
                    "score": round(m.score, 4),
                    "method": m.method,
                    "kind": m.pattern.kind.value,
                    "domain": m.pattern.domain.value,
                    "shared": m.shared_features[:10],
                    "body_preview": m.pattern.body[:220],
                }
                if not any(x.get("id") == row["id"] for x in matches):
                    matches.append(row)
            matches.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
            matches = matches[:limit]
            top_score = float(matches[0].get("score") or 0) if matches else top_score
        if report.distillation:
            lever = report.distillation.actual_variable or lever
            conf = max(conf, float(report.distillation.confidence or 0))
        if cycle_brief:
            brief = brief + "\n\n### Deep cycle\n" + cycle_brief[:2500]

    if thin_query and top_score < 0.35:
        lever = "insufficient_signal"
        conf = min(conf, 0.25)
    if thin_query:
        # Do not pretend random high-prior rules are about a vacuous query
        matches = []
        experiences = []
        hops = []
        top_score = 0.0
        lever = "insufficient_signal"
        conf = 0.12
        usable = False
        hint = _action_hint(lever, matches, conf)
        card_lines = [
            "## Pattern recognition",
            f"**Lever:** `{lever}` · **confidence:** {conf:.2f} · **needs more signal**",
            f"**Hint:** {hint}",
            "_Query was thin — concrete observations improve results sharply._",
        ]
        return {
            "success": True,
            "ability": "pattern_recognition",
            "usable": False,
            "lever": lever,
            "confidence": conf,
            "top_score": 0.0,
            "action_hint": hint,
            "matches": [],
            "experiences": [],
            "hops": [],
            "brief": brief,
            "card": "\n".join(card_lines),
            "deep_used": deep_used,
            "thin_query": True,
            "logged_experience": None,
            "active_task_id": lat.store.get_meta("active_task_id", ""),
            "pattern_ids": [],
        }

    if not hops:
        hops = _collect_hops(lat, matches)

    hint = _action_hint(lever, matches, conf)

    logged = None
    if log_experience and situation and lever != "insufficient_signal":
        logged = lat.experience(
            title=(experience_title or situation)[:100],
            body=blob[:4000],
            kind="event",
            task_id=task_id or lat.store.get_meta("active_task_id") or None,
            tags=["perceive", "auto"],
            confidence=max(0.4, conf),
            auto_connect=True,
        )

    usable = bool(matches) and top_score >= 0.18 and lever not in {"insufficient_signal", "unknown", ""}

    card_lines = [
        "## Pattern recognition",
        f"**Lever:** `{lever}` · **confidence:** {conf:.2f}"
        + (" · **usable**" if usable else " · **needs more signal**"),
        f"**Hint:** {hint}",
    ]
    if matches:
        card_lines.append("### Top structures")
        for m in matches[:5]:
            sc = float(m.get("score") or 0)
            card_lines.append(
                f"- `{sc:.2f}` **{m.get('title')}** ({m.get('kind')}/{m.get('domain')})"
            )
    if experiences:
        card_lines.append("### Lived echoes")
        for e in experiences[:3]:
            sc = float(e.get("score") or 0)
            card_lines.append(f"- `{sc:.2f}` **{e.get('title')}**")
    if hops:
        card_lines.append("### Hops")
        card_lines.append(
            "- " + ", ".join(f"{h.get('title')}←{h.get('via', '?')}" for h in hops[:5])
        )
    if deep_used:
        card_lines.append("_Deep cycle was used (thin or novel scene)._")
    if thin_query:
        card_lines.append("_Query was thin — concrete observations improve results sharply._")

    card = "\n".join(card_lines)

    return {
        "success": True,
        "ability": "pattern_recognition",
        "usable": usable,
        "lever": lever,
        "confidence": conf,
        "top_score": top_score,
        "action_hint": hint,
        "matches": matches,
        "experiences": experiences,
        "hops": hops,
        "brief": brief,
        "card": card,
        "deep_used": deep_used,
        "thin_query": thin_query,
        "logged_experience": logged,
        "active_task_id": lat.store.get_meta("active_task_id", ""),
        "pattern_ids": [m.get("id") for m in matches if m.get("id")],
    }
