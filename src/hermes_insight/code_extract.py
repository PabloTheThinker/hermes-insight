"""Code-aware and text structure extraction for higher-signal features."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from hermes_insight.features import extract_features, stem_token, tokenize

_DEF_RE = re.compile(
    r"^\s*(?:async\s+)?def\s+([A-Za-z_][\w]*)|^\s*class\s+([A-Za-z_][\w]*)",
    re.M,
)
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))",
    re.M,
)
_DOC_RE = re.compile(r'^\s*"""(.*?)"""|^\s*\'\'\'(.*?)\'\'\'', re.S | re.M)


def extract_python_structure(source: str, *, path: str = "") -> Dict[str, object]:
    """Pull defs, classes, imports, module docstring — prefer AST, regex fallback."""
    names: List[str] = []
    imports: List[str] = []
    docstring = ""
    try:
        tree = ast.parse(source)
        docstring = (ast.get_docstring(tree) or "").strip()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        imports.append(a.name.split(".")[0])
                elif node.module:
                    imports.append(node.module.split(".")[0])
        # nested one level
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        names.append(child.name)
    except SyntaxError:
        for m in _DEF_RE.finditer(source):
            names.append(m.group(1) or m.group(2))
        for m in _IMPORT_RE.finditer(source):
            imports.append((m.group(1) or m.group(2) or "").split(".")[0])
        dm = _DOC_RE.search(source)
        if dm:
            docstring = (dm.group(1) or dm.group(2) or "").strip()

    path_parts = [stem_token(p) for p in Path(path).parts if p not in (".", "..", "")]
    path_parts = [p for p in path_parts if p and p not in {"py", "src", "lib", "home"}]

    # structural features
    feats: List[str] = []
    for n in names[:40]:
        feats.append(stem_token(n))
        # split snake
        feats.extend(tokenize(n.replace("_", " ")))
    for im in imports[:20]:
        feats.append(stem_token(im))
    feats.extend(path_parts[-6:])
    if docstring:
        feats.extend(extract_features(docstring, max_features=20))

    # de-dupe
    seen = set()
    out_feats: List[str] = []
    for f in feats:
        fl = f.lower()
        if fl in seen or len(fl) < 2:
            continue
        seen.add(fl)
        out_feats.append(fl)

    title_hint = ""
    if names:
        title_hint = names[0]
    elif path:
        title_hint = Path(path).stem

    summary_bits = []
    if docstring:
        summary_bits.append(docstring.splitlines()[0][:200])
    if names:
        summary_bits.append("symbols: " + ", ".join(names[:12]))
    if imports:
        summary_bits.append("imports: " + ", ".join(sorted(set(imports))[:10]))
    body = "\n".join(summary_bits) if summary_bits else source[:1200]

    return {
        "features": out_feats[:64],
        "symbols": names[:40],
        "imports": sorted(set(imports))[:20],
        "docstring": docstring[:2000],
        "title_hint": title_hint,
        "body": body[:2500],
        "path_parts": path_parts[-6:],
    }


def file_to_pattern_fields(
    path: Path,
    *,
    max_bytes: int = 120_000,
) -> Optional[Tuple[str, str, List[str], List[str], Dict]]:
    """Return title, body, features, tags, metadata for a source file."""
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > max_bytes:
            return None
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    suffix = path.suffix.lower()
    tags = [suffix.lstrip(".") or "file", path.parent.name.replace("_", "-")[:24]]
    meta: Dict = {"path": str(path), "suffix": suffix}

    if suffix == ".py":
        st = extract_python_structure(raw, path=str(path))
        title = f"{path.parent.name}/{path.name}"
        body = str(st["body"])
        features = list(st["features"])  # type: ignore[arg-type]
        # keep some raw head for template match
        if not body.strip():
            body = "\n".join(raw.splitlines()[:40])[:1500]
        meta.update(
            {
                "symbols": list(st["symbols"]),  # type: ignore[arg-type]
                "imports": list(st["imports"]),  # type: ignore[arg-type]
                "docstring": str(st["docstring"])[:500],
                "path_parts": list(st["path_parts"]),  # type: ignore[arg-type]
            }
        )
        tags.extend(["python", "code"])
        for s in list(st["symbols"])[:8]:  # type: ignore[arg-type]
            tags.append(str(s).replace("_", "-")[:28].lower())
    else:
        title = path.name
        body = raw[:2000]
        features = extract_features(f"{title}\n{body}", max_features=48)
        tags.append("text")

    return title, body, features, tags, meta
