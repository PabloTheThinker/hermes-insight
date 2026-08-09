"""Trajectory extrapolation — see where a pattern is heading.

ND-style prediction: connect events into a directed sequence before
the surrounding system names the trend.
"""

from __future__ import annotations

from typing import List, Sequence

from hermes_insight.features import extract_features, tokenize
from hermes_insight.models import MatchResult, Pattern, Trajectory


def extrapolate(
    observations: Sequence[str],
    *,
    matches: Sequence[MatchResult] | None = None,
    title: str | None = None,
) -> Trajectory:
    steps = [s.strip() for s in observations if s and str(s).strip()]
    if not steps:
        steps = ["(no observations)"]

    # Pull directional cues from language
    direction = _infer_direction(steps, matches or [])
    next_expected = _next_expected(steps, direction, matches or [])
    risks = _risks(direction, steps)
    confidence = _traj_confidence(steps, matches or [])
    based_on = [m.pattern.id for m in (matches or [])[:8]]

    ttitle = title or _title_from_steps(steps, direction)
    return Trajectory.create(
        title=ttitle,
        steps=steps,
        direction=direction,
        confidence=confidence,
        based_on=based_on,
        next_expected=next_expected,
        risks=risks,
    )


def _title_from_steps(steps: Sequence[str], direction: str) -> str:
    head = steps[0][:48] if steps else "trajectory"
    return f"{direction}: {head}"


def _infer_direction(steps: Sequence[str], matches: Sequence[MatchResult]) -> str:
    blob = " ".join(steps).lower()
    feats = extract_features(blob, max_features=20)
    feat_set = set(feats)

    scores = {
        "escalating": 0.0,
        "stabilizing": 0.0,
        "degrading": 0.0,
        "converging": 0.0,
        "diverging": 0.0,
        "cycling": 0.0,
        "emerging": 0.0,
    }

    rules = [
        ("escalating", ("more", "increase", "grow", "spike", "compound", "accelerate", "worse", "critical")),
        ("degrading", ("fail", "error", "slow", "debt", "rot", "regress", "break", "outage", "decline")),
        ("stabilizing", ("stable", "steady", "plateau", "recover", "fix", "calm", "normalize")),
        ("converging", ("merge", "align", "same", "consensus", "unify", "standard")),
        ("diverging", ("split", "fork", "conflict", "diverge", "inconsistent", "drift")),
        ("cycling", ("again", "repeat", "cycle", "oscillat", "flip", "revisit")),
        ("emerging", ("new", "first", "novel", "appear", "nascent", "early")),
    ]
    for name, cues in rules:
        for c in cues:
            if c in blob:
                scores[name] += 1.0
            if c in feat_set or any(c in f for f in feat_set):
                scores[name] += 0.4

    for m in matches:
        if m.pattern.kind.value == "trajectory":
            scores["emerging"] += 0.3
        for tag in m.pattern.tags:
            if tag in scores:
                scores[tag] += 0.5 * m.score

    # Sequence length itself suggests emergence of a real trajectory
    if len(steps) >= 3:
        scores["emerging"] += 0.2
        scores["escalating"] += 0.1

    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] <= 0:
        return "emerging" if len(steps) <= 2 else "converging"
    return best[0]


def _next_expected(
    steps: Sequence[str],
    direction: str,
    matches: Sequence[MatchResult],
) -> str:
    last = steps[-1] if steps else ""
    templates = {
        "escalating": f"Intensity around “{last}” rises; expect compounding effects unless a brake is applied.",
        "degrading": f"Further failure modes related to “{last}” unless root lever is fixed.",
        "stabilizing": f"Variance shrinks; “{last}” becomes the new baseline if undisturbed.",
        "converging": f"Independent threads collapse toward a shared structure near “{last}”.",
        "diverging": f"Forks widen from “{last}”; coordination cost increases.",
        "cycling": f"Return to an earlier state resembling prior steps; watch for loop traps.",
        "emerging": f"A named pattern crystallizes from “{last}”; catalogue it before it spreads.",
    }
    base = templates.get(direction, f"Continuation from “{last}”.")
    if matches:
        top = matches[0].pattern.title
        base += f" Strongest prior: `{top}`."
    return base


def _risks(direction: str, steps: Sequence[str]) -> List[str]:
    common = {
        "escalating": ["runaway feedback", "late intervention", "alert fatigue"],
        "degrading": ["hidden root cause", "symptom-only fixes", "cascading failure"],
        "stabilizing": ["false calm", "regression when load returns"],
        "converging": ["premature consensus", "lost edge cases"],
        "diverging": ["incompatible forks", "duplicated effort"],
        "cycling": ["thrash", "unlearned lessons"],
        "emerging": ["unnamed pattern spreads unchecked", "overfitting noise"],
    }
    risks = list(common.get(direction, ["misread trajectory"]))
    if len(steps) < 2:
        risks.append("thin evidence — single snapshot")
    return risks


def _traj_confidence(steps: Sequence[str], matches: Sequence[MatchResult]) -> float:
    c = 0.25 + min(0.35, 0.08 * max(0, len(steps) - 1))
    if matches:
        c += 0.3 * matches[0].score
    return float(max(0.05, min(0.9, c)))


def observations_from_patterns(patterns: Sequence[Pattern]) -> List[str]:
    return [f"{p.title}: {p.body[:160]}" for p in patterns]
