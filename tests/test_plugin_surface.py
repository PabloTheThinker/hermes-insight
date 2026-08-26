"""Plugin hygiene: valid Hermes hooks and advisory manifest fields."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "hermes_plugin" / "hermes_insight_plugin"
PLUGIN_PY = PLUGIN / "__init__.py"
PLUGIN_YAML = PLUGIN / "plugin.yaml"


def test_plugin_registers_on_session_end_only():
    text = PLUGIN_PY.read_text(encoding="utf-8")
    assert 'register_hook("on_session_end"' in text
    assert 'register_hook("session_end"' not in text
    assert '("session_end", _on_session_end)' not in text


def test_plugin_yaml_declares_organ_hygiene():
    text = PLUGIN_YAML.read_text(encoding="utf-8")
    assert "kind: standalone" in text
    assert "provides_hooks:" in text
    assert "  - on_session_end" in text
    assert "session_end" not in text.replace("on_session_end", "")
    assert 'python_dependencies:' in text
    assert '"hermes-insight>=0.9.0,<0.10"' in text
    assert "  - insight_remember" in text
    assert "config_schema:" in text
    assert "  agent_id:" in text
    assert "  db_path:" in text
    assert "  agent_tier:" in text
    assert "  - insight_perceive" in text
    assert "  - insight_plan" in text
