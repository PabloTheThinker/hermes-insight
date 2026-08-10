"""Native Hermes Agent plugin — Hermes Insight tools + prompt stance.

Install (user plugin):
  mkdir -p \"$HERMES_HOME/plugins\"
  cp -R hermes_plugin/hermes_insight_plugin \"$HERMES_HOME/plugins/hermes-insight\"
  # enable in config.yaml:
  # plugins:
  #   enabled: [..., hermes-insight]
  #   entries:
  #     hermes-insight:
  #       agent_id: myagent   # optional multi-agent compartment

Requires: pip install hermes-insight  (or editable path)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

__plugin_name__ = "hermes-insight"
__plugin_version__ = "0.8.0"


def _cfg() -> dict:
    try:
        from hermes_cli.config import cfg_get, load_config_readonly

        all_cfg = load_config_readonly()
        # try both key styles
        e1 = cfg_get(all_cfg, "plugins", "entries", "hermes-insight", default=None)
        e2 = cfg_get(all_cfg, "plugins", "entries", "hermes_insight", default=None)
        return dict(e1 or e2 or {})
    except Exception:
        return {}


def _db_path() -> str:
    cfg = _cfg()
    if cfg.get("db_path"):
        return str(Path(cfg["db_path"]).expanduser())
    env = os.environ.get("HERMES_INSIGHT_DB")
    if env:
        return str(Path(env).expanduser())
    home = os.environ.get("HERMES_HOME")
    if home:
        p = Path(home) / "memories" / "hermes-insight" / "insight.db"
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    p = Path.home() / ".hermes-insight" / "insight.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def _agent_id() -> Optional[str]:
    cfg = _cfg()
    return cfg.get("agent_id") or os.environ.get("HERMES_INSIGHT_AGENT_ID")


def _agent_tier() -> str:
    cfg = _cfg()
    tier = cfg.get("agent_tier") or os.environ.get("HERMES_INSIGHT_AGENT_TIER") or "worker"
    return str(tier)


def _lattice():
    from hermes_insight import HermesInsight

    return HermesInsight(
        db_path=_db_path(),
        agent_id=_agent_id(),
        agent_tier=_agent_tier(),
    )


def _ok(data: Any) -> str:
    return json.dumps({"success": True, "data": data}, ensure_ascii=False, default=str)


def _err(msg: str) -> str:
    return json.dumps({"success": False, "error": msg}, ensure_ascii=False)


# --- tool handlers ---------------------------------------------------------

def handle_insight_cycle(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        report = lat.cycle(
            str(args.get("query") or ""),
            observations=list(args.get("observations") or []),
            ingest_query=bool(args.get("ingest", False)),
            domain=str(args.get("domain") or "general"),
            evolve=bool(args.get("evolve", True)),
        )
        return _ok(
            {
                "brief": report.brief,
                "distillation": report.distillation.to_dict() if report.distillation else None,
                "trajectory": report.trajectory.to_dict() if report.trajectory else None,
                "top_matches": [
                    {
                        "id": m.pattern.id,
                        "title": m.pattern.title,
                        "score": m.score,
                        "method": m.method,
                        "shared": m.shared_features[:12],
                    }
                    for m in report.matches[:8]
                ],
                "anomalies": report.anomalies,
                "stats": lat.stats(),
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_cycle failed")
        return _err(str(exc))


def handle_insight_ingest(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        path = args.get("path")
        if path:
            pat = lat.ingest_file(str(path), domain=str(args.get("domain") or "code"))
            if not pat:
                return _err(f"could not ingest path: {path}")
            return _ok(pat.to_dict())
        title = str(args.get("title") or "").strip()
        body = str(args.get("body") or "").strip()
        if not title or not body:
            return _err("title+body or path required")
        pat = lat.ingest(
            title,
            body,
            domain=str(args.get("domain") or "general"),
            kind=str(args.get("kind") or "prototype"),
            tags=list(args.get("tags") or []),
            confidence=float(args.get("confidence") or 0.6),
        )
        return _ok(pat.to_dict())
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_ingest_tree(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        root = str(args.get("root") or "").strip()
        if not root:
            return _err("root required")
        result = lat.ingest_tree(
            root,
            glob=str(args.get("glob") or "**/*.py"),
            limit=int(args.get("limit") or 60),
            domain=str(args.get("domain") or "code"),
            link=bool(args.get("link", True)),
        )
        return _ok(result)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_match(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        return _ok(
            lat.match(
                str(args.get("query") or ""),
                limit=int(args.get("limit") or 10),
                domain=args.get("domain"),
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_distill(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        return _ok(lat.distill(str(args.get("text") or "")))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_feedback(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        ids = args.get("pattern_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        return _ok(lat.feedback(list(ids), helpful=not bool(args.get("unhelpful"))))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_stats(args: dict, **kwargs) -> str:
    try:
        return _ok(_lattice().stats())
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_evolve(args: dict, **kwargs) -> str:
    try:
        return _ok(_lattice().evolve(decay=bool(args.get("decay", True))))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_index_server(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        roots = args.get("roots")
        if isinstance(roots, str):
            roots = [roots]
        result = lat.index_server(
            roots=roots,
            include_files=bool(args.get("include_files", True)),
            include_connections=bool(args.get("include_connections", True)),
            include_processes=bool(args.get("include_processes", True)),
            include_hermes=bool(args.get("include_hermes", True)),
            max_files_per_project=int(args.get("max_files_per_project") or 40),
            max_projects=int(args.get("max_projects") or 80),
            link=bool(args.get("link", True)),
        )
        return _ok(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_index_server failed")
        return _err(str(exc))


def handle_insight_index_path(args: dict, **kwargs) -> str:
    try:
        path = str(args.get("path") or "").strip()
        if not path:
            return _err("path required")
        return _ok(
            _lattice().index_path(
                path,
                max_files=int(args.get("max_files") or 60),
                link=bool(args.get("link", True)),
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_index_connections(args: dict, **kwargs) -> str:
    try:
        return _ok(_lattice().index_connections())
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_fabric_stats(args: dict, **kwargs) -> str:
    try:
        return _ok(_lattice().fabric_stats())
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_forge(args: dict, **kwargs) -> str:
    try:
        only = args.get("products") or args.get("only")
        if isinstance(only, str):
            only = [x.strip() for x in only.split(",") if x.strip()]
        result = _lattice().forge(
            out_dir=args.get("out_dir"),
            write_synthesis=bool(args.get("write_synthesis", True)),
            products=only,
        )
        return _ok(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_forge failed")
        return _err(str(exc))


def handle_insight_recall(args: dict, **kwargs) -> str:
    """Fast pre-action pattern + experience recall."""
    try:
        lat = _lattice()
        return _ok(
            lat.recall(
                str(args.get("query") or ""),
                limit=int(args.get("limit") or 8),
                include_experiences=bool(args.get("include_experiences", True)),
                domain=args.get("domain"),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_recall failed")
        return _err(str(exc))


def handle_insight_experience(args: dict, **kwargs) -> str:
    """Log a lived event/episode and auto-connect to the lattice."""
    try:
        lat = _lattice()
        return _ok(
            lat.experience(
                str(args.get("title") or ""),
                str(args.get("body") or ""),
                kind=str(args.get("kind") or "event"),
                task_id=args.get("task_id"),
                outcome=args.get("outcome"),
                tags=list(args.get("tags") or []),
                confidence=float(args.get("confidence") or 0.65),
                auto_connect=bool(args.get("auto_connect", True)),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_experience failed")
        return _err(str(exc))


def handle_insight_task(args: dict, **kwargs) -> str:
    """Open or close a task episode (connects experience across steps)."""
    try:
        lat = _lattice()
        action = str(args.get("action") or "open").lower().strip()
        if action in {"open", "start"}:
            return _ok(
                lat.open_task(
                    str(args.get("name") or args.get("title") or "task"),
                    goal=str(args.get("goal") or args.get("body") or ""),
                    tags=list(args.get("tags") or []),
                    task_id=args.get("task_id"),
                )
            )
        if action in {"close", "done", "fail", "end"}:
            outcome = str(args.get("outcome") or ("failed" if action == "fail" else "done"))
            return _ok(
                lat.close_task(
                    args.get("task_id"),
                    outcome=outcome,
                    summary=str(args.get("summary") or args.get("body") or ""),
                    reinforce_connected=bool(args.get("reinforce", True)),
                    used_pattern_ids=args.get("used_pattern_ids"),
                )
            )
        return _err("action must be open|close")
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_task failed")
        return _err(str(exc))


def handle_insight_connect(args: dict, **kwargs) -> str:
    """Link two patterns or auto-connect free text into the lattice."""
    try:
        lat = _lattice()
        return _ok(
            lat.connect(
                str(args.get("left") or args.get("a") or args.get("query") or ""),
                args.get("right") or args.get("b"),
                kind=str(args.get("kind") or "similar"),
                note=str(args.get("note") or ""),
                weight=float(args.get("weight") or 0.6),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_connect failed")
        return _err(str(exc))



def handle_insight_hygiene(args: dict, **kwargs) -> str:
    try:
        lat = _lattice()
        return _ok(lat.hygiene(
            decay=bool(args.get("decay", True)),
            densify=bool(args.get("densify", True)),
        ))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_bootstrap(args: dict, **kwargs) -> str:
    try:
        return _ok(_lattice().bootstrap(force=bool(args.get("force", False))))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def handle_insight_perceive(args: dict, **kwargs) -> str:
    """Primary pattern-recognition ability for any Hermes agent."""
    try:
        lat = _lattice()
        obs = args.get("observations") or []
        if isinstance(obs, str):
            obs = [obs]
        return _ok(
            lat.perceive(
                str(args.get("situation") or args.get("query") or ""),
                observations=list(obs),
                domain=args.get("domain"),
                limit=int(args.get("limit") or 8),
                log_experience=bool(args.get("log", False) or args.get("log_experience", False)),
                experience_title=args.get("title"),
                task_id=args.get("task_id"),
                deep=bool(args.get("deep", False)),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_perceive failed")
        return _err(str(exc))


def handle_insight_plan(args: dict, **kwargs) -> str:
    """Build a ranked plan from relevance, explicit outcomes, and local affordances."""
    try:
        obs = args.get("observations") or []
        if isinstance(obs, str):
            obs = [obs]
        return _ok(
            _lattice().plan(
                str(args.get("situation") or args.get("query") or ""),
                observations=list(obs),
                domain=args.get("domain"),
                limit=int(args.get("limit") or 5),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_plan failed")
        return _err(str(exc))


def handle_insight_observe(args: dict, **kwargs) -> str:
    """Record a typed event or capture a metadata-only environment snapshot."""
    try:
        lat = _lattice()
        mode = str(args.get("mode") or "event").strip().lower()
        if mode == "environment":
            result = lat.snapshot_environment(
                str(args.get("root") or "."),
                include_tools=bool(args.get("include_tools", True)),
            )
        elif mode == "event":
            result = lat.record_event(
                str(args.get("event_type") or "observation"),
                str(args.get("summary") or ""),
                details=dict(args.get("details") or {}),
                trace_id=str(args.get("trace_id") or ""),
                parent_event_id=str(args.get("parent_event_id") or ""),
                session_id=str(args.get("session_id") or ""),
                task_id=args.get("task_id"),
                step_id=str(args.get("step_id") or ""),
                attempt=int(args.get("attempt") or 1),
                status=str(args.get("status") or "observed"),
                outcome=str(args.get("outcome") or ""),
                model=str(args.get("model") or ""),
                tool=str(args.get("tool") or ""),
                skill_id=str(args.get("skill_id") or ""),
                environment_snapshot_id=str(args.get("environment_snapshot_id") or ""),
                duration_ms=args.get("duration_ms"),
                cost=args.get("cost"),
                input_artifact_refs=list(args.get("input_artifact_refs") or []),
                output_artifact_refs=list(args.get("output_artifact_refs") or []),
                provenance=dict(args.get("provenance") or {}),
                trust_class=str(args.get("trust_class") or "local"),
                sensitivity=str(args.get("sensitivity") or "private"),
            )
        else:
            return _err("mode must be event|environment")
        if not result.get("success"):
            return _err(str(result.get("error") or "observation failed"))
        return _ok(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_observe failed")
        return _err(str(exc))


def handle_insight_ingest_messages(args: dict, **kwargs) -> str:
    try:
        msgs = args.get("messages") or []
        if isinstance(msgs, str):
            import json as _json

            msgs = _json.loads(msgs)
        return _ok(
            _lattice().ingest_messages(
                list(msgs),
                task_id=args.get("task_id"),
                title=str(args.get("title") or "session slice"),
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


# schemas
_CYCLE_SCHEMA = {
    "name": "insight_cycle",
    "description": (
        "Run a Hermes Insight cognitive cycle: multi-lens pattern match, distill the "
        "actual variable, extrapolate trajectory, lateral links, novelty catalogue. "
        "Use for root-cause, architecture, ops, and cross-domain structure problems."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "observations": {"type": "array", "items": {"type": "string"}},
            "domain": {"type": "string", "description": "general|code|system|social|process|..."},
            "ingest": {"type": "boolean", "description": "Also catalogue the query"},
            "evolve": {"type": "boolean", "default": True},
        },
        "required": ["query"],
    },
}

_INGEST_SCHEMA = {
    "name": "insight_ingest",
    "description": "Catalogue a pattern (title+body) or a single source file path (code-aware).",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "path": {"type": "string", "description": "Source file to ingest"},
            "domain": {"type": "string"},
            "kind": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
    },
}

_TREE_SCHEMA = {
    "name": "insight_ingest_tree",
    "description": "Bulk code-aware ingest of a directory tree into the Insight lattice.",
    "parameters": {
        "type": "object",
        "properties": {
            "root": {"type": "string"},
            "glob": {"type": "string", "default": "**/*.py"},
            "limit": {"type": "integer", "default": 60},
            "domain": {"type": "string", "default": "code"},
            "link": {"type": "boolean", "default": True},
        },
        "required": ["root"],
    },
}

_MATCH_SCHEMA = {
    "name": "insight_match",
    "description": "Match a query against the Insight lattice (IDF hybrid recognition).",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
            "domain": {"type": "string"},
        },
        "required": ["query"],
    },
}

_DISTILL_SCHEMA = {
    "name": "insight_distill",
    "description": "Find the actual structural variable (lever) in messy text.",
    "parameters": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
}

_FEEDBACK_SCHEMA = {
    "name": "insight_feedback",
    "description": "Reinforce or weaken patterns after real-world use.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern_ids": {"type": "array", "items": {"type": "string"}},
            "unhelpful": {"type": "boolean", "default": False},
        },
        "required": ["pattern_ids"],
    },
}

_STATS_SCHEMA = {
    "name": "insight_stats",
    "description": "Insight lattice stats (path, counts, agent compartment).",
    "parameters": {"type": "object", "properties": {}},
}

_EVOLVE_SCHEMA = {
    "name": "insight_evolve",
    "description": "Run one evolution tick (optional decay + cluster synthesis).",
    "parameters": {
        "type": "object",
        "properties": {"decay": {"type": "boolean", "default": True}},
    },
}

_INDEX_SERVER_SCHEMA = {
    "name": "insight_index_server",
    "description": (
        "Index the server fabric into Insight: projects, source files, Hermes metadata, "
        "listening ports/connections, process snapshot. Secrets and host fingerprints scrubbed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "roots": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional roots; default discovers ~/projects, hermes-agent, HERMES_HOME",
            },
            "include_files": {"type": "boolean", "default": True},
            "include_connections": {"type": "boolean", "default": True},
            "include_processes": {"type": "boolean", "default": True},
            "include_hermes": {"type": "boolean", "default": True},
            "max_files_per_project": {"type": "integer", "default": 40},
            "max_projects": {"type": "integer", "default": 80},
            "link": {"type": "boolean", "default": True},
        },
    },
}

_INDEX_PATH_SCHEMA = {
    "name": "insight_index_path",
    "description": "Index one project directory or file into the Insight lattice (scrubbed).",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "max_files": {"type": "integer", "default": 60},
            "link": {"type": "boolean", "default": True},
        },
        "required": ["path"],
    },
}

_INDEX_CONN_SCHEMA = {
    "name": "insight_index_connections",
    "description": "Index listening ports and process connection classes only.",
    "parameters": {"type": "object", "properties": {}},
}

_FABRIC_STATS_SCHEMA = {
    "name": "insight_fabric_stats",
    "description": "Counts of fabric-tagged patterns (projects, listens, files, hermes runtime).",
    "parameters": {"type": "object", "properties": {}},
}

_FORGE_SCHEMA = {
    "name": "insight_forge",
    "description": (
        "Forge NEW products from lattice patterns and connections: orientation map, "
        "prediction board, transfer pack, invention seeds, action playbooks, watch edges. "
        "This is how patterns become useful — not just stored."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "out_dir": {"type": "string"},
            "products": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subset: map, predict, transfer, invent, playbooks, watch",
            },
            "write_synthesis": {"type": "boolean", "default": True},
        },
    },
}

_RECALL_SCHEMA = {
    "name": "insight_recall",
    "description": (
        "FAST pre-action pattern recall. Call BEFORE hard debugging, architecture choices, "
        "or recurring ops. Returns structural priors, lived experience echoes, graph hops, "
        "and a short brief with the actual lever. Prefer this over full insight_cycle when "
        "you need speed mid-task."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What you are about to work on / saw"},
            "limit": {"type": "integer", "default": 8},
            "domain": {"type": "string"},
            "include_experiences": {"type": "boolean", "default": True},
        },
        "required": ["query"],
    },
}

_EXPERIENCE_SCHEMA = {
    "name": "insight_experience",
    "description": (
        "Log a lived EVENT or EPISODE into the lattice and AUTO-CONNECT it to matching "
        "patterns. Use after a meaningful observation, failure, fix, or decision so the "
        "next session connects dots faster. Pass task_id when inside an open task."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "kind": {
                "type": "string",
                "description": "event | episode | task | sequence",
                "default": "event",
            },
            "task_id": {"type": "string"},
            "outcome": {"type": "string", "description": "optional: success|failed|blocked|..."},
            "tags": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
            "auto_connect": {"type": "boolean", "default": True},
        },
        "required": ["title", "body"],
    },
}

_TASK_SCHEMA = {
    "name": "insight_task",
    "description": (
        "Open or close a TASK episode. open → returns task_id + prior pattern matches for "
        "the goal. close → logs outcome, chains events, reinforces patterns that paid rent. "
        "Use around multi-step work so experiences link across steps."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "open | close",
            },
            "name": {"type": "string", "description": "Task name (open)"},
            "goal": {"type": "string"},
            "task_id": {"type": "string", "description": "Required for close unless one is active"},
            "outcome": {"type": "string", "description": "done|failed|blocked|shipped|..."},
            "summary": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "reinforce": {"type": "boolean", "default": True},
            "used_pattern_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Pattern/skill ids actually applied. Explicit credit lets future plans "
                    "learn from this outcome; omit rather than guessing."
                ),
            },
        },
        "required": ["action"],
    },
}

_CONNECT_SCHEMA = {
    "name": "insight_connect",
    "description": (
        "Explicitly link two pattern ids/titles, OR pass only `left` as free text to "
        "auto-catalogue and connect it into the lattice. Use when you see 'same shape as X'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "left": {"type": "string", "description": "Pattern id/title OR free text"},
            "right": {"type": "string", "description": "Pattern id/title (optional)"},
            "kind": {
                "type": "string",
                "description": "similar|analogy|causes|precedes|instance_of|experienced_as|next|...",
                "default": "similar",
            },
            "note": {"type": "string"},
            "weight": {"type": "number", "default": 0.6},
        },
        "required": ["left"],
    },
}

_HYGIENE_SCHEMA = {
    "name": "insight_hygiene",
    "description": (
        "Maintain the Insight lattice for better recognition: decay unused fabric/code "
        "noise and densify structural links (rules/skills). Run periodically or after bulk index."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "decay": {"type": "boolean", "default": True},
            "densify": {"type": "boolean", "default": True},
        },
    },
}

_BOOTSTRAP_SCHEMA = {

    "name": "insight_bootstrap",
    "description": "Seed starter agent-field patterns into an empty lattice (safe no-op if already populated).",
    "parameters": {
        "type": "object",
        "properties": {"force": {"type": "boolean", "default": False}},
    },
}

_PERCEIVE_SCHEMA = {
    "name": "insight_perceive",
    "description": (
        "PRIMARY pattern-recognition ability. Call when you need to understand a situation "
        "structurally: returns the controlling lever, top matching patterns, lived echoes, "
        "graph hops, and an action hint. Prefer this over inventing root cause from scratch. "
        "Set log=true to also catalogue the scene for future recall. Set deep=true for a "
        "full cognitive cycle when the scene looks novel."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "situation": {
                "type": "string",
                "description": "What you see / the problem / the decision",
            },
            "query": {"type": "string", "description": "Alias for situation"},
            "observations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Extra facts: errors, metrics, user quotes",
            },
            "domain": {"type": "string"},
            "limit": {"type": "integer", "default": 8},
            "log": {
                "type": "boolean",
                "default": False,
                "description": "Also log as experience (connects for next time)",
            },
            "deep": {
                "type": "boolean",
                "default": False,
                "description": "Force full cycle if scene may be novel",
            },
            "task_id": {"type": "string"},
            "title": {"type": "string", "description": "Optional experience title when log=true"},
        },
        "required": ["situation"],
    },
}

_PLAN_SCHEMA = {
    "name": "insight_plan",
    "description": (
        "Turn pattern recognition into an auditable action plan. Ranks rules, skills, "
        "and workflows by current relevance plus explicit success/failure history; also "
        "returns matching local tools, models, and agents. Does not execute anything."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "situation": {"type": "string", "description": "Task, event, or decision to plan"},
            "query": {"type": "string", "description": "Alias for situation"},
            "observations": {"type": "array", "items": {"type": "string"}},
            "domain": {"type": "string"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["situation"],
    },
}

_OBSERVE_SCHEMA = {
    "name": "insight_observe",
    "description": (
        "Hermes Insight native observation layer. mode=event records a typed, "
        "provenance-rich agent/tool/skill event. mode=environment captures scrubbed "
        "workspace metadata and a delta from its previous snapshot. No AgentDrive runtime."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "description": "event | environment"},
            "root": {"type": "string", "description": "Workspace root for environment mode"},
            "include_tools": {"type": "boolean", "default": True},
            "event_type": {"type": "string"},
            "summary": {"type": "string"},
            "details": {"type": "object"},
            "trace_id": {"type": "string"},
            "parent_event_id": {"type": "string"},
            "session_id": {"type": "string"},
            "task_id": {"type": "string"},
            "step_id": {"type": "string"},
            "attempt": {"type": "integer", "default": 1},
            "status": {"type": "string"},
            "outcome": {"type": "string"},
            "model": {"type": "string"},
            "tool": {"type": "string"},
            "skill_id": {"type": "string"},
            "environment_snapshot_id": {"type": "string"},
            "duration_ms": {"type": "number"},
            "cost": {"type": "number"},
            "input_artifact_refs": {"type": "array", "items": {"type": "string"}},
            "output_artifact_refs": {"type": "array", "items": {"type": "string"}},
            "provenance": {"type": "object"},
            "trust_class": {
                "type": "string",
                "description": "local | workspace | imported | community",
            },
            "sensitivity": {
                "type": "string",
                "description": "public | internal | private | restricted",
            },
        },
        "required": ["mode"],
    },
}

_INGEST_MSG_SCHEMA = {
    "name": "insight_ingest_messages",
    "description": (
        "Ingest a scrubbed session transcript slice (list of {role, content}) as one "
        "episode and auto-connect to patterns. Use to pull recent chat into the lattice."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "items": {"type": "object"},
                "description": "[{role, content}, ...]",
            },
            "title": {"type": "string"},
            "task_id": {"type": "string"},
        },
        "required": ["messages"],
    },
}


_SYSTEM_BLOCK = """## Hermes Insight — pattern recognition ability
You have structural pattern-processing tools (`insight_*`).

**Default ability (use this):**
- `insight_perceive` — ONE call: lever + matching structures + lived echoes + action hint.
  Use before hard debugging, architecture choices, or recurring failures.
  Set log=true after a meaningful scene so the next session is faster.
  Set deep=true when the scene looks novel.
- `insight_plan` — when work needs a route: ranked patterns/skills + local affordances +
  explicit outcome evidence. It recommends; it does not execute.
- `insight_observe` — record typed events or capture a scrubbed environment snapshot.

**Multi-step work:**
1. insight_perceive (situation)
2. insight_plan (for consequential or multi-step work)
3. insight_task open (keep task_id)
4. insight_experience after events/fixes
5. insight_task close with outcome + used_pattern_ids (only what was actually applied)

**Also:** insight_recall (fast only), insight_cycle (deep only), fabric index + insight_forge.
Distill the actual variable; do not force-fit novelty. Never paste raw credentials.
"""


def register(ctx) -> None:
    """Hermes plugin entrypoint."""
    try:
        import hermes_insight  # noqa: F401
    except ImportError:
        logger.warning(
            "hermes-insight plugin loaded but package missing — pip install hermes-insight"
        )
        return

    def _reg(schema, handler, emoji="◈"):
        ctx.register_tool(
            name=schema["name"],
            toolset="hermes_insight",
            schema=schema,
            handler=lambda args, **kw: handler(args or {}, **kw),
            description=schema.get("description", ""),
            emoji=emoji,
        )

    _reg(_CYCLE_SCHEMA, handle_insight_cycle)
    _reg(_INGEST_SCHEMA, handle_insight_ingest)
    _reg(_TREE_SCHEMA, handle_insight_ingest_tree)
    _reg(_MATCH_SCHEMA, handle_insight_match)
    _reg(_DISTILL_SCHEMA, handle_insight_distill)
    _reg(_FEEDBACK_SCHEMA, handle_insight_feedback)
    _reg(_STATS_SCHEMA, handle_insight_stats)
    _reg(_EVOLVE_SCHEMA, handle_insight_evolve)
    _reg(_INDEX_SERVER_SCHEMA, handle_insight_index_server)
    _reg(_INDEX_PATH_SCHEMA, handle_insight_index_path)
    _reg(_INDEX_CONN_SCHEMA, handle_insight_index_connections)
    _reg(_FABRIC_STATS_SCHEMA, handle_insight_fabric_stats)
    _reg(_FORGE_SCHEMA, handle_insight_forge)
    # Primary ability + experience path
    _reg(_PERCEIVE_SCHEMA, handle_insight_perceive, emoji="◈")
    _reg(_PLAN_SCHEMA, handle_insight_plan, emoji="◇")
    _reg(_OBSERVE_SCHEMA, handle_insight_observe, emoji="◉")
    _reg(_RECALL_SCHEMA, handle_insight_recall, emoji="◎")
    _reg(_EXPERIENCE_SCHEMA, handle_insight_experience, emoji="◉")
    _reg(_TASK_SCHEMA, handle_insight_task, emoji="▣")
    _reg(_CONNECT_SCHEMA, handle_insight_connect, emoji="⟷")
    _reg(_BOOTSTRAP_SCHEMA, handle_insight_bootstrap, emoji="🌱")
    _reg(_HYGIENE_SCHEMA, handle_insight_hygiene, emoji="🧹")
    _reg(_INGEST_MSG_SCHEMA, handle_insight_ingest_messages, emoji="☰")

    # optional prompt injection if host supports it
    if hasattr(ctx, "on_session_start_prompt") or hasattr(ctx, "register_system_prompt"):
        try:
            if hasattr(ctx, "register_system_prompt"):
                ctx.register_system_prompt(_SYSTEM_BLOCK)
        except Exception:
            logger.debug("system prompt register skipped", exc_info=True)

    if hasattr(ctx, "register_hook"):
        def _on_session_start(**_kwargs):
            return {"system_prompt_append": _SYSTEM_BLOCK}

        def _on_session_end(**kwargs):
            """Log only material session endings — not every completed chat turn."""
            try:
                import time as _time

                completed = bool(kwargs.get("completed"))
                interrupted = bool(kwargs.get("interrupted"))
                failed = bool(kwargs.get("failed"))
                if not (completed or interrupted or failed):
                    return None

                # Routine happy completes are noise. Keep failures/interrupts always.
                # Completed: at most one thin counter bump / hour — no episode flood.
                lat = _lattice()
                sid = str(kwargs.get("session_id") or "")
                key = f"{sid}:{kwargs.get('turn_id') or ''}"
                if lat.store.get_meta("last_auto_session_key", "") == key:
                    return None
                lat.store.set_meta("last_auto_session_key", key)

                platform = str(kwargs.get("platform") or "agent")
                model = str(kwargs.get("model") or "")
                now = _time.time()

                if completed and not interrupted and not failed:
                    # Counter only — experience growth comes from perceive/task/log=true
                    n = int(lat.store.get_meta("session_completed_count", "0") or 0) + 1
                    lat.store.set_meta("session_completed_count", str(n))
                    lat.store.set_meta("last_session_completed_at", str(now))
                    # rare light decay, never densify here
                    import random

                    if random.random() < 0.08:
                        lat.store.decay_fabric_noise(max_touch=40, min_age_days=0.5)
                    return None

                outcome = "interrupted" if interrupted else "failed"
                title = f"session {outcome} ({platform})"
                body = (
                    f"platform={platform}\nmodel={model}\n"
                    f"session={sid[:40]}\nturn={kwargs.get('turn_id') or ''}\n"
                    f"exit={kwargs.get('turn_exit_reason') or outcome}"
                )
                lat.experience(
                    title=title[:100],
                    body=body,
                    kind="episode",
                    outcome=outcome,
                    tags=["session", "auto", "material", platform.replace(" ", "_")[:24]],
                    confidence=0.55,
                    auto_connect=True,
                )
            except Exception:
                logger.debug("insight on_session_end auto-log failed", exc_info=True)
            return None

        for hook, fn in (
            ("on_session_start", _on_session_start),
            ("session_start", _on_session_start),
            ("on_session_end", _on_session_end),
            ("session_end", _on_session_end),
        ):
            try:
                ctx.register_hook(hook, fn)
            except Exception:
                pass

    if hasattr(ctx, "register_command"):
        def _slash(args_str: str = "") -> str:
            lat = _lattice()
            parts = (args_str or "").strip().split(maxsplit=1)
            sub = parts[0] if parts else "stats"
            if sub == "stats":
                return json.dumps(lat.stats(), indent=2)
            if sub == "bootstrap":
                return json.dumps(lat.bootstrap(), indent=2)
            if sub == "recall" and len(parts) > 1:
                return lat.recall(parts[1]).get("brief", "")
            if sub == "cycle" and len(parts) > 1:
                r = lat.cycle(parts[1])
                return r.brief
            if sub == "perceive" and len(parts) > 1:
                return lat.perceive(parts[1]).get("card", "")
            if sub == "plan" and len(parts) > 1:
                return lat.plan(parts[1]).get("card", "")
            if sub == "hygiene":
                return json.dumps(lat.hygiene(), indent=2)
            return "Usage: /insight stats|bootstrap|perceive <q>|plan <q>|recall <q>|cycle <q>|hygiene"

        try:
            ctx.register_command(
                "insight",
                handler=_slash,
                description="Hermes Insight — stats, bootstrap, recall, cycle",
            )
        except Exception:
            logger.debug("slash command registration skipped", exc_info=True)

    logger.info("hermes-insight plugin registered (v%s)", __plugin_version__)
