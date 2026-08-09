"""Pattern Lattice — superior pattern-processing harness for AI agents.

Neurodivergent-inspired connecting-the-dots cognition as software:
encode → match → link → distill → extrapolate → generate → reinforce.

Standalone. Zero host coupling. Optional Hermes Agent skill/plugin later.
"""

from __future__ import annotations

from pattern_lattice.harness import PatternLattice
from pattern_lattice.models import (
    Domain,
    Evidence,
    LinkKind,
    MatchResult,
    Pattern,
    PatternKind,
    Trajectory,
)

__version__ = "0.1.0"
__all__ = [
    "PatternLattice",
    "Pattern",
    "PatternKind",
    "Domain",
    "LinkKind",
    "MatchResult",
    "Trajectory",
    "Evidence",
    "__version__",
]
