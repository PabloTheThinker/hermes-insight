"""Feature decomposition — bottom-up perception layer.

Lightweight, dependency-free feature extraction so the lattice works without
an LLM. When an LLM is available, agents should still call `ingest` with
richer hand-authored features; this module bootstraps structure from raw text.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Sequence, Set

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_\-\.]{1,48}", re.I)
_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+")

# High-signal stopwords only — keep technical tokens.
_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "when",
    "while",
    "of",
    "to",
    "for",
    "in",
    "on",
    "at",
    "by",
    "with",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "this",
    "that",
    "these",
    "those",
    "i",
    "you",
    "we",
    "they",
    "he",
    "she",
    "them",
    "his",
    "her",
    "our",
    "your",
    "their",
    "not",
    "no",
    "yes",
    "do",
    "does",
    "did",
    "done",
    "have",
    "has",
    "had",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "into",
    "about",
    "over",
    "after",
    "before",
    "between",
    "than",
    "too",
    "very",
    "just",
    "also",
    "than",
    "such",
    "via",
    "per",
    "using",
    "use",
    "used",
    "using",
    "something",
    "anything",
    "everything",
    "nothing",
    "wrong",
    "broken",
}


def stem_token(tok: str) -> str:
    """Aggressive-light English stem so retries≈retry, failures≈failure."""
    t = tok.lower()
    if len(t) <= 3:
        return t
    # Never butcher high-frequency full words into garbage stems
    _NO_STEM = {
        "something",
        "anything",
        "everything",
        "nothing",
        "someone",
        "anyone",
        "everyone",
        "somewhere",
        "however",
        "during",
        "without",
        "within",
        "single",
        "simple",
        "string",
        "running",
        "warning",
    }
    if t in _NO_STEM:
        return t
    for suf in ("ingly", "edly", "ally"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    if t.endswith("ies") and len(t) > 5:
        return t[:-3] + "y"
    if t.endswith("ing") and len(t) > 6:
        base = t[:-3]
        # avoid something → someth, string → str
        if len(base) < 5:
            return t
        if len(base) >= 4 and base[-1] == base[-2]:
            base = base[:-1]
        return base
    if t.endswith("ers") and len(t) > 5:
        return t[:-1]  # breakers -> breaker
    if t.endswith("es") and len(t) > 5 and not t.endswith(("sses", "uses", "ses")):
        if t.endswith(("ses", "zes", "xes", "ches", "shes")):
            return t[:-2]
        return t[:-1]
    if t.endswith("s") and not t.endswith("ss") and len(t) > 4:
        return t[:-1]
    if t.endswith("ed") and len(t) > 5:
        base = t[:-2]
        if len(base) >= 4 and base[-1] == base[-2]:
            base = base[:-1]
        return base
    return t


def tokenize(text: str) -> List[str]:
    raw = _TOKEN_RE.findall((text or "").lower())
    out: List[str] = []
    for tok in raw:
        if tok in _STOP or len(tok) < 2:
            continue
        # split snake/kebab already lower; expand camel leftovers
        if "_" in tok or "-" in tok or "." in tok:
            parts = re.split(r"[_\-\.]+", tok)
            for p in parts:
                if p and p not in _STOP and len(p) > 1:
                    out.append(stem_token(p))
        else:
            out.append(stem_token(tok))
    return out


def extract_features(
    text: str,
    *,
    extra: Sequence[str] | None = None,
    max_features: int = 48,
) -> List[str]:
    """Return ordered unique features (salient tokens + multi-word cues)."""
    tokens = tokenize(text)
    counts = Counter(tokens)
    # unigrams by frequency, prefer mid-length technical tokens
    scored = sorted(
        counts.items(),
        key=lambda kv: (kv[1], min(len(kv[0]), 12), kv[0]),
        reverse=True,
    )
    feats: List[str] = []
    seen: Set[str] = set()

    def add(f: str) -> None:
        f = f.strip().lower()
        if not f or f in seen or f in _STOP:
            return
        seen.add(f)
        feats.append(f)

    for t, _ in scored:
        add(t)
        if len(feats) >= max_features:
            break

    # bigrams for sequence texture
    for a, b in zip(tokens, tokens[1:]):
        if a in _STOP or b in _STOP:
            continue
        add(f"{a}_{b}")
        if len(feats) >= max_features:
            break

    for e in extra or []:
        add(str(e))
        if len(feats) >= max_features + 16:
            break

    return feats[: max_features + 16]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(x.lower() for x in a), set(x.lower() for x in b)
    if not sa and not sb:
        return 0.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def overlap_list(a: Sequence[str], b: Sequence[str]) -> List[str]:
    sb = {x.lower() for x in b}
    return [x for x in a if x.lower() in sb]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())
