"""Evidence-gated workflow induction from independent Hermes task traces.

Lexical matching recognizes resemblance.  Induction recognizes recurrence:
the same ordered operation sequence appearing across distinct tasks, with
outcomes and counterexamples preserved.  Nothing here writes a Hermes skill or
grants execution authority; materialization creates reviewable ``sequence``
patterns inside the local Insight lattice.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from hermes_insight.features import extract_features
from hermes_insight.models import (
    Domain,
    Link,
    LinkKind,
    Pattern,
    PatternKind,
    content_hash,
)
from hermes_insight.observation import EVENT_SCHEMA

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight


_SUCCESS = {"done", "success", "fixed", "shipped", "resolved", "passed"}
_FAILURE = {"failed", "failure", "blocked", "wrong", "interrupted", "regressed"}


def _outcome_class(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _SUCCESS:
        return "success"
    if normalized in _FAILURE:
        return "failure"
    return "neutral"


def _wilson_lower(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    z2 = z * z
    numerator = p + z2 / (2 * total) - z * math.sqrt(
        (p * (1 - p) + z2 / (4 * total)) / total
    )
    denominator = 1 + z2 / total
    return max(0.0, numerator / denominator)


def _event_step(pattern: Pattern) -> str:
    metadata = pattern.metadata or {}
    event_type = str(metadata.get("event_type") or "observation").strip().lower()
    skill = str(metadata.get("skill_id") or "").strip().lower()
    tool = str(metadata.get("tool") or "").strip().lower()
    if skill:
        return f"skill:{skill}:{event_type}"
    if tool:
        return f"tool:{tool}:{event_type}"
    return f"event:{event_type}"


def _task_traces(
    lat: "HermesInsight",
    *,
    max_events: int = 10000,
) -> Tuple[
    Dict[str, List[Pattern]],
    Dict[str, str],
    Dict[str, str],
]:
    events: Dict[str, List[Pattern]] = defaultdict(list)
    outcomes: Dict[str, Tuple[float, str]] = {}
    environments: Dict[str, str] = {}
    for pattern in lat.store.all_patterns(limit=max_events):
        metadata = pattern.metadata or {}
        task_id = str(metadata.get("task_id") or "").strip()
        if not task_id:
            continue
        outcome = _outcome_class(metadata.get("outcome"))
        if outcome != "neutral":
            at = float(pattern.updated_at or pattern.created_at or 0.0)
            if task_id not in outcomes or at >= outcomes[task_id][0]:
                outcomes[task_id] = (at, outcome)
        if metadata.get("schema") != EVENT_SCHEMA:
            continue
        events[task_id].append(pattern)
        environment_id = str(metadata.get("environment_snapshot_id") or "").strip()
        if environment_id:
            environments[task_id] = environment_id

    for rows in events.values():
        rows.sort(
            key=lambda pattern: (
                float((pattern.metadata or {}).get("started_at") or pattern.created_at),
                pattern.created_at,
                pattern.id,
            )
        )
    return events, {task: row[1] for task, row in outcomes.items()}, environments


def _lifecycle(support: int, labeled: int, failures: int, lower_bound: float) -> str:
    if support >= 5 and labeled >= 5 and failures <= 1 and lower_bound >= 0.55:
        return "verified_local"
    if support >= 3:
        return "candidate"
    return "observed"


def _display_step(step: str) -> str:
    parts = step.split(":", 2)
    if len(parts) == 3:
        return f"{parts[0]} `{parts[1]}` → {parts[2]}"
    return step


def _existing_workflow(lat: "HermesInsight", signature: str) -> Optional[Pattern]:
    for pattern in lat.store.list_patterns(kind=PatternKind.SEQUENCE.value, limit=1000):
        if str((pattern.metadata or {}).get("workflow_signature") or "") == signature:
            return pattern
    return None


def _materialize(
    lat: "HermesInsight",
    candidate: Dict[str, Any],
) -> Pattern:
    steps = list(candidate["steps"])
    title_steps = " → ".join(
        step.split(":", 2)[1] if step.count(":") >= 2 else step
        for step in steps
    )
    title = f"workflow: {title_steps}"[:120]
    evidence = candidate["evidence"]
    body_lines = [
        "Induced recurring workflow (review before operational use).",
        f"Lifecycle: {candidate['lifecycle']}",
        f"Distinct task support: {evidence['distinct_tasks']}",
        (
            f"Outcomes: {evidence['successes']} success / "
            f"{evidence['failures']} failure / {evidence['neutral']} neutral"
        ),
        f"Wilson success lower bound: {evidence['success_lower_bound']:.3f}",
        "",
        "Ordered steps:",
        *[f"{index}. {_display_step(step)}" for index, step in enumerate(steps, 1)],
    ]
    if evidence["counterexample_task_ids"]:
        body_lines.extend(
            [
                "",
                "Counterexamples retained:",
                *[
                    f"- task `{task_id}`"
                    for task_id in evidence["counterexample_task_ids"][:10]
                ],
            ]
        )
    body = "\n".join(body_lines)
    metadata = {
        "induced": True,
        "workflow_signature": candidate["signature"],
        "lifecycle": candidate["lifecycle"],
        "steps": steps,
        "evidence": evidence,
        "score": candidate["score"],
        "updated_from_evidence_at": time.time(),
    }
    features = list(dict.fromkeys(extract_features(body, max_features=48) + steps))
    tags = ["induced", "workflow", candidate["lifecycle"]]
    if lat.agent_id:
        metadata["agent_id"] = lat.agent_id
        tags.insert(0, lat.agent_id)
    confidence = max(
        0.35,
        min(
            0.95,
            float(evidence["posterior_success"])
            * float(evidence["evidence_confidence"]),
        ),
    )

    pattern = _existing_workflow(lat, candidate["signature"])
    if pattern:
        pattern.title = title
        pattern.body = body
        pattern.features = features
        pattern.tags = tags
        pattern.confidence = confidence
        pattern.metadata = metadata
        pattern.updated_at = time.time()
        pattern.content_hash = content_hash(
            f"{pattern.title}\n{pattern.body}\n{'|'.join(pattern.features)}"
        )
        lat.store.upsert_pattern(pattern)
    else:
        pattern = lat.ingest(
            title,
            body,
            kind=PatternKind.SEQUENCE,
            domain=Domain.PROCESS,
            features=features,
            tags=tags,
            confidence=confidence,
            source="native-workflow-induction",
            metadata=metadata,
            link=False,
        )

    for event_id in candidate["evidence_event_ids"][:40]:
        if not lat.store.get_pattern(event_id):
            continue
        lat.store.upsert_link(
            Link.create(
                event_id,
                pattern.id,
                LinkKind.INSTANCE_OF,
                weight=max(0.4, float(candidate["score"])),
                note="event supports induced workflow",
                metadata={"workflow_signature": candidate["signature"]},
            )
        )
    return pattern


def induce_workflows(
    lat: "HermesInsight",
    *,
    min_support: int = 3,
    min_steps: int = 2,
    max_steps: int = 4,
    limit: int = 12,
    materialize: bool = False,
) -> Dict[str, Any]:
    """Mine recurring ordered event sequences across distinct task ids."""
    min_support = max(2, int(min_support))
    min_steps = max(2, int(min_steps))
    max_steps = max(min_steps, min(8, int(max_steps)))
    events, outcomes, environments = _task_traces(lat)

    occurrences: Dict[Tuple[str, ...], Dict[str, List[str]]] = defaultdict(dict)
    for task_id, rows in events.items():
        steps: List[str] = []
        event_ids: List[str] = []
        for pattern in rows:
            step = _event_step(pattern)
            # Compress exact duplicate emissions without erasing started/completed pairs.
            if steps and steps[-1] == step:
                continue
            steps.append(step)
            event_ids.append(pattern.id)
        if len(steps) < min_steps:
            continue
        for width in range(min_steps, min(max_steps, len(steps)) + 1):
            for start in range(0, len(steps) - width + 1):
                signature = tuple(steps[start : start + width])
                occurrences[signature].setdefault(
                    task_id,
                    event_ids[start : start + width],
                )

    candidates: List[Dict[str, Any]] = []
    for steps, task_rows in occurrences.items():
        task_ids = sorted(task_rows)
        support = len(task_ids)
        if support < min_support:
            continue
        successes = [task for task in task_ids if outcomes.get(task) == "success"]
        failures = [task for task in task_ids if outcomes.get(task) == "failure"]
        neutral = support - len(successes) - len(failures)
        labeled = len(successes) + len(failures)
        posterior = (len(successes) + 1.0) / (labeled + 2.0)
        evidence_confidence = labeled / (labeled + 3.0)
        lower_bound = _wilson_lower(len(successes), labeled)
        lifecycle = _lifecycle(support, labeled, len(failures), lower_bound)
        score = min(
            1.0,
            0.35 * min(1.0, support / 10.0)
            + 0.30 * posterior
            + 0.25 * lower_bound
            + 0.10 * min(1.0, len(steps) / 4.0),
        )
        signature_text = "\n".join(steps)
        signature_id = hashlib.sha256(signature_text.encode("utf-8")).hexdigest()[:16]
        evidence_event_ids = list(
            dict.fromkeys(
                event_id
                for task_id in task_ids
                for event_id in task_rows[task_id]
            )
        )
        candidates.append(
            {
                "signature": signature_id,
                "steps": list(steps),
                "support": support,
                "score": round(score, 4),
                "lifecycle": lifecycle,
                "evidence": {
                    "distinct_tasks": support,
                    "distinct_environments": len(
                        {
                            environments[task]
                            for task in task_ids
                            if task in environments
                        }
                    ),
                    "successes": len(successes),
                    "failures": len(failures),
                    "neutral": neutral,
                    "posterior_success": round(posterior, 4),
                    "evidence_confidence": round(evidence_confidence, 4),
                    "success_lower_bound": round(lower_bound, 4),
                    "task_ids": task_ids[:30],
                    "counterexample_task_ids": failures[:30],
                },
                "evidence_event_ids": evidence_event_ids,
            }
        )

    candidates.sort(
        key=lambda row: (
            {"verified_local": 2, "candidate": 1, "observed": 0}[row["lifecycle"]],
            row["score"],
            row["support"],
            len(row["steps"]),
        ),
        reverse=True,
    )
    candidates = candidates[: max(1, min(int(limit), 50))]
    materialized: List[Dict[str, Any]] = []
    if materialize:
        for candidate in candidates:
            pattern = _materialize(lat, candidate)
            materialized.append(
                {
                    "pattern_id": pattern.id,
                    "signature": candidate["signature"],
                    "title": pattern.title,
                    "lifecycle": candidate["lifecycle"],
                }
            )

    # Keep evidence event ids internal to the materializer; callers get compact provenance.
    public_candidates = []
    for candidate in candidates:
        row = dict(candidate)
        row.pop("evidence_event_ids", None)
        public_candidates.append(row)
    return {
        "success": True,
        "ability": "workflow_induction",
        "task_traces": len(events),
        "min_support": min_support,
        "candidates": public_candidates,
        "materialized": materialized,
        "safety": {
            "automatic_skill_write": False,
            "automatic_execution": False,
            "support_unit": "distinct task_id",
            "counterexamples_retained": True,
            "verified_local_gate": (
                ">=5 distinct tasks, >=5 labeled outcomes, <=1 failure, "
                "95% Wilson lower bound >=0.55"
            ),
        },
    }
