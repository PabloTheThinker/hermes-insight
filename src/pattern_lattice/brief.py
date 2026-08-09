"""Agent-facing briefs — finished products, not warehouses."""

from __future__ import annotations

from typing import Optional, Sequence

from pattern_lattice.models import CycleReport, Distillation, MatchResult, Trajectory


def format_brief(report: CycleReport, *, style: str = "agent") -> str:
    if style == "json":
        return report.to_json()
    return render_markdown(report)


def render_markdown(report: CycleReport) -> str:
    lines = [
        "# Pattern Lattice brief",
        "",
        f"**Query:** {report.query.strip() or '(none)'}",
        "",
    ]
    if report.dims_used:
        lines.append(f"**Dimensions:** {', '.join(report.dims_used)}")
        lines.append("")

    if report.distillation:
        d = report.distillation
        lines += [
            "## Distillation (actual variable)",
            f"- **Lever:** `{d.actual_variable}`",
            f"- **Confidence:** {d.confidence:.2f}",
            f"- **Principle:** {d.principle}",
            f"- **Action:** {d.actionable}",
        ]
        if d.supporting:
            lines.append(f"- **Supporting structure:** {', '.join(d.supporting[:8])}")
        lines.append("")

    if report.matches:
        lines.append("## Recognized patterns")
        for m in report.matches[:7]:
            lines.append(
                f"- **{m.pattern.title}** (`{m.pattern.id}`) · "
                f"score={m.score:.2f} · {m.method} · "
                f"{m.pattern.domain.value}/{m.pattern.kind.value}"
            )
            if m.shared_features:
                lines.append(f"  - shared: {', '.join(m.shared_features[:10])}")
        lines.append("")

    if report.links:
        lines.append("## Links / lateral hops")
        for lk in report.links[:10]:
            lines.append(
                f"- {lk.get('kind')} · {lk.get('source_id')} → {lk.get('target_id')} "
                f"(w={lk.get('weight', 0):.2f}) — {lk.get('note', '')}"
            )
        lines.append("")

    if report.trajectory:
        t = report.trajectory
        lines += [
            "## Trajectory",
            f"- **Direction:** {t.direction} (conf {t.confidence:.2f})",
            f"- **Next expected:** {t.next_expected}",
        ]
        if t.steps:
            lines.append("- **Steps:**")
            for s in t.steps[:8]:
                lines.append(f"  - {s}")
        if t.risks:
            lines.append(f"- **Risks:** {'; '.join(t.risks)}")
        lines.append("")

    if report.anomalies:
        lines.append("## Novelty / anomalies")
        for a in report.anomalies:
            lines.append(
                f"- status={a.get('status')} novelty={a.get('novelty')} — {a.get('reason')}"
            )
            if a.get("suggestion"):
                lines.append(f"  - suggest: {a['suggestion']}")
        lines.append("")

    if report.generated:
        lines.append("## Generated / filed")
        for p in report.generated:
            lines.append(f"- `{p.id}` · {p.kind.value} · **{p.title}**")
        lines.append("")

    if report.observations:
        lines.append("## Observations")
        for o in report.observations[:12]:
            lines.append(f"- {o}")
        lines.append("")

    lines.append("_Pattern Lattice — encode · match · link · distill · extrapolate · evolve_")
    return "\n".join(lines).strip() + "\n"


def compact_one_liner(
    distillation: Optional[Distillation],
    matches: Sequence[MatchResult],
    trajectory: Optional[Trajectory],
) -> str:
    parts = []
    if distillation:
        parts.append(f"lever=`{distillation.actual_variable}`")
    if matches:
        parts.append(f"match=`{matches[0].pattern.title}`@{matches[0].score:.2f}")
    if trajectory:
        parts.append(f"traj={trajectory.direction}")
    return " · ".join(parts) if parts else "no strong pattern yet"
