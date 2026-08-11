"""SQLite + FTS5 pattern graph store (Hermes-style durable local state).

No network. Path is caller-controlled. Safe for agent profiles:
pass an explicit db_path under the agent's own home.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from hermes_insight.models import Link, Pattern


SCHEMA = """
CREATE TABLE IF NOT EXISTS patterns (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  kind TEXT NOT NULL,
  domain TEXT NOT NULL,
  features_json TEXT NOT NULL DEFAULT '[]',
  tags_json TEXT NOT NULL DEFAULT '[]',
  confidence REAL NOT NULL DEFAULT 0.5,
  strength REAL NOT NULL DEFAULT 0.5,
  evidence_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  last_used_at REAL NOT NULL DEFAULT 0,
  use_count INTEGER NOT NULL DEFAULT 0,
  content_hash TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS links (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 0.5,
  note TEXT NOT NULL DEFAULT '',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at REAL NOT NULL,
  UNIQUE(source_id, target_id, kind),
  FOREIGN KEY(source_id) REFERENCES patterns(id) ON DELETE CASCADE,
  FOREIGN KEY(target_id) REFERENCES patterns(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_patterns_domain ON patterns(domain);
CREATE INDEX IF NOT EXISTS idx_patterns_kind ON patterns(kind);
CREATE INDEX IF NOT EXISTS idx_patterns_strength ON patterns(strength DESC);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_id);

CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts USING fts5(
  id UNINDEXED,
  title,
  body,
  features,
  tags,
  content='patterns',
  content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


class PatternStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._db() as conn:
            conn.executescript(SCHEMA)
            # Ensure FTS triggers for content sync
            conn.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS patterns_ai AFTER INSERT ON patterns BEGIN
                  INSERT INTO patterns_fts(rowid, id, title, body, features, tags)
                  VALUES (
                    new.rowid, new.id, new.title, new.body,
                    new.features_json, new.tags_json
                  );
                END;
                CREATE TRIGGER IF NOT EXISTS patterns_ad AFTER DELETE ON patterns BEGIN
                  INSERT INTO patterns_fts(patterns_fts, rowid, id, title, body, features, tags)
                  VALUES ('delete', old.rowid, old.id, old.title, old.body, old.features_json, old.tags_json);
                END;
                CREATE TRIGGER IF NOT EXISTS patterns_au AFTER UPDATE ON patterns BEGIN
                  INSERT INTO patterns_fts(patterns_fts, rowid, id, title, body, features, tags)
                  VALUES ('delete', old.rowid, old.id, old.title, old.body, old.features_json, old.tags_json);
                  INSERT INTO patterns_fts(rowid, id, title, body, features, tags)
                  VALUES (
                    new.rowid, new.id, new.title, new.body,
                    new.features_json, new.tags_json
                  );
                END;
                """
            )

    @staticmethod
    def _pattern_to_row(p: Pattern) -> Dict[str, Any]:
        return {
            "id": p.id,
            "title": p.title,
            "body": p.body,
            "kind": p.kind.value,
            "domain": p.domain.value,
            "features_json": json.dumps(p.features, ensure_ascii=False),
            "tags_json": json.dumps(p.tags, ensure_ascii=False),
            "confidence": p.confidence,
            "strength": p.strength,
            "evidence_json": json.dumps([e.to_dict() for e in p.evidence], ensure_ascii=False),
            "metadata_json": json.dumps(p.metadata, ensure_ascii=False),
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "last_used_at": p.last_used_at,
            "use_count": p.use_count,
            "content_hash": p.content_hash,
        }

    @staticmethod
    def _row_to_pattern(row: sqlite3.Row) -> Pattern:
        d = dict(row)
        return Pattern.from_dict(
            {
                "id": d["id"],
                "title": d["title"],
                "body": d["body"],
                "kind": d["kind"],
                "domain": d["domain"],
                "features": json.loads(d["features_json"] or "[]"),
                "tags": json.loads(d["tags_json"] or "[]"),
                "confidence": d["confidence"],
                "strength": d["strength"],
                "evidence": json.loads(d["evidence_json"] or "[]"),
                "metadata": json.loads(d["metadata_json"] or "{}"),
                "created_at": d["created_at"],
                "updated_at": d["updated_at"],
                "last_used_at": d["last_used_at"],
                "use_count": d["use_count"],
                "content_hash": d["content_hash"],
            }
        )

    def upsert_pattern(self, pattern: Pattern) -> Pattern:
        row = self._pattern_to_row(pattern)
        cols = ", ".join(row.keys())
        placeholders = ", ".join(":" + k for k in row.keys())
        updates = ", ".join(f"{k}=excluded.{k}" for k in row.keys() if k != "id")
        sql = f"""
        INSERT INTO patterns ({cols}) VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET {updates}
        """
        with self._db() as conn:
            conn.execute(sql, row)
        return pattern

    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        with self._db() as conn:
            cur = conn.execute("SELECT * FROM patterns WHERE id = ?", (pattern_id,))
            row = cur.fetchone()
            return self._row_to_pattern(row) if row else None

    def delete_pattern(self, pattern_id: str) -> bool:
        with self._db() as conn:
            cur = conn.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
            return cur.rowcount > 0

    def list_patterns(
        self,
        *,
        domain: Optional[str] = None,
        kind: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Pattern]:
        clauses: List[str] = []
        params: List[Any] = []
        if domain:
            clauses.append("domain = ?")
            params.append(domain)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM patterns {where} ORDER BY strength DESC, updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._db() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_pattern(r) for r in rows]

    def all_patterns(self, limit: int = 5000) -> List[Pattern]:
        return self.list_patterns(limit=limit)

    def structural_patterns(self, *, limit: int = 200) -> List[Pattern]:
        """High-value nodes for recognition shortlist (rules/skills/events first)."""
        kinds = (
            "rule",
            "skill",
            "sequence",
            "synthesis",
            "event",
            "episode",
            "task",
            "agent",
            "model",
            "tool",
        )
        out: List[Pattern] = []
        seen: set[str] = set()
        with self._db() as conn:
            for kind in kinds:
                rows = conn.execute(
                    """
                    SELECT * FROM patterns
                    WHERE kind = ?
                    ORDER BY strength DESC, use_count DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (kind, max(8, limit // len(kinds))),
                ).fetchall()
                for row in rows:
                    p = self._row_to_pattern(row)
                    if p.id not in seen:
                        seen.add(p.id)
                        out.append(p)
            # starters tagged
            rows = conn.execute(
                """
                SELECT * FROM patterns
                WHERE tags_json LIKE '%starter%' OR tags_json LIKE '%bootstrap%'
                ORDER BY strength DESC LIMIT 40
                """
            ).fetchall()
            for row in rows:
                p = self._row_to_pattern(row)
                if p.id not in seen:
                    seen.add(p.id)
                    out.append(p)
        return out[:limit]

    def candidate_pool(
        self,
        query: str,
        *,
        domain: Optional[str] = None,
        fts_limit: int = 48,
        structural_limit: int = 120,
        fill_limit: int = 80,
    ) -> List[Pattern]:
        """Fast shortlist: FTS hits + structural priors + optional domain fill.

        Avoids scoring the entire fabric dump on every perceive.
        """
        seen: set[str] = set()
        pool: List[Pattern] = []

        def _add(items: List[Pattern]) -> None:
            for p in items:
                if p.id not in seen:
                    seen.add(p.id)
                    pool.append(p)

        _add(self.fts_search(query, limit=fts_limit))
        _add(self.structural_patterns(limit=structural_limit))
        if domain:
            _add(self.list_patterns(domain=domain, limit=fill_limit // 2))
        # small strength-ranked fill for coverage without full table scan
        if len(pool) < fts_limit + 40:
            _add(self.list_patterns(limit=fill_limit))
        return pool

    def decay_fabric_noise(
        self,
        *,
        max_touch: int = 400,
        min_age_days: float = 0.5,
        strength_floor: float = 0.15,
        delta: float = 0.04,
    ) -> Dict[str, int]:
        """Weaken unused fabric/code dumps so they stop drowning recognition."""
        import time as _time

        now = _time.time()
        min_age = min_age_days * 86400
        weakened = 0
        skipped = 0
        pats = self.list_patterns(limit=3000)
        for p in pats:
            tags = set(p.tags or [])
            is_fabric = "fabric" in tags or (p.metadata or {}).get("fabric")
            is_code_dump = p.domain.value == "code" and p.kind.value in {"prototype", "template"}
            if not (is_fabric or is_code_dump):
                skipped += 1
                continue
            if p.kind.value in {"rule", "skill", "event", "episode", "task"}:
                skipped += 1
                continue
            if "starter" in tags or "bootstrap" in tags:
                skipped += 1
                continue
            age = now - float(p.last_used_at or p.updated_at or p.created_at or 0)
            if age < min_age:
                skipped += 1
                continue
            if p.use_count > 3 and p.strength > 0.55:
                skipped += 1
                continue
            old = p.strength
            p.strength = max(strength_floor, p.strength - delta)
            if p.strength < old:
                self.upsert_pattern(p)
                weakened += 1
            if weakened >= max_touch:
                break
        return {"weakened": weakened, "skipped": skipped}

    def fts_search(self, query: str, limit: int = 20) -> List[Pattern]:
        q = (query or "").strip()
        if not q:
            return []
        # Escape FTS5 special chars lightly
        safe = re_sub_fts(q)
        sql = """
        SELECT p.* FROM patterns_fts f
        JOIN patterns p ON p.id = f.id
        WHERE patterns_fts MATCH ?
        ORDER BY bm25(patterns_fts), p.strength DESC
        LIMIT ?
        """
        with self._db() as conn:
            try:
                rows = conn.execute(sql, (safe, limit)).fetchall()
            except sqlite3.OperationalError:
                # fallback: LIKE search
                like = f"%{q}%"
                rows = conn.execute(
                    """
                    SELECT * FROM patterns
                    WHERE title LIKE ? OR body LIKE ? OR features_json LIKE ?
                    ORDER BY strength DESC LIMIT ?
                    """,
                    (like, like, like, limit),
                ).fetchall()
            return [self._row_to_pattern(r) for r in rows]

    def upsert_link(self, link: Link) -> Link:
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO links (id, source_id, target_id, kind, weight, note, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, kind) DO UPDATE SET
                  weight=excluded.weight,
                  note=excluded.note,
                  metadata_json=excluded.metadata_json
                """,
                (
                    link.id,
                    link.source_id,
                    link.target_id,
                    link.kind.value,
                    link.weight,
                    link.note,
                    json.dumps(link.metadata, ensure_ascii=False),
                    link.created_at,
                ),
            )
            # fetch canonical id if conflict updated existing
            row = conn.execute(
                "SELECT * FROM links WHERE source_id=? AND target_id=? AND kind=?",
                (link.source_id, link.target_id, link.kind.value),
            ).fetchone()
            if row:
                return Link.from_dict(
                    {
                        "id": row["id"],
                        "source_id": row["source_id"],
                        "target_id": row["target_id"],
                        "kind": row["kind"],
                        "weight": row["weight"],
                        "note": row["note"],
                        "metadata": json.loads(row["metadata_json"] or "{}"),
                        "created_at": row["created_at"],
                    }
                )
        return link

    def links_for(self, pattern_id: str, *, limit: int = 50) -> List[Link]:
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM links
                WHERE source_id = ? OR target_id = ?
                ORDER BY weight DESC LIMIT ?
                """,
                (pattern_id, pattern_id, limit),
            ).fetchall()
            out: List[Link] = []
            for row in rows:
                out.append(
                    Link.from_dict(
                        {
                            "id": row["id"],
                            "source_id": row["source_id"],
                            "target_id": row["target_id"],
                            "kind": row["kind"],
                            "weight": row["weight"],
                            "note": row["note"],
                            "metadata": json.loads(row["metadata_json"] or "{}"),
                            "created_at": row["created_at"],
                        }
                    )
                )
            return out

    def neighbors(self, pattern_id: str, *, limit: int = 30) -> List[Pattern]:
        links = self.links_for(pattern_id, limit=limit)
        ids: List[str] = []
        for lk in links:
            other = lk.target_id if lk.source_id == pattern_id else lk.source_id
            if other not in ids:
                ids.append(other)
        out: List[Pattern] = []
        for i in ids[:limit]:
            p = self.get_pattern(i)
            if p:
                out.append(p)
        return out

    def count(self) -> Dict[str, int]:
        with self._db() as conn:
            pc = conn.execute("SELECT COUNT(*) AS c FROM patterns").fetchone()["c"]
            lc = conn.execute("SELECT COUNT(*) AS c FROM links").fetchone()["c"]
            return {"patterns": int(pc), "links": int(lc)}

    def set_meta(self, key: str, value: str) -> None:
        with self._db() as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_meta(self, key: str, default: str = "") -> str:
        with self._db() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return str(row["value"]) if row else default


def re_sub_fts(q: str) -> str:
    """Make a tolerable FTS5 query from free text."""
    import re

    tokens = re.findall(r"[A-Za-z0-9_\-]{2,}", q)
    if not tokens:
        return '""'
    # OR query for broader recall
    return " OR ".join(tokens[:12])
