"""Experience-grounded planning for Hermes Insight.

This module turns recognition into a small, auditable decision policy:

* relevance comes from the existing hybrid matcher;
* reliability comes only from patterns explicitly marked as applied to tasks;
* environment affordances expose matching local skills, tools, models, and agents;
* every score includes its components so "intuition" never becomes hidden authority.

The planner does not execute tools or mutate skills.  It recommends a route and
leaves outcome attribution to ``close_task(..., used_pattern_ids=[...])``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

from hermes_insight.features import extract_features
from hermes_insight.match import build_idf, expand_query_features, match_patterns
from hermes_insight.mindset import MindsetArg, apply_to_recall, is_thin_query, resolve_plate
from hermes_insight.models import LinkKind, Pattern, PatternKind
from hermes_insight.scrub import scrub_text

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight


_SUCCESS_OUTCOMES = {"done", "success", "fixed", "shipped", "resolved", "passed"}
_FAILURE_OUTCOMES = {"failed", "failure", "blocked", "wrong", "interrupted", "regressed"}
_RECOMMENDABLE_KINDS = {
    PatternKind.RULE,
    PatternKind.SKILL,
    PatternKind.SEQUENCE,
    PatternKind.SYNTHESIS,
    PatternKind.PROTOTYPE,
}
_AFFORDANCE_KINDS = {
    PatternKind.AGENT,
    PatternKind.MODEL,
    PatternKind.TOOL,
    PatternKind.SKILL,
}


def _outcome_class(pattern: Pattern) -> str:
    raw = str((pattern.metadata or {}).get("outcome") or "").strip().lower()
    if not raw:
        for tag in pattern.tags or []:
            tag_s = str(tag).lower()
            if tag_s.startswith("outcome:"):
                raw = tag_s.split(":", 1)[1]
                break
    if raw in _SUCCESS_OUTCOMES:
        return "success"
    if raw in _FAILURE_OUTCOMES:
        return "failure"
    return "neutral"


def _outcome_evidence(lat: "HermesInsight", pattern: Pattern) -> Dict[str, Any]:
    """Summarize direct application evidence, excluding mere similarity links."""
    successes = 0
    failures = 0
    samples: List[Dict[str, str]] = []
    seen: set[str] = set()
    for link in lat.store.links_for(pattern.id, limit=200):
        if link.kind != LinkKind.APPLIED:
            continue
        other_id = link.target_id if link.source_id == pattern.id else link.source_id
        if other_id in seen:
            continue
        seen.add(other_id)
        event = lat.store.get_pattern(other_id)
        if not event:
            continue
        outcome = _outcome_class(event)
        if outcome == "success":
            successes += 1
        elif outcome == "failure":
            failures += 1
        else:
            continue
        if len(samples) < 4:
            samples.append(
                {
                    "outcome": outcome,
                    "title": event.title[:100],
                    "task_id": str((event.metadata or {}).get("task_id") or ""),
                }
            )

    total = successes + failures
    # Beta(1,1) posterior: neutral for no evidence, conservative for small samples.
    posterior = (successes + 1.0) / (total + 2.0)
    evidence_confidence = total / (total + 3.0)
    reliability = 0.5 + (posterior - 0.5) * evidence_confidence
    return {
        "successes": successes,
        "failures": failures,
        "total": total,
        "posterior_success": round(posterior, 4),
        "evidence_confidence": round(evidence_confidence, 4),
        "reliability": round(max(0.0, min(1.0, reliability)), 4),
        "samples": samples,
    }


def _action_for(pattern: Pattern) -> str:
    body = " ".join(pattern.body.strip().split())
    action = body[:280] + ("…" if len(body) > 280 else "")
    lifecycle = str((pattern.metadata or {}).get("lifecycle") or "")
    if (pattern.metadata or {}).get("induced") and lifecycle != "verified_local":
        return (
            f"Review-only `{lifecycle or 'observed'}` workflow candidate. "
            "Check applicability and counterexamples before use. "
            + action
        ).strip()
    if lifecycle == "verified_local":
        return (
            "Locally verified workflow; confirm the current environment still matches. "
            + action
        ).strip()
    if pattern.kind == PatternKind.SKILL:
        name = str((pattern.metadata or {}).get("skill_name") or pattern.title.removeprefix("skill:"))
        return f"Load skill `{name}` and follow its playbook. {action}".strip()
    return action or f"Inspect and apply `{pattern.title}`."


def _affordance(pattern: Pattern, score: float) -> Dict[str, Any]:
    meta = pattern.metadata or {}
    invoke = ""
    if pattern.kind == PatternKind.SKILL:
        name = str(meta.get("skill_name") or pattern.title.removeprefix("skill:"))
        invoke = f"Load Hermes skill `{name}`."
    elif pattern.kind == PatternKind.TOOL:
        name = str(meta.get("tool_name") or pattern.title.removeprefix("tool:"))
        invoke = f"Use tool `{name}` if its current schema fits the task."
    elif pattern.kind == PatternKind.MODEL:
        invoke = "Consider this model route only if policy and cost constraints allow it."
    elif pattern.kind == PatternKind.AGENT:
        invoke = "Delegate only if this agent's compartment and capability match."
    return {
        "id": pattern.id,
        "title": pattern.title,
        "kind": pattern.kind.value,
        "score": round(score, 4),
        "invoke_hint": invoke,
    }


def plan_task(
    lat: "HermesInsight",
    situation: str,
    *,
    observations: Optional[Sequence[str]] = None,
    domain: Optional[str] = None,
    limit: int = 5,
    mindset: MindsetArg = None,
) -> Dict[str, Any]:
    """Build a ranked, experience-grounded plan without executing it."""
    situation = scrub_text(situation or "").strip()
    obs = [scrub_text(str(x)).strip() for x in (observations or []) if str(x).strip()]
    blob = "\n".join([situation, *obs]).strip()
    plate = resolve_plate(lat, mindset)
    knobs = apply_to_recall(plate)
    if not blob:
        return {
            "success": False,
            "error": "situation required",
            "usable": False,
            "recommendations": [],
            "mindset": plate.to_dict(),
        }

    from hermes_insight.experience import seed_agent_starters

    seed_agent_starters(lat)
    features = expand_query_features(extract_features(blob))
    thin_query = is_thin_query(blob, knobs, features)
    recall_pack = lat.recall(
        blob,
        limit=max(10, limit * 2),
        include_experiences=True,
        domain=domain,
        write_meta=False,
        mindset=mindset,
    )

    pool = lat.store.candidate_pool(
        blob,
        domain=domain,
        fts_limit=56,
        structural_limit=180,
        fill_limit=80,
    )
    hits = match_patterns(
        blob,
        features,
        pool,
        limit=max(30, limit * 5),
        min_score=0.04,
        domain_hint=domain,
        idf=build_idf(pool),
    )

    recommendations: List[Dict[str, Any]] = []
    affordances: List[Dict[str, Any]] = []
    seen_affordances: set[str] = set()
    for hit in hits:
        pattern = hit.pattern
        if pattern.kind in _AFFORDANCE_KINDS and pattern.id not in seen_affordances:
            affordances.append(_affordance(pattern, hit.score))
            seen_affordances.add(pattern.id)

        if pattern.kind not in _RECOMMENDABLE_KINDS:
            continue
        # Bare fabric files are inventory, not a workflow recommendation.
        if (pattern.metadata or {}).get("fabric") == "file":
            continue

        evidence = _outcome_evidence(lat, pattern)
        relevance = float(hit.score)
        reliability = float(evidence["reliability"])
        score = (
            0.68 * relevance
            + 0.17 * reliability
            + 0.10 * float(pattern.strength)
            + 0.05 * float(pattern.confidence)
        )
        structural_bonus = {
            PatternKind.RULE: 0.05,
            PatternKind.SKILL: 0.04,
            PatternKind.SEQUENCE: 0.03,
            PatternKind.SYNTHESIS: 0.02,
        }.get(pattern.kind, 0.0)
        score = min(1.0, score + structural_bonus)
        lifecycle = str((pattern.metadata or {}).get("lifecycle") or "")
        if lifecycle == "verified_local":
            score = min(1.0, score + 0.05)
        elif lifecycle == "candidate":
            score *= 0.90
        elif (pattern.metadata or {}).get("induced"):
            score *= 0.80
        if pattern.kind == PatternKind.RULE:
            score *= knobs.rule_weight
        elif pattern.kind == PatternKind.SEQUENCE:
            score *= knobs.sequence_weight
        score = min(1.0, score)
        recommendations.append(
            {
                "pattern_id": pattern.id,
                "title": pattern.title,
                "kind": pattern.kind.value,
                "domain": pattern.domain.value,
                "score": round(score, 4),
                "relevance": round(relevance, 4),
                "reliability": round(reliability, 4),
                "strength": round(float(pattern.strength), 4),
                "confidence": round(float(pattern.confidence), 4),
                "lifecycle": lifecycle or None,
                "actionable": not (pattern.metadata or {}).get("induced")
                or lifecycle == "verified_local",
                "shared_features": hit.shared_features[:12],
                "action": _action_for(pattern),
                "outcome_evidence": evidence,
                "why": (
                    f"relevance={relevance:.2f}; "
                    f"applied outcomes={evidence['successes']} success/"
                    f"{evidence['failures']} failure; kind={pattern.kind.value}"
                    + (f"; lifecycle={lifecycle}" if lifecycle else "")
                ),
            }
        )

    recommendations.sort(
        key=lambda row: (
            float(row["score"]),
            int(row["outcome_evidence"]["total"]),
            float(row["relevance"]),
        ),
        reverse=True,
    )
    recommendations = recommendations[: max(1, min(limit, 12))]
    affordances.sort(key=lambda row: float(row["score"]), reverse=True)
    affordances = affordances[:8]

    lever = str(recall_pack.get("lever") or "")
    confidence = float(recall_pack.get("confidence") or 0.0)
    top_relevance = float(recommendations[0]["relevance"]) if recommendations else 0.0
    usable = bool(
        recommendations
        and top_relevance >= 0.18
        and not thin_query
        and lever not in {"", "unknown", "insufficient_signal"}
    )
    if thin_query:
        lever = "insufficient_signal"
        confidence = min(confidence, 0.2)

    primary = recommendations[0] if recommendations else None
    workflow: List[Dict[str, str]] = [
        {
            "step": "orient",
            "action": (
                f"Verify `{lever}` with one observable measurement before intervention."
                if lever != "insufficient_signal"
                else "Gather concrete component names, errors, and what changed."
            ),
        }
    ]
    if primary:
        workflow.extend(
            [
                {
                    "step": "route",
                    "action": f"Use `{primary['title']}` as the primary pattern; keep lower-ranked items as alternatives.",
                },
                {"step": "execute", "action": str(primary["action"])},
                {
                    "step": "verify",
                    "action": "Define the expected observable result and a stop/rollback condition before changing state.",
                },
                {
                    "step": "learn",
                    "action": (
                        "Close the task with its real outcome and pass "
                        f"`used_pattern_ids=['{primary['pattern_id']}']` only if it was actually applied."
                    ),
                },
            ]
        )

    environment_state: Optional[Dict[str, Any]] = None
    environment_id = lat.store.get_meta("last_environment_snapshot_id", "")
    if environment_id:
        environment_pattern = lat.store.get_pattern(environment_id)
        if environment_pattern:
            metadata = environment_pattern.metadata or {}
            state = dict(metadata.get("snapshot") or {})
            git_state = dict(state.get("git") or {})
            environment_state = {
                "snapshot_id": environment_pattern.id,
                "fingerprint": str(metadata.get("fingerprint") or ""),
                "root_name": str(state.get("root_name") or ""),
                "branch": str(git_state.get("branch") or ""),
                "revision": str(git_state.get("revision") or "")[:12],
                "dirty_count": int(git_state.get("dirty_count") or 0),
                "manifests": list(state.get("manifests") or []),
                "delta": dict(metadata.get("delta") or {}),
            }

    card_lines = [
        "## Experience-grounded plan",
        f"**Lever:** `{lever}` · **confidence:** {confidence:.2f}"
        + (" · **usable**" if usable else " · **needs more signal**"),
    ]
    if environment_state:
        branch = environment_state["branch"] or "no-git"
        revision = environment_state["revision"] or "unversioned"
        card_lines.append(
            f"**Environment:** `{environment_state['root_name']}` · "
            f"`{branch}@{revision}` · dirty={environment_state['dirty_count']}"
        )
    if primary:
        ev = primary["outcome_evidence"]
        card_lines.append(
            f"**Primary:** **{primary['title']}** · plan score {primary['score']:.2f} "
            f"· explicit outcomes {ev['successes']}✓/{ev['failures']}✗"
        )
    for index, step in enumerate(workflow, 1):
        card_lines.append(f"{index}. **{step['step']}** — {step['action']}")
    if len(recommendations) > 1:
        card_lines.append(
            "**Alternatives:** " + ", ".join(r["title"] for r in recommendations[1:3])
        )
    if not usable:
        card_lines.append("_Do not execute this as a confident plan until the missing signal is gathered._")

    return {
        "success": True,
        "ability": "experience_grounded_planning",
        "usable": usable,
        "situation": situation,
        "observations": obs,
        "lever": lever,
        "confidence": round(confidence, 4),
        "recommendations": recommendations,
        "environment_affordances": affordances,
        "environment_state": environment_state,
        "lived_echoes": list(recall_pack.get("experiences") or [])[:5],
        "workflow": workflow,
        "card": "\n".join(card_lines),
        "thin_query": thin_query,
        "mindset": plate.to_dict(),
        "scoring": {
            "formula": "0.68 relevance + 0.17 reliability + 0.10 strength + 0.05 confidence + structural bonus",
            "reliability": "Beta(1,1) posterior, shrunk by explicit applied-outcome sample size",
            "credit_rule": "Only task-close used_pattern_ids create applied outcome evidence",
        },
    }
