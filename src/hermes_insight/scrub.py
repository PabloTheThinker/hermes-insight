"""Secret / fingerprint scrubbing before anything enters the lattice."""

from __future__ import annotations

import re
from typing import Iterable

# High-signal secret shapes
_SECRET_RES = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)postgres(?:ql)?://[^\s]+"),
    re.compile(r"(?i)redis://[^\s]+"),
    re.compile(r"(?i)mongodb(?:\+srv)?://[^\s]+"),
]

# Host fingerprints that should not live in shared lattices by default
_FINGERPRINT_RES = [
    re.compile(r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),  # CGNAT/mesh-style
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),  # generic IPv4 → redacted
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
]

_SKIP_NAME_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".tox",
    ".eggs",
    "egg-info",
    ".cache",
    "secrets",
    ".ssh",
    ".gnupg",
    "credentials",
    "auth.json",
    ".env",
}

_SKIP_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".der",
    ".sqlite",
    ".db",
    ".bin",
    ".pyc",
    ".so",
    ".o",
    ".a",
    ".woff",
    ".woff2",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp4",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
}


def scrub_text(text: str, *, redact_ips: bool = True, redact_homes: bool = True) -> str:
    if not text:
        return ""
    out = text
    for rx in _SECRET_RES:
        out = rx.sub("[REDACTED_SECRET]", out)
    if redact_ips or redact_homes:
        for rx in _FINGERPRINT_RES:
            if not redact_ips and r"\d{1,3}" in rx.pattern and "100" not in rx.pattern:
                continue
            if not redact_homes and "/home/" in rx.pattern:
                continue
            if "100\\." in rx.pattern:
                out = rx.sub("[MESH_IP]", out)
            elif r"\d{1,3}" in rx.pattern and "100" not in rx.pattern:
                if redact_ips:
                    out = rx.sub("[IP]", out)
            elif "/home/" in rx.pattern:
                if redact_homes:
                    out = rx.sub("[HOME]", out)
            else:
                out = rx.sub("[REDACTED]", out)
    return out


def should_skip_path(path_str: str) -> bool:
    parts = path_str.replace("\\", "/").split("/")
    base = parts[-1] if parts else ""
    if base.startswith(".env"):
        return True
    if base in {"auth.json", "credentials.json", "id_rsa", "id_ed25519"}:
        return True
    for p in parts:
        pl = p.lower()
        if pl in _SKIP_NAME_PARTS or pl.endswith(".egg-info"):
            return True
        if "secret" in pl and pl not in {"secret_sources"}:  # hermes module name ok
            if pl in {"secrets", ".secrets", "client-secrets"}:
                return True
    for suf in _SKIP_SUFFIXES:
        if base.lower().endswith(suf):
            return True
    return False


def scrub_metadata(meta: dict) -> dict:
    out = {}
    for k, v in (meta or {}).items():
        if isinstance(v, str):
            out[k] = scrub_text(v)
        elif isinstance(v, list):
            out[k] = [
                scrub_text(x)
                if isinstance(x, str)
                else scrub_metadata(x)
                if isinstance(x, dict)
                else x
                for x in v
            ]
        elif isinstance(v, dict):
            out[k] = scrub_metadata(v)
        else:
            out[k] = v
    return out


def is_probably_text(sample: bytes) -> bool:
    if not sample:
        return True
    if b"\x00" in sample[:2048]:
        return False
    # high ratio of printable
    printable = sum(1 for b in sample[:2048] if 9 <= b <= 13 or 32 <= b < 127)
    return printable / max(len(sample[:2048]), 1) > 0.85
