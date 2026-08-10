#!/usr/bin/env python3
"""Intense production E2E for Hermes Insight — agent-field stage.

Exercises: clean DB → seed agent ontology → fabric index → connections →
multi-agent isolation → cycle → forge → feedback → export scrub check.
Exits non-zero on any gate failure.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from hermes_insight import HermesInsight, __version__
from hermes_insight.scrub import scrub_text


GATES: list[tuple[str, bool, str]] = []


def gate(name: str, ok: bool, detail: str = "") -> None:
    GATES.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print(f"=== Hermes Insight production E2E v{__version__} ===")
    root = Path(tempfile.mkdtemp(prefix="hinsight-e2e-"))
    db = root / "prod.db"
    out = root / "forged"
    home = Path.home()
    hermes = home / ".hermes"
    projects = home / "projects"
    agent_src = home / "hermes-agent"
    if not agent_src.exists():
        # optional override for CI / unusual layouts
        import os

        alt = os.environ.get("HERMES_AGENT_SRC", "").strip()
        agent_src = Path(alt) if alt else agent_src

    # --- 1 fresh harness ---
    lat = HermesInsight(db_path=str(db), agent_id="e2e-conductor", agent_tier="conductor")
    gate("boot", lat.stats()["version"] == __version__, lat.stats()["version"])

    # --- 2 seed agent-field knowledge ---
    seeds = [
        (
            "rule:single-consumer-credential",
            "Only one agent long-poll consumer may hold a bot credential at a time.",
            "agent",
            "rule",
            ["credential", "consumer", "agent", "isolation"],
        ),
        (
            "rule:skill-model-routing",
            "Heavy coding skills should route to a coding model; cheap classify skills to a fast small model.",
            "model",
            "rule",
            ["skill", "model", "routing", "inference", "eval"],
        ),
        (
            "rule:compartment-no-client-leak",
            "Client agent memory and skills must never mix into house conductor compartment.",
            "multi_agent",
            "rule",
            ["compartment", "multi_agent", "client", "isolation", "memory"],
        ),
        (
            "proto:managed-ai-employee",
            "A managed AI employee is profile + model route + skill pack + weekly owner brief.",
            "agent",
            "prototype",
            ["employee", "profile", "skill", "model", "brief"],
        ),
    ]
    for title, body, domain, kind, tags in seeds:
        lat.ingest(title, body, domain=domain, kind=kind, tags=tags, confidence=0.9)
    gate("seed", lat.stats()["patterns"] >= 4, str(lat.stats()["patterns"]))

    # --- 3 multi-agent isolation ---
    client = HermesInsight(db_path=str(root / "client.db"), agent_id="e2e-client", agent_tier="client")
    client.ingest(
        "client-only-secret-pattern",
        "client payroll notes must stay compartmented",
        domain="agent",
        tags=["client", "private"],
    )
    house_titles = {p["title"] for p in lat.export_patterns()}
    gate("multi_agent_isolation", "client-only-secret-pattern" not in house_titles)

    # --- 4 fabric index (bounded production roots) ---
    roots = [p for p in (hermes, projects / "hermes-insight", agent_src) if p.exists()]
    rep = lat.index_server(
        roots=[str(r) for r in roots],
        include_files=True,
        include_connections=True,
        include_processes=True,
        include_hermes=True,
        max_projects=25,
        max_files_per_project=12,
    )
    gate("index_patterns", rep["stats"]["patterns"] >= 30, str(rep["stats"]["patterns"]))
    gate("index_projects_or_agent_field", rep.get("projects_found", 0) >= 1 or rep["stats"]["patterns"] >= 50,
         f"projects={rep.get('projects_found')} patterns={rep['stats']['patterns']}")
    gate("index_connections", rep.get("connections_found", 0) >= 1, str(rep.get("connections_found")))
    fs = lat.fabric_stats()
    kinds = fs.get("by_kind") or {}
    gate(
        "agent_field_nodes",
        any(k in kinds for k in ("skill", "plugin", "profile", "model", "tool", "hermes")),
        str({k: kinds.get(k) for k in ("skill", "plugin", "profile", "model", "tool", "hermes", "listen", "project")}),
    )

    # --- 5 production cycles ---
    cases = [
        (
            "Two agent workers share one bot credential and long-poll conflicts fire",
            ["profile isolation missing", "duplicate consumers"],
            "agent",
            {"credential", "consumer", "token", "isolation", "agent", "conflict", "compartment"},
        ),
        (
            "How should multi-agent profiles share a model route without leaking client skills?",
            ["default model route", "skill packs per profile"],
            "multi_agent",
            {"skill", "model", "agent", "profile", "compartment", "multi_agent", "memory", "routing"},
        ),
        (
            "Coding skill burns expensive model tokens on trivial classify tasks",
            ["need routing matrix", "eval gate"],
            "model",
            {"model", "skill", "routing", "inference", "eval", "tool"},
        ),
    ]
    for q, obs, domain, ok_levers in cases:
        r = lat.cycle(q, observations=obs, domain=domain, evolve=True)
        lever = (r.distillation.actual_variable if r.distillation else "") or ""
        top = r.matches[0].score if r.matches else 0.0
        gate(f"cycle_lever:{domain}", lever in ok_levers or top >= 0.12, f"lever={lever} top={top:.3f}")
        gate(f"cycle_brief:{domain}", "agent-field" in r.brief or "Hermes Insight" in r.brief)
        gate(f"cycle_match:{domain}", bool(r.matches) and top >= 0.08, f"top={top:.3f}")

    # --- 5b experience layer (any-agent path) ---
    boot = HermesInsight(db_path=str(root / "fresh.db"))
    bs = boot.bootstrap()
    gate("bootstrap_seed", bs.get("seeded", 0) >= 8, str(bs))
    rp = boot.recall("two workers share one bot credential and long-poll conflicts")
    gate("recall_brief", "Insight recall" in (rp.get("brief") or ""), rp.get("lever", ""))
    gate("recall_hits", bool(rp.get("matches") or rp.get("experiences")), str(len(rp.get("matches") or [])))
    opened = boot.open_task("e2e-conflict", goal="dual consumer credential fight")
    gate("task_open", opened.get("success") is True and bool(opened.get("task_id")), str(opened.get("task_id")))
    tid = opened.get("task_id") or ""
    ex = boot.experience(
        "409 conflict observed",
        "getUpdates conflict while second gateway still polling same bot token",
        task_id=tid,
        tags=["gateway", "telegram"],
    )
    gate("experience_log", ex.get("success") is True, ex.get("one_liner", ""))
    gate("experience_autoconnnect", isinstance(ex.get("connected"), list), str(len(ex.get("connected") or [])))
    closed = boot.close_task(tid, outcome="fixed", summary="single consumer restored")
    gate("task_close", closed.get("success") is True, closed.get("outcome", ""))
    perc = boot.perceive(
        "two gateway workers share one bot credential and long-poll conflicts",
        observations=["409 conflict"],
        domain="agent",
    )
    gate("perceive_card", "Pattern recognition" in (perc.get("card") or ""), perc.get("lever", ""))
    gate("perceive_hint", bool(perc.get("action_hint")), str(perc.get("action_hint", ""))[:80])
    gate(
        "perceive_structural_top",
        bool(perc.get("matches"))
        and (
            "credential" in (perc["matches"][0].get("title") or "").lower()
            or "consumer" in (perc["matches"][0].get("title") or "").lower()
            or float(perc["matches"][0].get("score") or 0) >= 0.2
        ),
        str((perc.get("matches") or [{}])[0].get("title")),
    )
    # plugin experience handlers
    try:
        import importlib.util
        import os

        plug = Path(__file__).resolve().parents[1] / "hermes_plugin" / "hermes_insight_plugin" / "__init__.py"
        spec = importlib.util.spec_from_file_location("hi_plug_exp", plug)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        os.environ["HERMES_INSIGHT_DB"] = str(root / "fresh.db")
        spec.loader.exec_module(mod)
        rr = json.loads(mod.handle_insight_recall({"query": "bot credential conflict"}))
        gate("plugin_recall", rr.get("success") is True and "brief" in (rr.get("data") or {}))
        pr = json.loads(
            mod.handle_insight_perceive(
                {"situation": "bot credential conflict dual consumer", "domain": "agent"}
            )
        )
        gate("plugin_perceive", pr.get("success") is True and "card" in (pr.get("data") or {}))
    except Exception as exc:  # noqa: BLE001
        gate("plugin_recall", False, str(exc))
        gate("plugin_perceive", False, str(exc))

    # --- 6 forge products ---
    fr = lat.forge(out_dir=str(out), write_synthesis=True)
    run = Path(fr["run_dir"])
    needed = [
        "01-orientation-map.md",
        "02-prediction-board.md",
        "03-transfer-pack.md",
        "04-invention-seeds.md",
        "05-action-playbooks.md",
        "06-watch-edges.md",
        "README.md",
    ]
    for name in needed:
        p = run / name
        gate(f"forge_file:{name}", p.exists() and p.stat().st_size > 200, f"bytes={p.stat().st_size if p.exists() else 0}")
    invent = (run / "04-invention-seeds.md").read_text(encoding="utf-8")
    gate("forge_agent_voice", any(w in invent.lower() for w in ("agent", "model", "skill", "multi-agent", "profile")))
    gate("forge_synthesis", len(fr.get("synthesis_ids") or []) >= 1, str(fr.get("synthesis_ids")))

    # --- 7 feedback loop ---
    if lat.export_patterns():
        pid = lat.export_patterns()[0]["id"]
        before = lat.get(pid).strength if lat.get(pid) else 0
        lat.feedback([pid], helpful=True)
        after = lat.get(pid).strength if lat.get(pid) else 0
        gate("feedback_reinforce", after >= before, f"{before}->{after}")

    # --- 8 scrub / no secret dump in forge outputs ---
    blob = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in run.glob("*.md"))
    bad = [
        r.findall(blob)
        for r in (
            re.compile(r"sk-[A-Za-z0-9]{10,}"),
            re.compile(r"ghp_[A-Za-z0-9]{10,}"),
            re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        )
    ]
    gate("scrub_no_private_keys", not any(bad))
    # ensure scrubber works on synthetic leak
    synthetic_key = "sk-" + "abcdefghijklmnopqrstuv"
    dirty = f"api_key={synthetic_key} password=supersecret path=/Users/someone/x"
    clean = scrub_text(dirty)
    gate(
        "scrub_function",
        synthetic_key not in clean and "supersecret" not in clean,
        clean[:120],
    )

    # --- 9 plugin handler smoke ---
    try:
        import importlib.util
        import os

        plug = Path(__file__).resolve().parents[1] / "hermes_plugin" / "hermes_insight_plugin" / "__init__.py"
        spec = importlib.util.spec_from_file_location("hi_plug_e2e", plug)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        os.environ["HERMES_INSIGHT_DB"] = str(db)
        spec.loader.exec_module(mod)
        st = json.loads(mod.handle_insight_stats({}))
        cy = json.loads(mod.handle_insight_cycle({"query": "agent skill model routing", "domain": "agent"}))
        fo = json.loads(mod.handle_insight_forge({"products": ["map", "invent"], "out_dir": str(root / "plug-forge")}))
        gate("plugin_stats", st.get("success") is True)
        gate("plugin_cycle", cy.get("success") is True and "brief" in (cy.get("data") or {}))
        gate("plugin_forge", fo.get("success") is True)
    except Exception as exc:  # noqa: BLE001
        gate("plugin_smoke", False, str(exc))

    # --- 10 export serializable ---
    data = lat.export_patterns(limit=50)
    json.dumps(data)
    gate("export_json", isinstance(data, list) and len(data) >= 10, str(len(data)))

    # summary
    failed = [g for g in GATES if not g[1]]
    passed = [g for g in GATES if g[1]]
    summary = {
        "version": __version__,
        "tmpdir": str(root),
        "passed": len(passed),
        "failed": len(failed),
        "fail_names": [f[0] for f in failed],
        "stats": lat.stats(),
        "fabric_by_kind": kinds,
        "forge_run": str(run),
    }
    summary_path = root / "E2E-SUMMARY.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # durable copy under project (paths scrubbed for public tree)
    durable = Path(__file__).resolve().parents[1] / "docs" / "E2E-PRODUCTION-LAST.json"
    pub = dict(summary)
    pub["tmpdir"] = "$TMP/hinsight-e2e"
    if isinstance(pub.get("stats"), dict):
        pub["stats"] = dict(pub["stats"])
        pub["stats"]["db_path"] = "$TMP/hinsight-e2e/prod.db"
    pub["forge_run"] = "$TMP/hinsight-e2e/forged"
    durable.write_text(json.dumps(pub, indent=2) + "\n", encoding="utf-8")
    print("=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"durable={durable}")
    # keep tree for inspection
    keep = Path(__file__).resolve().parents[1] / ".e2e-last"
    if keep.exists():
        shutil.rmtree(keep)
    shutil.copytree(root, keep)
    print(f"artifacts={keep}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
