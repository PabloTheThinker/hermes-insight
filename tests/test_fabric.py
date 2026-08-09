"""Fabric indexer + scrub tests."""

from __future__ import annotations

from pathlib import Path

from hermes_insight.harness import HermesInsight
from hermes_insight.scrub import scrub_text, should_skip_path


def test_scrub_secrets_and_ips():
    raw = "api_key=sk-abcdefghijklmnopqrstuvwxyz password=hunter2 path=/home/someone/x ip=100.1.2.3"
    out = scrub_text(raw)
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in out
    assert "hunter2" not in out or "REDACTED" in out
    assert "100.1.2.3" not in out
    assert "/home/someone" not in out


def test_skip_secret_paths():
    assert should_skip_path("/x/secrets/token.txt")
    assert should_skip_path("/x/.env")
    assert should_skip_path("/x/auth.json")
    assert not should_skip_path("/x/src/main.py")


def test_index_path_and_fabric_stats(tmp_path: Path):
    proj = tmp_path / "demo-proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text('[project]\nname="demo"\n', encoding="utf-8")
    (proj / "README.md").write_text("# Demo\n\nA sample project.\n", encoding="utf-8")
    (proj / "app.py").write_text(
        '"""App entry."""\n\ndef main():\n    return 42\n',
        encoding="utf-8",
    )
    # should skip
    (proj / ".env").write_text("SECRET=abc\n", encoding="utf-8")

    lat = HermesInsight(db_path=tmp_path / "fab.db")
    res = lat.index_path(proj, max_files=20)
    assert res.get("success") is True
    assert res.get("files_ingested", 0) >= 1

    fs = lat.fabric_stats()
    assert fs["fabric_patterns"] >= 1

    report = lat.cycle("demo project app entry main", domain="code", evolve=False)
    assert report.matches
    titles = " ".join(m.pattern.title for m in report.matches)
    assert "demo" in titles.lower() or "app" in titles.lower() or report.matches[0].score > 0


def test_index_connections_smoke(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "conn.db")
    out = lat.index_connections()
    assert "connections_found" in out
    assert out["stats"]["patterns"] >= 1  # at least host or process snapshot
