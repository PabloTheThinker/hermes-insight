"""Hermes Insight — superior pattern-processing harness for AI agents.

Neurodivergent-inspired connecting-the-dots cognition as software:
encode → match → link → distill → recall → extrapolate → generate → reinforce.

Standalone. Zero host coupling. Optional Hermes Agent plugin/skill.
Optional bounded perceive-card organ for Hermespace (soft-import;
not a MemoryProvider).
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

__version__ = "0.9.2"
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
