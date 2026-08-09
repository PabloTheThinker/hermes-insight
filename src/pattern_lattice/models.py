"""Core types for Pattern Lattice.

Maps cognitive pattern-recognition theories onto durable agent structures:

* Template / prototype / feature layers (classic cognitive PR)
* Six processing dimensions (perception → generation continuum)
* Evidence + confidence hygiene (analytic tradecraft for agents)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
import hashlib
import json
import time
import uuid


class PatternKind(str, Enum):
    """What kind of structure this node encodes."""

    TEMPLATE = "template"  # near-exact stored exemplar
    PROTOTYPE = "prototype"  # averaged / idealized category center
    FEATURE = "feature"  # atomic detectable part
    SEQUENCE = "sequence"  # ordered steps / timeline
    RELATION = "relation"  # link-shaped claim (A relates-to B)
    RULE = "rule"  # if/then regularity
    TRAJECTORY = "trajectory"  # direction over time
    ANOMALY = "anomaly"  # deliberate novelty marker
    SYNTHESIS = "synthesis"  # agent-generated composite idea


class Domain(str, Enum):
    """Soft domain labels — cross-domain linking is a first-class goal."""

    GENERAL = "general"
    CODE = "code"
    SYSTEM = "system"
    SOCIAL = "social"
    PROCESS = "process"
    SENSORY = "sensory"
    LANGUAGE = "language"
    MARKET = "market"
    SCIENCE = "science"
    SELF = "self"  # agent/meta patterns about its own operation


class LinkKind(str, Enum):
    SIMILAR = "similar"
    PART_OF = "part_of"
    CAUSES = "causes"
    PRECEDES = "precedes"
    ANALOGY = "analogy"  # cross-domain structural map
    CONTRADICTS = "contradicts"
    REFINES = "refines"
    INSTANCE_OF = "instance_of"
    ENABLES = "enables"
    RHYMES = "rhymes"  # weak associative / lateral hop


class ProcessDim(str, Enum):
    """Six dimensions of pattern cognition (research-inspired operationalization)."""

    PERCEPTION = "perception"  # intake / feature salience
    RECOGNITION = "recognition"  # match to known structure
    MAINTENANCE = "maintenance"  # hold / stabilize / catalogue
    GENERATION = "generation"  # invent new structure
    SEEKING = "seeking"  # active hunt for regularity
    PROCESSING = "processing"  # deep monotropic work on a focus


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "p") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class Evidence:
    """Source hygiene — observation vs conclusion stay separable."""

    source: str
    kind: str = "observation"  # observation | inference | report | test
    confidence: float = 0.5
    note: str = ""
    at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Evidence":
        return cls(
            source=str(d.get("source", "")),
            kind=str(d.get("kind", "observation")),
            confidence=float(d.get("confidence", 0.5)),
            note=str(d.get("note", "")),
            at=float(d.get("at", _now())),
        )


@dataclass
class Pattern:
    """A node in the lattice — one encoded structure."""

    id: str
    title: str
    body: str
    kind: PatternKind = PatternKind.PROTOTYPE
    domain: Domain = Domain.GENERAL
    features: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.5
    strength: float = 0.5  # reinforcement (use + feedback)
    evidence: List[Evidence] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    last_used_at: float = 0.0
    use_count: int = 0
    content_hash: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            self.kind = PatternKind(self.kind)
        if isinstance(self.domain, str):
            self.domain = Domain(self.domain)
        if not self.content_hash:
            self.content_hash = content_hash(f"{self.title}\n{self.body}\n{'|'.join(self.features)}")

    def touch(self, delta_strength: float = 0.02) -> None:
        self.use_count += 1
        self.last_used_at = _now()
        self.updated_at = self.last_used_at
        self.strength = max(0.0, min(1.0, self.strength + delta_strength))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["domain"] = self.domain.value
        d["evidence"] = [e.to_dict() if isinstance(e, Evidence) else e for e in self.evidence]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Pattern":
        ev = [Evidence.from_dict(e) if isinstance(e, dict) else e for e in d.get("evidence", [])]
        return cls(
            id=str(d["id"]),
            title=str(d.get("title", "")),
            body=str(d.get("body", "")),
            kind=PatternKind(d.get("kind", PatternKind.PROTOTYPE.value)),
            domain=Domain(d.get("domain", Domain.GENERAL.value)),
            features=list(d.get("features") or []),
            tags=list(d.get("tags") or []),
            confidence=float(d.get("confidence", 0.5)),
            strength=float(d.get("strength", 0.5)),
            evidence=ev,
            metadata=dict(d.get("metadata") or {}),
            created_at=float(d.get("created_at", _now())),
            updated_at=float(d.get("updated_at", _now())),
            last_used_at=float(d.get("last_used_at", 0.0)),
            use_count=int(d.get("use_count", 0)),
            content_hash=str(d.get("content_hash", "")),
        )

    @classmethod
    def create(
        cls,
        title: str,
        body: str,
        *,
        kind: PatternKind | str = PatternKind.PROTOTYPE,
        domain: Domain | str = Domain.GENERAL,
        features: Optional[Sequence[str]] = None,
        tags: Optional[Sequence[str]] = None,
        confidence: float = 0.5,
        evidence: Optional[Sequence[Evidence]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
    ) -> "Pattern":
        return cls(
            id=id or _new_id("p"),
            title=title.strip(),
            body=body.strip(),
            kind=PatternKind(kind) if not isinstance(kind, PatternKind) else kind,
            domain=Domain(domain) if not isinstance(domain, Domain) else domain,
            features=[f.strip() for f in (features or []) if str(f).strip()],
            tags=[t.strip().lower() for t in (tags or []) if str(t).strip()],
            confidence=float(confidence),
            evidence=list(evidence or []),
            metadata=dict(metadata or {}),
        )


@dataclass
class Link:
    """Directed edge between patterns."""

    id: str
    source_id: str
    target_id: str
    kind: LinkKind
    weight: float = 0.5
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            self.kind = LinkKind(self.kind)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Link":
        return cls(
            id=str(d["id"]),
            source_id=str(d["source_id"]),
            target_id=str(d["target_id"]),
            kind=LinkKind(d.get("kind", LinkKind.SIMILAR.value)),
            weight=float(d.get("weight", 0.5)),
            note=str(d.get("note", "")),
            metadata=dict(d.get("metadata") or {}),
            created_at=float(d.get("created_at", _now())),
        )

    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        kind: LinkKind | str,
        *,
        weight: float = 0.5,
        note: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Link":
        return cls(
            id=_new_id("l"),
            source_id=source_id,
            target_id=target_id,
            kind=LinkKind(kind) if not isinstance(kind, LinkKind) else kind,
            weight=float(weight),
            note=note,
            metadata=dict(metadata or {}),
        )


@dataclass
class MatchResult:
    pattern: Pattern
    score: float
    method: str  # template | prototype | feature | hybrid | fts
    shared_features: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern.to_dict(),
            "score": self.score,
            "method": self.method,
            "shared_features": self.shared_features,
            "rationale": self.rationale,
        }


@dataclass
class Trajectory:
    """Extrapolated direction from a sequence of observations/patterns."""

    id: str
    title: str
    steps: List[str]
    direction: str
    confidence: float
    based_on: List[str] = field(default_factory=list)
    next_expected: str = ""
    risks: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        title: str,
        steps: Sequence[str],
        direction: str,
        *,
        confidence: float = 0.5,
        based_on: Optional[Sequence[str]] = None,
        next_expected: str = "",
        risks: Optional[Sequence[str]] = None,
    ) -> "Trajectory":
        return cls(
            id=_new_id("t"),
            title=title,
            steps=list(steps),
            direction=direction,
            confidence=float(confidence),
            based_on=list(based_on or []),
            next_expected=next_expected,
            risks=list(risks or []),
        )


@dataclass
class Distillation:
    """'Find the actual variable' — ND-style core-variable extraction."""

    actual_variable: str
    supporting: List[str]
    discarded: List[str]
    confidence: float
    principle: str = ""
    actionable: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CycleReport:
    """One turn of the agent pattern cycle."""

    query: str
    observations: List[str]
    matches: List[MatchResult]
    links: List[Dict[str, Any]]
    distillation: Optional[Distillation]
    trajectory: Optional[Trajectory]
    generated: List[Pattern]
    anomalies: List[Dict[str, Any]]
    brief: str
    dims_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "observations": self.observations,
            "matches": [m.to_dict() for m in self.matches],
            "links": self.links,
            "distillation": self.distillation.to_dict() if self.distillation else None,
            "trajectory": self.trajectory.to_dict() if self.trajectory else None,
            "generated": [p.to_dict() for p in self.generated],
            "anomalies": self.anomalies,
            "brief": self.brief,
            "dims_used": self.dims_used,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
