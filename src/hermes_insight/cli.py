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
