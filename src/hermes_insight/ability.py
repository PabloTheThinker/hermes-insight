"""Pattern recognition as a first-class agent ability.

``perceive`` is the one-call API Hermes agents should use mid-task:

    observations → features → match (structural priors) → distill lever
    → hops → action hint → optional experience log

This is the product surface for \"make pattern recognition a real ability\" —
not a warehouse of tools the model might forget.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

from hermes_insight.scrub import scrub_text

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight


def _action_hint(lever: str, matches: Sequence[Dict[str, Any]], brief: str) -> str:
    """Short next-move suggestion from top structural prior."""
    if not matches:
        return (
            f"Lever looks like `{lever or 'unknown'}` but the lattice is thin — "
            "catalogue this scene with insight_experience, then re-perceive."
        )
    top = matches[0]
    title = top.get("title") or "prior"
    preview = (top.get("body_preview") or "").strip().split("\n")[0][:160]
    score = float(top.get("score") or 0)
    if score >= 0.35:
        return (
            f"Treat as instance of **{title}** (score {score:.2f}). "
            f"Apply that rule first: {preview}"
        )
    if score >= 0.15:
        return (
            f"Possible rhyme with **{title}** ({score:.2f}). "
            f"Verify the lever `{lever}` against: {preview}"
        )
    return (
        f"Weak prior **{title}** ({score:.2f}). "
        f"Hold lever `{lever}` lightly; gather one more observation before committing."
    )


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
    """Run pattern recognition on a live situation.

    Parameters
    ----------
    situation:
        What the agent is looking at / about to do.
    observations:
        Extra factual lines (errors, metrics, user quotes).
    log_experience:
        If True, also catalogue this as an experience event (connects for next time).
    deep:
        If True, run a full cognitive cycle when top match is weak.
    """
    situation = scrub_text(situation or "").strip()
    obs = [scrub_text(o).strip() for o in (observations or []) if o and str(o).strip()]
    blob = situation if not obs else situation + "\n" + "\n".join(obs)

    from hermes_insight.experience import seed_agent_starters

    seed_agent_starters(lat)

    pack = lat.recall(blob, limit=limit, domain=domain)
    matches: List[Dict[str, Any]] = list(pack.get("matches") or [])
    experiences: List[Dict[str, Any]] = list(pack.get("experiences") or [])
    hops: List[Dict[str, Any]] = list(pack.get("hops") or [])
    lever = str(pack.get("lever") or "")
    conf = float(pack.get("confidence") or 0.0)
    brief = str(pack.get("brief") or "")

    deep_used = False
    top_score = float(matches[0].get("score") or 0) if matches else 0.0
    if deep or (not matches and conf < 0.45) or top_score < 0.12:
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
        if report.distillation:
            lever = report.distillation.actual_variable or lever
            conf = max(conf, float(report.distillation.confidence or 0))
        if cycle_brief:
            brief = brief + "\n\n### Deep cycle\n" + cycle_brief[:2500]

    hint = _action_hint(lever, matches, brief)

    logged = None
    if log_experience and situation:
        logged = lat.experience(
            title=(experience_title or situation)[:100],
            body=blob[:4000],
            kind="event",
            task_id=task_id or lat.store.get_meta("active_task_id") or None,
            tags=["perceive", "auto"],
            confidence=max(0.4, conf),
            auto_connect=True,
        )

    card_lines = [
        "## Pattern recognition",
        f"**Lever:** `{lever}` · **confidence:** {conf:.2f}",
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
        card_lines.append("- " + ", ".join(h.get("title", "?") for h in hops[:5]))
    if deep_used:
        card_lines.append("_Deep cycle was used (thin or novel scene)._")

    card = "\n".join(card_lines)

    return {
        "success": True,
        "ability": "pattern_recognition",
        "lever": lever,
        "confidence": conf,
        "action_hint": hint,
        "matches": matches,
        "experiences": experiences,
        "hops": hops,
        "brief": brief,
        "card": card,
        "deep_used": deep_used,
        "logged_experience": logged,
        "active_task_id": lat.store.get_meta("active_task_id", ""),
        "pattern_ids": [m.get("id") for m in matches if m.get("id")],
    }
