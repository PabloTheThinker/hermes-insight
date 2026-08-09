"""Native Hermes Agent plugin — Hermes Insight tools + prompt stance.

Install (user plugin):
  mkdir -p \"$HERMES_HOME/plugins\"
  cp -R hermes_plugin/hermes_insight_plugin \"$HERMES_HOME/plugins/hermes-insight\"
  # enable in config.yaml:
  # plugins:
  #   enabled: [..., hermes-insight]
  #   entries:
  #     hermes-insight:
  #       agent_id: ilo   # optional multi-agent compartment

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
__plugin_version__ = "0.2.0"


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


def _lattice():
    from hermes_insight import HermesInsight

    return HermesInsight(db_path=_db_path(), agent_id=_agent_id())


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


_SYSTEM_BLOCK = """## Hermes Insight
You have structural pattern-processing tools (`insight_*`).
Prefer insight_cycle when diagnosing multi-factor systems, architectures, or recurring failures.
Distill the actual variable; do not force-fit novelty; reinforce patterns that paid rent via insight_feedback.
Catalogue durable structures with insight_ingest / insight_ingest_tree.
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

    # optional prompt injection if host supports it
    if hasattr(ctx, "register_hook"):
        def _prompt_block(**_kwargs):
            return _SYSTEM_BLOCK

        # Some Hermes versions use system_prompt hooks; safe no-op if unsupported name
        for hook in ("on_session_start",):
            try:
                ctx.register_hook(hook, lambda **kw: None)
            except Exception:
                pass

    if hasattr(ctx, "register_command"):
        def _slash(args_str: str = "") -> str:
            lat = _lattice()
            parts = (args_str or "").strip().split(maxsplit=1)
            sub = parts[0] if parts else "stats"
            if sub == "stats":
                return json.dumps(lat.stats(), indent=2)
            if sub == "cycle" and len(parts) > 1:
                r = lat.cycle(parts[1])
                return r.brief
            return "Usage: /insight stats | /insight cycle <query>"

        try:
            ctx.register_command(
                "insight",
                handler=_slash,
                description="Hermes Insight — stats or cycle",
            )
        except Exception:
            logger.debug("slash command registration skipped", exc_info=True)

    logger.info("hermes-insight plugin registered (v%s)", __plugin_version__)
