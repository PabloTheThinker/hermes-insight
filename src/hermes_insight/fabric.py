"""Server fabric indexer — projects, software trees, metadata, connections.

Makes the lattice see the machine's structural world (not secret contents):
file roles, project manifests, listen ports, process classes, graph edges.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from hermes_insight.code_extract import file_to_pattern_fields
from hermes_insight.features import extract_features
from hermes_insight.models import Domain, Link, LinkKind, Pattern, PatternKind
from hermes_insight.scrub import scrub_metadata, scrub_text, should_skip_path

# Default relative roots under $HOME (portable — no operator hostnames)
_DEFAULT_HOME_ROOTS = (
    "projects",
    "hermes-agent",
    ".hermes",
    ".ilo",
)

_MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "composer.json",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    "Makefile",
    "README.md",
    "AGENTS.md",
    "HERMES.md",
    ".hermes.md",
}

_CONFIG_GLOBS = (
    "config.yaml",
    "config.yml",
    "config.toml",
    "settings.json",
    "*.service",
)


@dataclass
class FabricReport:
    roots_scanned: List[str] = field(default_factory=list)
    files_seen: int = 0
    files_ingested: int = 0
    projects_found: int = 0
    connections_found: int = 0
    patterns_created: int = 0
    links_created: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    project_ids: List[str] = field(default_factory=list)
    connection_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roots_scanned": self.roots_scanned,
            "files_seen": self.files_seen,
            "files_ingested": self.files_ingested,
            "projects_found": self.projects_found,
            "connections_found": self.connections_found,
            "patterns_created": self.patterns_created,
            "links_created": self.links_created,
            "skipped": self.skipped,
            "errors": self.errors[:20],
            "project_ids": self.project_ids[:50],
            "connection_ids": self.connection_ids[:50],
        }


def default_scan_roots(
    *,
    home: Optional[Path] = None,
    extra: Optional[Sequence[str]] = None,
    include_hermes_home: bool = True,
) -> List[Path]:
    home = (home or Path.home()).expanduser()
    roots: List[Path] = []
    for rel in _DEFAULT_HOME_ROOTS:
        p = home / rel
        if p.exists():
            roots.append(p)
    if include_hermes_home:
        hh = os.environ.get("HERMES_HOME")
        if hh:
            p = Path(hh).expanduser()
            if p.exists() and p not in roots:
                roots.append(p)
    for e in extra or []:
        p = Path(e).expanduser()
        if p.exists() and p not in roots:
            roots.append(p)
    # de-dupe resolved
    seen: Set[str] = set()
    out: List[Path] = []
    for r in roots:
        key = str(r.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(r.resolve())
    return out


def _read_text_limited(path: Path, max_bytes: int = 64_000) -> str:
    try:
        data = path.read_bytes()[:max_bytes]
        if b"\x00" in data[:2048]:
            return ""
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def discover_projects(root: Path, *, max_depth: int = 4) -> List[Path]:
    """Project roots = dirs containing a known manifest, depth-limited."""
    found: List[Path] = []
    root = root.resolve()
    if not root.is_dir():
        return found

    # if root itself is a project
    if any((root / m).exists() for m in _MANIFEST_NAMES):
        found.append(root)

    try:
        for dirpath, dirnames, filenames in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            depth = len(rel.parts)
            # prune heavy/secret trees
            dirnames[:] = [
                d
                for d in dirnames
                if d not in {
                    ".git", ".venv", "venv", "node_modules", "__pycache__",
                    "dist", "build", ".tox", "target", ".cache", "secrets",
                }
                and not d.endswith(".egg-info")
            ]
            if depth > max_depth:
                dirnames[:] = []
                continue
            names = set(filenames)
            if names & _MANIFEST_NAMES:
                p = Path(dirpath)
                if p != root:
                    found.append(p)
            if len(found) >= 200:
                break
    except OSError:
        pass
    return found[:200]


def project_summary(project: Path) -> Dict[str, Any]:
    manifests = [m for m in _MANIFEST_NAMES if (project / m).exists()]
    langs: Set[str] = set()
    for m in manifests:
        if m in {"package.json"}:
            langs.add("javascript")
        if m in {"pyproject.toml"}:
            langs.add("python")
        if m == "Cargo.toml":
            langs.add("rust")
        if m == "go.mod":
            langs.add("go")
        if m.startswith("docker"):
            langs.add("docker")
    # quick file role counts
    roles = defaultdict(int)
    try:
        for p in project.rglob("*"):
            if not p.is_file():
                continue
            if should_skip_path(str(p)):
                continue
            suf = p.suffix.lower()
            if suf in {".py"}:
                roles["python"] += 1
            elif suf in {".ts", ".tsx", ".js", ".jsx"}:
                roles["js_ts"] += 1
            elif suf in {".md"}:
                roles["docs"] += 1
            elif suf in {".yml", ".yaml", ".toml", ".json"}:
                roles["config"] += 1
            elif suf in {".rs", ".go", ".java"}:
                roles["other_code"] += 1
            if sum(roles.values()) > 5000:
                break
    except OSError:
        pass

    git_remote = ""
    git_dir = project / ".git"
    if git_dir.exists():
        cfg = project / ".git" / "config"
        if cfg.is_file():
            txt = _read_text_limited(cfg, 8000)
            m = re.search(r"url\s*=\s*(\S+)", txt)
            if m:
                git_remote = scrub_text(m.group(1))

    readme_head = ""
    for name in ("README.md", "readme.md", "AGENTS.md"):
        rp = project / name
        if rp.is_file():
            readme_head = scrub_text(_read_text_limited(rp, 2500)[:800])
            break

    return scrub_metadata(
        {
            "path": scrub_text(str(project)),
            "name": project.name,
            "manifests": manifests,
            "languages": sorted(langs),
            "file_roles": dict(roles),
            "git_remote": git_remote,
            "readme_head": readme_head,
        }
    )


def collect_listening_ports() -> List[Dict[str, Any]]:
    """Parse `ss -lntup` when available; scrub addresses."""
    if not shutil.which("ss"):
        return _fallback_ports()
    try:
        proc = subprocess.run(
            ["ss", "-lntup"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        text = proc.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return _fallback_ports()

    rows: List[Dict[str, Any]] = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        # ss variants:
        #   LISTEN 0 5 127.0.0.1:80 ...
        #   tcp LISTEN 0 5 127.0.0.1:80 ...
        #   Netid State Recv-Q ...
        state = ""
        local = ""
        proto = "tcp"
        if parts[0] in {"LISTEN", "UNCONN", "ESTAB"}:
            state = parts[0]
            local = parts[3] if len(parts) > 3 else ""
        elif len(parts) > 1 and parts[1] in {"LISTEN", "UNCONN", "ESTAB"}:
            proto = parts[0].lower()
            state = parts[1]
            local = parts[4] if len(parts) > 4 else ""
        else:
            continue
        if state != "LISTEN":
            continue
        process = ""
        m = re.search(r'users:\(\("([^"]+)"', line)
        if m:
            process = m.group(1)
        host, port = _split_hostport(local)
        if not port:
            continue
        rows.append(
            scrub_metadata(
                {
                    "port": port,
                    "bind_class": _bind_class(host),
                    "process": process or "unknown",
                    "proto": proto,
                }
            )
        )
    # unique by port+process
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for r in rows:
        key = f"{r.get('port')}:{r.get('process')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out[:200]


def _fallback_ports() -> List[Dict[str, Any]]:
    # minimal: nothing if ss missing
    return []


def _split_hostport(local: str) -> Tuple[str, str]:
    # formats: 127.0.0.1:8080  *:22  [::1]:8080  0.0.0.0:80
    local = local.strip()
    if local.startswith("["):
        m = re.match(r"\[([^\]]+)\]:(\d+)$", local)
        if m:
            return m.group(1), m.group(2)
    if ":" in local:
        host, port = local.rsplit(":", 1)
        return host, port
    return local, ""


def _bind_class(host: str) -> str:
    h = host.lower()
    if h in {"127.0.0.1", "::1", "localhost"}:
        return "loopback"
    if h in {"0.0.0.0", "*", "::"}:
        return "all_interfaces"
    if h.startswith("100."):
        return "mesh"
    if re.match(r"\d+\.\d+\.\d+\.\d+", h):
        return "lan_or_public"
    return "other"


def collect_process_snapshot(limit: int = 80) -> List[Dict[str, Any]]:
    """Lightweight process class list (names only)."""
    try:
        proc = subprocess.run(
            ["ps", "-eo", "comm=", "--sort=-%mem"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        names = []
        for line in (proc.stdout or "").splitlines():
            n = line.strip()
            if n:
                names.append(n)
    except (OSError, subprocess.TimeoutExpired):
        return []
    counts: Dict[str, int] = defaultdict(int)
    for n in names:
        # strip path
        base = Path(n).name
        counts[base] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"process": k, "count": v} for k, v in ranked]


def hermes_profile_meta(hermes_home: Optional[Path] = None) -> Dict[str, Any]:
    hh = hermes_home or Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    hh = hh.expanduser()
    if not hh.exists():
        return {}
    profiles_dir = hh / "profiles"
    profiles = []
    if profiles_dir.is_dir():
        profiles = sorted([p.name for p in profiles_dir.iterdir() if p.is_dir()])[:40]
    skills = 0
    sk = hh / "skills"
    if sk.is_dir():
        skills = sum(1 for _ in sk.rglob("SKILL.md"))
    plugins = []
    pd = hh / "plugins"
    if pd.is_dir():
        plugins = sorted([p.name for p in pd.iterdir() if p.is_dir()])[:40]
    return scrub_metadata(
        {
            "hermes_home": scrub_text(str(hh)),
            "profiles": profiles,
            "skill_count": skills,
            "plugins": plugins,
            "has_config": (hh / "config.yaml").exists(),
            "has_gateway_logs": (hh / "logs").exists(),
        }
    )


class FabricIndexer:
    """Indexes server fabric into a HermesInsight store via callbacks."""

    def __init__(self, insight: Any) -> None:
        # insight: HermesInsight instance
        self.insight = insight

    def index_server(
        self,
        *,
        roots: Optional[Sequence[str | Path]] = None,
        include_projects: bool = True,
        include_files: bool = True,
        include_connections: bool = True,
        include_processes: bool = True,
        include_hermes: bool = True,
        max_files_per_project: int = 40,
        max_projects: int = 80,
        file_globs: Sequence[str] = ("**/*.py", "**/*.ts", "**/*.tsx", "**/*.md", "**/*.yaml", "**/*.yml"),
        link: bool = True,
    ) -> FabricReport:
        report = FabricReport()
        # empty roots should still allow connection-only scan
        if roots is not None and len(list(roots)) == 0:
            root_paths = []
        elif roots is None:
            root_paths = default_scan_roots()
        else:
            root_paths = [Path(r).expanduser().resolve() for r in roots if Path(r).expanduser().exists()]

        report.roots_scanned = [scrub_text(str(r)) for r in root_paths]

        project_pattern_ids: Dict[str, str] = {}

        if include_hermes:
            hm = hermes_profile_meta()
            if hm:
                pat = self.insight.ingest(
                    title="fabric:hermes-runtime",
                    body=json.dumps(hm, indent=2)[:3000],
                    domain=Domain.SYSTEM,
                    kind=PatternKind.PROTOTYPE,
                    tags=["fabric", "hermes", "runtime", "metadata"],
                    features=extract_features(json.dumps(hm), max_features=40),
                    confidence=0.7,
                    source="fabric-indexer",
                    metadata={"fabric": "hermes", **hm},
                    link=link,
                )
                report.patterns_created += 1
                project_pattern_ids["hermes-runtime"] = pat.id

        # Projects
        all_projects: List[Path] = []
        if include_projects:
            for root in root_paths:
                all_projects.extend(discover_projects(root))
            # unique
            seen: Set[str] = set()
            uniq: List[Path] = []
            for p in all_projects:
                k = str(p.resolve())
                if k in seen:
                    continue
                seen.add(k)
                uniq.append(p)
            all_projects = uniq[:max_projects]
            report.projects_found = len(all_projects)

            for proj in all_projects:
                summary = project_summary(proj)
                body = (
                    f"Project `{summary.get('name')}`\n"
                    f"manifests: {', '.join(summary.get('manifests') or [])}\n"
                    f"languages: {', '.join(summary.get('languages') or [])}\n"
                    f"roles: {summary.get('file_roles')}\n"
                    f"git: {summary.get('git_remote') or 'none'}\n"
                    f"{summary.get('readme_head') or ''}"
                )
                tags = [
                    "fabric",
                    "project",
                    str(summary.get("name", "proj"))[:32],
                    *[str(x) for x in (summary.get("languages") or [])],
                ]
                feats = extract_features(body, max_features=48)
                feats.extend([str(x) for x in (summary.get("manifests") or [])])
                pat = self.insight.ingest(
                    title=f"project:{summary.get('name')}",
                    body=scrub_text(body)[:3500],
                    domain=Domain.CODE,
                    kind=PatternKind.PROTOTYPE,
                    tags=tags,
                    features=feats,
                    confidence=0.65,
                    source="fabric-project",
                    metadata={"fabric": "project", **summary},
                    link=link,
                )
                report.patterns_created += 1
                report.project_ids.append(pat.id)
                project_pattern_ids[str(summary.get("name"))] = pat.id

                if include_files:
                    n = self._ingest_project_files(
                        proj,
                        project_id=pat.id,
                        max_files=max_files_per_project,
                        globs=file_globs,
                        link=link,
                        report=report,
                    )

        if include_connections:
            ports = collect_listening_ports()
            report.connections_found = len(ports)
            # group by process
            by_proc: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for row in ports:
                by_proc[str(row.get("process") or "unknown")].append(row)

            for proc_name, rows in list(by_proc.items())[:60]:
                ports_s = sorted({str(r.get("port")) for r in rows if r.get("port")})
                binds = sorted({str(r.get("bind_class")) for r in rows})
                body = (
                    f"Process `{proc_name}` listens on ports {', '.join(ports_s)}; "
                    f"bind classes: {', '.join(binds)}."
                )
                feats = extract_features(body + " " + proc_name + " " + " ".join(ports_s))
                feats.extend(["listen", "port", "connection", proc_name])
                pat = self.insight.ingest(
                    title=f"listen:{proc_name}",
                    body=body,
                    domain=Domain.SYSTEM,
                    kind=PatternKind.RELATION,
                    tags=["fabric", "connection", "listen", proc_name[:24]],
                    features=feats,
                    confidence=0.7,
                    source="fabric-ss",
                    metadata={"fabric": "listen", "process": proc_name, "ports": ports_s, "binds": binds},
                    link=link,
                )
                report.patterns_created += 1
                report.connection_ids.append(pat.id)

                # link listen nodes to matching project names / hermes
                if link:
                    self._link_connection_to_projects(pat, proc_name, project_pattern_ids, report)

        if include_processes:
            snap = collect_process_snapshot(60)
            if snap:
                body = "Top processes by memory class:\n" + "\n".join(
                    f"- {r['process']} x{r['count']}" for r in snap[:40]
                )
                pat = self.insight.ingest(
                    title="fabric:process-snapshot",
                    body=body,
                    domain=Domain.SYSTEM,
                    kind=PatternKind.SEQUENCE,
                    tags=["fabric", "process", "snapshot"],
                    features=extract_features(body, max_features=40),
                    confidence=0.55,
                    source="fabric-ps",
                    metadata={"fabric": "processes", "top": snap[:40]},
                    link=link,
                )
                report.patterns_created += 1

        # host identity (non-sensitive)
        host_body = (
            f"hostname_class={scrub_text(socket.gethostname())}; "
            f"platform={os.uname().sysname if hasattr(os, 'uname') else 'unknown'}; "
            f"roots={len(root_paths)}; projects={report.projects_found}; "
            f"listens={report.connections_found}"
        )
        self.insight.ingest(
            title="fabric:host-summary",
            body=host_body,
            domain=Domain.SYSTEM,
            kind=PatternKind.PROTOTYPE,
            tags=["fabric", "host", "summary"],
            features=extract_features(host_body),
            confidence=0.6,
            source="fabric-host",
            metadata={"fabric": "host"},
            link=link,
        )
        report.patterns_created += 1

        report.patterns_created = max(report.patterns_created, 0)
        return report

    def _ingest_project_files(
        self,
        project: Path,
        *,
        project_id: str,
        max_files: int,
        globs: Sequence[str],
        link: bool,
        report: FabricReport,
    ) -> int:
        paths: List[Path] = []
        for g in globs:
            try:
                for p in project.glob(g):
                    if not p.is_file():
                        continue
                    if should_skip_path(str(p)):
                        report.skipped += 1
                        continue
                    try:
                        if p.stat().st_size > 120_000 or p.stat().st_size < 40:
                            continue
                    except OSError:
                        continue
                    paths.append(p)
            except OSError as exc:
                report.errors.append(f"{project}: {exc}")
        # prefer smaller / entry-ish files
        paths = sorted(set(paths), key=lambda p: (p.stat().st_size if p.exists() else 1e9))[:max_files]
        count = 0
        for p in paths:
            report.files_seen += 1
            try:
                pat = self.insight.ingest_file(p, domain=Domain.CODE, link=False)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"{p.name}: {exc}")
                report.skipped += 1
                continue
            if not pat:
                report.skipped += 1
                continue
            # scrub path in metadata
            if pat.metadata:
                pat.metadata = scrub_metadata(pat.metadata)
                pat.metadata["project_pattern_id"] = project_id
                pat.metadata["fabric"] = "file"
                self.insight.store.upsert_pattern(pat)
            if link:
                try:
                    self.insight.store.upsert_link(
                        Link.create(pat.id, project_id, LinkKind.PART_OF, weight=0.7, note="file in project")
                    )
                    report.links_created += 1
                except Exception:
                    pass
            report.files_ingested += 1
            report.patterns_created += 1
            count += 1
        return count

    def _link_connection_to_projects(
        self,
        listen_pat: Pattern,
        proc_name: str,
        project_ids: Dict[str, str],
        report: FabricReport,
    ) -> None:
        pname = proc_name.lower()
        for proj_name, pid in project_ids.items():
            pn = proj_name.lower()
            if pn in pname or pname in pn or any(
                tok and tok in pname for tok in re.split(r"[-_]", pn) if len(tok) > 3
            ):
                try:
                    self.insight.store.upsert_link(
                        Link.create(
                            listen_pat.id,
                            pid,
                            LinkKind.ENABLES,
                            weight=0.55,
                            note=f"process {proc_name} ~ project {proj_name}",
                        )
                    )
                    report.links_created += 1
                except Exception:
                    pass
        # hermes runtime
        if "hermes" in pname and "hermes-runtime" in project_ids:
            try:
                self.insight.store.upsert_link(
                    Link.create(
                        listen_pat.id,
                        project_ids["hermes-runtime"],
                        LinkKind.PART_OF,
                        weight=0.6,
                        note="hermes process",
                    )
                )
                report.links_created += 1
            except Exception:
                pass
