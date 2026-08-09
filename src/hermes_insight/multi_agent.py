"""Multi-agent compartments — isolated lattices that can share controlled links."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_agent_id(agent_id: str) -> str:
    s = (agent_id or "default").strip().lower()
    s = _SAFE.sub("-", s).strip("-._")
    return s[:64] or "default"


@dataclass
class AgentScope:
    """One agent identity / trust compartment."""

    agent_id: str
    display_name: str = ""
    tier: str = "worker"  # conductor | worker | client | public | lab
    parent_id: Optional[str] = None
    share_tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.agent_id = sanitize_agent_id(self.agent_id)
        if self.parent_id:
            self.parent_id = sanitize_agent_id(self.parent_id)
        self.display_name = self.display_name or self.agent_id
        self.share_tags = [t.lower() for t in self.share_tags]

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "tier": self.tier,
            "parent_id": self.parent_id,
            "share_tags": self.share_tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "AgentScope":
        return cls(
            agent_id=str(d.get("agent_id", "default")),
            display_name=str(d.get("display_name", "")),
            tier=str(d.get("tier", "worker")),
            parent_id=d.get("parent_id"),
            share_tags=list(d.get("share_tags") or []),
            metadata=dict(d.get("metadata") or {}),
        )


class MultiAgentRegistry:
    """Persists agent scopes beside the lattice DB."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._agents: Dict[str, AgentScope] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for row in data.get("agents") or []:
            a = AgentScope.from_dict(row)
            self._agents[a.agent_id] = a

    def save(self) -> None:
        payload = {"agents": [a.to_dict() for a in self._agents.values()]}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def register(self, scope: AgentScope) -> AgentScope:
        self._agents[scope.agent_id] = scope
        self.save()
        return scope

    def get(self, agent_id: str) -> Optional[AgentScope]:
        return self._agents.get(sanitize_agent_id(agent_id))

    def list(self) -> List[AgentScope]:
        return list(self._agents.values())

    def db_path_for(self, base_dir: Path | str, agent_id: str) -> Path:
        """Per-agent sqlite path under a root dir."""
        root = Path(base_dir)
        root.mkdir(parents=True, exist_ok=True)
        aid = sanitize_agent_id(agent_id)
        return root / f"{aid}.insight.db"


def resolve_agent_db(
    *,
    explicit_db: Optional[str] = None,
    agent_id: Optional[str] = None,
    home: Optional[str] = None,
) -> Path:
    """Resolve DB path with multi-agent awareness.

    Priority:
      1. explicit_db
      2. HERMES_INSIGHT_DB env (if no agent_id)
      3. {home|HERMES_INSIGHT_HOME|~/.hermes-insight}/agents/{id}.insight.db
      4. default single-tenant insight.db
    """
    import os

    if explicit_db:
        return Path(explicit_db).expanduser().resolve()
    if agent_id:
        base = Path(
            home
            or os.environ.get("HERMES_INSIGHT_HOME")
            or (Path(os.environ["HERMES_HOME"]) / "memories" / "hermes-insight"
                if os.environ.get("HERMES_HOME")
                else Path("~/.hermes-insight").expanduser())
        ).expanduser()
        reg = MultiAgentRegistry(base / "agents.json")
        if not reg.get(agent_id):
            reg.register(AgentScope(agent_id=agent_id))
        return reg.db_path_for(base / "agents", agent_id)
    env = os.environ.get("HERMES_INSIGHT_DB")
    if env:
        return Path(env).expanduser().resolve()
    home_p = Path(os.environ.get("HERMES_INSIGHT_HOME", "~/.hermes-insight")).expanduser()
    home_p.mkdir(parents=True, exist_ok=True)
    return home_p / "insight.db"
