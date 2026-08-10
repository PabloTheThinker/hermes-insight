"""Typed agent events and local environment snapshots.

This is Hermes Insight's native observation layer.  It borrows the general
idea of provenance-rich experience records from agent-memory research while
remaining dependency-free, local, and built on Insight's existing lattice.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, TYPE_CHECKING

from hermes_insight.features import extract_features
from hermes_insight.models import Domain, Link, LinkKind, Pattern, PatternKind
from hermes_insight.scrub import scrub_metadata, scrub_text, should_skip_path

if TYPE_CHECKING:
    from hermes_insight.harness import HermesInsight


EVENT_SCHEMA = "hermes-insight.event.v1"
ENVIRONMENT_SCHEMA = "hermes-insight.environment.v1"
REDACTION_VERSION = "1"

_TRUST_CLASSES = {"local", "workspace", "imported", "community"}
_SENSITIVITY_CLASSES = {"public", "internal", "private", "restricted"}
_MANIFESTS = (
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "requirements.txt",
    "uv.lock",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
)
_TOOLS = ("git", "python3", "node", "npm", "docker", "rg", "pytest", "uv")


def _clean_token(value: Any, *, limit: int = 120) -> str:
    return scrub_text(str(value or "")).strip()[:limit]


def _normalize_class(value: str, allowed: set[str], fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback


def _run(root: Path, args: Sequence[str], *, timeout: float = 4.0) -> str:
    try:
        proc = subprocess.run(
            list(args),
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _git_state(root: Path) -> Dict[str, Any]:
    top = _run(root, ["git", "rev-parse", "--show-toplevel"])
    if not top:
        return {
            "is_repo": False,
            "revision": "",
            "branch": "",
            "dirty": [],
            "dirty_count": 0,
        }
    revision = _run(root, ["git", "rev-parse", "HEAD"])[:40]
    branch = _run(root, ["git", "branch", "--show-current"])[:120]
    raw_status = _run(root, ["git", "status", "--short", "--untracked-files=normal"])
    dirty: List[Dict[str, str]] = []
    for line in raw_status.splitlines()[:200]:
        if len(line) < 3:
            continue
        relative_path = line[3:].strip()
        if should_skip_path(relative_path):
            continue
        dirty.append(
            {
                "status": line[:2].strip() or "?",
                "path": scrub_text(relative_path)[:300],
            }
        )
    return {
        "is_repo": True,
        "revision": revision,
        "branch": scrub_text(branch),
        "dirty": dirty,
        "dirty_count": len(dirty),
    }


def _state_delta(previous: Mapping[str, Any], current: Mapping[str, Any]) -> Dict[str, Any]:
    changed: Dict[str, Dict[str, Any]] = {}
    for key in ("git", "manifests", "tools", "runtime"):
        before = previous.get(key)
        after = current.get(key)
        if before != after:
            changed[key] = {"before": before, "after": after}
    return {
        "changed": bool(changed),
        "changed_fields": sorted(changed),
        "changes": changed,
    }


def snapshot_environment(
    lat: "HermesInsight",
    root: str | Path,
    *,
    include_tools: bool = True,
) -> Dict[str, Any]:
    """Capture a scrubbed, metadata-only workspace snapshot and its delta."""
    path = Path(root).expanduser().resolve()
    if not path.exists():
        return {"success": False, "error": f"path not found: {scrub_text(str(path))}"}
    if path.is_file():
        path = path.parent

    root_id = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    manifests = sorted(name for name in _MANIFESTS if (path / name).is_file())
    state: Dict[str, Any] = {
        "schema": ENVIRONMENT_SCHEMA,
        "root_id": root_id,
        "root_name": scrub_text(path.name)[:120],
        "git": _git_state(path),
        "manifests": manifests,
        "runtime": {
            "python": platform.python_version(),
            "platform": sys.platform,
        },
        "tools": (
            {name: bool(shutil.which(name)) for name in _TOOLS}
            if include_tools
            else {}
        ),
    }
    state = scrub_metadata(state)
    canonical = json.dumps(state, sort_keys=True, ensure_ascii=False)
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]

    previous: Optional[Pattern] = None
    previous_id = lat.store.get_meta(f"environment_snapshot:{root_id}", "")
    if previous_id:
        previous = lat.store.get_pattern(previous_id)
    previous_state = dict((previous.metadata or {}).get("snapshot") or {}) if previous else {}
    delta = _state_delta(previous_state, state) if previous else {
        "changed": True,
        "changed_fields": ["initial"],
        "changes": {},
    }

    body = json.dumps(
        {"state": state, "delta": delta},
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    pattern = lat.ingest(
        title=f"environment:{state['root_name']}:{fingerprint[:8]}",
        body=body,
        kind=PatternKind.PROTOTYPE,
        domain=Domain.SYSTEM,
        features=extract_features(body, max_features=48)
        + ["environment", "snapshot", "workspace", state["root_name"]],
        tags=["fabric", "environment", "snapshot", f"root:{root_id}"],
        confidence=0.9,
        source="environment-observer",
        metadata={
            "fabric": "environment_snapshot",
            "schema": ENVIRONMENT_SCHEMA,
            "root_id": root_id,
            "fingerprint": fingerprint,
            "snapshot": state,
            "delta": delta,
            "captured_at": time.time(),
        },
        link=False,
    )
    if previous and previous.id != pattern.id:
        lat.store.upsert_link(
            Link.create(
                previous.id,
                pattern.id,
                LinkKind.PRECEDES,
                weight=0.9,
                note="environment snapshot delta",
                metadata={"root_id": root_id},
            )
        )
    lat.store.set_meta(f"environment_snapshot:{root_id}", pattern.id)
    lat.store.set_meta("last_environment_snapshot_id", pattern.id)
    return {
        "success": True,
        "snapshot_id": pattern.id,
        "schema": ENVIRONMENT_SCHEMA,
        "fingerprint": fingerprint,
        "state": state,
        "delta": delta,
        "previous_snapshot_id": previous.id if previous else None,
    }


def record_event(
    lat: "HermesInsight",
    event_type: str,
    summary: str,
    *,
    details: Optional[Mapping[str, Any]] = None,
    trace_id: str = "",
    parent_event_id: str = "",
    session_id: str = "",
    task_id: Optional[str] = None,
    step_id: str = "",
    attempt: int = 1,
    status: str = "observed",
    outcome: str = "",
    model: str = "",
    tool: str = "",
    skill_id: str = "",
    environment_snapshot_id: str = "",
    duration_ms: Optional[float] = None,
    cost: Optional[float] = None,
    input_artifact_refs: Optional[Sequence[str]] = None,
    output_artifact_refs: Optional[Sequence[str]] = None,
    provenance: Optional[Mapping[str, Any]] = None,
    trust_class: str = "local",
    sensitivity: str = "private",
    started_at: Optional[float] = None,
) -> Dict[str, Any]:
    """Record one provenance-rich agent/tool/skill/environment event."""
    event_type = _clean_token(event_type or "observation", limit=80).lower().replace(" ", ".")
    summary = scrub_text(summary or "").strip()
    if not summary:
        return {"success": False, "error": "summary required"}
    task_id = task_id or lat.store.get_meta("active_task_id", "") or None
    environment_snapshot_id = (
        environment_snapshot_id
        or lat.store.get_meta("last_environment_snapshot_id", "")
    )
    trust_class = _normalize_class(trust_class, _TRUST_CLASSES, "local")
    sensitivity = _normalize_class(sensitivity, _SENSITIVITY_CLASSES, "private")
    safe_details = scrub_metadata(dict(details or {}))
    safe_provenance = scrub_metadata(dict(provenance or {}))
    envelope: Dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "trace_id": _clean_token(trace_id),
        "parent_event_id": _clean_token(parent_event_id),
        "session_id": _clean_token(session_id),
        "task_id": _clean_token(task_id),
        "step_id": _clean_token(step_id),
        "attempt": max(1, int(attempt or 1)),
        "event_type": event_type,
        "status": _clean_token(status, limit=40).lower() or "observed",
        "outcome": _clean_token(outcome, limit=40).lower(),
        "agent_id": _clean_token(lat.agent_id),
        "model": _clean_token(model),
        "tool": _clean_token(tool),
        "skill_id": _clean_token(skill_id),
        "environment_snapshot_id": _clean_token(environment_snapshot_id),
        "started_at": float(started_at if started_at is not None else time.time()),
        "duration_ms": float(duration_ms) if duration_ms is not None else None,
        "cost": float(cost) if cost is not None else None,
        "input_artifact_refs": [
            scrub_text(str(x))[:500] for x in (input_artifact_refs or [])
        ][:40],
        "output_artifact_refs": [
            scrub_text(str(x))[:500] for x in (output_artifact_refs or [])
        ][:40],
        "provenance": safe_provenance,
        "trust_class": trust_class,
        "sensitivity": sensitivity,
        "redaction_version": REDACTION_VERSION,
        "details": safe_details,
    }
    body = json.dumps(
        {"summary": summary, "event": envelope},
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    tags = ["experience", "event", f"event:{event_type}", f"status:{envelope['status']}"]
    if task_id:
        from hermes_insight.experience import _task_tag

        tags.append(_task_tag(task_id))
    if envelope["outcome"]:
        tags.append(f"outcome:{envelope['outcome']}")
    pattern = lat.ingest(
        title=f"{event_type}: {summary}"[:120],
        body=body,
        kind=PatternKind.EVENT,
        domain=Domain.EXPERIENCE,
        features=extract_features(body, max_features=48)
        + ["event", event_type, envelope["status"]],
        tags=tags,
        confidence=0.85 if trust_class in {"local", "workspace"} else 0.6,
        source="typed-event",
        metadata={**envelope, "event": True, "summary": summary},
        link=False,
    )

    links: List[Dict[str, Any]] = []
    if parent_event_id and lat.store.get_pattern(parent_event_id):
        link = lat.store.upsert_link(
            Link.create(
                parent_event_id,
                pattern.id,
                LinkKind.PRECEDES,
                weight=0.9,
                note="event parent/child sequence",
                metadata={"trace_id": envelope["trace_id"]},
            )
        )
        links.append(link.to_dict())
    if environment_snapshot_id and lat.store.get_pattern(environment_snapshot_id):
        link = lat.store.upsert_link(
            Link.create(
                pattern.id,
                environment_snapshot_id,
                LinkKind.OBSERVED_IN,
                weight=0.9,
                note="event observed in environment snapshot",
            )
        )
        links.append(link.to_dict())
    if task_id:
        from hermes_insight.experience import _chain_task_event

        _chain_task_event(lat.store, pattern, task_id)

    lat.store.set_meta("last_typed_event_id", pattern.id)
    return {
        "success": True,
        "event_id": pattern.id,
        "event": pattern.to_dict(),
        "envelope": {**envelope, "event_id": pattern.id},
        "links": links,
    }
