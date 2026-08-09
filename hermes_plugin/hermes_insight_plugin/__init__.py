"""Plugin entry placeholder.

Wire `register(ctx)` to your installed Hermes plugin API, for example:

    def register(ctx):
        from hermes_insight import HermesInsight
        from pathlib import Path
        import os

        def db_path():
            home = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
            return str(Path(home) / "memories" / "hermes-insight.db")

        def pattern_cycle(args, **kwargs):
            lat = HermesInsight(db_path=db_path())
            report = lat.cycle(
                args.get("query", ""),
                observations=args.get("observations") or [],
                ingest_query=bool(args.get("ingest", False)),
                domain=args.get("domain", "general"),
            )
            return report.to_json()

        # ctx.register_tool(name="pattern_cycle", schema=..., handler=pattern_cycle)
        # Exact register signature: see Hermes docs for your version.

See README.md in this folder.
"""

from __future__ import annotations

__plugin_name__ = "hermes_insight"
__plugin_version__ = "0.1.0"


def register(ctx=None):  # pragma: no cover - host-specific
    """Called by Hermes plugin loader when fully implemented."""
    return {
        "name": __plugin_name__,
        "version": __plugin_version__,
        "status": "skeleton",
        "message": "Install hermes-insight package and wire tools per Hermes plugin API.",
    }
