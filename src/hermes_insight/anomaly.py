"""Anomaly / novelty detection against the catalogue.

ND sensory-cataloguing analog: unknown input raises a structured alert
until identified and filed — curiosity, not ambient anxiety.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from hermes_insight.features import extract_features, jaccard
from hermes_insight.match import match_patterns
from hermes_insight.models import MatchResult, Pattern, PatternKind


def detect_anomalies(
    text: str,
    catalogue: Sequence[Pattern],
    *,
    novelty_threshold: float = 0.18,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return anomaly records when input does not match known structure well."""
    feats = extract_features(text)
    if not catalogue:
        return [
            {
                "status": "uncatalogued",
                "novelty": 1.0,
                "reason": "empty catalogue — everything is novel",
                "features": feats[:16],
                "suggestion": "ingest this observation as a new pattern",
            }
        ]

    matches = match_patterns(text, feats, catalogue, limit=limit, min_score=0.0)
    best = matches[0].score if matches else 0.0
    novelty = float(max(0.0, min(1.0, 1.0 - best)))

    if best >= novelty_threshold:
        return []  # recognized — no anomaly brief

    nearest = [
        {
            "id": m.pattern.id,
            "title": m.pattern.title,
            "score": round(m.score, 4),
            "shared": m.shared_features[:8],
        }
        for m in matches[:3]
    ]
    return [
        {
            "status": "novel",
            "novelty": round(novelty, 4),
            "reason": (
                f"best match score {best:.3f} below recognition threshold "
                f"{novelty_threshold:.3f}"
            ),
            "features": feats[:20],
            "nearest": nearest,
            "suggestion": "catalogue as anomaly or new prototype; do not force-fit",
        }
    ]


def file_anomaly(
    text: str,
    *,
    title: str | None = None,
    domain: str = "general",
    matches: Sequence[MatchResult] | None = None,
) -> Pattern:
    feats = extract_features(text)
    t = title or (f"anomaly: {text.strip()[:60]}" if text.strip() else "anomaly")
    meta = {
        "nearest": [
            {"id": m.pattern.id, "score": m.score} for m in (matches or [])[:5]
        ]
    }
    return Pattern.create(
        title=t,
        body=text.strip(),
        kind=PatternKind.ANOMALY,
        domain=domain,
        features=feats,
        tags=["anomaly", "novel"],
        confidence=0.4,
        metadata=meta,
    )
