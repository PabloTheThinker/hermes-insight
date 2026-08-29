"""Cognitive plates — trait-based, non-diagnostic agent mindsets.

Inspired by Sonny Jane Wise's Neurodiversity Smorgasbord (2024): a plate of
human differences, not a DSM label. The plate can change at any time.

This module is an engineering overlay on recall / perceive / plan. It does not
claim lived neurodivergent identity, diagnose people or agents, or simulate
distress. Skipped platters: eating, sleep, motor, stimming-as-tic,
voice-hearing, mania / psychosis / hallucination.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight

META_KEY = "active_mindset"
PRESET_NAMES = ("balanced", "monotropic", "polytropic", "catalogue")
_FORBIDDEN = ("autism", "adhd", "disorder", "diagnosis", "dsm", "psychosis", "mania")

Attention = str
MemoryBias = str
TimeStyle = str
Sensory = str
Processing = str
MindsetArg = Union[str, Dict[str, Any], "CognitivePlate", None]


@dataclass(frozen=True)
class RecallKnobs:
    """Numeric overlay for the recall engine. Balanced equals 0.9 defaults."""

    spread_steps: int = 3
    spread_factor: float = 0.80
    inhibit_top_m: int = 7
    inhibit_beta: float = 0.12
    usable_activation: float = 0.12
    recency_half_life_days: float = 30.0
    env_boost: float = 1.35
    lane_limit_scale: float = 1.0
    rule_weight: float = 1.0
    fact_weight: float = 1.0
    echo_weight: float = 1.0
    sequence_weight: float = 1.0
    hop_weight: float = 1.0
    analogy_boost: float = 1.0
    thin_min_features: int = 3
    thin_min_words: int = 8
    thin_require_both: bool = True
    brief_match_n: int = 5
    brief_fact_n: int = 4
    brief_echo_n: int = 4
    brief_hop_n: int = 5
    refine_min_score: float = 0.45
    deep_min_len: int = 48

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CognitivePlate:
    """One inspectable plate. Axes are traits, not labels."""

    name: str = "balanced"
    attention: Attention = "balanced"
    memory: MemoryBias = "balanced"
    time: TimeStyle = "balanced"
    sensory: Sensory = "balanced"
    processing: Processing = "balanced"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "attention": self.attention,
            "memory": self.memory,
            "time": self.time,
            "sensory": self.sensory,
            "processing": self.processing,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def summary(self) -> str:
        return (
            f"mindset={self.name}"
            f" · attention={self.attention}"
            f" · memory={self.memory}"
            f" · time={self.time}"
            f" · sensory={self.sensory}"
            f" · processing={self.processing}"
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitivePlate":
        name = str(data.get("name") or "custom").strip().lower() or "custom"
        return cls(
            name=name if name in PRESET_NAMES or name == "custom" else "custom",
            attention=_axis(data.get("attention"), ("monotropic", "balanced", "polytropic")),
            memory=_axis(data.get("memory"), ("semantic", "balanced", "episodic", "procedural")),
            time=_axis(data.get("time"), ("linear", "balanced", "cyclical")),
            sensory=_axis(data.get("sensory"), ("filter", "balanced", "sensitive")),
            processing=_axis(data.get("processing"), ("gist", "balanced", "distill")),
        )


def _axis(value: Any, allowed: Sequence[str], default: str = "balanced") -> str:
    raw = str(value or default).strip().lower()
    return raw if raw in allowed else default


def plate_from_name(name: str) -> CognitivePlate:
    key = str(name or "balanced").strip().lower()
    presets: Dict[str, CognitivePlate] = {
        "balanced": CognitivePlate(),
        "monotropic": CognitivePlate(
            name="monotropic",
            attention="monotropic",
            memory="semantic",
            time="linear",
            sensory="filter",
            processing="distill",
        ),
        "polytropic": CognitivePlate(
            name="polytropic",
            attention="polytropic",
            memory="episodic",
            time="cyclical",
            sensory="sensitive",
            processing="gist",
        ),
        "catalogue": CognitivePlate(
            name="catalogue",
            attention="monotropic",
            memory="semantic",
            time="cyclical",
            sensory="sensitive",
            processing="distill",
        ),
    }
    return presets.get(key, CognitivePlate(name="custom"))


def apply_to_recall(plate: CognitivePlate) -> RecallKnobs:
    """Map a plate onto recall constants. Balanced reproduces 0.9 defaults."""
    knobs = RecallKnobs()
    if plate.attention == "monotropic":
        knobs = RecallKnobs(
            spread_steps=2,
            spread_factor=0.70,
            inhibit_top_m=4,
            inhibit_beta=0.22,
            usable_activation=knobs.usable_activation,
            recency_half_life_days=knobs.recency_half_life_days,
            lane_limit_scale=0.5,
            hop_weight=0.70,
        )
    elif plate.attention == "polytropic":
        knobs = RecallKnobs(
            spread_steps=4,
            spread_factor=0.88,
            inhibit_top_m=12,
            inhibit_beta=0.05,
            usable_activation=0.08,
            recency_half_life_days=knobs.recency_half_life_days,
            lane_limit_scale=1.5,
            hop_weight=1.30,
            analogy_boost=1.20,
        )

    rule_w, fact_w, echo_w, seq_w = 1.0, 1.0, 1.0, 1.0
    if plate.memory == "semantic":
        rule_w, fact_w, echo_w = 1.25, 1.10, 0.75
    elif plate.memory == "episodic":
        rule_w, fact_w, echo_w = 0.85, 1.05, 1.30
    elif plate.memory == "procedural":
        rule_w, seq_w, echo_w = 1.10, 1.30, 0.80

    half_life = knobs.recency_half_life_days
    if plate.time == "linear":
        half_life = max(7.0, half_life * 0.5)
    elif plate.time == "cyclical":
        half_life = min(90.0, half_life * 2.0)
        seq_w *= 1.35

    thin_feats, thin_words, both = 3, 8, True
    usable = knobs.usable_activation
    if plate.sensory == "filter":
        thin_feats, thin_words, both = 4, 6, False
        usable = max(usable, 0.16)
    elif plate.sensory == "sensitive":
        thin_feats, thin_words, both = 2, 5, True
        usable = min(usable, 0.08)

    analogy = knobs.analogy_boost
    brief_match_n, brief_fact_n, brief_echo_n, brief_hop_n = 5, 4, 4, 5
    refine_min_score = 0.45
    deep_min_len = 48
    if plate.processing == "distill":
        analogy *= 0.95
        refine_min_score = 0.35
        deep_min_len = 40
    elif plate.processing == "gist":
        analogy *= 1.05
        brief_match_n, brief_fact_n, brief_echo_n, brief_hop_n = 3, 2, 2, 2
        refine_min_score = 0.55
        deep_min_len = 80

    return RecallKnobs(
        spread_steps=knobs.spread_steps,
        spread_factor=knobs.spread_factor,
        inhibit_top_m=knobs.inhibit_top_m,
        inhibit_beta=knobs.inhibit_beta,
        usable_activation=usable,
        recency_half_life_days=half_life,
        env_boost=knobs.env_boost,
        lane_limit_scale=knobs.lane_limit_scale,
        rule_weight=rule_w,
        fact_weight=fact_w,
        echo_weight=echo_w,
        sequence_weight=seq_w,
        hop_weight=knobs.hop_weight,
        analogy_boost=analogy,
        thin_min_features=thin_feats,
        thin_min_words=thin_words,
        thin_require_both=both,
        brief_match_n=brief_match_n,
        brief_fact_n=brief_fact_n,
        brief_echo_n=brief_echo_n,
        brief_hop_n=brief_hop_n,
        refine_min_score=refine_min_score,
        deep_min_len=deep_min_len,
    )


def is_thin_query(text: str, knobs: RecallKnobs, features: Sequence[str]) -> bool:
    words = len((text or "").split())
    nfeat = len(features)
    short_feat = nfeat < knobs.thin_min_features
    short_words = words < knobs.thin_min_words
    if knobs.thin_require_both:
        return short_feat and short_words
    return short_feat or short_words


def contains_forbidden_language(text: str) -> bool:
    blob = (text or "").lower()
    return any(term in blob for term in _FORBIDDEN)


def parse_mindset_arg(value: Any) -> MindsetArg:
    """Accept a preset name, JSON object, plate, or omit (None)."""
    if value is None or value == "":
        return None
    if isinstance(value, CognitivePlate):
        return value
    if isinstance(value, dict):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(data, dict):
            return data
    return raw


def resolve_plate(lat: Optional["HermesInsight"] = None, mindset: MindsetArg = None) -> CognitivePlate:
    if isinstance(mindset, CognitivePlate):
        return mindset
    if isinstance(mindset, dict):
        return CognitivePlate.from_dict(mindset)
    if isinstance(mindset, str) and mindset.strip():
        return plate_from_name(mindset)
    if lat is not None:
        raw = lat.store.get_meta(META_KEY, "")
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return CognitivePlate.from_dict(data)
            except json.JSONDecodeError:
                return plate_from_name(raw)
    return plate_from_name("balanced")


def persist_plate(lat: "HermesInsight", plate: CognitivePlate) -> None:
    lat.store.set_meta(META_KEY, plate.to_json())


def attune(
    lat: "HermesInsight",
    mindset: MindsetArg = "balanced",
    **axes: Any,
) -> Dict[str, Any]:
    """Set the active plate. The plate can change at any time."""
    if axes and not isinstance(mindset, CognitivePlate):
        data = plate_from_name(str(mindset or "custom")).to_dict()
        if isinstance(mindset, dict):
            data = {**mindset}
        data.update({k: v for k, v in axes.items() if v is not None})
        data["name"] = "custom" if axes else data.get("name", "custom")
        plate = CognitivePlate.from_dict(data)
    else:
        plate = resolve_plate(None, mindset)
    persist_plate(lat, plate)
    return {
        "success": True,
        "mindset": plate.to_dict(),
        "knobs": apply_to_recall(plate).to_dict(),
        "summary": plate.summary(),
        "note": (
            "Trait plate for this seat only. Not a clinical label. "
            "Not a claim of lived neurodivergent identity. The plate can change."
        ),
    }
