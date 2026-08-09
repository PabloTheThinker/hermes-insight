"""Forge product tests."""

from __future__ import annotations

from pathlib import Path

from hermes_insight import HermesInsight


def test_forge_creates_products(tmp_path: Path):
    lat = HermesInsight(db_path=tmp_path / "f.db")
    lat.ingest(
        "project:alpha",
        "python service with retry backoff",
        domain="code",
        tags=["fabric", "project", "python"],
        features=["retry", "backoff", "service", "python"],
        metadata={"fabric": "project", "name": "alpha", "languages": ["python"]},
    )
    lat.ingest(
        "project:beta",
        "python worker with retry and circuit",
        domain="code",
        tags=["fabric", "project", "python"],
        features=["retry", "circuit", "worker", "python"],
        metadata={"fabric": "project", "name": "beta", "languages": ["python"]},
    )
    lat.ingest(
        "listen:alpha",
        "Process alpha listens on ports 8080",
        domain="system",
        tags=["fabric", "connection", "listen"],
        features=["listen", "port", "alpha", "connection"],
        metadata={"fabric": "listen", "process": "alpha", "ports": ["8080"], "binds": ["loopback"]},
    )
    out = tmp_path / "forged"
    result = lat.forge(out_dir=out, write_synthesis=True)
    assert result["success"]
    run = Path(result["run_dir"])
    assert (run / "01-orientation-map.md").exists()
    assert (run / "04-invention-seeds.md").exists()
    assert (run / "README.md").exists()
    assert len(result["synthesis_ids"]) >= 1
    invent = (run / "04-invention-seeds.md").read_text(encoding="utf-8")
    assert "Invention" in invent or "seed" in invent.lower()
