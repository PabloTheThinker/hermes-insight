"""CLI for Hermes Insight — agent-friendly JSON or human markdown."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List

from hermes_insight import __version__
from hermes_insight.harness import HermesInsight, default_db_path


def _print(data: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        if isinstance(data, str):
            print(data)
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hermes-insight",
        description=(
            "Superior pattern-processing harness for AI agents. "
            "Encode, match, link, distill, extrapolate, evolve."
        ),
    )
    p.add_argument("--version", action="version", version=f"hermes-insight {__version__}")
    p.add_argument(
        "--db",
        default=None,
        help="SQLite path (default: $HERMES_INSIGHT_DB or ~/.hermes-insight/insight.db)",
    )
    p.add_argument(
        "--agent",
        default=None,
        help="Multi-agent compartment id (separate lattice DB per agent)",
    )
    p.add_argument("--json", action="store_true", help="JSON output")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stats", help="Database counts and path")
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("ingest", help="Add a pattern to the catalogue")
    s.add_argument("title")
    s.add_argument("body")
    s.add_argument("--domain", default="general")
    s.add_argument("--kind", default="prototype")
    s.add_argument("--tag", action="append", default=[])
    s.add_argument("--confidence", type=float, default=0.6)
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("ingest-tree", help="Ingest a source tree (code-aware)")
    s.add_argument("root")
    s.add_argument("--glob", default="**/*.py")
    s.add_argument("-n", "--limit", type=int, default=80)
    s.add_argument("--domain", default="code")
    s.add_argument("--no-link", action="store_true")
    s.set_defaults(func=cmd_ingest_tree)

    s = sub.add_parser("match", help="Match query against the lattice")
    s.add_argument("query")
    s.add_argument("-n", "--limit", type=int, default=10)
    s.add_argument("--domain", default=None)
    s.set_defaults(func=cmd_match)

    s = sub.add_parser("search", help="FTS + hybrid search")
    s.add_argument("query")
    s.add_argument("-n", "--limit", type=int, default=15)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("cycle", help="Full cognitive cycle → brief")
    s.add_argument("query")
    s.add_argument("-o", "--observation", action="append", default=[])
    s.add_argument("--ingest", action="store_true", help="Also catalogue the query")
    s.add_argument("--domain", default="general")
    s.add_argument("--no-evolve", action="store_true")
    s.set_defaults(func=cmd_cycle)

    s = sub.add_parser("distill", help="Find the actual variable")
    s.add_argument("text")
    s.set_defaults(func=cmd_distill)

    s = sub.add_parser("extrapolate", help="Trajectory from observations")
    s.add_argument("observations", nargs="+")
    s.set_defaults(func=cmd_extrapolate)

    s = sub.add_parser("analogy", help="Cross-domain analogy map")
    s.add_argument("pattern_id")
    s.add_argument("target_domain")
    s.add_argument("-n", "--limit", type=int, default=5)
    s.set_defaults(func=cmd_analogy)

    s = sub.add_parser("feedback", help="Reinforce or weaken patterns")
    s.add_argument("pattern_ids", nargs="+")
    s.add_argument("--unhelpful", action="store_true")
    s.set_defaults(func=cmd_feedback)

    s = sub.add_parser("evolve", help="Run one evolution tick")
    s.add_argument("--no-decay", action="store_true")
    s.set_defaults(func=cmd_evolve)

    s = sub.add_parser("export", help="Export patterns as JSON")
    s.add_argument("-n", "--limit", type=int, default=1000)
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("register-agent", help="Register a multi-agent compartment")
    s.add_argument("agent_id")
    s.add_argument("--tier", default="worker", choices=["conductor", "worker", "client", "public", "lab"])
    s.add_argument("--display-name", default="")
    s.add_argument("--parent", default=None)
    s.set_defaults(func=cmd_register_agent)

    s = sub.add_parser("agents", help="List registered agents")
    s.set_defaults(func=cmd_agents)

    s = sub.add_parser("demo", help="Seed a tiny demo lattice and run a cycle")
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser(
        "index-server",
        help="Index server fabric: projects, files, metadata, connections (scrubbed)",
    )
    s.add_argument(
        "--root",
        action="append",
        default=None,
        help="Root path to scan (repeatable). Default: ~/projects, ~/hermes-agent, HERMES_HOME…",
    )
    s.add_argument("--max-projects", type=int, default=80)
    s.add_argument("--max-files", type=int, default=40, help="Max files per project")
    s.add_argument("--no-files", action="store_true")
    s.add_argument("--no-connections", action="store_true")
    s.add_argument("--no-processes", action="store_true")
    s.add_argument("--no-hermes", action="store_true")
    s.add_argument("--no-link", action="store_true")
    s.set_defaults(func=cmd_index_server)

    s = sub.add_parser("index-path", help="Index one project/directory/file into the lattice")
    s.add_argument("path")
    s.add_argument("--max-files", type=int, default=60)
    s.add_argument("--no-link", action="store_true")
    s.set_defaults(func=cmd_index_path)

    s = sub.add_parser("index-connections", help="Index listening ports / process connections only")
    s.set_defaults(func=cmd_index_connections)

    s = sub.add_parser("fabric-stats", help="Counts of fabric-tagged patterns in the lattice")
    s.set_defaults(func=cmd_fabric_stats)

    s = sub.add_parser(
        "forge",
        help="Forge new products from patterns: map, predict, transfer, invent, playbooks, watch",
    )
    s.add_argument(
        "--out",
        default=None,
        help="Output directory (default: <db-dir>/forged/<timestamp>)",
    )
    s.add_argument(
        "--only",
        default=None,
        help="Comma list: map,predict,transfer,invent,playbooks,watch",
    )
    s.add_argument("--no-synthesis", action="store_true", help="Do not write synthesis nodes back")
    s.set_defaults(func=cmd_forge)

    # Experience path (any agent)
    s = sub.add_parser("bootstrap", help="Seed starter agent-field patterns (empty DB)")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_bootstrap)

    s = sub.add_parser("hygiene", help="Decay fabric noise + densify structural links")
    s.add_argument("--no-decay", action="store_true")
    s.add_argument("--no-densify", action="store_true")
    s.set_defaults(func=cmd_hygiene)

    s = sub.add_parser(
        "perceive",
        help="Pattern recognition ability — lever + priors + action hint (primary)",
    )
    s.add_argument("situation")
    s.add_argument("-o", "--observation", action="append", default=[])
    s.add_argument("--domain", default=None)
    s.add_argument("-n", "--limit", type=int, default=8)
    s.add_argument("--log", action="store_true", help="Also catalogue as experience")
    s.add_argument("--deep", action="store_true", help="Force deep cycle if thin")
    s.set_defaults(func=cmd_perceive)

    s = sub.add_parser(
        "plan",
        help="Experience-grounded plan — ranked patterns, skills, tools, and workflow",
    )
    s.add_argument("situation")
    s.add_argument("-o", "--observation", action="append", default=[])
    s.add_argument("--domain", default=None)
    s.add_argument("-n", "--limit", type=int, default=5)
    s.set_defaults(func=cmd_plan)

    s = sub.add_parser(
        "observe",
        help="Record a typed event or capture a local environment snapshot",
    )
    s.add_argument("mode", choices=["event", "environment"])
    s.add_argument("summary", nargs="?", default="")
    s.add_argument("--event-type", default="observation")
    s.add_argument("--root", default=".")
    s.add_argument("--detail", action="append", default=[], help="Event detail as key=value")
    s.add_argument("--task-id", default=None)
    s.add_argument("--trace-id", default="")
    s.add_argument("--parent-event-id", default="")
    s.add_argument("--status", default="observed")
    s.add_argument("--outcome", default="")
    s.add_argument("--tool", default="")
    s.add_argument("--skill-id", default="")
    s.add_argument("--environment-snapshot-id", default="")
    s.add_argument("--trust-class", default="local")
    s.add_argument("--sensitivity", default="private")
    s.add_argument("--no-tools", action="store_true", help="Skip tool availability in snapshots")
    s.set_defaults(func=cmd_observe)

    s = sub.add_parser(
        "learn",
        help="Induce recurring workflows from distinct typed task traces",
    )
    s.add_argument("--min-support", type=int, default=3)
    s.add_argument("--min-steps", type=int, default=2)
    s.add_argument("--max-steps", type=int, default=4)
    s.add_argument("-n", "--limit", type=int, default=12)
    s.add_argument(
        "--materialize",
        action="store_true",
        help="Write reviewable sequence patterns; never writes or executes skills",
    )
    s.set_defaults(func=cmd_learn)

    s = sub.add_parser("recall", help="Fast pre-action recall (priors + experiences + hops)")
    s.add_argument("query")
    s.add_argument("-n", "--limit", type=int, default=8)
    s.add_argument("--domain", default=None)
    s.set_defaults(func=cmd_recall)

    s = sub.add_parser("experience", help="Log lived event/episode and auto-connect")
    s.add_argument("title")
    s.add_argument("body")
    s.add_argument("--kind", default="event", help="event|episode|task|sequence")
    s.add_argument("--task-id", default=None)
    s.add_argument("--outcome", default=None)
    s.add_argument("--tag", action="append", default=[])
    s.set_defaults(func=cmd_experience)

    s = sub.add_parser("task", help="Open or close a task episode")
    s.add_argument("action", choices=["open", "close"])
    s.add_argument("--name", default="task")
    s.add_argument("--goal", default="")
    s.add_argument("--task-id", default=None)
    s.add_argument("--outcome", default="done")
    s.add_argument("--summary", default="")
    s.add_argument(
        "--used-pattern",
        action="append",
        default=None,
        help="Pattern/skill id actually applied (repeatable; enables outcome learning)",
    )
    s.set_defaults(func=cmd_task)

    s = sub.add_parser("connect", help="Link two patterns or auto-connect free text")
    s.add_argument("left")
    s.add_argument("right", nargs="?", default=None)
    s.add_argument("--kind", default="similar")
    s.add_argument("--note", default="")
    s.set_defaults(func=cmd_connect)

    return p


def _lattice(args: argparse.Namespace) -> HermesInsight:
    return HermesInsight(
        db_path=args.db,
        agent_id=getattr(args, "agent", None),
    )


def cmd_stats(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.stats(), as_json=True)
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    pat = lat.ingest(
        args.title,
        args.body,
        domain=args.domain,
        kind=args.kind,
        tags=args.tag,
        confidence=args.confidence,
    )
    _print(pat.to_dict(), as_json=True)
    return 0


def cmd_ingest_tree(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    result = lat.ingest_tree(
        args.root,
        glob=args.glob,
        limit=args.limit,
        domain=args.domain,
        link=not args.no_link,
    )
    _print(result, as_json=True)
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.match(args.query, limit=args.limit, domain=args.domain), as_json=True)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    pats = lat.search(args.query, limit=args.limit)
    _print([p.to_dict() for p in pats], as_json=True)
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    report = lat.cycle(
        args.query,
        observations=args.observation,
        ingest_query=args.ingest,
        domain=args.domain,
        evolve=not args.no_evolve,
    )
    if args.json:
        _print(report.to_dict(), as_json=True)
    else:
        print(report.brief)
    return 0


def cmd_distill(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.distill(args.text), as_json=True)
    return 0


def cmd_extrapolate(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.extrapolate(args.observations), as_json=True)
    return 0


def cmd_analogy(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.analogy(args.pattern_id, args.target_domain, limit=args.limit), as_json=True)
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.feedback(args.pattern_ids, helpful=not args.unhelpful), as_json=True)
    return 0


def cmd_evolve(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.evolve(decay=not args.no_decay), as_json=True)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.export_patterns(limit=args.limit), as_json=True)
    return 0


def cmd_register_agent(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(
        lat.register_agent(
            args.agent_id,
            tier=args.tier,
            display_name=args.display_name,
            parent_id=args.parent,
        ),
        as_json=True,
    )
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.list_agents(), as_json=True)
    return 0


def cmd_index_server(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    result = lat.index_server(
        roots=args.root,
        include_files=not args.no_files,
        include_connections=not args.no_connections,
        include_processes=not args.no_processes,
        include_hermes=not args.no_hermes,
        max_files_per_project=args.max_files,
        max_projects=args.max_projects,
        link=not args.no_link,
    )
    _print(result, as_json=True)
    return 0


def cmd_index_path(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(
        lat.index_path(args.path, max_files=args.max_files, link=not args.no_link),
        as_json=True,
    )
    return 0


def cmd_index_connections(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.index_connections(), as_json=True)
    return 0


def cmd_fabric_stats(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.fabric_stats(), as_json=True)
    return 0


def cmd_forge(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    only = None
    if args.only:
        only = [x.strip() for x in args.only.split(",") if x.strip()]
    result = lat.forge(
        out_dir=args.out,
        write_synthesis=not args.no_synthesis,
        products=only,
    )
    _print(result, as_json=True)
    # human pointer
    if not args.json and result.get("run_dir"):
        print(f"\nForged → {result['run_dir']}", file=sys.stderr)
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(lat.bootstrap(force=bool(args.force)), as_json=True)
    return 0


def cmd_hygiene(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(
        lat.hygiene(decay=not args.no_decay, densify=not args.no_densify),
        as_json=True,
    )
    return 0


def cmd_perceive(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    pack = lat.perceive(
        args.situation,
        observations=args.observation,
        domain=args.domain,
        limit=args.limit,
        log_experience=bool(args.log),
        deep=bool(args.deep),
    )
    if args.json:
        _print(pack, as_json=True)
    else:
        print(pack.get("card") or pack.get("brief") or json.dumps(pack, indent=2))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    pack = lat.plan(
        args.situation,
        observations=args.observation,
        domain=args.domain,
        limit=args.limit,
    )
    if args.json:
        _print(pack, as_json=True)
    else:
        print(pack.get("card") or json.dumps(pack, indent=2))
    return 0


def cmd_observe(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    if args.mode == "environment":
        result = lat.snapshot_environment(args.root, include_tools=not args.no_tools)
    else:
        details = {}
        for index, item in enumerate(args.detail):
            if "=" in item:
                key, value = item.split("=", 1)
                details[key.strip() or f"detail_{index + 1}"] = value.strip()
            else:
                details[f"detail_{index + 1}"] = item
        result = lat.record_event(
            args.event_type,
            args.summary,
            details=details,
            trace_id=args.trace_id,
            parent_event_id=args.parent_event_id,
            task_id=args.task_id,
            status=args.status,
            outcome=args.outcome,
            tool=args.tool,
            skill_id=args.skill_id,
            environment_snapshot_id=args.environment_snapshot_id,
            trust_class=args.trust_class,
            sensitivity=args.sensitivity,
        )
    _print(result, as_json=True)
    return 0 if result.get("success") else 1


def cmd_learn(args: argparse.Namespace) -> int:
    result = _lattice(args).learn(
        min_support=args.min_support,
        min_steps=args.min_steps,
        max_steps=args.max_steps,
        limit=args.limit,
        materialize=bool(args.materialize),
    )
    _print(result, as_json=True)
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    pack = lat.recall(args.query, limit=args.limit, domain=args.domain)
    if args.json:
        _print(pack, as_json=True)
    else:
        print(pack.get("brief") or json.dumps(pack, indent=2))
    return 0


def cmd_experience(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(
        lat.experience(
            args.title,
            args.body,
            kind=args.kind,
            task_id=args.task_id,
            outcome=args.outcome,
            tags=args.tag,
        ),
        as_json=True,
    )
    return 0


def cmd_task(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    if args.action == "open":
        _print(
            lat.open_task(args.name, goal=args.goal, task_id=args.task_id),
            as_json=True,
        )
    else:
        _print(
            lat.close_task(
                args.task_id,
                outcome=args.outcome,
                summary=args.summary,
                used_pattern_ids=args.used_pattern,
            ),
            as_json=True,
        )
    return 0


def cmd_connect(args: argparse.Namespace) -> int:
    lat = _lattice(args)
    _print(
        lat.connect(args.left, args.right, kind=args.kind, note=args.note),
        as_json=True,
    )
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    import tempfile
    from pathlib import Path

    # isolated temp db unless user passed --db
    if not args.db:
        tmp = Path(tempfile.mkdtemp(prefix="hermes-insight-demo-")) / "demo.db"
        args.db = str(tmp)

    lat = _lattice(args)
    seeds = [
        (
            "retry with jitter",
            "Transient network failures resolve when clients retry with exponential backoff and jitter.",
            "code",
            "rule",
            ["retry", "backoff", "jitter", "network", "transient"],
        ),
        (
            "circuit breaker",
            "When downstream error rate spikes, open the circuit to fail fast and protect the caller.",
            "code",
            "rule",
            ["circuit", "breaker", "fail-fast", "downstream", "error-rate"],
        ),
        (
            "alert fatigue",
            "Too many low-signal alerts train operators to ignore pages; severity inflation follows.",
            "system",
            "prototype",
            ["alert", "fatigue", "noise", "oncall", "severity"],
        ),
        (
            "social masking scripts",
            "Explicit pattern catalogues of social rules enable real-time scripting at high cognitive cost.",
            "social",
            "prototype",
            ["masking", "scripts", "social", "rules", "cognitive-load"],
        ),
        (
            "cache stampede",
            "Expired hot keys cause thundering herds; soft TTL and singleflight coalesce recompute.",
            "code",
            "rule",
            ["cache", "stampede", "ttl", "singleflight", "thundering-herd"],
        ),
    ]
    for title, body, domain, kind, tags in seeds:
        lat.ingest(title, body, domain=domain, kind=kind, tags=tags, confidence=0.75)

    report = lat.cycle(
        "API timeouts keep spiking and on-call is drowning in pages",
        observations=[
            "error rate up after deploy",
            "retries amplified load on the dependency",
            "pages every few minutes, many duplicates",
        ],
        domain="system",
        evolve=True,
    )
    if args.json:
        _print(report.to_dict(), as_json=True)
    else:
        print(report.brief)
        print(f"\n[demo db: {args.db}]")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
