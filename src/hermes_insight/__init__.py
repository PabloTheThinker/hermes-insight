"""Hermes Insight — superior pattern-processing harness for AI agents.

Neurodivergent-inspired connecting-the-dots cognition as software:
encode → match → link → distill → extrapolate → generate → reinforce.

Standalone. Zero host coupling. Optional Hermes Agent skill/plugin later.
"""

from __future__ import annotations

from hermes_insight.harness import HermesInsight
from hermes_insight.models import (
    Domain,
    Evidence,
    LinkKind,
    MatchResult,
    Pattern,
    PatternKind,
    Trajectory,
)

__version__ = "0.7.2"
__all__ = [
    "HermesInsight",
    "Pattern",
    "PatternKind",
    "Domain",
    "LinkKind",
    "MatchResult",
    "Trajectory",
    "Evidence",
    "__version__",
]
