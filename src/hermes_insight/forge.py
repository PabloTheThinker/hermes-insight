"""Pattern Forge — turn catalogue + connections into *new* human-usable products.

People don't collect patterns for sport. They use them to:

1. **Orient** — map the field (what's connected to what)
2. **Predict** — see trajectory before the break
3. **Transfer** — carry a structure from domain A → B (analogy)
4. **Invent** — recombine clusters into something that didn't exist
5. **Act** — distill levers into playbooks / standing moves
6. **Watch** — track hubs and novelty edges

Forge reads the lattice and emits finished artifacts (markdown + synthesis nodes).
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from hermes_insight.cross_domain import analogy_map, auto_link
from hermes_insight.distill import distill
from hermes_insight.extrapolate import extrapolate
from hermes_insight.features import extract_features, jaccard
from hermes_insight.match import build_idf, expand_query_features, match_patterns
from hermes_insight.models import Domain, Pattern, PatternKind
from hermes_insight.scrub import scrub_text


@dataclass
class ForgeBundle:
    """One forge run — multiple products from the same lattice state."""

    created_at: str
    db_path: str
    products: Dict[str, str] = field(default_factory=dict)
    synthesis_ids: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "db_path": self.db_path,
            "products": {k: (v[:200] + "…" if len(v) > 200 else v) for k, v in self.products.items()},
            "product_paths": list(self.products.keys()),
            "synthesis_ids": self.synthesis_ids,
            "stats": self.stats,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _degree_map(insight: Any, limit_patterns: int = 3000) -> Dict[str, int]:
    deg: Dict[str, int] = defaultdict(int)
    for p in insight.store.all_patterns(limit=limit_patterns):
        for lk in insight.store.links_for(p.id, limit=40):
            deg[lk.source_id] += 1
            deg[lk.target_id] += 1
    return deg


def _by_fabric(patterns: Sequence[Pattern]) -> Dict[str, List[Pattern]]:
    out: Dict[str, List[Pattern]] = defaultdict(list)
    for p in patterns:
        kind = (p.metadata or {}).get("fabric") or "other"
        out[str(kind)].append(p)
    return out


def build_orientation_map(insight: Any) -> str:
    """Product 1 — Orient: the agent field as a usable map."""
    from hermes_insight.ontology import FORGE_VOICE

    patterns = insight.store.all_patterns(limit=5000)
    by = _by_fabric(patterns)
    deg = _degree_map(insight)
    voice = FORGE_VOICE

    lines = [
        f"# {voice['map_title']}",
        "",
        f"_{voice['map_blurb']}_",
        "",
        f"_Forged {_now_iso()}. Agent-field map: agents · models · tools · skills · endpoints._",
        "",
        "## Terrain counts",
        "",
    ]
    for k in sorted(by.keys(), key=lambda x: -len(by[x])):
        lines.append(f"- **{k}**: {len(by[k])}")
    lines += ["", "## Leverage hubs (highest link degree)", ""]
    hubs = sorted(deg.items(), key=lambda kv: -kv[1])[:15]
    for pid, d in hubs:
        p = insight.store.get_pattern(pid)
        if not p:
            continue
        fab = (p.metadata or {}).get("fabric", "")
        lines.append(f"- **{p.title}** · degree={d} · {fab or p.domain.value}/{p.kind.value}")

    lines += ["", "## Runtime endpoints (agent-stack listens)", ""]
    for p in by.get("listen") or []:
        lines.append(f"- **{p.title}** — {p.body[:160]}")

    lines += ["", "## Agent identities (profiles)", ""]
    for p in (by.get("profile") or [])[:20]:
        lines.append(f"- **{p.title}** · {p.domain.value}")

    lines += ["", "## Models", ""]
    for p in (by.get("model") or [])[:15]:
        lines.append(f"- **{p.title}**")

    lines += ["", "## Skills (sample)", ""]
    for p in (by.get("skill") or [])[:25]:
        lines.append(f"- **{p.title}**")

    lines += ["", "## Plugins / tool providers", ""]
    for p in (by.get("plugin") or [])[:20]:
        lines.append(f"- **{p.title}**")

    lines += ["", "## Code surfaces agents work in (top projects)", ""]
    proj = by.get("project") or []
    proj_ranked = sorted(proj, key=lambda p: deg.get(p.id, 0), reverse=True)[:20]
    for p in proj_ranked:
        langs = ",".join((p.metadata or {}).get("languages") or []) or "?"
        lines.append(f"- **{p.title}** · deg={deg.get(p.id, 0)} · langs={langs}")

    hermes = by.get("hermes") or []
    if hermes:
        lines += ["", "## Agent harness runtime", "", hermes[0].body[:1200]]

    lines += [
        "",
        "## How to use this map (agent ops)",
        "",
        "1. Start at **hubs** — agent/product surfaces where changes ripple.",
        "2. Pair each **listen:** with the agent or plugin that owns it.",
        "3. Trace **agent → model (USES_MODEL)** and **harness → skill (HAS_SKILL)**.",
        "4. Keep client agent compartments off the house agent graph.",
        "5. Re-forge after indexing so the fleet map tracks reality.",
        "",
    ]
    return "\n".join(lines)


def build_prediction_board(insight: Any) -> str:
    """Product 2 — Predict: trajectories in the agent fleet / model routes."""
    from hermes_insight.ontology import FORGE_VOICE

    patterns = insight.store.all_patterns(limit=5000)
    by = _by_fabric(patterns)
    listens = by.get("listen") or []
    projects = by.get("project") or []
    voice = FORGE_VOICE

    observations = []
    for p in listens:
        observations.append(f"endpoint:{p.title}: {p.body[:120]}")
    for p in (by.get("skill") or [])[:15]:
        observations.append(f"skill-present:{p.title}")
    for p in (by.get("model") or [])[:8]:
        observations.append(f"model-route:{p.title}")
    for p in (by.get("profile") or [])[:8]:
        observations.append(f"agent-identity:{p.title}")

    deg = _degree_map(insight)
    busy = sorted(projects, key=lambda p: deg.get(p.id, 0), reverse=True)[:8]
    for p in busy:
        observations.append(f"dense agent-code surface {p.title} (deg={deg.get(p.id, 0)})")

    traj = extrapolate(
        observations[:20] or ["sparse agent field"],
        matches=match_patterns(
            " ".join(observations[:10]),
            expand_query_features(extract_features(" ".join(observations[:10]))),
            patterns,
            limit=8,
            idf=build_idf(patterns),
        ),
        title="forge-agent-prediction",
    )

    blob = "\n".join(observations[:15])
    d = distill(
        blob + "\n agent model tool skill context memory multi_agent",
        matches=match_patterns(
            blob,
            expand_query_features(extract_features(blob)),
            patterns,
            limit=10,
            idf=build_idf(patterns),
        ),
    )

    lines = [
        f"# {voice['predict_title']}",
        "",
        f"_{voice['predict_blurb']}_",
        "",
        "## Controlling variable",
        f"- **Lever:** `{d.actual_variable}`",
        f"- **Confidence:** {d.confidence:.2f}",
        f"- **Principle:** {d.principle}",
        f"- **Action:** {d.actionable}",
        "",
        "## Trajectory",
        f"- **Direction:** {traj.direction} (conf {traj.confidence:.2f})",
        f"- **Next expected:** {traj.next_expected}",
        "",
        "### Evidence steps",
    ]
    for s in traj.steps[:12]:
        lines.append(f"- {s}")
    lines += ["", "### Risks", ""]
    for r in traj.risks:
        lines.append(f"- {r}")

    lines += [
        "",
        "## Agent-field watchlist",
        "",
        "1. **Credential / single-consumer** — two agents sharing one bot token or OAuth.",
        "2. **Model route drift** — default model changes without eval gate.",
        "3. **Skill sprawl** — many skills, few HAS_SKILL links to real agents.",
        "4. **Unowned endpoints** — listen nodes with no agent/plugin owner.",
        "5. **Context overflow** — rising session length without compression policy.",
        "6. **Cross-compartment leak risk** — client agent data patterns near house agents.",
        "",
        "## Decision prompts",
        "",
        "- If lever is `credential`/`agent`/`compartment`: isolation before new tools.",
        "- If lever is `model`/`inference`: freeze route + add eval before prompt churn.",
        "- If lever is `tool`/`skill`: consolidate capability graph before new agents.",
        "",
    ]
    return "\n".join(lines)


def build_transfer_pack(insight: Any) -> str:
    """Product 3 — Transfer: structural analogies across projects/domains."""
    patterns = insight.store.all_patterns(limit=5000)
    by = _by_fabric(patterns)
    projects = by.get("project") or []
    listens = by.get("listen") or []
    deg = _degree_map(insight)

    lines = [
        "# Transfer pack — analogy product",
        "",
        "_People use patterns by carrying a working shape from one domain into another._",
        "",
        "## Cross-project structural rhymes",
        "",
    ]

    # Compare top hubs pairwise for feature jaccard
    hubs = sorted(projects, key=lambda p: deg.get(p.id, 0), reverse=True)[:12]
    pairs: List[Tuple[float, Pattern, Pattern, List[str]]] = []
    for i, a in enumerate(hubs):
        for b in hubs[i + 1 :]:
            shared = sorted(set(x.lower() for x in a.features) & set(x.lower() for x in b.features))
            score = jaccard(a.features, b.features)
            if score >= 0.08 and len(shared) >= 3:
                pairs.append((score, a, b, shared[:12]))
    pairs.sort(key=lambda t: t[0], reverse=True)
    if not pairs:
        lines.append("_No strong project–project feature rhymes yet — re-index with more file depth._")
    for score, a, b, shared in pairs[:12]:
        lines.append(
            f"- **{a.title}** ↔ **{b.title}** · j={score:.2f} · shared: {', '.join(shared[:8])}"
        )
        lines.append(
            f"  - *Transfer idea:* treat a fix/pattern that worked on `{a.title.replace('project:', '')}` "
            f"as a candidate playbook for `{b.title.replace('project:', '')}`."
        )

    lines += ["", "## Listen → project ownership transfers", ""]
    for lp in listens:
        proc = (lp.metadata or {}).get("process") or lp.title.replace("listen:", "")
        # find projects whose name tokens hit process
        hits = []
        for proj in projects:
            name = (proj.metadata or {}).get("name") or proj.title
            if any(tok and tok in str(name).lower() for tok in str(proc).lower().split("-") if len(tok) > 2):
                hits.append(proj.title)
            if str(proc).lower() in proj.body.lower():
                hits.append(proj.title)
        hits = list(dict.fromkeys(hits))[:5]
        if hits:
            lines.append(f"- **{lp.title}** likely owned by / transfers to: {', '.join(hits)}")
        else:
            lines.append(f"- **{lp.title}** — *unowned in lattice* → invent an owner project or ops runbook.")

    lines += [
        "",
        "## Domain bridges worth exploiting",
        "",
        "| From | To | Why |",
        "|------|----|-----|",
        "| listen isolation (single consumer) | multi-agent lattices | same shape: one credential → one compartment |",
        "| project hub density | revenue products | attention mass often marks where value already concentrates |",
        "| hermes plugin surface | specialized agents | factory pattern: package what works into profile seats |",
        "| code retry/circuit rules | ops listen health | failure modes rhyme across software and process planes |",
        "",
        "## One transfer challenge",
        "",
        "Pick the strongest rhyme above and write a 5-line playbook that works in **both** projects without renaming nouns until the last line.",
        "",
    ]
    return "\n".join(lines)


def build_invention_seeds(insight: Any) -> str:
    """Product 4 — Invent: new AI agent capabilities from cluster intersections."""
    from hermes_insight.ontology import FORGE_VOICE

    patterns = insight.store.all_patterns(limit=5000)
    by = _by_fabric(patterns)
    deg = _degree_map(insight)
    projects = sorted(by.get("project") or [], key=lambda p: deg.get(p.id, 0), reverse=True)
    listens = by.get("listen") or []
    hermes = by.get("hermes") or []
    voice = FORGE_VOICE

    seeds = []

    commercial_hints = (
        "pay",
        "commerce",
        "hire",
        "employee",
        "billing",
        "checkout",
        "saas",
        "customer",
        "sales",
        "desk",
        "shop",
        "store",
    )
    commercial = [
        p
        for p in projects
        if any(h in p.title.lower() or h in p.body.lower() for h in commercial_hints)
    ]
    if hermes and commercial:
        seeds.append(
            {
                "title": "Managed AI employee with private Insight compartment",
                "parents": [hermes[0].title, commercial[0].title],
                "idea": (
                    "Each managed AI employee seat is a Hermes profile + model route + skill pack; "
                    "nightly forge emits an owner-facing agent brief (field map + trajectory). "
                    "Product is the agent + the brief, not raw logs."
                ),
                "first_build": "Profile factory → index-path(client) → forge → Friday value ledger attachment.",
            }
        )

    unowned = []
    for lp in listens:
        proc = str((lp.metadata or {}).get("process") or "")
        if proc in {"unknown", ""}:
            unowned.append(lp)
    if unowned:
        seeds.append(
            {
                "title": "Agent endpoint ownership graph",
                "parents": [p.title for p in unowned[:3]],
                "idea": (
                    "Map listen endpoints → agent profiles / plugins / tools automatically. "
                    "Every runtime port becomes an owned node in the multi-agent graph."
                ),
                "first_build": "Extend fabric index_connections to link listen:* → agent:* / plugin:*.",
            }
        )

    if (by.get("skill") or []) and (by.get("model") or []):
        seeds.append(
            {
                "title": "Skill↔model routing matrix",
                "parents": [
                    (by.get("skill") or [None])[0].title if by.get("skill") else "skills",
                    (by.get("model") or [None])[0].title if by.get("model") else "models",
                ],
                "idea": (
                    "Not every skill should hit the default model. Forge a routing table: "
                    "heavy coding skills → coding model; cheap classify skills → small/fast model."
                ),
                "first_build": "Emit markdown matrix from skill tags × model routes; wire config overrides.",
            }
        )

    if len(projects) >= 3:
        top3 = projects[:3]
        seeds.append(
            {
                "title": f"Multi-agent triangle: {', '.join(t.title.replace('project:','') for t in top3)}",
                "parents": [t.title for t in top3],
                "idea": (
                    "Three densest code surfaces become explicit agent workspaces with shared skill core "
                    "and divergent product skills — stop one god-agent thrashing all repos."
                ),
                "first_build": "Define three profiles + shared skill namespace + per-product skill packs.",
            }
        )

    seeds.append(
        {
            "title": "Conductor agent sensory organ (Insight pulse)",
            "parents": ["fabric:hermes-runtime", "listen:hermes", "agent:default"],
            "idea": (
                "Main conductor agent heartbeats forge prediction board; pages human only on "
                "high-confidence degrading multi-agent trajectory. Green = silence."
            ),
            "first_build": "Cron: index-connections + forge --only predict → gate on direction.",
        }
    )

    if len(projects) >= 2:
        a, b = projects[0], projects[1]
        seeds.append(
            {
                "title": f"Shared agent kernel: {a.title.replace('project:','')} × {b.title.replace('project:','')}",
                "parents": [a.title, b.title],
                "idea": (
                    "Extract shared tools/skills into one internal agent package both products load — "
                    "one evaluation harness, two product skins."
                ),
                "first_build": "Transfer-pack shared features → one skill pack dependency.",
            }
        )

    lines = [
        f"# {voice['invent_title']}",
        "",
        f"_{voice['invent_blurb']}_",
        "",
        "_Imagination in the agent field = recombining agents, models, tools, and skills._",
        "",
    ]
    for i, s in enumerate(seeds, 1):
        lines += [
            f"## {i}. {s['title']}",
            f"- **Parents:** {', '.join(str(x) for x in s['parents'])}",
            f"- **Idea:** {s['idea']}",
            f"- **First build:** {s['first_build']}",
            "",
        ]
    lines += [
        "## Selection rule (agent products)",
        "",
        "Ship the seed that: (1) improves an agent seat or model route this week, "
        "(2) touches revenue or trust, (3) reuses an existing hub agent instead of spawning an orphan profile.",
        "",
    ]
    return "\n".join(lines)


def build_action_playbooks(insight: Any) -> str:
    """Product 5 — Act: playbooks from levers + listens + hermes."""
    patterns = insight.store.all_patterns(limit=5000)
    by = _by_fabric(patterns)
    listens = {p.title: p for p in (by.get("listen") or [])}

    lines = [
        "# Action playbooks — execution product",
        "",
        "_Patterns earn rent when they change what you do next. Each playbook is a reusable move._",
        "",
        "## Playbook A — Credential / single-consumer lock",
        "",
        "**When:** long-poll conflicts, duplicate bots, dual workers on one token.",
        "**Lever:** `credential` / `consumer`",
        "**Moves:**",
        "1. Inventory every process that holds the credential (Insight `listen:*` + agent profiles).",
        "2. Enforce one consumer; others become webhook or offline.",
        "3. Separate `HERMES_HOME` / Insight `agent_id` per identity.",
        "4. Re-run `index-connections` and confirm a single listen owner.",
        "5. `insight_feedback` on the patterns that correctly predicted the failure.",
        "",
        "## Playbook B — Listen ownership",
        "",
        "**When:** `listen:unknown` or mesh/all_interfaces without a product face.",
        "**Moves:**",
        "1. Resolve process → unit → repo.",
        "2. `index-path` the owning project.",
        "3. Link listen→project (`enables` / `part_of`).",
        "4. If no owner: stop the port or accept it as infrastructure with a named runbook.",
        "",
        "### Current listen roster",
        "",
    ]
    for title, p in sorted(listens.items()):
        ports = ",".join((p.metadata or {}).get("ports") or [])
        binds = ",".join((p.metadata or {}).get("binds") or [])
        lines.append(f"- **{title}** ports=[{ports}] binds=[{binds}]")

    lines += [
        "",
        "## Playbook C — Hub focus (monotropic build)",
        "",
        "**When:** too many projects thrash attention.",
        "**Moves:**",
        "1. Open orientation map hubs.",
        "2. Pick ONE hub for the work block (Ship gate: revenue / drag / trust).",
        "3. All other hubs → watchlist only until the block ends.",
        "4. Forge invention seeds only from the chosen hub's neighbors.",
        "",
        "## Playbook D — Post-index forge ritual",
        "",
        "After any large `index-server`:",
        "1. `fabric-stats` — did counts move?",
        "2. `forge` — regenerate map, prediction, transfer, seeds, playbooks.",
        "3. Skim prediction board risks only (not the whole warehouse).",
        "4. File one synthesis pattern back if a new house rule appeared.",
        "",
    ]
    return "\n".join(lines)


def build_watch_edges(insight: Any) -> str:
    """Product 6 — Watch: novelty edges and weak links."""
    patterns = insight.store.all_patterns(limit=5000)
    deg = _degree_map(insight)
    by = _by_fabric(patterns)

    orphans = [
        p
        for p in (by.get("project") or [])
        if deg.get(p.id, 0) <= 2
    ][:15]
    weak_files = [
        p
        for p in (by.get("file") or [])
        if deg.get(p.id, 0) == 0
    ][:20]

    lines = [
        "# Watch edges — maintenance product",
        "",
        "_Pattern maintenance is half the skill: keep the catalogue honest._",
        "",
        "## Low-degree projects (possible orphans or new arrivals)",
        "",
    ]
    if not orphans:
        lines.append("- None flagged.")
    for p in orphans:
        lines.append(f"- {p.title} · deg={deg.get(p.id, 0)}")

    lines += ["", "## Unlinked files (sample)", ""]
    for p in weak_files[:12]:
        lines.append(f"- {p.title}")

    lines += [
        "",
        "## Hygiene moves",
        "",
        "1. Re-link files with `index-path` on their project root.",
        "2. Drop dead projects from scan roots if abandoned.",
        "3. Promote stable playbooks into Hermes skills (procedure > memory prose).",
        "4. Decay is allowed — not every file deserves eternal strength.",
        "",
    ]
    return "\n".join(lines)


def forge(
    insight: Any,
    *,
    out_dir: Optional[Path | str] = None,
    write_synthesis: bool = True,
    products: Optional[Sequence[str]] = None,
) -> ForgeBundle:
    """Run the forge and optionally write artifacts + synthesis nodes."""
    want = set(products or ("map", "predict", "transfer", "invent", "playbooks", "watch"))
    out_path = Path(out_dir) if out_dir else Path(insight.db_path).expanduser().resolve().parent / "forged"
    out_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_path / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        "map": ("01-orientation-map.md", build_orientation_map),
        "predict": ("02-prediction-board.md", build_prediction_board),
        "transfer": ("03-transfer-pack.md", build_transfer_pack),
        "invent": ("04-invention-seeds.md", build_invention_seeds),
        "playbooks": ("05-action-playbooks.md", build_action_playbooks),
        "watch": ("06-watch-edges.md", build_watch_edges),
    }

    bundle = ForgeBundle(created_at=_now_iso(), db_path=str(insight.db_path))
    written: Dict[str, Path] = {}

    for key, (fname, fn) in builders.items():
        if key not in want:
            continue
        text = scrub_text(fn(insight), redact_ips=True, redact_homes=True)
        path = run_dir / fname
        path.write_text(text, encoding="utf-8")
        bundle.products[str(path)] = text
        written[key] = path

    # Index + latest pointers
    index_lines = [
        f"# Forge run {stamp}",
        "",
        f"Created: {bundle.created_at}",
        f"DB: `{bundle.db_path}`",
        "",
        "## Products",
        "",
    ]
    for key, path in written.items():
        index_lines.append(f"- **{key}**: [{path.name}](./{path.name})")
    index_lines += [
        "",
        "## Human use cheat-sheet",
        "",
        "| Need | Open |",
        "|------|------|",
        "| Where am I? | orientation map |",
        "| What's coming? | prediction board |",
        "| Reuse a shape | transfer pack |",
        "| Make something new | invention seeds |",
        "| What do I do? | action playbooks |",
        "| What's rotting? | watch edges |",
        "",
    ]
    (run_dir / "README.md").write_text("\n".join(index_lines), encoding="utf-8")
    latest = out_path / "LATEST"
    latest.write_text(str(run_dir) + "\n", encoding="utf-8")

    if write_synthesis:
        # One synthesis node per major product theme
        synth_specs = []
        if "invent" in written:
            synth_specs.append(
                (
                    "forge:invention-batch",
                    written["invent"].read_text(encoding="utf-8")[:2500],
                    ["forge", "invention", "synthesis"],
                )
            )
        if "predict" in written:
            synth_specs.append(
                (
                    "forge:prediction-board",
                    written["predict"].read_text(encoding="utf-8")[:2000],
                    ["forge", "prediction", "trajectory"],
                )
            )
        if "playbooks" in written:
            synth_specs.append(
                (
                    "forge:action-playbooks",
                    written["playbooks"].read_text(encoding="utf-8")[:2000],
                    ["forge", "playbook", "action"],
                )
            )
        for title, body, tags in synth_specs:
            pat = insight.ingest(
                title=title,
                body=body,
                domain=Domain.PROCESS,
                kind=PatternKind.SYNTHESIS,
                tags=tags,
                features=extract_features(body, max_features=40),
                confidence=0.7,
                source="pattern-forge",
                metadata={"fabric": "forge", "run": stamp},
                link=True,
            )
            bundle.synthesis_ids.append(pat.id)

    st = insight.stats()
    fs = insight.fabric_stats() if hasattr(insight, "fabric_stats") else {}
    bundle.stats = {
        "run_dir": str(run_dir),
        "product_count": len(written),
        "lattice": st,
        "fabric": {k: fs.get(k) for k in ("fabric_patterns", "by_kind") if isinstance(fs, dict)},
    }
    # machine summary
    (run_dir / "bundle.json").write_text(
        json.dumps(
            {
                "created_at": bundle.created_at,
                "db_path": bundle.db_path,
                "run_dir": str(run_dir),
                "products": list(written.keys()),
                "synthesis_ids": bundle.synthesis_ids,
                "stats": bundle.stats,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return bundle
